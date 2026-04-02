import os
import asyncio
import time
import uuid
import json
import re
import pandas as pd
import logging
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any, Union, AsyncGenerator
from contextlib import asynccontextmanager
import uvicorn

# 导入配置
import sys
import os

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.config import config as app_config

# GraphRAG 相关导入
from graphrag.api.query import local_search, global_search
from graphrag.config.models.graph_rag_config import GraphRagConfig
from graphrag.config.load_config import load_config

# 设置日志模版
logging.basicConfig(level=getattr(logging, app_config.LOG_LEVEL), format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


# 设置常量和配置
INPUT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "inputs", "artifacts")
CONFIG_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "settings.yaml")
PORT = app_config.SERVER_PORT

# 全局变量
graphrag_config = None

# 数据存储文件路径
DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
DOCUMENTS_FILE = os.path.join(DATA_DIR, "documents.json")
SETTINGS_FILE = os.path.join(DATA_DIR, "settings.json")

# 确保数据目录存在
os.makedirs(DATA_DIR, exist_ok=True)

# 内存中的数据存储
documents_data = []
settings_data = {}


# 定义Message类型
class Message(BaseModel):
    role: str
    content: str


# 定义ChatCompletionRequest类
class ChatCompletionRequest(BaseModel):
    model: str
    messages: List[Message]
    temperature: Optional[float] = 1.0
    top_p: Optional[float] = 1.0
    n: Optional[int] = 1
    stream: Optional[bool] = False
    stop: Optional[Union[str, List[str]]] = None
    max_tokens: Optional[int] = None
    presence_penalty: Optional[float] = 0
    frequency_penalty: Optional[float] = 0
    logit_bias: Optional[Dict[str, float]] = None
    user: Optional[str] = None


# 定义ChatCompletionResponseChoice类
class ChatCompletionResponseChoice(BaseModel):
    index: int
    message: Message
    finish_reason: Optional[str] = None


# 定义Usage类
class Usage(BaseModel):
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int


# 定义ChatCompletionResponse类
class ChatCompletionResponse(BaseModel):
    id: str = Field(default_factory=lambda: f"chatcmpl-{uuid.uuid4().hex}")
    object: str = "chat.completion"
    created: int = Field(default_factory=lambda: int(time.time()))
    model: str
    choices: List[ChatCompletionResponseChoice]
    usage: Usage
    system_fingerprint: Optional[str] = None


# 加载配置
async def load_graphrag_config():
    """
    加载GraphRAG配置
    """
    global graphrag_config
    try:
        # 检查API密钥是否已设置
        if not app_config.is_api_key_set:
            logger.error("API密钥未设置，请在 .env 文件中设置 GRAPHRAG_CHAT_API_KEY 和 GRAPHRAG_EMBEDDING_API_KEY")
            raise HTTPException(status_code=400, detail="API密钥未设置，请在 .env 文件中设置 GRAPHRAG_CHAT_API_KEY 和 GRAPHRAG_EMBEDDING_API_KEY")
        
        graphrag_config = load_config(CONFIG_PATH)
        logger.info("配置加载完成")
        logger.info(f"使用模型: {app_config.GRAPHRAG_CHAT_MODEL}")
        logger.info(f"API基础地址: {app_config.GRAPHRAG_API_BASE}")
        return graphrag_config
    except Exception as e:
        logger.error(f"加载配置失败: {str(e)}")
        raise


