"""
智能问答 API - 多模式问答 + SSE 流式输出 + Agentic RAG (Phase 2)
"""
import json
import time
import uuid
import logging
from typing import List, AsyncGenerator
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.database import get_db
from app.core.config import config
from app.models.document import Document
from app.services.deepseek_client import DeepSeekClient
from app.services.char_stream import char_stream
from app.schemas.chat import (
    ChatRequest,
    ChatResponse,
    ChatResponseChoice,
    ChatUsage,
    Message,
)

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


@router.get("/agent/clear")
async def clear_agent_memory(
    kb_id: str = Query("__global__", description="知识库ID（v3.2: kb_id 隔离）"),
    session_id: str = Query("default", description="会话ID"),
):
    """清除 Agent 会话记忆（v3.2: kb_id 隔离）"""
    from app.services.agent_service import ReActAgent
    ReActAgent.clear_session(kb_id, session_id)
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
            async for event in agent.run(user_query):
                if event["type"] == "agent/answer":
                    full_answer = event["content"]
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
                           request.temperature, request.max_tokens),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
            },
        )
    else:
        result = await DeepSeekClient.chat(
            messages=messages,
            temperature=request.temperature,
            max_tokens=request.max_tokens,
        )

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


async def _stream_response(chat_id: str, model: str, messages: List[dict],
                         temperature: float = None, max_tokens: int = None):
    """SSE 流式响应生成器"""
    try:
        # 发送首帧
        yield f"data: {json.dumps({'id': chat_id, 'object': 'chat.completion.chunk', 'created': int(time.time()), 'model': model, 'choices': [{'index': 0, 'delta': {'role': 'assistant'}, 'finish_reason': None}]})}\n\n"

        # 流式生成内容 — 逐字符分类推送（打字机效果）
        full_content = ""
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

    except Exception as e:
        logger.error(f"流式响应错误: {e}")
        yield f"data: {json.dumps({'error': str(e)})}\n\n"
        yield "data: [DONE]\n\n"


def _get_user_query(messages: List[Message]) -> str:
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
    from app.services.agent_service import ReActAgent
    from app.core.database import async_session_factory

    user_query = _get_user_query(request.messages)
    session_id = getattr(request, 'session_id', 'default')
    enable_web = getattr(request, 'enable_web', False)

    try:
        async with async_session_factory() as db:
            agent = ReActAgent(db, request.kb_id, session_id, enable_web=enable_web)

            async for event in agent.run(user_query):
                event_type = event.get("type", "")

                if event_type == "agent/answer":
                    # 最终答案 — 使用打字机效果逐字符推送
                    answer = event.get("content", "")
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

    except Exception as e:
        logger.error(f"Agent SSE 响应错误: {e}")
        yield f"data: {json.dumps({'error': str(e)})}\n\n"
        yield "data: [DONE]\n\n"


async def _char_by_char(text: str):
    """将文本逐字符 yield（模拟流式输出）"""
    for char in text:
        yield char


async def _build_rag_messages(
    messages: List[Message],
    kb_id: str,
    model: str,
    db: AsyncSession,
) -> List[dict]:
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
                    Document.status == "done",
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
