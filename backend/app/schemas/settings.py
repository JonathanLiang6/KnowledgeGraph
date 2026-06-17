"""
系统设置 Pydantic Schemas - 仅含系统参数，不含 API 密钥
"""
from typing import Optional
from pydantic import BaseModel, Field


class SystemParams(BaseModel):
    """系统参数（前端可读写）"""
    batch_size: int = Field(5, ge=1, le=100, description="批处理大小")
    chunk_size: int = Field(1000, ge=100, le=5000, description="文本块大小(字符)")
    overlap_ratio: float = Field(0.1, ge=0.0, le=0.5, description="重叠比例")
    entity_threshold: float = Field(0.7, ge=0.0, le=1.0, description="实体提取阈值")
    relation_threshold: float = Field(0.6, ge=0.0, le=1.0, description="关系提取阈值")


class VisualSettings(BaseModel):
    """视觉设置（前端可读写）"""
    primary_color: str = Field("#4F8CF7", description="主色调")
    font_size: str = Field("medium", description="字号")
    animations: bool = Field(True, description="是否启用动画")


class SettingsUpdate(BaseModel):
    """设置更新请求"""
    system: Optional[SystemParams] = None
    visual: Optional[VisualSettings] = None


class SystemStatus(BaseModel):
    """系统状态（只读，后端提供）"""
    api_configured: bool = False
    api_model: str = ""
    embedding_model: str = ""
    database_ok: bool = True
    server_version: str = "2.0.0"


class DataStats(BaseModel):
    """数据统计"""
    documents: int = 0
    entities: int = 0
    relationships: int = 0
    storage_used: str = "0 B"
    knowledge_bases: int = 0


class SettingsResponse(BaseModel):
    """设置响应"""
    system: SystemParams
    visual: VisualSettings
    system_status: SystemStatus
    data_stats: DataStats
