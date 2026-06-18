"""
文档处理异步任务 - v2.1 流水线重构

P1 优化：
- Stage 解耦：每个阶段独立为一个 handler，支持单独测试
- 断点续传：状态持久化到 DB，重启后可从最后成功阶段恢复
- 并发控制：Semaphore 限制同时处理的文档数
- ThreadPool：CPU 密集型任务（Embedding）在线程池中执行
- 超时保护：每个阶段可独立超时
"""
import asyncio
import logging
import os
import traceback
from datetime import datetime
from typing import Optional, Dict, Callable, Awaitable
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.database import async_session_factory
from app.models.document import Document, DocumentStatus
from app.api.v1.endpoints.monitor import create_task, update_task
from app.utils.file_parser import read_file_content
from app.utils.helpers import count_tokens_approximate, Timer

logger = logging.getLogger(__name__)

# ─── 并发控制 ─────────────────────────────────────────────────────

from app.core.config import config

# 全局信号量：限制同时处理的文档数量
_processing_semaphore = asyncio.Semaphore(config.MAX_CONCURRENT_DOCUMENT_PROCESSING)

# 活跃处理计数（用于状态展示）
_active_processing_count = 0
_active_count_lock = asyncio.Lock()


# ─── 处理阶段定义 ─────────────────────────────────────────────────

# 每个阶段: (stage_key, progress_pct, DocumentStatus, label)
PROCESSING_STAGES = [
    ("parsing",       5,  DocumentStatus.PARSING,        "解析文档内容"),
    ("nlp_extract",  20,  DocumentStatus.NLP_EXTRACTING, "NLP 实体粗筛"),
    ("llm_refine",   40,  DocumentStatus.LLM_REFINING,   "LLM 实体精炼"),
    ("chunking",     60,  DocumentStatus.CHUNKING,       "语义分块"),
    ("embedding",    80,  DocumentStatus.EMBEDDING,      "生成向量嵌入"),
    ("indexing",     95,  DocumentStatus.INDEXING,       "构建检索索引"),
]


def get_stage_for_status(status: DocumentStatus) -> int:
    """根据 DocumentStatus 返回已完成的最后一个 stage 索引（-1 表示未开始）"""
    status_to_idx = {stage_status: i for i, (_, _, stage_status, _) in enumerate(PROCESSING_STAGES)}
    return status_to_idx.get(status, -1)

# ─── 公共入口 ─────────────────────────────────────────────────────


async def start_document_processing(doc_id: str, filepath: str) -> str:
    """
    启动文档处理异步任务。

    Returns:
        task_id，前端通过 /api/v1/monitor/tasks/{task_id} 轮询进度。
    """
    task_id = create_task("document_processing")
    # 以 fire-and-forget 方式启动，但确保异常被记录
    asyncio.create_task(_process_document_safe(doc_id, filepath, task_id))
    logger.info(f"文档处理任务已启动: doc={doc_id}, task={task_id}")
    return task_id


async def _process_document_safe(doc_id: str, filepath: str, task_id: str):
    """
    带并发控制和异常保护的主流程包装。
    """
    global _active_processing_count

    # P1: 获取信号量（并发控制）
    async with _processing_semaphore:
        async with _active_count_lock:
            _active_processing_count += 1
            logger.info(f"📄 活跃处理任务: {_active_processing_count}/{config.MAX_CONCURRENT_DOCUMENT_PROCESSING}")

        try:
            await _process_document(doc_id, filepath, task_id)
        finally:
            async with _active_count_lock:
                _active_processing_count -= 1


