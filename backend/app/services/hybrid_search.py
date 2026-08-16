"""
混合检索服务 - LanceDB 向量检索 + BM25 稀疏检索 + 加权 RRF 融合
v4.1: kb_id 知识库隔离（向量/FTS5 双路过滤 + 旧 schema 自动迁移）
v4.0: FTS5 替代 rank-bm25 — 真正增量更新，零额外依赖
v3.1: 统一 RRF 融合算法（标准 Reciprocal Rank Fusion, k=60）
"""
import logging
import os
import re
import sqlite3
import threading
from dataclasses import dataclass

from cachetools import LRUCache

logger = logging.getLogger(__name__)


@dataclass
class SearchResult:
    """检索结果"""
    chunk_id: str
    text: str
    score: float
    parent_text: str | None = None
    source: str = ""  # "vector", "bm25", "fusion"


# ─── 分词器（修复版）─────────────────────────────────────────────

class Tokenizer:
    """
    统一分词器 - 中英文混合分词。
    优先使用 jieba，失败时回退到字符级分词。
    """

    _jieba_available: bool | None = None

    @classmethod
    def tokenize(cls, text: str) -> list[str]:
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
    def _jieba_tokenize(cls, text: str) -> list[str]:
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
    def _fallback_tokenize(text: str) -> list[str]:
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

    线程安全 (#60):
    - 单连接 + check_same_thread=False，跨线程并发使用会损坏连接状态，
      所有数据库操作必须持有 self._lock 串行执行

    知识库隔离 (#46):
    - 表结构含 kb_id UNINDEXED 列，search 可按 kb_id 过滤
    """

    def __init__(self, db_path: str = None):
        if db_path is None:
            from app.core.config import config
            db_path = os.path.join(config.DATA_DIR, "knowledge_graph.db")
        self._db_path = db_path
        self._table_name = "fts_chunks"
        self._conn: sqlite3.Connection | None = None
        # #60: 连接被多线程共享（check_same_thread=False），操作必须持锁串行化
        self._lock = threading.RLock()
        # #46: 旧 schema（无 kb_id 列）迁移标志 — 上层据此触发全量回填
        self.schema_migrated = False
        self._init_table()

    def _get_conn(self) -> sqlite3.Connection:
        """获取或创建 SQLite 连接（WAL 模式兼容并发读写）— #60: 双重检查加锁"""
        if self._conn is None:
            with self._lock:
                if self._conn is None:
                    self._conn = sqlite3.connect(self._db_path, check_same_thread=False)
                    self._conn.execute("PRAGMA journal_mode=WAL")
                    self._conn.row_factory = sqlite3.Row
        return self._conn

    def _init_table(self):
        """
        创建 FTS5 虚拟表（如果不存在）— trigram tokenizer 天然支持中文 n-gram

        #46: 旧 schema 迁移 — 检测到已存在的表缺少 kb_id 列时，
        丢弃旧表并按新 schema 重建空表（数据由上层从向量库全量回填），
        同时置 schema_migrated=True 通知上层触发 rebuild。
        """
        conn = self._get_conn()
        with self._lock:
            existing_cols = self._existing_columns(conn)
            if existing_cols and "kb_id" not in existing_cols:
                conn.execute(f"DROP TABLE {self._table_name}")
                conn.commit()
                self.schema_migrated = True
                logger.warning(
                    f"FTS5 表 {self._table_name} 为旧 schema（无 kb_id 列），"
                    "已丢弃旧表并按新 schema 重建（空表），等待从向量库全量回填"
                )
            conn.execute(f"""
                CREATE VIRTUAL TABLE IF NOT EXISTS {self._table_name} USING fts5(
                    chunk_id UNINDEXED,
                    doc_id UNINDEXED,
                    kb_id UNINDEXED,
                    text,
                    tokenize='trigram'
                )
            """)
            conn.commit()

    def _existing_columns(self, conn: sqlite3.Connection) -> list[str]:
        """读取现有表结构的列名；表不存在或读取失败返回 []"""
        try:
            rows = conn.execute(f"PRAGMA table_info({self._table_name})").fetchall()
            return [r["name"] for r in rows]
        except sqlite3.Error:
            return []

    def add(self, docs: list[tuple]):
        """
        增量添加文档到 FTS5 索引。

        Args:
            docs: [(chunk_id, text), ...] 或 [(chunk_id, text, kb_id), ...]
                  — 每项一个分块；缺省 kb_id 记为空串（按库过滤时不可见）
        """
        if not docs:
            return
        conn = self._get_conn()
        with self._lock:
            with conn:
                for doc in docs:
                    chunk_id, text = doc[0], doc[1]
                    kb_id = doc[2] if len(doc) > 2 else ""
                    # 提取 doc_id（chunk_id 格式通常为 uuid）
                    doc_id = chunk_id[:36] if len(chunk_id) >= 36 else chunk_id
                    conn.execute(
                        f"INSERT INTO {self._table_name} (chunk_id, doc_id, kb_id, text) VALUES (?, ?, ?, ?)",
                        (chunk_id, doc_id, kb_id, text or ""),
                    )
        logger.debug(f"FTS5 增量添加: {len(docs)} 块")

    def search(
        self,
        query: str,
        top_k: int = 10,
        kb_id: str | None = None,
    ) -> list[tuple[str, float]]:
        """
        FTS5 BM25 搜索。

        使用简化的 FTS5 查询语法，将用户查询中的特殊字符转义。

        Args:
            query: 查询文本
            top_k: 返回数量
            kb_id: 知识库ID — #46 非空时仅检索该知识库的块（隔离过滤）

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

        # #46: kb_id 为 UNINDEXED 普通列，可直接并入 WHERE（参数化，无注入风险）
        kb_filter = "AND kb_id = ?" if kb_id else ""
        params = (safe_query, kb_id, top_k) if kb_id else (safe_query, top_k)

        try:
            with self._lock:
                rows = conn.execute(f"""
                    SELECT chunk_id, bm25({self._table_name}) AS score
                    FROM {self._table_name}
                    WHERE {self._table_name} MATCH ?
                    {kb_filter}
                    ORDER BY score
                    LIMIT ?
                """, params).fetchall()
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
        with self._lock:
            with conn:
                conn.execute(
                    f"DELETE FROM {self._table_name} WHERE doc_id = ?",
                    (doc_id,),
                )
        logger.debug(f"FTS5 删除文档: {doc_id}")

    def remove_by_chunk_id(self, chunk_id: str):
        """增量删除单个分块"""
        conn = self._get_conn()
        with self._lock:
            with conn:
                conn.execute(
                    f"DELETE FROM {self._table_name} WHERE chunk_id = ?",
                    (chunk_id,),
                )

    def clear(self):
        """清空所有索引内容"""
        conn = self._get_conn()
        with self._lock:
            with conn:
                conn.execute(f"DELETE FROM {self._table_name}")
        logger.info("FTS5 索引已清空")

    def close(self):
        """关闭数据库连接"""
        with self._lock:
            if self._conn is not None:
                self._conn.close()
                self._conn = None

    @property
    def document_count(self) -> int:
        conn = self._get_conn()
        with self._lock:
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

    知识库隔离 (#46): 记录含 kb_id 列，search 支持 where 过滤。
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
        # #46: 旧 schema 迁移暂存记录（create_or_open_table 检测到旧表时填充）
        self.pending_migration_records: list[dict] = []

    def create_or_open_table(self, table_name: str = "chunks"):
        """
        创建或打开表（自动发现已有表）。

        #46: 若打开的旧表 schema 缺少 kb_id 列 → 读取全部记录后丢弃旧表，
        记录暂存到 pending_migration_records（含 vector），由上层补充 kb_id
        后通过 _add_raw_records 回填重建 — 迁移不损失向量，无需重新 embed。
        """
        self._table_name = table_name
        try:
            self._table = self.db.open_table(table_name)
        except Exception:
            self._table = None
            logger.info(f"LanceDB 表不存在，将在首次写入时创建: {table_name}")
            return

        # #46: 检测旧 schema（无 kb_id 列）→ 暂存记录并丢弃旧表
        col_names = self._get_column_names()
        if col_names and "kb_id" not in col_names:
            try:
                self.pending_migration_records = self._table.to_pandas().to_dict('records')
            except Exception as e:
                logger.error(f"LanceDB 旧表数据读取失败，放弃迁移（保持旧表）: {e}")
                self.pending_migration_records = []
            if self.pending_migration_records:
                self.db.drop_table(table_name)
                self._table = None
                logger.warning(
                    f"LanceDB 表 {table_name} 为旧 schema（无 kb_id 列），"
                    f"已读取 {len(self.pending_migration_records)} 条记录并丢弃旧表，等待回填迁移"
                )
                return

        count = self._table.count_rows() if hasattr(self._table, 'count_rows') else "?"
        logger.info(f"LanceDB 表已打开: {table_name} (rows={count})")

    def _get_column_names(self) -> list[str]:
        """读取当前表的列名；表未打开或读取失败返回 []"""
        if self._table is None:
            return []
        try:
            return list(self._table.schema.names)
        except Exception as e:
            logger.debug(f"LanceDB schema 读取失败，跳过迁移检查: {e}")
            return []

    def add(self, chunks: list[dict], embeddings: list[list[float]]):
        """
        批量添加向量记录。

        Args:
            chunks: 文档块列表（含 id, text, parent_id, kb_id 等）
            embeddings: 对应的向量列表
        """

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
                "kb_id": chunk.get("kb_id", ""),  # #46: 知识库隔离维度
            })

        self._add_raw_records(records)
        logger.info(f"LanceDB 添加 {len(records)} 条向量记录到 {self._table_name}")

    def _add_raw_records(self, records: list[dict]):
        """写入完整记录 dict（含 vector/kb_id）— 常规 add 与 schema 迁移回填共用"""
        if not records:
            return
        if self._table is None:
            self._table = self.db.create_table(self._table_name, records)
            logger.info(f"LanceDB 表创建完成: {self._table_name}, {len(records)} 条记录")
        else:
            self._table.add(records)

    def search(
        self,
        query_vector: list[float],
        top_k: int = 20,
        kb_id: str | None = None,
    ) -> list[dict]:
        """
        向量检索。

        Args:
            query_vector: 查询向量
            top_k: 返回数量
            kb_id: 知识库ID — #46 非空时仅检索该知识库的块（隔离过滤）

        Returns:
            [{"id": ..., "text": ..., "_distance": ..., "parent_id": ..., ...}, ...]
        """
        if self._table is None:
            return []

        try:
            builder = self._table.search(query_vector)
            if kb_id:
                # #46: prefilter 先按 kb_id 过滤再算向量距离，避免搜索后过滤截断
                # 单引号双写转义，防止过滤表达式注入/语法破坏
                safe_kb = kb_id.replace("'", "''")
                where_expr = f"kb_id = '{safe_kb}'"
                try:
                    builder = builder.where(where_expr, prefilter=True)
                except TypeError:
                    # 旧版 LanceDB 无 prefilter 参数
                    builder = builder.where(where_expr)
            results = builder.limit(top_k).to_pandas()
            return results.to_dict('records')
        except Exception as e:
            logger.error(f"LanceDB 搜索失败: {e}")
            return []

    def get_all_chunks(self) -> list[dict]:
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
    混合检索服务 - LanceDB 向量检索 + FTS5 BM25 关键词检索 + 加权 RRF 融合。

    v4.1: kb_id 知识库隔离 — 双路检索均按 kb_id 过滤，杜绝跨知识库泄漏。
    v4.0: 使用 SQLite FTS5 替代 rank-bm25 — 支持真正的增量索引。
    """

    # #61: parent_text 查找缓存封顶 — 原为无界 dict，长寿命进程会无限增长；
    # 4096 条足够容纳常见知识库的热点块，超出按 LRU 淘汰最久未访问的
    _CACHE_MAXSIZE = 4096

    def __init__(self):
        self.vector_store = LanceDBStore()
        self.bm25_index = FTS5Index()
        # 用于 parent_text 查找的完整块缓存（#61: LRUCache 封顶）
        self._all_chunks_cache = LRUCache(maxsize=self._CACHE_MAXSIZE)
        # #46: 旧索引 schema（无 kb_id）自动迁移 — 失败不阻断启动，下次启动重试
        try:
            self._migrate_kb_id_if_needed()
        except Exception as e:
            logger.error(f"检索索引 kb_id 迁移失败（跳过，下次启动重试）: {e}")

    def _migrate_kb_id_if_needed(self):
        """
        #46: 旧索引 schema（无 kb_id 列）自动迁移 — 封装在服务初始化内，不改 main.py。

        流程:
        1. LanceDB: create_or_open_table 检测旧 schema → 读取全部记录 → 丢弃旧表，
           记录暂存于 vector_store.pending_migration_records
        2. FTS5: _init_table 检测旧 schema → 丢弃旧表按新 schema 重建空表
           （置 bm25_index.schema_migrated=True）
        3. 从 SQLite documents 表反查 doc_id → kb_id 映射，为向量记录补充 kb_id 后回填
        4. 任一侧发生迁移 → 从（已迁移的）向量库全量重建 FTS5 索引

        注意: main.py lifespan 只在 count>0 时才 rebuild，迁移丢弃旧表后 count=0
        会被跳过，因此重建必须在这里主动触发，否则 FTS5 将保持空表。
        """
        self.vector_store.create_or_open_table("chunks")

        need_rebuild = self.bm25_index.schema_migrated
        records = self.vector_store.pending_migration_records or []

        if records:
            doc_to_kb = self._load_doc_to_kb_map()
            matched = 0
            for rec in records:
                kb = doc_to_kb.get(rec.get("doc_id", ""), "")
                if kb:
                    matched += 1
                rec["kb_id"] = kb
                rec.setdefault("parent_id", "")
                rec.setdefault("chunk_level", "child")
                rec.setdefault("doc_id", "")
            self.vector_store._add_raw_records(records)
            self.vector_store.pending_migration_records = []
            need_rebuild = True
            logger.info(
                f"LanceDB kb_id 迁移完成: {len(records)} 条记录回填，"
                f"其中 {matched} 条匹配到知识库（未匹配的 kb_id 为空，按库过滤时不可见）"
            )

        if need_rebuild:
            self.rebuild_index_from_store()
            logger.info("检测到旧索引 schema，已从向量库全量重建 FTS5 索引（含 kb_id）")

    @staticmethod
    def _load_doc_to_kb_map() -> dict[str, str]:
        """
        从 SQLite documents 表读取 doc_id → kb_id 映射（迁移回填用）。

        使用独立短连接读取，不与 FTS5 共享连接；documents 表不存在
        （全新环境）时返回空映射。
        """
        from app.core.config import config
        db_path = os.path.join(config.DATA_DIR, "knowledge_graph.db")
        mapping: dict[str, str] = {}
        if not os.path.exists(db_path):
            return mapping
        conn = sqlite3.connect(db_path)
        try:
            rows = conn.execute("SELECT id, kb_id FROM documents").fetchall()
            mapping = {str(r[0]): str(r[1]) for r in rows if r[1]}
        except sqlite3.Error as e:
            logger.warning(f"读取 documents 表构建 doc→kb 映射失败: {e}")
        finally:
            conn.close()
        return mapping

    def index_document(
        self,
        chunks: list[dict],
        embeddings: list[list[float]],
        kb_id: str | None = None,
    ):
        """
        对新文档建立索引（LanceDB 向量 + FTS5 增量关键词）。

        v4.0: FTS5 支持真正的增量 INSERT，无需全量重建。

        Args:
            chunks: Chunk 列表
            embeddings: 对应的向量
            kb_id: 知识库ID — #46 写入索引的隔离维度；缺失时该批块
                   无法按知识库过滤（仅全局检索可见）
        """
        if kb_id is None:
            logger.warning("index_document 未指定 kb_id，该批块将无法按知识库隔离过滤")

        # 确保向量表已创建
        self.vector_store.create_or_open_table("chunks")

        # #46: kb_id 注入到每个块（向量与 FTS5 记录均携带）
        for chunk in chunks:
            chunk.setdefault("kb_id", kb_id or "")

        # 向量索引
        self.vector_store.add(chunks, embeddings)

        # 更新缓存
        for chunk in chunks:
            self._all_chunks_cache[chunk["id"]] = chunk

        # FTS5 增量添加（v4.0: 真正 O(1) 增量，无需全量重建；#46: 携带 kb_id）
        new_docs = [
            (chunk["id"], chunk["text"], chunk.get("kb_id", ""))
            for chunk in chunks if chunk.get("chunk_level") == "child"
        ]
        if new_docs:
            self.bm25_index.add(new_docs)

    def rebuild_index_from_store(self):
        """从 LanceDB 重建 FTS5 索引（服务恢复用）— v4.0: 清空后增量写入；#46: 携带 kb_id"""
        all_chunks = self.vector_store.get_all_chunks()
        if not all_chunks:
            return

        # 清空 FTS5
        self.bm25_index.clear()

        # 增量写入所有子块（#46: kb_id 一并写入 FTS5）
        docs = [
            (c["id"], c["text"], c.get("kb_id", ""))
            for c in all_chunks if c.get("chunk_level") == "child"
        ]
        self.bm25_index.add(docs)

        # 重建缓存（#61: LRUCache 封顶，防止无界增长）
        self._all_chunks_cache = LRUCache(maxsize=self._CACHE_MAXSIZE)
        for c in all_chunks:
            self._all_chunks_cache[c["id"]] = c
        logger.info(f"从 LanceDB 重建 FTS5 索引: {len(docs)} 子块")

    def search(
        self,
        query: str,
        query_vector: list[float],
        top_k: int = 20,
        kb_id: str | None = None,
    ) -> list[SearchResult]:
        """
        混合检索：LanceDB 向量 + FTS5 BM25 → 加权 RRF 融合。

        Args:
            query: 查询文本
            query_vector: 查询向量
            top_k: 返回数量
            kb_id: 知识库ID — #46 双路检索均按 kb_id 隔离过滤；
                   None 时不过滤（全局检索），打 warning 提示潜在跨库泄漏
        """
        from app.core.config import config

        if kb_id is None:
            logger.warning(
                "HybridSearchService.search 未指定 kb_id，检索未做知识库隔离（可能跨库泄漏）"
            )

        # 1. 向量检索（#46: kb_id 过滤）
        vector_results_raw = self.vector_store.search(query_vector, top_k=top_k * 2, kb_id=kb_id)
        vector_results: list[SearchResult] = []
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

        # 2. FTS5 BM25 检索（v4.0: 真正增量索引；#46: kb_id 过滤）
        bm25_raw = self.bm25_index.search(query, top_k=top_k * 2, kb_id=kb_id)
        bm25_results: list[SearchResult] = []
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

        # 3. 加权 RRF 融合（#62: 消费 config 的 VECTOR_WEIGHT / BM25_WEIGHT）
        fused = rrf_fusion(
            [vector_results, bm25_results],
            k=60,
            weights=[config.VECTOR_WEIGHT, config.BM25_WEIGHT],
        )
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

        # FTS5 增量删除（v4.0: 真正 O(1) 删除，无需重建）
        self.bm25_index.remove_by_doc_id(doc_id)
        logger.info(f"已移除文档 FTS5 索引: {doc_id} ({len(keys_to_remove)} 块)")


# ─── 模块级单例 ─────────────────────────────────────────────────
# 所有检索和索引操作共享同一实例，确保 FTS5 和向量数据一致
hybrid_search_service = HybridSearchService()


# ─── 加权 RRF 融合函数 ─────────────────────────────────────────
# 统一使用 Reciprocal Rank Fusion (k=60)，支持按检索路加权（#62）
# 所有检索融合（向量+BM25、混合+图检索）都调用此函数

def rrf_fusion(
    result_sets: list[list[SearchResult]],
    k: int = 60,
    weights: list[float] | None = None,
) -> list[SearchResult]:
    """
    Reciprocal Rank Fusion — 融合多路检索结果（#62: 支持加权）。

    为每个 chunk 计算 RRF 分数:
        score = Σ w_i / (k + rank_i)
    其中 rank_i 是该 chunk 在第 i 路结果中的排名（从 1 开始），
    w_i 是第 i 路的权重（向量路 VECTOR_WEIGHT、BM25 路 BM25_WEIGHT、
    图谱路 GRAPH_RETRIEVAL_WEIGHT）。

    Args:
        result_sets: 多路检索结果列表，每路是 SearchResult 列表
        k: RRF 平滑常数，默认 60
        weights: 各路权重，与 result_sets 一一对应；None 时全为 1.0
                 （等价于标准 RRF）

    Returns:
        融合后的检索结果列表，按加权 RRF 分数降序排列
    """
    if weights is None:
        weights = [1.0] * len(result_sets)
    elif len(weights) != len(result_sets):
        logger.warning(
            f"rrf_fusion 权重数量 ({len(weights)}) 与检索路数 ({len(result_sets)}) "
            "不一致，忽略权重退化为标准 RRF"
        )
        weights = [1.0] * len(result_sets)

    chunk_scores: dict[str, float] = {}
    chunk_data: dict[str, SearchResult] = {}

    for results, weight in zip(result_sets, weights):
        for rank, r in enumerate(results, start=1):
            cid = r.chunk_id
            rrf_score = weight / (k + rank)
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
