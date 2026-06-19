"""
系统设置模型
"""
from datetime import datetime
from sqlalchemy import String, JSON, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column
from app.core.database import Base


class SystemSetting(Base):
    """系统设置表 - 键值对存储"""

    __tablename__ = "system_settings"

    key: Mapped[str] = mapped_column(
        String(100), primary_key=True, comment="设置键"
    )
    value: Mapped[dict] = mapped_column(JSON, default=dict, comment="设置值(JSON)")
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now(), comment="更新时间"
    )

    def __repr__(self) -> str:
        return f"<SystemSetting(key={self.key})>"