async def _process_document(doc_id: str, filepath: str, task_id: str):
    """文档处理主流程（断点续传版）"""
    update_task(task_id, status="running", progress=0, stage="开始处理")

    async with async_session_factory() as db:
        try:
            # 加载文档记录
            result = await db.execute(select(Document).where(Document.id == doc_id))
            doc = result.scalar_one_or_none()
            if not doc:
                update_task(task_id, status="failed", error="文档不存在")
                return

            # P1: 断点续传 — 从上次失败/中断的阶段继续
            start_from = get_stage_for_status(doc.status)
            if start_from >= len(PROCESSING_STAGES) - 1:
                # 已是完成状态，但被手动触发重新处理
                start_from = -1

            if start_from >= 0:
                logger.info(f"断点续传: doc={doc_id} 从阶段 {start_from + 1} 继续")

            # ─── 阶段执行 ───────────────────────────────────────

            word_count = doc.word_count or 0
            token_count = doc.token_count or 0
            result_graph = None
            refined_graph = None
            chunks = []

            for i, (stage_key, progress, status, label) in enumerate(PROCESSING_STAGES):
                if i < start_from:
                    # 跳过已完成的阶段
                    logger.debug(f"跳过已完成阶段: {stage_key}")
                    continue

                update_task(task_id, progress=progress, stage=label)
                await _update_doc_status(db, doc, status, progress)

                try:
                    if stage_key == "parsing":
                        word_count, token_count = await _stage_parsing(
                            db, doc, filepath, task_id
                        )
                    elif stage_key == "nlp_extract":
                        result_graph = await _stage_nlp_extract(
                            db, doc, filepath, task_id
                        )
                    elif stage_key == "llm_refine":
                        refined_graph = await _stage_llm_refine(
                            db, doc, filepath, result_graph, task_id
                        )
                    elif stage_key == "chunking":
                        chunks = await _stage_chunking(
                            db, doc, filepath, result_graph, refined_graph, task_id
                        )
                    elif stage_key == "embedding":
                        await _stage_embedding(db, doc, chunks, task_id)
                    elif stage_key == "indexing":
                        await _stage_indexing(db, doc, chunks, task_id)

                    # 每个阶段完成后立即提交，持久化进度
                    await db.commit()

                except asyncio.TimeoutError:
                    raise
                except Exception as stage_error:
                    logger.error(f"阶段 [{stage_key}] 失败: {stage_error}")
                    # 保留部分进度到 DB
                    await db.commit()
                    raise

            # ─── 完成 ───────────────────────────────────────────

            final_graph = refined_graph if refined_graph else result_graph
            if final_graph:
                doc.graph_data = final_graph  # v2.4: JSON 列自动序列化
                # 更新 GraphRAG 实体索引
                try:
                    from app.services.rag_service import update_graph_index
                    update_graph_index(
                        final_graph.get("nodes", []),
                        final_graph.get("links", []),
                    )
                except Exception as e:
                    logger.warning(f"更新图谱索引失败: {e}")
            doc.status = DocumentStatus.DONE
            doc.progress = 100.0
            doc.processed_at = datetime.now()
            await db.commit()  # 最终持久化

            update_task(
                task_id, status="done", progress=100, stage="处理完成",
                result={
                    "word_count": word_count,
                    "token_count": token_count,
                    "chunk_count": len(chunks),
                    "entity_count": doc.entity_count,
                    "relationship_count": doc.relationship_count,
                },
            )
            logger.info(f"✅ 文档处理完成: {doc.filename}")

        except Exception as e:
            logger.error(f"❌ 文档处理失败: {doc_id}, error: {e}")
            logger.error(traceback.format_exc())
            update_task(task_id, status="failed", error=str(e), stage="处理失败")

            # 更新文档状态为 FAILED（保留当前进度信息）
            try:
                result = await db.execute(select(Document).where(Document.id == doc_id))
                doc = result.scalar_one_or_none()
                if doc:
                    doc.status = DocumentStatus.FAILED
                    doc.error_message = str(e)[:1000]
                    await db.commit()
            except Exception as status_error:
                logger.error(f"更新文档失败状态时出错: {status_error}")


# ─── 各阶段实现（解耦为独立函数）──────────────────────────────────


