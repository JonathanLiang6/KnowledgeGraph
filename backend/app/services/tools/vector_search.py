"""向量检索工具"""
import logging
from typing import List
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


async def vector_search(
    db: AsyncSession,
    kb_id: str,
    query: str,
    top_k: int = 5,
) -> str:
    """
    语义向量检索 — 在知识库中查找与查询语义相似的文档片段。

    Args:
        db: 数据库会话
        kb_id: 知识库ID
        query: 搜索查询文本
        top_k: 返回结果数

    Returns:
        格式化的检索结果文本
    """
    from app.services.rag_service import RAGService

    try:
        results = await RAGService.search_async(
            query=query,
            kb_id=kb_id,
            db=db,
            top_k=top_k,
            use_rerank=True,
        )
    except Exception as e:
        logger.warning(f"向量检索失败: {e}")
        return f"向量检索出错: {e}"

    if not results:
        return "未找到相关的文档片段。"

    lines = [f"向量检索「{query}」返回 {len(results)} 个结果:"]
    for i, r in enumerate(results, 1):
        text = (r.parent_text or r.text or "")[:300]
        score = r.score
        lines.append(f"\n[{i}] 相关性={score:.3f}\n{text}")
    return "\n".join(lines)
