"""
知识图谱 API - 图谱数据、实体详情、路径查询、社区检测 (Phase 1)
"""
import json
import logging
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.database import get_db
from app.core.colors import TYPE_COLORS, get_color_for_type, get_legend
from app.models.document import Document
from app.schemas.graph import (
    GraphData, GraphNode, GraphLink, EntityDetail,
    GraphPath, PathsResponse, CommunityInfo, CommunityDetail,
    CommunitiesResponse, NeighborInfo, GraphStats,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/graph", tags=["知识图谱"])


# ── Phase 1: 新增 GraphRAG API 端点 ──────────────────────────
# 注意: /entity/{entity_id}/neighbors 必须在 /entity/{entity_id} 之前定义


@router.get("/paths")
async def find_paths(
    source: str = Query(..., description="起始实体ID"),
    target: str = Query(..., description="目标实体ID"),
    kb_id: str = Query(..., description="知识库ID"),
    max_hops: int = Query(3, ge=1, le=6, description="最大跳数"),
    db: AsyncSession = Depends(get_db),
):
    """查询两个实体之间的所有路径（多跳推理）"""
    from app.services.graph_service import GraphService

    paths = await GraphService.find_paths(db, source, target, kb_id, max_hops)
    formatted = [
        GraphPath(
            path=p["path"], relations=p["relations"],
            length=p["length"], total_weight=p["total_weight"],
        )
        for p in paths
    ]
    return PathsResponse(source=source, target=target, paths=formatted, count=len(formatted))


@router.get("/communities")
async def get_communities(
    kb_id: str = Query(..., description="知识库ID"),
    min_size: int = Query(None, description="最小社区节点数"),
    db: AsyncSession = Depends(get_db),
):
    """获取知识图谱的 Louvain 社区检测结果"""
    from app.services.graph_service import GraphService

    communities = await GraphService.detect_communities(db, kb_id, min_size)
    formatted = [
        CommunityInfo(
            id=c["id"], label=c["label"], node_ids=c["node_ids"],
            node_count=c["node_count"], top_entities=c["top_entities"],
            description=c.get("description", ""),
        )
        for c in communities
    ]
    return CommunitiesResponse(kb_id=kb_id, communities=formatted, count=len(formatted))


@router.get("/communities/{community_id}")
async def get_community_detail(
    community_id: str,
    kb_id: str = Query(..., description="知识库ID"),
    db: AsyncSession = Depends(get_db),
):
    """获取指定社区的详细信息（含所有节点和边）"""
    from app.services.graph_service import GraphService

    detail = await GraphService.get_community_summary(db, community_id, kb_id)
    if not detail:
        raise HTTPException(status_code=404, detail="社区不存在")
    return CommunityDetail(**detail)


@router.get("/entity/{entity_id}/neighbors")
async def get_entity_neighbors(
    entity_id: str,
    kb_id: str = Query(None, description="知识库ID"),
    hops: int = Query(1, ge=1, le=3, description="跳数"),
    db: AsyncSession = Depends(get_db),
):
    """获取实体的邻居子图（BFS 展开）"""
    from app.services.graph_service import GraphService

    result = await GraphService.get_neighbors(db, entity_id, kb_id, hops)
    if not result:
        raise HTTPException(status_code=404, detail="实体不存在")
    return NeighborInfo(**result)


@router.post("/cleanup-orphans")
async def cleanup_orphan_nodes(
    kb_id: str = Query(..., description="知识库ID"),
    db: AsyncSession = Depends(get_db),
):
    """v3.2: 清理知识库中无法建立任何链接的孤立节点"""
    from app.services.graph_service import GraphService

    result = await GraphService.clean_orphan_nodes(db, kb_id)
    return {"status": "ok", "kb_id": kb_id, "deleted": result["deleted"]}


@router.get("/stats")
async def get_graph_stats(
    kb_id: str = Query(None, description="知识库ID（可选，不传则返回全局统计）"),
    db: AsyncSession = Depends(get_db),
):
    """获取知识图谱统计信息"""
    from app.services.graph_service import GraphService

    stats = await GraphService.get_graph_stats(db, kb_id)
    return GraphStats(**stats)


# ── 现有端点（向后兼容）──────────────────────────────────────


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
                stored = doc.graph_data  # v2.4: JSON 列自动反序列化
                for node in stored.get("nodes", []):
                    nid = node.get("id", "")
                    if nid and nid not in nodes_map:
                        etype = node.get("type", "概念")
                        color = get_color_for_type(etype, color_idx)
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
                        dashed=link.get("dashed", False),
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

    # 孤立节点桥接 — 将散落小分量连入核心网络
    nodes, links = _bridge_isolated_nodes(nodes, links)

    legend = get_legend(entity_types) if entity_types else {"概念": TYPE_COLORS["概念"]}

    if not nodes:
        return _get_demo_graph_data()

    return GraphData(nodes=nodes, links=links[:limit], legend=legend)


@router.get("/entity/{entity_id}", response_model=EntityDetail)
async def get_entity_detail(
    entity_id: str,
    kb_id: str = Query(None, description="知识库ID"),
    db: AsyncSession = Depends(get_db),
):
    """获取实体详情（含关联实体和来源文档）"""
    query = select(Document).where(Document.graph_data.isnot(None))
    if kb_id:
        query = query.where(Document.kb_id == kb_id)
    result = await db.execute(query)
    docs = result.scalars().all()

    all_links = []
    all_nodes = {}
    target_node = None

    for doc in docs:
        try:
            stored = doc.graph_data  # v2.4: JSON 列自动反序列化
            if not stored:
                continue
            for node in stored.get("nodes", []):
                nid = node.get("id", "")
                if nid and nid not in all_nodes:
                    all_nodes[nid] = node
                    if nid == entity_id:
                        target_node = node
            for link in stored.get("links", []):
                all_links.append(link)
        except (json.JSONDecodeError, TypeError):
            continue

    if not target_node:
        raise HTTPException(status_code=404, detail="实体不存在")

    # 收集关联实体
    related_entities = []
    related_docs = [doc.filename for doc in docs if doc.filename]
    seen_related = set()

    for link in all_links:
        src = link.get("source", "")
        tgt = link.get("target", "")
        other_id = None
        if src == entity_id:
            other_id = tgt
        elif tgt == entity_id:
            other_id = src
        if other_id and other_id in all_nodes and other_id not in seen_related:
            other = all_nodes[other_id]
            related_entities.append({
                "id": other_id,
                "name": other.get("name", other_id),
                "type": other.get("type", "概念"),
                "relation": link.get("relation", "关联"),
                "color": other.get("color", get_color_for_type(other.get("type", "概念"), 0)),
                "weight": other.get("weight", 0.5),
            })
            seen_related.add(other_id)

    return EntityDetail(
        id=entity_id,
        name=target_node.get("name", entity_id),
        type=target_node.get("type", "概念"),
        description=target_node.get("description", ""),
        weight=target_node.get("weight", 0.5),
        related_entities=related_entities,
        related_documents=related_docs,
    )


def _bridge_isolated_nodes(nodes: list, links: list) -> tuple:
    """
    将孤立节点和极小连通分量通过虚线弱关联连接到核心网络。

    算法:
    1. Union-Find 计算连通分量
    2. 识别主分量 (节点数 >= 3 或包含 top-5 高权重节点)
    3. 对非主分量节点计算与核心节点的名称相似度
    4. 创建 dashed 弱关联边
    """
    if len(nodes) < 3:
        return nodes, links

    n = len(nodes)
    node_ids = [nd.id for nd in nodes]
    id_to_idx = {nid: i for i, nid in enumerate(node_ids)}
    name_to_id = {nd.name: nd.id for nd in nodes}

    # Union-Find
    parent = list(range(n))

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a, b):
        pa, pb = find(a), find(b)
        if pa != pb:
            parent[pb] = pa

    for link in links:
        si = id_to_idx.get(link.source)
        ti = id_to_idx.get(link.target)
        if si is not None and ti is not None:
            union(si, ti)

    # 分组
    comps: dict[int, list[int]] = {}
    for i in range(n):
        r = find(i)
        comps.setdefault(r, []).append(i)

    # 识别主分量
    sorted_nodes = sorted(nodes, key=lambda nd: nd.weight or 0, reverse=True)
    top5_ids = {nd.id for nd in sorted_nodes[:5]}
    main_root = None
    main_size = 0
    for root, indices in comps.items():
        if len(indices) > main_size:
            main_size = len(indices)
            main_root = root

    # 主分量: 最大分量 或 包含 top-5 节点 或 size >= 3
    main_roots = set()
    for root, indices in comps.items():
        comp_ids = {node_ids[i] for i in indices}
        if len(indices) >= 3 or bool(comp_ids & top5_ids) or root == main_root:
            main_roots.add(root)

    if not main_roots:
        return nodes, links

    # 核心节点池
    core_pool = []
    for root in main_roots:
        for i in comps[root]:
            core_pool.append(nodes[i])
    core_names = {nd.name for nd in core_pool}

    # 桥接
    max_new_edges = max(1, n // 3)
    new_edge_count = 0
    existing_edges = {(l.source, l.target) for l in links}
    existing_edges.update({(l.target, l.source) for l in links})

    new_links = list(links)

    for root, indices in comps.items():
        if root in main_roots:
            continue
        for i in indices:
            if new_edge_count >= max_new_edges:
                break
            node = nodes[i]
            if node.name in core_names:
                continue

            # 计算与核心节点的名称相似度 (Jaccard)
            best_core = None
            best_sim = 0.0
            n_chars = set(node.name)
            for core in core_pool:
                c_chars = set(core.name)
                intersection = n_chars & c_chars
                union = n_chars | c_chars
                sim = len(intersection) / len(union) if union else 0
                if sim > best_sim and sim > 0.15:  # 最低相似阈值
                    best_sim = sim
                    best_core = core

            if best_core and (node.id, best_core.id) not in existing_edges:
                new_links.append(GraphLink(
                    id=f"bridge_{node.id}_{best_core.id}",
                    source=node.id,
                    target=best_core.id,
                    relation="弱关联",
                    value=round(0.1 + best_sim * 0.15, 3),
                    sentence="",
                    dashed=True,
                ))
                existing_edges.add((node.id, best_core.id))
                existing_edges.add((best_core.id, node.id))
                new_edge_count += 1

    if new_edge_count > 0:
        logger.info(f"图谱桥接: {new_edge_count} 条虚线弱关联边")

    return nodes, new_links


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
