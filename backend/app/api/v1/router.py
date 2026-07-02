"""
API v1 路由汇总 - 聚合所有子路由 (v3.2: + topology, + analytics)
"""
from fastapi import APIRouter
from app.api.v1.endpoints import (
    knowledge_base,
    document,
    chat,
    graph,
    settings,
    monitor,
    topology,
    analytics,
)

api_router = APIRouter(prefix="/api/v1")

# 注册各模块路由
api_router.include_router(knowledge_base.router)
api_router.include_router(document.router)
api_router.include_router(chat.router)
api_router.include_router(graph.router)
api_router.include_router(settings.router)
api_router.include_router(monitor.router)
api_router.include_router(topology.router)
api_router.include_router(analytics.router)
