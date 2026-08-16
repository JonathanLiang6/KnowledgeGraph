"""
记忆服务 - Phase 2 Agentic RAG 三层记忆系统

- 工作记忆 (Working Memory): Agent 当前推理循环中的中间步骤
- 情景记忆 (Episodic Memory): 会话级别的对话摘要
- 语义记忆 (Semantic Memory): 知识图谱（由 GraphService 提供）

v3.2: kb_id 隔离 — 存储 Key 统一加 kb_id 前缀，确保不同知识库的记忆相互隔离
v4.0: 添加 asyncio.Lock 保护 _session_memories 并发访问
"""
import asyncio
import time
import logging
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, field

from app.core.config import config

logger = logging.getLogger(__name__)

# 会话记忆 TTL（秒），默认 30 分钟
SESSION_MEMORY_TTL = 30 * 60


@dataclass
class AgentStep:
    """Agent 单步推理记录"""
    step_num: int
    thought: str = ""
    action: str = ""
    action_input: str = ""
    observation: str = ""
    timestamp: float = field(default_factory=time.monotonic)


class WorkingMemory:
    """
    工作记忆 — Agent 当前推理循环中的暂存信息。

    存储 ReAct 循环中的 Thought-Action-Observation 三元组，
    在生成最终答案时作为上下文注入。
    """

    def __init__(self):
        self.steps: List[AgentStep] = []
        self.final_answer: str = ""
        self._scratchpad: List[str] = []
        # v4.0: 从配置读取最大步数，确保与 Agent 配置同步
        # v4.1 (#81): 移除强制下限 10 — 直接使用配置值，与 Agent 循环步数保持一致
        self.max_steps = config.AGENT_MAX_STEPS

    def add_step(self, step: AgentStep):
        """记录一个推理步骤"""
        self.steps.append(step)
        if len(self.steps) > self.max_steps:
            self.steps = self.steps[-self.max_steps:]

    def add_thought(self, text: str):
        """添加临时思考（供特殊场景使用）"""
        self._scratchpad.append(text)
        if len(self._scratchpad) > 20:
            self._scratchpad = self._scratchpad[-20:]

    def get_scratchpad(self) -> List[str]:
        """获取草稿内容"""
        return list(self._scratchpad)

    def get_context(self) -> str:
        """获取工作记忆上下文（注入 LLM prompt）"""
        if not self.steps:
            return ""
        lines = []
        for s in self.steps:
            if s.thought:
                lines.append(f"Thought: {s.thought}")
            if s.action:
                lines.append(f"Action: {s.action}({s.action_input})")
            if s.observation:
                # 截断过长观察
                obs = s.observation[:500]
                if len(s.observation) > 500:
                    obs += "..."
                lines.append(f"Observation: {obs}")
        return "\n".join(lines)

    def clear(self):
        """清空工作记忆"""
        self.steps.clear()
        self.final_answer = ""
        self._scratchpad.clear()


class EpisodicMemory:
    """
    情景记忆 — 对话级别的历史摘要。

    在多轮对话中，压缩之前轮次的问答为简短摘要
    """

    def __init__(self, max_turns: int = 5):
        self.max_turns = max_turns
        self.turns: List[Dict[str, str]] = []

    def add_turn(self, user_query: str, answer: str):
        """记录一轮对话"""
        self.turns.append({
            "query": user_query[:200],
            "answer": answer[:300],
        })
        if len(self.turns) > self.max_turns:
            self.turns = self.turns[-self.max_turns:]

    def get_summary(self) -> str:
        """获取对话历史摘要"""
        if not self.turns:
            return ""
        lines = ["## 对话历史"]
        for i, turn in enumerate(self.turns, 1):
            lines.append(f"用户{i}: {turn['query']}")
            lines.append(f"助手{i}: {turn['answer'][:150]}...")
        return "\n".join(lines)

    def clear(self):
        self.turns.clear()


# ── v3.2: kb_id 隔离 ─────────────────────────────────────────────
# 存储 key: "{kb_id}::{session_id}" → (WorkingMemory, EpisodicMemory, last_access_ts)
# 当 kb_id 为空时使用 "__global__" 作为前缀
_session_memories: Dict[str, Tuple[WorkingMemory, EpisodicMemory, float]] = {}
# v4.0: 并发保护锁
_session_lock = asyncio.Lock()


def _make_session_key(kb_id: str, session_id: str) -> str:
    """生成 kb_id 隔离的会话存储 key"""
    kb_prefix = kb_id if kb_id else "__global__"
    return f"{kb_prefix}::{session_id}"


def _purge_expired_sessions():
    """惰性清理过期会话（调用时触发，需在锁内调用）"""
    now = time.monotonic()
    expired = [
        key for key, (_, _, ts) in _session_memories.items()
        if now - ts > SESSION_MEMORY_TTL
    ]
    for key in expired:
        wm, em, _ = _session_memories[key]
        wm.clear()
        em.clear()
        del _session_memories[key]
    if expired:
        logger.debug(f"清理 {len(expired)} 个过期会话记忆")


async def get_session_memory(kb_id: str, session_id: str) -> tuple:
    """获取或创建会话记忆 (working_memory, episodic_memory)，惰性清理过期会话

    v3.2: 强制 kb_id 隔离 — 不同知识库的记忆互不干扰
    v4.0: 使用 asyncio.Lock 保护并发访问
    """
    async with _session_lock:
        _purge_expired_sessions()
        key = _make_session_key(kb_id, session_id)
        now = time.monotonic()
        if key not in _session_memories:
            _session_memories[key] = (WorkingMemory(), EpisodicMemory(), now)
        else:
            wm, em, _ = _session_memories[key]
            _session_memories[key] = (wm, em, now)  # 刷新访问时间
        wm, em, _ = _session_memories[key]
        return wm, em


async def clear_session_memory(kb_id: str, session_id: str):
    """清除会话记忆（v3.2: 需要 kb_id 隔离, v4.0: 并发保护）"""
    async with _session_lock:
        key = _make_session_key(kb_id, session_id)
        if key in _session_memories:
            wm, em, _ = _session_memories[key]
            wm.clear()
            em.clear()
            del _session_memories[key]
