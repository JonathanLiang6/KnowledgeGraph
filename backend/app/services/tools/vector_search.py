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
    from app.services.hybrid_search import hybrid_search_service
    from app.services.embedding_service import EmbeddingService

    # v4.0: 使用纯向量检索（不经过 GraphRAG 增强，让 Agent 自行决定是否调用图遍历）
    try:
        query_vector = EmbeddingService.encode_single(query)
        # #46: 按 kb_id 隔离，只检索当前知识库的块
        raw_results = hybrid_search_service.vector_store.search(query_vector, top_k=top_k, kb_id=kb_id)
        # 转换为 SearchResult 格式
        results = []
        for r in raw_results:
            distance = r.get("_distance", 0.0)
            similarity = 1.0 / (1.0 + distance)
            data = hybrid_search_service._all_chunks_cache.get(r.get("id", ""), {})
            results.append({
                "chunk_id": r.get("id", ""),
                "text": data.get("text", r.get("text", "")),
                "score": similarity,
                "source": "vector",
            })
    except Exception as e:
        logger.warning(f"向量检索失败: {e}")
        return f"向量检索出错: {e}"

    if not results:
        return "未找到相关的文档片段。"

    lines = [f"向量检索「{query}」返回 {len(results)} 个结果:"]
    for i, r in enumerate(results, 1):
        text = (r.get("text", "") or "")[:300]
        score = r.get("score", 0)
        lines.append(f"\n[{i}] 相似度={score:.3f}\n{text}")
    return "\n".join(lines)
