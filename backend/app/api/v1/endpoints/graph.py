"""
知识图谱 API - 图谱数据、实体详情
"""
import json
import logging
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.database import get_db
from app.models.document import Document
from app.schemas.graph import GraphData, GraphNode, GraphLink, EntityDetail

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/graph", tags=["知识图谱"])


# 通用知识图谱实体配色
TYPE_COLORS = {
    "概念":      "#4F8CF7",
    "人物":      "#E57373",
    "事件":      "#FFB74D",
    "地点":      "#4DB6AC",
    "组织":      "#9575CD",
    "理论":      "#F06292",
    "方法":      "#64B5F6",
    "公式":      "#BA68C8",
    "定律":      "#FF8A65",
    "学科":      "#81C784",
    "技术":      "#4DD0E1",
    "应用":      "#AED581",
    "著作":      "#FFD54F",
    "术语":      "#90A4AE",
    "数据":      "#A1887F",
}
FALLBACK = list(TYPE_COLORS.values())


@router.get("/data", response_model=GraphData)
async def get_graph_data(
    kb_id: str = Query(None, description="知识库ID"),
    limit: int = Query(200, ge=10, le=2000, description="节点数量上限"),
    db: AsyncSession = Depends(get_db),
):
    """获取知识图谱数据"""
    query = select(Document).where(Document.status == "done")
    if kb_id:
        query = query.where(Document.kb_id == kb_id)
    result = await db.execute(query)
    docs = result.scalars().all()

    if not docs:
        return _get_demo_graph_data()

    nodes_map = {}
    links = []
    color_idx = 0
    entity_types = set()

    for doc in docs:
        if doc.graph_data:
            try:
                stored = json.loads(doc.graph_data) if isinstance(doc.graph_data, str) else doc.graph_data
                for node in stored.get("nodes", []):
                    nid = node.get("id", "")
                    if nid and nid not in nodes_map:
                        etype = node.get("type", "概念")
                        color = TYPE_COLORS.get(etype, FALLBACK[color_idx % len(FALLBACK)])
                        nodes_map[nid] = GraphNode(
                            id=nid,
                            name=node.get("name", nid),
                            type=etype,
                            weight=node.get("weight", 0.5),
                            color=color,
                        )
                        color_idx += 1
                        entity_types.add(etype)
                for link in stored.get("links", []):
                    links.append(GraphLink(
                        id=link.get("id", ""),
                        source=link.get("source", ""),
                        target=link.get("target", ""),
                        relation=link.get("relation", "关联"),
                        value=link.get("value", 0.5),
                        sentence=link.get("sentence", ""),
                    ))
            except (json.JSONDecodeError, TypeError) as e:
                logger.warning(f"解析文档图谱数据失败: {e}")

    if not nodes_map and docs:
        for doc in docs:
            nid = doc.id
            if nid not in nodes_map:
                nodes_map[nid] = GraphNode(
                    id=nid,
                    name=(doc.filename or "文档").rsplit(".", 1)[0][:30],
                    type="概念",
                    weight=min(doc.entity_count / 100.0, 1.0) if doc.entity_count else 0.5,
                    color=TYPE_COLORS["概念"],
                )
                color_idx += 1
                entity_types.add("概念")

    nodes = list(nodes_map.values())[:limit]

    legend = {}
    for i, t in enumerate(sorted(entity_types)):
        legend[t] = TYPE_COLORS.get(t, FALLBACK[i % len(FALLBACK)])
    if not legend:
        legend = {"概念": TYPE_COLORS["概念"]}

    if not nodes:
        return _get_demo_graph_data()

    return GraphData(nodes=nodes, links=links[:limit], legend=legend)


@router.get("/entity/{entity_id}", response_model=EntityDetail)
async def get_entity_detail(entity_id: str, db: AsyncSession = Depends(get_db)):
    """获取实体详情"""
    result = await db.execute(select(Document).where(Document.graph_data.isnot(None)))
    docs = result.scalars().all()
    for doc in docs:
        try:
            stored = json.loads(doc.graph_data) if isinstance(doc.graph_data, str) else doc.graph_data
            for node in stored.get("nodes", []):
                if node.get("id") == entity_id:
                    return EntityDetail(
                        id=entity_id,
                        name=node.get("name", entity_id),
                        type=node.get("type", "概念"),
                        description=node.get("description", ""),
                        weight=node.get("weight", 0.5),
                        related_entities=[],
                        related_documents=[doc.filename],
                    )
        except (json.JSONDecodeError, TypeError):
            continue
    raise HTTPException(status_code=404, detail="实体不存在")


