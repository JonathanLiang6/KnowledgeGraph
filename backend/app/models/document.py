"""
文档模型
"""
import uuid
import enum
from datetime import datetime
from sqlalchemy import String, Text, Integer, Float, DateTime, Enum, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base


class DocumentStatus(str, enum.Enum):
    """文档处理状态"""
    PENDING = "pending"
    PARSING = "parsing"
    NLP_EXTRACTING = "nlp_extracting"
    LLM_REFINING = "llm_refining"
    CHUNKING = "chunking"
    EMBEDDING = "embedding"
    INDEXING = "indexing"
    DONE = "done"
    FAILED = "failed"


class Document(Base):
    """文档表 - 存储上传文档的元数据与处理状态"""

    __tablename__ = "documents"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    kb_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("knowledge_bases.id", ondelete="CASCADE"),
        nullable=False, comment="所属知识库ID"
    )

    # 文件信息
    filename: Mapped[str] = mapped_column(String(500), nullable=False, comment="原始文件名")
    file_path: Mapped[str] = mapped_column(String(1000), nullable=False, comment="存储路径")
    file_type: Mapped[str] = mapped_column(String(20), default="unknown", comment="文件类型")
    file_size: Mapped[int] = mapped_column(Integer, default=0, comment="文件大小(字节)")

    # 处理状态
    status: Mapped[DocumentStatus] = mapped_column(
        Enum(DocumentStatus), default=DocumentStatus.PENDING, comment="处理状态"
    )
    progress: Mapped[float] = mapped_column(Float, default=0.0, comment="处理进度 0-100")

    # 统计信息
    word_count: Mapped[int] = mapped_column(Integer, default=0, comment="字数")
    token_count: Mapped[int] = mapped_column(Integer, default=0, comment="Token消耗")
    chunk_count: Mapped[int] = mapped_column(Integer, default=0, comment="分块数量")
    entity_count: Mapped[int] = mapped_column(Integer, default=0, comment="提取实体数")
    relationship_count: Mapped[int] = mapped_column(Integer, default=0, comment="提取关系数")

    # 错误信息
    error_message: Mapped[str] = mapped_column(Text, default="", comment="错误信息")

    # 图谱数据 (JSON 字符串，提取完成时写入)
    graph_data: Mapped[str] = mapped_column(Text, nullable=True, default=None, comment="提取的图谱数据JSON")

    # 时间戳
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), comment="上传时间"
    )
    processed_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=True, comment="处理完成时间"
    )

    # 关联
    knowledge_base = relationship("KnowledgeBase", back_populates="documents")

    def __repr__(self) -> str:
        return f"<Document(id={self.id}, name={self.filename}, status={self.status})>"
