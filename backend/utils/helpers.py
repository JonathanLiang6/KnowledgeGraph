"""
知识图谱系统工具函数模块
提供通用的辅助功能和工具函数
"""

import os
import re
import json
import hashlib
from typing import List, Dict, Any, Optional, Union
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


def generate_id(text: str, prefix: str = "") -> str:
    """
    基于文本内容生成唯一ID
    
    参数:
        text: 输入文本
        prefix: ID前缀
        
    返回:
        生成的唯一ID
    """
    hash_obj = hashlib.md5(text.encode('utf-8'))
    hash_hex = hash_obj.hexdigest()[:12]
    return f"{prefix}_{hash_hex}" if prefix else hash_hex


def sanitize_filename(filename: str) -> str:
    """
    清理文件名，移除非法字符
    
    参数:
        filename: 原始文件名
        
    返回:
        清理后的文件名
    """
    # 移除或替换非法字符
    sanitized = re.sub(r'[<>:"/\\|?*]', '_', filename)
    # 限制长度
    if len(sanitized) > 200:
        name, ext = os.path.splitext(sanitized)
        sanitized = name[:200 - len(ext)] + ext
    return sanitized


def truncate_text(text: str, max_length: int = 100, suffix: str = "...") -> str:
    """
    截断文本到指定长度
    
    参数:
        text: 原始文本
        max_length: 最大长度
        suffix: 截断后缀
        
    返回:
        截断后的文本
    """
    if len(text) <= max_length:
        return text
    return text[:max_length - len(suffix)] + suffix


def format_datetime(dt: Optional[datetime] = None, fmt: str = "%Y-%m-%d %H:%M:%S") -> str:
    """
    格式化日期时间
    
    参数:
        dt: 日期时间对象，默认为当前时间
        fmt: 格式字符串
        
    返回:
        格式化后的时间字符串
    """
    if dt is None:
        dt = datetime.now()
    return dt.strftime(fmt)


def parse_json_safe(text: str, default: Any = None) -> Any:
    """
    安全地解析JSON字符串
    
    参数:
        text: JSON字符串
        default: 解析失败时的默认值
        
    返回:
        解析后的对象或默认值
    """
    try:
        return json.loads(text)
    except (json.JSONDecodeError, TypeError) as e:
        logger.warning(f"JSON解析失败: {e}")
        return default


def merge_dicts(base: Dict, override: Dict) -> Dict:
    """
    递归合并两个字典
    
    参数:
        base: 基础字典
        override: 覆盖字典
        
    返回:
        合并后的字典
    """
    result = base.copy()
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = merge_dicts(result[key], value)
        else:
            result[key] = value
    return result


def chunk_list(items: List, chunk_size: int) -> List[List]:
    """
    将列表分块
    
    参数:
        items: 原始列表
        chunk_size: 每块大小
        
    返回:
        分块后的列表
    """
    return [items[i:i + chunk_size] for i in range(0, len(items), chunk_size)]


def flatten_list(nested_list: List) -> List:
    """
    展平嵌套列表
    
    参数:
        nested_list: 嵌套列表
        
    返回:
        展平后的列表
    """
    result = []
    for item in nested_list:
        if isinstance(item, list):
            result.extend(flatten_list(item))
        else:
            result.append(item)
    return result


def remove_duplicates_preserve_order(items: List) -> List:
    """
    移除列表中的重复项，保持原有顺序
    
    参数:
        items: 原始列表
        
    返回:
        去重后的列表
    """
    seen = set()
    result = []
    for item in items:
        if item not in seen:
            seen.add(item)
            result.append(item)
    return result


def extract_keywords(text: str, min_length: int = 2) -> List[str]:
    """
    从文本中提取关键词（简单实现）
    
    参数:
        text: 输入文本
        min_length: 最小关键词长度
        
    返回:
        关键词列表
    """
    # 移除标点符号，分割成单词
    words = re.findall(r'\b\w+\b', text.lower())
    # 过滤短词和常见停用词
    stopwords = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by'}
    keywords = [w for w in words if len(w) >= min_length and w not in stopwords]
    return remove_duplicates_preserve_order(keywords)


def calculate_similarity(text1: str, text2: str) -> float:
    """
    计算两个文本的相似度（基于词集合的简单Jaccard相似度）
    
    参数:
        text1: 第一个文本
        text2: 第二个文本
        
    返回:
        相似度分数（0-1之间）
    """
    set1 = set(text1.lower().split())
    set2 = set(text2.lower().split())
    
    if not set1 or not set2:
        return 0.0
    
    intersection = len(set1 & set2)
    union = len(set1 | set2)
    
    return intersection / union if union > 0 else 0.0


def ensure_dir(path: str) -> str:
    """
    确保目录存在，不存在则创建
    
    参数:
        path: 目录路径
        
    返回:
        目录路径
    """
    if not os.path.exists(path):
        os.makedirs(path, exist_ok=True)
        logger.info(f"创建目录: {path}")
    return path


