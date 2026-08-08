"""
RAG 编排服务 - 串联 chunk → embed → hybrid search → rerank → build context
v4.0 (Phase 1): GraphRAG 升级 — 使用 GraphRetriever 替代内存索引 + 全局搜索 + 查询路由
"""
import asyncio
import time
import logging
from typing import List, Optional
from cachetools import TTLCache

from sqlalchemy.ext.asyncio import AsyncSession

from app.services.chunking_service import SemanticChunker
from app.services.embedding_service import EmbeddingService
from app.services.hybrid_search import SearchResult, hybrid_search_service, rrf_fusion
from app.services.reranker_service import RerankerService
from app.core.config import config

logger = logging.getLogger(__name__)

# ── 全局服务实例 ─────────────────────────────────────────────
_chunker = SemanticChunker(
    parent_chunk_size=config.PARENT_CHUNK_SIZE,
    child_chunk_size=config.CHILD_CHUNK_SIZE,
    chunk_overlap=config.CHUNK_OVERLAP,
    strategy="parent_child",
)
_hybrid_search = hybrid_search_service

# ── 查询类型分类 ─────────────────────────────────────────────

# 总结类关键词 → global search
_SUMMARY_KEYWORDS = [
    "总结", "概述", "归纳", "全局", "整体", "概览", "有哪些", "所有", "全部",
    "summarize", "overview", "summary", "all",
]
# 事实类关键词 → local search
_FACTUAL_KEYWORDS = [
    "什么是", "如何", "怎样", "为什么", "定义", "解释", "区别", "比较", "对比",
    "异同", "优缺点", "特点", "特征", "关系",
    "what", "how", "why", "define", "explain", "compare", "difference",
]
# 否定前缀 — 以此开头的短句不应触发摘要路由
_NEGATION_PREFIXES = ["不要", "别", "禁止", "不能", "不应该", "不需要"]


def classify_query_type(query: str) -> str:
    """
    将查询分类为 'factual'（局部检索）或 'summary'（全局检索）。

    - summary: 总结、概述、全局性问题 → global_search (社区摘要)
    - factual: 具体事实、定义、关系查询 → local_search (混合检索+图检索)
    """
    q_stripped = query.strip()
    q_lower = q_stripped.lower()
    # 否定检测：如果以否定前缀开头，不作为摘要类
    has_negation = any(q_stripped.startswith(p) for p in _NEGATION_PREFIXES)
    if not has_negation:
        for kw in _SUMMARY_KEYWORDS:
            if kw in q_lower:
                return "summary"
    for kw in _FACTUAL_KEYWORDS:
        if kw in q_lower:
            return "factual"
    # v4.0: 默认一律使用 factual（局部检索），避免误分类
    return "factual"


# ── LRU 检索缓存（使用 cachetools.TTLCache）────────────────
# v4.0: 增加知识库版本号用于缓存失效

_search_cache: TTLCache = TTLCache(
    maxsize=config.SEARCH_CACHE_SIZE,
    ttl=config.SEARCH_CACHE_TTL,
)
# 每个 kb_id 的内容版本号，文档变更时递增
_kb_content_versions: dict = {}


# ── RAG 编排 ─────────────────────────────────────────────────

