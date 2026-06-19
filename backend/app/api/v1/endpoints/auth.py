"""
认证 API - 预留接口，当前为空占位
"""
from fastapi import APIRouter

router = APIRouter(prefix="/auth", tags=["认证"])


@router.get("/status")
async def auth_status():
    """认证状态"""
    return {"enabled": False, "message": "认证模块尚未启用"}
