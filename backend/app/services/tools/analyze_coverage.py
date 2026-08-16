"""
知识覆盖诊断工具 - v3.2 Q9

Agent 调用此工具时，自动分析当前知识库的实体覆盖情况，
识别强项和薄弱领域，生成覆盖诊断报告。
"""
import logging

logger = logging.getLogger(__name__)


async def analyze_coverage(
    db=None,
    kb_id: str | None = None,
    **kwargs,
) -> str:
    """
    知识库覆盖诊断工具 — 分析实体分布，识别知识盲区。

    返回每个分类的实体数、最后更新天数，帮助用户发现薄弱领域。

    Args:
        kb_id: 知识库ID（由 Agent 自动注入）
    """
    if not kb_id:
        return "错误: 未指定知识库ID，无法进行覆盖分析。"

    try:
        from app.services.analytics_service import AnalyticsService
        coverage = await AnalyticsService.get_kb_coverage(db, kb_id)

        if not coverage:
            return f"知识库 {kb_id} 暂无实体数据，无法进行覆盖分析。请先上传文档并完成处理。"

        lines = [f"📊 知识库覆盖分析报告 (kb_id={kb_id}):"]
        lines.append(f"\n总计 {len(coverage)} 个分类，{sum(c['count'] for c in coverage)} 个实体。")

        # 按实体数降序排列
        coverage_sorted = sorted(coverage, key=lambda c: c["count"], reverse=True)

        # 强项（前 3）
        top3 = coverage_sorted[:3]
        lines.append("\n## 🟢 知识强项 (实体数最多的领域)")
        for c in top3:
            lines.append(f"  - {c['name']}: {c['count']} 个实体 (最后更新 {c['last_updated_days']} 天前)")

        # 弱项（实体数 ≤ 3）
        weak = [c for c in coverage_sorted if c["count"] <= 3]
        if weak:
            lines.append("\n## 🟡 知识弱项 (实体数较少的领域，建议补充)")
            for c in weak:
                lines.append(f"  - {c['name']}: 仅 {c['count']} 个实体 (最后更新 {c['last_updated_days']} 天前)")

        # 老旧领域（30 天以上未更新）
        stale = [c for c in coverage_sorted if c["last_updated_days"] > 30]
        if stale:
            lines.append("\n## 🔴 老旧领域 (超过 30 天未更新)")
            for c in stale:
                lines.append(f"  - {c['name']}: {c['count']} 个实体，{c['last_updated_days']} 天未更新")

        if not weak and not stale:
            lines.append("\n✅ 知识库覆盖良好，各领域实体分布较为均衡。")

        lines.append("\n💡 建议：可以在 ChatStudio 中点击「📊 知识体检」按钮查看可视化矩形树图。")

        return "\n".join(lines)

    except Exception as e:
        logger.error(f"覆盖分析失败: {e}")
        return f"覆盖分析出错: {e}"
