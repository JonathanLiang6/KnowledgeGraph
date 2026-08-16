"""
专用 CPU 线程池 (v4.1 #51)

事件循环绝不应直接执行 BERT/CrossEncoder 推理、LanceDB/FTS5 查询等
同步 CPU/IO 密集操作 — 全部经此池执行，且受 CPU_WORKER_THREADS 配置约束
（此前 run_in_executor(None, ...) 走默认线程池，该配置从未被消费）。
"""
from concurrent.futures import ThreadPoolExecutor

from app.core.config import config

_CPU_POOL: ThreadPoolExecutor | None = None


def get_cpu_pool() -> ThreadPoolExecutor:
    """获取全局共享的 CPU 线程池（懒初始化，进程内单例）"""
    global _CPU_POOL
    if _CPU_POOL is None:
        workers = max(1, config.CPU_WORKER_THREADS)
        _CPU_POOL = ThreadPoolExecutor(
            max_workers=workers,
            thread_name_prefix="kg-cpu",
        )
    return _CPU_POOL


def shutdown_cpu_pool() -> None:
    """应用关闭时调用，优雅关停线程池"""
    global _CPU_POOL
    if _CPU_POOL is not None:
        _CPU_POOL.shutdown(wait=False)
        _CPU_POOL = None
