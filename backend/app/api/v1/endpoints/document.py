"""
文档管理 API - 上传、列表、处理、删除
"""
import os
import uuid
import logging
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.core.database import get_db
from app.core.config import config
from app.models.document import Document, DocumentStatus
from app.models.knowledge_base import KnowledgeBase
from app.schemas.document import (
    DocumentResponse,
    DocumentListResponse,
    DocumentUploadResponse,
    DocumentStats,
)
from app.utils.file_parser import read_file_content, get_file_info
from app.utils.helpers import format_file_size, ensure_dir

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/documents", tags=["文档管理"])


@router.get("", response_model=DocumentListResponse)
async def list_documents(
    kb_id: str = None,
    status: str = None,
    page: int = 1,
    page_size: int = 20,
    db: AsyncSession = Depends(get_db),
):
    """获取文档列表，支持按知识库和状态筛选"""
    query = select(Document)

    if kb_id:
        query = query.where(Document.kb_id == kb_id)
    if status:
        query = query.where(Document.status == status)

    # 总数
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    # 分页
    query = query.order_by(Document.created_at.desc())
    query = query.offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    docs = result.scalars().all()

    items = [DocumentResponse.model_validate(doc) for doc in docs]
    return DocumentListResponse(items=items, total=total)


@router.post("/upload", response_model=DocumentUploadResponse)
async def upload_document(
    file: UploadFile = File(...),
    kb_id: str = Form(...),
    db: AsyncSession = Depends(get_db),
):
    """
    上传文档并触发异步处理。
    返回 document_id 和 task_id，前端可轮询进度。
    """
    # 验证知识库存在
    kb_result = await db.execute(select(KnowledgeBase).where(KnowledgeBase.id == kb_id))
    if not kb_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="知识库不存在")

    # 保存文件
    ensure_dir(config.LOCAL_DATA_DIR)
    safe_filename = file.filename or "untitled"
    stored_path = os.path.join(config.LOCAL_DATA_DIR, safe_filename)

    # 避免文件名冲突
    base, ext = os.path.splitext(safe_filename)
    counter = 1
    while os.path.exists(stored_path):
        stored_path = os.path.join(config.LOCAL_DATA_DIR, f"{base}_{counter}{ext}")
        counter += 1

    content = await file.read()
    with open(stored_path, "wb") as f:
        f.write(content)

    # 获取文件信息
    file_info = get_file_info(stored_path)

    # 创建文档记录
    doc = Document(
        kb_id=kb_id,
        filename=safe_filename,
        file_path=stored_path,
        file_type=file_info["type"],
        file_size=file_info["size"],
        status=DocumentStatus.PENDING,
    )
    db.add(doc)
    await db.flush()
    await db.refresh(doc)

    # 生成任务 ID
    task_id = str(uuid.uuid4())

    # 触发异步处理（Phase 5 实现完整任务系统，这里先占位）
    # await start_document_processing(doc.id, task_id, stored_path)

    return DocumentUploadResponse(
        document_id=doc.id,
        task_id=task_id,
        filename=safe_filename,
        status="pending",
        message="文档已上传，等待处理",
    )


@router.get("/{doc_id}", response_model=DocumentResponse)
async def get_document(doc_id: str, db: AsyncSession = Depends(get_db)):
    """获取文档详情"""
    result = await db.execute(select(Document).where(Document.id == doc_id))
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=404, detail="文档不存在")
    return DocumentResponse.model_validate(doc)


@router.delete("/{doc_id}")
async def delete_document(doc_id: str, db: AsyncSession = Depends(get_db)):
    """删除文档及其文件"""
    result = await db.execute(select(Document).where(Document.id == doc_id))
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=404, detail="文档不存在")

    # 删除物理文件
    if os.path.exists(doc.file_path):
        try:
            os.remove(doc.file_path)
        except OSError as e:
            logger.warning(f"删除文件失败: {doc.file_path}, {e}")

    await db.delete(doc)
    await db.flush()
    return {"message": f"文档 '{doc.filename}' 已删除", "id": doc_id}


@router.get("/stats/overview", response_model=DocumentStats)
async def get_document_stats(db: AsyncSession = Depends(get_db)):
    """获取文档统计信息"""
    result = await db.execute(select(Document))
    docs = result.scalars().all()

    total_entities = sum(d.entity_count for d in docs)
    total_relations = sum(d.relationship_count for d in docs)
    total_size = sum(d.file_size for d in docs)

    return DocumentStats(
        documents=len(docs),
        entities=total_entities,
        relationships=total_relations,
        storage_used=format_file_size(total_size),
    )
