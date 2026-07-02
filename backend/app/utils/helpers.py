"""
通用工具函数 - 文件安全、流式 I/O、格式化
"""
import hashlib
import re
import os
import time
import logging
from pathlib import Path
from typing import Tuple

logger = logging.getLogger(__name__)

# ─── 安全/校验工具 ─────────────────────────────────────────────


def compute_file_hash(filepath: str, algorithm: str = "sha256") -> str:
    """
    计算文件哈希值，用于去重检测。
    流式读取，支持大文件。
    """
    hasher = hashlib.new(algorithm)
    with open(filepath, "rb") as f:
        for chunk in iter(lambda: f.read(64 * 1024), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def detect_mime_type(filepath: str) -> str:
    """
    基于文件内容（magic bytes）检测 MIME 类型。
    回退到扩展名推测。

    Returns:
        MIME 类型字符串，如 "application/pdf"
    """
    try:
        import filetype
        kind = filetype.guess(filepath)
        if kind is not None:
            return kind.mime
    except ImportError:
        pass

    try:
        with open(filepath, "rb") as f:
            header = f.read(8)
    except OSError:
        return "application/octet-stream"

    if header[:4] == b"%PDF":
        return "application/pdf"
    if header[:4] == b"PK\x03\x04":
        ext = Path(filepath).suffix.lower()
        if ext == ".docx":
            return "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        if ext == ".pptx":
            return "application/vnd.openxmlformats-officedocument.presentationml.presentation"
        if ext == ".epub":
            return "application/epub+zip"
        return "application/zip"
    if header.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if header.startswith(b"\x89PNG"):
        return "image/png"
    if header[:4] == b"RIFF" and header[8:12] == b"WEBP":
        return "image/webp"

    try:
        header.decode("utf-8")
        ext = Path(filepath).suffix.lower()
        if ext in (".md", ".markdown"):
            return "text/markdown"
        if ext in (".html", ".htm"):
            return "text/html"
        return "text/plain"
    except UnicodeDecodeError:
        pass

    return "application/octet-stream"


def validate_file_allowed(filepath: str, original_filename: str,
                          detected_mime: str = None) -> Tuple[bool, str]:
    """
    校验文件是否在允许列表中。

    Returns:
        (is_allowed, reason)
    """
    from app.core.config import config

    if detected_mime is None:
        detected_mime = detect_mime_type(filepath)

    ext = Path(original_filename).suffix.lower()

    if ext not in config.ALLOWED_EXTENSIONS:
        return False, f"文件类型 '{ext}' 不在允许列表中"

    if detected_mime not in config.ALLOWED_MIME_TYPES:
        return False, f"MIME 类型 '{detected_mime}' 不在允许列表中"

    return True, "ok"


# ─── 流式文件写入 ─────────────────────────────────────────────────


def stream_save_upload(file_obj, dest_path: str, chunk_size: int = 1024 * 1024) -> int:
    """
    流式写入上传文件到磁盘，避免全量读入内存。

    Args:
        file_obj: 类文件对象（如 UploadFile.file）
        dest_path: 目标路径
        chunk_size: 每次写入块大小（默认 1MB）

    Returns:
        写入的总字节数
    """
    ensure_dir(os.path.dirname(dest_path))
    total = 0
    with open(dest_path, "wb") as f:
        while True:
            chunk = file_obj.read(chunk_size)
            if not chunk:
                break
            f.write(chunk)
            total += len(chunk)
    return total


# ─── 基础工具 ─────────────────────────────────────────────────


def generate_id(text: str, prefix: str = "") -> str:
    """基于文本生成 SHA256 唯一 ID"""
    hash_obj = hashlib.sha256(text.encode("utf-8"))
    raw_id = hash_obj.hexdigest()[:12]
    return f"{prefix}_{raw_id}" if prefix else raw_id


def sanitize_filename(filename: str) -> str:
    """移除文件名中的非法字符"""
    return re.sub(r'[<>:"/\\|?*]', "_", filename)


def truncate_text(text: str, max_length: int = 500, suffix: str = "...") -> str:
    """截断文本到指定长度"""
    if len(text) <= max_length:
        return text
    return text[:max_length] + suffix


def ensure_dir(path: str):
    """确保目录存在"""
    Path(path).mkdir(parents=True, exist_ok=True)


def format_file_size(size_bytes: int) -> str:
    """格式化文件大小"""
    for unit in ["B", "KB", "MB", "GB"]:
        if size_bytes < 1024:
            return f"{size_bytes:.1f} {unit}" if unit != "B" else f"{size_bytes} B"
        size_bytes /= 1024
    return f"{size_bytes:.1f} TB"


def count_tokens_approximate(text: str) -> int:
    """估算 token 数量"""
    chinese_chars = len(re.findall(r"[一-鿿㐀-䶿豈-﫿]", text))
    english_words = len(re.findall(r"[a-zA-Z]+", text))
    other_chars = len(re.findall(r"[^\s]", text)) - chinese_chars - english_words * 3
    return chinese_chars + int(english_words * 1.3) + max(0, int(other_chars * 0.25))


def extract_keywords(text: str, min_length: int = 2) -> list:
    """简单关键词提取"""
    words = re.findall(r"[一-鿿㐀-䶿豈-﫿a-zA-Z]+", text)
    return [w for w in words if len(w) >= min_length]


def calculate_similarity(text1: str, text2: str) -> float:
    """Jaccard 相似度"""
    set1 = set(extract_keywords(text1))
    set2 = set(extract_keywords(text2))
    if not set1 or not set2:
        return 0.0
    intersection = set1 & set2
    union = set1 | set2
    return len(intersection) / len(union)


# ─── 上下文管理器 ──────────────────────────────────────────────────


class Timer:
    """上下文管理器：计时器"""

    def __init__(self, name: str = ""):
        self.name = name
        self.start_time = None
        self.elapsed = 0

    def __enter__(self):
        self.start_time = time.perf_counter()
        return self

    def __exit__(self, *args):
        self.elapsed = time.perf_counter() - self.start_time
        label = f" [{self.name}]" if self.name else ""
        logger.info(f"⏱ 耗时{label}: {self.elapsed:.2f}秒")