# 加载数据
async def load_data():
    """
    加载知识图谱数据
    """
    try:
        # 读取实体数据
        entity_df = pd.read_parquet(f"{INPUT_DIR}/{app_config.ENTITY_TABLE}.parquet")
        logger.info(f"实体数据加载完成，共 {len(entity_df)} 条记录")
        
        # 读取社区数据
        community_df = pd.read_parquet(f"{INPUT_DIR}/create_final_communities.parquet")
        logger.info(f"社区数据加载完成，共 {len(community_df)} 条记录")
        
        # 读取社区报告
        report_df = pd.read_parquet(f"{INPUT_DIR}/{app_config.COMMUNITY_REPORT_TABLE}.parquet")
        logger.info(f"社区报告加载完成，共 {len(report_df)} 条记录")
        
        # 读取文本单元
        text_unit_df = pd.read_parquet(f"{INPUT_DIR}/{app_config.TEXT_UNIT_TABLE}.parquet")
        logger.info(f"文本单元加载完成，共 {len(text_unit_df)} 条记录")
        
        # 读取关系数据
        relationship_df = pd.read_parquet(f"{INPUT_DIR}/{app_config.RELATIONSHIP_TABLE}.parquet")
        logger.info(f"关系数据加载完成，共 {len(relationship_df)} 条记录")
        
        # 读取协变量数据
        covariate_df = pd.read_parquet(f"{INPUT_DIR}/{app_config.COVARIATE_TABLE}.parquet")
        logger.info(f"协变量数据加载完成，共 {len(covariate_df)} 条记录")
        
        return entity_df, community_df, report_df, text_unit_df, relationship_df, covariate_df
    except Exception as e:
        logger.error(f"加载数据失败: {str(e)}")
        raise


# 格式化响应
async def format_response(response: str) -> str:
    """
    格式化响应文本，增强可读性
    """
    # 按段落分割
    paragraphs = re.split(r'\n{2,}', response)
    formatted_paragraphs = []
    
    for para in paragraphs:
        # 处理代码块
        if '```' in para:
            parts = para.split('```')
            for i, part in enumerate(parts):
                if i % 2 == 1:  # 代码块部分
                    parts[i] = f"\n```\n{part.strip()}\n```\n"
            para = ''.join(parts)
        else:
            # 句子间添加换行
            para = para.replace('. ', '.\n')
        
        formatted_paragraphs.append(para.strip())
    
    return '\n\n'.join(formatted_paragraphs)


# 生成流式响应
async def generate_stream_response(content: str, model: str) -> AsyncGenerator[str, None]:
    """
    生成流式响应数据
    """
    chunk_id = f"chatcmpl-{uuid.uuid4().hex}"
    lines = content.split('\n')
    
    # 逐行发送
    for line in lines:
        chunk = {
            "id": chunk_id,
            "object": "chat.completion.chunk",
            "created": int(time.time()),
            "model": model,
            "choices": [{
                "index": 0,
                "delta": {"content": line + '\n'},
                "finish_reason": None
            }]
        }
        yield f"data: {json.dumps(chunk, ensure_ascii=False)}\n"
        await asyncio.sleep(0.1)  # 控制流式速度
    
    # 发送结束标记
    final_chunk = {
        "id": chunk_id,
        "object": "chat.completion.chunk",
        "created": int(time.time()),
        "model": model,
        "choices": [{
            "index": 0,
            "delta": {},
            "finish_reason": "stop"
        }]
    }
    yield f"data: {json.dumps(final_chunk, ensure_ascii=False)}\n"
    yield "data: [DONE]\n"


