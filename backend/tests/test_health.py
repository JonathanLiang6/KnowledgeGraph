"""
健康检查 & 基础 API 冒烟测试
"""
import pytest


@pytest.mark.anyio
async def test_health_check(async_client):
    """验证 /health 端点返回正常"""
    response = await async_client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert "version" in data
    assert "active_processing" in data


@pytest.mark.anyio
async def test_api_docs_available(async_client):
    """验证 OpenAPI 文档可访问"""
    response = await async_client.get("/docs")
    assert response.status_code == 200


@pytest.mark.anyio
async def test_list_models(async_client):
    """验证模型列表端点"""
    response = await async_client.get("/api/v1/chat/models")
    assert response.status_code == 200
    data = response.json()
    assert "data" in data
    assert len(data["data"]) >= 1


@pytest.mark.anyio
async def test_list_knowledge_bases(async_client):
    """验证知识库列表端点"""
    response = await async_client.get("/api/v1/knowledge-bases")
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert "total" in data


@pytest.mark.anyio
async def test_chat_without_api_key(async_client):
    """验证未配置 API Key 时返回 503"""
    from app.core.config import config
    if not config.is_api_key_set:
        response = await async_client.post("/api/v1/chat/completions", json={
            "model": "deepseek-chat",
            "messages": [{"role": "user", "content": "Hello"}],
        })
        assert response.status_code == 503
