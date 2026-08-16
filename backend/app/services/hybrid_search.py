"""
混合检索服务 - LanceDB 向量检索 + BM25 稀疏检索 + RRF 融合
v4.0: FTS5 替代 rank-bm25 — 真正增量更新，零额外依赖
v3.1: 统一 RRF 融合算法（标准 Reciprocal Rank Fusion, k=60）
"""
import os
import re
import sqlite3
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


# ─── FTS5 全文索引（增量 BM25）────────────────────────────────

class FTS5Index:
    """
    SQLite FTS5 全文索引 — 原生支持增量 INSERT/DELETE + BM25 排序。

    优势 vs rank-bm25:
    - 真正的增量更新（INSERT/DELETE 单条记录，无需全量重建）
    - Python 标准库自带，零额外依赖
    - trigram tokenizer 天然支持中文 (3-gram) 和英文 (词级)
    - BM25 排序内置，FTS5 自动管理倒排索引

    分词策略:
    - FTS5 使用 `trigram` tokenizer
    - 自动生成 3-字符 n-gram，中文无需额外分词器
    - 等效于字符级 trigram 索引，兼顾子串匹配精度
    """

    def __init__(self, db_path: str = None):
        if db_path is None:
            from app.core.config import config
            db_path = os.path.join(config.DATA_DIR, "knowledge_graph.db")
        self._db_path = db_path
        self._table_name = "fts_chunks"
        self._conn: Optional[sqlite3.Connection] = None
        self._init_table()

    def _get_conn(self) -> sqlite3.Connection:
        """获取或创建 SQLite 连接（WAL 模式兼容并发读写）"""
        if self._conn is None:
            self._conn = sqlite3.connect(self._db_path, check_same_thread=False)
            self._conn.execute("PRAGMA journal_mode=WAL")
            self._conn.row_factory = sqlite3.Row
        return self._conn

    def _init_table(self):
        """创建 FTS5 虚拟表（如果不存在）— trigram tokenizer 天然支持中文 n-gram"""
        conn = self._get_conn()
        conn.execute(f"""
            CREATE VIRTUAL TABLE IF NOT EXISTS {self._table_name} USING fts5(
                chunk_id UNINDEXED,
                doc_id UNINDEXED,
                text,
                tokenize='trigram'
            )
        """)
        conn.commit()

    def add(self, docs: List[Tuple[str, str]]):
        """
        增量添加文档到 FTS5 索引。

        Args:
            docs: [(chunk_id, text), ...] — 每项一个分块
        """
        if not docs:
            return
        conn = self._get_conn()
        with conn:
            for chunk_id, text in docs:
                # 提取 doc_id（chunk_id 格式通常为 uuid）
                doc_id = chunk_id[:36] if len(chunk_id) >= 36 else chunk_id
                conn.execute(
                    f"INSERT INTO {self._table_name} (chunk_id, doc_id, text) VALUES (?, ?, ?)",
                    (chunk_id, doc_id, text or ""),
                )
        logger.debug(f"FTS5 增量添加: {len(docs)} 块")

    def search(self, query: str, top_k: int = 10) -> List[Tuple[str, float]]:
        """
        FTS5 BM25 搜索。

        使用简化的 FTS5 查询语法，将用户查询中的特殊字符转义。

        Returns:
            [(chunk_id, bm25_score), ...] 按 BM25 分数降序排列
        """
        conn = self._get_conn()
        if not query or not query.strip():
            return []

        # 转义 FTS5 特殊字符，构建安全的 MATCH 查询
        safe_query = self._escape_fts5_query(query.strip())
        if not safe_query:
            return []

        try:
            rows = conn.execute(f"""
                SELECT chunk_id, bm25({self._table_name}) AS score
                FROM {self._table_name}
                WHERE {self._table_name} MATCH ?
                ORDER BY score
                LIMIT ?
            """, (safe_query, top_k)).fetchall()
        except sqlite3.OperationalError as e:
            logger.warning(f"FTS5 搜索语法错误: {e}, query={safe_query[:100]}")
            return []

        if not rows:
            return []

        # 归一化分数到 [0, 1]
        scores = [row["score"] for row in rows]
        min_score = min(scores)
        max_score = max(scores)
        denom = max_score - min_score if max_score != min_score else 1.0
        # FTS5 BM25 分数越低越相关，取负后归一化
        return [
            (row["chunk_id"], round(1.0 - (row["score"] - min_score) / denom, 4))
            for row in rows
        ]

    def remove_by_doc_id(self, doc_id: str):
        """增量删除指定文档的所有分块"""
        conn = self._get_conn()
        with conn:
            conn.execute(
                f"DELETE FROM {self._table_name} WHERE doc_id = ?",
                (doc_id,),
            )
        logger.debug(f"FTS5 删除文档: {doc_id}")

    def remove_by_chunk_id(self, chunk_id: str):
        """增量删除单个分块"""
        conn = self._get_conn()
        with conn:
            conn.execute(
                f"DELETE FROM {self._table_name} WHERE chunk_id = ?",
                (chunk_id,),
            )

    def clear(self):
        """清空所有索引内容"""
        conn = self._get_conn()
        with conn:
            conn.execute(f"DELETE FROM {self._table_name}")
        logger.info("FTS5 索引已清空")

    def close(self):
        """关闭数据库连接"""
        if self._conn is not None:
            self._conn.close()
            self._conn = None

    @property
    def document_count(self) -> int:
        conn = self._get_conn()
        row = conn.execute(
            f"SELECT COUNT(DISTINCT doc_id) FROM {self._table_name}"
        ).fetchone()
        return row[0] if row else 0

    @staticmethod
    def _escape_fts5_query(query: str) -> str:
        """
        转义 FTS5 特殊字符，构建安全的查询字符串。

        FTS5 会将裸词用 AND 连接。对于中文，每个 n-gram 字符
        会被自动匹配，所以直接传入查询文本即可。
        只需移除/转义可能破坏查询语法的特殊字符。
        """
        # 移除 FTS5 保留字符
        cleaned = re.sub(r'[\[\]\(\)\{\}"\*]', '', query)
        # 压缩空白
        cleaned = re.sub(r'\s+', ' ', cleaned).strip()
        return cleaned



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
    混合检索服务 - LanceDB 向量检索 + FTS5 BM25 关键词检索 + RRF 融合。

    v4.0: 使用 SQLite FTS5 替代 rank-bm25 — 支持真正的增量索引。
    """

    def __init__(self):
        self.vector_store = LanceDBStore()
        self.bm25_index = FTS5Index()
        self.vector_weight = 0.7
        self.bm25_weight = 0.3
        # 用于 parent_text 查找的完整块缓存
        self._all_chunks_cache: Dict[str, dict] = {}

    def index_document(self, chunks: List[dict], embeddings: List[List[float]]):
        """
        对新文档建立索引（LanceDB 向量 + FTS5 增量关键词）。

        v4.0: FTS5 支持真正的增量 INSERT，无需全量重建。

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

        # FTS5 增量添加（v4.0: 真正 O(1) 增量，无需全量重建）
        new_docs = [(chunk["id"], chunk["text"]) for chunk in chunks
                     if chunk.get("chunk_level") == "child"]
        if new_docs:
            self.bm25_index.add(new_docs)

    def rebuild_index_from_store(self):
        """从 LanceDB 重建 FTS5 索引（服务恢复用）— v4.0: 清空后增量写入"""
        all_chunks = self.vector_store.get_all_chunks()
        if not all_chunks:
            return

        # 清空 FTS5
        self.bm25_index.clear()

        # 增量写入所有子块
        docs = [(c["id"], c["text"]) for c in all_chunks if c.get("chunk_level") == "child"]
        self.bm25_index.add(docs)

        # 重建缓存
        self._all_chunks_cache = {c["id"]: c for c in all_chunks}
        logger.info(f"从 LanceDB 重建 FTS5 索引: {len(docs)} 子块")

    def search(
        self,
        query: str,
        query_vector: List[float],
        top_k: int = 20,
    ) -> List[SearchResult]:
        """
        混合检索：LanceDB 向量 + FTS5 BM25 → RRF 融合。

        v4.0: FTS5 替代 rank-bm25，BM25 分数由 SQLite 内置 bm25() 函数计算。
        """
        # 1. 向量检索
        vector_results_raw = self.vector_store.search(query_vector, top_k=top_k * 2)
        vector_results: List[SearchResult] = []
        vector_ids: set = set()
        for r in vector_results_raw:
            vid = r["id"]
            distance = r.get("_distance", 0.0)
            similarity = 1.0 / (1.0 + distance)
            vector_results.append(SearchResult(
                chunk_id=vid,
                text=r.get("text", ""),
                score=similarity,
                parent_text=None,
                source="vector",
            ))
            vector_ids.add(vid)

        # 2. FTS5 BM25 检索（v4.0: 真正增量索引）
        bm25_raw = self.bm25_index.search(query, top_k=top_k * 2)
        bm25_results: List[SearchResult] = []
        for doc_id, score in bm25_raw:
            if doc_id not in vector_ids:
                data = self._all_chunks_cache.get(doc_id, {})
                bm25_results.append(SearchResult(
                    chunk_id=doc_id,
                    text=data.get("text", ""),
                    score=score,
                    parent_text=None,
                    source="fts5",
                ))

        # 3. RRF 融合 (标准 Reciprocal Rank Fusion)
        fused = rrf_fusion([vector_results, bm25_results], k=60)
        fused = fused[:top_k]

        # 4. 补充 parent_text
        results = []
        for r in fused:
            parent_text = None
            data = self._all_chunks_cache.get(r.chunk_id, {})
            parent_id = data.get("parent_id", "")
            if parent_id:
                parent_data = self._all_chunks_cache.get(parent_id, {})
                parent_text = parent_data.get("text")
            results.append(SearchResult(
                chunk_id=r.chunk_id,
                text=data.get("text", r.text),
                score=r.score,
                parent_text=parent_text,
                source=r.source,
            ))

        return results

    def remove_document(self, doc_id: str):
        """移除文档的索引 — v4.0: FTS5 增量 DELETE，无需重建"""
        # 从 LanceDB 移除
        self.vector_store.remove_by_doc_id(doc_id)

        # 从缓存移除
        keys_to_remove = [k for k, v in self._all_chunks_cache.items()
                          if v.get("doc_id") == doc_id]
        for k in keys_to_remove:
            self._all_chunks_cache.pop(k, None)

        # FTS5 增量删除（v4.0: 真正 O(1) 删除，无需全量重建）
        self.bm25_index.remove_by_doc_id(doc_id)
        logger.info(f"已移除文档 FTS5 索引: {doc_id} ({len(keys_to_remove)} 块)")


# ─── 模块级单例 ─────────────────────────────────────────────────
# 所有检索和索引操作共享同一实例，确保 FTS5 和向量数据一致
hybrid_search_service = HybridSearchService()


# ─── 标准 RRF 融合函数 ─────────────────────────────────────────
# 统一使用标准 Reciprocal Rank Fusion (k=60)
# 所有检索融合（向量+BM25、混合+图检索）都调用此函数

def rrf_fusion(
    result_sets: List[List[SearchResult]],
    k: int = 60,
) -> List[SearchResult]:
    """
    Reciprocal Rank Fusion — 融合多路检索结果。

    为每个 chunk 计算 RRF 分数:
        score = Σ 1/(k + rank_i)
    其中 rank_i 是该 chunk 在第 i 路结果中的排名（从 1 开始）。

    Args:
        result_sets: 多路检索结果列表，每路是 SearchResult 列表
        k: RRF 平滑常数，默认 60

    Returns:
        融合后的检索结果列表，按 RRF 分数降序排列
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
