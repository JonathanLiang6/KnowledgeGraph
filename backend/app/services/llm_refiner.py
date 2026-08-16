"""
第二阶段：LLM 精炼与对齐
- 指代消解 (Coreference Resolution)
- 三元组验证 (Entity-Relation-Entity)
- 置信度打分
"""
import difflib
import logging

from app.core.config import config
from app.services.deepseek_client import DeepSeekClient

logger = logging.getLogger(__name__)


def _bigrams(s: str) -> set:
    """返回字符串的字符 bigram 集合（长度 < 2 时为空集）"""
    return {s[i:i + 2] for i in range(len(s) - 1)} if len(s) >= 2 else set()


def compute_name_similarity(a: str, b: str) -> float:
    """
    v4.1 (#57): 计算两个实体名称的混合相似度（模块级纯函数，便于测试）。

    取两者的最大值:
    - 字符 bigram Jaccard: 对中文友好（"机器学习" vs "机器学习算法" 共享 "机器/器学/学习"）
    - difflib.SequenceMatcher.ratio(): 对编辑距离敏感（增删字符的小改动）

    返回 [0, 1]；任一为空字符串时返回 0（无有效字符可比）。
    """
    if not a or not b:
        return 0.0
    a_bi, b_bi = _bigrams(a), _bigrams(b)
    if a_bi or b_bi:
        union = a_bi | b_bi
        bigram_jaccard = len(a_bi & b_bi) / len(union) if union else 0.0
    else:
        bigram_jaccard = 0.0
    ratio = difflib.SequenceMatcher(None, a, b).ratio()
    return max(bigram_jaccard, ratio)


class LLMEntityRefiner:
    """使用 DeepSeek V4 对 NLP 粗筛结果进行精炼"""

    # v4.1 (#57): 模糊匹配阈值改为运行时读取全局配置（默认 0.85），
    # 与 GraphRAG 实体消歧共用 GRAPH_ENTITY_RESOLUTION_THRESHOLD，删除硬编码 0.75

    @classmethod
    async def refine(
        cls,
        text: str,
        candidates: list[dict],
        max_candidates: int = 30,
    ) -> dict:
        """
        精炼实体提取结果。

        Args:
            text: 原文内容
            candidates: NLP 粗筛的候选实体
            max_candidates: 最大送入 LLM 的候选实体数

        Returns:
            {"entities": [...], "relationships": [...]}
        """
        result = await DeepSeekClient.extract_entities(
            text=text,
            candidate_entities=candidates[:max_candidates],
        )

        # 合并 NLP 和 LLM 结果
        merged = cls._merge_results(candidates, result)
        return merged

    @classmethod
    def _format_candidates(cls, candidates: list[dict]) -> str:
        """格式化候选实体列表"""
        lines = []
        for ent in candidates:
            lines.append(
                f"- {ent['name']} | 类型: {ent.get('type', '未知')} | "
                f"权重: {ent.get('weight', 0):.3f}"
            )
        return '\n'.join(lines)

    @classmethod
    def _find_best_match(cls, name: str, candidates: dict, threshold: float = None) -> str | None:
        """
        v4.0: 模糊匹配实体名。先精确匹配，再使用混合相似度模糊匹配。
        解决 LLM 微调实体名（如 "机器学习"→"机器学习算法"）后的对不齐问题。

        v4.1 (#57): 相似度改用 compute_name_similarity（bigram Jaccard + SequenceMatcher），
        阈值运行时读取 config.GRAPH_ENTITY_RESOLUTION_THRESHOLD（默认 0.85）。
        """
        if threshold is None:
            threshold = config.GRAPH_ENTITY_RESOLUTION_THRESHOLD

        # 精确匹配
        if name in candidates:
            return name

        # 模糊匹配：混合相似度（对中文与编辑距离均友好）
        best_key = None
        best_sim = 0.0
        for key in candidates:
            sim = compute_name_similarity(name, key)
            if sim > best_sim and sim >= threshold:
                best_sim = sim
                best_key = key
        return best_key

    @classmethod
    def _merge_results(cls, nlp_candidates: list[dict], llm_result: dict) -> dict:
        """
        合并 NLP 粗筛和 LLM 精炼结果：
        - LLM 确认的实体保留并更新描述和置信度
        - NLP 独有但 LLM 未提及的低权重实体保留（防漏）
        - LLM 新增的实体直接加入
        """
        llm_entities = llm_result.get("entities", [])
        llm_relationships = llm_result.get("relationships", [])

        # 构建 LLM 实体名集合
        llm_names = {e.get("name", "") for e in llm_entities}

        # 合并实体（v4.0: 使用模糊匹配处理 LLM 微调后的实体名）
        merged_entities = {}
        used_llm_names = set()
        for ent in nlp_candidates:
            name = ent["name"]
            # v4.0: 先精确再模糊匹配
            matched_name = cls._find_best_match(name, dict.fromkeys(llm_names, True))
            if matched_name:
                # LLM 确认：更新
                llm_ent = next(e for e in llm_entities if e.get("name") == matched_name)
                used_llm_names.add(matched_name)
                merged_entities[name] = {
                    **ent,
                    "description": llm_ent.get("description", ""),
                    "confidence": llm_ent.get("confidence", ent.get("weight", 0.5)),
                    "source": "nlp+llm",
                }
            else:
                # LLM 未提及但 NLP 发现：保留（降低置信度）
                merged_entities[name] = {
                    **ent,
                    "description": "",
                    "confidence": ent.get("weight", 0.3) * 0.5,
                    "source": "nlp_only",
                }

        # 加入 LLM 新增实体
        color_idx = len(merged_entities)
        for llm_ent in llm_entities:
            name = llm_ent.get("name", "")
            if name in used_llm_names:
                continue
            # v4.0: 检查是否与已有实体模糊匹配（LLM 改名的情况）
            matched_existing = cls._find_best_match(name, dict.fromkeys(merged_entities, True))
            if matched_existing:
                # LLM 改名了但 NLP 有类似实体：合并描述
                existing = merged_entities[matched_existing]
                if llm_ent.get("description"):
                    existing["description"] = llm_ent.get("description", "")
                existing["source"] = "nlp+llm"
            else:
                merged_entities[name] = {
                    "id": str(color_idx + 1),
                    "name": name,
                    "type": llm_ent.get("type", "概念"),
                    "weight": llm_ent.get("confidence", 0.5),
                    "description": llm_ent.get("description", ""),
                    "confidence": llm_ent.get("confidence", 0.5),
                    "source": "llm_only",
                    "color": "#4F8CF7",  # 默认颜色
                    "pos": "n",
                }
                color_idx += 1

        # 重新索引
        entities = []
        for i, (name, ent) in enumerate(merged_entities.items()):
            entities.append({**ent, "id": str(i + 1)})

        # 构建 name → id 映射
        name_to_id = {e["name"]: e["id"] for e in entities}

        # 处理关系
        relationships = []
        rel_id = 1
        for rel in llm_relationships:
            source = rel.get("source", "")
            target = rel.get("target", "")
            if source in name_to_id and target in name_to_id:
                relationships.append({
                    "id": str(rel_id),
                    "source": name_to_id[source],
                    "target": name_to_id[target],
                    "relation": rel.get("relation", "关联"),
                    "value": rel.get("confidence", 0.5),
                    "sentence": rel.get("description", ""),
                    "source_type": "llm",
                })
                rel_id += 1

        logger.info(
            f"合并结果: NLP {len(nlp_candidates)} → 合并 {len(entities)} 实体, "
            f"{len(relationships)} 关系"
        )

        return {
            "entities": entities,
            "relationships": relationships,
        }
