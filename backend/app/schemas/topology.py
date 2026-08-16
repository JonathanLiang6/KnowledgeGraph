"""
拓扑导航 Pydantic Schemas - v3.2 Q10
"""
from datetime import datetime

from pydantic import BaseModel, Field


class TopologyNodeCreate(BaseModel):
    """创建拓扑节点"""
    name: str = Field(..., min_length=1, max_length=255, description="节点名称")
    icon: str = Field("📁", max_length=10, description="Emoji 图标")
    kb_id: str | None = Field(None, description="绑定的知识库ID")
    position_x: float = Field(0.0, description="X 坐标")
    position_y: float = Field(0.0, description="Y 坐标")


class TopologyNodeUpdate(BaseModel):
    """更新拓扑节点"""
    name: str | None = Field(None, min_length=1, max_length=255)
    icon: str | None = Field(None, max_length=10)
    kb_id: str | None = Field(None)
    position_x: float | None = Field(None)
    position_y: float | None = Field(None)


class TopologyNodeOut(BaseModel):
    """拓扑节点响应"""
    id: str
    uuid: str
    name: str
    icon: str
    kb_id: str | None = None
    position_x: float
    position_y: float
    is_root: bool
    created_at: datetime | None = None

    model_config = {"from_attributes": True}


class TopologyEdgeCreate(BaseModel):
    """创建拓扑边"""
    source_id: str = Field(..., description="源节点ID")
    target_id: str = Field(..., description="目标节点ID")


class TopologyEdgeOut(BaseModel):
    """拓扑边响应"""
    id: str
    source_id: str
    target_id: str

    model_config = {"from_attributes": True}


class TopologyData(BaseModel):
    """全量拓扑数据"""
    nodes: list[TopologyNodeOut]
    edges: list[TopologyEdgeOut]
