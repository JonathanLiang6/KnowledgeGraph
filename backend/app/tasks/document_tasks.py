"""
文档处理异步任务 - v2.1 流水线重构

P1 优化：
- Stage 解耦：每个阶段独立为一个 handler，支持单独测试
- 断点续传：状态持久化到 DB；v4.1 起各阶段中间产物（解析文本/NLP 图/
  LLM 精炼图/分块）落盘到 data/artifacts/{doc_id}/，服务重启后按阶段
  回载数据而非只恢复状态码，修复"恢复后文档 DONE 但图谱永久缺失"
- 并发控制：Semaphore 限制同时处理的文档数
- ThreadPool：CPU 密集型阶段（解析/NLP/分块）在线程池中执行，
  使 asyncio.wait_for 的阶段超时真实可取消（v4.1 修复假超时）
- 超时保护：每个阶段可独立超时
"""
import asyncio
import json
import logging
import os
import shutil
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


# ─── 阶段产物持久化 (v4.1: 断点续传不再丢失中间结果) ────────────────


def _artifacts_dir(doc_id: str) -> str:
    return os.path.join(config.DATA_DIR, "artifacts", doc_id)


def _save_artifact_text(doc_id: str, name: str, text: str) -> None:
    try:
        d = _artifacts_dir(doc_id)
        os.makedirs(d, exist_ok=True)
        with open(os.path.join(d, name), "w", encoding="utf-8") as f:
            f.write(text)
    except OSError as e:
        logger.warning(f"保存阶段产物失败 [{name}] doc={doc_id}: {e}")


def _load_artifact_text(doc_id: str, name: str) -> Optional[str]:
    path = os.path.join(_artifacts_dir(doc_id), name)
    if not os.path.exists(path):
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    except OSError:
        return None


def _save_artifact_json(doc_id: str, name: str, obj) -> None:
    try:
        d = _artifacts_dir(doc_id)
        os.makedirs(d, exist_ok=True)
        with open(os.path.join(d, name), "w", encoding="utf-8") as f:
            json.dump(obj, f, ensure_ascii=False)
    except (OSError, TypeError) as e:
        logger.warning(f"保存阶段产物失败 [{name}] doc={doc_id}: {e}")


def _load_artifact_json(doc_id: str, name: str):
    path = os.path.join(_artifacts_dir(doc_id), name)
    if not os.path.exists(path):
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        return None


def _has_artifact(doc_id: str, name: str) -> bool:
    return os.path.exists(os.path.join(_artifacts_dir(doc_id), name))


def cleanup_doc_artifacts(doc_id: str) -> None:
    """清理文档的阶段产物（文档完成/删除时调用）"""
    d = _artifacts_dir(doc_id)
    if os.path.isdir(d):
        shutil.rmtree(d, ignore_errors=True)


