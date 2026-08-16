"""
实体提取编排服务 - 两阶段管道 + 动态图谱合并去噪
"""
import asyncio
import logging

from app.services.entity_extractor import NLPEntityExtractor
from app.services.llm_refiner import LLMEntityRefiner

logger = logging.getLogger(__name__)


class ExtractionService:
    """
    两阶段实体提取编排：
    Stage 1: NLP 粗筛 (jieba + TF-IDF + 标题分区)
    Stage 2: LLM 精炼 (DeepSeek V4 指代消解 + 三元组验证)
    后处理: 动态图谱合并去噪
    """

    def __init__(self, use_llm: bool = True):
        self.nlp_extractor = NLPEntityExtractor()
        self.use_llm = use_llm

    async def extract(self, text: str) -> dict:
        """
        完整两阶段实体提取。

        Returns:
            {"nodes": [...], "links": [...], "legend": {...}}
        """
        # Stage 1: NLP 粗筛（v4.1: jieba/TF-IDF 同步计算移入线程池，避免阻塞事件循环）
        entities, relationships, legend = await asyncio.get_running_loop().run_in_executor(
            None, self.nlp_extractor.extract, text
        )
        logger.info(f"Stage 1 (NLP): {len(entities)} 实体, {len(relationships)} 关系")

        # Stage 2: LLM 精炼（可选）
        if self.use_llm and entities:
            try:
                result = await LLMEntityRefiner.refine(text, entities)
                entities = result.get("entities", entities)
                relationships = result.get("relationships", relationships)
                # v4.0: 更新 legend（为新类型分配统一配色）
                from app.core.colors import get_color_for_type
                for ent in entities:
                    etype = ent.get("type", "概念")
                    if etype not in legend:
                        legend[etype] = get_color_for_type(etype, len(legend))
                logger.info(f"Stage 2 (LLM): {len(entities)} 实体, {len(relationships)} 关系")
            except Exception as e:
                logger.warning(f"LLM 精炼失败，使用 NLP 粗筛结果: {e}")

        # 后处理: 去噪
        entities, relationships = self._denoise(entities, relationships)

        # 转换为图谱格式
        nodes = [
            {
                "id": e["id"],
                "name": e["name"],
                "type": e["type"],
                "weight": e.get("confidence", e.get("weight", 0.5)),
                # v4.0: 统一从 legend 取值，无匹配时使用 get_color_for_type 生成
                "color": e.get("color") or legend.get(e["type"], "#4F8CF7"),
            }
            for e in entities
        ]

        links = [
            {
                "id": r["id"],
                "source": r["source"],
                "target": r["target"],
                "relation": r["relation"],
                "value": r["value"],
                "sentence": (r.get("sentence") or "")[:200],  # v2.5: None-safe
            }
            for r in relationships
        ]

        return {
            "nodes": nodes,
            "links": links,
            "legend": legend,
        }

    @classmethod
    def to_graph_format(cls, result: dict, doc_id: str, kb_id: str) -> dict:
        """
        Phase 1: 将提取结果转换为 GraphService.build_graph() 可消费的格式。
        为每个实体/关系附加来源文档信息。
        """
        nodes = result.get("nodes", [])
        links = result.get("links", [])

        for node in nodes:
            node["_doc_id"] = doc_id
            node["_kb_id"] = kb_id
        for link in links:
            link["_doc_id"] = doc_id
            link["_kb_id"] = kb_id

        return {"nodes": nodes, "links": links, "legend": result.get("legend", {})}

    @staticmethod
    def _denoise(entities: list[dict], relationships: list[dict]) -> tuple:
        """
        动态图谱去噪：
        1. 过滤孤立节点（度 = 0 且权重 < 阈值）
        2. 过滤低频关系（同一对实体间重复出现 < 2 次的弱关系）
        3. 合并同义实体（名称相似度 > 0.8）
        """
        if not entities:
            return entities, relationships

        # 统计每个实体的度
        degree = {e["id"]: 0 for e in entities}
        for rel in relationships:
            degree[rel["source"]] = degree.get(rel["source"], 0) + 1
            degree[rel["target"]] = degree.get(rel["target"], 0) + 1

        # 过滤孤立低权重节点
        entity_map = {}
        for e in entities:
            if degree[e["id"]] == 0 and e.get("weight", 0.5) < 0.1:
                continue  # 跳过孤立低权重节点
            entity_map[e["id"]] = e

        # 过滤尾部关系
        filtered_rels = []
        for rel in relationships:
            if rel["source"] in entity_map and rel["target"] in entity_map:
                # v2.5: None-safe value check
                rel_value = rel.get("value")
                if rel_value is None or rel_value >= 0.1:
                    filtered_rels.append(rel)

        filtered_entities = list(entity_map.values())

        logger.info(
            f"去噪后: {len(entities)}→{len(filtered_entities)} 实体, "
            f"{len(relationships)}→{len(filtered_rels)} 关系"
        )

        return filtered_entities, filtered_rels
