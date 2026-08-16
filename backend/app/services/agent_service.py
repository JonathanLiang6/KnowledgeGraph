"""
Agent 服务 - Phase 2 Agentic RAG 核心

ReAct (Reasoning + Acting) 模式的多步推理 Agent。
Agent 自主决策：规划 → 调用工具 → 观察结果 → 反思 → 生成答案。

架构:
  User Query → [Planner] → [Tool Selector] → [Tool Executor]
                  ↑                                    ↓
                  └──── [Reflector] ←──── [Observation] ┘
                  ↓ (信息充分)
            [Final Answer]
"""
import json
import logging
import re
from typing import Any, AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import config
from app.services.deepseek_client import DeepSeekClient
from app.services.memory_service import (
    AgentStep,
    EpisodicMemory,
    WorkingMemory,
    clear_session_memory,
    get_session_memory,
)
from app.services.tools import TOOL_REGISTRY, get_tools_description

logger = logging.getLogger(__name__)

# v4.1 (#81): 不再模块级固化 MAX_AGENT_STEPS — 各处运行时读取 config.AGENT_MAX_STEPS，
# 保证配置修改后无需重启进程即可生效（热更新）


def _truncate_observation(text: str, max_chars: int) -> str:
    """
    v4.1 (#56): 截断过长的 Observation，防止多步检索长文档后上下文爆炸。

    超过 max_chars 时保留前 60% + 截断提示 + 后 40%，提示中标注省略的字符数。
    max_chars 非正数时原样返回（视为不限制）。
    """
    if max_chars <= 0 or len(text) <= max_chars:
        return text
    keep_head = max_chars * 3 // 5   # 前 60%
    keep_tail = max_chars - keep_head  # 后 40%
    omitted = len(text) - keep_head - keep_tail
    marker = f"\n...[Observation 已截断，共省略 {omitted} 字符]...\n"
    return text[:keep_head] + marker + text[len(text) - keep_tail:]

# ReAct System Prompt 模板（v3.2: 联网搜索 + 知识覆盖诊断）
REACT_SYSTEM_PROMPT = """你是一个基于知识图谱的智能问答 Agent。你可以使用以下工具来查找回答问题所需的信息。

## 可用工具

{tools_description}

## 回答格式

在每一步，你必须使用以下格式：

Thought: <你的推理：需要什么信息？为什么？接下来做什么？>
Action: <工具名称>
Action Input: <工具的输入参数>

等待 Observation 结果后，继续下一轮思考。

当你收集到足够信息可以回答用户问题时，使用：

Thought: <总结推理过程>
Final Answer: <最终回答>

## 规则

1. 每次只调用一个工具
2. 每一步都要先 Thought 再 Action
3. 如果工具返回的信息不足以回答问题，继续调用其他工具
4. 最多进行 {max_steps} 步推理
5. 最终答案必须基于工具返回的实际信息，不要编造
6. 如果知识库中没有相关信息，诚实说明
7. 引用信息来源

{web_search_rules}

## 对话历史

{episodic_memory}

用户问题: {user_query}

现在请开始推理。"""

# v3.2: 联网搜索规则
WEB_SEARCH_RULES_ENABLED = """
## 联网搜索规则（当前已启用）

8. **置信度回退**：当本地检索（向量/图谱）结果为空，或最高相似度 < 0.6 时，且知识库内容不足以回答问题，应调用 web_search 获取互联网信息。
9. **时效触发**：若问题包含"今天"、"最新"、"2026"、"新闻"、"天气"、"股价"等时效性关键词，优先调用 web_search。
10. **标注义务**：引用联网内容时，回答开头必须添加 🌐 图标，并注明"以下内容源自互联网搜索，仅供参考"。"""

WEB_SEARCH_RULES_DISABLED = """
## 联网搜索规则（当前已禁用）

8. 仅使用本地知识库的数据回答问题。如果知识库中没有相关信息，直接说明"知识库中暂无相关信息"。
9. 不要尝试搜索互联网。"""


