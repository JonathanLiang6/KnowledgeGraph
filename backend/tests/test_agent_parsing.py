"""
Agent 纯逻辑单元测试（不碰数据库 / 不调真实 LLM）

覆盖:
- ReActAgent._parse_tool_input: JSON / 严格 key=value / 含 = 的自然语言 / 空输入 (#82)
- compute_name_similarity: 实体判重混合相似度，中文优化 (#57)
- _truncate_observation: Observation 截断 (#56)
- Agent 配置热更 + LLM 失败短路 (#81/#82)
"""
import pytest

from app.core.config import config

# ══════════════════════════════════════════════════════════
# _parse_tool_input (#82)
# ══════════════════════════════════════════════════════════

def _agent():
    """构造无需数据库的 Agent 实例（仅测试纯解析逻辑）"""
    from app.services.agent_service import ReActAgent
    return ReActAgent.__new__(ReActAgent)  # 跳过 __init__（不初始化记忆/DB）


def test_parse_tool_input_json():
    """JSON 对象输入 → 直接解析为 dict"""
    result = _agent()._parse_tool_input(
        "vector_search", '{"query": "机器学习", "top_k": 3}'
    )
    assert result == {"query": "机器学习", "top_k": 3}


def test_parse_tool_input_json_non_dict():
    """JSON 但非对象（如数组）→ 不按 JSON 结果，落入后续分支"""
    result = _agent()._parse_tool_input("vector_search", '["机器学习"]')
    # 非 dict 的 JSON 解析结果不采纳，作为查询位置参数
    assert result == {"query": '["机器学习"]'}


def test_parse_tool_input_strict_kv():
    """严格 key=value → 按 kv 拆分"""
    result = _agent()._parse_tool_input("vector_search", "query=机器学习")
    assert result == {"query": "机器学习"}


def test_parse_tool_input_strict_multi_kv():
    """多个 key=value（允许逗号后空格）→ 按 kv 拆分"""
    result = _agent()._parse_tool_input("vector_search", "query=机器学习, top_k=3")
    assert result == {"query": "机器学习", "top_k": "3"}


def test_parse_tool_input_natural_language_with_equals():
    """含 = 的自然语言（"什么是 a=b"）→ 必须作为 query，不得误拆 kv"""
    result = _agent()._parse_tool_input("vector_search", "什么是 a=b")
    assert result == {"query": "什么是 a=b"}


def test_parse_tool_input_kv_space_in_key():
    """key 含空格 → 不是合法 kv，整体作为查询"""
    result = _agent()._parse_tool_input("vector_search", "什么是 机器学习=入门")
    assert result == {"query": "什么是 机器学习=入门"}


def test_parse_tool_input_natural_language():
    """纯自然语言（无 =）→ 作为第一个位置参数"""
    result = _agent()._parse_tool_input("vector_search", "深度学习入门")
    assert result == {"query": "深度学习入门"}


def test_parse_tool_input_first_param_mapping():
    """不同工具的首参数名不同（graph_traverse → entity_name）"""
    agent = _agent()
    assert agent._parse_tool_input("graph_traverse", "牛顿") == {"entity_name": "牛顿"}
    assert agent._parse_tool_input(
        "graph_traverse", "entity_name=牛顿"
    ) == {"entity_name": "牛顿"}


def test_parse_tool_input_empty():
    """空输入 → 仍映射到首参数（保持旧行为兼容）"""
    result = _agent()._parse_tool_input("vector_search", "")
    assert result == {"query": ""}


def test_parse_tool_input_tool_without_params():
    """无参数工具（analyze_coverage）→ 返回空 dict"""
    result = _agent()._parse_tool_input("analyze_coverage", "分析一下")
    assert result == {}


# ══════════════════════════════════════════════════════════
# compute_name_similarity (#57)
# ══════════════════════════════════════════════════════════

def test_similarity_identical():
    from app.services.llm_refiner import compute_name_similarity
    assert compute_name_similarity("机器学习", "机器学习") == 1.0
    assert compute_name_similarity("AI", "AI") == 1.0


def test_similarity_identical_single_char():
    """单字符（无 bigram）相同 → SequenceMatcher 兜底为 1.0"""
    from app.services.llm_refiner import compute_name_similarity
    assert compute_name_similarity("中", "中") == 1.0


def test_similarity_chinese_better_than_char_jaccard():
    """"机器学习" vs "深度学习"：新混合相似度应高于旧字符集 Jaccard (2/6≈0.333)"""
    from app.services.llm_refiner import compute_name_similarity
    sim = compute_name_similarity("机器学习", "深度学习")
    # 旧实现: 交集{学,习}/并集{机,器,学,习,深,度} = 0.333...
    old_char_jaccard = len({"机", "器", "学", "习"} & {"深", "度", "学", "习"}) / len(
        {"机", "器", "学", "习"} | {"深", "度", "学", "习"}
    )
    assert sim > old_char_jaccard
    # difflib: 公共块"学习" → ratio = 2*2/(4+4) = 0.5
    assert sim == pytest.approx(0.5)


def test_similarity_edit_distance_sensitive():
    """LLM 微调实体名（追加后缀）→ difflib 捕获编辑距离相似度"""
    from app.services.llm_refiner import compute_name_similarity
    sim = compute_name_similarity("机器学习", "机器学习算法")
    assert sim == pytest.approx(0.8)  # SequenceMatcher: 2*4/(4+6)


