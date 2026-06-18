"""
RAG 编排服务 - 串联 chunk → embed → hybrid search → rerank → build context
v2.2: GraphRAG 增强检索 / 查询改写 / LRU 缓存 / 检索指标日志
v2.3: 图谱索引线程安全 + 缓存 key 包含图谱状态
"""
import time
import asyncio
import logging
from typing import List, Optional, Dict
from collections import OrderedDict
from app.services.chunking_service import SemanticChunker, Chunk
from app.services.embedding_service import EmbeddingService
from app.services.hybrid_search import HybridSearchService, SearchResult
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
_hybrid_search = HybridSearchService()

# ── 图谱实体索引 (内存) + 线程安全 ──────────────────────────
# 结构: {"实体名": {"type": "...", "related": ["关联实体1", ...], "id": "..."}}
_graph_entity_index: Dict[str, dict] = {}
_graph_index_lock = asyncio.Lock()
_graph_version: int = 0  # 图谱版本号, 用于缓存失效


def update_graph_index(nodes: List[dict], links: List[dict]):
    """更新图谱实体索引，供 GraphRAG 检索使用（非异步，由调用方保证线程安全）"""
    global _graph_version
    if not nodes:
        return
    _graph_entity_index.clear()
    name_to_info = {}
    for nd in nodes:
        name_to_info[nd.get("name", "")] = {
            "id": nd.get("id", ""),
            "type": nd.get("type", ""),
            "weight": nd.get("weight", 0.5),
            "related": [],
        }

    # 填充关联实体 (v2.3: 先构建 ID→name 映射, O(n+m) 替代 O(n*m))
    id_to_name = {nd.get("id", ""): nd.get("name", "") for nd in nodes}
    for link in links:
        src = link.get("source", "")
        tgt = link.get("target", "")
        src_name = id_to_name.get(src, "")
        tgt_name = id_to_name.get(tgt, "")
        if src_name in name_to_info:
            name_to_info[src_name]["related"].append(tgt_name)
        if tgt_name in name_to_info:
            name_to_info[tgt_name]["related"].append(src_name)

    for name, info in name_to_info.items():
        _graph_entity_index[name] = info
    _graph_version += 1
    logger.debug(f"[GraphRAG] 图谱索引更新: {len(_graph_entity_index)} 实体 (v{_graph_version})")


async def _extract_query_entities_async(query: str) -> List[str]:
    """从查询中快速匹配图谱实体（基于子串匹配, 带锁）"""
    async with _graph_index_lock:
        matched = []
        for name in _graph_entity_index:
            if len(name) >= 2 and name in query:
                matched.append(name)
        # 按权重排序，取 top
        matched.sort(key=lambda n: _graph_entity_index[n].get("weight", 0), reverse=True)
        return matched


def _extract_query_entities(query: str) -> List[str]:
    """同步版本（内部使用，调用方需确保线程安全）"""
    matched = []
    for name in _graph_entity_index:
        if len(name) >= 2 and name in query:
            matched.append(name)
    matched.sort(key=lambda n: _graph_entity_index[n].get("weight", 0), reverse=True)
    return matched


# ── LRU 检索缓存 ────────────────────────────────────────────

class _SearchCache:
    """线程安全的 LRU 检索缓存"""

    def __init__(self, max_size: int = 128, ttl: int = 60):
        self._cache = OrderedDict()
        self._max_size = max_size
        self._ttl = ttl

    def get(self, key: str) -> Optional[List[SearchResult]]:
        if key not in self._cache:
            return None
        entry = self._cache[key]
        if time.monotonic() - entry["ts"] > self._ttl:
            del self._cache[key]
            return None
        self._cache.move_to_end(key)
        return entry["results"]

    def set(self, key: str, results: List[SearchResult]):
        if key in self._cache:
            self._cache.move_to_end(key)
            self._cache[key] = {"results": results, "ts": time.monotonic()}
        else:
            self._cache[key] = {"results": results, "ts": time.monotonic()}
            if len(self._cache) > self._max_size:
                self._cache.popitem(last=False)

    def clear(self):
        self._cache.clear()


_search_cache = _SearchCache(
    max_size=config.SEARCH_CACHE_SIZE,
    ttl=config.SEARCH_CACHE_TTL,
)


# ── RAG 编排 ─────────────────────────────────────────────────

