"""
数据库配置 - SQLAlchemy async engine + session factory
"""
import os
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from app.core.config import config


# 确保数据目录存在
os.makedirs(config.DATA_DIR, exist_ok=True)

# 创建异步引擎
engine = create_async_engine(
    config.DATABASE_URL,
    echo=False,
    future=True,
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
    """FastAPI 依赖注入: 获取数据库 session"""
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
    """初始化数据库 - 创建所有表"""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def close_db():
    """关闭数据库连接"""
    await engine.dispose()
