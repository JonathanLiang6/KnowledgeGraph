"""
联网搜索工具 - v3.2 Q8 Agent 联网搜索

使用 DuckDuckGo 免费搜索（无需 API Key），返回 Top 3 结果。
当本地知识库检索结果不足或用户询问时效性内容时自动触发。
"""
import logging
from typing import Optional

logger = logging.getLogger(__name__)


async def web_search(
    db=None,
    kb_id: Optional[str] = None,
    query: str = "",
    max_results: int = 3,
    **kwargs,
) -> str:
    """
    联网搜索工具 — DuckDuckGo 文本搜索。

    Args:
        query: 搜索查询文本
        max_results: 最大返回结果数（默认 3）

    Returns:
        格式化的搜索结果文本
    """
    if not query or not query.strip():
        return "错误: 搜索查询不能为空"

    query = query.strip()
    logger.info(f"联网搜索: query='{query[:100]}...'")

    try:
        from duckduckgo_search import DDGS

        results = []
        with DDGS() as ddgs:
            for r in ddgs.text(query, max_results=max_results):
                results.append({
                    "title": r.get("title", ""),
                    "snippet": r.get("body", "")[:200],
                    "link": r.get("href", ""),
                })

        if not results:
            return f"🌐 联网搜索未找到与 '{query}' 相关的结果。"

        lines = [f"🌐 联网搜索结果 (查询: {query}):"]
        for i, r in enumerate(results, 1):
            lines.append(f"\n{i}. **{r['title']}**")
            lines.append(f"   {r['snippet']}")
            lines.append(f"   来源: {r['link']}")

        return "\n".join(lines)

    except ImportError:
        logger.warning("duckduckgo-search 未安装，web_search 不可用")
        return "错误: 联网搜索功能未安装（缺少 duckduckgo-search 依赖）。"
    except Exception as e:
        logger.error(f"联网搜索失败: {e}")
        return f"🌐 联网搜索遇到错误: {e}"
