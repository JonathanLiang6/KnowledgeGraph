"""测试工具函数"""
import pytest
from app.utils.helpers import (
    compute_file_hash,
    count_tokens_approximate,
    calculate_similarity,
)


def test_count_tokens_chinese():
    """中文文本 token 计数"""
    text = "这是一个测试句子"
    tokens = count_tokens_approximate(text)
    assert tokens > 0
    assert isinstance(tokens, int)


def test_count_tokens_english():
    """英文文本 token 计数"""
    text = "This is a test sentence"
    tokens = count_tokens_approximate(text)
    assert tokens > 0


def test_count_tokens_empty():
    """空文本"""
    assert count_tokens_approximate("") == 0


def test_calculate_similarity_identical():
    """相同文本的 Jaccard 相似度"""
    text = "人工智能机器学习"
    assert calculate_similarity(text, text) == 1.0


def test_calculate_similarity_different():
    """完全不同文本的相似度"""
    sim = calculate_similarity("机器学习", "化学反应")
    assert sim < 0.5


def test_calculate_similarity_partial():
    """部分重叠文本的相似度 — 使用英文可确保词级分割"""
    sim = calculate_similarity("machine learning deep learning", "machine learning neural network")
    assert 0 < sim < 1.0


def test_compute_file_hash(tmp_path):
    """SHA256 文件哈希计算"""
    file_path = tmp_path / "test.txt"
    file_path.write_text("hello world", encoding="utf-8")
    hash_val = compute_file_hash(str(file_path))
    assert len(hash_val) == 64  # SHA256 hex
    assert isinstance(hash_val, str)


def test_compute_file_hash_deterministic(tmp_path):
    """同一文件产生相同哈希"""
    file_path = tmp_path / "test2.txt"
    file_path.write_text("test content", encoding="utf-8")
    h1 = compute_file_hash(str(file_path))
    h2 = compute_file_hash(str(file_path))
    assert h1 == h2
