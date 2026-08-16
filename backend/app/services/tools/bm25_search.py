"""BM25 关键词检索工具"""
import logging

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

    # v4.0: 使用纯 BM25 检索（而非混合检索），与工具名称保持一致
    try:
        # #46: 按 kb_id 隔离，只检索当前知识库的块
        raw_results = hybrid_search_service.bm25_index.search(keywords, top_k=top_k, kb_id=kb_id)
        # 补充文本内容
        results = []
        for doc_id, score in raw_results:
            data = hybrid_search_service._all_chunks_cache.get(doc_id, {})
            results.append({
                "chunk_id": doc_id,
                "text": data.get("text", ""),
                "score": score,
                "source": "bm25",
            })
    except Exception as e:
        logger.warning(f"BM25检索失败: {e}")
        return f"BM25 检索出错: {e}"

    if not results:
        return f"未找到包含关键词「{keywords}」的文档片段。"

    lines = [f"BM25关键词检索「{keywords}」返回 {len(results)} 个结果:"]
    for i, r in enumerate(results, 1):
        text = (r.get("text", "") or "")[:300]
        score = r.get("score", 0)
        lines.append(f"\n[{i}] BM25 相关性={score:.3f}\n{text}")
    return "\n".join(lines)
