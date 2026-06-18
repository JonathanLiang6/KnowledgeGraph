"""
统一实体类型配色模块 — 整个项目的唯一配色真相来源 (single source of truth)

使用方式:
    from app.core.colors import TYPE_COLORS, get_color_for_type, FALLBACK_COLORS
"""

# ── 20 种常见实体类型的固定配色 ──────────────────────────────
# 设计原则: 色相环均匀分布, 对比度 ≥ 4.5:1 (WCAG AA), 冷/暖色调混搭
TYPE_COLORS: dict[str, str] = {
    # 冷色系 (认知/逻辑)
    "概念": "#4F8CF7",   # 蓝
    "理论": "#5C6BC0",   # 靛蓝
    "方法": "#26A69A",   # 青绿
    "技术": "#4DD0E1",   # 天蓝
    "算法": "#42A5F5",   # 浅蓝
    "框架": "#64B5F6",   # 柔和蓝
    "公式": "#7C5CFC",   # 紫罗兰
    "模型": "#00ACC1",   # 深青
    "术语": "#90A4AE",   # 灰蓝

    # 暖色系 (人物/组织)
    "人物": "#E57373",   # 柔红
    "组织": "#FF8A65",   # 暖橙
    "机构": "#FF7043",   # 深橙
    "事件": "#FFB74D",   # 琥珀

    # 中性/混合
    "地点": "#4DB6AC",   # 蓝绿
    "学科": "#81C784",   # 柔绿
    "应用": "#AED581",   # 浅绿
    "数据": "#A1887F",   # 暖灰
    "著作": "#FFD54F",   # 金
    "时间": "#EF5350",   # 珊瑚
    "定律": "#BA68C8",   # 淡紫
}

# ── 超出 20 种类型的后备冷色调 ────────────────────────────────
FALLBACK_COLORS: list[str] = [
    "#5C6BC0", "#AB47BC", "#29B6F6", "#9CCC65", "#3F51B5",
    "#8E24AA", "#43A047", "#1E88E5", "#5E35B1", "#00897B",
    "#3949AB", "#039BE5", "#7CB342", "#6D4C41", "#00BFA5",
    "#D32F2F", "#F57C00", "#1976D2", "#388E3C", "#C2185B",
]


def get_color_for_type(entity_type: str, index: int = 0) -> str:
    """
    为实体类型获取一致的颜色。

    优先从 TYPE_COLORS 查表，缺失时从 FALLBACK_COLORS 按 index 轮转分配。
    保证同类型始终同色。
    """
    if entity_type in TYPE_COLORS:
        return TYPE_COLORS[entity_type]
    return FALLBACK_COLORS[index % len(FALLBACK_COLORS)]


def get_legend(types: set[str]) -> dict[str, str]:
    """
    从实体类型集合生成图例字典 (type → color)，按类型名排序。
    """
    legend: dict[str, str] = {}
    fallback_idx = 0
    for t in sorted(types):
        if t in TYPE_COLORS:
            legend[t] = TYPE_COLORS[t]
        else:
            legend[t] = FALLBACK_COLORS[fallback_idx % len(FALLBACK_COLORS)]
            fallback_idx += 1
    return legend