class _RestoredChunk:
    """从 chunks.json 恢复的轻量 chunk（具备 embedding/indexing 阶段所需接口）"""

    def __init__(self, d: dict):
        self._dict = d
        self.text = d.get("text", "")
        self.chunk_level = d.get("chunk_level", "child")
        self._embedding = None

    def to_dict(self) -> dict:
        return self._dict

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

            word_count = doc.word_count or 0
            token_count = doc.token_count or 0
            result_graph = None
            refined_graph = None
            chunks = []
            cached_content = None

            if start_from == -1:
                # 全新处理：清理上一轮残留的阶段产物
                cleanup_doc_artifacts(doc_id)
            else:
                # v4.1: 从磁盘产物恢复中间结果，而非只恢复状态码
                if start_from >= 4:
                    restored_chunks = _load_artifact_json(doc_id, "chunks.json")
                    if isinstance(restored_chunks, list) and restored_chunks:
                        chunks = [_RestoredChunk(c) for c in restored_chunks]
                    else:
                        logger.info("断点续传: chunks 产物缺失，回退到 chunking 阶段")
                        start_from = 3
                if start_from >= 2:
                    result_graph = _load_artifact_json(doc_id, "nlp_graph.json")
                if start_from >= 3:
                    refined_graph = _load_artifact_json(doc_id, "refined_graph.json")
                if start_from >= 1:
                    cached_content = _load_artifact_text(doc_id, "content.txt")
                    if cached_content is None:
                        logger.info("断点续传: 解析文本产物缺失，回退到 parsing 阶段")
                        start_from = 0

                # v4.1 保障：已跳过图构建阶段（nlp/llm）但图产物全部缺失时，
                # 必须回退重建，否则文档会以 DONE 结束但知识图谱永久缺失
                if start_from >= 2 and not (refined_graph or result_graph) and not doc.graph_data:
                    logger.warning("断点续传: 图谱中间产物丢失，回退到 NLP 提取阶段重建图谱")
                    start_from = 1
                    refined_graph = None
                    result_graph = None

                logger.info(f"断点续传: doc={doc_id} 从阶段 {start_from + 1} 继续")

            # 产物缺失时的兜底：跳过 parsing 但后续阶段需要内容时再读文件
            async def _ensure_content():
                nonlocal cached_content
                if cached_content is None:
                    cached_content = read_file_content(filepath)
                    if cached_content:
                        logger.debug(f"延迟读取文件内容: {len(cached_content)} 字符")

            # ─── 阶段执行 ───────────────────────────────────────

            for i, (stage_key, progress, status, label) in enumerate(PROCESSING_STAGES):
                if i < start_from:
                    # 跳过已完成的阶段
                    logger.debug(f"跳过已完成阶段: {stage_key}")
                    continue

                update_task(task_id, progress=progress, stage=label)
                await _update_doc_status(db, doc, status, progress)

                try:
                    # 每个阶段独立超时（默认 30 分钟总超时，每阶段 5 分钟）
                    stage_timeout = max(60, config.DOCUMENT_PROCESSING_TIMEOUT_MINUTES * 60 // len(PROCESSING_STAGES))
                    if stage_key == "parsing":
                        word_count, token_count, cached_content = await asyncio.wait_for(
                            _stage_parsing(db, doc, filepath, task_id), timeout=stage_timeout
                        )
                        _save_artifact_text(doc_id, "content.txt", cached_content or "")
                    elif stage_key == "nlp_extract":
                        await _ensure_content()
                        result_graph = await asyncio.wait_for(
                            _stage_nlp_extract(db, doc, cached_content, task_id), timeout=stage_timeout
                        )
                        _save_artifact_json(doc_id, "nlp_graph.json", result_graph)
                    elif stage_key == "llm_refine":
                        await _ensure_content()
                        refined_graph = await asyncio.wait_for(
                            _stage_llm_refine(db, doc, cached_content, result_graph, task_id), timeout=stage_timeout
                        )
                        # 显式落盘（含 None：表示该阶段已执行、LLM 失败降级）
                        _save_artifact_json(doc_id, "refined_graph.json", refined_graph)
                    elif stage_key == "chunking":
                        await _ensure_content()
                        chunks = await asyncio.wait_for(
                            _stage_chunking(db, doc, cached_content, refined_graph, task_id), timeout=stage_timeout
                        )
                        _save_artifact_json(doc_id, "chunks.json", [c.to_dict() for c in chunks])
                    elif stage_key == "embedding":
                        await asyncio.wait_for(
                            _stage_embedding(db, doc, chunks, task_id), timeout=stage_timeout
                        )
                    elif stage_key == "indexing":
                        await asyncio.wait_for(
                            _stage_indexing(db, doc, chunks, task_id), timeout=stage_timeout
                        )

                    # 每个阶段完成后立即提交，持久化进度
                    await db.commit()

                except asyncio.TimeoutError:
                    logger.error(f"阶段 [{stage_key}] 超时 ({stage_timeout}s)")
                    update_task(task_id, status="failed", error=f"阶段 [{stage_key}] 超时", stage=label)
                    raise
                except Exception as stage_error:
                    logger.error(f"阶段 [{stage_key}] 失败: {stage_error}")
                    await db.commit()
                    raise

            # ─── 完成 ───────────────────────────────────────────

            final_graph = refined_graph if refined_graph else result_graph
            if final_graph:
                doc.graph_data = final_graph  # v2.4: JSON 列自动序列化（向后兼容）
                # Phase 1: 持久化到独立图存储 (GraphEntity + GraphRelation)
                try:
                    from app.services.graph_service import GraphService
                    await GraphService.build_graph(
                        db=db,
                        kb_id=doc.kb_id,
                        nodes=final_graph.get("nodes", []),
                        links=final_graph.get("links", []),
                        doc_id=doc.id,
                    )
                except Exception as e:
                    logger.warning(f"图谱持久化失败（不影响文档处理）: {e}")
            doc.status = DocumentStatus.DONE
            doc.progress = 100.0
            doc.processed_at = datetime.now()
            await db.commit()  # 最终持久化
            cleanup_doc_artifacts(doc_id)  # v4.1: 完成后清理阶段产物

            # v4.0: 通知缓存系统知识库内容已变更
            try:
                from app.services.rag_service import invalidate_kb_cache
                invalidate_kb_cache(doc.kb_id)
            except Exception:
                pass

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
                    # v4.0: 错误信息脱敏，移除路径和堆栈信息
                    err_msg = str(e).split("Traceback")[0].strip()
                    # 移除可能的服务器绝对路径
                    import re as _re
                    err_msg = _re.sub(r'[A-Za-z]:\\[^\s,;]+', '[path]', err_msg)
                    err_msg = _re.sub(r'/[^\s,;]+\.py', '[path]', err_msg)
                    doc.error_message = err_msg[:1000]
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
    返回 (word_count, token_count, content) 供后续阶段复用。
    """
    update_task(task_id, progress=5, stage="解析文档内容")

    # v4.1: 同步文件解析移入线程池，使 wait_for 超时真实可取消
    loop = asyncio.get_running_loop()
    content = await loop.run_in_executor(None, read_file_content, filepath)
    if not content:
        raise ValueError("文档内容解析失败或为空")

    word_count = len(content)
    token_count = count_tokens_approximate(content)
    doc.word_count = word_count
    doc.token_count = token_count
    await db.flush()

    logger.info(f"Stage 1 [parsing]: {word_count} 字, {token_count} tokens")
    return word_count, token_count, content


async def _stage_nlp_extract(
    db: AsyncSession, doc: Document, content: str, task_id: str
) -> dict:
    """
    Stage 2: NLP 粗筛实体提取 (v2.5: 复用 parsing 阶段读取的内容)。
    """
    update_task(task_id, progress=15, stage="NLP 实体粗筛")

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
    db: AsyncSession, doc: Document, content: str,
    nlp_graph: dict, task_id: str
) -> Optional[dict]:
    """
    Stage 3: LLM 精炼实体 (v2.5: 复用 parsing 阶段读取的内容)。

    使用 DeepSeek V4 校正实体与关系。
    失败时返回 None（不阻塞流程）。
    """
    update_task(task_id, progress=35, stage="LLM 实体精炼")

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
    db: AsyncSession, doc: Document, content: str,
    refined_graph: Optional[dict], task_id: str
) -> list:
    """
    Stage 4: 语义分块 (v2.5: 复用 parsing 阶段读取的内容)。
    使用父子块架构进行文档分块。
    """
    update_task(task_id, progress=55, stage="语义分块")

    if not content:
        raise ValueError("无法读取文件内容进行分块")

    from app.services.chunking_service import SemanticChunker
    chunker = SemanticChunker(
        parent_chunk_size=config.PARENT_CHUNK_SIZE,
        child_chunk_size=config.CHILD_CHUNK_SIZE,
        chunk_overlap=config.CHUNK_OVERLAP,
        strategy="parent_child",
    )
    # v4.1: 同步分块（CPU 密集）移入线程池，使 wait_for 超时真实可取消
    loop = asyncio.get_running_loop()
    chunks = await loop.run_in_executor(None, lambda: chunker.chunk(content, doc.id))
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

    # 写入混合检索引擎 (v2.5: 使用模块级单例，确保索引与搜索共享同一实例)
    from app.services.hybrid_search import hybrid_search_service
    # 清理旧索引条目，防止 reprocess 产生重复
    hybrid_search_service.remove_document(doc.id)
    chunk_dicts = [c.to_dict() for c in child_chunks]
    hybrid_search_service.index_document(chunk_dicts, embeddings)

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
