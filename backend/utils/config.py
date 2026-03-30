"""
知识图谱系统配置文件
包含所有系统配置参数和环境变量设置
"""

import os
from dataclasses import dataclass
from typing import Optional
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()


@dataclass
class Neo4jConfig:
    """Neo4j图数据库配置类"""
    uri: str = "bolt://localhost:7687"          # 数据库连接地址
    username: str = "neo4j"                      # 用户名
    password: str = "password"                   # 密码
    database: str = "neo4j"                      # 数据库名称
    batch_size: int = 1000                       # 批量导入批次大小


@dataclass
class LLMConfig:
    """大语言模型配置类"""
    api_base: str = "https://open.bigmodel.cn/api/paas/v4"   # 智谱AI API基础地址
    api_key: str = "17784fc5c5c440d090f268a31ae5359c.Ddl2iFE5IQnt5cUW"                # API密钥
    chat_model: str = "glm-4-flash"               # 对话模型名称
    embedding_model: str = "embedding-2"         # 嵌入模型名称
    max_tokens: int = 2000                       # 最大token数
    temperature: float = 0.0                     # 温度参数
    max_retries: int = 10                        # 最大重试次数


@dataclass
class GraphRAGConfig:
    """GraphRAG索引配置类"""
    input_dir: str = "input"                     # 输入目录
    cache_dir: str = "cache"                     # 缓存目录
    storage_dir: str = "inputs/artifacts"        # 存储目录
    reporting_dir: str = "inputs/reports"        # 报告目录
    prompts_dir: str = "prompts"                 # 提示词目录
    community_level: int = 2                     # 社区层级
    chunk_size: int = 800                        # 文本块大小
    chunk_overlap: int = 100                     # 文本块重叠大小


@dataclass
class ServerConfig:
    """FastAPI服务配置类"""
    host: str = "0.0.0.0"                        # 服务地址
    port: int = 8012                             # 服务端口
    log_level: str = "INFO"                      # 日志级别


class Config:
    """系统主配置类"""
    
    def __init__(self):
        # Neo4j配置
        self.neo4j = Neo4jConfig(
            uri=os.getenv("NEO4J_URI", "bolt://localhost:7687"),
            username=os.getenv("NEO4J_USERNAME", "neo4j"),
            password=os.getenv("NEO4J_PASSWORD", "password"),
            database=os.getenv("NEO4J_DATABASE", "neo4j"),
            batch_size=int(os.getenv("NEO4J_BATCH_SIZE", "1000"))
        )
        
        # LLM配置
        self.llm = LLMConfig(
            api_base=os.getenv("GRAPHRAG_API_BASE", "https://open.bigmodel.cn/api/paas/v4"),
            api_key=os.getenv("GRAPHRAG_CHAT_API_KEY", "your-api-key"),
            chat_model=os.getenv("GRAPHRAG_CHAT_MODEL", "glm-4-flash"),
            embedding_model=os.getenv("GRAPHRAG_EMBEDDING_MODEL", "embedding-2"),
            max_tokens=int(os.getenv("LLM_MAX_TOKENS", "2000")),
            temperature=float(os.getenv("LLM_TEMPERATURE", "0.0")),
            max_retries=int(os.getenv("LLM_MAX_RETRIES", "20"))
        )
        
        # GraphRAG配置
        self.graphrag = GraphRAGConfig(
            input_dir=os.getenv("GRAPHRAG_INPUT_DIR", "input"),
            cache_dir=os.getenv("GRAPHRAG_CACHE_DIR", "cache"),
            storage_dir=os.getenv("GRAPHRAG_STORAGE_DIR", "inputs/artifacts"),
            reporting_dir=os.getenv("GRAPHRAG_REPORTING_DIR", "inputs/reports"),
            prompts_dir=os.getenv("GRAPHRAG_PROMPTS_DIR", "prompts"),
            community_level=int(os.getenv("COMMUNITY_LEVEL", "2")),
            chunk_size=int(os.getenv("CHUNK_SIZE", "800")),
            chunk_overlap=int(os.getenv("CHUNK_OVERLAP", "100"))
        )
        
        # 服务配置
        self.server = ServerConfig(
            host=os.getenv("SERVER_HOST", "0.0.0.0"),
            port=int(os.getenv("SERVER_PORT", "8012")),
            log_level=os.getenv("LOG_LEVEL", "INFO")
        )
        
        # 计算派生路径
        self.lancedb_uri = f"{self.graphrag.storage_dir}/lancedb"
        
    def get_artifact_path(self, filename: str) -> str:
        """获取知识图谱数据文件路径"""
        return os.path.join(self.graphrag.storage_dir, filename)


# 全局配置实例
config = Config()
