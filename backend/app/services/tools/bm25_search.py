"""BM25 关键词检索工具"""
import logging
from typing import List
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


async def bm25_search(
    db: AsyncSession,
    kb_id: str,
    keywords: str,
    top_k: int = 5,
) -> str:
    """
    关键词精确匹配检索 — 在知识库中查找包含特定术语/编号的文档片段。

    Args:
        db: 数据库会话
        kb_id: 知识库ID
        keywords: 关键词（空格分隔）
        top_k: 返回结果数

    Returns:
        格式化的检索结果文本
    """
    from app.services.hybrid_search import hybrid_search_service
    from app.services.embedding_service import EmbeddingService

    try:
        query_vector = EmbeddingService.encode_single(keywords)
        results = hybrid_search_service.search(
            keywords, query_vector, top_k=top_k
        )
    except Exception as e:
        logger.warning(f"BM25检索失败: {e}")
        return f"BM25 检索出错: {e}"

    if not results:
        return f"未找到包含关键词「{keywords}」的文档片段。"

    lines = [f"BM25检索「{keywords}」返回 {len(results)} 个结果:"]
    for i, r in enumerate(results, 1):
        text = (r.text or "")[:300]
        score = r.score
        source = r.source if r.source else "hybrid"
        lines.append(f"\n[{i}] {source} 相关性={score:.3f}\n{text}")
    return "\n".join(lines)
