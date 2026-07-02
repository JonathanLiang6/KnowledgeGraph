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
import re
import json
import logging
from typing import AsyncGenerator, Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import config
from app.services.deepseek_client import DeepSeekClient
from app.services.tools import TOOL_REGISTRY, get_tools_description
from app.services.memory_service import (
    WorkingMemory, EpisodicMemory, AgentStep,
    get_session_memory, clear_session_memory,
)

logger = logging.getLogger(__name__)

# Agent 最大推理步数（从配置读取）
MAX_AGENT_STEPS = config.AGENT_MAX_STEPS

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

## 工作记忆（之前的推理步骤）

{working_memory}

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
        self.working_memory, self.episodic_memory = get_session_memory(kb_id, session_id)

    async def run(
        self,
        user_query: str,
    ) -> AsyncGenerator[Dict[str, Any], None]:
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
        yield {"type": "agent/thought", "content": f"开始分析问题: {user_query[:100]}..."}

        tools_desc = get_tools_description(enable_web=self.enable_web)
        episodic_context = self.episodic_memory.get_summary()
        web_search_rules = WEB_SEARCH_RULES_ENABLED if self.enable_web else WEB_SEARCH_RULES_DISABLED

        # 构建初始系统提示
        def _build_system_prompt(wm_context: str) -> str:
            return REACT_SYSTEM_PROMPT.format(
                tools_description=tools_desc,
                max_steps=MAX_AGENT_STEPS,
                episodic_memory=episodic_context or "无历史对话",
                working_memory=wm_context,
                user_query=user_query,
                web_search_rules=web_search_rules,
            )

        working_memory_context = self.working_memory.get_context()
        if not working_memory_context:
            working_memory_context = "无（第一步）"

        messages = [
            {"role": "system", "content": _build_system_prompt(working_memory_context)},
        ]

        # Step 循环
        for step_num in range(1, MAX_AGENT_STEPS + 1):
            yield {"type": "agent/thought", "content": f"推理步骤 {step_num}/{MAX_AGENT_STEPS}..."}

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

                # 更新工作记忆上下文并重建系统提示
                working_memory_context = self.working_memory.get_context()
                messages[0]["content"] = _build_system_prompt(working_memory_context)

                # 更新消息继续循环
                messages.append({"role": "assistant", "content": content})
                messages.append({
                    "role": "user",
                    "content": f"Observation: {observation}\n\n"
                               f"请继续推理。如果信息充分，请给出 Final Answer。"
                               f"剩余步数: {MAX_AGENT_STEPS - step_num}",
                })
            else:
                # 没有解析到有效 action，可能是 LLM 直接回答了
                logger.warning(f"Agent step={step_num}: 未解析到有效 action，使用内容作为回答")
                yield {"type": "agent/answer", "content": content}
                self.episodic_memory.add_turn(user_query, content)
                yield {"type": "agent/done"}
                return

        # 达到最大步数，强制生成答案
        logger.info(f"Agent 达到最大步数 {MAX_AGENT_STEPS}，强制生成最终答案")
        yield {"type": "agent/thought", "content": "达到最大推理步数，综合已有信息生成回答..."}

        try:
            summary_messages = messages + [{
                "role": "user",
                "content": (
                    f"你已经完成了 {MAX_AGENT_STEPS} 步推理。请基于以上所有 Observation "
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
            return str(result)
        except Exception as e:
            logger.error(f"工具 {tool_name} 执行失败: {e}")
            return f"工具执行出错: {e}"

    def _parse_tool_input(self, tool_name: str, tool_input: str) -> dict:
        """解析工具输入参数"""
        kwargs = {}

        # 尝试 JSON 解析
        try:
            parsed = json.loads(tool_input)
            if isinstance(parsed, dict):
                return parsed
        except (json.JSONDecodeError, TypeError):
            pass

        # 对于非 JSON 输入，直接作为第一个参数
        param_keys = list(TOOL_REGISTRY[tool_name]["parameters"].keys())
        if param_keys:
            first_param = param_keys[0]
            # 尝试解析 "key=value" 格式
            if "=" in tool_input:
                for part in tool_input.split(","):
                    part = part.strip()
                    if "=" in part:
                        k, v = part.split("=", 1)
                        kwargs[k.strip()] = v.strip().strip("\"'")
            else:
                kwargs[first_param] = tool_input.strip().strip("\"'")

        return kwargs

    def _parse_react_output(self, content: str) -> dict:
        """
        解析 ReAct 格式的 LLM 输出。

        支持的格式:
        - Thought: ... \n Action: tool_name \n Action Input: ...
        - Final Answer: ...
        """
        result = {}

        # 提取 Thought
        thought_match = re.search(r'Thought:\s*(.+?)(?=\n(?:Action|Final)|\Z)', content, re.DOTALL)
        if thought_match:
            result["thought"] = thought_match.group(1).strip()

        # 检查 Final Answer
        final_match = re.search(r'Final\s*Answer:\s*(.+)', content, re.DOTALL | re.IGNORECASE)
        if final_match:
            result["final_answer"] = final_match.group(1).strip()
            return result

        # 提取 Action
        action_match = re.search(r'Action:\s*(\w+)', content)
        if action_match:
            result["action"] = action_match.group(1).strip()

        # 提取 Action Input
        input_match = re.search(r'Action\s*Input:\s*(.+?)(?=\n(?:Observation|Thought)|\Z)', content, re.DOTALL)
        if input_match:
            result["action_input"] = input_match.group(1).strip()

        return result

    @classmethod
    def clear_session(cls, kb_id: str, session_id: str):
        """清除指定会话的 Agent 记忆（v3.2: kb_id 隔离）"""
        clear_session_memory(kb_id, session_id)
