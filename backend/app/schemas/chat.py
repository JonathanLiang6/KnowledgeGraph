"""
聊天 Pydantic Schemas
"""
from typing import Optional, List
from pydantic import BaseModel, Field


class Message(BaseModel):
    """单条消息"""
    role: str = Field(..., description="角色: user/assistant/system")
    content: str = Field(..., description="消息内容")


class ChatRequest(BaseModel):
    """聊天请求 - OpenAI 兼容格式 (v3.2: + enable_web)"""
    model: str = Field("deepseek-chat", description="模型名称")
    messages: List[Message] = Field(..., description="对话消息列表")
    temperature: Optional[float] = Field(1.0, ge=0.0, le=2.0)
    max_tokens: Optional[int] = Field(4096, ge=1, le=32768)
    stream: Optional[bool] = Field(False, description="是否流式输出")
    kb_id: Optional[str] = Field(None, description="知识库ID(可选，用于RAG/Agent模式)")
    session_id: Optional[str] = Field("default", description="会话ID(Agent模式记忆)")
    enable_web: Optional[bool] = Field(False, description="是否启用联网搜索 (Q8)")


class ChatResponseChoice(BaseModel):
    """聊天响应选项"""
    index: int = 0
    message: Message
    finish_reason: Optional[str] = "stop"


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
    choices: List[ChatResponseChoice]
    usage: Optional[ChatUsage] = None

    model_config = {"from_attributes": True}
