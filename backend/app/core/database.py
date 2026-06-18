"""
数据库配置 - SQLAlchemy async engine + session factory
v2.1: 连接池配置、Alembic 迁移支持
"""
import os
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.pool import StaticPool
from app.core.config import config


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
    初始化数据库 - 创建所有表并启用 SQLite WAL 模式。
    v2.4: WAL 模式提升 SQLite 并发读写性能。
    """
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        if _is_sqlite:
            await conn.run_sync(
                lambda sync_conn: sync_conn.exec_driver_sql("PRAGMA journal_mode=WAL")
            )


async def close_db():
    """关闭数据库连接"""
    await engine.dispose()