class RAGService:
    """
    RAG 检索增强生成编排服务。

    完整流程：文档 → 分块 → 嵌入 → 混合索引 → 查询检索 → 重排序 → 构建上下文
    Phase 1: GraphRAG 使用 GraphRetriever 进行多跳图检索 + 全局社区搜索
    """

    @classmethod
    async def index_document(cls, doc_id: str, text: str) -> dict:
        """对文档进行完整索引"""
        chunks = _chunker.chunk(text, doc_id)
        child_chunks = [c for c in chunks if c.chunk_level == "child"]
        parent_chunks = [c for c in chunks if c.chunk_level == "parent"]
        logger.info(f"文档 {doc_id}: {len(parent_chunks)} 父块, {len(child_chunks)} 子块")

        child_texts = [c.text for c in child_chunks]
        embeddings = await EmbeddingService.encode_async(child_texts)

        chunk_dicts = [c.to_dict() for c in child_chunks]
        _hybrid_search.index_document(chunk_dicts, embeddings)

        return {
            "chunk_count": len(chunks),
            "parent_count": len(parent_chunks),
            "child_count": len(child_chunks),
        }

    @classmethod
    async def search_async(
        cls,
        query: str,
        kb_id: str = None,
        db: AsyncSession = None,
        top_k: int = None,
        use_rerank: bool = True,
    ) -> List[SearchResult]:
        """
        异步查询检索 + GraphRAG 增强 (Phase 1)。

        Args:
            query: 用户查询
            kb_id: 知识库ID（用于图检索）
            db: 数据库会话（用于图检索）
            top_k: 返回结果数
            use_rerank: 是否启用重排序
        """
        # 检查缓存（v4.0: 加入知识库内容版本号，文档变更时缓存自动失效）
        kb_version = _kb_content_versions.get(kb_id, 0) if kb_id else 0
        cache_key = f"{query}:{kb_id}:{top_k}:{use_rerank}:v{kb_version}"
        cached = _search_cache.get(cache_key)
        if cached is not None:
            logger.debug(f"[RAG] 缓存命中: {query[:50]}...")
            return cached  # type: ignore[return-value]

        t_start = time.monotonic()

        if top_k is None:
            top_k = config.HYBRID_SEARCH_TOP_K

        # Phase 1: GraphRAG 增强 — 使用 GraphRetriever（当 kb_id 和 db 可用时）
        if config.ENABLE_GRAPH_RAG and kb_id and db:
            results = await _graph_enhanced_search_async(query, top_k, use_rerank, kb_id, db)
        else:
            results = _do_search(query, top_k, use_rerank)

        elapsed_ms = (time.monotonic() - t_start) * 1000

        # 缓存结果
        _search_cache[cache_key] = results

        # 指标日志
        scores = [r.score for r in results] if results else []
        avg_score = sum(scores) / len(scores) if scores else 0.0
        logger.info(
            f"[RAG] 检索完成 | query={query[:60]}... | "
            f"results={len(results)} | avg_score={avg_score:.3f} | "
            f"elapsed={elapsed_ms:.0f}ms | graph_rag={config.ENABLE_GRAPH_RAG}"
        )

        return results

    @classmethod
    async def global_search(
        cls,
        query: str,
        kb_id: str,
        db: AsyncSession,
    ) -> dict:
        """
        全局搜索：使用社区摘要进行 Map-Reduce 式问答 (Microsoft GraphRAG 风格)。

        适用场景: "这个知识库主要讲了什么？" / "有哪些核心主题？"

        Map 阶段: 每个社区独立回答
        Reduce 阶段: 综合所有社区答案生成最终回答
        """
        from app.services.graph_service import GraphService
        from app.services.deepseek_client import DeepSeekClient

        communities = await GraphService.detect_communities(db, kb_id)
        if not communities:
            return {
                "answer": "该知识库暂无社区检测结果，请先上传文档构建知识图谱。",
                "sources": [],
            }

        # 按社区大小排序，取 top N
        top_communities = sorted(
            communities, key=lambda c: c["node_count"], reverse=True
        )[:config.GRAPH_GLOBAL_SEARCH_TOP_COMMUNITIES]

        # Map: 每个社区并发回答
        async def _map_community(comm):
            context = GraphService.format_community_context(comm)
            prompt = (
                f"你是一个知识分析助手。以下是知识图谱中一个社区的摘要信息。\n\n"
                f"社区内容:\n{context}\n\n"
                f"请用简洁的中文回答以下问题（50-100字）:\n{query}\n\n"
                f"如果该社区与问题无关，请回答「不相关」。"
            )
            try:
                result = await DeepSeekClient.chat(
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.3,
                    max_tokens=512,
                )
                return {
                    "community_id": comm["id"],
                    "community_label": comm.get("label", ""),
                    "answer": result["content"],
                    "node_count": comm["node_count"],
                }
            except Exception as e:
                logger.warning(f"社区 {comm['id']} 回答失败: {e}")
                return None

        # 使用 Semaphore 限制并发 API 调用（默认 3-5）
        map_semaphore = asyncio.Semaphore(5)
        async def _map_with_limit(comm):
            async with map_semaphore:
                return await _map_community(comm)

        intermediate_answers_raw = await asyncio.gather(
            *[_map_with_limit(comm) for comm in top_communities],
            return_exceptions=True,
        )
        intermediate_answers = [a for a in intermediate_answers_raw if a is not None and not isinstance(a, Exception)]

        if not intermediate_answers:
            return {"answer": "无法生成全局回答，请重试。", "sources": []}

        # Reduce: 综合所有社区答案
        reduce_prompt = (
            f"用户问题：{query}\n\n"
            f"以下是对知识图谱中 {len(intermediate_answers)} 个不同社区的局部回答，"
            f"请综合成一份全面的最终回答（200-400字）：\n\n"
        )
        for i, ans in enumerate(intermediate_answers):
            reduce_prompt += (
                f"社区{i+1}「{ans['community_label']}」"
                f"（{ans['node_count']}个实体）：{ans['answer']}\n\n"
            )

        try:
            final = await DeepSeekClient.chat(
                messages=[{"role": "user", "content": reduce_prompt}],
                temperature=0.3,
                max_tokens=2048,
            )
        except Exception as e:
            logger.error(f"全局搜索 Reduce 阶段失败: {e}")
            return {"answer": "全局搜索生成失败，请重试。", "sources": []}

        return {
            "answer": final["content"],
            "intermediate_answers": intermediate_answers,
            "community_count": len(top_communities),
        }

    @classmethod
    def build_context(
        cls,
        results: List[SearchResult],
        max_tokens: int = 3000,
        max_sources: int = None,
    ) -> str:
        """将检索结果构建为 LLM 上下文文本"""
        from app.utils.helpers import count_tokens_approximate

        if max_sources is None:
            max_sources = config.CONTEXT_MAX_SOURCES

        context_parts = []
        token_count = 0
        seen_texts = set()

        for i, result in enumerate(results):
            if i >= max_sources:
                break

            text = result.parent_text if result.parent_text else result.text
            if not text:
                continue
            # 文本去重
            text_key = text[:100]
            if text_key in seen_texts:
                continue

            tokens = count_tokens_approximate(text)
            if token_count + tokens > max_tokens:
                break

            source_label = ""
            if result.source:
                source_label = f" (来源: {result.source})"

            context_parts.append(
                f"### 知识片段 {i + 1} (相关性: {result.score:.2f}){source_label}\n{text}\n"
            )
            token_count += tokens
            seen_texts.add(text_key)

        return "\n".join(context_parts)


