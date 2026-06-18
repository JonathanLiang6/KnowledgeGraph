"""
DeepSeek V4 API 客户端封装 - 支持 Chat Completions (含流式) 和 Embedding
使用 OpenAI 兼容 SDK
"""
import json
import time
import logging
from typing import Optional, AsyncGenerator, List, Dict, Any
import httpx
from openai import AsyncOpenAI
from app.core.config import config

logger = logging.getLogger(__name__)

# 初始化 AsyncOpenAI 客户端（指向 DeepSeek API）
client = AsyncOpenAI(
    api_key=config.DEEPSEEK_API_KEY,
    base_url=config.DEEPSEEK_API_BASE,
    timeout=httpx.Timeout(120.0, connect=10.0),
)


class DeepSeekClient:
    """DeepSeek V4 API 统一客户端"""

    CHAT_MODEL = config.DEEPSEEK_CHAT_MODEL
    MAX_TOKENS = config.LLM_MAX_TOKENS
    TEMPERATURE = config.LLM_TEMPERATURE
    MAX_RETRIES = config.LLM_MAX_RETRIES

    @classmethod
    async def chat(
        cls,
        messages: List[Dict[str, str]],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        stream: bool = False,
    ) -> dict:
        """
        调用 DeepSeek V4 Chat Completions（非流式）

        Args:
            messages: 消息列表 [{"role": "user", "content": "..."}]
            temperature: 温度参数
            max_tokens: 最大 token 数
            stream: 是否流式（非流式时返回完整响应）

        Returns:
            {"content": "...", "usage": {"prompt_tokens": N, ...}}
        """
        if not config.is_api_key_set:
            raise ValueError("DeepSeek API Key 未配置，请在 .env 中设置 DEEPSEEK_API_KEY")

        for attempt in range(cls.MAX_RETRIES):
            try:
                response = await client.chat.completions.create(
                    model=cls.CHAT_MODEL,
                    messages=messages,
                    temperature=temperature if temperature is not None else cls.TEMPERATURE,
                    max_tokens=max_tokens if max_tokens is not None else cls.MAX_TOKENS,
                    stream=False,
                )
                choice = response.choices[0]
                return {
                    "content": choice.message.content or "",
                    "usage": {
                        "prompt_tokens": response.usage.prompt_tokens if response.usage else 0,
                        "completion_tokens": response.usage.completion_tokens if response.usage else 0,
                        "total_tokens": response.usage.total_tokens if response.usage else 0,
                    },
                    "finish_reason": choice.finish_reason or "stop",
                }
            except Exception as e:
                logger.warning(f"DeepSeek Chat 调用失败 (尝试 {attempt + 1}/{cls.MAX_RETRIES}): {e}")
                if attempt == cls.MAX_RETRIES - 1:
                    raise
                await _async_sleep(2 ** attempt)

    @classmethod
    async def chat_stream(
        cls,
        messages: List[Dict[str, str]],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> AsyncGenerator[str, None]:
        """
        调用 DeepSeek V4 Chat Completions（流式 SSE）

        Yields:
            文本片段（delta content）
        """
        if not config.is_api_key_set:
            raise ValueError("DeepSeek API Key 未配置")

        for attempt in range(cls.MAX_RETRIES):
            try:
                stream = await client.chat.completions.create(
                    model=cls.CHAT_MODEL,
                    messages=messages,
                    temperature=temperature if temperature is not None else cls.TEMPERATURE,
                    max_tokens=max_tokens if max_tokens is not None else cls.MAX_TOKENS,
                    stream=True,
                )
                async for chunk in stream:
                    if chunk.choices and chunk.choices[0].delta.content:
                        yield chunk.choices[0].delta.content
                return  # 流完成，退出
            except Exception as e:
                logger.warning(f"DeepSeek Stream 调用失败 (尝试 {attempt + 1}/{cls.MAX_RETRIES}): {e}")
                if attempt == cls.MAX_RETRIES - 1:
                    raise
                await _async_sleep(2 ** attempt)

    @classmethod
    async def embed(cls, texts: List[str]) -> List[List[float]]:
        """
        生成文本 Embedding（使用 DeepSeek 兼容 API）

        Args:
            texts: 文本列表

        Returns:
            向量列表 [[dim_1, dim_2, ...], ...]
        """
        if not config.is_api_key_set:
            raise ValueError("DeepSeek API Key 未配置")

        for attempt in range(cls.MAX_RETRIES):
            try:
                # DeepSeek 可能支持 /embeddings 端点
                response = await client.embeddings.create(
                    model=config.DEEPSEEK_CHAT_MODEL,
                    input=texts,
                )
                return [item.embedding for item in response.data]
            except Exception as e:
                err_str = str(e)
                # 404 不重试——端点不存在
                if "404" in err_str or "not found" in err_str.lower():
                    logger.warning(f"DeepSeek Embedding 端点不可用 (404)，请使用本地模型")
                    raise
                logger.warning(f"DeepSeek Embedding 调用失败 (尝试 {attempt + 1}): {e}")
                if attempt == cls.MAX_RETRIES - 1:
                    logger.error(
                        "DeepSeek Embedding API 不可用。"
                        f"请使用本地 Embedding 模型: {config.EMBEDDING_MODEL}"
                    )
                    raise
                await _async_sleep(2 ** attempt)

    @classmethod
    async def extract_entities(
        cls,
        text: str,
        candidate_entities: Optional[List[dict]] = None,
    ) -> dict:
        """
        使用 DeepSeek V4 进行实体精炼提取

        Args:
            text: 原文内容
            candidate_entities: NLP 粗筛的候选实体列表

        Returns:
            {"entities": [...], "relationships": [...]}
        """
        # 构建 prompt
        candidate_text = ""
        if candidate_entities:
            candidate_text = "\n候选实体列表（来自NLP粗筛）：\n"
            for ent in candidate_entities[:30]:
                candidate_text += f"- {ent.get('name', '')} (类型: {ent.get('type', '未知')}, 权重: {ent.get('weight', 0)})\n"

        system_prompt = _build_entity_extraction_prompt()
        user_message = f"""请从以下教学文本中提取知识实体和关系。

{candidate_text}

原文内容：
---
{text[:8000]}
---

请以 JSON 格式输出提取结果。"""

        result = await cls.chat(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ],
            temperature=0.0,
            max_tokens=4096,
        )

        # 解析 JSON 输出
        return _parse_entity_json(result["content"])


