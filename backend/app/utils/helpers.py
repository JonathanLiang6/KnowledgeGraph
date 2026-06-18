"""
通用工具函数 - 文件安全、去重、流式 I/O、格式化
"""
import hashlib
import re
import json
import os
import time
import logging
from pathlib import Path
from typing import Optional, Any, Tuple, Generator

logger = logging.getLogger(__name__)

# ─── 安全/校验工具 (P0) ───────────────────────────────────────────


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
    # 1. 尝试用 filetype 库（轻量级 magic bytes）
    try:
        import filetype
        kind = filetype.guess(filepath)
        if kind is not None:
            return kind.mime
    except ImportError:
        pass

    # 2. 回退：通过前 8 字节 magic bytes 手动检测
    try:
        with open(filepath, "rb") as f:
            header = f.read(8)
    except OSError:
        return "application/octet-stream"

    if header[:4] == b"%PDF":
        return "application/pdf"
    if header[:4] == b"PK\x03\x04":
        # ZIP-based: DOCX, PPTX are ZIP archives — further check filenames
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

    # 3. 文本类型：尝试 UTF-8 解码前几个字节
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


def find_duplicate_file(filepath: str) -> Optional[str]:
    """
    在 LOCAL_DATA_DIR 中查找内容哈希相同的文件。
    仅做哈希匹配，不检查 DB 记录（由调用方负责验证）。
    返回已存在文件的路径，无匹配返回 None。
    """
    from app.core.config import config

    target_hash = compute_file_hash(filepath)
    local_dir = Path(config.LOCAL_DATA_DIR)

    if not local_dir.exists():
        return None

    for existing in local_dir.iterdir():
        if not existing.is_file():
            continue
        try:
            if existing.samefile(Path(filepath)):
                continue  # 跳过自身
        except OSError:
            pass
        try:
            if compute_file_hash(str(existing)) == target_hash:
                return str(existing)
        except OSError:
            continue
    return None


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


def read_file_stream(filepath: str, chunk_size: int = 64 * 1024) -> Generator[bytes, None, None]:
    """流式读取文件，用于大文件处理"""
    with open(filepath, "rb") as f:
        for chunk in iter(lambda: f.read(chunk_size), b""):
            yield chunk


# ─── 基础工具（保留原有）───────────────────────────────────────────


def generate_id(text: str, prefix: str = "") -> str:
    """基于文本生成 SHA256 唯一 ID (v2.4: SHA256 替代 MD5)"""
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


def format_datetime(dt, fmt: str = "%Y-%m-%d %H:%M:%S") -> str:
    """格式化日期时间"""
    if dt is None:
        return ""
    return dt.strftime(fmt)


def parse_json_safe(text: str, default: Any = None) -> Any:
    """安全解析 JSON 字符串"""
    try:
        return json.loads(text)
    except (json.JSONDecodeError, TypeError):
        return default


def merge_dicts(base: dict, override: dict) -> dict:
    """递归合并两个字典"""
    result = base.copy()
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = merge_dicts(result[key], value)
        else:
            result[key] = value
    return result


def chunk_list(items: list, chunk_size: int) -> list:
    """将列表按固定大小分块"""
    return [items[i : i + chunk_size] for i in range(0, len(items), chunk_size)]


def flatten_list(nested_list: list) -> list:
    """展平嵌套列表"""
    result = []
    for item in nested_list:
        if isinstance(item, list):
            result.extend(flatten_list(item))
        else:
            result.append(item)
    return result


def remove_duplicates_preserve_order(items: list) -> list:
    """去重并保持顺序"""
    seen = set()
    result = []
    for item in items:
        if item not in seen:
            seen.add(item)
            result.append(item)
    return result


def extract_keywords(text: str, min_length: int = 2) -> list:
    """简单关键词提取 (v2.4: 扩展CJK范围)"""
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


def ensure_dir(path: str):
    """确保目录存在"""
    Path(path).mkdir(parents=True, exist_ok=True)


def read_file_safe(filepath: str, encoding: str = "utf-8", default: str = "") -> str:
    """安全读取文件（支持编码自动检测）"""
    try:
        with open(filepath, "r", encoding=encoding) as f:
            return f.read()
    except UnicodeDecodeError:
        # 回退到常见编码
        for enc in ["gbk", "gb2312", "gb18030", "latin-1"]:
            try:
                with open(filepath, "r", encoding=enc) as f:
                    logger.info(f"文件 {filepath} 使用编码 {enc} 读取成功")
                    return f.read()
            except UnicodeDecodeError:
                continue
        logger.warning(f"无法解码文件: {filepath}")
        return default
    except (FileNotFoundError, PermissionError) as e:
        logger.warning(f"读取文件失败: {filepath}, 错误: {e}")
        return default


def write_file_safe(filepath: str, content: str, encoding: str = "utf-8"):
    """安全写入文件"""
    try:
        ensure_dir(os.path.dirname(filepath))
        with open(filepath, "w", encoding=encoding) as f:
            f.write(content)
    except (PermissionError, OSError) as e:
        logger.error(f"写入文件失败: {filepath}, 错误: {e}")
        raise


def format_file_size(size_bytes: int) -> str:
    """格式化文件大小"""
    for unit in ["B", "KB", "MB", "GB"]:
        if size_bytes < 1024:
            return f"{size_bytes:.1f} {unit}" if unit != "B" else f"{size_bytes} B"
        size_bytes /= 1024
    return f"{size_bytes:.1f} TB"


def count_tokens_approximate(text: str) -> int:
    """估算 token 数量 (v2.4: 扩展CJK + 非空白字符兜底)"""
    chinese_chars = len(re.findall(r"[一-鿿㐀-䶿豈-﫿]", text))
    english_words = len(re.findall(r"[a-zA-Z]+", text))
    # 剩余非空白字符（数字、标点等）
    other_chars = len(re.findall(r"[^\s]", text)) - chinese_chars - english_words * 3
    # 中文字符 ≈ 1 token, 英文单词 ≈ 1.3 token, 其他 ≈ 0.25 token/char
    return chinese_chars + int(english_words * 1.3) + max(0, int(other_chars * 0.25))


def mask_sensitive_info(text: str, mask: str = "****") -> str:
    """遮盖 API key 等敏感信息"""
    return re.sub(
        r'(api[_-]?key|secret|token|password)["\s:=]+(["\']?)([^\s"\'&]+)',
        rf"\1\2{mask}",
        text,
        flags=re.IGNORECASE,
    )


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


class ProgressTracker:
    """进度跟踪器"""

    def __init__(self, total: int, label: str = ""):
        self.total = total
        self.current = 0
        self.label = label
        self.start_time = time.perf_counter()

    def update(self, n: int = 1):
        """更新进度"""
        self.current += n
        elapsed = time.perf_counter() - self.start_time
        pct = (self.current / self.total) * 100 if self.total > 0 else 100
        eta = (elapsed / self.current) * (self.total - self.current) if self.current > 0 else 0
        label = f" [{self.label}]" if self.label else ""
        logger.info(
            f"📊 进度{label}: {self.current}/{self.total} ({pct:.1f}%) "
            f"| 用时: {elapsed:.1f}s | 预计剩余: {eta:.1f}s"
        )
