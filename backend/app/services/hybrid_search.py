"""
混合检索服务 - LanceDB 向量检索 + BM25 稀疏检索 + RRF 融合
P2 优化：BM25 增量更新、LanceDB 持久化、分词修复
"""
import os
import logging
from typing import List, Tuple, Optional, Dict
from dataclasses import dataclass, field
import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class SearchResult:
    """检索结果"""
    chunk_id: str
    text: str
    score: float
    parent_text: Optional[str] = None
    source: str = ""  # "vector", "bm25", "fusion"


# ─── 分词器（修复版）─────────────────────────────────────────────

class Tokenizer:
    """
    统一分词器 - 中英文混合分词。
    优先使用 jieba，失败时回退到字符级分词。
    """

    _jieba_available: Optional[bool] = None

    @classmethod
    def tokenize(cls, text: str) -> List[str]:
        """
        对文本进行分词。

        Returns:
            词条列表
        """
        if not text:
            return []

        # 中英文混合文本 → 需要分词
        has_chinese = any('一' <= ch <= '鿿' for ch in text)

        if not has_chinese:
            # 纯英文/数字 → 空格分词 + 小写
            return text.lower().split()

        # 中文文本 → jieba 分词
        return cls._jieba_tokenize(text)

    @classmethod
    def _jieba_tokenize(cls, text: str) -> List[str]:
        """jieba 分词，带错误恢复"""
        if cls._jieba_available is None:
            cls._check_jieba()

        if cls._jieba_available:
            try:
                import jieba
                return list(jieba.cut(text))
            except Exception as e:
                logger.warning(f"jieba 分词失败: {e}，回退到字符级分词")
                cls._jieba_available = False

        # 回退：字符 + 英文词混合分词
        return cls._fallback_tokenize(text)

    @classmethod
    def _check_jieba(cls):
        """检查 jieba 是否可用"""
        try:
            import jieba
            # 预热
            list(jieba.cut("测试分词"))
            cls._jieba_available = True
        except Exception:
            cls._jieba_available = False

    @staticmethod
    def _fallback_tokenize(text: str) -> List[str]:
        """回退分词：中文字符级 + 英文词级"""
        import re
        tokens = []
        # 提取中文字符序列和英文单词
        for match in re.finditer(r'[一-鿿]+|[a-zA-Z]+|\d+', text):
            segment = match.group()
            if re.match(r'[一-鿿]', segment[0]):
                # 中文字符 → 逐字 + 双字组合
                tokens.extend(list(segment))
                if len(segment) >= 2:
                    tokens.extend(segment[i:i+2] for i in range(len(segment) - 1))
            else:
                tokens.append(segment.lower())
        return tokens


# ─── BM25 索引（增量更新）────────────────────────────────────────

class BM25Index:
    """
    BM25 索引 — 支持增量更新。
    文档数 ≤ threshold 时使用全量重建，超过后使用增量添加。
    """

    def __init__(self):
        self.corpus: List[str] = []
        self.doc_ids: List[str] = []
        self._bm25 = None

    def index(self, docs: List[Tuple[str, str]]):
        """
        全量构建 BM25 索引。

        Args:
            docs: [(doc_id, text), ...] 列表
        """
        from rank_bm25 import BM25Okapi

        self.doc_ids = [d[0] for d in docs]
        self.corpus = [d[1] for d in docs]
        if not docs:
            self._bm25 = None
            return

        tokenized = [Tokenizer.tokenize(text) for text in self.corpus]
        self._bm25 = BM25Okapi(tokenized)
        logger.info(f"BM25 全量索引构建完成: {len(docs)} 篇文档")

    def add_documents(self, docs: List[Tuple[str, str]]):
        """
        添加文档并立即重建索引。

        v2.3 修复: 移除伪增量模式 — 不再延迟重建;
        rank_bm25 不支持增量更新, 每次添加文档后立即全量重建。

        Args:
            docs: [(doc_id, text), ...] 新增文档列表
        """
        if not docs:
            return

        self.doc_ids.extend(d[0] for d in docs)
        self.corpus.extend(d[1] for d in docs)
        self._pending_docs = []
        self._dirty = False
        self._rebuild_index()
        logger.debug(f"BM25 添加 {len(docs)} 篇文档, 累计 {len(self.doc_ids)} 篇（索引已重建）")

    def _rebuild_index(self):
        """全量重建 BM25 索引"""
        from rank_bm25 import BM25Okapi
        if not self.corpus:
            self._bm25 = None
            return
        tokenized = [Tokenizer.tokenize(text) for text in self.corpus]
        self._bm25 = BM25Okapi(tokenized)
        logger.debug(f"BM25 索引重建完成: {len(self.corpus)} 篇文档")

    def _ensure_index(self):
        """确保索引可用（延迟初始化）"""
        if self._bm25 is None and self.corpus:
            self._rebuild_index()

    def search(self, query: str, top_k: int = 10) -> List[Tuple[str, float]]:
        """
        BM25 搜索。

        Returns:
            [(doc_id, score), ...] 按分数降序排列
        """
        self._ensure_index()

        if self._bm25 is None or not self.corpus:
            return []

        tokenized_query = Tokenizer.tokenize(query)
        if not tokenized_query:
            return []

        scores = self._bm25.get_scores(tokenized_query)

        # 归一化
        max_score = float(max(scores)) if len(scores) > 0 and max(scores) > 0 else 1.0
        normalized = scores / max_score

        # 排序取 top_k
        ranked = sorted(
            zip(self.doc_ids, normalized),
            key=lambda x: x[1],
            reverse=True,
        )[:top_k]

        return [(doc_id, float(score)) for doc_id, score in ranked]

    def remove_document(self, doc_id: str):
        """移除文档 (v2.4: 不再每次重建, 由调用方控制)"""
        if doc_id not in self.doc_ids:
            return
        idx = self.doc_ids.index(doc_id)
        self.doc_ids.pop(idx)
        self.corpus.pop(idx)
        logger.debug(f"BM25 移除文档: {doc_id}")

    @property
    def document_count(self) -> int:
        return len(self.doc_ids)


