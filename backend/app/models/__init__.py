"""
合并所有模型以方便 Base.metadata.create_all
"""
from app.models.knowledge_base import KnowledgeBase
from app.models.document import Document, DocumentStatus
from app.models.chat_history import ChatHistory
from app.models.system_setting import SystemSetting

__all__ = [
    "KnowledgeBase",
    "Document",
    "DocumentStatus",
    "ChatHistory",
    "SystemSetting",
]
