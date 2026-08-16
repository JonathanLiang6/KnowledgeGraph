"""
混合检索 FTS5 索引单元测试
v4.0: FTS5 替代 rank-bm25 — 真正增量索引
v4.1: kb_id 知识库隔离 + 旧 schema 自动迁移 + 加权 RRF
"""
import os
import sqlite3
import tempfile
from app.services.hybrid_search import FTS5Index


def _make_temp_index():
    """创建临时数据库的 FTS5Index，测试隔离"""
    fd, path = tempfile.mkstemp(suffix=".db", prefix="test_fts5_")
    os.close(fd)
    return FTS5Index(db_path=path), path


def _cleanup(index, path):
    """关闭连接并删除临时文件"""
    index.close()
    os.unlink(path)


def test_fts5_index_build_and_search():
    """验证 FTS5 索引构建和搜索"""
    index, path = _make_temp_index()
    try:
        docs = [
            ("d1", "机器学习是人工智能的一个分支"),
            ("d2", "深度学习使用神经网络进行特征学习"),
            ("d3", "Python 是一种流行的编程语言"),
        ]
        index.add(docs)
        assert index.document_count == 3

        results = index.search("机器学习", top_k=2)
        assert len(results) <= 2
        assert len(results) > 0
    finally:
        _cleanup(index, path)


def test_fts5_incremental_add():
    """v4.0: FTS5 支持真正的增量添加，无需重建"""
    index, path = _make_temp_index()
    try:
        index.add([("d1", "机器学习是人工智能的一个分支")])
        assert index.document_count == 1

        index.add([("d2", "深度学习使用神经网络")])
        assert index.document_count == 2

        results = index.search("神经网络", top_k=5)
        assert len(results) > 0
    finally:
        _cleanup(index, path)


def test_fts5_remove_document():
    """v4.0: FTS5 支持增量删除，无需重建"""
    index, path = _make_temp_index()
    try:
        index.add([
            ("d1", "机器学习"),
            ("d2", "深度学习"),
        ])
        assert index.document_count == 2

        index.remove_by_chunk_id("d1")

        results = index.search("机器学习", top_k=5)
        d1_results = [r for r in results if r[0] == "d1"]
        assert len(d1_results) == 0
    finally:
        _cleanup(index, path)


def test_fts5_empty_index():
    """空索引搜索不崩溃"""
    index, path = _make_temp_index()
    try:
        results = index.search("test", top_k=5)
        assert results == []
    finally:
        _cleanup(index, path)


# ─── v4.1: kb_id 知识库隔离 ────────────────────────────────────

def test_fts5_kb_id_isolation():
    """#46: FTS5 检索按 kb_id 隔离 — A 库查询不得返回 B 库内容"""
    index, path = _make_temp_index()
    try:
        index.add([
            ("chunk-a1", "机器学习是人工智能的一个分支", "kb-A"),
            ("chunk-b1", "机器学习在金融领域的应用", "kb-B"),
        ])
        assert index.document_count == 2

        results_a = index.search("机器学习", top_k=10, kb_id="kb-A")
        assert [cid for cid, _ in results_a] == ["chunk-a1"]

        results_b = index.search("机器学习", top_k=10, kb_id="kb-B")
        assert [cid for cid, _ in results_b] == ["chunk-b1"]

        # 不过滤（kb_id=None）时两库均可见
        results_all = index.search("机器学习", top_k=10)
        assert {cid for cid, _ in results_all} == {"chunk-a1", "chunk-b1"}
    finally:
        _cleanup(index, path)


def test_lancedb_kb_id_isolation(tmp_path):
    """#46: LanceDB 向量检索按 kb_id 隔离 — A 库查询不得返回 B 库内容"""
    from app.services.hybrid_search import LanceDBStore

    store = LanceDBStore(db_path=str(tmp_path))
    chunks = [
        {"id": "a1", "text": "苹果是一种水果", "doc_id": "d1",
         "chunk_level": "child", "kb_id": "kb-A"},
        {"id": "b1", "text": "苹果公司发布新品", "doc_id": "d2",
         "chunk_level": "child", "kb_id": "kb-B"},
    ]
    store.add(chunks, [[0.1, 0.9], [0.9, 0.1]])
    assert store.count == 2

    res_a = store.search([0.1, 0.9], top_k=10, kb_id="kb-A")
    assert [r["id"] for r in res_a] == ["a1"]

    res_b = store.search([0.1, 0.9], top_k=10, kb_id="kb-B")
    assert [r["id"] for r in res_b] == ["b1"]

    # 不过滤（kb_id=None）时两库均可见
    res_all = store.search([0.5, 0.5], top_k=10)
    assert {r["id"] for r in res_all} == {"a1", "b1"}


