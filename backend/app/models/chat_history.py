"""
聊天历史模型
"""
import uuid
from datetime import datetime
from sqlalchemy import String, Text, DateTime, ForeignKey, JSON, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base


class ChatHistory(Base):
    """聊天历史表"""

    __tablename__ = "chat_histories"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    kb_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("knowledge_bases.id", ondelete="CASCADE"),
        nullable=False, comment="所属知识库ID"
    )
    session_id: Mapped[str] = mapped_column(
        String(36), nullable=False, index=True, comment="会话ID"
    )
    role: Mapped[str] = mapped_column(
        String(20), nullable=False, comment="角色: user/assistant/system"
    )
    content: Mapped[str] = mapped_column(Text, nullable=False, comment="消息内容")
    sources: Mapped[dict] = mapped_column(
        JSON, default=dict, comment="引用的来源 chunks/entities"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), comment="创建时间"
    )

    # 关联
    knowledge_base = relationship("KnowledgeBase", back_populates="chat_histories")

    def __repr__(self) -> str:
        return f"<ChatHistory(id={self.id}, session={self.session_id}, role={self.role})>"