class ReActAgent:
    """
    ReAct Agent — 多步推理 + 工具调用。

    使用方式:
        agent = ReActAgent(db, kb_id, session_id)
        async for event in agent.run(user_query):
            yield event  # SSE 事件流
    """

    def __init__(
        self,
        db: AsyncSession,
        kb_id: str,
        session_id: str = "default",
        enable_web: bool = False,
    ):
        self.db = db
        self.kb_id = kb_id
        self.session_id = session_id
        self.enable_web = enable_web
        # v4.0: get_session_memory 现在是 async 的（内部有并发锁）
        self._memory_initialized = False
        self.working_memory = WorkingMemory()
        self.episodic_memory = EpisodicMemory()

    async def _ensure_memory(self):
        """延迟初始化会话记忆（首次 run 时调用）"""
        if not self._memory_initialized:
            self.working_memory, self.episodic_memory = await get_session_memory(
                self.kb_id, self.session_id
            )
            self._memory_initialized = True

    async def run(
        self,
        user_query: str,
    ) -> AsyncGenerator[dict[str, Any], None]:
        """
        执行 ReAct Agent 循环，yield SSE 事件。

        事件类型:
        - {"type": "agent/thought", "content": "..."}
        - {"type": "agent/action", "tool": "...", "input": "..."}
        - {"type": "agent/observation", "content": "..."}
        - {"type": "agent/answer", "content": "..."}
        - {"type": "agent/error", "content": "..."}
        - {"type": "agent/done"}
        """
        # v4.0: 延迟初始化会话记忆（首次运行）
        await self._ensure_memory()

        # v4.1 (#81): 每次运行时从配置读取最大步数（热更新），单次运行内保持一致
        max_steps = config.AGENT_MAX_STEPS

        yield {"type": "agent/thought", "content": f"开始分析问题: {user_query[:100]}..."}

        tools_desc = get_tools_description(enable_web=self.enable_web)
        episodic_context = self.episodic_memory.get_summary()
        web_search_rules = WEB_SEARCH_RULES_ENABLED if self.enable_web else WEB_SEARCH_RULES_DISABLED

        # 构建初始系统提示（v4.0: 移除冗余的工作记忆注入，通过对话消息传递推理历史）
        def _build_system_prompt() -> str:
            return REACT_SYSTEM_PROMPT.format(
                tools_description=tools_desc,
                max_steps=max_steps,
                episodic_memory=episodic_context or "无历史对话",
                user_query=user_query,
                web_search_rules=web_search_rules,
            )

        messages = [
            {"role": "system", "content": _build_system_prompt()},
        ]

        # v4.1 (#82): 标记 LLM 调用是否失败 — 失败后短路返回，不再触发额外的总结 LLM 调用
        llm_failed = False

        # Step 循环
        for step_num in range(1, max_steps + 1):
            yield {"type": "agent/thought", "content": f"推理步骤 {step_num}/{max_steps}..."}

            # 调用 LLM
            try:
                response = await DeepSeekClient.chat(
                    messages=messages,
                    temperature=config.AGENT_TEMPERATURE,
                    max_tokens=config.AGENT_MAX_TOKENS,
                )
                content = response.get("content", "")
            except Exception as e:
                logger.error(f"Agent LLM 调用失败 step={step_num}: {e}")
                yield {"type": "agent/error", "content": f"LLM调用失败: {e}"}
                llm_failed = True
                break

            # 解析响应
            parsed = self._parse_react_output(content)

            if parsed.get("final_answer"):
                answer = parsed["final_answer"]
                self.working_memory.final_answer = answer
                self.episodic_memory.add_turn(user_query, answer)
                yield {"type": "agent/answer", "content": answer}
                yield {"type": "agent/done"}
                return

            if parsed.get("action") and parsed.get("action_input"):
                action = parsed["action"]
                action_input = parsed["action_input"]
                thought = parsed.get("thought", "")

                # 记录推理步骤
                step = AgentStep(
                    step_num=step_num,
                    thought=thought,
                    action=action,
                    action_input=action_input,
                )

                yield {"type": "agent/thought", "content": thought}
                yield {"type": "agent/action", "tool": action, "input": action_input}

                # 执行工具
                observation = await self._execute_tool(action, action_input)
                step.observation = observation
                self.working_memory.add_step(step)

                yield {"type": "agent/observation", "content": observation}

                # 更新消息继续循环（推理历史通过对话消息传递，无需重建系统提示）
                messages.append({"role": "assistant", "content": content})
                messages.append({
                    "role": "user",
                    "content": f"Observation: {observation}\n\n"
                               f"请继续推理。如果信息充分，请给出 Final Answer。"
                               f"剩余步数: {max_steps - step_num}",
                })
            else:
                # 没有解析到有效 action，可能是 LLM 直接回答了
                logger.warning(f"Agent step={step_num}: 未解析到有效 action，使用内容作为回答")
                yield {"type": "agent/answer", "content": content}
                self.episodic_memory.add_turn(user_query, content)
                yield {"type": "agent/done"}
                return

        # v4.1 (#82): LLM 调用失败 — 短路返回，不再触发"达到最大步数"的额外总结 LLM 调用
        if llm_failed:
            yield {"type": "agent/done"}
            return

        # 达到最大步数，强制生成答案（v4.0: 记录到工作记忆）
        logger.info(f"Agent 达到最大步数 {max_steps}，强制生成最终答案")
        self.working_memory.add_step(AgentStep(
            step_num=max_steps + 1,
            thought="达到最大推理步数，综合已有信息生成回答",
            action="generate_summary",
            action_input="综合所有 Observation",
        ))
        yield {"type": "agent/thought", "content": "达到最大推理步数，综合已有信息生成回答..."}

        try:
            summary_messages = messages + [{
                "role": "user",
                "content": (
                    f"你已经完成了 {max_steps} 步推理。请基于以上所有 Observation "
                    f"综合出一个完整回答。问题: {user_query}"
                ),
            }]
            final = await DeepSeekClient.chat(
                messages=summary_messages,
                temperature=0.3,
                max_tokens=2048,
            )
            answer = final.get("content", "抱歉，无法生成回答。")
        except Exception as e:
            logger.error(f"Agent 最终回答生成失败: {e}")
            answer = f"推理过程中遇到错误: {e}"

        self.episodic_memory.add_turn(user_query, answer)
        yield {"type": "agent/answer", "content": answer}
        yield {"type": "agent/done"}

    async def _execute_tool(self, tool_name: str, tool_input: str) -> str:
        """执行工具调用"""
        tool_info = TOOL_REGISTRY.get(tool_name)
        if not tool_info:
            return f"错误: 未知工具 '{tool_name}'。可用工具: {list(TOOL_REGISTRY.keys())}"

        try:
            # 解析工具输入
            kwargs = {"db": self.db, "kb_id": self.kb_id}
            kwargs.update(self._parse_tool_input(tool_name, tool_input))

            result = await tool_info["function"](**kwargs)
            # v4.1 (#56): 截断过长 Observation，防止上下文爆炸
            return _truncate_observation(str(result), config.AGENT_OBSERVATION_MAX_CHARS)
        except Exception as e:
            logger.error(f"工具 {tool_name} 执行失败: {e}")
            return f"工具执行出错: {e}"

    # v4.1 (#82): 严格 key=value 模式 — key 为字母/数字/中文/下划线/连字符（不含空格），
    # value 不含逗号和等号，逗号分隔（允许逗号前后空白），整体不允许有多余裸文本。
    _KV_KEY = r"[A-Za-z0-9_\-\u4e00-\u9fff]+"
    _STRICT_KV_RE = re.compile(rf"^{_KV_KEY}=[^,=]+(?:\s*,\s*{_KV_KEY}=[^,=]+)*$")

    def _parse_tool_input(self, tool_name: str, tool_input: str) -> dict:
        """
        解析工具输入参数。

        优先级:
        1. JSON 对象 → 直接返回
        2. 严格匹配 "key=value[,key=value]*" → 按 key=value 拆分
        3. 其余（含 "=" 的自然语言，如 "什么是 a=b"）→ 整体作为第一个位置参数
        """
        if tool_input is None:
            tool_input = ""

        # 尝试 JSON 解析
        try:
            parsed = json.loads(tool_input)
            if isinstance(parsed, dict):
                return parsed
        except (json.JSONDecodeError, TypeError):
            pass

        # 对于非 JSON 输入，直接作为第一个参数
        param_keys = list(TOOL_REGISTRY[tool_name]["parameters"].keys())
        if not param_keys:
            return {}

        first_param = param_keys[0]
        text = tool_input.strip().strip("\"'")

        # 仅当整体严格匹配 key=value 列表时才拆 kv；否则视为自然语言查询
        # （fullmatch 避免 $ 匹配尾部换行导致的误判）
        if text and self._STRICT_KV_RE.fullmatch(text):
            kwargs = {}
            for part in text.split(","):
                k, v = part.split("=", 1)
                kwargs[k.strip()] = v.strip().strip("\"'")
            return kwargs

        return {first_param: text}

    def _parse_react_output(self, content: str) -> dict:
        """
        解析 ReAct 格式的 LLM 输出（v4.0: 更健壮的多行解析）。

        支持的格式:
        - Thought: ... \\n Action: tool_name \\n Action Input: ...
        - Final Answer: ...
        """
        result = {}

        # 检查 Final Answer（优先，避免误解析）
        final_match = re.search(r'Final\s*Answer:\s*(.+)', content, re.DOTALL | re.IGNORECASE)
        if final_match:
            result["final_answer"] = final_match.group(1).strip()
            return result

        # v4.0: 提取 Thought — 支持多行内容，一直匹配到 Action 或 Final 为止
        thought_match = re.search(
            r'Thought:\s*(.+?)(?=\n\s*(?:Action|Final)|\Z)',
            content, re.DOTALL | re.IGNORECASE
        )
        if thought_match:
            result["thought"] = thought_match.group(1).strip()

        # 提取 Action
        action_match = re.search(r'Action:\s*(\w+)', content, re.IGNORECASE)
        if action_match:
            result["action"] = action_match.group(1).strip()

        # v4.0: 提取 Action Input — 支持多行输入，到 Observation/Thought 或结尾
        input_match = re.search(
            r'Action\s*Input:\s*(.+?)(?=\n\s*(?:Observation|Thought|Action)|\Z)',
            content, re.DOTALL | re.IGNORECASE
        )
        if input_match:
            result["action_input"] = input_match.group(1).strip()

        return result

    @classmethod
    async def clear_session(cls, kb_id: str, session_id: str):
        """清除指定会话的 Agent 记忆（v3.2: kb_id 隔离）— v4.0: 修复缺少 await"""
        await clear_session_memory(kb_id, session_id)
