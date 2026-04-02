#!/usr/bin/env python3
"""
启动知识图谱服务的简化脚本
"""
import os
import sys
import logging

# 设置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def check_env_file():
    """
    检查.env文件是否存在，并提示用户配置API密钥
    """
    env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '.env')
    
    if not os.path.exists(env_path):
        logger.error(f"未找到 .env 文件，请在 {env_path} 创建配置文件")
        logger.info("示例 .env 文件内容:")
        logger.info("""
# 智谱AI API配置
GRAPHRAG_API_BASE=https://open.bigmodel.cn/api/paas/v4
GRAPHRAG_CHAT_API_KEY=your-api-key-here
GRAPHRAG_EMBEDDING_API_KEY=your-api-key-here
GRAPHRAG_CHAT_MODEL=glm-4-flash
GRAPHRAG_EMBEDDING_MODEL=embedding-2
        """)
        return False
    
    # 检查API密钥是否已设置
    with open(env_path, 'r', encoding='utf-8') as f:
        content = f.read()
        
    if 'your-api-key-here' in content:
        logger.error("API密钥未设置，请在 .env 文件中替换 'your-api-key-here' 为实际的API密钥")
        return False
    
    return True


def check_requirements():
    """
    检查依赖是否已安装
    """
    try:
        import graphrag
        import fastapi
        import uvicorn
        import pandas
        import dotenv
        logger.info("所有依赖已安装")
        return True
    except ImportError as e:
        logger.error(f"缺少依赖: {e}")
        logger.info("请运行: pip install -r requirements.txt")
        return False


def start_server():
    """
    启动服务器
    """
    # 检查环境文件
    if not check_env_file():
        return
    
    # 检查依赖
    if not check_requirements():
        return
    
    # 启动服务器
    try:
        from utils.main import app
        import uvicorn
        from utils.config import config as app_config
        
        logger.info(f"启动知识图谱服务...")
        logger.info(f"服务地址: http://{app_config.SERVER_HOST}:{app_config.SERVER_PORT}")
        logger.info(f"API接口: http://{app_config.SERVER_HOST}:{app_config.SERVER_PORT}/v1/chat/completions")
        
        uvicorn.run(
            "utils.main:app",
            host=app_config.SERVER_HOST,
            port=app_config.SERVER_PORT,
            log_level=app_config.LOG_LEVEL.lower()
        )
    except Exception as e:
        logger.error(f"启动服务器失败: {str(e)}")
        return


if __name__ == "__main__":
    start_server()
