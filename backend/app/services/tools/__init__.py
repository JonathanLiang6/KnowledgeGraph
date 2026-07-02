"""
Agent 工具集 — Phase 2 Agentic RAG + v3.2 扩展

每个工具都是一个标准化的 async 函数，被 AgentService 的 ReAct 循环调用。
工具接口: async def tool(db, kb_id, **kwargs) -> str (返回可读的结果文本)

v3.2: + web_search (Q8), + analyze_coverage (Q9)
"""
from .vector_search import vector_search
from .graph_traverse import graph_traverse
from .entity_lookup import entity_lookup
from .bm25_search import bm25_search
from .web_search import web_search
from .analyze_coverage import analyze_coverage

# 工具注册表 — Agent 通过此表发现可用工具
TOOL_REGISTRY = {
    "vector_search": {
        "function": vector_search,
        "description": "语义向量检索。在知识库中查找与查询语义相似的文档片段。适合模糊概念查询。",
        "parameters": {"query": "搜索查询文本", "top_k": "返回结果数(默认5)"},
    },
    "graph_traverse": {
        "function": graph_traverse,
        "description": "知识图谱多跳遍历。从指定实体出发沿关系路径探索关联实体。适合关系型/多步推理问题。",
        "parameters": {"entity_name": "起始实体名称", "max_hops": "最大跳数(默认2)"},
    },
    "entity_lookup": {
        "function": entity_lookup,
        "description": "实体详情查询。查找知识图谱中某个实体的属性、描述和关联文档。适合了解特定概念/人物/事物。",
        "parameters": {"entity_name": "要查询的实体名称"},
    },
    "bm25_search": {
        "function": bm25_search,
        "description": "关键词精确匹配检索。在知识库中查找包含特定术语/编号的文档片段。适合精确术语查询。",
        "parameters": {"keywords": "关键词（空格分隔）", "top_k": "返回结果数(默认5)"},
    },
    "web_search": {
        "function": web_search,
        "description": "🌐 互联网搜索（仅当本地知识库信息不足或用户询问时效性内容时使用）。"
                     "使用 DuckDuckGo 搜索互联网获取最新信息。",
        "parameters": {"query": "搜索查询文本", "max_results": "返回结果数(默认3)"},
    },
    "analyze_coverage": {
        "function": analyze_coverage,
        "description": "📊 知识库覆盖诊断。分析当前知识库的实体分布，识别强项与薄弱领域。"
                     "适合用户询问'分析知识库'、'覆盖情况'等场景。",
        "parameters": {},
    },
}


def get_tools_description(enable_web: bool = False) -> str:
    """生成工具描述文本，注入 Agent 的 system prompt

    Args:
        enable_web: 是否包含 web_search 工具（由用户控制开关）
    """
    lines = []
    for name, info in TOOL_REGISTRY.items():
        # v3.2: web_search 仅在 enable_web=True 时暴露
        if name == "web_search" and not enable_web:
            continue
        params = ", ".join(
            f"{k}: {v}" for k, v in info["parameters"].items()
        )
        lines.append(f"- {name}({params}): {info['description']}")
    return "\n".join(lines)
