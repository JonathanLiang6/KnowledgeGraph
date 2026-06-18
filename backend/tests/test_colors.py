"""
颜色模块单元测试 — 验证 fallback 一致性
"""
from app.core.colors import get_color_for_type, get_legend, TYPE_COLORS, FALLBACK_COLORS


def test_type_colors_not_empty():
    """验证配色字典非空"""
    assert len(TYPE_COLORS) > 0
    assert len(FALLBACK_COLORS) > 0


def test_get_color_for_type_known():
    """已知类型返回固定颜色"""
    color = get_color_for_type("概念")
    assert color == "#4F8CF7"


def test_get_color_for_type_english():
    """v2.3: 英文类型名也能匹配"""
    color = get_color_for_type("concept")
    assert color == "#4F8CF7"


def test_get_color_for_type_unknown_deterministic():
    """v2.3: 未知类型两次调用返回相同颜色"""
    c1 = get_color_for_type("量子纠缠")
    c2 = get_color_for_type("量子纠缠")
    assert c1 == c2


def test_get_color_and_get_legend_consistent():
    """v2.3: get_color_for_type 和 get_legend 对同一未知类型返回相同颜色"""
    types = {"概念", "量子纠缠", "弦理论", "concept"}
    legend = get_legend(types)
    for t in types:
        assert get_color_for_type(t) == legend[t]
