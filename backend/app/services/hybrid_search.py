"""
混合检索服务 - LanceDB 向量检索 + BM25 稀疏检索 + RRF 融合
"""
import os
import logging
from typing import List, Tuple, Optional
from dataclasses import dataclass
import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class SearchResult:
    """检索结果"""
    chunk_id: str
    text: str
    score: float
    parent_text: Optional[str] = None
    source: str = ""  # "vector" or "bm25"


class BM25Index:
    """
    轻量级 BM25 索引。
    基于 rank_bm25 库实现稀疏检索。
    """

    def __init__(self):
        self.corpus: List[str] = []
        self.doc_ids: List[str] = []
        self._bm25 = None

    def index(self, docs: List[Tuple[str, str]]):
        """
        构建 BM25 索引

        Args:
            docs: [(doc_id, text), ...] 列表
        """
        from rank_bm25 import BM25Okapi

        self.doc_ids = [d[0] for d in docs]
        self.corpus = [d[1] for d in docs]

        # 对中文文本进行分词处理
        tokenized = [self._tokenize(text) for text in self.corpus]
        self._bm25 = BM25Okapi(tokenized)
        logger.info(f"BM25 索引构建完成: {len(docs)} 篇文档")

    def search(self, query: str, top_k: int = 10) -> List[Tuple[str, float]]:
        """
        BM25 搜索

        Returns:
            [(doc_id, score), ...] 按分数降序排列
        """
        if self._bm25 is None:
            return []

        tokenized_query = self._tokenize(query)
        scores = self._bm25.get_scores(tokenized_query)

        # 归一化分数
        max_score = max(scores) if len(scores) > 0 and max(scores) > 0 else 1.0
        normalized = scores / max_score

        # 排序取 top_k
        ranked = sorted(
            zip(self.doc_ids, normalized),
            key=lambda x: x[1],
            reverse=True,
        )[:top_k]

        return [(doc_id, float(score)) for doc_id, score in ranked]

    @staticmethod
    def _tokenize(text: str) -> List[str]:
        """中文分词"""
        try:
            import jieba
            return list(jieba.cut(text))
        except ImportError:
            # 回退：按字符分词
            return list(text)


class LanceDBStore:
    """
    LanceDB 向量存储封装。
    提供向量索引的创建、写入和搜索。
    """

    def __init__(self, db_path: str = None):
        import lancedb
        if db_path is None:
            from app.core.config import config
            db_path = os.path.join(config.DATA_DIR, "lancedb")
        os.makedirs(db_path, exist_ok=True)
        self.db = lancedb.connect(db_path)
        self._table = None

    def create_or_open_table(self, table_name: str = "chunks"):
        """创建或打开表"""
        try:
            self._table = self.db.open_table(table_name)
            logger.info(f"LanceDB 表已打开: {table_name}")
        except Exception:
            self._table = None
            logger.info(f"LanceDB 表不存在，将在首次写入时创建: {table_name}")

    def add(self, chunks: List[dict], embeddings: List[List[float]]):
        """
        批量添加向量

        Args:
            chunks: 文档块列表（含 id, text, parent_id 等）
            embeddings: 对应的向量列表
        """
        import pyarrow as pa

        records = []
        for chunk, vec in zip(chunks, embeddings):
            records.append({
                "id": chunk["id"],
                "text": chunk["text"],
                "vector": vec,
                "parent_id": chunk.get("parent_id", ""),
                "chunk_level": chunk.get("chunk_level", "child"),
                "doc_id": chunk.get("doc_id", ""),
            })

        if self._table is None:
            self._table = self.db.create_table("chunks", records)
            logger.info(f"LanceDB 表创建完成: {len(records)} 条记录")
        else:
            self._table.add(records)
            logger.info(f"LanceDB 添加 {len(records)} 条向量记录")

    def search(self, query_vector: List[float], top_k: int = 20) -> List[dict]:
        """
        向量检索

        Returns:
            [{"id": ..., "text": ..., "score": ..., "parent_id": ...}, ...]
        """
        if self._table is None:
            return []

        try:
            results = self._table.search(query_vector).limit(top_k).to_list()
            return results
        except Exception as e:
            logger.error(f"LanceDB 搜索失败: {e}")
            return []


class HybridSearchService:
    """
    混合检索服务 - 向量 + BM25 双路并行检索 + RRF 融合
    """

    def __init__(self):
        self.vector_store = LanceDBStore()
        self.bm25_index = BM25Index()
        self.vector_weight = 0.7   # config.VECTOR_WEIGHT
        self.bm25_weight = 0.3     # config.BM25_WEIGHT

    def index_document(self, chunks: List[dict], embeddings: List[List[float]]):
        """
        对新文档建立索引（向量 + BM25）

        Args:
            chunks: Chunk 列表
            embeddings: 对应的向量
        """
        from app.core.config import config

        self.vector_weight = config.VECTOR_WEIGHT
        self.bm25_weight = config.BM25_WEIGHT

        # 确保向量表已创建
        self.vector_store.create_or_open_table("chunks")

        # 向量索引
        self.vector_store.add(chunks, embeddings)

        # BM25 索引：重建整个索引
        # （简化实现，生产环境应增量更新）
        all_chunks = []
        try:
            existing = self.vector_store._table.to_list() if self.vector_store._table else []
            for record in existing:
                all_chunks.append((record["id"], record["text"]))
        except Exception as e:
            logger.warning(f"读取已有向量索引时出错（将重建索引）: {e}")
        for chunk in chunks:
            all_chunks.append((chunk["id"], chunk["text"]))
        self.bm25_index.index(all_chunks)

    def search(
        self,
        query: str,
        query_vector: List[float],
        top_k: int = 20,
    ) -> List[SearchResult]:
        """
        混合检索：向量 + BM25 → RRF 融合

        Args:
            query: 查询文本
            query_vector: 查询向量
            top_k: 返回结果数

        Returns:
            融合后的检索结果列表，按分数降序
        """
        # 1. 向量检索
        vector_results = self.vector_store.search(query_vector, top_k=top_k * 2)
        vector_scores = {r["id"]: (1.0 - r.get("_distance", 0.0)) for r in vector_results}

        # 2. BM25 检索
        bm25_results = self.bm25_index.search(query, top_k=top_k * 2)
        bm25_scores = {doc_id: score for doc_id, score in bm25_results}

        # 3. RRF (Reciprocal Rank Fusion) 融合
        all_ids = set(list(vector_scores.keys()) + list(bm25_scores.keys()))

        fused = []
        for chunk_id in all_ids:
            v_score = vector_scores.get(chunk_id, 0.0)
            b_score = bm25_scores.get(chunk_id, 0.0)
            fused_score = self.vector_weight * v_score + self.bm25_weight * b_score
            fused.append((chunk_id, fused_score))

        # 排序
        fused.sort(key=lambda x: x[1], reverse=True)
        fused = fused[:top_k]

        # 构建 SearchResult
        results = []
        for chunk_id, score in fused:
            # 从向量结果获取文本
            text = ""
            parent_text = None
            for r in vector_results:
                if r["id"] == chunk_id:
                    text = r.get("text", "")
                    parent_id = r.get("parent_id", "")
                    if parent_id:
                        # 查找父块文本
                        for pr in vector_results:
                            if pr["id"] == parent_id:
                                parent_text = pr.get("text", "")
                                break
                    break

            source = "vector" if chunk_id in vector_scores else "bm25"
            results.append(SearchResult(
                chunk_id=chunk_id,
                text=text,
                score=score,
                parent_text=parent_text,
                source=source,
            ))

        return results
