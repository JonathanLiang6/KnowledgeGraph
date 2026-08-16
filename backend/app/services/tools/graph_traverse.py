"""图谱遍历工具"""
import logging

from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


async def graph_traverse(
    db: AsyncSession,
    kb_id: str,
    entity_name: str,
    max_hops: int = 2,
) -> str:
    """
    知识图谱多跳遍历 — 从指定实体出发沿关系路径探索关联实体。

    Args:
        db: 数据库会话
        kb_id: 知识库ID
        entity_name: 起始实体名称
        max_hops: 最大跳数

    Returns:
        格式化的遍历结果文本
    """
    from sqlalchemy import select

    from app.models.graph_entity import GraphEntity
    from app.services.graph_service import GraphService

    # 1. 定位起始实体（v4.0: 精确匹配优先，避免模糊匹配返回无关实体）
    stmt = select(GraphEntity).where(
        GraphEntity.kb_id == kb_id,
        GraphEntity.name == entity_name,
    )
    result = await db.execute(stmt)
    entities = result.scalars().all()

    # 精确匹配无结果时回退到包含匹配
    if not entities:
        stmt = select(GraphEntity).where(
            GraphEntity.kb_id == kb_id,
            GraphEntity.name.contains(entity_name),
        ).limit(3)
        result = await db.execute(stmt)
        entities = result.scalars().all()

    if not entities:
        return f"未在知识图谱中找到名为「{entity_name}」的实体。"

    lines = [f"图谱遍历: 从「{entity_name}」出发，最多 {max_hops} 跳:"]

    for entity in entities[:3]:
        neighbors = await GraphService.get_neighbors(db, entity.id, kb_id, max_hops)
        if not neighbors:
            continue

        lines.append(f"\n--- 实体: {entity.name} ({entity.entity_type}) ---")
        if entity.description:
            lines.append(f"描述: {entity.description[:200]}")

        for n in neighbors.get("neighbors", [])[:8]:
            lines.append(
                f"  -[{n.get('relation', '关联')}]-> {n['name']} "
                f"({n.get('type', '')}, 权重: {n.get('weight', 0):.2f})"
            )
        if len(neighbors.get("neighbors", [])) > 8:
            lines.append(f"  ... 还有 {len(neighbors['neighbors']) - 8} 个关联实体")

    if len(entities) > 3:
        lines.append(f"\n(仅展示前3个匹配实体的结果，共找到 {len(entities)} 个匹配)")

    return "\n".join(lines)
