"""
混合检索 BM25 索引单元测试
"""
from app.services.hybrid_search import BM25Index


def test_bm25_index_build_and_search():
    """验证 BM25 索引构建和搜索"""
    index = BM25Index()
    docs = [
        ("d1", "机器学习是人工智能的一个分支"),
        ("d2", "深度学习使用神经网络进行特征学习"),
        ("d3", "Python 是一种流行的编程语言"),
    ]
    index.index(docs)
    assert index.document_count == 3

    results = index.search("机器学习", top_k=2)
    assert len(results) <= 2
    assert len(results) > 0
    # "d1" 应该最相关
    assert results[0][0] == "d1"


def test_bm25_add_documents_rebuild():
    """v2.3: add_documents 后立即重建索引"""
    index = BM25Index()
    index.index([("d1", "机器学习是人工智能的一个分支")])
    assert index.document_count == 1

    index.add_documents([("d2", "深度学习使用神经网络")])
    assert index.document_count == 2

    results = index.search("神经网络", top_k=5)
    assert len(results) > 0


def test_bm25_remove_document():
    """验证文档移除"""
    index = BM25Index()
    index.index([
        ("d1", "机器学习"),
        ("d2", "深度学习"),
    ])
    assert index.document_count == 2

    index.remove_document("d1")
    assert index.document_count == 1

    results = index.search("机器学习", top_k=5)
    assert len(results) <= 1


def test_bm25_empty_corpus():
    """空语料库搜索不崩溃"""
    index = BM25Index()
    results = index.search("test", top_k=5)
    assert results == []
