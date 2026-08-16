"""
API 认证中间件测试 (v4.1 安全加固)

不触碰数据库：仅验证中间件的放行/拦截逻辑。
"""
import pytest
from httpx import ASGITransport, AsyncClient

from app.core.config import config


@pytest.fixture
def anyio_backend():
    return "asyncio"


def _client():
    from app.main import app
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


async def test_auth_disabled_allows_all():
    """API_AUTH_TOKEN 为空 = 认证关闭，所有请求放行"""
    import app.core.security as sec
    from fastapi import Request

    # 直接验证纯逻辑
    assert sec.auth_middleware_check(None, "") is None  # type: ignore[arg-type]


async def test_health_exempt_when_auth_enabled(monkeypatch):
    """启用认证后 /health 仍可匿名访问"""
    monkeypatch.setattr(config, "API_AUTH_TOKEN", "test-token-123")
    async with _client() as c:
        resp = await c.get("/health")
        assert resp.status_code == 200


async def test_protected_path_rejected_without_token(monkeypatch):
    """启用认证后，受保护路径无 Token 返回 401（路由不存在也无妨，认证先于路由）"""
    monkeypatch.setattr(config, "API_AUTH_TOKEN", "test-token-123")
    async with _client() as c:
        resp = await c.get("/api/v1/nonexistent-path")
        assert resp.status_code == 401
        assert "未授权" in resp.json()["detail"]


async def test_protected_path_rejected_with_wrong_token(monkeypatch):
    """错误 Token 返回 401"""
    monkeypatch.setattr(config, "API_AUTH_TOKEN", "test-token-123")
    async with _client() as c:
        resp = await c.get(
            "/api/v1/nonexistent-path",
            headers={"Authorization": "Bearer wrong-token"},
        )
        assert resp.status_code == 401


async def test_protected_path_passes_with_correct_token(monkeypatch):
    """正确 Token 放行（此处路由不存在 → 404，证明已通过认证层）"""
    monkeypatch.setattr(config, "API_AUTH_TOKEN", "test-token-123")
    async with _client() as c:
        resp_bearer = await c.get(
            "/api/v1/nonexistent-path",
            headers={"Authorization": "Bearer test-token-123"},
        )
        resp_header = await c.get(
            "/api/v1/nonexistent-path",
            headers={"X-API-Token": "test-token-123"},
        )
        assert resp_bearer.status_code == 404
        assert resp_header.status_code == 404


async def test_extract_api_token_prioritizes_bearer():
    """Bearer 头优先于 X-API-Token"""
    import app.core.security as sec

    class FakeRequest:
        def __init__(self, headers):
            self.headers = headers

    req = FakeRequest({"Authorization": "Bearer abc", "X-API-Token": "xyz"})
    assert sec.extract_api_token(req) == "abc"
    req2 = FakeRequest({"X-API-Token": "xyz"})
    assert sec.extract_api_token(req2) == "xyz"
    req3 = FakeRequest({})
    assert sec.extract_api_token(req3) == ""
