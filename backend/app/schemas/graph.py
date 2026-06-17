"""
知识图谱 Pydantic Schemas
"""
from typing import Optional, List
from pydantic import BaseModel


class GraphNode(BaseModel):
    """图谱节点"""
    id: str
    name: str
    type: str
    weight: float
    color: str


class GraphLink(BaseModel):
    """图谱边"""
    id: str
    source: str
    target: str
    relation: str
    value: float
    sentence: str = ""


class GraphData(BaseModel):
    """图谱数据"""
    nodes: List[GraphNode] = []
    links: List[GraphLink] = []
    legend: dict = {}


class EntityDetail(BaseModel):
    """实体详情"""
    id: str
    name: str
    type: str
    description: str = ""
    weight: float = 0.0
    related_entities: list = []
    related_documents: list = []