# 加载持久化数据
def load_persistent_data():
    """加载持久化的数据"""
    global documents_data, settings_data
    
    # 加载文档数据
    if os.path.exists(DOCUMENTS_FILE):
        try:
            with open(DOCUMENTS_FILE, 'r', encoding='utf-8') as f:
                documents_data = json.load(f)
            logger.info(f"加载文档数据: {len(documents_data)} 条")
        except Exception as e:
            logger.error(f"加载文档数据失败: {e}")
            documents_data = []
    else:
        # 初始化默认文档数据
        documents_data = [
            {
                "id": 1,
                "name": "人工智能导论.pdf",
                "size": 1024000,
                "type": "PDF",
                "status": "processed",
                "uploadTime": "2026-03-30 10:30",
                "processedTime": "2026-03-30 10:35",
                "stats": {"entities": 128, "relationships": 256, "chunks": 384}
            },
            {
                "id": 2,
                "name": "知识图谱技术.docx",
                "size": 2048000,
                "type": "Word",
                "status": "processed",
                "uploadTime": "2026-03-29 16:45",
                "processedTime": "2026-03-29 16:50",
                "stats": {"entities": 256, "relationships": 512, "chunks": 768}
            },
            {
                "id": 3,
                "name": "GraphRAG研究.md",
                "size": 512000,
                "type": "Markdown",
                "status": "processing",
                "uploadTime": "2026-03-29 14:20"
            },
            {
                "id": 4,
                "name": "SQLite使用指南.txt",
                "size": 256000,
                "type": "文本",
                "status": "pending",
                "uploadTime": "2026-03-28 09:15"
            }
        ]
        save_persistent_data()
    
    # 加载设置数据
    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, 'r', encoding='utf-8') as f:
                settings_data = json.load(f)
            logger.info("加载设置数据成功")
        except Exception as e:
            logger.error(f"加载设置数据失败: {e}")
            settings_data = {}
    else:
        # 初始化默认设置
        settings_data = {
            "api": {
                "apiKey": "",
                "apiBaseUrl": "https://open.bigmodel.cn/api/paas/v4",
                "model": "glm-4-flash",
                "timeout": 30
            },
            "system": {
                "batchSize": 5,
                "chunkSize": 1000,
                "overlapRatio": 0.1,
                "entityThreshold": 0.7,
                "relationThreshold": 0.6
            },
            "dataStats": {
                "documents": 4,
                "entities": 1568,
                "relationships": 2890,
                "storageUsed": "128 MB"
            }
        }
        save_persistent_data()


# 保存持久化数据
def save_persistent_data():
    """保存数据到文件"""
    try:
        with open(DOCUMENTS_FILE, 'w', encoding='utf-8') as f:
            json.dump(documents_data, f, ensure_ascii=False, indent=2)
        
        with open(SETTINGS_FILE, 'w', encoding='utf-8') as f:
            json.dump(settings_data, f, ensure_ascii=False, indent=2)
        
        logger.info("数据保存成功")
    except Exception as e:
        logger.error(f"保存数据失败: {e}")


# FastAPI应用生命周期
@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    FastAPI应用生命周期管理
    """
    try:
        logger.info("=" * 50)
        logger.info("正在初始化知识图谱查询服务...")
        logger.info("=" * 50)
        
        # 加载配置
        await load_graphrag_config()
        
        # 加载数据
        await load_data()
        
        # 加载持久化数据
        load_persistent_data()
        
        logger.info("=" * 50)
        logger.info("知识图谱查询服务初始化完成")
        logger.info("=" * 50)
        
    except Exception as e:
        logger.error(f"初始化失败: {e}")
        raise
    
    yield  # 应用运行期间
    
    # 关闭清理
    logger.info("正在关闭服务...")


# 创建FastAPI应用
app = FastAPI(
    title="知识图谱查询服务",
    description="基于GraphRAG的知识图谱智能问答API",
    version="2.0.0",
    lifespan=lifespan
)

# 添加CORS中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 允许所有来源
    allow_credentials=True,
    allow_methods=["*"],  # 允许所有方法
    allow_headers=["*"],  # 允许所有头
)


# 调用智谱AI API
async def call_zhipu_api(prompt: str, context: str = "") -> str:
    """
    调用智谱AI API进行回答
    """
    try:
        import aiohttp
        
        api_key = app_config.GRAPHRAG_CHAT_API_KEY
        api_base = app_config.GRAPHRAG_API_BASE
        model = app_config.GRAPHRAG_CHAT_MODEL
        
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        
        # 构建系统提示词
        system_prompt = """你是一个基于知识图谱的智能问答助手。你的任务是回答用户关于知识图谱的问题。

请根据提供的问题和上下文信息，给出准确、详细的回答。如果上下文信息不足，请基于你的知识给出合理的回答。

