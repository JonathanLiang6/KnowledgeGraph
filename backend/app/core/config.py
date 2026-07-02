"""
核心配置模块 - 所有配置从 .env 读取，前端不可见 API 密钥
v3.1: 安全的 env var 解析 + set 类型优化 + 版本号统一 + 占位符检测
"""

# 应用版本号 — 单一真实来源
APP_VERSION = "4.0.0"

# API 密钥占位符前缀 — 以此前缀开头的视为未配置
_API_KEY_PLACEHOLDER_PREFIX = "your-"
import os
import logging
from pathlib import Path
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

# 加载项目根目录的 .env 文件
BASE_DIR = Path(__file__).resolve().parent.parent.parent
load_dotenv(BASE_DIR / ".env")


def _safe_int(key: str, default: str) -> int:
    """安全解析 int 环境变量，格式错误时回退到默认值并警告"""
    val = os.getenv(key, default)
    try:
        return int(val)
    except (ValueError, TypeError):
        logger.warning(f"环境变量 {key}={val!r} 不是有效的整数，使用默认值 {default}")
        return int(default)


def _safe_float(key: str, default: str) -> float:
    """安全解析 float 环境变量，格式错误时回退到默认值并警告"""
    val = os.getenv(key, default)
    try:
        return float(val)
    except (ValueError, TypeError):
        logger.warning(f"环境变量 {key}={val!r} 不是有效的浮点数，使用默认值 {default}")
        return float(default)


