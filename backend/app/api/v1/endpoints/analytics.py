"""
分析 API - v3.2 Q9 知识覆盖热力图

提供知识库实体覆盖分析接口，供前端 ECharts Treemap 渲染。
"""
import logging
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.services.analytics_service import AnalyticsService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/analytics", tags=["知识分析"])


@router.get("/kb/{kb_id}/coverage")
async def get_kb_coverage(
    kb_id: str,
    db: AsyncSession = Depends(get_db),
):
    """
    获取知识库实体覆盖分析数据。

    Returns:
        [{"name": "分类名", "count": 实体数, "last_updated_days": 最近更新天数}, ...]
    """
    coverage = await AnalyticsService.get_kb_coverage(db, kb_id)
    return {
        "kb_id": kb_id,
        "categories": coverage,
        "total_entities": sum(c["count"] for c in coverage),
        "category_count": len(coverage),
    }
