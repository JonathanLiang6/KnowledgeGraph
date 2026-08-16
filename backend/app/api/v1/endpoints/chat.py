"""
智能问答 API - 多模式问答 + SSE 流式输出 + Agentic RAG (Phase 2)
"""
import asyncio
import json
import logging
import time
import uuid
from datetime import UTC
from typing import AsyncGenerator

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import config
from app.core.database import get_db
from app.models.chat_conversation import ChatConversation, ChatMessage
from app.models.document import Document, DocumentStatus
from app.models.knowledge_base import KnowledgeBase
from app.schemas.chat import (
    ChatMessageOut,
    ChatRequest,
    ChatResponse,
    ChatResponseChoice,
    ChatUsage,
    ConversationCreate,
    ConversationDetail,
    ConversationListResponse,
    ConversationOut,
    ConversationUpdate,
    Message,
)
from app.services.char_stream import char_stream
from app.services.deepseek_client import DeepSeekClient

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/chat", tags=["智能问答"])


# 可用的搜索模式 (v3.2: 简化为两种核心模式 + Agent)
SEARCH_MODES = {
    "rag-hybrid": "RAG 混合检索（向量+BM25+重排序）— 知识库问答推荐模式",
    "rag-agent": "Agentic RAG — 多步推理 + 工具调用（图谱遍历+混合检索）",
}


@router.get("/models")
async def list_models():
    """列出可用的问答模型/模式"""
    return {
        "object": "list",
        "data": [
            {"id": mode, "object": "model", "description": desc}
            for mode, desc in SEARCH_MODES.items()
        ],
    }


# v4.1 (#83): 改为 POST — 清除记忆是有副作用的操作，不应由 GET（可被预取/爬虫误触发）执行
@router.post("/agent/clear")
async def clear_agent_memory(
    kb_id: str = Query("__global__", description="知识库ID（v3.2: kb_id 隔离）"),
    session_id: str = Query("default", description="会话ID"),
):
    """清除 Agent 会话记忆（v3.2: kb_id 隔离）"""
    from app.services.agent_service import ReActAgent
    await ReActAgent.clear_session(kb_id, session_id)
    return {"status": "ok", "message": f"会话 {session_id} (kb={kb_id}) 的记忆已清除"}


