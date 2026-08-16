"""
拓扑导航模型 - v3.2 Q10 个人知识库拓扑启动台

topology_nodes: 拓扑节点（知识库入口或文件夹）
topology_edges: 拓扑边（星型结构：根节点 ↔ 子节点）
"""
import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class TopologyNode(Base):
    """拓扑节点 — 知识库入口或纯文件夹"""

    __tablename__ = "topology_nodes"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    uuid: Mapped[str] = mapped_column(
        String(36), default=lambda: str(uuid.uuid4()), nullable=False
    )
    name: Mapped[str] = mapped_column(
        String(255), nullable=False, comment="节点名称"
    )
    icon: Mapped[str] = mapped_column(
        String(10), default="📁", comment="Emoji 图标"
    )
    kb_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("knowledge_bases.id", ondelete="SET NULL"),
        nullable=True, default=None, comment="绑定的知识库ID（可空）"
    )
    position_x: Mapped[float] = mapped_column(
        Float, default=0.0, comment="X 坐标"
    )
    position_y: Mapped[float] = mapped_column(
        Float, default=0.0, comment="Y 坐标"
    )
    is_root: Mapped[bool] = mapped_column(
        Boolean, default=False, comment="是否为根节点（全库唯一）"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), comment="创建时间"
    )

    def __repr__(self) -> str:
        return f"<TopologyNode(id={self.id}, name={self.name}, is_root={self.is_root})>"


class TopologyEdge(Base):
    """拓扑边 — 节点间连接（星型结构）"""

    __tablename__ = "topology_edges"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    source_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("topology_nodes.id", ondelete="CASCADE"),
        nullable=False, comment="源节点ID"
    )
    target_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("topology_nodes.id", ondelete="CASCADE"),
        nullable=False, comment="目标节点ID"
    )

    def __repr__(self) -> str:
        return f"<TopologyEdge({self.source_id} -> {self.target_id})>"
