"""
图实体与关系 ORM 模型 - Phase 1 GraphRAG 独立图存储

将知识图谱从 Document.graph_data JSON 字段升级为独立的关系表，
支持跨文档实体对齐、图遍历、社区检测等真正的 GraphRAG 能力。
"""
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, String, Text, func
from sqlalchemy.dialects.sqlite import JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class GraphEntity(Base):
    """图实体表 - 跨文档统一的知识图谱实体节点"""

    __tablename__ = "graph_entities"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    kb_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("knowledge_bases.id", ondelete="CASCADE"),
        nullable=False, index=True, comment="所属知识库ID"
    )
    name: Mapped[str] = mapped_column(
        String(500), nullable=False, index=True, comment="实体名称"
    )
    entity_type: Mapped[str] = mapped_column(
        String(100), nullable=False, default="概念", index=True, comment="实体类型"
    )
    description: Mapped[str] = mapped_column(
        Text, default="", comment="实体描述/摘要"
    )
    weight: Mapped[float] = mapped_column(
        Float, default=0.5, comment="实体权重 (0-1)"
    )
    color: Mapped[str] = mapped_column(
        String(20), default="#4F8CF7", comment="前端显示颜色"
    )
    # 来源追踪：记录实体来自哪些文档及片段
    source_doc_ids: Mapped[dict | None] = mapped_column(
        JSON, nullable=True, default=None,
        comment="来源文档列表 [{\"doc_id\": \"...\", \"sentence\": \"...\"}]"
    )
    properties: Mapped[dict | None] = mapped_column(
        JSON, nullable=True, default=None, comment="扩展属性 (JSON)"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), comment="创建时间"
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now(), comment="更新时间"
    )

    # 关系：发出的边和进入的边
    relations_out = relationship(
        "GraphRelation", foreign_keys="GraphRelation.source_id",
        back_populates="source_entity", cascade="all, delete-orphan"
    )
    relations_in = relationship(
        "GraphRelation", foreign_keys="GraphRelation.target_id",
        back_populates="target_entity", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<GraphEntity(id={self.id}, name={self.name}, type={self.entity_type})>"


class GraphRelation(Base):
    """图关系表 - 实体间的有向关系边"""

    __tablename__ = "graph_relations"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    kb_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("knowledge_bases.id", ondelete="CASCADE"),
        nullable=False, index=True, comment="所属知识库ID"
    )
    source_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("graph_entities.id", ondelete="CASCADE"),
        nullable=False, index=True, comment="源实体ID"
    )
    target_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("graph_entities.id", ondelete="CASCADE"),
        nullable=False, index=True, comment="目标实体ID"
    )
    relation_type: Mapped[str] = mapped_column(
        String(100), nullable=False, default="关联", index=True, comment="关系类型"
    )
    description: Mapped[str] = mapped_column(
        Text, default="", comment="关系描述"
    )
    weight: Mapped[float] = mapped_column(
        Float, default=0.5, comment="关系权重 (0-1)"
    )
    sentence: Mapped[str] = mapped_column(
        Text, default="", comment="关系来源句子"
    )
    source_doc_id: Mapped[str | None] = mapped_column(
        String(36), nullable=True, default=None, comment="来源文档ID"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), comment="创建时间"
    )

    # ORM 关联
    source_entity = relationship(
        "GraphEntity", foreign_keys=[source_id], back_populates="relations_out"
    )
    target_entity = relationship(
        "GraphEntity", foreign_keys=[target_id], back_populates="relations_in"
    )

    def __repr__(self) -> str:
        return (
            f"<GraphRelation(id={self.id}, "
            f"{self.source_id} -[{self.relation_type}]-> {self.target_id})>"
        )
