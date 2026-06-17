"""
RAG 编排服务 - 串联 chunk → embed → hybrid search → rerank → build context
"""
import logging
from typing import List, Optional
from app.services.chunking_service import SemanticChunker, Chunk
from app.services.embedding_service import EmbeddingService
from app.services.hybrid_search import HybridSearchService, SearchResult
from app.services.reranker_service import RerankerService
from app.core.config import config

logger = logging.getLogger(__name__)

# 全局服务实例
_chunker = SemanticChunker(
    parent_chunk_size=config.PARENT_CHUNK_SIZE,
    child_chunk_size=config.CHILD_CHUNK_SIZE,
    chunk_overlap=config.CHUNK_OVERLAP,
    strategy="parent_child",
)
_hybrid_search = HybridSearchService()


class RAGService:
    """
    RAG 检索增强生成编排服务。
    完整流程：文档 → 分块 → 嵌入 → 混合索引 → 查询检索 → 重排序 → 构建上下文
    """

    @classmethod
    async def index_document(cls, doc_id: str, text: str) -> dict:
        """
        对文档进行完整索引：
        1. 分块（父子块架构）
        2. 生成 Embedding（仅子块）
        3. 写入 LanceDB（子块向量 + 父块文本）
        4. 构建 BM25 索引

        Returns:
            {"chunk_count": N, "parent_count": M, "child_count": K}
        """
        # 1. 分块
        chunks = _chunker.chunk(text, doc_id)
        child_chunks = [c for c in chunks if c.chunk_level == "child"]
        parent_chunks = [c for c in chunks if c.chunk_level == "parent"]

        logger.info(f"文档 {doc_id}: {len(parent_chunks)} 父块, {len(child_chunks)} 子块")

        # 2. 仅对子块生成 Embedding
        child_texts = [c.text for c in child_chunks]
        embeddings = EmbeddingService.encode(child_texts)

        # 3. 写入混合检索引擎
        chunk_dicts = [c.to_dict() for c in child_chunks]
        _hybrid_search.index_document(chunk_dicts, embeddings)

        return {
            "chunk_count": len(chunks),
            "parent_count": len(parent_chunks),
            "child_count": len(child_chunks),
        }

    @classmethod
    def search(
        cls,
        query: str,
        top_k: int = None,
        use_rerank: bool = True,
    ) -> List[SearchResult]:
        """
        查询检索：
        1. 对 query 生成 Embedding
        2. 混合检索（向量 + BM25 → RRF 融合）
        3. 重排序（可选）
        4. 返回结果（含父块上下文）

        Args:
            query: 查询文本
            top_k: 返回数量
            use_rerank: 是否启用重排序

        Returns:
            排序后的检索结果列表
        """
        if top_k is None:
            top_k = config.HYBRID_SEARCH_TOP_K

        # 1. 生成查询向量
        query_vector = EmbeddingService.encode_single(query)

        # 2. 混合检索
        results = _hybrid_search.search(query, query_vector, top_k=top_k * 2)

        # 3. 重排序
        if use_rerank and len(results) > top_k:
            rerank_input = [
                {"text": r.text, "score": r.score, "chunk_id": r.chunk_id,
                 "parent_text": r.parent_text, "source": r.source}
                for r in results
            ]
            reranked = RerankerService.rerank(query, rerank_input, top_k=top_k)

            # 重建 SearchResult
            results = []
            for item in reranked:
                results.append(SearchResult(
                    chunk_id=item["chunk_id"],
                    text=item["text"],
                    score=item.get("rerank_score", item.get("score", 0)),
                    parent_text=item.get("parent_text"),
                    source=item.get("source", ""),
                ))

        return results[:top_k]

    @classmethod
    def build_context(cls, results: List[SearchResult], max_tokens: int = 3000) -> str:
        """
        将检索结果构建为 LLM 上下文文本。
        优先使用父块（完整上下文），回退到子块。

        Args:
            results: 检索结果列表
            max_tokens: 上下文最大 token 数

        Returns:
            构建好的上下文字符串
        """
        from app.utils.helpers import count_tokens_approximate

        context_parts = []
        token_count = 0
        seen_texts = set()

        for i, result in enumerate(results):
            # 优先使用父块文本
            text = result.parent_text if result.parent_text else result.text
            if text in seen_texts:
                continue

            tokens = count_tokens_approximate(text)
            if token_count + tokens > max_tokens:
                break

            context_parts.append(f"### 知识片段 {i + 1} (相关性: {result.score:.2f})\n{text}\n")
            token_count += tokens
            seen_texts.add(text)

        return "\n".join(context_parts)