def read_file_safe(filepath: str, encoding: str = 'utf-8', default: str = "") -> str:
    """
    安全地读取文件内容
    
    参数:
        filepath: 文件路径
        encoding: 文件编码
        default: 读取失败时的默认值
        
    返回:
        文件内容或默认值
    """
    try:
        with open(filepath, 'r', encoding=encoding) as f:
            return f.read()
    except Exception as e:
        logger.warning(f"读取文件失败 {filepath}: {e}")
        return default


def write_file_safe(filepath: str, content: str, encoding: str = 'utf-8') -> bool:
    """
    安全地写入文件内容
    
    参数:
        filepath: 文件路径
        content: 文件内容
        encoding: 文件编码
        
    返回:
        是否写入成功
    """
    try:
        # 确保父目录存在
        parent_dir = os.path.dirname(filepath)
        if parent_dir:
            ensure_dir(parent_dir)
        
        with open(filepath, 'w', encoding=encoding) as f:
            f.write(content)
        return True
    except Exception as e:
        logger.error(f"写入文件失败 {filepath}: {e}")
        return False


def format_file_size(size_bytes: int) -> str:
    """
    格式化文件大小显示
    
    参数:
        size_bytes: 字节数
        
    返回:
        格式化后的大小字符串
    """
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.2f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.2f} PB"


def count_tokens_approximate(text: str) -> int:
    """
    近似计算文本的token数量（简单估算）
    
    参数:
        text: 输入文本
        
    返回:
        估算的token数量
    """
    # 简单的估算：英文单词数 + 中文字符数
    english_words = len(re.findall(r'\b\w+\b', text))
    chinese_chars = len(re.findall(r'[\u4e00-\u9fff]', text))
    return english_words + chinese_chars


class Timer:
    """
    计时器上下文管理器
    用于测量代码块执行时间
    
    示例:
        with Timer("数据处理"):
            process_data()
    """
    
    def __init__(self, name: str = "操作", logger_instance: Optional[logging.Logger] = None):
        self.name = name
        self.logger = logger_instance or logger
        self.start_time = None
        self.end_time = None
        
    def __enter__(self):
        self.start_time = time.time()
        return self
        
    def __exit__(self, *args):
        self.end_time = time.time()
        elapsed = self.end_time - self.start_time
        self.logger.info(f"{self.name} 耗时: {elapsed:.3f}秒")
        
    @property
    def elapsed(self) -> float:
        """获取已过去的时间"""
        if self.end_time:
            return self.end_time - self.start_time
        return time.time() - self.start_time if self.start_time else 0


class ProgressTracker:
    """
    进度追踪器
    用于显示长时间运行的任务进度
    
    示例:
        tracker = ProgressTracker(total=100, label="处理中")
        for i in range(100):
            tracker.update(1)
    """
    
    def __init__(self, total: int, label: str = "进度", log_interval: int = 10):
        self.total = total
        self.current = 0
        self.label = label
        self.log_interval = log_interval
        self.start_time = time.time()
        
    def update(self, increment: int = 1):
        """更新进度"""
        self.current += increment
        percentage = (self.current / self.total) * 100
        
        if self.current % self.log_interval == 0 or self.current >= self.total:
            elapsed = time.time() - self.start_time
            rate = self.current / elapsed if elapsed > 0 else 0
            remaining = (self.total - self.current) / rate if rate > 0 else 0
            
            logger.info(
                f"{self.label}: {self.current}/{self.total} "
                f"({percentage:.1f}%) - "
                f"速率: {rate:.1f}项/秒 - "
                f"预计剩余: {remaining:.1f}秒"
            )
            
    def finish(self):
        """完成进度"""
        elapsed = time.time() - self.start_time
        logger.info(f"{self.label} 完成: 共处理{self.total}项，总耗时{elapsed:.2f}秒")


def validate_config(config_dict: Dict[str, Any], required_keys: List[str]) -> List[str]:
    """
    验证配置字典是否包含必需的键
    
    参数:
        config_dict: 配置字典
        required_keys: 必需的键列表
        
    返回:
        缺失的键列表
    """
    missing = [key for key in required_keys if key not in config_dict or config_dict[key] is None]
    return missing


def mask_sensitive_info(text: str, mask: str = "***") -> str:
    """
    遮盖敏感信息（如API密钥）
    
    参数:
        text: 原始文本
        mask: 遮盖字符串
        
    返回:
        处理后的文本
    """
    # 遮盖API密钥模式
    patterns = [
        (r'sk-[a-zA-Z0-9]{20,}', f'sk-{mask}'),
        (r'api[_-]?key["\']?\s*[:=]\s*["\']?[a-zA-Z0-9]{10,}', f'api_key={mask}'),
    ]
    
    result = text
    for pattern, replacement in patterns:
        result = re.sub(pattern, replacement, result, flags=re.IGNORECASE)
    
    return result


# 导入time模块用于Timer类
import time
