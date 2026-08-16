"""
知识图谱 Pydantic Schemas
"""
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
    dashed: bool = False


class GraphData(BaseModel):
    """图谱数据"""
    nodes: list[GraphNode] = []
    links: list[GraphLink] = []
    legend: dict = {}


class EntityDetail(BaseModel):
    """实体详情 (v2.4: typed lists)"""
    id: str
    name: str
    type: str
    description: str = ""
    weight: float = 0.0
    related_entities: list[dict] = []
    related_documents: list[dict] = []

    model_config = {"from_attributes": True}


# ── Phase 1: 新增 GraphRAG API Schema ──────────────────────

class GraphPath(BaseModel):
    """实体间路径"""
    path: list[str] = []
    relations: list[str] = []
    length: int = 0
    total_weight: float = 0.0


class PathsResponse(BaseModel):
    """路径查询响应"""
    source: str
    target: str
    paths: list[GraphPath] = []
    count: int = 0


class CommunityInfo(BaseModel):
    """社区摘要信息"""
    id: str
    label: str = ""
    node_ids: list[str] = []
    node_count: int = 0
    top_entities: list[dict] = []
    description: str = ""


class CommunityDetail(BaseModel):
    """社区详细信息"""
    id: str
    label: str = ""
    node_count: int = 0
    nodes: list[dict] = []
    edges: list[dict] = []
    description: str = ""
    density: float = 0.0


class CommunitiesResponse(BaseModel):
    """社区列表响应"""
    kb_id: str
    communities: list[CommunityInfo] = []
    count: int = 0


class NeighborInfo(BaseModel):
    """实体邻居信息"""
    entity: dict = {}
    neighbors: list[dict] = []
    subgraph_nodes: list[dict] = []
    subgraph_edges: list[dict] = []


class GraphStats(BaseModel):
    """图谱统计信息"""
    node_count: int = 0
    edge_count: int = 0
    entity_type_distribution: dict = {}
    relation_type_distribution: dict = {}
    density: float = 0.0
    community_count: int = 0
    avg_degree: float = 0.0
    isolated_node_count: int = 0
    kb_count: int = 0
