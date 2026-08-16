"""
系统监控 API - 任务进度查询、系统状态
v3.1: 任务 TTL 自动清理 + 线程安全 + 版本号从 config 读取
"""
import logging
import threading
import time
from datetime import datetime

from fastapi import APIRouter

from app.core.config import APP_VERSION, config

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/monitor", tags=["系统监控"])

# 任务过期时间（秒）
TASK_TTL_SECONDS = 3600  # 1小时

# 内存任务存储 + threading.Lock 保护
_task_store: dict[str, dict] = {}
_task_store_lock = threading.Lock()


def _purge_expired_tasks():
    """v2.4: 清理过期任务"""
    now = time.monotonic()
    expired = [
        tid for tid, t in _task_store.items()
        if now - t.get("_created_ts", 0) > TASK_TTL_SECONDS
    ]
    for tid in expired:
        del _task_store[tid]
    if expired:
        logger.debug(f"清理 {len(expired)} 个过期任务")


def create_task(task_type: str) -> str:
    """创建新任务并返回 task_id (v2.4: threading.Lock 保护)"""
    import uuid
    with _task_store_lock:
        _purge_expired_tasks()
        task_id = str(uuid.uuid4())
        _task_store[task_id] = {
        "task_id": task_id,
        "type": task_type,
        "status": "pending",
        "progress": 0.0,
        "stage": "等待开始",
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat(),
        "error": None,
        "result": None,
        "_created_ts": time.monotonic(),
    }
    return task_id


def update_task(task_id: str, status: str = None, progress: float = None,
                stage: str = None, error: str = None, result: dict = None):
    """更新任务状态 (v2.4: threading.Lock 保护)"""
    with _task_store_lock:
        if task_id not in _task_store:
            return
        task = _task_store[task_id]
        if status is not None:
            task["status"] = status
        if progress is not None:
            task["progress"] = progress
        if stage is not None:
            task["stage"] = stage
        if error is not None:
            task["error"] = error
        if result is not None:
            task["result"] = result
        task["updated_at"] = datetime.now().isoformat()


@router.get("/tasks")
async def list_tasks():
    """列出所有任务"""
    return {
        "tasks": list(_task_store.values()),
        "total": len(_task_store),
    }


@router.get("/tasks/{task_id}")
async def get_task(task_id: str):
    """查询单个任务状态"""
    task = _task_store.get(task_id)
    if not task:
        return {"error": "任务不存在", "task_id": task_id}
    return task


@router.get("/status")
async def get_system_status():
    """获取系统运行状态"""
    return {
        "status": "running",
        "api_configured": config.is_api_key_set,
        "api_model": config.DEEPSEEK_CHAT_MODEL,
        "server_version": APP_VERSION,
        "timestamp": datetime.now().isoformat(),
        "active_tasks": len(_task_store),
    }
