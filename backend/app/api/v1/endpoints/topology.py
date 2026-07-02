"""
拓扑导航 API - v3.2 Q10

个人知识库拓扑启动台的 CRUD 端点。
管理 topology_nodes 和 topology_edges 的增删改查。
"""
import logging
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.core.database import get_db
from app.models.topology import TopologyNode, TopologyEdge
from app.schemas.topology import (
    TopologyNodeCreate, TopologyNodeUpdate, TopologyNodeOut,
    TopologyEdgeCreate, TopologyEdgeOut, TopologyData,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/topology", tags=["拓扑导航"])


# ── 获取全量拓扑数据 ────────────────────────────────────────────────

@router.get("", response_model=TopologyData)
async def get_topology(db: AsyncSession = Depends(get_db)):
    """获取全量拓扑数据（Nodes + Edges），自动清理重复根节点"""
    # 获取所有节点
    nodes_result = await db.execute(select(TopologyNode).order_by(TopologyNode.created_at))
    nodes = list(nodes_result.scalars().all())

    # v3.2: 清理重复根节点（保留最早创建的）并删除其关联边
    root_nodes = [n for n in nodes if n.is_root]
    if len(root_nodes) > 1:
        root_nodes.sort(key=lambda n: n.created_at)
        keep = root_nodes[0]
        to_delete = root_nodes[1:]
        for dup in to_delete:
            # 删除重复根节点的所有边
            edge_stmt = select(TopologyEdge).where(
                (TopologyEdge.source_id == dup.id) | (TopologyEdge.target_id == dup.id)
            )
            edge_result = await db.execute(edge_stmt)
            for edge in edge_result.scalars():
                await db.delete(edge)
            await db.delete(dup)
        await db.commit()
        logger.info(f"清理 {len(to_delete)} 个重复根节点，保留: {keep.name}")
        # 重新加载
        nodes_result = await db.execute(select(TopologyNode).order_by(TopologyNode.created_at))
        nodes = list(nodes_result.scalars().all())

    # 获取所有边
    edges_result = await db.execute(select(TopologyEdge))
    edges = edges_result.scalars().all()

    return TopologyData(
        nodes=[TopologyNodeOut.model_validate(n) for n in nodes],
        edges=[TopologyEdgeOut.model_validate(e) for e in edges],
    )


# ── 节点 CRUD ───────────────────────────────────────────────────────

@router.post("/nodes", response_model=TopologyNodeOut, status_code=201)
async def create_topology_node(
    payload: TopologyNodeCreate,
    db: AsyncSession = Depends(get_db),
):
    """创建拓扑节点（知识库入口或文件夹）。首个节点自动成为根节点。"""
    # 检查是否已存在根节点
    root_stmt = select(TopologyNode).where(TopologyNode.is_root == True)
    root_result = await db.execute(root_stmt)
    root = root_result.scalar_one_or_none()

    # 如果没有根节点，首个节点自动成为根节点
    if not root:
        node = TopologyNode(
            name=payload.name,
            icon=payload.icon,
            kb_id=payload.kb_id,
            position_x=payload.position_x,
            position_y=payload.position_y,
            is_root=True,
        )
        db.add(node)
        await db.commit()
        await db.refresh(node)
        logger.info(f"创建根节点: {node.name}")
        return node

    node = TopologyNode(
        name=payload.name,
        icon=payload.icon,
        kb_id=payload.kb_id,
        position_x=payload.position_x,
        position_y=payload.position_y,
        is_root=False,
    )
    db.add(node)
    await db.commit()
    await db.refresh(node)
    logger.info(f"创建拓扑节点: {node.name}")
    return node


@router.put("/nodes/{node_id}", response_model=TopologyNodeOut)
async def update_topology_node(
    node_id: str,
    payload: TopologyNodeUpdate,
    db: AsyncSession = Depends(get_db),
):
    """更新拓扑节点（名称、绑定的 kb_id、坐标）"""
    stmt = select(TopologyNode).where(TopologyNode.id == node_id)
    result = await db.execute(stmt)
    node = result.scalar_one_or_none()
    if not node:
        raise HTTPException(status_code=404, detail="节点不存在")

    if payload.name is not None:
        node.name = payload.name
    if payload.icon is not None:
        node.icon = payload.icon
    if payload.kb_id is not None:
        node.kb_id = payload.kb_id
    if payload.position_x is not None:
        node.position_x = payload.position_x
    if payload.position_y is not None:
        node.position_y = payload.position_y

    await db.commit()
    await db.refresh(node)
    return node


@router.delete("/nodes/{node_id}")
async def delete_topology_node(
    node_id: str,
    db: AsyncSession = Depends(get_db),
):
    """删除拓扑节点（不级联删除关联的知识库）"""
    stmt = select(TopologyNode).where(TopologyNode.id == node_id)
    result = await db.execute(stmt)
    node = result.scalar_one_or_none()
    if not node:
        raise HTTPException(status_code=404, detail="节点不存在")

    if node.is_root:
        raise HTTPException(status_code=400, detail="不能删除根节点")

    # 删除该节点的所有边
    edge_stmt = select(TopologyEdge).where(
        (TopologyEdge.source_id == node_id) | (TopologyEdge.target_id == node_id)
    )
    edge_result = await db.execute(edge_stmt)
    for edge in edge_result.scalars():
        await db.delete(edge)

    await db.delete(node)
    await db.commit()
    return {"status": "ok", "message": f"节点 '{node.name}' 已删除"}


# ── 边 CRUD ─────────────────────────────────────────────────────────

@router.post("/edges", response_model=TopologyEdgeOut, status_code=201)
async def create_topology_edge(
    payload: TopologyEdgeCreate,
    db: AsyncSession = Depends(get_db),
):
    """建立拓扑连接（source_id → target_id）"""
    # 验证节点存在
    for nid in [payload.source_id, payload.target_id]:
        stmt = select(TopologyNode).where(TopologyNode.id == nid)
        result = await db.execute(stmt)
        if not result.scalar_one_or_none():
            raise HTTPException(status_code=404, detail=f"节点 {nid} 不存在")

    # 检查是否已存在相同边
    existing_stmt = select(TopologyEdge).where(
        (TopologyEdge.source_id == payload.source_id) &
        (TopologyEdge.target_id == payload.target_id)
    )
    existing = await db.execute(existing_stmt)
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="该连接已存在")

    edge = TopologyEdge(
        source_id=payload.source_id,
        target_id=payload.target_id,
    )
    db.add(edge)
    await db.commit()
    await db.refresh(edge)
    return edge


@router.delete("/edges/{edge_id}")
async def delete_topology_edge(
    edge_id: str,
    db: AsyncSession = Depends(get_db),
):
    """断开拓扑连接"""
    stmt = select(TopologyEdge).where(TopologyEdge.id == edge_id)
    result = await db.execute(stmt)
    edge = result.scalar_one_or_none()
    if not edge:
        raise HTTPException(status_code=404, detail="边不存在")

    await db.delete(edge)
    await db.commit()
    return {"status": "ok", "message": "边已删除"}
