"""
文档管理 API - v2.1 优化版
P0: 文件大小限制、MIME 白名单、流式写入、去重
P2: 批量上传、重新处理、去重检测
"""
import os
import uuid
import logging
from typing import List
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Query
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
    BatchUploadResponse,
    BatchUploadItem,
    ReprocessRequest,
    ReprocessResponse,
    DedupCheckResponse,
)
from app.utils.file_parser import get_file_info
from app.utils.helpers import (
    format_file_size, ensure_dir, sanitize_filename,
    detect_mime_type, validate_file_allowed,
    stream_save_upload, compute_file_hash,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/documents", tags=["文档管理"])

# ─── 文件上传安全检查 ─────────────────────────────────────────────


async def _validate_upload(file: UploadFile) -> None:
    """
    P0 安全校验：
    1. 文件大小检查
    2. 扩展名白名单检查
    3. 空文件检查
    """
    # 检查文件名
    if not file.filename or file.filename.strip() == "":
        raise HTTPException(status_code=400, detail="文件名为空")

    # 检查扩展名
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in config.ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"不支持的文件类型: {ext}。支持的类型: {', '.join(sorted(config.ALLOWED_EXTENSIONS))}"
        )

    # 读取文件内容进行大小检查（流式）
    max_size = config.MAX_FILE_SIZE_BYTES
    total_size = 0
    chunk_size = 64 * 1024  # 64KB per chunk

    while True:
        chunk = await file.read(chunk_size)
        if not chunk:
            break
        total_size += len(chunk)
        if total_size > max_size:
            raise HTTPException(
                status_code=413,
                detail=f"文件大小 ({format_file_size(total_size)}) 超过限制 ({config.MAX_FILE_SIZE_MB}MB)"
            )

    # 空文件检查
    if total_size == 0:
        raise HTTPException(status_code=400, detail="文件为空")

    # 重置文件指针供后续读取
    await file.seek(0)


def _validate_saved_file(filepath: str, original_filename: str) -> None:
    """
    P0 保存后校验：MIME 内容检测。
    在文件保存到磁盘后调用。
    """
    detected_mime = detect_mime_type(filepath)
    is_allowed, reason = validate_file_allowed(filepath, original_filename, detected_mime)
    if not is_allowed:
        # 删除不安全文件
        try:
            os.remove(filepath)
        except OSError:
            pass
        raise HTTPException(
            status_code=400,
            detail=f"文件安全校验失败: {reason}"
        )


# ─── API 端点 ─────────────────────────────────────────────────────


@router.get("", response_model=DocumentListResponse)
async def list_documents(
    kb_id: str = Query(default=None, description="知识库 ID"),
    status: str = Query(default=None, description="状态筛选"),
    page: int = Query(default=1, ge=1, description="页码"),
    page_size: int = Query(default=20, ge=1, le=100, description="每页数量"),
    db: AsyncSession = Depends(get_db),
):
    """获取文档列表，支持按知识库和状态筛选"""
    # 构建查询
    conditions = []
    if kb_id:
        conditions.append(Document.kb_id == kb_id)
    if status:
        conditions.append(Document.status == status)

    # 总数（修复：使用正确的 count 查询方式）
    count_query = select(func.count(Document.id))
    if conditions:
        count_query = count_query.where(*conditions)
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    # 分页查询
    query = select(Document)
    if conditions:
        query = query.where(*conditions)
    query = query.order_by(Document.created_at.desc())
    query = query.offset((page - 1) * page_size).limit(page_size)

    result = await db.execute(query)
    docs = result.scalars().all()

    items = [DocumentResponse.model_validate(doc) for doc in docs]
    return DocumentListResponse(items=items, total=total, page=page, page_size=page_size)


