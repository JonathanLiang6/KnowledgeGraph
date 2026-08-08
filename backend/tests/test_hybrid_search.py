"""
混合检索 FTS5 索引单元测试
v4.0: FTS5 替代 rank-bm25 — 真正增量索引
"""
import os
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
