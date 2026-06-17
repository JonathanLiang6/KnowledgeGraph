"""
智能问答 API - 多模式问答 + SSE 流式输出
"""
import json
import time
import uuid
import logging
from typing import List
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.database import get_db
from app.core.config import config
from app.models.document import Document
from app.models.chat_history import ChatHistory
from app.services.deepseek_client import DeepSeekClient
from app.schemas.chat import (
    ChatRequest,
    ChatResponse,
    ChatResponseChoice,
    ChatUsage,
    Message,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/chat", tags=["智能问答"])


# 可用的搜索模式
SEARCH_MODES = {
    "deepseek-chat": "DeepSeek V4 直接问答",
    "rag-local": "RAG 本地知识库检索",
    "rag-hybrid": "RAG 混合检索（向量+BM25+重排序）",
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


@router.post("/completions")
async def chat_completions(
    request: ChatRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    问答接口（OpenAI 兼容格式）。
    支持流式 (stream=True) 和非流式两种模式。
    """
    if not config.is_api_key_set:
        raise HTTPException(status_code=503, detail="DeepSeek API 未配置")

    chat_id = f"chatcmpl-{uuid.uuid4().hex[:12]}"

    # 根据 model 决定搜索模式
    if request.model in ("rag-local", "rag-hybrid") and request.kb_id:
        # RAG 模式：先检索再回答
        messages = await _build_rag_messages(
            request.messages, request.kb_id, request.model, db
        )
    else:
        # 直接问答模式
        messages = [m.model_dump() for m in request.messages]

    if request.stream:
        return StreamingResponse(
            _stream_response(chat_id, request.model, messages),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
            },
        )
    else:
        # 非流式
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


async def _stream_response(chat_id: str, model: str, messages: List[dict]):
    """SSE 流式响应生成器"""
    try:
        # 发送首帧
        yield f"data: {json.dumps({'id': chat_id, 'object': 'chat.completion.chunk', 'created': int(time.time()), 'model': model, 'choices': [{'index': 0, 'delta': {'role': 'assistant'}, 'finish_reason': None}]})}\n\n"

        # 流式生成内容
        full_content = ""
        async for chunk in DeepSeekClient.chat_stream(messages=messages):
            full_content += chunk
            yield f"data: {json.dumps({'id': chat_id, 'object': 'chat.completion.chunk', 'created': int(time.time()), 'model': model, 'choices': [{'index': 0, 'delta': {'content': chunk}, 'finish_reason': None}]})}\n\n"

        # 发送结束帧
        yield f"data: {json.dumps({'id': chat_id, 'object': 'chat.completion.chunk', 'created': int(time.time()), 'model': model, 'choices': [{'index': 0, 'delta': {}, 'finish_reason': 'stop'}]})}\n\n"
        yield "data: [DONE]\n\n"

    except Exception as e:
        logger.error(f"流式响应错误: {e}")
        yield f"data: {json.dumps({'error': str(e)})}\n\n"
        yield "data: [DONE]\n\n"


async def _build_rag_messages(
    messages: List[Message],
    kb_id: str,
    model: str,
    db: AsyncSession,
) -> List[dict]:
    """
    构建 RAG 增强的消息列表。
    根据 model 选择检索策略：
    - rag-local: 仅向量检索
    - rag-hybrid: 向量 + BM25 + 重排序
    （详细实现在 Phase 3 完成，此处为简化版）
    """
    # 获取最后的用户消息
    user_query = ""
    for msg in reversed(messages):
        if msg.role == "user":
            user_query = msg.content
            break

    # 检索相关文档块（简化版，Phase 3 实现完整的混合检索）
    context_parts = []
    try:
        # 查询该知识库下的已处理文档
        result = await db.execute(
            select(Document).where(
                Document.kb_id == kb_id,
                Document.status == "done",
            )
        )
        docs = result.scalars().all()

        if docs:
            context_parts.append("## 知识库相关内容\n")
            for doc in docs[:3]:  # 最多3篇文档
                context_parts.append(f"### 来自文档《{doc.filename}》\n")
                # 这里后续会替换为实际的 chunk 检索结果
                context_parts.append(f"(文档包含 {doc.chunk_count} 个知识块，{doc.entity_count} 个实体)\n")

    except Exception as e:
        logger.warning(f"RAG 检索失败: {e}")

    context = "\n".join(context_parts) if context_parts else ""

    # 构建 system prompt
    system_msg = {
        "role": "system",
        "content": f"""你是教学知识库问答助手。请基于以下知识库内容回答用户问题。

{context}

要求：
1. 回答基于提供的知识内容，如果知识库中没有相关信息，请诚实说明
2. 引用来源时标注文档名
3. 回答简洁准确，适合教学场景
4. 对于复杂概念，给出逐步解释""",
    }

    return [system_msg] + [m.model_dump() for m in messages]
