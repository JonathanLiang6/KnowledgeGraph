"""
测试配置与共享 fixtures — v4.1 全面隔离版

关键原则：所有测试运行在独立临时目录 + 临时 SQLite 上，绝不触碰
真实生产库（backend/data/knowledge_graph.db）、LanceDB 索引与上传文件。

环境变量必须在导入任何 app.* 模块之前设置（config 在导入时读取 env）。
"""
import asyncio
import os
import shutil
import tempfile

import pytest
from httpx import ASGITransport, AsyncClient

# ── 环境隔离（先于 app 导入执行）────────────────────────────────
_TEST_ROOT = tempfile.mkdtemp(prefix="kg_test_")
_TEST_DB = os.path.join(_TEST_ROOT, "test.db").replace(os.sep, "/")

os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{_TEST_DB}"
os.environ["DATA_DIR"] = _TEST_ROOT
os.environ["LANCEDB_PATH"] = os.path.join(_TEST_ROOT, "lancedb")
os.environ["LOCAL_DATA_DIR"] = os.path.join(_TEST_ROOT, "files")
os.environ.setdefault("DEEPSEEK_API_KEY", "")


@pytest.fixture(scope="session")
def event_loop():
    """创建 session 级事件循环"""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session", autouse=True)
def _init_test_db():
    """
    在临时数据库上初始化表结构（等价于 main.lifespan 的核心步骤）。

    v4.1 (#48)：ASGITransport 不触发 lifespan，此前测试直接落到生产库；
    现在统一在临时库上 init_db，测试结束清理整个临时目录。

    注：用独立事件循环执行 — 本仓 anyio 与 pytest-asyncio 双插件共存，
    session 级异步 fixture 的循环会在首个模块后被关闭导致级联失败；
    文件库为 NullPool，跨循环无残留连接，安全。
    """
    import asyncio

    from app.core.database import init_db

    asyncio.run(init_db())
    yield
    try:
        from app.core.database import close_db
        asyncio.run(close_db())
    except Exception:
        pass
    shutil.rmtree(_TEST_ROOT, ignore_errors=True)


@pytest.fixture
async def async_client():
    """异步 HTTP 测试客户端（请求经 app 的 get_db 走临时库）"""
    from app.main import app
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client


@pytest.fixture
async def db_session():
    """与应用同源（临时库）的数据库会话，用于服务层单测"""
    from app.core.database import async_session_factory
    async with async_session_factory() as session:
        yield session
