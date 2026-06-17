"""
FastAPI 应用入口 - 模块化企业级知识图谱管理后台
"""
import logging
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
    # 启动
    logger.info("=" * 50)
    logger.info("🚀 知识图谱管理后台启动中...")
    logger.info(f"   DeepSeek API: {config.DEEPSEEK_API_BASE}")
    logger.info(f"   Chat Model: {config.DEEPSEEK_CHAT_MODEL}")
    logger.info(f"   Embedding Model: {config.EMBEDDING_MODEL}")
    logger.info(f"   API Configured: {config.is_api_key_set}")

    # 初始化数据库
    try:
        await init_db()
        logger.info("✅ 数据库初始化完成")
    except Exception as e:
        logger.error(f"❌ 数据库初始化失败: {e}")

    logger.info(f"🌐 服务器启动于 http://{config.SERVER_HOST}:{config.SERVER_PORT}")
    logger.info(f"📚 API 文档: http://{config.SERVER_HOST}:{config.SERVER_PORT}/docs")
    logger.info("=" * 50)

    yield

    # 关闭
    logger.info("🛑 知识图谱管理后台关闭中...")
    await close_db()
    logger.info("✅ 数据库连接已关闭")


# 创建 FastAPI 应用
app = FastAPI(
    title="KnowledgeGraph - 教学知识图谱管理后台",
    description="基于 DeepSeek V4 + GraphRAG 的企业级知识图谱问答系统",
    version="2.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS 中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生产环境应限制具体域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册 API 路由
app.include_router(api_router)


# 健康检查（简化路径）
@app.get("/health")
async def health_check():
    """健康检查"""
    return {
        "status": "healthy",
        "version": "2.0.0",
        "api_configured": config.is_api_key_set,
    }


# ============================================================
# 旧版兼容路由（从 v1 迁移过渡期使用）
# ============================================================
@app.get("/api/overview")
async def legacy_overview():
    """旧版概览接口 - 兼容过渡（后续移除）"""
    return {
        "system": "KnowledgeGraph v2.0.0",
        "status": "running",
        "message": "请使用 /api/v1/settings 获取系统信息",
    }


@app.get("/api/settings")
async def legacy_settings():
    """旧版设置接口 - 重定向提示"""
    from fastapi.responses import RedirectResponse
    return RedirectResponse(url="/api/v1/settings")
