"""
文档 Pydantic Schemas - v2.1 扩展
"""
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field, field_validator


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


class DocumentBriefResponse(BaseModel):
    """文档简要响应（列表用）"""
    id: str
    kb_id: str
    filename: str
    file_type: str
    file_size: int
    status: str
    progress: float
    entity_count: int
    relationship_count: int
    error_message: str
    created_at: datetime
    processed_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class DocumentListResponse(BaseModel):
    """文档列表响应"""
    items: List[DocumentResponse]
    total: int
    page: int = 1
    page_size: int = 20


class DocumentUploadResponse(BaseModel):
    """单文档上传响应"""
    document_id: str
    task_id: str
    filename: str
    status: str
    message: str
    duplicate: bool = False
    duplicate_of: Optional[str] = None


class BatchUploadItem(BaseModel):
    """批量上传单项结果"""
    filename: str
    success: bool
    document_id: Optional[str] = None
    task_id: Optional[str] = None
    message: str = ""
    duplicate: bool = False


class BatchUploadResponse(BaseModel):
    """批量上传响应"""
    total: int
    succeeded: int
    failed: int
    duplicates: int
    items: List[BatchUploadItem]


class ReprocessRequest(BaseModel):
    """重新处理请求"""
    force: bool = Field(default=False, description="是否强制重新处理（忽略已有图谱数据）")


class ReprocessResponse(BaseModel):
    """重新处理响应"""
    document_id: str
    task_id: str
    previous_status: str
    message: str


class DedupCheckResponse(BaseModel):
    """去重检测响应"""
    has_duplicate: bool
    duplicate_doc_id: Optional[str] = None
    duplicate_filename: Optional[str] = None
    file_hash: str


class DocumentStats(BaseModel):
    """文档统计"""
    documents: int = 0
    entities: int = 0
    relationships: int = 0
    storage_used: str = "0 B"
    pending: int = 0
    processing: int = 0
    done: int = 0
    failed: int = 0


class FileValidationError(BaseModel):
    """文件校验错误"""
    filename: str
    error: str
    error_type: str  # "size_exceeded", "type_not_allowed", "mime_not_allowed", "duplicate"
