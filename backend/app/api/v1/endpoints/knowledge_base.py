"""
知识库管理 API - CRUD 操作
"""
import logging
import os

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.document import Document
from app.models.knowledge_base import KnowledgeBase
from app.schemas.knowledge_base import (
    KnowledgeBaseCreate,
    KnowledgeBaseListResponse,
    KnowledgeBaseResponse,
    KnowledgeBaseUpdate,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/knowledge-bases", tags=["知识库管理"])


def _kb_response(kb: KnowledgeBase, doc_count: int = 0) -> KnowledgeBaseResponse:
    """构建知识库响应"""
    return KnowledgeBaseResponse(
        id=kb.id,
        name=kb.name,
        description=kb.description,
        created_at=kb.created_at,
        updated_at=kb.updated_at,
        document_count=doc_count,
    )


async def _get_kb_with_count(db: AsyncSession, kb_id: str):
    """获取单个知识库及其文档数（单次查询）"""
    doc_count_subq = (
        select(func.count(Document.id))
        .where(Document.kb_id == kb_id)
        .scalar_subquery()
    )
    stmt = select(KnowledgeBase, doc_count_subq.label("doc_count")).where(
        KnowledgeBase.id == kb_id
    )
    result = await db.execute(stmt)
    row = result.one_or_none()
    if row is None:
        return None, 0
    return row[0], row[1] or 0


@router.get("", response_model=KnowledgeBaseListResponse)
async def list_knowledge_bases(db: AsyncSession = Depends(get_db)):
    """获取所有知识库列表（单次查询带文档数）"""
    # 子查询：每个 KB 的文档数
    doc_count_subq = (
        select(Document.kb_id, func.count(Document.id).label("doc_count"))
        .group_by(Document.kb_id)
        .subquery()
    )
    stmt = (
        select(KnowledgeBase, func.coalesce(doc_count_subq.c.doc_count, 0))
        .outerjoin(doc_count_subq, KnowledgeBase.id == doc_count_subq.c.kb_id)
        .order_by(KnowledgeBase.updated_at.desc())
    )
    result = await db.execute(stmt)
    rows = result.all()

    items = [_kb_response(kb, doc_count) for kb, doc_count in rows]
    return KnowledgeBaseListResponse(items=items, total=len(items))


@router.post("", response_model=KnowledgeBaseResponse, status_code=201)
async def create_knowledge_base(
    data: KnowledgeBaseCreate,
    db: AsyncSession = Depends(get_db),
):
    """创建新知识库"""
    kb = KnowledgeBase(name=data.name, description=data.description)
    db.add(kb)
    await db.flush()
    await db.refresh(kb)
    return _kb_response(kb, 0)


@router.get("/{kb_id}", response_model=KnowledgeBaseResponse)
async def get_knowledge_base(kb_id: str, db: AsyncSession = Depends(get_db)):
    """获取单个知识库详情"""
    kb, doc_count = await _get_kb_with_count(db, kb_id)
    if not kb:
        raise HTTPException(status_code=404, detail="知识库不存在")
    return _kb_response(kb, doc_count)


@router.put("/{kb_id}", response_model=KnowledgeBaseResponse)
async def update_knowledge_base(
    kb_id: str,
    data: KnowledgeBaseUpdate,
    db: AsyncSession = Depends(get_db),
):
    """更新知识库"""
    kb, _ = await _get_kb_with_count(db, kb_id)
    if not kb:
        raise HTTPException(status_code=404, detail="知识库不存在")

    if data.name is not None:
        kb.name = data.name
    if data.description is not None:
        kb.description = data.description

    await db.flush()
    await db.refresh(kb)

    # 重新获取文档数
    _, doc_count = await _get_kb_with_count(db, kb_id)
    return _kb_response(kb, doc_count)


@router.delete("/{kb_id}")
async def delete_knowledge_base(
    kb_id: str,
    confirm: bool = Query(default=False, description="必须传 confirm=true 执行不可逆删除"),
    db: AsyncSession = Depends(get_db),
):
    """删除知识库及其所有文档（含物理文件清理）"""
    if not confirm:
        raise HTTPException(
            status_code=400,
            detail="删除操作不可逆：请显式传递 confirm=true 以确认删除",
        )
    result = await db.execute(select(KnowledgeBase).where(KnowledgeBase.id == kb_id))
    kb = result.scalar_one_or_none()
    if not kb:
        raise HTTPException(status_code=404, detail="知识库不存在")

    # 收集文档ID和文件路径（在级联删除前）
    docs_result = await db.execute(
        select(Document.id, Document.file_path).where(Document.kb_id == kb_id)
    )
    doc_rows = docs_result.all()
    doc_ids = [row[0] for row in doc_rows]
    file_paths = [row[1] for row in doc_rows if row[1]]

    kb_name = kb.name

    # v2.5: 先清理检索引擎中的索引 (使用模块级单例)
    try:
        from app.services.hybrid_search import hybrid_search_service
        for doc_id in doc_ids:
            hybrid_search_service.remove_document(doc_id)
        logger.info(f"已清理 {len(doc_ids)} 个文档的检索索引")
    except Exception as e:
        logger.warning(f"清理检索索引失败（非致命）: {e}")

    # 删除关联的拓扑节点（如果存在）
    try:
        from app.models.topology import TopologyEdge, TopologyNode
        node_stmt = select(TopologyNode).where(TopologyNode.kb_id == kb_id)
        node_result = await db.execute(node_stmt)
        node = node_result.scalar_one_or_none()
        if node:
            # 删除该节点的所有边
            edge_stmt = select(TopologyEdge).where(
                (TopologyEdge.source_id == node.id) | (TopologyEdge.target_id == node.id)
            )
            edge_result = await db.execute(edge_stmt)
            for edge in edge_result.scalars():
                await db.delete(edge)
            await db.delete(node)
            logger.info(f"已删除关联的拓扑节点: {node.name}")
    except Exception as e:
        logger.warning(f"清理拓扑节点失败（非致命）: {e}")

    # v4.1: 显式清理图谱数据（SQLite 未启用 PRAGMA foreign_keys，FK CASCADE 不生效）
    try:
        from sqlalchemy import delete as sa_delete

        from app.models.graph_entity import GraphEntity, GraphRelation
        await db.execute(sa_delete(GraphRelation).where(GraphRelation.kb_id == kb_id))
        await db.execute(sa_delete(GraphEntity).where(GraphEntity.kb_id == kb_id))
        logger.info(f"已清理知识库图谱数据: {kb_id}")
    except Exception as e:
        logger.warning(f"清理图谱数据失败（非致命）: {e}")

    # v4.1: 失效检索缓存（KB 删除后不再返回陈旧结果）与图谱缓存
    try:
        from app.services.rag_service import invalidate_kb_cache
        invalidate_kb_cache(kb_id)
    except Exception as e:
        logger.warning(f"检索缓存失效失败（非致命）: {e}")
    try:
        from app.services.graph_service import GraphService
        GraphService._invalidate_nx_cache(kb_id)
    except Exception as e:
        logger.warning(f"图谱缓存失效失败（非致命）: {e}")

    # v4.1: 清理各文档的阶段产物
    try:
        from app.tasks.document_tasks import cleanup_doc_artifacts
        for did in doc_ids:
            cleanup_doc_artifacts(did)
    except Exception as e:
        logger.warning(f"清理阶段产物失败（非致命）: {e}")

    # 删除 KB（级联删除文档记录）
    await db.delete(kb)
    await db.flush()

    # 清理物理文件
    for fp in file_paths:
        if os.path.exists(fp):
            try:
                os.remove(fp)
            except OSError as e:
                logger.warning(f"删除文件失败: {fp}, {e}")

    return {"message": f"知识库 '{kb_name}' 已删除", "id": kb_id}
