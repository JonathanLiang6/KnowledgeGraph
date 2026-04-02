import os
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()


class Config:
    """
    配置类，用于管理所有配置项
    """
    # 服务器配置
    SERVER_HOST = os.getenv('SERVER_HOST', '0.0.0.0')
    SERVER_PORT = int(os.getenv('SERVER_PORT', '8012'))
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
    
    # 智谱AI API配置
    GRAPHRAG_API_BASE = os.getenv('GRAPHRAG_API_BASE', 'https://open.bigmodel.cn/api/paas/v4')
    GRAPHRAG_CHAT_API_KEY = os.getenv('GRAPHRAG_CHAT_API_KEY', '')
    GRAPHRAG_EMBEDDING_API_KEY = os.getenv('GRAPHRAG_EMBEDDING_API_KEY', '')
    GRAPHRAG_CHAT_MODEL = os.getenv('GRAPHRAG_CHAT_MODEL', 'glm-4-flash')
    GRAPHRAG_EMBEDDING_MODEL = os.getenv('GRAPHRAG_EMBEDDING_MODEL', 'embedding-2')
    
    # LLM参数
    LLM_MAX_TOKENS = int(os.getenv('LLM_MAX_TOKENS', '2000'))
    LLM_TEMPERATURE = float(os.getenv('LLM_TEMPERATURE', '0.0'))
    LLM_MAX_RETRIES = int(os.getenv('LLM_MAX_RETRIES', '20'))
    
    # GraphRAG配置
    GRAPHRAG_INPUT_DIR = os.getenv('GRAPHRAG_INPUT_DIR', 'input')
    GRAPHRAG_CACHE_DIR = os.getenv('GRAPHRAG_CACHE_DIR', 'cache')
    GRAPHRAG_STORAGE_DIR = os.getenv('GRAPHRAG_STORAGE_DIR', 'inputs/artifacts')
    GRAPHRAG_REPORTING_DIR = os.getenv('GRAPHRAG_REPORTING_DIR', 'inputs/reports')
    GRAPHRAG_PROMPTS_DIR = os.getenv('GRAPHRAG_PROMPTS_DIR', 'prompts')
    COMMUNITY_LEVEL = int(os.getenv('COMMUNITY_LEVEL', '2'))
    CHUNK_SIZE = int(os.getenv('CHUNK_SIZE', '800'))
    CHUNK_OVERLAP = int(os.getenv('CHUNK_OVERLAP', '100'))
    
    # 提示词文件配置
    GRAPHRAG_ENTITY_EXTRACTION_PROMPT_FILE = os.getenv('GRAPHRAG_ENTITY_EXTRACTION_PROMPT_FILE', 'prompts/entity_extraction.txt')
    GRAPHRAG_SUMMARIZE_DESCRIPTIONS_PROMPT_FILE = os.getenv('GRAPHRAG_SUMMARIZE_DESCRIPTIONS_PROMPT_FILE', 'prompts/summarize_descriptions.txt')
    GRAPHRAG_CLAIM_EXTRACTION_PROMPT_FILE = os.getenv('GRAPHRAG_CLAIM_EXTRACTION_PROMPT_FILE', 'prompts/claim_extraction.txt')
    GRAPHRAG_COMMUNITY_REPORT_PROMPT_FILE = os.getenv('GRAPHRAG_COMMUNITY_REPORT_PROMPT_FILE', 'prompts/community_report.txt')
    
    # 数据文件配置
    COMMUNITY_REPORT_TABLE = 'create_final_community_reports'
    ENTITY_TABLE = 'create_final_nodes'
    RELATIONSHIP_TABLE = 'create_final_relationships'
    COVARIATE_TABLE = 'create_final_covariates'
    TEXT_UNIT_TABLE = 'create_final_text_units'
    
    @property
    def is_api_key_set(self):
        """
        检查API密钥是否已设置
        """
        return bool(self.GRAPHRAG_CHAT_API_KEY and self.GRAPHRAG_EMBEDDING_API_KEY)
    
    def get_api_config(self):
        """
        获取API配置
        """
        return {
            'api_base': self.GRAPHRAG_API_BASE,
            'chat_api_key': self.GRAPHRAG_CHAT_API_KEY,
            'embedding_api_key': self.GRAPHRAG_EMBEDDING_API_KEY,
            'chat_model': self.GRAPHRAG_CHAT_MODEL,
            'embedding_model': self.GRAPHRAG_EMBEDDING_MODEL
        }


# 创建配置实例
config = Config()
