"""
拓扑导航 Pydantic Schemas - v3.2 Q10
"""
from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, Field


class TopologyNodeCreate(BaseModel):
    """创建拓扑节点"""
    name: str = Field(..., min_length=1, max_length=255, description="节点名称")
    icon: str = Field("📁", max_length=10, description="Emoji 图标")
    kb_id: Optional[str] = Field(None, description="绑定的知识库ID")
    position_x: float = Field(0.0, description="X 坐标")
    position_y: float = Field(0.0, description="Y 坐标")


class TopologyNodeUpdate(BaseModel):
    """更新拓扑节点"""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    icon: Optional[str] = Field(None, max_length=10)
    kb_id: Optional[str] = Field(None)
    position_x: Optional[float] = Field(None)
    position_y: Optional[float] = Field(None)


class TopologyNodeOut(BaseModel):
    """拓扑节点响应"""
    id: str
    uuid: str
    name: str
    icon: str
    kb_id: Optional[str] = None
    position_x: float
    position_y: float
    is_root: bool
    created_at: Optional[datetime] = None

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
    nodes: List[TopologyNodeOut]
    edges: List[TopologyEdgeOut]
