"""
通用工具函数 - 迁移自原 utils/helpers.py
"""
import hashlib
import re
import json
import os
import time
import logging
from pathlib import Path
from typing import Optional, Any

logger = logging.getLogger(__name__)


def generate_id(text: str, prefix: str = "") -> str:
    """基于文本生成 MD5 唯一 ID"""
    hash_obj = hashlib.md5(text.encode("utf-8"))
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
    """简单关键词提取"""
    words = re.findall(r"[一-龥a-zA-Z]+", text)
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
    """安全读取文件"""
    try:
        with open(filepath, "r", encoding=encoding) as f:
            return f.read()
    except (FileNotFoundError, PermissionError, UnicodeDecodeError) as e:
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
    """估算 token 数量（英文单词 + 中文字符）"""
    chinese_chars = len(re.findall(r"[一-龥]", text))
    english_words = len(re.findall(r"[a-zA-Z]+", text))
    # 中文字符 ≈ 1 token，英文单词 ≈ 1.3 token
    return chinese_chars + int(english_words * 1.3)


def mask_sensitive_info(text: str, mask: str = "****") -> str:
    """遮盖 API key 等敏感信息"""
    return re.sub(
        r'(api[_-]?key|secret|token|password)["\s:=]+(["\']?)([^\s"\'&]+)',
        rf"\1\2{mask}",
        text,
        flags=re.IGNORECASE,
    )


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