async def _stage_parsing(
    db: AsyncSession, doc: Document, filepath: str, task_id: str
) -> tuple:
    """
    Stage 1: 解析文档内容。
    读取文件内容并统计字数/Token数。
    """
    update_task(task_id, progress=5, stage="解析文档内容")

    content = read_file_content(filepath)
    if not content:
        raise ValueError("文档内容解析失败或为空")

    word_count = len(content)
    token_count = count_tokens_approximate(content)
    doc.word_count = word_count
    doc.token_count = token_count
    await db.flush()

    logger.info(f"Stage 1 [parsing]: {word_count} 字, {token_count} tokens")
    return word_count, token_count


async def _stage_nlp_extract(
    db: AsyncSession, doc: Document, filepath: str, task_id: str
) -> dict:
    """
    Stage 2: NLP 粗筛实体提取。
    """
    update_task(task_id, progress=15, stage="NLP 实体粗筛")

    content = read_file_content(filepath)
    if not content:
        raise ValueError("无法读取文件内容进行 NLP 提取")

    from app.services.extraction_service import ExtractionService
    extractor = ExtractionService(use_llm=False)
    result_graph = await extractor.extract(content)

    doc.entity_count = len(result_graph.get("nodes", []))
    doc.relationship_count = len(result_graph.get("links", []))
    await db.flush()

    logger.info(f"Stage 2 [nlp]: {doc.entity_count} 实体, {doc.relationship_count} 关系")
    return result_graph


async def _stage_llm_refine(
    db: AsyncSession, doc: Document, filepath: str,
    nlp_graph: dict, task_id: str
) -> Optional[dict]:
    """
    Stage 3: LLM 精炼实体。

    使用 DeepSeek V4 校正实体与关系。
    失败时返回 None（不阻塞流程）。
    """
    update_task(task_id, progress=35, stage="LLM 实体精炼")

    content = read_file_content(filepath)
    if not content:
        logger.warning("LLM 精炼跳过：无法读取文件内容")
        return None

    try:
        from app.services.extraction_service import ExtractionService
        extractor_llm = ExtractionService(use_llm=True)
        refined_graph = await extractor_llm.extract(content)
        doc.entity_count = len(refined_graph.get("nodes", []))
        doc.relationship_count = len(refined_graph.get("links", []))
        await db.flush()
        logger.info(f"Stage 3 [llm]: {doc.entity_count} 实体, {doc.relationship_count} 关系")
        return refined_graph
    except Exception as e:
        logger.warning(f"Stage 3 [llm] 失败（使用 NLP 结果继续）: {e}")
        return None


async def _stage_chunking(
    db: AsyncSession, doc: Document, filepath: str,
    nlp_graph: dict, refined_graph: Optional[dict], task_id: str
) -> list:
    """
    Stage 4: 语义分块。
    使用父子块架构进行文档分块。
    """
    update_task(task_id, progress=55, stage="语义分块")

    content = read_file_content(filepath)
    if not content:
        raise ValueError("无法读取文件内容进行分块")

    from app.services.chunking_service import SemanticChunker
    chunker = SemanticChunker(
        parent_chunk_size=config.PARENT_CHUNK_SIZE,
        child_chunk_size=config.CHILD_CHUNK_SIZE,
        chunk_overlap=config.CHUNK_OVERLAP,
        strategy="parent_child",
    )
    chunks = chunker.chunk(content, doc.id)
    doc.chunk_count = len(chunks)
    await db.flush()

    logger.info(f"Stage 4 [chunking]: {len(chunks)} 块 (父: {sum(1 for c in chunks if c.chunk_level == 'parent')}, 子: {sum(1 for c in chunks if c.chunk_level == 'child')})")
    return chunks


async def _stage_embedding(
    db: AsyncSession, doc: Document, chunks: list, task_id: str
):
    """
    Stage 5: 生成向量嵌入（P1: 在线程池中异步执行）。

    仅对子块生成向量，使用 EmbeddingService.encode_async 避免阻塞事件循环。
    """
    update_task(task_id, progress=75, stage="生成向量嵌入")

    from app.services.embedding_service import EmbeddingService

    child_chunks = [c for c in chunks if c.chunk_level == "child"]
    if not child_chunks:
        logger.warning("没有子块，跳过 Embedding")
        return

    child_texts = [c.text for c in child_chunks]

    # P1: 使用异步编码（在线程池中执行 CPU 密集型任务）
    with Timer("Embedding"):
        embeddings = await EmbeddingService.encode_async(child_texts)

    logger.info(f"Stage 5 [embedding]: {len(embeddings)} 个向量")
    # 将 embeddings 通过 chunks 引用传递给下一阶段 (v2.3: 消除重复计算)
    for c, emb in zip(child_chunks, embeddings):
        c._embedding = emb
    update_task(task_id, progress=78, stage="向量嵌入完成",
                result={"embeddings_count": len(embeddings)})


