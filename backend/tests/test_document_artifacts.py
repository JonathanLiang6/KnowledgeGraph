"""
文档处理阶段产物持久化测试 (v4.1 断点续传加固)

纯文件系统逻辑，不触碰数据库。
"""

from app.models.document import DocumentStatus
from app.tasks.document_tasks import (
    _has_artifact,
    _load_artifact_json,
    _load_artifact_text,
    _RestoredChunk,
    _save_artifact_json,
    _save_artifact_text,
    cleanup_doc_artifacts,
    get_stage_for_status,
)


def test_artifact_text_roundtrip(tmp_path, monkeypatch):
    from app.core.config import config as cfg
    monkeypatch.setattr(cfg, "DATA_DIR", str(tmp_path))
    doc_id = "doc-rt-1"

    assert _load_artifact_text(doc_id, "content.txt") is None
    assert not _has_artifact(doc_id, "content.txt")

    _save_artifact_text(doc_id, "content.txt", "这是解析出的文档内容")
    assert _has_artifact(doc_id, "content.txt")
    assert _load_artifact_text(doc_id, "content.txt") == "这是解析出的文档内容"


def test_artifact_json_roundtrip_and_null(tmp_path, monkeypatch):
    from app.core.config import config as cfg
    monkeypatch.setattr(cfg, "DATA_DIR", str(tmp_path))
    doc_id = "doc-rt-2"

    graph = {"nodes": [{"id": "n1", "name": "机器学习"}], "links": []}
    _save_artifact_json(doc_id, "nlp_graph.json", graph)
    assert _load_artifact_json(doc_id, "nlp_graph.json") == graph

    # None（LLM 失败降级）也应可写入与读取，且与"文件不存在"可区分
    _save_artifact_json(doc_id, "refined_graph.json", None)
    assert _has_artifact(doc_id, "refined_graph.json")
    assert _load_artifact_json(doc_id, "refined_graph.json") is None
    assert not _has_artifact(doc_id, "chunks.json")
    assert _load_artifact_json(doc_id, "chunks.json") is None


def test_cleanup_artifacts(tmp_path, monkeypatch):
    from app.core.config import config as cfg
    monkeypatch.setattr(cfg, "DATA_DIR", str(tmp_path))
    doc_id = "doc-rt-3"
    _save_artifact_text(doc_id, "content.txt", "x")
    cleanup_doc_artifacts(doc_id)
    assert not _has_artifact(doc_id, "content.txt")
    # 幂等：对不存在的目录清理不报错
    cleanup_doc_artifacts(doc_id)


def test_restored_chunk_interface():
    d = {
        "id": "c1",
        "text": "子块内容",
        "parent_id": "p1",
        "chunk_level": "child",
        "doc_id": "d1",
    }
    c = _RestoredChunk(d)
    assert c.text == "子块内容"
    assert c.chunk_level == "child"
    assert c.to_dict() == d
    assert c._embedding is None  # embedding/indexing 阶段可注入


def test_stage_status_mapping():
    assert get_stage_for_status(DocumentStatus.PARSING) == 0
    assert get_stage_for_status(DocumentStatus.NLP_EXTRACTING) == 1
    assert get_stage_for_status(DocumentStatus.LLM_REFINING) == 2
    assert get_stage_for_status(DocumentStatus.CHUNKING) == 3
    assert get_stage_for_status(DocumentStatus.EMBEDDING) == 4
    assert get_stage_for_status(DocumentStatus.INDEXING) == 5
    assert get_stage_for_status(DocumentStatus.PENDING) == -1
    assert get_stage_for_status(DocumentStatus.DONE) == -1
