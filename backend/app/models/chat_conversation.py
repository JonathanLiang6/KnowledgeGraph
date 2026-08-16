"""
对话历史 ORM 模型 - v4.2 对话持久化

将聊天记录从 localStorage 迁移到服务端存储：
- ChatConversation: 一个知识库下的多轮对话（可命名/重命名）
- ChatMessage: 对话内消息（含 Agent 推理步骤 JSON）
"""
import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.dialects.sqlite import JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class ChatConversation(Base):
    """对话表 — 网页聊天应用式会话管理"""

    __tablename__ = "chat_conversations"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    kb_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("knowledge_bases.id", ondelete="CASCADE"),
        nullable=False, index=True, comment="所属知识库ID"
    )
    title: Mapped[str] = mapped_column(
        String(200), nullable=False, default="新对话", comment="对话标题（可重命名）"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), comment="创建时间"
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now(),
        comment="最后活跃时间（发消息时刷新）"
    )

    messages: Mapped[list["ChatMessage"]] = relationship(
        "ChatMessage",
        cascade="all, delete-orphan",
        order_by="ChatMessage.created_at",
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return f"<ChatConversation(id={self.id}, title={self.title!r}, kb={self.kb_id})>"


class ChatMessage(Base):
    """对话消息表"""

    __tablename__ = "chat_messages"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    conversation_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("chat_conversations.id", ondelete="CASCADE"),
        nullable=False, index=True, comment="所属对话ID"
    )
    role: Mapped[str] = mapped_column(
        String(20), nullable=False, comment="角色: user/assistant"
    )
    content: Mapped[str] = mapped_column(
        Text, nullable=False, default="", comment="消息内容"
    )
    # Agent 推理步骤（thought/action/observation 列表），普通问答为 NULL
    reasoning_steps: Mapped[list | None] = mapped_column(
        JSON, nullable=True, default=None, comment="Agent 推理步骤"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), comment="创建时间"
    )

    def __repr__(self) -> str:
        return f"<ChatMessage(id={self.id}, role={self.role}, len={len(self.content)})>"