# ─── LanceDB 向量存储（持久化）───────────────────────────────────

class LanceDBStore:
    """
    LanceDB 向量存储封装 — 支持持久化和表管理。
    """

    def __init__(self, db_path: str = None):
        import lancedb
        if db_path is None:
            from app.core.config import config
            db_path = os.path.join(config.DATA_DIR, "lancedb")
        os.makedirs(db_path, exist_ok=True)
        self.db_path = db_path
        self.db = lancedb.connect(db_path)
        self._table = None
        self._table_name = "chunks"

    def create_or_open_table(self, table_name: str = "chunks"):
        """创建或打开表（自动发现已有表）"""
        self._table_name = table_name
        try:
            self._table = self.db.open_table(table_name)
            count = self._table.count_rows() if hasattr(self._table, 'count_rows') else "?"
            logger.info(f"LanceDB 表已打开: {table_name} (rows={count})")
        except Exception:
            self._table = None
            logger.info(f"LanceDB 表不存在，将在首次写入时创建: {table_name}")

    def add(self, chunks: List[dict], embeddings: List[List[float]]):
        """
        批量添加向量记录。

        Args:
            chunks: 文档块列表（含 id, text, parent_id 等）
            embeddings: 对应的向量列表
        """
        import pyarrow as pa

        if not chunks:
            return

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
            self._table = self.db.create_table(self._table_name, records)
            logger.info(f"LanceDB 表创建完成: {self._table_name}, {len(records)} 条记录")
        else:
            self._table.add(records)
            logger.info(f"LanceDB 添加 {len(records)} 条向量记录到 {self._table_name}")

    def search(self, query_vector: List[float], top_k: int = 20) -> List[dict]:
        """
        向量检索。

        Returns:
            [{"id": ..., "text": ..., "_distance": ..., "parent_id": ..., ...}, ...]
        """
        if self._table is None:
            return []

        try:
            results = self._table.search(query_vector).limit(top_k).to_pandas()
            return results.to_dict('records')
        except Exception as e:
            logger.error(f"LanceDB 搜索失败: {e}")
            return []

    def get_all_chunks(self) -> List[dict]:
        """获取所有已索引的块"""
        if self._table is None:
            return []
        try:
            return self._table.to_pandas().to_dict('records')
        except Exception as e:
            logger.error(f"LanceDB 读取全部数据失败: {e}")
            return []

    def remove_by_doc_id(self, doc_id: str):
        """删除指定文档的所有块"""
        if self._table is None:
            return
        try:
            # v2.3: 使用参数化过滤表达式防止 SQL 注入
            try:
                self._table.delete("doc_id = :doc_id", filter_args={"doc_id": doc_id})
            except TypeError:
                # 旧版 LanceDB 不支持参数化, 回退到转义
                safe_id = doc_id.replace("'", "''")
                self._table.delete(f"doc_id = '{safe_id}'")
            logger.info(f"LanceDB 删除文档块: {doc_id}")
        except Exception as e:
            logger.warning(f"LanceDB 删除失败: {e}")

    def compact(self):
        """压缩表文件"""
        if self._table is not None:
            try:
                self._table.compact_files()
                logger.info("LanceDB 表压缩完成")
            except Exception as e:
                logger.debug(f"LanceDB compact 跳过: {e}")

    @property
    def count(self) -> int:
        if self._table is None:
            return 0
        try:
            return self._table.count_rows()
        except Exception:
            return len(self._table.to_pandas())


# ─── 混合检索服务 ─────────────────────────────────────────────────