@router.post("/upload", response_model=DocumentUploadResponse)
async def upload_document(
    file: UploadFile = File(...),
    kb_id: str = Form(...),
    db: AsyncSession = Depends(get_db),
):
    """
    上传文档并触发异步处理（P0 加固版）。

    安全检查：
    - 文件大小限制（MAX_FILE_SIZE_MB）
    - 扩展名白名单（ALLOWED_EXTENSIONS）
    - MIME 内容检测
    - 文件去重（SHA256）
    """
    raw_filename = file.filename or "untitled"

    # P0: 文件上传安全检查
    await _validate_upload(file)

    # 验证知识库存在
    kb = (await db.execute(select(KnowledgeBase).where(KnowledgeBase.id == kb_id))).scalar_one_or_none()
    if not kb:
        raise HTTPException(status_code=404, detail="知识库不存在")

    # v3.2: 按知识库名称分文件夹存储，方便管理
    kb_folder = sanitize_filename(kb.name)
    upload_dir = os.path.join(config.LOCAL_DATA_DIR, kb_folder)
    ensure_dir(upload_dir)
    safe_filename = sanitize_filename(raw_filename)
    stored_path = os.path.join(upload_dir, safe_filename)

    total_written = stream_save_upload(file.file, stored_path)
    await file.close()

    # P0: 保存后 MIME 校验
    _validate_saved_file(stored_path, raw_filename)

    # P0: 文件去重检查 (v2.3: DB查询替代磁盘扫描)
    duplicate_of = None
    if config.ENABLE_FILE_DEDUP:
        file_hash_val = compute_file_hash(stored_path)
        dup_doc_result = await db.execute(
            select(Document).where(
                Document.file_hash == file_hash_val,
                Document.kb_id == kb_id,
            )
        )
        dup_doc = dup_doc_result.scalar_one_or_none()

        if dup_doc:
            # 真正重复 → 删除新保存的文件
            try:
                os.remove(stored_path)
            except OSError:
                pass
            logger.info(f"检测到重复文件: {raw_filename}, 已存在: doc={dup_doc.id}")
            return DocumentUploadResponse(
                document_id="",
                task_id="",
                filename=raw_filename,
                status="duplicate",
                message=f"文件已存在（文档: {dup_doc.filename}）",
                duplicate=True,
                duplicate_of=dup_doc.id,
            )
        else:
            # 设置 file_hash 用于后续写入
            pass  # file_hash_val will be set below

    # 获取文件信息 (v2.5: 复用已计算的 hash)
    file_info = get_file_info(stored_path, file_hash=file_hash_val if config.ENABLE_FILE_DEDUP else None)

    # 创建文档记录 (v2.3: 存储 file_hash 用于 DB 去重)
    doc = Document(
        kb_id=kb_id,
        filename=raw_filename,
        file_path=stored_path,
        file_type=file_info["type"],
        file_size=file_info["size"],
        file_hash=file_hash_val if config.ENABLE_FILE_DEDUP else None,
        status=DocumentStatus.PENDING,
    )
    db.add(doc)
    await db.flush()
    await db.refresh(doc)

    # 触发异步处理
    from app.tasks.document_tasks import start_document_processing
    task_id = await start_document_processing(doc.id, stored_path)

    # v2.5: 检查 upload 返回值是否有效
    if total_written == 0:
        raise HTTPException(status_code=400, detail="文件保存失败（写入 0 字节）")

    return DocumentUploadResponse(
        document_id=doc.id,
        task_id=task_id,
        filename=raw_filename,
        status="processing",
        message="文档已上传，正在处理",
        duplicate=False,
    )


@router.post("/upload/batch", response_model=BatchUploadResponse)
async def batch_upload_documents(
    files: List[UploadFile] = File(...),
    kb_id: str = Form(...),
    db: AsyncSession = Depends(get_db),
):
    """
    P2: 批量上传文档（最多 20 个文件）。
    每个文件独立校验，互不影响。
    """
    if len(files) > 20:
        raise HTTPException(status_code=400, detail="单次批量上传不超过 20 个文件")

    # 验证知识库存在
    kb = (await db.execute(select(KnowledgeBase).where(KnowledgeBase.id == kb_id))).scalar_one_or_none()
    if not kb:
        raise HTTPException(status_code=404, detail="知识库不存在")

    kb_folder = sanitize_filename(kb.name)
    upload_dir = os.path.join(config.LOCAL_DATA_DIR, kb_folder)
    ensure_dir(upload_dir)

    items = []
    succeeded = 0
    failed = 0
    duplicates = 0

    for file in files:
        try:
            raw_filename = file.filename or "untitled"

            # 安全检查
            await _validate_upload(file)

            # 保存文件
            safe_filename = sanitize_filename(raw_filename)
            stored_path = os.path.join(upload_dir, safe_filename)

            total_written = stream_save_upload(file.file, stored_path)
            await file.close()

            # MIME 校验
            _validate_saved_file(stored_path, raw_filename)

            # 去重 (v2.3: DB查询替代磁盘扫描)
            if config.ENABLE_FILE_DEDUP:
                file_hash_val = compute_file_hash(stored_path)
                dup_doc_result = await db.execute(
                    select(Document).where(
                        Document.file_hash == file_hash_val,
                        Document.kb_id == kb_id,
                    )
                )
                dup_doc = dup_doc_result.scalar_one_or_none()

                if dup_doc:
                    # 真正重复
                    try:
                        os.remove(stored_path)
                    except OSError:
                        pass
                    items.append(BatchUploadItem(
                        filename=raw_filename,
                        success=True,
                        document_id=dup_doc.id,
                        message=f"文件已存在（文档: {dup_doc.filename}）",
                        duplicate=True,
                    ))
                    duplicates += 1
                    continue

            # 创建记录
            file_info = get_file_info(stored_path)
            doc = Document(
                kb_id=kb_id,
                filename=raw_filename,
                file_path=stored_path,
                file_type=file_info["type"],
                file_size=file_info["size"],
                file_hash=file_hash_val if config.ENABLE_FILE_DEDUP else None,
                status=DocumentStatus.PENDING,
            )
            db.add(doc)
            await db.flush()
            await db.refresh(doc)

            # 触发处理
            from app.tasks.document_tasks import start_document_processing
            task_id = await start_document_processing(doc.id, stored_path)

            items.append(BatchUploadItem(
                filename=raw_filename,
                success=True,
                document_id=doc.id,
                task_id=task_id,
                message="上传成功",
            ))
            succeeded += 1

        except HTTPException:
            raise  # FastAPI 异常直接传播
        except Exception as e:
            logger.error(f"批量上传失败 [{file.filename}]: {e}")
            items.append(BatchUploadItem(
                filename=file.filename or "unknown",
                success=False,
                message=str(e),
            ))
            failed += 1

    return BatchUploadResponse(
        total=len(files),
        succeeded=succeeded,
        failed=failed,
        duplicates=duplicates,
        items=items,
    )


