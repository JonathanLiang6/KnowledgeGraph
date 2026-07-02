"""实体查询工具"""
import logging
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


async def entity_lookup(
    db: AsyncSession,
    kb_id: str,
    entity_name: str,
) -> str:
    """
    实体详情查询 — 查找知识图谱中实体的属性、描述和关联信息。

    Args:
        db: 数据库会话
        kb_id: 知识库ID
        entity_name: 要查询的实体名称

    Returns:
        格式化的实体信息文本
    """
    from app.models.graph_entity import GraphEntity
    from app.services.graph_service import GraphService
    from sqlalchemy import select

    # 精确匹配优先
    stmt = select(GraphEntity).where(
        GraphEntity.kb_id == kb_id,
        GraphEntity.name == entity_name,
    )
    result = await db.execute(stmt)
    entity = result.scalar_one_or_none()

    # 模糊匹配
    if not entity:
        stmt = select(GraphEntity).where(
            GraphEntity.kb_id == kb_id,
            GraphEntity.name.contains(entity_name),
        ).limit(1)
        result = await db.execute(stmt)
        entity = result.scalar_one_or_none()

    if not entity:
        return f"未在知识图谱中找到名为「{entity_name}」的实体。"

    lines = [
        f"实体详情: {entity.name}",
        f"类型: {entity.entity_type}",
        f"权重: {entity.weight:.3f}",
    ]
    if entity.description:
        lines.append(f"描述: {entity.description}")

    # 获取邻居
    neighbors = await GraphService.get_neighbors(db, entity.id, kb_id, hops=1)
    if neighbors and neighbors.get("neighbors"):
        lines.append(f"\n直接关联 ({len(neighbors['neighbors'])} 个):")
        for n in neighbors["neighbors"]:
            lines.append(
                f"  -[{n.get('relation', '关联')}]-> {n['name']} "
                f"({n.get('type', '')})"
            )

    # 来源文档
    if entity.source_doc_ids:
        sources = entity.source_doc_ids
        if isinstance(sources, list) and len(sources) > 0:
            doc_ids = {s.get("doc_id", "") for s in sources if s.get("doc_id")}
            lines.append(f"\n来源文档数: {len(doc_ids)}")

    return "\n".join(lines)
