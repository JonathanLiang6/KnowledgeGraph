"""
知识图谱查询服务API
基于FastAPI框架提供知识问答接口
支持本地搜索、全局搜索和综合搜索三种模式
"""

import os
import sys
import asyncio
import time
import uuid
import json
import re
import logging
from typing import List, Optional, Dict, Any, Union, AsyncGenerator
from contextlib import asynccontextmanager

import pandas as pd
import tiktoken
from pydantic import BaseModel, Field
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

# 将上级目录添加到路径以导入graphrag
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# GraphRAG相关导入
from graphrag.query.context_builder.entity_extraction import EntityVectorStoreKey
from graphrag.query.indexer_adapters import (
    read_indexer_covariates,
    read_indexer_entities,
    read_indexer_relationships,
    read_indexer_reports,
    read_indexer_text_units,
)
from graphrag.query.input.loaders.dfs import store_entity_semantic_embeddings
from graphrag.query.llm.oai.chat_openai import ChatOpenAI
from graphrag.query.llm.oai.embedding import OpenAIEmbedding
from graphrag.query.llm.oai.typing import OpenaiApiType
from graphrag.query.question_gen.local_gen import LocalQuestionGen
from graphrag.query.structured_search.local_search.mixed_context import LocalSearchMixedContext
from graphrag.query.structured_search.local_search.search import LocalSearch
from graphrag.query.structured_search.global_search.community_context import GlobalCommunityContext
from graphrag.query.structured_search.global_search.search import GlobalSearch
from graphrag.vector_stores.lancedb import LanceDBVectorStore

from config import config