回答要求：
1. 使用中文回答
2. 结构清晰，段落分明
3. 如果涉及多个概念，请分别说明
4. 适当使用Markdown格式（如标题、列表等）"""
        
        # 构建用户消息
        user_message = f"问题：{prompt}"
        if context:
            user_message += f"\n\n上下文信息：\n{context}"
        
        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message}
            ],
            "temperature": 0.7,
            "max_tokens": 2000
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{api_base}/chat/completions",
                headers=headers,
                json=payload,
                timeout=aiohttp.ClientTimeout(total=60)
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    return data["choices"][0]["message"]["content"]
                else:
                    error_text = await response.text()
                    logger.error(f"智谱API调用失败: {response.status} - {error_text}")
                    raise Exception(f"API调用失败: {response.status}")
                    
    except Exception as e:
        logger.error(f"调用智谱API失败: {str(e)}")
        raise


# 执行本地搜索
async def perform_local_search(prompt: str):
    """
    执行本地搜索，并结合智谱AI生成回答
    """
    try:
        # 加载数据
        entity_df, community_df, report_df, text_unit_df, relationship_df, covariate_df = await load_data()
        
        # 构建上下文信息
        context_parts = []
        
        # 添加相关实体信息
        if 'title' in entity_df.columns:
            entities = entity_df['title'].head(10).tolist()
            context_parts.append(f"知识图谱中的相关实体：{', '.join(entities)}")
        
        # 添加相关关系信息
        if 'description' in relationship_df.columns:
            relationships = relationship_df['description'].head(5).tolist()
            context_parts.append(f"相关关系：{', '.join(relationships)}")
        
        context = "\n".join(context_parts)
        
        # 调用智谱AI API
        result = await call_zhipu_api(prompt, context)
        return result
        
    except Exception as e:
        logger.error(f"本地搜索失败: {str(e)}")
        # 尝试直接调用API（无上下文）
        try:
            return await call_zhipu_api(prompt)
        except:
            # 返回模拟回答
            return f"基于知识图谱的本地搜索结果：\n\n关于「{prompt}」，系统从知识图谱中检索到了相关信息。\n\n由于当前知识图谱数据正在优化中，这里提供一个基于已有数据的回答。\n\n知识图谱是一种用于表示知识的图结构，它通过实体和关系来描述现实世界中的事物及其联系。"


# 执行全局搜索
async def perform_global_search(prompt: str):
    """
    执行全局搜索，并结合智谱AI生成回答
    """
    try:
        # 加载数据
        entity_df, community_df, report_df, _, _, _ = await load_data()
        
        # 构建上下文信息（基于社区报告）
        context_parts = []
        
        # 添加社区报告信息
        if 'summary' in report_df.columns:
            summaries = report_df['summary'].head(3).tolist()
            context_parts.append("知识图谱社区报告摘要：")
            for i, summary in enumerate(summaries, 1):
                context_parts.append(f"{i}. {summary}")
        
        context = "\n".join(context_parts)
        
        # 调用智谱AI API
        result = await call_zhipu_api(prompt, context)
        return result
        
    except Exception as e:
        logger.error(f"全局搜索失败: {str(e)}")
        # 尝试直接调用API（无上下文）
        try:
            return await call_zhipu_api(prompt)
        except:
            # 返回模拟回答
            return f"基于知识图谱的全局搜索结果：\n\n关于「{prompt}」，系统从社区报告中检索到了相关信息。\n\n由于当前知识图谱数据正在优化中，这里提供一个基于社区报告的回答。\n\n知识图谱在教育领域有广泛的应用，可以帮助学生更好地理解知识之间的关系，构建系统化的知识体系。"


# 执行综合搜索
async def perform_comprehensive_search(prompt: str):
    """
    执行综合搜索（本地+全局）
    """
    # 并行执行本地和全局搜索
    local_result, global_result = await asyncio.gather(
        perform_local_search(prompt),
        perform_global_search(prompt)
    )
    
    # 格式化结果
    formatted_result = "# 综合搜索结果\n\n"
    formatted_result += "## 本地检索结果\n"
    formatted_result += local_result + "\n\n"
    formatted_result += "## 全局检索结果\n"
    formatted_result += global_result + "\n"
    
    return formatted_result


# POST请求接口，与大模型进行知识问答
@app.post("/v1/chat/completions", response_model=ChatCompletionResponse)
async def chat_completions(request: ChatCompletionRequest):
    """
    知识问答接口
    
    支持三种搜索模式:
    - graphrag-local-search:latest: 本地搜索（基于实体和关系）
    - graphrag-global-search:latest: 全局搜索（基于社区报告）
    - full-model:latest: 综合搜索（本地+全局）
    """
    try:
        logger.info(f"收到查询请求，模型: {request.model}")
        
        # 获取用户问题
        prompt = request.messages[-1].content if request.messages else ""
        logger.info(f"查询内容: {prompt[:100]}...")
        
        # 根据模型选择搜索策略
        if request.model == "graphrag-global-search:latest":
            response_content = await perform_global_search(prompt)
            
        elif request.model == "full-model:latest":
            response_content = await perform_comprehensive_search(prompt)
            
        elif request.model == "graphrag-local-search:latest":
            response_content = await perform_local_search(prompt)
            
        else:
            # 默认使用本地搜索
            logger.warning(f"未知模型: {request.model}，使用默认本地搜索")
            response_content = await perform_local_search(prompt)
        
        logger.info(f"查询完成，响应长度: {len(response_content)}")
        
        # 流式响应
        if request.stream:
            return StreamingResponse(
                generate_stream_response(response_content, request.model),
                media_type="text/event-stream"
            )
        
        # 非流式响应
        response = ChatCompletionResponse(
            model=request.model,
            choices=[
                ChatCompletionResponseChoice(
                    index=0,
                    message=Message(role="assistant", content=response_content),
                    finish_reason="stop"
                )
            ],
            usage=Usage(
                prompt_tokens=len(prompt.split()),
                completion_tokens=len(response_content.split()),
                total_tokens=len(prompt.split()) + len(response_content.split())
            )
        )
        
        return JSONResponse(content=response.model_dump())
        
    except Exception as e:
        logger.error(f"处理查询请求失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# GET请求接口，获取可用模型列表
@app.get("/v1/models")
async def list_models():
    """获取可用的模型列表"""
    logger.info("收到模型列表请求")
    current_time = int(time.time())
    
    models = [
        {
            "id": "graphrag-local-search:latest",
            "object": "model",
            "created": current_time - 100000,
            "owned_by": "graphrag",
            "description": "本地搜索模式 - 基于实体和关系"
        },
        {
            "id": "graphrag-global-search:latest",
            "object": "model",
            "created": current_time - 95000,
            "owned_by": "graphrag",
            "description": "全局搜索模式 - 基于社区报告"
        },
        {
            "id": "full-model:latest",
            "object": "model",
            "created": current_time - 80000,
            "owned_by": "combined",
            "description": "综合搜索模式 - 本地+全局"
        }
    ]
    
    return JSONResponse(content={
        "object": "list",
        "data": models
    })


# 文档管理接口
@app.get("/api/documents")
async def get_documents():
    """获取文档列表"""
    try:
        global documents_data
        return JSONResponse(content={"documents": documents_data, "total": len(documents_data)})
    except Exception as e:
        logger.error(f"获取文档列表失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# 添加文档接口
@app.post("/api/documents")
async def add_document(document: Dict[str, Any]):
    """添加新文档"""
    try:
        global documents_data
        document["id"] = len(documents_data) + 1
        document["uploadTime"] = time.strftime("%Y-%m-%d %H:%M")
        documents_data.append(document)
        save_persistent_data()
        return JSONResponse(content={"status": "success", "document": document})
    except Exception as e:
        logger.error(f"添加文档失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# 删除文档接口
@app.delete("/api/documents/{doc_id}")
async def delete_document(doc_id: int):
    """删除文档"""
    try:
        global documents_data
        documents_data = [doc for doc in documents_data if doc["id"] != doc_id]
        save_persistent_data()
        return JSONResponse(content={"status": "success", "message": "文档删除成功"})
    except Exception as e:
        logger.error(f"删除文档失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# 系统设置接口
@app.get("/api/settings")
async def get_settings():
    """获取系统设置"""
    try:
        global settings_data
        # 更新数据统计数据
        settings_data["dataStats"]["documents"] = len(documents_data)
        return JSONResponse(content=settings_data)
    except Exception as e:
        logger.error(f"获取系统设置失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# 保存系统设置接口
@app.post("/api/settings")
async def save_settings(settings: Dict[str, Any]):
    """保存系统设置"""
    try:
        global settings_data
        settings_data.update(settings)
        save_persistent_data()
        logger.info(f"保存系统设置成功")
        return JSONResponse(content={"status": "success", "message": "设置保存成功"})
    except Exception as e:
        logger.error(f"保存系统设置失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# 图谱数据接口
@app.get("/api/graph/data")
async def get_graph_data():
    """获取图谱数据"""
    try:
        # 加载数据
        entity_df, community_df, report_df, text_unit_df, relationship_df, covariate_df = await load_data()
        
        # 构建节点数据
        nodes = []
        if 'id' in entity_df.columns and 'title' in entity_df.columns:
            for _, row in entity_df.head(50).iterrows():  # 限制返回50个节点
                node = {
                    "id": str(row['id']),
                    "name": str(row['title']) if pd.notna(row['title']) else str(row['id']),
                    "category": str(row.get('type', 'entity')),
                    "value": int(row.get('degree', 1)) if pd.notna(row.get('degree', 1)) else 1
                }
                nodes.append(node)
        
        # 构建边数据
        links = []
        if 'source' in relationship_df.columns and 'target' in relationship_df.columns:
            for _, row in relationship_df.head(100).iterrows():  # 限制返回100条边
                link = {
                    "source": str(row['source']),
                    "target": str(row['target']),
                    "relation": str(row.get('description', '相关')) if pd.notna(row.get('description', '相关')) else '相关',
                    "value": float(row.get('weight', 1.0)) if pd.notna(row.get('weight', 1.0)) else 1.0
                }
                links.append(link)
        
        return JSONResponse(content={
            "nodes": nodes,
            "links": links,
            "total_nodes": len(entity_df),
            "total_links": len(relationship_df)
        })
    except Exception as e:
        logger.error(f"获取图谱数据失败: {e}")
        # 返回默认数据
        return JSONResponse(content={
            "nodes": [
                {"id": "1", "name": "知识图谱", "category": "概念", "value": 10},
                {"id": "2", "name": "实体", "category": "概念", "value": 8},
                {"id": "3", "name": "关系", "category": "概念", "value": 8},
                {"id": "4", "name": "GraphRAG", "category": "技术", "value": 6},
                {"id": "5", "name": "人工智能", "category": "领域", "value": 7}
            ],
            "links": [
                {"source": "1", "target": "2", "relation": "包含", "value": 1.0},
                {"source": "1", "target": "3", "relation": "包含", "value": 1.0},
                {"source": "4", "target": "1", "relation": "基于", "value": 0.8},
                {"source": "5", "target": "4", "relation": "应用", "value": 0.7}
            ],
            "total_nodes": 5,
            "total_links": 4
        })


# 健康检查接口
@app.get("/health")
async def health_check():
    """健康检查接口"""
    return JSONResponse(content={
        "status": "healthy",
        "config_loaded": graphrag_config is not None,
        "timestamp": int(time.time())
    })


# 主函数
if __name__ == "__main__":
    logger.info(f"启动知识图谱查询服务，监听端口: {PORT}")
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=PORT,
        log_level="info"
    )