class Config:
    """集中管理所有配置项，敏感信息仅从环境变量读取"""

    # ========================
    # 服务器配置
    # ========================
    SERVER_HOST: str = os.getenv("SERVER_HOST", "0.0.0.0")
    SERVER_PORT: int = _safe_int("SERVER_PORT", "8013")
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")

    # ========================
    # DeepSeek V4 API 配置
    # ========================
    DEEPSEEK_API_KEY: str = os.getenv("DEEPSEEK_API_KEY", "")
    DEEPSEEK_API_BASE: str = os.getenv("DEEPSEEK_API_BASE", "https://api.deepseek.com/v1")
    DEEPSEEK_CHAT_MODEL: str = os.getenv("DEEPSEEK_CHAT_MODEL", "deepseek-chat")

    # ========================
    # Embedding 模型配置 (本地 BGE)
    # ========================
    EMBEDDING_MODEL: str = os.getenv("EMBEDDING_MODEL", "BAAI/bge-small-zh-v1.5")
    EMBEDDING_DEVICE: str = os.getenv("EMBEDDING_DEVICE", "cpu")
    EMBEDDING_DIM: int = _safe_int("EMBEDDING_DIM", "512")
    EMBEDDING_BATCH_SIZE: int = _safe_int("EMBEDDING_BATCH_SIZE", "32")

    # ========================
    # Reranker 模型配置 (本地 BGE)
    # ========================
    RERANKER_MODEL: str = os.getenv("RERANKER_MODEL", "BAAI/bge-reranker-base")
    RERANKER_DEVICE: str = os.getenv("RERANKER_DEVICE", "cpu")

    # ========================
    # LLM 参数
    # ========================
    LLM_MAX_TOKENS: int = _safe_int("LLM_MAX_TOKENS", "4096")
    LLM_TEMPERATURE: float = _safe_float("LLM_TEMPERATURE", "0.0")
    LLM_MAX_RETRIES: int = _safe_int("LLM_MAX_RETRIES", "3")

    # ========================
    # 分块参数
    # ========================
    CHUNK_SIZE: int = _safe_int("CHUNK_SIZE", "800")
    CHUNK_OVERLAP: int = _safe_int("CHUNK_OVERLAP", "100")
    PARENT_CHUNK_SIZE: int = _safe_int("PARENT_CHUNK_SIZE", "1200")
    CHILD_CHUNK_SIZE: int = _safe_int("CHILD_CHUNK_SIZE", "300")

    # ========================
    # 文件上传限制 (P0 安全加固)
    # ========================
    MAX_FILE_SIZE_MB: int = _safe_int("MAX_FILE_SIZE_MB", "50")
    MAX_FILE_SIZE_BYTES: int = MAX_FILE_SIZE_MB * 1024 * 1024
    ALLOWED_MIME_TYPES: set = {
        "text/plain",
        "text/markdown",
        "text/x-markdown",
        "application/pdf",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "application/vnd.openxmlformats-officedocument.presentationml.presentation",
        "text/html",
        "application/epub+zip",
        "image/jpeg", "image/png", "image/webp",  # v3.2: Q3 多模态图像支持
    }
    ALLOWED_EXTENSIONS: set = {
        ".txt", ".md", ".markdown", ".pdf", ".docx", ".pptx", ".html", ".htm", ".epub",
        ".jpg", ".jpeg", ".png", ".webp",  # v3.2: Q3 多模态图像支持
    }
    # 是否启用文件去重（基于 SHA256）
    ENABLE_FILE_DEDUP: bool = os.getenv("ENABLE_FILE_DEDUP", "true").lower() == "true"

    # ========================
    # 并发控制 (P1 流水线重构)
    # ========================
    MAX_CONCURRENT_DOCUMENT_PROCESSING: int = _safe_int("MAX_CONCURRENT_DOC_PROCESSING", "3")
    DOCUMENT_PROCESSING_TIMEOUT_MINUTES: int = _safe_int("DOC_PROCESSING_TIMEOUT", "30")
    CPU_WORKER_THREADS: int = _safe_int("CPU_WORKER_THREADS", "2")

    # ========================
    # 检索引擎配置 (P2)
    # ========================
    LANCEDB_PATH: str = os.getenv("LANCEDB_PATH", str(BASE_DIR / "data" / "lancedb"))
    INDEX_PERSIST_INTERVAL: int = _safe_int("INDEX_PERSIST_INTERVAL", "0")
    BM25_INCREMENTAL_THRESHOLD: int = _safe_int("BM25_INCREMENTAL_THRESHOLD", "10")

    # ========================
    # GraphRAG Phase 1: 图检索与社区检测配置
    # ========================
    GRAPH_TRAVERSAL_MAX_HOPS: int = _safe_int("GRAPH_TRAVERSAL_MAX_HOPS", "3")
    GRAPH_TRAVERSAL_MAX_NODES: int = _safe_int("GRAPH_TRAVERSAL_MAX_NODES", "50")
    GRAPH_TRAVERSAL_STRATEGY: str = os.getenv("GRAPH_TRAVERSAL_STRATEGY", "bfs")
    GRAPH_COMMUNITY_MIN_SIZE: int = _safe_int("GRAPH_COMMUNITY_MIN_SIZE", "3")
    GRAPH_ENTITY_RESOLUTION_THRESHOLD: float = _safe_float("GRAPH_ENTITY_RESOLUTION_THRESHOLD", "0.85")
    GRAPH_GLOBAL_SEARCH_TOP_COMMUNITIES: int = _safe_int("GRAPH_GLOBAL_SEARCH_TOP_COMMUNITIES", "5")
    GRAPH_RETRIEVAL_WEIGHT: float = _safe_float("GRAPH_RETRIEVAL_WEIGHT", "0.3")

    # ========================
    # Phase 2: Agent 配置
    # ========================
    AGENT_MAX_STEPS: int = _safe_int("AGENT_MAX_STEPS", "6")
    AGENT_TEMPERATURE: float = _safe_float("AGENT_TEMPERATURE", "0.3")
    AGENT_MAX_TOKENS: int = _safe_int("AGENT_MAX_TOKENS", "2048")
    AGENT_MEMORY_MAX_TURNS: int = _safe_int("AGENT_MEMORY_MAX_TURNS", "5")

    # ========================
    # 数据配置
    # ========================
    DATA_DIR: str = os.getenv("DATA_DIR", str(BASE_DIR / "data"))
    LOCAL_DATA_DIR: str = os.getenv("LOCAL_DATA_DIR", str(BASE_DIR / "inputs" / "files"))
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL", f"sqlite+aiosqlite:///{BASE_DIR / 'data' / 'knowledge_graph.db'}"
    )

    # ========================
    # 检索配置
    # ========================
    HYBRID_SEARCH_TOP_K: int = _safe_int("HYBRID_SEARCH_TOP_K", "20")
    RERANK_TOP_K: int = _safe_int("RERANK_TOP_K", "5")
    BM25_WEIGHT: float = _safe_float("BM25_WEIGHT", "0.3")
    VECTOR_WEIGHT: float = _safe_float("VECTOR_WEIGHT", "0.7")

    # ========================
    # 知识图谱配置
    # ========================
    ENTITY_WEIGHT_THRESHOLD: float = _safe_float("ENTITY_WEIGHT_THRESHOLD", "0.02")
    MAX_ENTITIES: int = _safe_int("MAX_ENTITIES", "30")
    MAX_RELATIONSHIPS: int = _safe_int("MAX_RELATIONSHIPS", "40")
    BRIDGE_EDGE_DIVISOR: int = _safe_int("BRIDGE_EDGE_DIVISOR", "3")
    BRIDGE_MIN_SIMILARITY: float = _safe_float("BRIDGE_MIN_SIMILARITY", "0.15")

    # ========================
    # RAG 增强配置 (v2.2)
    # ========================
    ENABLE_QUERY_REWRITING: bool = os.getenv("ENABLE_QUERY_REWRITING", "false").lower() == "true"
    ENABLE_GRAPH_RAG: bool = os.getenv("ENABLE_GRAPH_RAG", "true").lower() == "true"
    GRAPH_RAG_EXPAND_ENTITIES: int = _safe_int("GRAPH_RAG_EXPAND_ENTITIES", "3")
    SEARCH_CACHE_SIZE: int = _safe_int("SEARCH_CACHE_SIZE", "128")
    SEARCH_CACHE_TTL: int = _safe_int("SEARCH_CACHE_TTL", "60")
    CONTEXT_MAX_SOURCES: int = _safe_int("CONTEXT_MAX_SOURCES", "8")

    @property
    def is_api_key_set(self) -> bool:
        """检查 DeepSeek API 密钥是否已配置（前缀匹配占位符）"""
        return bool(
            self.DEEPSEEK_API_KEY
            and not self.DEEPSEEK_API_KEY.startswith(_API_KEY_PLACEHOLDER_PREFIX)
            and len(self.DEEPSEEK_API_KEY) > 10
        )

    def get_api_config(self) -> dict:
        """获取 API 配置（仅供后端使用，不暴露给前端）"""
        return {
            "api_base": self.DEEPSEEK_API_BASE,
            "api_key_masked": self._mask_key(self.DEEPSEEK_API_KEY),
            "chat_model": self.DEEPSEEK_CHAT_MODEL,
            "embedding_model": self.EMBEDDING_MODEL,
        }

    @staticmethod
    def _mask_key(key: str) -> str:
        """遮盖密钥显示，仅显示前后各 4 位"""
        if not key or len(key) < 8:
            return "***"
        return key[:4] + "*" * (len(key) - 8) + key[-4:]


# 全局配置单例
config = Config()
