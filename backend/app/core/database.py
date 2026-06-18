"""
数据库配置 - SQLAlchemy async engine + session factory
v2.1: 连接池配置、Alembic 迁移支持
"""
import os
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
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
        # SQLite 单连接模式（避免写锁冲突）
        connect_args={"check_same_thread": False},
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
    """
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_db():
    """
    初始化数据库 - 创建所有表。
    生产环境建议使用 Alembic 迁移。
    """
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def close_db():
    """关闭数据库连接"""
    await engine.dispose()