def _get_demo_graph_data() -> GraphData:
    """通用知识图谱演示数据"""
    nodes = [
        # 概念层
        GraphNode(id="1",  name="知识图谱",    type="概念", weight=0.95, color=TYPE_COLORS["概念"]),
        GraphNode(id="2",  name="人工智能",    type="概念", weight=0.92, color=TYPE_COLORS["概念"]),
        GraphNode(id="3",  name="机器学习",    type="概念", weight=0.88, color=TYPE_COLORS["概念"]),
        GraphNode(id="4",  name="自然语言处理", type="概念", weight=0.85, color=TYPE_COLORS["概念"]),
        # 人物层
        GraphNode(id="5",  name="艾伦·图灵",   type="人物", weight=0.90, color=TYPE_COLORS["人物"]),
        GraphNode(id="6",  name="约翰·麦卡锡",  type="人物", weight=0.78, color=TYPE_COLORS["人物"]),
        GraphNode(id="7",  name="杰弗里·辛顿",  type="人物", weight=0.82, color=TYPE_COLORS["人物"]),
        # 理论层
        GraphNode(id="8",  name="深度学习",     type="理论", weight=0.87, color=TYPE_COLORS["理论"]),
        GraphNode(id="9",  name="图灵测试",     type="理论", weight=0.75, color=TYPE_COLORS["理论"]),
        GraphNode(id="10", name="注意力机制",   type="理论", weight=0.83, color=TYPE_COLORS["理论"]),
        # 方法层
        GraphNode(id="11", name="监督学习",     type="方法", weight=0.80, color=TYPE_COLORS["方法"]),
        GraphNode(id="12", name="无监督学习",   type="方法", weight=0.76, color=TYPE_COLORS["方法"]),
        GraphNode(id="13", name="强化学习",     type="方法", weight=0.78, color=TYPE_COLORS["方法"]),
        GraphNode(id="14", name="迁移学习",     type="方法", weight=0.72, color=TYPE_COLORS["方法"]),
        # 技术层
        GraphNode(id="15", name="Transformer",  type="技术", weight=0.89, color=TYPE_COLORS["技术"]),
        GraphNode(id="16", name="BERT",         type="技术", weight=0.84, color=TYPE_COLORS["技术"]),
        GraphNode(id="17", name="GPT",          type="技术", weight=0.86, color=TYPE_COLORS["技术"]),
        GraphNode(id="18", name="CNN",          type="技术", weight=0.80, color=TYPE_COLORS["技术"]),
        GraphNode(id="19", name="RNN",          type="技术", weight=0.77, color=TYPE_COLORS["技术"]),
        # 应用层
        GraphNode(id="20", name="智能问答",     type="应用", weight=0.81, color=TYPE_COLORS["应用"]),
        GraphNode(id="21", name="机器翻译",     type="应用", weight=0.74, color=TYPE_COLORS["应用"]),
        GraphNode(id="22", name="图像识别",     type="应用", weight=0.76, color=TYPE_COLORS["应用"]),
        # 学科层
        GraphNode(id="23", name="计算机科学",   type="学科", weight=0.91, color=TYPE_COLORS["学科"]),
        GraphNode(id="24", name="数学",         type="学科", weight=0.88, color=TYPE_COLORS["学科"]),
        GraphNode(id="25", name="语言学",       type="学科", weight=0.73, color=TYPE_COLORS["学科"]),
        GraphNode(id="26", name="认知科学",     type="学科", weight=0.70, color=TYPE_COLORS["学科"]),
        # 地点 / 组织
        GraphNode(id="27", name="MIT",           type="组织", weight=0.72, color=TYPE_COLORS["组织"]),
        GraphNode(id="28", name="Google DeepMind", type="组织", weight=0.79, color=TYPE_COLORS["组织"]),
        GraphNode(id="29", name="OpenAI",        type="组织", weight=0.77, color=TYPE_COLORS["组织"]),
    ]

    links = [
        # 概念层级
        GraphLink(id="1",  source="2",  target="23", relation="属于",   value=0.90, sentence="人工智能属于计算机科学"),
        GraphLink(id="2",  source="3",  target="2",  relation="子领域", value=0.92, sentence="机器学习是人工智能的子领域"),
        GraphLink(id="3",  source="4",  target="2",  relation="子领域", value=0.88, sentence="自然语言处理是人工智能的子领域"),
        GraphLink(id="4",  source="4",  target="3",  relation="交叉",   value=0.82, sentence="自然语言处理与机器学习交叉"),
        # 人物关系
        GraphLink(id="5",  source="5",  target="9",  relation="提出",   value=0.85, sentence="图灵提出图灵测试"),
        GraphLink(id="6",  source="6",  target="2",  relation="命名",   value=0.80, sentence="麦卡锡命名人工智能"),
        GraphLink(id="7",  source="7",  target="8",  relation="贡献",   value=0.86, sentence="辛顿对深度学习有重大贡献"),
        GraphLink(id="8",  source="7",  target="27", relation="任职",   value=0.60, sentence="辛顿曾任职于MIT"),
        # 理论与方法
        GraphLink(id="9",  source="8",  target="3",  relation="属于",   value=0.90, sentence="深度学习是机器学习的分支"),
        GraphLink(id="10", source="10", target="15", relation="核心",   value=0.88, sentence="注意力机制是Transformer的核心"),
        GraphLink(id="11", source="11", target="3",  relation="属于",   value=0.85, sentence="监督学习属于机器学习"),
        GraphLink(id="12", source="12", target="3",  relation="属于",   value=0.84, sentence="无监督学习属于机器学习"),
        GraphLink(id="13", source="13", target="3",  relation="属于",   value=0.83, sentence="强化学习属于机器学习"),
        GraphLink(id="14", source="14", target="3",  relation="属于",   value=0.78, sentence="迁移学习属于机器学习"),
        # 技术实现
        GraphLink(id="15", source="15", target="10", relation="基于",   value=0.90, sentence="Transformer基于注意力机制"),
        GraphLink(id="16", source="16", target="15", relation="基于",   value=0.86, sentence="BERT基于Transformer架构"),
        GraphLink(id="17", source="17", target="15", relation="基于",   value=0.88, sentence="GPT基于Transformer架构"),
        GraphLink(id="18", source="18", target="8",  relation="属于",   value=0.82, sentence="CNN是深度学习的重要架构"),
        GraphLink(id="19", source="19", target="8",  relation="属于",   value=0.78, sentence="RNN是深度学习的重要架构"),
        GraphLink(id="20", source="19", target="10", relation="改进",   value=0.72, sentence="注意力机制改进了RNN的缺陷"),
        # 应用
        GraphLink(id="21", source="20", target="4",  relation="应用",   value=0.84, sentence="智能问答是NLP的典型应用"),
        GraphLink(id="22", source="20", target="17", relation="基于",   value=0.82, sentence="智能问答常基于GPT"),
        GraphLink(id="23", source="21", target="4",  relation="应用",   value=0.80, sentence="机器翻译是NLP的典型应用"),
        GraphLink(id="24", source="22", target="18", relation="基于",   value=0.78, sentence="图像识别基于CNN"),
        # 组织和学科
        GraphLink(id="25", source="28", target="7",  relation="关联",   value=0.65, sentence="DeepMind与辛顿的研究相关"),
        GraphLink(id="26", source="29", target="17", relation="开发",   value=0.84, sentence="OpenAI开发了GPT系列"),
        GraphLink(id="27", source="23", target="24", relation="依赖",   value=0.92, sentence="计算机科学依赖数学基础"),
        GraphLink(id="28", source="24", target="25", relation="支撑",   value=0.76, sentence="数学支撑语言学模型"),
        GraphLink(id="29", source="26", target="2",  relation="交叉",   value=0.74, sentence="认知科学与人工智能交叉研究"),
        GraphLink(id="30", source="3",  target="24", relation="依赖",   value=0.86, sentence="机器学习依赖数学"),
    ]

    legend = {}
    for n in nodes:
        if n.type not in legend:
            legend[n.type] = n.color

    return GraphData(nodes=nodes, links=links, legend=legend)
