"""
系统设置 API - 仅系统参数和视觉设置，不含 API 密钥
"""
import logging
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.core.database import get_db
from app.core.config import config
from app.models.document import Document
from app.models.system_setting import SystemSetting
from app.models.knowledge_base import KnowledgeBase
from app.schemas.settings import (
    SystemParams,
    VisualSettings,
    SettingsUpdate,
    SystemStatus,
    DataStats,
    SettingsResponse,
)
from app.utils.helpers import format_file_size

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/settings", tags=["系统设置"])

# 默认系统参数
DEFAULT_SYSTEM_PARAMS = SystemParams()
DEFAULT_VISUAL_SETTINGS = VisualSettings()


@router.get("", response_model=SettingsResponse)
async def get_settings(db: AsyncSession = Depends(get_db)):
    """获取系统设置 - 不返回 API 密钥"""
    settings_dict = {}

    # 从数据库加载
    result = await db.execute(select(SystemSetting))
    db_settings = result.scalars().all()
    for s in db_settings:
        settings_dict[s.key] = s.value

    # 系统参数
    system = SystemParams(**settings_dict.get("system", {})) if "system" in settings_dict else DEFAULT_SYSTEM_PARAMS

    # 视觉设置
    visual = VisualSettings(**settings_dict.get("visual", {})) if "visual" in settings_dict else DEFAULT_VISUAL_SETTINGS

    # 系统状态（后端提供，只读）
    status = SystemStatus(
        api_configured=config.is_api_key_set,
        api_model=config.DEEPSEEK_CHAT_MODEL,
        embedding_model=config.EMBEDDING_MODEL,
    )

    # 数据统计
    result = await db.execute(select(Document))
    docs = result.scalars().all()
    kb_result = await db.execute(select(func.count(KnowledgeBase.id)))
    kb_count = kb_result.scalar() or 0

    total_entities = sum(d.entity_count for d in docs)
    total_relations = sum(d.relationship_count for d in docs)
    total_size = sum(d.file_size for d in docs)

    data_stats = DataStats(
        documents=len(docs),
        entities=total_entities,
        relationships=total_relations,
        storage_used=format_file_size(total_size),
        knowledge_bases=kb_count,
    )

    return SettingsResponse(
        system=system,
        visual=visual,
        system_status=status,
        data_stats=data_stats,
    )


@router.post("")
async def save_settings(
    data: SettingsUpdate,
    db: AsyncSession = Depends(get_db),
):
    """保存系统设置 - 仅接受系统参数和视觉设置"""
    if data.system is not None:
        await _upsert_setting(db, "system", data.system.model_dump())

    if data.visual is not None:
        await _upsert_setting(db, "visual", data.visual.model_dump())

    await db.flush()
    return {"message": "设置保存成功"}


async def _upsert_setting(db: AsyncSession, key: str, value: dict):
    """插入或更新设置"""
    from sqlalchemy import select as sa_select

    result = await db.execute(sa_select(SystemSetting).where(SystemSetting.key == key))
    existing = result.scalar_one_or_none()

    if existing:
        existing.value = value
    else:
        db.add(SystemSetting(key=key, value=value))
