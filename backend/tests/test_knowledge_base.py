"""测试知识库 CRUD 端点"""
import pytest
import uuid


@pytest.mark.anyio
async def test_list_knowledge_bases(async_client):
    """列出知识库"""
    response = await async_client.get("/api/v1/knowledge-bases")
    assert response.status_code == 200
    data = response.json()
    assert "items" in data


@pytest.mark.anyio
async def test_create_knowledge_base(async_client):
    """创建知识库"""
    name = f"测试知识库-{uuid.uuid4().hex[:6]}"
    response = await async_client.post("/api/v1/knowledge-bases", json={
        "name": name,
        "description": "自动化测试知识库",
    })
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == name
    assert data["id"] is not None


@pytest.mark.anyio
async def test_create_knowledge_base_empty_name(async_client):
    """空名称创建应失败"""
    response = await async_client.post("/api/v1/knowledge-bases", json={
        "name": "",
        "description": "",
    })
    assert response.status_code == 422  # Pydantic validation


@pytest.mark.anyio
async def test_knowledge_base_not_found(async_client):
    """不存在的知识库应返回 404"""
    fake_id = str(uuid.uuid4())
    response = await async_client.get(f"/api/v1/knowledge-bases/{fake_id}")
    assert response.status_code == 404