@router.post("/completions")
async def chat_completions(
    request: ChatRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    问答接口（OpenAI 兼容格式）。
    支持流式 (stream=True) 和非流式两种模式。
    Phase 2: + rag-agent 模式
    """
    if not config.is_api_key_set:
        raise HTTPException(status_code=503, detail="DeepSeek API 未配置")

    chat_id = f"chatcmpl-{uuid.uuid4().hex[:12]}"

    # v4.2: 对话持久化 — 请求进入即落库用户消息（流式生成器运行时请求会话已关闭，
    # 持久化统一走独立会话；助手消息在流/响应完成后落库）
    if request.conversation_id:
        user_query = _get_user_query(request.messages)
        if user_query:
            await _persist_user_message(request.conversation_id, user_query)

    # v3.2: Agent 模式（支持联网搜索开关）
    if request.model == "rag-agent" and request.kb_id:
        enable_web = getattr(request, 'enable_web', False)
        if request.stream:
            return StreamingResponse(
                _stream_agent_response(chat_id, request),
                media_type="text/event-stream",
                headers={
                    "Cache-Control": "no-cache",
                    "Connection": "keep-alive",
                    "X-Accel-Buffering": "no",
                },
            )
        else:
            # 非流式 Agent
            from app.services.agent_service import ReActAgent
            agent = ReActAgent(
                db, request.kb_id,
                getattr(request, 'session_id', 'default'),
                enable_web=enable_web,
            )
            user_query = _get_user_query(request.messages)
            full_answer = ""
            agent_error = None
            async for event in agent.run(user_query):
                if event["type"] == "agent/answer":
                    full_answer = event["content"]
                elif event["type"] == "agent/error":
                    agent_error = event.get("content", "")
            # v4.1 (#82): Agent/LLM 失败时返回 502，而非 200 空答案
            if not full_answer:
                logger.error(f"非流式 Agent 未产生回答: kb_id={request.kb_id}, error={agent_error}")
                raise HTTPException(status_code=502, detail="Agent 推理失败，请稍后重试")
            if request.conversation_id:
                await _persist_assistant_message(request.conversation_id, full_answer)

            return ChatResponse(
                id=chat_id,
                created=int(time.time()),
                model=request.model,
                choices=[
                    ChatResponseChoice(
                        index=0,
                        message=Message(role="assistant", content=full_answer),
                        finish_reason="stop",
                    )
                ],
                usage=ChatUsage(),
            )

    # v3.2: 简化模式 — rag-hybrid 检索知识库，否则直接对话
    if request.model == "rag-hybrid" and request.kb_id:
        messages = await _build_rag_messages(
            request.messages, request.kb_id, request.model, db
        )
    else:
        messages = [m.model_dump() for m in request.messages]

    if request.stream:
        return StreamingResponse(
            _stream_response(chat_id, request.model, messages,
                           request.temperature, request.max_tokens,
                           conversation_id=request.conversation_id),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
            },
        )
    else:
        # v4.1 (#82): LLM 调用失败返回 502 并记录异常详情，而非抛出未处理异常
        try:
            result = await DeepSeekClient.chat(
                messages=messages,
                temperature=request.temperature,
                max_tokens=request.max_tokens,
            )
        except Exception as e:
            logger.exception("非流式 LLM 调用失败")
            raise HTTPException(status_code=502, detail="LLM 服务调用失败，请稍后重试") from e

        if request.conversation_id:
            await _persist_assistant_message(request.conversation_id, result["content"])

        return ChatResponse(
            id=chat_id,
            created=int(time.time()),
            model=request.model,
            choices=[
                ChatResponseChoice(
                    index=0,
                    message=Message(role="assistant", content=result["content"]),
                    finish_reason=result.get("finish_reason", "stop"),
                )
            ],
            usage=ChatUsage(**result.get("usage", {})),
        )


async def _stream_response(chat_id: str, model: str, messages: list[dict],
                         temperature: float = None, max_tokens: int = None,
                         conversation_id: str = None):
    """SSE 流式响应生成器 (v4.2: conversation_id 提供时流结束落库助手消息)"""
    full_content = ""
    try:
        # 发送首帧
        yield f"data: {json.dumps({'id': chat_id, 'object': 'chat.completion.chunk', 'created': int(time.time()), 'model': model, 'choices': [{'index': 0, 'delta': {'role': 'assistant'}, 'finish_reason': None}]})}\n\n"

        # 流式生成内容 — 逐字符分类推送（打字机效果）
        async for char_item in char_stream(
            DeepSeekClient.chat_stream(
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
            )
        ):
            full_content += char_item["char"]
            yield f"data: {json.dumps({'id': chat_id, 'object': 'chat.completion.chunk', 'created': int(time.time()), 'model': model, 'choices': [{'index': 0, 'delta': {'content': char_item['char'], 'char_type': char_item['type']}, 'finish_reason': None}]})}\n\n"

        # 发送结束帧
        yield f"data: {json.dumps({'id': chat_id, 'object': 'chat.completion.chunk', 'created': int(time.time()), 'model': model, 'choices': [{'index': 0, 'delta': {}, 'finish_reason': 'stop'}]})}\n\n"
        yield "data: [DONE]\n\n"

    except Exception:
        # v4.1 (#83): 不向客户端泄露异常原文，详情记录到服务端日志
        logger.exception("流式响应错误")
        yield f"data: {json.dumps({'error': '服务处理异常，请稍后重试'})}\n\n"
        yield "data: [DONE]\n\n"

    # v4.2: 已产出内容则落库（中途失败也保留部分回答）
    if conversation_id and full_content:
        await _persist_assistant_message(conversation_id, full_content)


def _get_user_query(messages: list[Message]) -> str:
    """从消息列表中提取最后的用户消息"""
    for msg in reversed(messages):
        if msg.role == "user":
            return msg.content
    return ""


async def _stream_agent_response(
    chat_id: str,
    request: ChatRequest,
) -> AsyncGenerator[str, None]:
    """
    SSE 流式 Agent 响应生成器 (Phase 2)。

    发送 Agent 推理事件:
    - agent/thought: Agent 的思考过程
    - agent/action: 工具调用
    - agent/observation: 工具返回结果
    - agent/answer: 最终答案
    - agent/error: 错误信息
    """
    from app.core.database import async_session_factory
    from app.services.agent_service import ReActAgent

    user_query = _get_user_query(request.messages)
    session_id = getattr(request, 'session_id', 'default')
    enable_web = getattr(request, 'enable_web', False)

    # v4.2: 收集推理步骤与最终答案，流结束后落库
    reasoning_steps: list[dict] = []
    final_answer = ""

    try:
        async with async_session_factory() as db:
            agent = ReActAgent(db, request.kb_id, session_id, enable_web=enable_web)

            async for event in agent.run(user_query):
                event_type = event.get("type", "")

                if event_type in ("agent/thought", "agent/action", "agent/observation", "agent/error"):
                    reasoning_steps.append(event)

                if event_type == "agent/answer":
                    # 最终答案 — 使用打字机效果逐字符推送
                    answer = event.get("content", "")
                    final_answer = answer
                    async for char_item in char_stream(_char_by_char(answer)):
                        chunk = {
                            "id": chat_id,
                            "object": "agent.chunk",
                            "created": int(time.time()),
                            "model": request.model,
                            "choices": [{
                                "index": 0,
                                "delta": {
                                    "content": char_item["char"],
                                    "char_type": char_item["type"],
                                },
                                "finish_reason": None,
                            }],
                        }
                        yield f"data: {json.dumps(chunk)}\n\n"
                elif event_type in ("agent/thought", "agent/action", "agent/observation", "agent/error"):
                    # Agent 推理事件 — 作为特殊事件推送
                    agent_event = {
                        "id": chat_id,
                        "object": "agent.event",
                        "created": int(time.time()),
                        "model": request.model,
                        "event": event,
                    }
                    yield f"data: {json.dumps(agent_event)}\n\n"

        # 发送结束帧
        done_chunk = {
            "id": chat_id,
            "object": "chat.completion.chunk",
            "created": int(time.time()),
            "model": request.model,
            "choices": [{"index": 0, "delta": {}, "finish_reason": "stop"}],
        }
        yield f"data: {json.dumps(done_chunk)}\n\n"
        yield "data: [DONE]\n\n"

    except Exception:
        # v4.1 (#83): 不向客户端泄露异常原文，详情记录到服务端日志
        logger.exception("Agent SSE 响应错误")
        yield f"data: {json.dumps({'error': '服务处理异常，请稍后重试'})}\n\n"
        yield "data: [DONE]\n\n"

    # v4.2: Agent 回答与推理步骤落库
    if request.conversation_id and final_answer:
        await _persist_assistant_message(
            request.conversation_id, final_answer,
            reasoning_steps=reasoning_steps or None,
        )


async def _char_by_char(text: str):
    """将文本逐字符 yield（v4.0: 添加 asyncio.sleep(0) 让出事件循环）"""
    for char in text:
        yield char
        await asyncio.sleep(0)  # 让出事件循环，避免阻塞其他协程


async def _build_rag_messages(
    messages: list[Message],
    kb_id: str,
    model: str,
    db: AsyncSession,
) -> list[dict]:
    """
    构建 RAG 增强的消息列表 (v2.3: 实现真正的混合检索上下文)。

    根据 model 选择检索策略：
    - rag-local: 仅向量检索
    - rag-hybrid: 向量 + BM25 + 重排序
    """
    # 获取最后的用户消息
    user_query = ""
    for msg in reversed(messages):
        if msg.role == "user":
            user_query = msg.content
            break

    if not user_query:
        return [m.model_dump() for m in messages]

    # v2.3: 执行真正的混合检索
    context_text = ""
    try:
        from app.services.rag_service import RAGService

        use_rerank = (model == "rag-hybrid")
        search_results = await RAGService.search_async(
            query=user_query,
            kb_id=kb_id,
            db=db,
            top_k=config.HYBRID_SEARCH_TOP_K,
            use_rerank=use_rerank,
        )

        if search_results:
            context_text = RAGService.build_context(
                search_results,
                max_tokens=3000,  # v2.4: 默认上下文 token 上限
                max_sources=config.CONTEXT_MAX_SOURCES,
            )
            logger.info(
                f"RAG 检索完成: query={user_query[:50]}..., "
                f"results={len(search_results)}"
            )
        else:
            # 回退: 查找知识库文档元数据
            result = await db.execute(
                select(Document).where(
                    Document.kb_id == kb_id,
                    Document.status == DocumentStatus.DONE,
                )
            )
            docs = result.scalars().all()
            if docs:
                parts = ["## 知识库相关内容 (文档摘要)\n"]
                for doc in docs[:3]:
                    parts.append(
                        f"### 来自文档《{doc.filename}》\n"
                        f"(文档包含 {doc.chunk_count} 个知识块，{doc.entity_count} 个实体)\n"
                    )
                context_text = "\n".join(parts)

    except Exception as e:
        logger.warning(f"RAG 检索失败, 回退到纯对话模式: {e}")
        context_text = ""

    # 构建 system prompt
    if context_text:
        system_msg = {
            "role": "system",
            "content": (
                "你是教学知识库问答助手。请基于以下知识库内容回答用户问题。\n\n"
                f"{context_text}\n\n"
                "要求：\n"
                "1. 回答基于提供的知识内容，如果知识库中没有相关信息，请诚实说明\n"
                "2. 引用来源时标注文档名\n"
                "3. 回答简洁准确，适合教学场景\n"
                "4. 对于复杂概念，给出逐步解释"
            ),
        }
        return [system_msg] + [m.model_dump() for m in messages]
    else:
        return [m.model_dump() for m in messages]


# ═══════════════════════════════════════════════════════════
# v4.2: 对话管理（网页聊天应用式会话持久化）
# ═══════════════════════════════════════════════════════════

_MAX_PERSIST_CONTENT = 100000


async def _persist_user_message(conversation_id: str, content: str) -> None:
    """落库用户消息 + 自动命名（默认标题时取首条消息前 24 字）。

    使用独立会话：流式生成器运行期间请求级会话已归还。
    """
    from app.core.database import async_session_factory

    try:
        async with async_session_factory() as db:
            result = await db.execute(
                select(ChatConversation).where(ChatConversation.id == conversation_id)
            )
            conv = result.scalar_one_or_none()
            if not conv:
                logger.warning(f"持久化跳过：对话不存在 {conversation_id}")
                return
            db.add(ChatMessage(
                conversation_id=conversation_id,
                role="user",
                content=content[:_MAX_PERSIST_CONTENT],
            ))
            if conv.title == "新对话" and content.strip():
                conv.title = content.strip().replace("\n", " ")[:24]
            await db.commit()
    except Exception:
        logger.exception(f"用户消息落库失败 conversation={conversation_id}")


async def _persist_assistant_message(
    conversation_id: str, content: str, reasoning_steps: list | None = None
) -> None:
    """落库助手消息（含 Agent 推理步骤），并刷新对话活跃时间。"""
    from app.core.database import async_session_factory

    if not content:
        return
    try:
        async with async_session_factory() as db:
            db.add(ChatMessage(
                conversation_id=conversation_id,
                role="assistant",
                content=content[:_MAX_PERSIST_CONTENT],
                reasoning_steps=reasoning_steps,
            ))
            result = await db.execute(
                select(ChatConversation.updated_at).where(
                    ChatConversation.id == conversation_id
                )
            )
            if result.one_or_none() is None:
                logger.warning(f"持久化跳过：对话不存在 {conversation_id}")
                await db.rollback()
                return
            # 触发 onupdate 刷新活跃时间
            await db.execute(
                ChatConversation.__table__.update()
                .where(ChatConversation.id == conversation_id)
                .values(updated_at=func.now())
            )
            await db.commit()
    except Exception:
        logger.exception(f"助手消息落库失败 conversation={conversation_id}")


def _as_utc(dt):
    """SQLite CURRENT_TIMESTAMP 存 UTC 但无时区标注 — 补上 UTC 使前端
    new Date() 解析正确（否则被当本地时间，显示偏差数小时）。"""
    if dt is not None and dt.tzinfo is None:
        return dt.replace(tzinfo=UTC)
    return dt


def _conversation_out(conv: ChatConversation) -> ConversationOut:
    return ConversationOut(
        id=conv.id,
        kb_id=conv.kb_id,
        title=conv.title,
        message_count=len(conv.messages),
        created_at=_as_utc(conv.created_at),
        updated_at=_as_utc(conv.updated_at),
    )


@router.get("/conversations", response_model=ConversationListResponse)
async def list_conversations(
    kb_id: str = Query(..., description="知识库ID"),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """列出知识库下的对话（按最后活跃倒序）"""
    conditions = [ChatConversation.kb_id == kb_id]
    total = (
        await db.execute(
            select(func.count(ChatConversation.id)).where(*conditions)
        )
    ).scalar() or 0

    result = await db.execute(
        select(ChatConversation)
        .where(*conditions)
        .order_by(ChatConversation.updated_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    items = [_conversation_out(c) for c in result.scalars().all()]
    return ConversationListResponse(items=items, total=total)


@router.post("/conversations", response_model=ConversationOut, status_code=201)
async def create_conversation(
    data: ConversationCreate,
    db: AsyncSession = Depends(get_db),
):
    """创建新对话"""
    kb = (
        await db.execute(select(KnowledgeBase).where(KnowledgeBase.id == data.kb_id))
    ).scalar_one_or_none()
    if not kb:
        raise HTTPException(status_code=404, detail="知识库不存在")

    conv = ChatConversation(kb_id=data.kb_id, title=data.title)
    db.add(conv)
    await db.flush()
    await db.refresh(conv)
    return _conversation_out(conv)


@router.get("/conversations/{conversation_id}", response_model=ConversationDetail)
async def get_conversation(
    conversation_id: str,
    db: AsyncSession = Depends(get_db),
):
    """获取对话详情（含全部消息）"""
    result = await db.execute(
        select(ChatConversation).where(ChatConversation.id == conversation_id)
    )
    conv = result.scalar_one_or_none()
    if not conv:
        raise HTTPException(status_code=404, detail="对话不存在")
    detail = ConversationDetail(
        id=conv.id,
        kb_id=conv.kb_id,
        title=conv.title,
        message_count=len(conv.messages),
        created_at=_as_utc(conv.created_at),
        updated_at=_as_utc(conv.updated_at),
        messages=[
            ChatMessageOut(
                id=m.id,
                role=m.role,
                content=m.content,
                reasoning_steps=m.reasoning_steps,
                created_at=_as_utc(m.created_at),
            )
            for m in conv.messages
        ],
    )
    return detail


@router.patch("/conversations/{conversation_id}", response_model=ConversationOut)
async def rename_conversation(
    conversation_id: str,
    data: ConversationUpdate,
    db: AsyncSession = Depends(get_db),
):
    """重命名对话"""
    result = await db.execute(
        select(ChatConversation).where(ChatConversation.id == conversation_id)
    )
    conv = result.scalar_one_or_none()
    if not conv:
        raise HTTPException(status_code=404, detail="对话不存在")

    conv.title = data.title.strip()
    await db.flush()
    await db.refresh(conv)
    return _conversation_out(conv)


@router.delete("/conversations/{conversation_id}")
async def delete_conversation(
    conversation_id: str,
    confirm: bool = Query(default=False, description="必须传 confirm=true 执行不可逆删除"),
    db: AsyncSession = Depends(get_db),
):
    """删除对话及其全部消息（不可逆）"""
    if not confirm:
        raise HTTPException(
            status_code=400,
            detail="删除操作不可逆：请显式传递 confirm=true 以确认删除",
        )
    result = await db.execute(
        select(ChatConversation).where(ChatConversation.id == conversation_id)
    )
    conv = result.scalar_one_or_none()
    if not conv:
        raise HTTPException(status_code=404, detail="对话不存在")

    title = conv.title
    await db.delete(conv)
    await db.flush()
    return {"message": f"对话 '{title}' 已删除", "id": conversation_id}
