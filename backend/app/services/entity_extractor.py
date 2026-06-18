"""
第一阶段：NLP 粗筛实体提取器
- jieba 分词 + POS 词性标注（修复版）
- TF-IDF 关键字权重计算
- 基于 Markdown 标题的实体分类
- 停用词过滤 + 共现关系提取
"""
import re
import logging
from typing import List, Dict, Tuple, Optional
from collections import Counter

from app.core.colors import get_color_for_type

logger = logging.getLogger(__name__)

# 停用词表（中英文）
STOP_WORDS = set([
    '的', '了', '和', '是', '就', '都', '而', '及', '与', '着', '或',
    '一个', '没有', '我们', '你们', '他们', '她', '他', '它', '这', '那',
    '在', '有', '被', '对', '等', '能', '也', '会', '可', '到', '以', '为',
    'the', 'a', 'an', 'is', 'are', 'was', 'were', 'be', 'been', 'being',
    'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could',
    'should', 'may', 'might', 'can', 'shall', 'to', 'of', 'in', 'for',
    'on', 'with', 'at', 'by', 'from', 'as', 'into', 'through', 'during',
    'before', 'after', 'above', 'below', 'between', 'under', 'again',
])

# 中文词性 → 实体类型映射
POS_TO_ENTITY_TYPE: Dict[str, str] = {
    'nr': '人物',      # 人名
    'ns': '地点',      # 地名
    'nt': '机构',      # 机构团体
    'nz': '概念',      # 其他专名
    'n': '概念',       # 名词 → 概念
    'vn': '概念',      # 动名词
    'eng': '概念',     # 英文
    't': '时间',       # 时间词
    'm': '方法',       # 数词 → 可能表示公式/方法
}

# 关系匹配模式
RELATION_PATTERNS = {
    '包含': [r'包含|包括|涵盖|分为|由.*组成'],
    '因果': [r'导致|引起|造成|使得|因为|由于|所以|因此|从而'],
    '前提': [r'前提|基础|必要条件|依赖于|建立在'],
    '应用': [r'应用|运用|用于|用来|使用|采用'],
    '对比': [r'相反|对立|差异|区别于|不同于|与.*不同|比较|对比|相比'],
    '发展': [r'发展|演变|进化|演化为|转变|逐步|演变为'],
    '例证': [r'例如|比如|举例|典型|实例|代表性|如'],
    '关联': [r'关联|相关|有关|联系|涉及|关系'],
}