# 配置日志
logging.basicConfig(
    level=getattr(logging, config.server.log_level),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ==================== 数据模型定义 ====================

class Message(BaseModel):
    """对话消息模型"""
    role: str                                    # 消息角色：system/user/assistant
    content: str                                 # 消息内容


class ChatCompletionRequest(BaseModel):
    """聊天完成请求模型"""
    model: str                                   # 模型名称
    messages: List[Message]                      # 消息列表
    temperature: Optional[float] = 1.0           # 采样温度
    top_p: Optional[float] = 1.0                 # 核采样参数
    n: Optional[int] = 1                         # 生成结果数量
    stream: Optional[bool] = False               # 是否流式输出
    stop: Optional[Union[str, List[str]]] = None # 停止词
    max_tokens: Optional[int] = None             # 最大token数
    presence_penalty: Optional[float] = 0        # 存在惩罚
    frequency_penalty: Optional[float] = 0       # 频率惩罚


class ChatCompletionResponseChoice(BaseModel):
    """聊天完成响应选项模型"""
    index: int                                   # 选项索引
    message: Message                             # 消息内容
    finish_reason: Optional[str] = None          # 完成原因


class Usage(BaseModel):
    """Token使用统计模型"""
    prompt_tokens: int                           # 提示token数
    completion_tokens: int                       # 完成token数
    total_tokens: int                            # 总token数


class ChatCompletionResponse(BaseModel):
    """聊天完成响应模型"""
    id: str = Field(default_factory=lambda: f"chatcmpl-{uuid.uuid4().hex}")
    object: str = "chat.completion"
    created: int = Field(default_factory=lambda: int(time.time()))
    model: str
    choices: List[ChatCompletionResponseChoice]
    usage: Usage
    system_fingerprint: Optional[str] = None


# ==================== 全局变量 ====================

# 搜索引擎实例
local_search_engine: Optional[LocalSearch] = None
global_search_engine: Optional[GlobalSearch] = None
question_generator: Optional[LocalQuestionGen] = None

# 数据表名称常量
COMMUNITY_REPORT_TABLE = "create_final_community_reports"
ENTITY_TABLE = "create_final_nodes"
ENTITY_EMBEDDING_TABLE = "create_final_entities"
RELATIONSHIP_TABLE = "create_final_relationships"
COVARIATE_TABLE = "create_final_covariates"
TEXT_UNIT_TABLE = "create_final_text_units"


# ==================== 核心功能函数 ====================

async def setup_llm_and_embedder() -> tuple:
    """
    初始化语言模型和嵌入模型
    
    返回:
        (llm, token_encoder, text_embedder) 三元组
    """
    logger.info("正在初始化语言模型和嵌入模型...")
    
    # 创建大语言模型客户端
    llm = ChatOpenAI(
        api_base=config.llm.api_base,
        api_key=config.llm.api_key,
        model=config.llm.chat_model,
        api_type=OpenaiApiType.OpenAI,
        max_tokens=config.llm.max_tokens,
        temperature=config.llm.temperature,
    )
    
    # 初始化token编码器
    token_encoder = tiktoken.get_encoding("cl100k_base")
    
    # 创建文本嵌入模型
    text_embedder = OpenAIEmbedding(
        api_base=config.llm.api_base,
        api_key=config.llm.api_key,
        model=config.llm.embedding_model,
        deployment_name=config.llm.embedding_model,
        api_type=OpenaiApiType.OpenAI,
        max_retries=config.llm.max_retries,
    )
    
    logger.info("语言模型和嵌入模型初始化完成")
    return llm, token_encoder, text_embedder


async def load_knowledge_graph_data() -> tuple:
    """
    加载知识图谱数据
    
    返回:
        (entities, relationships, reports, text_units, embedding_store, covariates) 六元组
    """
    logger.info("正在加载知识图谱数据...")
    
    try:
        # 读取实体数据
        entity_df = pd.read_parquet(
            f"{config.graphrag.storage_dir}/{ENTITY_TABLE}.parquet"
        )
        entity_embedding_df = pd.read_parquet(
            f"{config.graphrag.storage_dir}/{ENTITY_EMBEDDING_TABLE}.parquet"
        )
        entities = read_indexer_entities(
            entity_df, 
            entity_embedding_df, 
            config.graphrag.community_level
        )
        
        # 初始化向量存储
        embedding_store = LanceDBVectorStore(
            collection_name="entity_description_embeddings"
        )
        embedding_store.connect(db_uri=config.lancedb_uri)
        store_entity_semantic_embeddings(
            entities=entities, 
            vectorstore=embedding_store
        )
        
        # 读取关系数据
        relationship_df = pd.read_parquet(
            f"{config.graphrag.storage_dir}/{RELATIONSHIP_TABLE}.parquet"
        )
        relationships = read_indexer_relationships(relationship_df)
        
        # 读取社区报告
        report_df = pd.read_parquet(
            f"{config.graphrag.storage_dir}/{COMMUNITY_REPORT_TABLE}.parquet"
        )
        reports = read_indexer_reports(
            report_df, 
            entity_df, 
            config.graphrag.community_level
        )
        
        # 读取文本单元
        text_unit_df = pd.read_parquet(
            f"{config.graphrag.storage_dir}/{TEXT_UNIT_TABLE}.parquet"
        )
        text_units = read_indexer_text_units(text_unit_df)
        
        # 读取协变量
        covariate_df = pd.read_parquet(
            f"{config.graphrag.storage_dir}/{COVARIATE_TABLE}.parquet"
        )
        claims = read_indexer_covariates(covariate_df)
        covariates = {"claims": claims}
        
        logger.info(f"知识图谱数据加载完成，声明记录数: {len(claims)}")
        
        return entities, relationships, reports, text_units, embedding_store, covariates
        
    except Exception as e:
        logger.error(f"加载知识图谱数据失败: {e}")
        raise


async def setup_search_engines(
    llm: ChatOpenAI,
    token_encoder,
    text_embedder: OpenAIEmbedding,
    entities,
    relationships,
    reports,
    text_units,
    embedding_store,
    covariates
) -> tuple:
    """
    配置本地和全局搜索引擎
    
    参数:
        llm: 大语言模型实例
        token_encoder: token编码器
        text_embedder: 文本嵌入模型
        entities: 实体数据
        relationships: 关系数据
        reports: 社区报告
        text_units: 文本单元
        embedding_store: 向量存储
        covariates: 协变量
        
    返回:
        (local_search_engine, global_search_engine, ...) 多元组
    """
    logger.info("正在配置搜索引擎...")
    
    # ========== 本地搜索引擎配置 ==========
    local_context_builder = LocalSearchMixedContext(
        community_reports=reports,
        text_units=text_units,
        entities=entities,
        relationships=relationships,
        covariates=covariates,
        entity_text_embeddings=embedding_store,
        embedding_vectorstore_key=EntityVectorStoreKey.ID,
        text_embedder=text_embedder,
        token_encoder=token_encoder,
    )
    
    local_context_params = {
        "text_unit_prop": 0.5,
        "community_prop": 0.1,
        "conversation_history_max_turns": 5,
        "conversation_history_user_turns_only": True,
        "top_k_mapped_entities": 10,
        "top_k_relationships": 10,
        "include_entity_rank": True,
        "include_relationship_weight": True,
        "include_community_rank": False,
        "return_candidate_context": False,
        "embedding_vectorstore_key": EntityVectorStoreKey.ID,
        "max_tokens": 4096,
    }
    
    local_llm_params = {
        "max_tokens": 4096,
        "temperature": 0.0,
    }
    
    local_engine = LocalSearch(
        llm=llm,
        context_builder=local_context_builder,
        token_encoder=token_encoder,
        llm_params=local_llm_params,
        context_builder_params=local_context_params,
        response_type="multiple paragraphs",
    )
    
    # ========== 全局搜索引擎配置 ==========
    global_context_builder = GlobalCommunityContext(
        community_reports=reports,
        entities=entities,
        token_encoder=token_encoder,
    )
    
    global_context_params = {
        "use_community_summary": False,
        "shuffle_data": True,
        "include_community_rank": True,
        "min_community_rank": 0,
        "community_rank_name": "rank",
        "include_community_weight": True,
        "community_weight_name": "occurrence weight",
        "normalize_community_weight": True,
        "max_tokens": 4096,
        "context_name": "Reports",
    }
    
    map_llm_params = {
        "max_tokens": 1000,
        "temperature": 0.0,
        "response_format": {"type": "json_object"},
    }
    
    reduce_llm_params = {
        "max_tokens": 2000,
        "temperature": 0.0,
    }
    
    global_engine = GlobalSearch(
        llm=llm,
        context_builder=global_context_builder,
        token_encoder=token_encoder,
        max_data_tokens=4096,
        map_llm_params=map_llm_params,
        reduce_llm_params=reduce_llm_params,
        allow_general_knowledge=False,
        json_mode=True,
        context_builder_params=global_context_params,
        concurrent_coroutines=32,
        response_type="multiple paragraphs",
    )
    
    # 创建问题生成器
    question_gen = LocalQuestionGen(
        llm=llm,
        context_builder=local_context_builder,
        token_encoder=token_encoder,
        llm_params=local_llm_params,
        context_builder_params=local_context_params,
    )
    
    logger.info("搜索引擎配置完成")
    return local_engine, global_engine, local_context_builder, local_llm_params, local_context_params


def format_response(response: str) -> str:
    """
    格式化响应文本，增强可读性
    
    参数:
        response: 原始响应文本
        
    返回:
        格式化后的文本
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


async def perform_comprehensive_search(prompt: str) -> str:
    """
    执行综合搜索（本地+全局）
    
    参数:
        prompt: 查询问题
        
    返回:
        格式化的搜索结果
    """
    # 并行执行本地和全局搜索
    local_result, global_result = await asyncio.gather(
        local_search_engine.asearch(prompt),
        global_search_engine.asearch(prompt)
    )
    
    # 格式化结果
    formatted_result = "# 综合搜索结果\n\n"
    formatted_result += "## 本地检索结果\n"
    formatted_result += format_response(local_result.response) + "\n\n"
    formatted_result += "## 全局检索结果\n"
    formatted_result += format_response(global_result.response) + "\n"
    
    return formatted_result


async def generate_stream_response(
    content: str, 
    model: str
) -> AsyncGenerator[str, None]:
    """
    生成流式响应数据
    
    参数:
        content: 响应内容
        model: 模型名称
        
    生成:
        SSE格式的数据流
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


# ==================== FastAPI应用生命周期 ====================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    FastAPI应用生命周期管理
    处理启动初始化和关闭清理
    """
    global local_search_engine, global_search_engine, question_generator
    
    try:
        logger.info("=" * 50)
        logger.info("正在初始化知识图谱查询服务...")
        logger.info("=" * 50)
        
        # 初始化模型
        llm, token_encoder, text_embedder = await setup_llm_and_embedder()
        
        # 加载数据
        entities, relationships, reports, text_units, embedding_store, covariates = await load_knowledge_graph_data()
        
        # 配置搜索引擎
        local_search_engine, global_search_engine, local_context_builder, local_llm_params, local_context_params = await setup_search_engines(
            llm, token_encoder, text_embedder,
            entities, relationships, reports, text_units,
            embedding_store, covariates
        )
        
        # 创建问题生成器
        question_generator = LocalQuestionGen(
            llm=llm,
            context_builder=local_context_builder,
            token_encoder=token_encoder,
            llm_params=local_llm_params,
            context_builder_params=local_context_params,
        )
        
        logger.info("=" * 50)
        logger.info("知识图谱查询服务初始化完成")
        logger.info("=" * 50)
        
    except Exception as e:
        logger.error(f"初始化失败: {e}")
        raise
    
    yield  # 应用运行期间
    
    # 关闭清理
    logger.info("正在关闭服务...")


# ==================== 创建FastAPI应用 ====================

app = FastAPI(
    title="知识图谱查询服务",
    description="基于GraphRAG的知识图谱智能问答API",
    version="2.0.0",
    lifespan=lifespan
)

# 添加CORS中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ==================== API端点 ====================

@app.post("/v1/chat/completions", response_model=ChatCompletionResponse)
async def chat_completions(request: ChatCompletionRequest):
    """
    知识问答接口
    
    支持三种搜索模式:
    - graphrag-local-search:latest: 本地搜索（基于实体和关系）
    - graphrag-global-search:latest: 全局搜索（基于社区报告）
    - full-model:latest: 综合搜索（本地+全局）
    """
    # 检查搜索引擎是否就绪
    if not local_search_engine or not global_search_engine:
        logger.error("搜索引擎未初始化")
        raise HTTPException(status_code=503, detail="搜索引擎未就绪")
    
    try:
        logger.info(f"收到查询请求，模型: {request.model}")
        
        # 获取用户问题
        prompt = request.messages[-1].content if request.messages else ""
        logger.info(f"查询内容: {prompt[:100]}...")
        
        # 根据模型选择搜索策略
        if request.model == "graphrag-global-search:latest":
            result = await global_search_engine.asearch(prompt)
            response_content = format_response(result.response)
            
        elif request.model == "full-model:latest":
            response_content = await perform_comprehensive_search(prompt)
            
        elif request.model == "graphrag-local-search:latest":
            result = await local_search_engine.asearch(prompt)
            response_content = format_response(result.response)
            
        else:
            # 默认使用本地搜索
            logger.warning(f"未知模型: {request.model}，使用默认本地搜索")
            result = await local_search_engine.asearch(prompt)
            response_content = format_response(result.response)
        
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


@app.get("/v1/models")
async def list_models():
    """获取可用的模型列表"""
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


@app.get("/health")
async def health_check():
    """健康检查接口"""
    return JSONResponse(content={
        "status": "healthy",
        "local_search_ready": local_search_engine is not None,
        "global_search_ready": global_search_engine is not None,
        "timestamp": int(time.time())
    })


# ==================== 主函数 ====================

def main():
    """启动服务"""
    logger.info(f"启动知识图谱查询服务，监听端口: {config.server.port}")
    uvicorn.run(
        app,
        host=config.server.host,
        port=config.server.port,
        log_level=config.server.log_level.lower()
    )


if __name__ == "__main__":
    main()