class HybridSearchService:
    """
    混合检索服务 - 向量 + BM25 双路并行检索 + RRF 融合。

    P2 优化：
    - BM25 增量更新（文档数 > threshold 时增量添加）
    - LanceDB 持久化路径确认
    - parent_text 双路查找（向量表 + BM25 文本库）
    """

    def __init__(self):
        self.vector_store = LanceDBStore()
        self.bm25_index = BM25Index()
        self.vector_weight = 0.7
        self.bm25_weight = 0.3
        # 用于 parent_text 查找的完整块缓存
        self._all_chunks_cache: Dict[str, dict] = {}

    def index_document(self, chunks: List[dict], embeddings: List[List[float]]):
        """
        对新文档建立索引（向量 + BM25 增量）。

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

        # 更新缓存
        for chunk in chunks:
            self._all_chunks_cache[chunk["id"]] = chunk

        # BM25 增量更新（修复：不再每次全量重建）
        new_docs = [(chunk["id"], chunk["text"]) for chunk in chunks
                     if chunk.get("chunk_level") == "child"]
        if new_docs:
            current_count = self.bm25_index.document_count
            if current_count == 0:
                self.bm25_index.index(new_docs)
            else:
                self.bm25_index.add_documents(new_docs)

    def rebuild_index_from_store(self):
        """从 LanceDB 重建 BM25 索引（服务恢复用）"""
        all_chunks = self.vector_store.get_all_chunks()
        if not all_chunks:
            return

        docs = [(c["id"], c["text"]) for c in all_chunks if c.get("chunk_level") == "child"]
        self.bm25_index.index(docs)

        # 重建缓存
        self._all_chunks_cache = {c["id"]: c for c in all_chunks}
        logger.info(f"从 LanceDB 重建索引: {len(docs)} 子块")

    def search(
        self,
        query: str,
        query_vector: List[float],
        top_k: int = 20,
    ) -> List[SearchResult]:
        """
        混合检索：向量 + BM25 → RRF 融合。

        Args:
            query: 查询文本
            query_vector: 查询向量
            top_k: 返回结果数

        Returns:
            融合后的检索结果列表，按分数降序
        """
        # 1. 向量检索
        vector_results = self.vector_store.search(query_vector, top_k=top_k * 2)
        vector_scores: Dict[str, float] = {}
        vector_data: Dict[str, dict] = {}
        for r in vector_results:
            vid = r["id"]
            # LanceDB 返回 _distance，转为相似度分数
            distance = r.get("_distance", 0.0)
            similarity = 1.0 / (1.0 + distance)  # 距离 → 相似度
            vector_scores[vid] = similarity
            vector_data[vid] = r

        # 2. BM25 检索
        bm25_results = self.bm25_index.search(query, top_k=top_k * 2)
        bm25_scores: Dict[str, float] = {}
        for doc_id, score in bm25_results:
            bm25_scores[doc_id] = score

        # 3. RRF 融合
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

        # 4. 构建 SearchResult（修复 parent_text 查找）
        results = []
        for chunk_id, score in fused:
            # 优先从向量结果获取数据
            data = vector_data.get(chunk_id)
            if data is None:
                # BM25 only 的结果：从缓存获取
                data = self._all_chunks_cache.get(chunk_id, {})

            text = data.get("text", "")
            parent_text = None
            parent_id = data.get("parent_id", "")

            if parent_id:
                # 查找父块文本：先查向量数据，再查缓存
                parent_data = vector_data.get(parent_id) or self._all_chunks_cache.get(parent_id, {})
                parent_text = parent_data.get("text", "")

            source = "fusion"
            if chunk_id in vector_scores and chunk_id not in bm25_scores:
                source = "vector"
            elif chunk_id in bm25_scores and chunk_id not in vector_scores:
                source = "bm25"

            results.append(SearchResult(
                chunk_id=chunk_id,
                text=text,
                score=score,
                parent_text=parent_text,
                source=source,
            ))

        return results

    def remove_document(self, doc_id: str):
        """移除文档的索引 (v2.4: 批量移除后一次重建 BM25)"""
        # 从 LanceDB 移除
        self.vector_store.remove_by_doc_id(doc_id)

        # 从缓存移除并收集待删除 BM25 ID
        keys_to_remove = [k for k, v in self._all_chunks_cache.items()
                          if v.get("doc_id") == doc_id]
        to_rebuild = []
        for k in keys_to_remove:
            self._all_chunks_cache.pop(k, None)
            if k in self.bm25_index.doc_ids:
                idx = self.bm25_index.doc_ids.index(k)
                self.bm25_index.doc_ids.pop(idx)
                self.bm25_index.corpus.pop(idx)
                to_rebuild.append(k)

        # 批量移除后一次重建 BM25
        if to_rebuild:
            self.bm25_index._rebuild_index()
            logger.info(f"已移除文档索引: {doc_id} ({len(to_rebuild)} 块)")
