"""
文档处理异步任务 - 编排完整的文档处理流水线
进度: parsing → nlp_extracting → llm_refining → chunking → embedding → indexing → done/failed
"""
import asyncio
import logging
import traceback
from datetime import datetime
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.database import async_session_factory
from app.models.document import Document, DocumentStatus
from app.api.v1.endpoints.monitor import create_task, update_task
from app.utils.file_parser import read_file_content
from app.utils.helpers import count_tokens_approximate

logger = logging.getLogger(__name__)


# 处理阶段定义 (阶段名, 进度百分比, DocumentStatus)
PROCESSING_STAGES = [
    ("parsing", 5, DocumentStatus.PARSING),
    ("nlp_extracting", 15, DocumentStatus.NLP_EXTRACTING),
    ("llm_refining", 35, DocumentStatus.LLM_REFINING),
    ("chunking", 55, DocumentStatus.CHUNKING),
    ("embedding", 75, DocumentStatus.EMBEDDING),
    ("indexing", 90, DocumentStatus.INDEXING),
    ("done", 100, DocumentStatus.DONE),
]


async def start_document_processing(doc_id: str, filepath: str) -> str:
    """
    启动文档处理异步任务。
    返回 task_id，前端通过 /api/v1/monitor/tasks/{task_id} 轮询进度。
    """
    task_id = create_task("document_processing")
    asyncio.create_task(_process_document(doc_id, filepath, task_id))
    logger.info(f"文档处理任务已启动: doc={doc_id}, task={task_id}")
    return task_id


async def _process_document(doc_id: str, filepath: str, task_id: str):
    """文档处理主流程"""
    update_task(task_id, status="running", progress=0, stage="开始处理")

    async with async_session_factory() as db:
        try:
            result = await db.execute(select(Document).where(Document.id == doc_id))
            doc = result.scalar_one_or_none()
            if not doc:
                update_task(task_id, status="failed", error="文档不存在")
                return

            # ---- Stage 1: 解析 ----
            update_task(task_id, progress=5, stage="解析文档内容")
            await _update_doc_status(db, doc, DocumentStatus.PARSING, 5)
            content = read_file_content(filepath)
            if not content:
                raise ValueError("文档内容解析失败或为空")

            word_count = len(content)
            token_count = count_tokens_approximate(content)
            doc.word_count = word_count
            doc.token_count = token_count
            await db.flush()

            # ---- Stage 2: NLP 粗筛 ----
            update_task(task_id, progress=20, stage="NLP 实体粗筛")
            await _update_doc_status(db, doc, DocumentStatus.NLP_EXTRACTING, 20)
            from app.services.extraction_service import ExtractionService
            extractor = ExtractionService(use_llm=False)
            result_graph = await extractor.extract(content)
            doc.entity_count = len(result_graph.get("nodes", []))
            doc.relationship_count = len(result_graph.get("links", []))
            await db.flush()

            # ---- Stage 3: LLM 精炼 ----
            update_task(task_id, progress=40, stage="LLM 实体精炼")
            await _update_doc_status(db, doc, DocumentStatus.LLM_REFINING, 40)
            try:
                extractor_llm = ExtractionService(use_llm=True)
                refined_graph = await extractor_llm.extract(content)
                doc.entity_count = len(refined_graph.get("nodes", []))
                doc.relationship_count = len(refined_graph.get("links", []))
                await db.flush()
            except Exception as e:
                logger.warning(f"LLM 精炼跳过: {e}")
                # 不阻塞流程，使用 NLP 结果

            # ---- Stage 4: 分块 ----
            update_task(task_id, progress=60, stage="语义分块")
            await _update_doc_status(db, doc, DocumentStatus.CHUNKING, 60)
            from app.services.chunking_service import SemanticChunker
            from app.core.config import config
            chunker = SemanticChunker(
                parent_chunk_size=config.PARENT_CHUNK_SIZE,
                child_chunk_size=config.CHILD_CHUNK_SIZE,
                chunk_overlap=config.CHUNK_OVERLAP,
                strategy="parent_child",
            )
            chunks = chunker.chunk(content, doc_id)
            child_chunks = [c for c in chunks if c.chunk_level == "child"]
            doc.chunk_count = len(chunks)
            await db.flush()

            # ---- Stage 5: Embedding ----
            update_task(task_id, progress=80, stage="生成向量嵌入")
            await _update_doc_status(db, doc, DocumentStatus.EMBEDDING, 80)
            from app.services.embedding_service import EmbeddingService
            child_texts = [c.text for c in child_chunks]
            embeddings = EmbeddingService.encode(child_texts)

            # ---- Stage 6: 向量索引 ----
            update_task(task_id, progress=95, stage="构建检索索引")
            await _update_doc_status(db, doc, DocumentStatus.INDEXING, 95)
            from app.services.hybrid_search import HybridSearchService
            hybrid = HybridSearchService()
            chunk_dicts = [c.to_dict() for c in child_chunks]
            hybrid.index_document(chunk_dicts, embeddings)

            # ---- 完成 ----
            import json
            # 保存图谱数据供 graph 端点使用
            final_graph = refined_graph if 'refined_graph' in dir() else result_graph
            doc.graph_data = json.dumps(final_graph, ensure_ascii=False)
            doc.status = DocumentStatus.DONE
            doc.progress = 100.0
            doc.processed_at = datetime.now()
            await db.flush()

            update_task(
                task_id,
                status="done",
                progress=100,
                stage="处理完成",
                result={
                    "word_count": word_count,
                    "token_count": token_count,
                    "chunk_count": len(chunks),
                    "entity_count": doc.entity_count,
                    "relationship_count": doc.relationship_count,
                },
            )
            logger.info(f"文档处理完成: {doc.filename}")

        except Exception as e:
            logger.error(f"文档处理失败: {doc_id}, error: {e}")
            logger.error(traceback.format_exc())
            update_task(task_id, status="failed", error=str(e), stage="处理失败")

            # 更新文档状态
            try:
                result = await db.execute(select(Document).where(Document.id == doc_id))
                doc = result.scalar_one_or_none()
                if doc:
                    doc.status = DocumentStatus.FAILED
                    doc.error_message = str(e)
                    await db.flush()
            except Exception as status_error:
                logger.error(f"更新文档失败状态时出错: {status_error}")


async def _update_doc_status(
    db: AsyncSession, doc: Document, status: DocumentStatus, progress: float
):
    """更新文档处理状态"""
    doc.status = status
    doc.progress = progress
    await db.flush()
