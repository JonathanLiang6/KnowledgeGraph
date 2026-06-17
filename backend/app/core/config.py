"""
核心配置模块 - 所有配置从 .env 读取，前端不可见 API 密钥
"""
import os
from pathlib import Path
from dotenv import load_dotenv

# 加载项目根目录的 .env 文件
BASE_DIR = Path(__file__).resolve().parent.parent.parent
load_dotenv(BASE_DIR / ".env")


class Config:
    """集中管理所有配置项，敏感信息仅从环境变量读取"""

    # ========================
    # 服务器配置
    # ========================
    SERVER_HOST: str = os.getenv("SERVER_HOST", "0.0.0.0")
    SERVER_PORT: int = int(os.getenv("SERVER_PORT", "8013"))
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
    EMBEDDING_DIM: int = int(os.getenv("EMBEDDING_DIM", "512"))

    # ========================
    # Reranker 模型配置 (本地 BGE)
    # ========================
    RERANKER_MODEL: str = os.getenv("RERANKER_MODEL", "BAAI/bge-reranker-base")
    RERANKER_DEVICE: str = os.getenv("RERANKER_DEVICE", "cpu")

    # ========================
    # LLM 参数
    # ========================
    LLM_MAX_TOKENS: int = int(os.getenv("LLM_MAX_TOKENS", "4096"))
    LLM_TEMPERATURE: float = float(os.getenv("LLM_TEMPERATURE", "0.0"))
    LLM_MAX_RETRIES: int = int(os.getenv("LLM_MAX_RETRIES", "3"))

    # ========================
    # GraphRAG 配置
    # ========================
    GRAPHRAG_INPUT_DIR: str = os.getenv("GRAPHRAG_INPUT_DIR", "input")
    GRAPHRAG_CACHE_DIR: str = os.getenv("GRAPHRAG_CACHE_DIR", "cache")
    GRAPHRAG_STORAGE_DIR: str = os.getenv("GRAPHRAG_STORAGE_DIR", "inputs/artifacts")
    GRAPHRAG_REPORTING_DIR: str = os.getenv("GRAPHRAG_REPORTING_DIR", "inputs/reports")
    GRAPHRAG_PROMPTS_DIR: str = os.getenv("GRAPHRAG_PROMPTS_DIR", "prompts")
    COMMUNITY_LEVEL: int = int(os.getenv("COMMUNITY_LEVEL", "2"))

    # ========================
    # 分块参数（优化：更小块 = 更快嵌入）
    # ========================
    CHUNK_SIZE: int = int(os.getenv("CHUNK_SIZE", "800"))
    CHUNK_OVERLAP: int = int(os.getenv("CHUNK_OVERLAP", "50"))
    PARENT_CHUNK_SIZE: int = int(os.getenv("PARENT_CHUNK_SIZE", "800"))
    CHILD_CHUNK_SIZE: int = int(os.getenv("CHILD_CHUNK_SIZE", "200"))

    # ========================
    # 提示词文件路径
    # ========================
    PROMPT_ENTITY_EXTRACTION: str = os.getenv(
        "GRAPHRAG_ENTITY_EXTRACTION_PROMPT_FILE", "prompts/entity_extraction.txt"
    )
    PROMPT_SUMMARIZE_DESCRIPTIONS: str = os.getenv(
        "GRAPHRAG_SUMMARIZE_DESCRIPTIONS_PROMPT_FILE", "prompts/summarize_descriptions.txt"
    )
    PROMPT_CLAIM_EXTRACTION: str = os.getenv(
        "GRAPHRAG_CLAIM_EXTRACTION_PROMPT_FILE", "prompts/claim_extraction.txt"
    )
    PROMPT_COMMUNITY_REPORT: str = os.getenv(
        "GRAPHRAG_COMMUNITY_REPORT_PROMPT_FILE", "prompts/community_report.txt"
    )

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
    HYBRID_SEARCH_TOP_K: int = int(os.getenv("HYBRID_SEARCH_TOP_K", "20"))
    RERANK_TOP_K: int = int(os.getenv("RERANK_TOP_K", "5"))
    BM25_WEIGHT: float = float(os.getenv("BM25_WEIGHT", "0.3"))
    VECTOR_WEIGHT: float = float(os.getenv("VECTOR_WEIGHT", "0.7"))

    # ========================
    # 知识图谱配置（优化：减少实体数加速处理）
    # ========================
    ENTITY_WEIGHT_THRESHOLD: float = float(os.getenv("ENTITY_WEIGHT_THRESHOLD", "0.02"))
    MAX_ENTITIES: int = int(os.getenv("MAX_ENTITIES", "30"))
    MAX_RELATIONSHIPS: int = int(os.getenv("MAX_RELATIONSHIPS", "40"))

    @property
    def is_api_key_set(self) -> bool:
        """检查 DeepSeek API 密钥是否已配置"""
        return bool(self.DEEPSEEK_API_KEY and self.DEEPSEEK_API_KEY != "your-api-key-here")

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