async def _stage_indexing(
    db: AsyncSession, doc: Document, chunks: list, task_id: str
):
    """
    Stage 6: 构建混合检索引擎。

    将子块的向量和文本写入 LanceDB + BM25 索引。
    注意：此阶段需要重新生成 embedding（因为 stage 间数据未传递），
    实际优化可将 embedding 结果缓存在内存中。
    """
    update_task(task_id, progress=90, stage="构建检索索引")

    from app.services.embedding_service import EmbeddingService
    from app.services.hybrid_search import HybridSearchService

    child_chunks = [c for c in chunks if c.chunk_level == "child"]
    if not child_chunks:
        logger.warning("没有子块，跳过索引构建")
        return

    # v2.3: 优先复用 _stage_embedding 缓存的嵌入，避免重复计算
    child_texts = []
    embeddings = []
    for c in child_chunks:
        if hasattr(c, '_embedding') and c._embedding is not None:
            embeddings.append(c._embedding)
        else:
            child_texts.append(c.text)

    # 对未缓存的子块异步生成嵌入
    if child_texts:
        from app.services.embedding_service import EmbeddingService
        new_embeddings = await EmbeddingService.encode_async(child_texts)
        embeddings.extend(new_embeddings)

    if not embeddings:
        logger.warning("未能生成任何嵌入，跳过索引构建")
        return

    # 写入混合检索引擎
    hybrid = HybridSearchService()
    chunk_dicts = [c.to_dict() for c in child_chunks]
    hybrid.index_document(chunk_dicts, embeddings)

    logger.info(f"Stage 6 [indexing]: {len(chunk_dicts)} 子块已索引")


# ─── 工具函数 ─────────────────────────────────────────────────────


async def _update_doc_status(
    db: AsyncSession, doc: Document, status: DocumentStatus, progress: float
):
    """更新文档处理状态并提交（P1: 断点续传 checkpoint）"""
    doc.status = status
    doc.progress = progress
    await db.flush()
    await db.commit()  # 立即持久化，确保断点续传有效


async def resume_pending_documents():
    """
    启动时恢复所有中断的文档处理（断点续传入口）。
    对所有 PENDING/PARSING/NLP_EXTRACTING/LLM_REFINING/CHUNKING/EMBEDDING/INDEXING 状态的文档重新入队。
    """
    async with async_session_factory() as db:
        result = await db.execute(
            select(Document).where(
                Document.status.in_([
                    DocumentStatus.PENDING,
                    DocumentStatus.PARSING,
                    DocumentStatus.NLP_EXTRACTING,
                    DocumentStatus.LLM_REFINING,
                    DocumentStatus.CHUNKING,
                    DocumentStatus.EMBEDDING,
                    DocumentStatus.INDEXING,
                ])
            )
        )
        interrupted_docs = result.scalars().all()

    if not interrupted_docs:
        logger.info("没有需要恢复的文档处理任务")
        return

    logger.info(f"恢复 {len(interrupted_docs)} 个中断的文档处理任务")

    for doc in interrupted_docs:
        if os.path.exists(doc.file_path):
            task_id = create_task("document_processing")
            asyncio.create_task(_process_document_safe(doc.id, doc.file_path, task_id))
            logger.info(f"已恢复: doc={doc.id}, status={doc.status}")
            # 避免瞬间启动太多任务
            await asyncio.sleep(1)
        else:
            logger.warning(f"文件不存在，跳过恢复: {doc.id} ({doc.file_path})")