class RAGService:
    """
    RAG 检索增强生成编排服务。
    完整流程：文档 → 分块 → 嵌入 → 混合索引 → 查询检索 → 重排序 → 构建上下文
    v2.2: + GraphRAG 增强 + 查询改写 + 缓存 + 指标
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
    def search(
        cls,
        query: str,
        top_k: int = None,
        use_rerank: bool = True,
    ) -> List[SearchResult]:
        """同步查询检索"""
        return _do_search(query, top_k, use_rerank)

    @classmethod
    async def search_async(
        cls,
        query: str,
        top_k: int = None,
        use_rerank: bool = True,
    ) -> List[SearchResult]:
        """异步查询检索 + GraphRAG 增强"""
        # 检查缓存 (v2.3: 缓存 key 包含图谱版本)
        cache_key = f"{query}:{top_k}:{use_rerank}:gv{_graph_version}"
        cached = _search_cache.get(cache_key)
        if cached is not None:
            logger.debug(f"[RAG] 缓存命中: {query[:50]}...")
            return cached

        t_start = time.monotonic()

        if top_k is None:
            top_k = config.HYBRID_SEARCH_TOP_K

        # GraphRAG 增强: 用图谱实体扩展查询 (v2.3: 带锁保护)
        if config.ENABLE_GRAPH_RAG and _graph_entity_index:
            results = await _graph_enhanced_search_async(query, top_k, use_rerank)
        else:
            results = _do_search(query, top_k, use_rerank)

        elapsed_ms = (time.monotonic() - t_start) * 1000

        # 缓存结果
        _search_cache.set(cache_key, results)

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


async def _graph_enhanced_search_async(
    query: str,
    top_k: int,
    use_rerank: bool,
) -> List[SearchResult]:
    """
    GraphRAG 增强检索 (v2.3: 带 asyncio.Lock 保护)：
    1. 从 query 中匹配图谱实体
    2. 用关联实体名扩展 query
    3. 原始 query + 扩展 query 各检索一轮
    4. RRF 融合两轮结果
    """
    t0 = time.monotonic()

    # 1. 匹配图谱实体（带锁）
    matched = await _extract_query_entities_async(query)

    if not matched:
        logger.debug("[GraphRAG] 未匹配到图谱实体，使用原始检索")
        return _do_search(query, top_k, use_rerank)

    # 2. 收集关联实体（带锁读取）
    async with _graph_index_lock:
        expand_terms = []
        seen_expand = set(matched)
        for name in matched[:config.GRAPH_RAG_EXPAND_ENTITIES]:
            info = _graph_entity_index.get(name, {})
            for rel in info.get("related", [])[:5]:
                if rel not in seen_expand:
                    expand_terms.append(rel)
                    seen_expand.add(rel)

    if not expand_terms:
        return _do_search(query, top_k, use_rerank)

    # 3. 扩展查询
    expanded_query = query + " " + " ".join(expand_terms[:5])
    logger.debug(f"[GraphRAG] 匹配实体: {matched[:3]}, 扩展词: {expand_terms[:5]}")

    # 4. 两轮检索
    raw_results = _do_search(query, top_k, use_rerank)
    exp_results = _do_search(expanded_query, top_k, use_rerank)

    # 5. RRF 融合
    merged = _rrf_fusion([raw_results, exp_results], k=60)
    merged.sort(key=lambda r: r.score, reverse=True)

    elapsed = (time.monotonic() - t0) * 1000
    logger.debug(
        f"[GraphRAG] 增强检索: raw={len(raw_results)} exp={len(exp_results)} "
        f"merged={len(merged)} | {elapsed:.0f}ms"
    )

    return merged[:top_k]


def _graph_enhanced_search(
    query: str,
    top_k: int,
    use_rerank: bool,
) -> List[SearchResult]:
    """
    GraphRAG 增强检索（同步版, 仅供内部非并发场景使用）：
    1. 从 query 中匹配图谱实体
    2. 用关联实体名扩展 query
    3. 原始 query + 扩展 query 各检索一轮
    4. RRF 融合两轮结果
    """
    t0 = time.monotonic()

    # 1. 匹配图谱实体
    matched = _extract_query_entities(query)

    if not matched:
        logger.debug("[GraphRAG] 未匹配到图谱实体，使用原始检索")
        return _do_search(query, top_k, use_rerank)

    # 2. 收集关联实体
    expand_terms = []
    seen_expand = set(matched)
    for name in matched[:config.GRAPH_RAG_EXPAND_ENTITIES]:
        info = _graph_entity_index.get(name, {})
        for rel in info.get("related", [])[:5]:
            if rel not in seen_expand:
                expand_terms.append(rel)
                seen_expand.add(rel)

    if not expand_terms:
        return _do_search(query, top_k, use_rerank)

    # 3. 扩展查询
    expanded_query = query + " " + " ".join(expand_terms[:5])
    logger.debug(f"[GraphRAG] 匹配实体: {matched[:3]}, 扩展词: {expand_terms[:5]}")

    # 4. 两轮检索
    raw_results = _do_search(query, top_k, use_rerank)
    exp_results = _do_search(expanded_query, top_k, use_rerank)

    # 5. RRF 融合
    merged = _rrf_fusion([raw_results, exp_results], k=60)
    merged.sort(key=lambda r: r.score, reverse=True)

    elapsed = (time.monotonic() - t0) * 1000
    logger.debug(
        f"[GraphRAG] 增强检索: raw={len(raw_results)} exp={len(exp_results)} "
        f"merged={len(merged)} | {elapsed:.0f}ms"
    )

    return merged[:top_k]


def _rrf_fusion(
    result_sets: List[List[SearchResult]],
    k: int = 60,
) -> List[SearchResult]:
    """
    Reciprocal Rank Fusion — 融合多轮检索结果。

    为每个 chunk 计算 RRF 分数:
        score = Σ 1/(k + rank_i)
    其中 rank_i 是该 chunk 在第 i 轮结果中的排名。
    """
    chunk_scores: Dict[str, float] = {}
    chunk_data: Dict[str, SearchResult] = {}

    for results in result_sets:
        for rank, r in enumerate(results, start=1):
            cid = r.chunk_id
            rrf_score = 1.0 / (k + rank)
            chunk_scores[cid] = chunk_scores.get(cid, 0.0) + rrf_score
            if cid not in chunk_data:
                chunk_data[cid] = r

    # 按 RRF 分数排序
    sorted_ids = sorted(chunk_scores, key=chunk_scores.get, reverse=True)

    merged = []
    for cid in sorted_ids:
        data = chunk_data[cid]
        data.score = round(chunk_scores[cid], 4)
        merged.append(data)

    return merged
