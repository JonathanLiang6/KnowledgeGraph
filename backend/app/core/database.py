"""
数据库配置 - SQLAlchemy async engine + session factory
v2.1: 连接池配置、Alembic 迁移支持
"""
import os
import logging
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.pool import StaticPool
from app.core.config import config

logger = logging.getLogger(__name__)


# 确保数据目录存在
os.makedirs(config.DATA_DIR, exist_ok=True)

# 判断是否是 SQLite
_is_sqlite = "sqlite" in config.DATABASE_URL

# 创建异步引擎（P2: 连接池配置）
if _is_sqlite:
    engine = create_async_engine(
        config.DATABASE_URL,
        echo=False,
        future=True,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
else:
    # PostgreSQL/MySQL 连接池配置
    engine = create_async_engine(
        config.DATABASE_URL,
        echo=False,
        future=True,
        pool_size=10,
        max_overflow=20,
        pool_recycle=3600,
        pool_pre_ping=True,
    )

# 创建异步 session 工厂
async_session_factory = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


class Base(DeclarativeBase):
    """SQLAlchemy Declarative Base - 所有模型继承此类"""
    pass


# 确保所有模型在 create_all 前被导入（字符串关系依赖）
import app.models.knowledge_base  # noqa: E402
import app.models.document  # noqa: E402
import app.models.system_setting  # noqa: E402
import app.models.graph_entity  # noqa: E402  # Phase 1: GraphRAG
import app.models.topology  # noqa: E402  # v3.2: Q10 拓扑导航


async def get_db() -> AsyncSession:
    """
    FastAPI 依赖注入: 获取数据库 session。
    每个请求一个事务，请求成功自动 commit，异常自动 rollback。

    v2.4: 移除冗余 session.close() — async with 已处理清理。
    """
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def init_db():
    """
    初始化数据库 - 创建所有表 + 迁移 (v2.4: WAL模式 + file_hash列迁移)。

    生产环境建议使用 Alembic 迁移。
    """
    async with engine.begin() as conn:
        # 创建新表
        await conn.run_sync(Base.metadata.create_all)

        # WAL 模式
        if _is_sqlite:
            await conn.run_sync(
                lambda sync_conn: sync_conn.exec_driver_sql("PRAGMA journal_mode=WAL")
            )

        # v2.4: 迁移 — 为已有 documents 表添加 file_hash 列
        if _is_sqlite:
            try:
                await conn.run_sync(
                    lambda sync_conn: sync_conn.exec_driver_sql(
                        "ALTER TABLE documents ADD COLUMN file_hash VARCHAR(64)"
                    )
                )
                logger.info("数据库迁移: 已添加 documents.file_hash 列")
            except Exception:
                # 列已存在，忽略
                pass

        # Phase 1: 迁移 — 为 graph_entities/graph_relations 添加 kb_id 列
        if _is_sqlite:
            for table_name in ["graph_entities", "graph_relations"]:
                try:
                    await conn.run_sync(
                        lambda sync_conn, tn=table_name: sync_conn.exec_driver_sql(
                            f"ALTER TABLE {tn} ADD COLUMN kb_id VARCHAR(36)"
                        )
                    )
                    logger.info(f"数据库迁移: 已添加 {table_name}.kb_id 列")
                except Exception:
                    pass  # 列已存在


async def close_db():
    """关闭数据库连接"""
    await engine.dispose()