class NLPEntityExtractor:
    """
    第一阶段 NLP 粗筛实体提取器。
    基于 jieba + TF-IDF + 标题分区，不依赖 LLM。

    修复：
    - 修复了死代码 POS 标注逻辑
    - 修复了 jieba 分词空输入崩溃问题
    - 使用 jieba.posseg 进行词性标注 + 实体类型推导
    """

    def __init__(self):
        self.entity_colors: Dict[str, str] = {}
        self.color_index = 0
        self._ensure_jieba_initialized()

    @staticmethod
    def _ensure_jieba_initialized():
        """确保 jieba 已初始化"""
        try:
            import jieba
            import jieba.posseg as pseg
            # 预热：触发词典加载
            list(jieba.cut("初始化"))
            list(pseg.cut("初始化"))
        except Exception as e:
            logger.warning(f"jieba 初始化警告: {e}")

    def _get_color_for_type(self, entity_type: str) -> str:
        """为实体类型分配一致的颜色（使用统一配色模块）"""
        if entity_type not in self.entity_colors:
            color = get_color_for_type(entity_type, self.color_index)
            self.entity_colors[entity_type] = color
            self.color_index += 1
        return self.entity_colors[entity_type]

    def extract(self, text: str) -> Tuple[List[dict], List[dict], Dict[str, str]]:
        """
        从文本中提取实体和关系。

        Returns:
            (entities, relationships, legend)
        """
        if not text or not text.strip():
            return [], [], {}

        # 1. 按 Markdown 标题分块
        blocks = self._split_by_headers(text)

        # 2. 每块提取 TF-IDF 关键词作为候选实体
        entities, entity_names, processed_sentences = self._extract_from_blocks(blocks)

        # 3. 基于共现和模式匹配提取关系
        relationships = self._extract_relationships(entities, processed_sentences)

        # 4. 优化去噪
        entities, relationships = self.optimize(entities, relationships)

        return entities, relationships, self.entity_colors

    # ─── 分块 ─────────────────────────────────────────────────────

    def _split_by_headers(self, text: str) -> List[Tuple[str, str]]:
        """按 Markdown 标题分块，标题作为实体类型"""
        lines = text.split('\n')
        blocks = []
        current_title = "通用概念"
        current_content = []

        for line in lines:
            title_match = re.match(r'^(#{1,6})\s+(.+)$', line.strip())
            if title_match:
                if current_content:
                    blocks.append((current_title, '\n'.join(current_content)))

                raw_title = title_match.group(2).strip()
                # 过滤编号前缀
                clean_title = re.sub(
                    r'^[\d\.、一二三四五六七八九十①②③④⑤⑥⑦⑧⑨⑩]+', '', raw_title
                ).strip()
                if not clean_title:
                    clean_title = raw_title
                if len(clean_title) > 15:
                    clean_title = clean_title[:15]

                current_title = clean_title
                current_content = []
            else:
                current_content.append(line)

        if current_content:
            blocks.append((current_title, '\n'.join(current_content)))

        return blocks

    # ─── 实体提取（修复版）─────────────────────────────────────────

    def _extract_from_blocks(
        self, blocks: List[Tuple[str, str]]
    ) -> Tuple[List[dict], set, List[Tuple[str, List[str]]]]:
        """
        从每个块提取 TF-IDF 关键词作为实体。

        修复：
        - 使用 jieba.posseg 进行词性标注并推导实体类型
        - 修复了原有死代码（空循环 + pass）
        - 空内容不去调用 jieba.analyse.extract_tags（避免崩溃）
        """
        import jieba
        import jieba.analyse
        import jieba.posseg as pseg

        entities = []
        entity_names = set()
        entity_id = 0
        processed_sentences = []

        # 按实体名称追踪最优 POS（用于类型推导）
        entity_pos_best: Dict[str, Tuple[str, int]] = {}

        for title, content in blocks:
            # 分句
            sentences = re.split(r'[。！？.!?\n]+', content)
            sentences = [s.strip() for s in sentences if s.strip()]
            if not sentences:
                continue

            block_words: List[str] = []
            for sentence in sentences:
                # jieba 分词（含词性标注）
                try:
                    words_with_pos = [(w.word, w.flag) for w in pseg.cut(sentence)]
                except Exception:
                    # pseg 失败时回退到基本分词
                    try:
                        words_with_pos = [(w, 'x') for w in jieba.cut(sentence)]
                    except Exception:
                        continue

                valid_words = [
                    (w, pos) for w, pos in words_with_pos
                    if len(w.strip()) > 1
                    and w not in STOP_WORDS
                    and not w.isdigit()
                    and not re.match(r'^[^一-鿿_a-zA-Z]+$', w)
                ]
                if valid_words:
                    words_only = [w for w, _ in valid_words]
                    processed_sentences.append((sentence, words_only))
                    block_words.extend(words_only)

                    # 统计每个词的词性出现频次
                    for w, pos in valid_words:
                        if w not in entity_pos_best:
                            entity_pos_best[w] = (pos, 1)
                        else:
                            prev_pos, count = entity_pos_best[w]
                            if pos == prev_pos:
                                entity_pos_best[w] = (pos, count + 1)
                            elif count > 1:
                                entity_pos_best[w] = (prev_pos, count - 1)
                            else:
                                # 用新词性替换（更常见）
                                entity_pos_best[w] = (pos, 1)

            if not block_words:
                continue

            # TF-IDF 关键词提取（需要确保输入非空）
            block_text = ' '.join(block_words)
            if not block_text.strip():
                continue

            try:
                keywords = jieba.analyse.extract_tags(
                    block_text, topK=20, withWeight=True
                )
            except Exception as e:
                logger.warning(f"TF-IDF 提取失败: {e}")
                keywords = [(w, 1.0) for w in set(block_words)]

            for keyword, weight in keywords:
                if keyword in entity_names:
                    continue

                # 根据词性推导实体类型
                best_pos = entity_pos_best.get(keyword, ('n', 1))[0]
                entity_type = POS_TO_ENTITY_TYPE.get(best_pos, title)

                color = self._get_color_for_type(entity_type)

                entities.append({
                    "id": str(entity_id),
                    "name": keyword,
                    "type": entity_type,
                    "weight": round(weight, 4),
                    "color": color,
                    "pos": best_pos,
                })
                entity_names.add(keyword)
                entity_id += 1

        return entities, entity_names, processed_sentences

    # ─── 关系提取 ─────────────────────────────────────────────────

    def _extract_relationships(
        self, entities: List[dict], processed_sentences: List[Tuple[str, List[str]]]
    ) -> List[dict]:
        """基于共现和模式匹配提取关系"""
        relationships = []
        relationship_id = 0
        entity_map = {e["name"]: e["id"] for e in entities}

        # 用于合并重复边
        edge_map: Dict[Tuple[str, str], dict] = {}

        for sentence, words in processed_sentences:
            sentence_entities = [w for w in words if w in entity_map]
            if len(sentence_entities) < 2:
                continue

            for i in range(len(sentence_entities)):
                for j in range(i + 1, len(sentence_entities)):
                    source = entity_map[sentence_entities[i]]
                    target = entity_map[sentence_entities[j]]
                    if source == target:
                        continue

                    # 距离加权
                    distance = abs(i - j)
                    weight = 1.0 / (distance + 1)

                    # 关系类型识别
                    relation_type = self._identify_relation_type(sentence)

                    # 合并重复边
                    edge_key = (min(source, target), max(source, target))
                    if edge_key in edge_map:
                        edge_map[edge_key]["value"] += weight
                    else:
                        edge_map[edge_key] = {
                            "id": str(relationship_id),
                            "source": source,
                            "target": target,
                            "relation": relation_type,
                            "value": round(weight, 4),
                            "sentence": sentence[:100],
                        }
                        relationship_id += 1

        return list(edge_map.values())

    @staticmethod
    def _identify_relation_type(context: str) -> str:
        """根据上下文模式识别关系类型"""
        for relation_type, patterns in RELATION_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, context):
                    return relation_type
        return "关联"

    # ─── 优化去噪 ─────────────────────────────────────────────────

    def optimize(
        self, entities: List[dict], relationships: List[dict]
    ) -> Tuple[List[dict], List[dict]]:
        """
        去噪优化 (v2.4: O(n+m) 替代 O(n*m))：
        - 过滤低权重实体
        - 限制实体/关系数量
        - 重新索引 ID
        """
        from app.core.config import config

        if not entities:
            return [], []

        # 过滤低权重实体
        threshold = config.ENTITY_WEIGHT_THRESHOLD
        filtered_entities = [e for e in entities if e["weight"] > threshold]

        # 限制数量
        max_entities = config.MAX_ENTITIES
        if len(filtered_entities) > max_entities:
            filtered_entities = sorted(
                filtered_entities, key=lambda x: x["weight"], reverse=True
            )[:max_entities]

        # v2.4: 构建 id→name 和 name→id 映射 (O(n) 替代 O(n*m))
        orig_id_to_name = {e["id"]: e["name"] for e in entities}
        entity_name_to_id = {e["name"]: e["id"] for e in filtered_entities}

        # 过滤关系：使用 dict 查找 (O(1) 替代 O(n))
        filtered_relationships = []
        for rel in relationships:
            src_name = orig_id_to_name.get(rel["source"])
            tgt_name = orig_id_to_name.get(rel["target"])
            if src_name and tgt_name and src_name in entity_name_to_id and tgt_name in entity_name_to_id:
                rel["source"] = entity_name_to_id[src_name]
                rel["target"] = entity_name_to_id[tgt_name]
                filtered_relationships.append(rel)

        # 限制关系数量
        max_rels = config.MAX_RELATIONSHIPS
        if len(filtered_relationships) > max_rels:
            filtered_relationships = sorted(
                filtered_relationships, key=lambda x: x["value"], reverse=True
            )[:max_rels]

        # 重新索引 ID (v2.4: 单次遍历 + dict 查找)
        optimized_entities = []
        new_name_to_id = {}
        for i, entity in enumerate(filtered_entities):
            new_id = str(i + 1)
            new_name_to_id[entity["name"]] = new_id
            optimized_entities.append({
                "id": new_id,
                "name": entity["name"],
                "type": entity["type"],
                "weight": entity["weight"],
                "color": entity["color"],
                "pos": entity.get("pos", "n"),
            })

        # v2.4: 用映射表重定向 source/target
        new_id_to_name = {e["id"]: e["name"] for e in filtered_entities}
        optimized_relationships = []
        for i, rel in enumerate(filtered_relationships):
            source_name = new_id_to_name.get(rel["source"])
            target_name = new_id_to_name.get(rel["target"])
            if source_name and target_name:
                optimized_relationships.append({
                    "id": str(i + 1),
                    "source": new_name_to_id[source_name],
                    "target": new_name_to_id[target_name],
                    "relation": rel["relation"],
                    "value": rel["value"],
                    "sentence": rel.get("sentence", ""),
                })

        logger.info(
            f"图谱优化: {len(entities)}→{len(optimized_entities)} 实体, "
            f"{len(relationships)}→{len(optimized_relationships)} 关系"
        )
        return optimized_entities, optimized_relationships