def _build_entity_extraction_prompt() -> str:
    """构建实体提取系统提示词"""
    return """你是一位教育知识图谱构建专家。你的任务是从教学文本中提取关键知识实体及其关系。

## 实体类型
- 概念 (concept): 核心知识点、术语定义
- 人物 (person): 历史人物、学者、作者
- 事件 (event): 历史事件、重要节点
- 公式 (formula): 数学/物理/化学公式
- 定理 (theorem): 定律、定理、公理
- 方法 (method): 解题方法、实验方法、分析方法
- 时间 (time): 时间段、时期、年代
- 地点 (location): 地理位置、区域
- 机构 (organization): 学校、研究机构

## 关系类型
- 包含 (contains): A 包含 B，整体与部分
- 因果 (causes): A 导致 B
- 前提 (prerequisite): A 是 B 的前提/基础
- 应用 (applies): A 应用于 B
- 对比 (contrasts): A 与 B 对比/对立
- 发展 (develops): A 发展为 B
- 例证 (example_of): A 是 B 的例证
- 关联 (relates): A 与 B 一般关联

## 输出格式
请以严格 JSON 格式输出:
{
  "entities": [
    {"name": "实体名", "type": "实体类型", "description": "简短描述", "confidence": 0.85}
  ],
  "relationships": [
    {"source": "源实体名", "target": "目标实体名", "relation": "关系类型", "description": "关系说明", "confidence": 0.75}
  ]
}

要求:
1. 实体名称准确、标准化（进行指代消解，将"它"、"该概念"等替换为具体名称）
2. 关系描述使用中文
3. 置信度 0-1，低于 0.3 的勿输出
4. 仅输出 JSON，不要其他文字"""


def _parse_entity_json(text: str) -> dict:
    """从 LLM 输出中解析实体 JSON"""
    try:
        # 尝试直接解析
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # 尝试从代码块中提取 JSON
    import re
    json_match = re.search(r'```(?:json)?\s*\n?(.*?)\n?```', text, re.DOTALL)
    if json_match:
        try:
            return json.loads(json_match.group(1))
        except json.JSONDecodeError:
            pass

    # 尝试找到最外层的大括号
    brace_start = text.find("{")
    brace_end = text.rfind("}")
    if brace_start >= 0 and brace_end > brace_start:
        try:
            return json.loads(text[brace_start:brace_end + 1])
        except json.JSONDecodeError:
            pass

    logger.warning(f"无法解析 LLM 实体提取输出: {text[:200]}")
    return {"entities": [], "relationships": []}


async def _async_sleep(seconds: float):
    """异步等待"""
    import asyncio
    await asyncio.sleep(seconds)
