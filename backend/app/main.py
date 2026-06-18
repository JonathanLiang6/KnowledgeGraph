"""
FastAPI 应用入口 - v2.1 企业级知识图谱管理后台
"""
import logging
import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import config
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
    logger.info("🚀 KnowledgeGraph v2.4 启动中...")
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

    # P2: 从 LanceDB 恢复检索索引
    try:
        from app.services.hybrid_search import HybridSearchService
        hybrid = HybridSearchService()
        hybrid.vector_store.create_or_open_table("chunks")
        if hybrid.vector_store.count > 0:
            hybrid.rebuild_index_from_store()
            logger.info(f"✅ 检索索引恢复: {hybrid.vector_store.count} 条向量记录")
        else:
            logger.info("📭 检索索引为空，跳过恢复")
    except Exception as e:
        logger.warning(f"⚠️ 检索索引恢复跳过: {e}")

    # P1: 恢复中断的文档处理任务
    try:
        from app.tasks.document_tasks import resume_pending_documents
        # 延迟恢复（等待其他服务初始化完成）
        asyncio.create_task(_delayed_resume())
    except Exception as e:
        logger.warning(f"⚠️ 文档恢复初始化跳过: {e}")

    logger.info(f"🌐 服务器启动于 http://{config.SERVER_HOST}:{config.SERVER_PORT}")
    logger.info(f"📚 API 文档: http://{config.SERVER_HOST}:{config.SERVER_PORT}/docs")
    logger.info("=" * 50)

    yield

    # ─── 关闭 ───────────────────────────────────────────────
    logger.info("🛑 KnowledgeGraph v2.4 关闭中...")
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
    description="基于 DeepSeek V4 + GraphRAG 的企业级知识图谱问答系统 v2.1",
    version="2.4.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS 中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:8013",
        "http://127.0.0.1:8013",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册 API 路由
app.include_router(api_router)


# 健康检查
@app.get("/health")
async def health_check():
    """健康检查"""
    from app.tasks.document_tasks import _active_processing_count
    return {
        "status": "healthy",
        "version": "2.4.0",
        "api_configured": config.is_api_key_set,
        "active_processing": _active_processing_count,
        "max_file_size_mb": config.MAX_FILE_SIZE_MB,
    }


# ============================================================
# 旧版兼容路由（从 v1 迁移过渡期使用）
# ============================================================
@app.get("/api/overview")
async def legacy_overview():
    """旧版概览接口 - 兼容过渡（后续移除）"""
    return {
        "system": "KnowledgeGraph v2.4.0",
        "status": "running",
        "message": "请使用 /api/v1/settings 获取系统信息",
    }


@app.get("/api/settings")
async def legacy_settings():
    """旧版设置接口 - 重定向提示"""
    from fastapi.responses import RedirectResponse
    return RedirectResponse(url="/api/v1/settings")