@router.post("/{doc_id}/reprocess", response_model=ReprocessResponse)
async def reprocess_document(
    doc_id: str,
    req: ReprocessRequest = ReprocessRequest(),
    db: AsyncSession = Depends(get_db),
):
    """
    P2: 重新处理文档。
    从已保存的文件重新执行完整处理流水线。
    """
    result = await db.execute(select(Document).where(Document.id == doc_id))
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=404, detail="文档不存在")

    if not os.path.exists(doc.file_path):
        raise HTTPException(status_code=400, detail="原始文件不存在，无法重新处理")

    previous_status = doc.status.value if isinstance(doc.status, DocumentStatus) else str(doc.status)

    # 重置状态
    doc.status = DocumentStatus.PENDING
    doc.progress = 0.0
    doc.error_message = ""
    if req.force:
        doc.graph_data = None
        doc.entity_count = 0
        doc.relationship_count = 0
        doc.chunk_count = 0
    await db.flush()

    # 触发处理
    from app.tasks.document_tasks import start_document_processing
    task_id = await start_document_processing(doc.id, doc.file_path)

    return ReprocessResponse(
        document_id=doc.id,
        task_id=task_id,
        previous_status=previous_status,
        message="重新处理已启动",
    )


@router.get("/check-duplicate", response_model=DedupCheckResponse)
async def check_duplicate(
    file_hash: str = Query(..., description="文件 SHA256 哈希"),
    kb_id: str = Query(default=None, description="限定知识库范围"),
    db: AsyncSession = Depends(get_db),
):
    """
    P2: 根据文件哈希检测是否已存在 (v2.3: DB查询替代磁盘扫描)。

    前端上传前可先调用此接口做客户端去重。
    """
    query = select(Document).where(Document.file_hash == file_hash)
    if kb_id:
        query = query.where(Document.kb_id == kb_id)
    result = await db.execute(query)
    doc = result.scalar_one_or_none()

    if doc:
        return DedupCheckResponse(
            has_duplicate=True,
            duplicate_doc_id=doc.id,
            duplicate_filename=doc.filename,
            file_hash=file_hash,
        )

    return DedupCheckResponse(has_duplicate=False, file_hash=file_hash)


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
    """
    删除文档及其文件和索引。

    P2: 同时清理混合检索引擎中的索引数据。
    """
    result = await db.execute(select(Document).where(Document.id == doc_id))
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=404, detail="文档不存在")

    # 删除物理文件
    if os.path.exists(doc.file_path):
        try:
            os.remove(doc.file_path)
            logger.info(f"已删除文件: {doc.file_path}")
        except OSError as e:
            logger.warning(f"删除文件失败: {doc.file_path}, {e}")

    # P2: 清理检索引擎中的索引 (v2.5: 使用模块级单例)
    try:
        from app.services.hybrid_search import hybrid_search_service
        hybrid_search_service.remove_document(doc.id)
        logger.info(f"已清理检索索引: {doc.id}")
    except Exception as e:
        logger.warning(f"清理检索索引失败（非致命）: {e}")

    await db.delete(doc)
    await db.flush()
    return {"message": f"文档 '{doc.filename}' 已删除", "id": doc_id}


@router.get("/stats/overview", response_model=DocumentStats)
async def get_document_stats(db: AsyncSession = Depends(get_db)):
    """
    获取文档统计信息 (v2.5: SQL 聚合，避免全量加载到 Python)。
    """
    # v2.5: 使用数据库聚合计算，O(1) 网络传输
    from sqlalchemy import case, and_

    # 处理中状态: 排除 done/failed/pending
    processing_statuses = ["parsing", "nlp_extracting", "llm_refining",
                           "chunking", "embedding", "indexing"]

    stats_query = select(
        func.count(Document.id).label("total"),
        func.coalesce(func.sum(Document.entity_count), 0).label("total_entities"),
        func.coalesce(func.sum(Document.relationship_count), 0).label("total_relations"),
        func.coalesce(func.sum(Document.file_size), 0).label("total_size"),
        func.count().filter(Document.status == "done").label("done_count"),
        func.count().filter(Document.status == "failed").label("failed_count"),
        func.count().filter(Document.status.in_(processing_statuses)).label("processing_count"),
        func.count().filter(Document.status == "pending").label("pending_count"),
    )
    result = await db.execute(stats_query)
    row = result.one()

    return DocumentStats(
        documents=row.total,
        entities=row.total_entities,
        relationships=row.total_relations,
        storage_used=format_file_size(row.total_size),
        pending=row.pending_count,
        processing=row.processing_count,
        done=row.done_count,
        failed=row.failed_count,
    )
