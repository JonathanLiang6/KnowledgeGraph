"""
聊天 Pydantic Schemas
"""
from typing import Literal

from pydantic import BaseModel, Field


class Message(BaseModel):
    """单条消息"""
    # v4.1 (#83): role 收紧为白名单，防止任意字符串透传给 LLM
    role: Literal["system", "user", "assistant"] = Field(..., description="角色: system/user/assistant")
    # v4.1 (#83): 限制单条消息长度，防止超长输入打爆上下文/计费
    content: str = Field(..., max_length=100000, description="消息内容")


class ChatRequest(BaseModel):
    """聊天请求 - OpenAI 兼容格式 (v3.2: + enable_web)"""
    model: str = Field("deepseek-chat", description="模型名称")
    # v4.1 (#83): 限制消息条数，防止历史消息无限堆积
    messages: list[Message] = Field(..., max_length=50, description="对话消息列表（最多 50 条）")
    temperature: float | None = Field(1.0, ge=0.0, le=2.0)
    max_tokens: int | None = Field(4096, ge=1, le=32768)
    stream: bool | None = Field(False, description="是否流式输出")
    kb_id: str | None = Field(None, description="知识库ID(可选，用于RAG/Agent模式)")
    session_id: str | None = Field("default", description="会话ID(Agent模式记忆)")
    enable_web: bool | None = Field(False, description="是否启用联网搜索 (Q8)")


class ChatResponseChoice(BaseModel):
    """聊天响应选项"""
    index: int = 0
    message: Message
    finish_reason: str | None = "stop"


class ChatUsage(BaseModel):
    """Token 使用统计"""
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0


class ChatResponse(BaseModel):
    """聊天响应"""
    id: str
    object: str = "chat.completion"
    created: int
    model: str
    choices: list[ChatResponseChoice]
    usage: ChatUsage | None = None

    model_config = {"from_attributes": True}
