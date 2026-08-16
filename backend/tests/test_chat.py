"""测试智能问答端点"""
import pytest


@pytest.mark.anyio
async def test_chat_models(async_client):
    """获取可用的聊天模型列表"""
    response = await async_client.get("/api/v1/chat/models")
    assert response.status_code == 200
    data = response.json()
    assert "data" in data
    assert isinstance(data["data"], list)
    assert len(data["data"]) > 0


@pytest.mark.anyio
async def test_completion_without_kb(async_client):
    """无知识库的纯 LLM 对话"""
    response = await async_client.post("/api/v1/chat/completions", json={
        "model": "deepseek-chat",
        "messages": [{"role": "user", "content": "你好"}],
        "stream": False,
    })
    # 可能成功或返回 503（API 密钥未配置）
    assert response.status_code in (200, 503)


@pytest.mark.anyio
async def test_chat_completion_with_kb(async_client):
    """RAG 混合检索模式请求"""
    response = await async_client.post("/api/v1/chat/completions", json={
        "model": "rag-hybrid",
        "messages": [{"role": "user", "content": "测试查询"}],
        "stream": False,
    })
    # 可能成功或返回 503
    assert response.status_code in (200, 503)


@pytest.mark.anyio
async def test_agent_clear_memory(async_client):
    """清除 Agent 会话记忆（v4.1 #83: 改为 POST）"""
    response = await async_client.post("/api/v1/chat/agent/clear?session_id=test-session-123")
    assert response.status_code == 200
    data = response.json()
    assert data.get("status") == "ok"