def test_similarity_mixed_cn_en():
    """中英文混合用例"""
    from app.services.llm_refiner import compute_name_similarity
    # 共享英文子串 + 共同后缀
    sim = compute_name_similarity("Python编程", "Python编程语言")
    # SequenceMatcher: "Python编程"(8字符) 整体子串匹配 → 2*8/(8+10)
    assert sim == pytest.approx(8 / 9)
    # 完全无关
    assert compute_name_similarity("苹果", "banana") == 0.0


def test_similarity_empty_string():
    from app.services.llm_refiner import compute_name_similarity
    assert compute_name_similarity("", "abc") == 0.0
    assert compute_name_similarity("", "") == 0.0


def test_find_best_match_threshold_from_config(monkeypatch):
    """阈值应运行时读取 GRAPH_ENTITY_RESOLUTION_THRESHOLD（默认 0.85，无硬编码 0.75）"""
    from app.services.llm_refiner import LLMEntityRefiner
    candidates = {"机器学习算法": True}

    # 默认阈值 0.85: 相似度 0.8 → 不匹配
    monkeypatch.setattr(config, "GRAPH_ENTITY_RESOLUTION_THRESHOLD", 0.85)
    assert LLMEntityRefiner._find_best_match("机器学习", candidates) is None

    # 调低阈值到 0.75 → 匹配（证明读取的是配置而非硬编码）
    monkeypatch.setattr(config, "GRAPH_ENTITY_RESOLUTION_THRESHOLD", 0.75)
    assert LLMEntityRefiner._find_best_match("机器学习", candidates) == "机器学习算法"

    # 精确匹配优先
    assert LLMEntityRefiner._find_best_match("机器学习算法", candidates) == "机器学习算法"


# ══════════════════════════════════════════════════════════
# _truncate_observation (#56)
# ══════════════════════════════════════════════════════════

def test_truncate_observation_short_untouched():
    from app.services.agent_service import _truncate_observation
    text = "短结果"
    assert _truncate_observation(text, 2000) == text


def test_truncate_observation_long():
    from app.services.agent_service import _truncate_observation
    text = "A" * 60 + "B" * 200 + "C" * 40  # 共 300 字符
    result = _truncate_observation(text, 100)
    # 前 60% + 标记 + 后 40%
    assert result.startswith("A" * 60)
    assert result.endswith("C" * 40)
    assert "[Observation 已截断，共省略 200 字符]" in result
    # 截断后总长受限（远小于原文）
    assert len(result) < 200


def test_truncate_observation_disabled():
    from app.services.agent_service import _truncate_observation
    text = "A" * 500
    assert _truncate_observation(text, 0) == text  # 非正值 = 不限制


# ══════════════════════════════════════════════════════════
# 配置热更 (#81) + LLM 失败短路 (#82)
# ══════════════════════════════════════════════════════════

def test_working_memory_max_steps_follows_config(monkeypatch):
    """WorkingMemory.max_steps 直接使用配置值（原实现强制下限 10）"""
    from app.services.memory_service import WorkingMemory
    monkeypatch.setattr(config, "AGENT_MAX_STEPS", 3)
    assert WorkingMemory().max_steps == 3


@pytest.mark.anyio
async def test_agent_llm_failure_short_circuit(monkeypatch):
    """LLM 调用失败 → 短路返回，不得再触发"达到最大步数"的额外 LLM 调用"""
    from app.services import agent_service

    calls = {"count": 0}

    async def fake_chat(**kwargs):
        calls["count"] += 1
        raise RuntimeError("LLM 服务不可用")

    monkeypatch.setattr(agent_service.DeepSeekClient, "chat", staticmethod(fake_chat))

    agent = agent_service.ReActAgent(db=None, kb_id="test-kb", session_id="test-llm-fail")
    events = [e async for e in agent.run("测试问题")]

    # 仅第一次循环内的调用；失败后短路，不再调用总结 LLM
    assert calls["count"] == 1
    assert any(e["type"] == "agent/error" for e in events)
    assert not any(e["type"] == "agent/answer" for e in events)
    assert events[-1]["type"] == "agent/done"


@pytest.mark.anyio
async def test_agent_max_steps_hot_reload(monkeypatch):
    """AGENT_MAX_STEPS 运行时修改 → Agent 循环按新值执行（不重启进程）"""
    from app.services import agent_service

    calls = {"count": 0}

    async def fake_chat(**kwargs):
        calls["count"] += 1
        return {"content": "Thought: 继续\nAction: nonexistent_tool\nAction Input: x"}

    monkeypatch.setattr(agent_service.DeepSeekClient, "chat", staticmethod(fake_chat))
    monkeypatch.setattr(config, "AGENT_MAX_STEPS", 2)

    agent = agent_service.ReActAgent(db=None, kb_id="test-kb", session_id="test-hot-reload")
    events = [e async for e in agent.run("测试问题")]

    thoughts = [e["content"] for e in events if e["type"] == "agent/thought"]
    assert "推理步骤 1/2..." in thoughts
    assert "推理步骤 2/2..." in thoughts
    assert not any("推理步骤 3/" in t for t in thoughts)  # 未超过热更后的步数
    # 2 步循环 + 1 次总结 = 3 次调用
    assert calls["count"] == 3
    assert events[-2]["type"] == "agent/answer"
    assert events[-1]["type"] == "agent/done"
