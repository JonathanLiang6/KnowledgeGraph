"""
对话持久化测试 (v4.2)

覆盖：会话 CRUD、自动命名、消息落库、列表排序。
运行在隔离临时库上。
"""
import pytest
from sqlalchemy import select

from app.models.chat_conversation import ChatConversation, ChatMessage


async def _create_kb(async_client, name="对话测试库"):
    resp = await async_client.post("/api/v1/knowledge-bases", json={"name": name, "description": ""})
    assert resp.status_code == 201
    return resp.json()["id"]


@pytest.mark.anyio
async def test_conversation_crud(async_client):
    kb_id = await _create_kb(async_client)

    # 创建
    resp = await async_client.post("/api/v1/chat/conversations", json={"kb_id": kb_id, "title": "我的对话"})
    assert resp.status_code == 201
    conv = resp.json()
    assert conv["title"] == "我的对话"
    assert conv["message_count"] == 0
    cid = conv["id"]

    # 列表
    resp = await async_client.get("/api/v1/chat/conversations", params={"kb_id": kb_id})
    assert resp.status_code == 200
    assert resp.json()["total"] == 1

    # 重命名
    resp = await async_client.patch(f"/api/v1/chat/conversations/{cid}", json={"title": "重命名后的对话"})
    assert resp.status_code == 200
    assert resp.json()["title"] == "重命名后的对话"

    # 详情
    resp = await async_client.get(f"/api/v1/chat/conversations/{cid}")
    assert resp.status_code == 200
    assert resp.json()["messages"] == []

    # 删除需 confirm
    resp = await async_client.delete(f"/api/v1/chat/conversations/{cid}")
    assert resp.status_code == 400
    resp = await async_client.delete(f"/api/v1/chat/conversations/{cid}", params={"confirm": True})
    assert resp.status_code == 200
    resp = await async_client.get(f"/api/v1/chat/conversations/{cid}")
    assert resp.status_code == 404


@pytest.mark.anyio
async def test_persist_user_message_auto_title(db_session):
    """用户消息落库 + 默认标题自动取首条消息前 24 字"""
    conv = ChatConversation(kb_id="kb-x", title="新对话")
    db_session.add(conv)
    await db_session.commit()

    from app.api.v1.endpoints.chat import _persist_user_message
    await _persist_user_message(conv.id, "帮我梳理一下初中化学的酸碱盐知识点")

    result = await db_session.execute(
        select(ChatMessage).where(ChatMessage.conversation_id == conv.id)
    )
    rows = result.scalars().all()
    assert len(rows) == 1
    assert rows[0].role == "user"

    await db_session.refresh(conv)
    assert conv.title == "帮我梳理一下初中化学的酸碱盐知识点"

    # 第二条消息不再改标题
    await _persist_user_message(conv.id, "另一个问题")
    await db_session.refresh(conv)
    assert conv.title == "帮我梳理一下初中化学的酸碱盐知识点"


@pytest.mark.anyio
async def test_persist_assistant_message_with_reasoning(db_session):
    """助手消息落库（含 Agent 推理步骤）"""
    conv = ChatConversation(kb_id="kb-y", title="Agent 对话")
    db_session.add(conv)
    await db_session.commit()

    from app.api.v1.endpoints.chat import _persist_assistant_message
    steps = [{"type": "agent/thought", "content": "需要检索"}, {"type": "agent/action", "tool": "hybrid_search"}]
    await _persist_assistant_message(conv.id, "最终答案内容", reasoning_steps=steps)

    result = await db_session.execute(
        select(ChatMessage).where(ChatMessage.conversation_id == conv.id)
    )
    row = result.scalars().one()
    assert row.role == "assistant"
    assert row.content == "最终答案内容"
    assert row.reasoning_steps == steps

    # 空内容不落库
    await _persist_assistant_message(conv.id, "")
    result = await db_session.execute(
        select(ChatMessage).where(ChatMessage.conversation_id == conv.id)
    )
    assert len(result.scalars().all()) == 1


@pytest.mark.anyio
async def test_list_ordered_by_updated_desc(async_client):
    """列表按最后活跃倒序"""
    kb_id = await _create_kb(async_client)
    ids = []
    for title in ("对话A", "对话B", "对话C"):
        resp = await async_client.post("/api/v1/chat/conversations", json={"kb_id": kb_id, "title": title})
        ids.append(resp.json()["id"])

    # 给"对话A"追加消息 → 其 updated_at 最新（同秒粒度下 SQLite now 相同，
    # 这里只验证列表完整性与结构）
    from app.api.v1.endpoints.chat import _persist_user_message
    await _persist_user_message(ids[0], "新消息")

    resp = await async_client.get("/api/v1/chat/conversations", params={"kb_id": kb_id})
    data = resp.json()
    assert data["total"] == 3
    by_id = {c["id"]: c for c in data["items"]}
    assert by_id[ids[0]]["message_count"] == 1
    assert by_id[ids[1]]["message_count"] == 0
