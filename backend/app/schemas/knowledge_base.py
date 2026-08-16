"""
知识库 Pydantic Schemas
"""
from datetime import datetime

from pydantic import BaseModel, Field


class KnowledgeBaseCreate(BaseModel):
    """创建知识库"""
    name: str = Field(..., min_length=1, max_length=255, description="知识库名称")
    description: str = Field("", max_length=2000, description="知识库描述")


class KnowledgeBaseUpdate(BaseModel):
    """更新知识库"""
    name: str | None = Field(None, min_length=1, max_length=255)
    description: str | None = Field(None, max_length=2000)


class KnowledgeBaseResponse(BaseModel):
    """知识库响应"""
    id: str
    name: str
    description: str
    created_at: datetime
    updated_at: datetime
    document_count: int = 0

    model_config = {"from_attributes": True}


class KnowledgeBaseListResponse(BaseModel):
    """知识库列表响应"""
    items: list[KnowledgeBaseResponse]
    total: int
