"""
文档 Pydantic Schemas
"""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class DocumentResponse(BaseModel):
    """文档响应"""
    id: str
    kb_id: str
    filename: str
    file_path: str
    file_type: str
    file_size: int
    status: str
    progress: float
    word_count: int
    token_count: int
    chunk_count: int
    entity_count: int
    relationship_count: int
    error_message: str
    created_at: datetime
    processed_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class DocumentListResponse(BaseModel):
    """文档列表响应"""
    items: list[DocumentResponse]
    total: int


class DocumentUploadResponse(BaseModel):
    """文档上传响应"""
    document_id: str
    task_id: str
    filename: str
    status: str
    message: str


class DocumentStats(BaseModel):
    """文档统计"""
    documents: int = 0
    entities: int = 0
    relationships: int = 0
    storage_used: str = "0 B"
