"""
FastAPI 应用入口 - v3.1 智能教学知识图谱管理平台
"""
import logging
import asyncio
import os
import uuid
import time
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import config, APP_VERSION
from app.core.database import init_db, close_db
from app.api.v1.router import api_router

# 配置日志
logging.basicConfig(
    level=getattr(logging, config.LOG_LEVEL),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # ─── 启动 ───────────────────────────────────────────────
    logger.info("=" * 50)
    logger.info(f"🚀 KnowledgeGraph v{APP_VERSION} 启动中...")
    logger.info(f"   DeepSeek API: {config.DEEPSEEK_API_BASE}")
    logger.info(f"   Chat Model: {config.DEEPSEEK_CHAT_MODEL}")
    logger.info(f"   Embedding Model: {config.EMBEDDING_MODEL}")
    logger.info(f"   API Configured: {config.is_api_key_set}")
    logger.info(f"   Max File Size: {config.MAX_FILE_SIZE_MB}MB")
    logger.info(f"   Max Concurrent Processing: {config.MAX_CONCURRENT_DOCUMENT_PROCESSING}")

    # 初始化数据库 (v2.4: 失败时阻止启动)
    try:
        await init_db()
        logger.info("✅ 数据库初始化完成")
    except Exception as e:
        logger.critical(f"❌ 数据库初始化失败, 应用无法启动: {e}")
        raise RuntimeError(f"数据库初始化失败: {e}") from e

    # P2: 从 LanceDB 恢复检索索引 (v2.5: 使用模块级单例)
    try:
        from app.services.hybrid_search import hybrid_search_service
        hybrid_search_service.vector_store.create_or_open_table("chunks")
        if hybrid_search_service.vector_store.count > 0:
            hybrid_search_service.rebuild_index_from_store()
            logger.info(f"✅ 检索索引恢复: {hybrid_search_service.vector_store.count} 条向量记录")
        else:
            logger.info("📭 检索索引为空，跳过恢复")
    except Exception as e:
        logger.warning(f"⚠️ 检索索引恢复跳过: {e}")

    # v3.2: 清理孤立节点 — 删除无法建立任何链接的实体
    try:
        from app.core.database import async_session_factory
        from app.models.knowledge_base import KnowledgeBase
        from app.services.graph_service import GraphService
        from sqlalchemy import select as sa_select

        async with async_session_factory() as session:
            kb_result = await session.execute(sa_select(KnowledgeBase.id))
            kb_ids = [row[0] for row in kb_result]
            for kid in kb_ids:
                try:
                    result = await GraphService.clean_orphan_nodes(session, kid)
                    if result["deleted"] > 0:
                        logger.info(f"🧹 KB {kid}: 清理 {result['deleted']} 个孤立节点")
                except Exception as e:
                    logger.debug(f"KB {kid} 孤立节点清理跳过: {e}")
    except Exception as e:
        logger.warning(f"⚠️ 孤立节点清理跳过: {e}")

    # Phase 1: 图谱数据迁移 — 将现有 document.graph_data JSON → GraphEntity/GraphRelation 表
    try:
        from app.core.database import async_session_factory
        from app.models.document import Document, DocumentStatus
        from app.models.graph_entity import GraphEntity
        from app.services.graph_service import GraphService
        from sqlalchemy import select, func

        async with async_session_factory() as session:
            # 检查是否需要迁移
            doc_count = await session.execute(
                select(func.count(Document.id)).where(Document.graph_data.isnot(None))
            )
            entity_count = await session.execute(
                select(func.count(GraphEntity.id))
            )
            if doc_count.scalar() > 0 and entity_count.scalar() == 0:
                logger.info("🔄 开始图谱数据迁移...")
                doc_result = await session.execute(
                    select(Document).where(
                        Document.graph_data.isnot(None),
                        Document.status == DocumentStatus.DONE,
                    )
                )
                docs = doc_result.scalars().all()
                migrated = 0
                for doc in docs:
                    try:
                        stats = await GraphService.build_graph(
                            db=session,
                            kb_id=doc.kb_id,
                            nodes=doc.graph_data.get("nodes", []),
                            links=doc.graph_data.get("links", []),
                            doc_id=doc.id,
                        )
                        migrated += 1
                    except Exception as e:
                        logger.warning(f"迁移文档图谱失败 doc={doc.id}: {e}")
                logger.info(f"✅ 图谱数据迁移完成: {migrated}/{len(docs)} 个文档")
            else:
                logger.debug("📭 图谱数据无需迁移")
    except Exception as e:
        logger.warning(f"⚠️ 图谱数据迁移跳过: {e}")

    # P1: 恢复中断的文档处理任务 (v2.5: 存储 task 句柄以便关闭时取消)
    app.state._resume_task = None
    try:
        from app.tasks.document_tasks import resume_pending_documents
        # 延迟恢复（等待其他服务初始化完成）
        app.state._resume_task = asyncio.create_task(_delayed_resume())
    except Exception as e:
        logger.warning(f"⚠️ 文档恢复初始化跳过: {e}")

    logger.info(f"🌐 服务器启动于 http://{config.SERVER_HOST}:{config.SERVER_PORT}")
    logger.info(f"📚 API 文档: http://{config.SERVER_HOST}:{config.SERVER_PORT}/docs")
    logger.info("=" * 50)

    yield

    # ─── 关闭 ───────────────────────────────────────────────
    logger.info(f"🛑 KnowledgeGraph v{APP_VERSION} 关闭中...")
    # 取消后台恢复任务
    if app.state._resume_task and not app.state._resume_task.done():
        app.state._resume_task.cancel()
        try:
            await app.state._resume_task
        except asyncio.CancelledError:
            logger.info("后台恢复任务已取消")
    await close_db()
    logger.info("✅ 数据库连接已关闭")


async def _delayed_resume():
    """延迟恢复中断的文档处理任务（等待 Embedding 模型等加载完成）"""
    await asyncio.sleep(2)  # v2.4: 缩短等待时间
    try:
        from app.tasks.document_tasks import resume_pending_documents
        await resume_pending_documents()
    except Exception as e:
        logger.error(f"文档恢复失败: {e}")


# 创建 FastAPI 应用
app = FastAPI(
    title="KnowledgeGraph - 教学知识图谱管理后台",
    description="基于 DeepSeek V4 + GraphRAG + AgentRAG 的智能教学知识图谱管理平台",
    version=APP_VERSION,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS 中间件 — 从配置读取允许的来源
_cors_origins_str = os.getenv("CORS_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000,http://localhost:8013,http://127.0.0.1:8013")
_cors_origins = [o.strip() for o in _cors_origins_str.split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Request-ID 中间件 — 注入唯一请求 ID 到响应头和日志上下文
@app.middleware("http")
async def request_id_middleware(request: Request, call_next):
    request_id = request.headers.get("X-Request-ID", str(uuid.uuid4())[:8])
    request.state.request_id = request_id
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    return response

# 慢请求日志中间件 — 超过阈值的请求记录 WARNING
@app.middleware("http")
async def slow_request_middleware(request: Request, call_next):
    start = time.monotonic()
    response = await call_next(request)
    elapsed = time.monotonic() - start
    if elapsed > 3.0:
        logger.warning(f"慢请求 {request.method} {request.url.path} 耗时 {elapsed:.2f}s")
    return response

# 注册 API 路由
app.include_router(api_router)


# 健康检查
@app.get("/health")
async def health_check():
    """健康检查"""
    from app.tasks.document_tasks import _active_processing_count
    return {
        "status": "healthy",
        "version": APP_VERSION,
        "api_configured": config.is_api_key_set,
        "active_processing": _active_processing_count,
        "max_file_size_mb": config.MAX_FILE_SIZE_MB,
    }