# ── 内部检索实现 ─────────────────────────────────────────────

def _do_search(
    query: str,
    top_k: int = None,
    use_rerank: bool = True,
) -> List[SearchResult]:
    """核心检索流程（单轮）"""
    if top_k is None:
        top_k = config.HYBRID_SEARCH_TOP_K

    query_vector = EmbeddingService.encode_single(query)
    results = _hybrid_search.search(query, query_vector, top_k=top_k * 2)

    if use_rerank and len(results) > top_k:
        rerank_input = [
            {"text": r.text, "score": r.score, "chunk_id": r.chunk_id,
             "parent_text": r.parent_text, "source": r.source}
            for r in results
        ]
        reranked = RerankerService.rerank(query, rerank_input, top_k=top_k)

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


def invalidate_kb_cache(kb_id: str):
    """文档变更时调用，递增知识库内容版本号使缓存失效"""
    _kb_content_versions[kb_id] = _kb_content_versions.get(kb_id, 0) + 1
    logger.debug(f"知识库 {kb_id} 缓存版本递增至 {_kb_content_versions[kb_id]}")


async def _graph_enhanced_search_async(
    query: str,
    top_k: int,
    use_rerank: bool,
    kb_id: str,
    db: AsyncSession,
) -> List[SearchResult]:
    """
    GraphRAG 增强检索 (Phase 1) — 使用 GraphRetriever 进行多跳图遍历。

    流程：
    1. GraphRetriever 定位种子实体 → BFS 多跳遍历
    2. 收集遍历路径上的实体上下文
    3. 图检索结果 + 混合检索结果 → RRF 融合
    """
    from app.services.graph_retriever import GraphRetriever

    t0 = time.monotonic()
    retriever = GraphRetriever()

    try:
        graph_results = await retriever.retrieve(query, kb_id, db, top_k=top_k)
    except Exception as e:
        logger.warning(f"[GraphRAG] 图检索失败，回退到混合检索: {e}")
        return _do_search(query, top_k, use_rerank)

    if not graph_results:
        logger.debug("[GraphRAG] 图检索无结果，使用混合检索")
        return _do_search(query, top_k, use_rerank)

    # 标准混合检索
    hybrid_results = _do_search(query, top_k, use_rerank)

    # 将图检索结果转换为 SearchResult 格式
    # v4.0: 移除 RRF 融合前的权重预乘（RRF 基于排名而非原始分数，预乘无意义）
    graph_as_search = []
    for gr in graph_results:
        graph_as_search.append(SearchResult(
            chunk_id=f"graph:{gr.entity_id}",
            text=gr.context_text,
            score=gr.score,
            source="graph_traversal",
        ))

    # RRF 融合：混合检索 + 图检索（rrf_fusion 已按 RRF 分数降序排列）
    merged = rrf_fusion([hybrid_results, graph_as_search], k=60)

    elapsed = (time.monotonic() - t0) * 1000
    logger.debug(
        f"[GraphRAG] 增强检索: hybrid={len(hybrid_results)} graph={len(graph_results)} "
        f"merged={len(merged)} | {elapsed:.0f}ms"
    )

    return merged[:top_k]