def test_fts5_old_schema_migration():
    """#46: 检测到旧 FTS5 表（无 kb_id 列）→ 丢弃重建 + 置迁移标志"""
    fd, path = tempfile.mkstemp(suffix=".db", prefix="test_fts5_old_")
    os.close(fd)
    conn = sqlite3.connect(path)
    conn.execute(
        "CREATE VIRTUAL TABLE fts_chunks USING fts5("
        "chunk_id UNINDEXED, doc_id UNINDEXED, text, tokenize='trigram')"
    )
    conn.execute(
        "INSERT INTO fts_chunks (chunk_id, doc_id, text) VALUES ('x1', 'd1', '旧内容')"
    )
    conn.commit()
    conn.close()

    index = FTS5Index(db_path=path)
    try:
        assert index.schema_migrated is True
        # 旧数据已随旧表丢弃
        assert index.search("旧内容", top_k=5) == []
        # 新 schema 支持带 kb_id 的写入与过滤
        index.add([("y1", "新内容", "kb-A")])
        hits = index.search("新内容", top_k=5, kb_id="kb-A")
        assert [c for c, _ in hits] == ["y1"]
        assert index.search("新内容", top_k=5, kb_id="kb-B") == []
    finally:
        _cleanup(index, path)


def test_full_migration_rebuilds_fts_with_kb_id(tmp_path, monkeypatch):
    """#46: 旧 LanceDB + 旧 FTS5 schema → 服务初始化自动迁移并从 DB 反查 kb_id 回填重建"""
    import lancedb as lancedb_lib
    from app.core.config import config
    from app.services.hybrid_search import HybridSearchService

    monkeypatch.setattr(config, "DATA_DIR", str(tmp_path))

    doc_id = "11111111-1111-1111-1111-111111111111"

    # 1. 构造旧 schema 的 LanceDB 表（无 kb_id 列）
    lance_dir = tmp_path / "lancedb"
    os.makedirs(lance_dir)
    db = lancedb_lib.connect(str(lance_dir))
    db.create_table("chunks", [{
        "id": f"{doc_id}_c0",
        "text": "机器学习是人工智能的分支",
        "vector": [0.1, 0.2],
        "parent_id": "",
        "chunk_level": "child",
        "doc_id": doc_id,
    }])

    # 2. 构造旧 schema 的 FTS5 表（无 kb_id 列）+ documents 表（doc→kb 映射）
    conn = sqlite3.connect(str(tmp_path / "knowledge_graph.db"))
    conn.execute(
        "CREATE VIRTUAL TABLE fts_chunks USING fts5("
        "chunk_id UNINDEXED, doc_id UNINDEXED, text, tokenize='trigram')"
    )
    conn.execute(
        "INSERT INTO fts_chunks (chunk_id, doc_id, text) VALUES ('old1', ?, '远古遗留数据')",
        (doc_id,),
    )
    conn.execute("CREATE TABLE documents (id TEXT PRIMARY KEY, kb_id TEXT)")
    conn.execute("INSERT INTO documents (id, kb_id) VALUES (?, 'kb-A')", (doc_id,))
    conn.commit()
    conn.close()

    # 3. 服务初始化触发迁移
    svc = HybridSearchService()

    # LanceDB: 记录已回填 kb_id，旧表已按新 schema 重建
    assert svc.vector_store.pending_migration_records == []
    assert "kb_id" in svc.vector_store._get_column_names()
    hits_a = svc.vector_store.search([0.1, 0.2], top_k=5, kb_id="kb-A")
    assert [r["id"] for r in hits_a] == [f"{doc_id}_c0"]
    assert svc.vector_store.search([0.1, 0.2], top_k=5, kb_id="kb-B") == []

    # FTS5: 已从（迁移后的）向量库重建，携带 kb_id
    fts_a = svc.bm25_index.search("机器学习", top_k=5, kb_id="kb-A")
    assert [c for c, _ in fts_a] == [f"{doc_id}_c0"]
    assert svc.bm25_index.search("机器学习", top_k=5, kb_id="kb-B") == []
    # 旧 FTS5 表的遗留行已丢弃，不再泄漏
    assert svc.bm25_index.search("远古遗留", top_k=5) == []


def test_rrf_fusion_weighted():
    """#62: 加权 RRF — score = Σ w_i/(k + rank_i)，等价标准 RRF 当权重全 1"""
    from app.services.hybrid_search import SearchResult, rrf_fusion

    vec_hits = [SearchResult("x", "t", 1.0, source="vector")]
    bm_hits = [SearchResult("y", "t", 0.8, source="fts5")]

    # x 仅在向量路 rank1，y 仅在 BM25 路 rank1
    fused = rrf_fusion([vec_hits, bm_hits], k=60, weights=[0.7, 0.3])
    assert fused[0].chunk_id == "x"
    assert abs(fused[0].score - round(0.7 / 61, 4)) < 1e-9
    assert abs(fused[1].score - round(0.3 / 61, 4)) < 1e-9

    # 不传权重 → 标准 RRF（全 1.0）
    fused_eq = rrf_fusion([vec_hits, bm_hits])
    assert abs(fused_eq[0].score - round(1.0 / 61, 4)) < 1e-9

    # 同一 chunk 命中多路 → 加权分数累加
    fused_both = rrf_fusion(
        [vec_hits, [SearchResult("x", "t", 0.5)]], k=60, weights=[0.7, 0.3]
    )
    assert abs(fused_both[0].score - round((0.7 + 0.3) / 61, 4)) < 1e-9

    # 权重数量不匹配 → 忽略权重退化为标准 RRF，不抛异常
    fused_bad = rrf_fusion([vec_hits, bm_hits], k=60, weights=[0.9])
    assert abs(fused_bad[0].score - round(1.0 / 61, 4)) < 1e-9
