"""
知识图谱 API - 图谱数据、实体详情
"""
import logging
import re
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.database import get_db
from app.models.document import Document
from app.schemas.graph import GraphData, GraphNode, GraphLink, EntityDetail
from app.utils.helpers import read_file_safe
from app.utils.file_parser import read_file_content

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/graph", tags=["知识图谱"])


# 冷色调配色（保留原有方案）
COLD_COLORS = [
    "#4F8CF7", "#5C6BC0", "#26A69A", "#7C5CFC", "#66BB6A",
    "#42A5F5", "#AB47BC", "#29B6F6", "#9CCC65", "#3F51B5",
    "#00ACC1", "#8E24AA", "#43A047", "#1E88E5", "#5E35B1",
    "#00897B", "#3949AB", "#039BE5", "#7CB342", "#6D4C41",
]


@router.get("/data", response_model=GraphData)
async def get_graph_data(
    kb_id: str = Query(None, description="知识库ID"),
    limit: int = Query(200, ge=10, le=2000, description="节点数量上限"),
    db: AsyncSession = Depends(get_db),
):
    """
    获取知识图谱数据（节点 + 边 + 图例）。
    目前基于文档内容的实体提取，后续 Phase 4 升级为两阶段管道。
    """
    # 查询文档
    query = select(Document).where(Document.status == "done")
    if kb_id:
        query = query.where(Document.kb_id == kb_id)
    result = await db.execute(query)
    docs = result.scalars().all()

    if not docs:
        # 返回演示数据
        return _get_demo_graph_data()

    # 尝试从文档获取图谱数据
    # （Phase 4 会实现完整的图谱存储和检索）
    return _get_demo_graph_data()


@router.get("/entity/{entity_id}", response_model=EntityDetail)
async def get_entity_detail(entity_id: str):
    """获取实体详情"""
    # Phase 4 实现完整的实体详情查询
    return EntityDetail(
        id=entity_id,
        name=f"实体 {entity_id}",
        type="概念",
        description="实体详情将在 Phase 4 实现",
        weight=0.5,
        related_entities=[],
        related_documents=[],
    )


def _get_demo_graph_data() -> GraphData:
    """返回演示图谱数据（用于测试）"""
    nodes = [
        GraphNode(id="1", name="知识图谱", type="概念", weight=0.9, color=COLD_COLORS[0]),
        GraphNode(id="2", name="RAG技术", type="方法", weight=0.85, color=COLD_COLORS[1]),
        GraphNode(id="3", name="向量检索", type="方法", weight=0.8, color=COLD_COLORS[2]),
        GraphNode(id="4", name="BM25检索", type="方法", weight=0.75, color=COLD_COLORS[2]),
        GraphNode(id="5", name="实体提取", type="方法", weight=0.8, color=COLD_COLORS[3]),
        GraphNode(id="6", name="DeepSeek V4", type="技术", weight=0.9, color=COLD_COLORS[4]),
        GraphNode(id="7", name="混合检索", type="方法", weight=0.85, color=COLD_COLORS[5]),
        GraphNode(id="8", name="重排序", type="方法", weight=0.7, color=COLD_COLORS[6]),
        GraphNode(id="9", name="教学知识库", type="概念", weight=0.95, color=COLD_COLORS[7]),
        GraphNode(id="10", name="LLM问答", type="方法", weight=0.85, color=COLD_COLORS[8]),
    ]

    links = [
        GraphLink(id="1", source="1", target="2", relation="包含", value=0.9, sentence="知识图谱包含RAG技术"),
        GraphLink(id="2", source="2", target="3", relation="包含", value=0.85, sentence="RAG技术包含向量检索"),
        GraphLink(id="3", source="2", target="4", relation="包含", value=0.8, sentence="RAG技术包含BM25检索"),
        GraphLink(id="4", source="7", target="3", relation="包含", value=0.9, sentence="混合检索包含向量检索"),
        GraphLink(id="5", source="7", target="4", relation="包含", value=0.9, sentence="混合检索包含BM25检索"),
        GraphLink(id="6", source="5", target="1", relation="应用", value=0.8, sentence="实体提取应用于知识图谱"),
        GraphLink(id="7", source="2", target="6", relation="依赖", value=0.85, sentence="RAG技术依赖DeepSeek V4"),
        GraphLink(id="8", source="7", target="8", relation="关联", value=0.7, sentence="混合检索后接重排序"),
        GraphLink(id="9", source="9", target="2", relation="应用", value=0.9, sentence="教学知识库应用RAG技术"),
        GraphLink(id="10", source="10", target="6", relation="依赖", value=0.85, sentence="LLM问答依赖DeepSeek V4"),
        GraphLink(id="11", source="10", target="2", relation="依赖", value=0.85, sentence="LLM问答依赖RAG技术"),
    ]

    legend = {
        "概念": COLD_COLORS[0],
        "方法": COLD_COLORS[2],
        "技术": COLD_COLORS[4],
    }

    return GraphData(nodes=nodes, links=links, legend=legend)
