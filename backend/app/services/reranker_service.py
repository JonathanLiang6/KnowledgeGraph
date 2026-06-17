"""
重排序服务 - 使用 BGE-Reranker (Cross-Encoder) 对检索结果二次打分
"""
import logging
from typing import List
from app.core.config import config

logger = logging.getLogger(__name__)

# 延迟加载
_reranker_model = None


def _get_reranker():
    """懒加载 Cross-Encoder 模型"""
    global _reranker_model
    if _reranker_model is None:
        try:
            from sentence_transformers import CrossEncoder
            logger.info(f"加载本地 Reranker 模型: {config.RERANKER_MODEL}")
            _reranker_model = CrossEncoder(
                config.RERANKER_MODEL,
                device=config.RERANKER_DEVICE,
            )
            logger.info("本地 Reranker 模型加载完成")
        except Exception as e:
            logger.warning(f"本地 Reranker 模型加载失败: {e}")
            _reranker_model = None
    return _reranker_model


class RerankerService:
    """
    重排序服务。
    使用 Cross-Encoder 模型对 (query, chunk) 对进行精确相关性打分。
    """

    @classmethod
    def rerank(
        cls,
        query: str,
        chunks: List[dict],
        top_k: int = None,
    ) -> List[dict]:
        """
        对 chunks 进行重排序

        Args:
            query: 查询文本
            chunks: [{"text": ..., "score": ..., ...}, ...] 候选 chunk 列表
            top_k: 返回 top_k 个结果，默认为 config.RERANK_TOP_K

        Returns:
            重排序后的 chunk 列表，附带 new_score
        """
        if top_k is None:
            top_k = config.RERANK_TOP_K

        if not chunks:
            return []

        model = _get_reranker()

        if model is not None:
            return cls._local_rerank(model, query, chunks, top_k)
        else:
            return cls._fallback_rerank(query, chunks, top_k)

    @classmethod
    def _local_rerank(cls, model, query: str, chunks: List[dict], top_k: int) -> List[dict]:
        """本地 Cross-Encoder 重排序"""
        # 构建 (query, chunk_text) 对
        pairs = [(query, chunk["text"]) for chunk in chunks]

        try:
            scores = model.predict(pairs, show_progress_bar=False)

            # 附加新分数并排序
            for chunk, score in zip(chunks, scores):
                chunk["rerank_score"] = float(score)

            chunks.sort(key=lambda x: x.get("rerank_score", 0), reverse=True)
            logger.info(f"Reranker 完成: {len(chunks)} chunks → top {top_k}")
            return chunks[:top_k]

        except Exception as e:
            logger.error(f"Local Reranker 失败: {e}")
            return cls._fallback_rerank(query, chunks, top_k)

    @classmethod
    def _fallback_rerank(cls, query: str, chunks: List[dict], top_k: int) -> List[dict]:
        """
        回退方案：基于文本相似度的简单重排序
        使用 Jaccard 相似度 + 原始检索分数
        """
        from app.utils.helpers import calculate_similarity

        for chunk in chunks:
            similarity = calculate_similarity(query, chunk.get("text", ""))
            # 结合原始检索分数
            original_score = chunk.get("score", chunk.get("_distance", 0))
            chunk["rerank_score"] = 0.5 * similarity + 0.5 * original_score

        chunks.sort(key=lambda x: x.get("rerank_score", 0), reverse=True)
        logger.info(f"Fallback Reranker: {len(chunks)} chunks → top {top_k}")
        return chunks[:top_k]
