"""
统一实体类型配色模块 — 整个项目的唯一配色真相来源 (single source of truth)

v2.3: 中英双语键 + 确定性哈希 fallback

使用方式:
    from app.core.colors import TYPE_COLORS, get_color_for_type, FALLBACK_COLORS
"""

# ── 20 种常见实体类型的固定配色 ──────────────────────────────
# 设计原则: 色相环均匀分布, 对比度 ≥ 4.5:1 (WCAG AA), 冷/暖色调混搭
# v2.3: 同时提供中英文键, 与 settings.yaml entity_types 对齐
TYPE_COLORS: dict[str, str] = {
    # 冷色系 (认知/逻辑)
    "概念": "#4F8CF7",   # 蓝
    "concept": "#4F8CF7",
    "理论": "#5C6BC0",   # 靛蓝
    "theory": "#5C6BC0",
    "方法": "#26A69A",   # 青绿
    "method": "#26A69A",
    "技术": "#4DD0E1",   # 天蓝
    "technology": "#4DD0E1",
    "算法": "#42A5F5",   # 浅蓝
    "algorithm": "#42A5F5",
    "框架": "#64B5F6",   # 柔和蓝
    "framework": "#64B5F6",
    "公式": "#7C5CFC",   # 紫罗兰
    "formula": "#7C5CFC",
    "模型": "#00ACC1",   # 深青
    "model": "#00ACC1",
    "术语": "#90A4AE",   # 灰蓝
    "term": "#90A4AE",
    "topic": "#90A4AE",  # 同术语
    "定义": "#90A4AE",   # 同术语
    "definition": "#90A4AE",

    # 暖色系 (人物/组织)
    "人物": "#E57373",   # 柔红
    "person": "#E57373",
    "组织": "#FF8A65",   # 暖橙
    "organization": "#FF8A65",
    "机构": "#FF7043",   # 深橙
    "institution": "#FF7043",
    "事件": "#FFB74D",   # 琥珀
    "event": "#FFB74D",

    # 中性/混合
    "地点": "#4DB6AC",   # 蓝绿
    "location": "#4DB6AC",
    "学科": "#81C784",   # 柔绿
    "discipline": "#81C784",
    "应用": "#AED581",   # 浅绿
    "application": "#AED581",
    "数据": "#A1887F",   # 暖灰
    "data": "#A1887F",
    "著作": "#FFD54F",   # 金
    "work": "#FFD54F",
    "时间": "#EF5350",   # 珊瑚
    "time": "#EF5350",
    "定律": "#BA68C8",   # 淡紫
    "law": "#BA68C8",
    "定理": "#BA68C8",   # 同定律
    "theorem": "#BA68C8",
    "原理": "#5C6BC0",   # 同理论
    "principle": "#5C6BC0",
    "流程": "#26A69A",   # 同方法
    "process": "#26A69A",
    "特性": "#4DD0E1",   # 同技术
    "characteristic": "#4DD0E1",
    "结构": "#00ACC1",   # 同模型
    "structure": "#00ACC1",
    "功能": "#42A5F5",   # 同算法
    "function": "#42A5F5",
    "标准": "#64B5F6",   # 同框架
    "standard": "#64B5F6",
    "规则": "#7C5CFC",   # 同公式
    "rule": "#7C5CFC",
    "工具": "#4DD0E1",   # 同技术
    "tool": "#4DD0E1",
    "资源": "#AED581",   # 同应用
    "resource": "#AED581",
    "案例": "#81C784",   # 同学科
    "case": "#81C784",
    "问题": "#E57373",   # 同人物（区分度）
    "problem": "#E57373",
    "解决方案": "#26A69A",  # 同方法
    "solution": "#26A69A",
    "文档": "#A1887F",   # 同数据
    "document_type": "#A1887F",
    "分类": "#90A4AE",   # 同术语
    "classification": "#90A4AE",
    "关系": "#BA68C8",   # 同定律
    "relationship": "#BA68C8",
    "组成部分": "#FF8A65",  # 同组织
    "component": "#FF8A65",
    "属性": "#4DB6AC",   # 同地点
    "attribute": "#4DB6AC",
    "要求": "#FF7043",   # 同机构
    "requirement": "#FF7043",
    "实践": "#81C784",   # 同学科
    "practice": "#81C784",
    "参考": "#A1887F",   # 同数据
    "reference": "#A1887F",
}

# ── 超出 20 种类型的后备冷色调 ────────────────────────────────
FALLBACK_COLORS: list[str] = [
    "#5C6BC0", "#AB47BC", "#29B6F6", "#9CCC65", "#3F51B5",
    "#8E24AA", "#43A047", "#1E88E5", "#5E35B1", "#00897B",
    "#3949AB", "#039BE5", "#7CB342", "#6D4C41", "#00BFA5",
    "#D32F2F", "#F57C00", "#1976D2", "#388E3C", "#C2185B",
]


def _get_fallback_color(entity_type: str) -> str:
    """基于实体类型名称的确定性哈希 fallback 颜色。保证同类型始终同色。

    v4.1 (#84): 改用 zlib.crc32 — 内置 hash() 受 PYTHONHASHSEED 影响，
    跨进程不稳定，重启后同一类型会漂移到不同颜色。
    """
    import zlib
    idx = zlib.crc32(entity_type.encode("utf-8")) % len(FALLBACK_COLORS)
    return FALLBACK_COLORS[idx]


def get_color_for_type(entity_type: str, index: int = 0) -> str:
    """
    为实体类型获取一致的颜色。

    优先从 TYPE_COLORS 查表，缺失时使用确定性哈希 fallback。
    保证同类型在 get_color_for_type 和 get_legend 中始终同色。
    """
    if entity_type in TYPE_COLORS:
        return TYPE_COLORS[entity_type]
    return _get_fallback_color(entity_type)


def get_legend(types: set[str]) -> dict[str, str]:
    """
    从实体类型集合生成图例字典 (type → color)，按类型名排序。
    v2.3: 使用确定性哈希 fallback, 与 get_color_for_type 保持一致。
    """
    legend: dict[str, str] = {}
    for t in sorted(types):
        if t in TYPE_COLORS:
            legend[t] = TYPE_COLORS[t]
        else:
            legend[t] = _get_fallback_color(t)
    return legend
