"""
图检索器 - Phase 1 GraphRAG 多跳检索

将用户查询映射到知识图谱中的实体，沿关系路径进行多跳遍历，
收集遍历路径上的实体和关系信息作为 LLM 的结构化上下文。

与 hybrid_search.py 配合使用：图检索结果通过 RRF 与向量/BM25 结果融合。
"""
import logging
from typing import List, Optional, Set, Tuple
from dataclasses import dataclass, field
from collections import deque

from sqlalchemy import select, and_, or_, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import config
from app.models.graph_entity import GraphEntity
from app.services.graph_service import GraphService

logger = logging.getLogger(__name__)

# ── jieba 可用性检查（带降级机制）──────────────────────────────
_jieba_available = False
try:
    import jieba
    # 预热测试
    list(jieba.cut("测试分词"))
    _jieba_available = True
except Exception:
    logger.warning("jieba 不可用，图检索将使用字符级关键词提取")


def _tokenize_query(text: str) -> list:
    """提取查询关键词（v4.0: 带 jieba 降级机制）"""
    if _jieba_available:
        try:
            tokens = list(jieba.cut(text))
            return [t.strip() for t in tokens if len(t.strip()) >= 2]
        except Exception as e:
            logger.warning(f"jieba 分词失败: {e}，回退到字符级关键词提取")

    # 回退：提取连续中文字符和英文单词作为关键词
    import re
    tokens = []
    for match in re.finditer(r'[一-鿿]{2,}|[a-zA-Z]{2,}|\d+', text):
        tokens.append(match.group())
    return tokens


@dataclass
class GraphRetrievalResult:
    """图检索结果"""
    entity_id: str
    entity_name: str
    entity_type: str
    score: float                          # 相关性分数
    traversal_path: List[str] = field(default_factory=list)      # 路径上的实体ID序列
    path_relations: List[str] = field(default_factory=list)       # 路径上的关系类型
    context_text: str = ""                 # 格式化后的文本上下文
    description: str = ""                  # 实体描述


class GraphRetriever:
    """
    多跳图检索器。

    检索流程：
    1. 从查询中提取关键词，在 graph_entities 表中定位种子实体
    2. 以种子实体为起点做 BFS/DFS 多跳遍历
    3. 收集遍历路径上的实体和关系
    4. 格式化为结构化上下文文本
    """

    def __init__(self):
        self._max_hops = config.GRAPH_TRAVERSAL_MAX_HOPS
        self._max_nodes = config.GRAPH_TRAVERSAL_MAX_NODES

    async def retrieve(
        self,
        query: str,
        kb_id: str,
        db: AsyncSession,
        top_k: int = 5,
    ) -> List[GraphRetrievalResult]:
        """
        主检索入口：从查询出发在图谱中检索相关信息。

        Args:
            query: 用户查询文本
            kb_id: 知识库ID
            db: 数据库会话
            top_k: 返回的最大结果数

        Returns:
            按分数降序排列的图检索结果列表
        """
        # Step 1: 定位种子实体
        seed_entities = await self._locate_seed_entities(query, kb_id, db)
        if not seed_entities:
            logger.debug(f"图检索: 未找到种子实体 kb={kb_id}")
            return []

        logger.debug(
            f"图检索: 找到 {len(seed_entities)} 个种子实体 "
            f"kb={kb_id}: {[e.name for e in seed_entities[:5]]}"
        )

        # Step 2: 加载 NetworkX 图
        G = await GraphService.load_networkx(db, kb_id)
        if G.number_of_nodes() == 0:
            return []

        # Step 3: 从种子实体出发做多跳遍历（使用 GraphService 统一 BFS）
        seed_ids = [e.id for e in seed_entities if e.id in G]
        traversal = GraphService.traverse_graph(G, seed_ids, self._max_hops, self._max_nodes)

        # Step 4: 构建结果
        results = self._build_results(G, seed_entities, traversal, query)

        # 按分数排序，截取 top_k
        results.sort(key=lambda r: r.score, reverse=True)
        return results[:top_k]

    # ---------- 种子实体定位 ----------

    async def _locate_seed_entities(
        self, query: str, kb_id: str, db: AsyncSession
    ) -> List[GraphEntity]:
        """
        从查询中提取关键词，在 graph_entities 中匹配种子实体。

        匹配策略：
        1. jieba 分词提取关键词（长度 >= 2）
        2. 对每个关键词在 DB 中做 LIKE 匹配
        3. 完全匹配 > 前缀匹配 > 子串匹配，按实体权重加权
        """
        # 提取关键词（v4.0: 带 jieba 降级机制）
        keywords = _tokenize_query(query)

        if not keywords:
            return []

        # 对每个关键词做 DB 查询
        all_matches: List[Tuple[GraphEntity, float]] = []
        seen_ids: Set[str] = set()

        for kw in keywords:
            # 先精确匹配
            exact_stmt = select(GraphEntity).where(
                and_(GraphEntity.kb_id == kb_id, GraphEntity.name == kw)
            )
            exact_result = await db.execute(exact_stmt)
            for entity in exact_result.scalars():
                if entity.id not in seen_ids:
                    all_matches.append((entity, 1.0 * (entity.weight or 0.5)))
                    seen_ids.add(entity.id)

            # 再 LIKE 模糊匹配
            like_stmt = select(GraphEntity).where(
                and_(
                    GraphEntity.kb_id == kb_id,
                    GraphEntity.name.contains(kw),
                    GraphEntity.name != kw,  # 排除已精确匹配的
                )
            ).limit(10)
            like_result = await db.execute(like_stmt)
            for entity in like_result.scalars():
                if entity.id not in seen_ids:
                    # 前缀匹配比子串匹配得分更高
                    if entity.name.startswith(kw):
                        score = 0.8 * (entity.weight or 0.5)
                    else:
                        score = 0.5 * (entity.weight or 0.5)
                    all_matches.append((entity, score))
                    seen_ids.add(entity.id)

        # 按得分排序，去重
        all_matches.sort(key=lambda x: x[1], reverse=True)
        return [e for e, _ in all_matches[:10]]  # 最多 10 个种子

    # ---------- 结果构建 ----------

    def _build_results(
        self,
        G,
        seed_entities: List[GraphEntity],
        traversal: dict,
        query: str,
    ) -> List[GraphRetrievalResult]:
        """将遍历结果构建为 GraphRetrievalResult 列表"""
        results = []
        seed_ids = {e.id for e in seed_entities}
        visited = traversal["visited_nodes"]
        paths = traversal["paths"]

        for node_id in visited:
            if node_id in G:
                node_data = G.nodes[node_id]
                # 计算分数：种子实体分数高，距离种子越近分数越高
                is_seed = node_id in seed_ids
                path_len = len(paths.get(node_id, [node_id])) - 1

                if is_seed:
                    # 种子实体：使用匹配分数
                    seed = next((e for e in seed_entities if e.id == node_id), None)
                    base_score = seed.weight if seed else 0.5
                    score = base_score
                else:
                    # 非种子：距离衰减
                    node_weight = node_data.get("weight", 0.5)
                    score = node_weight * (1.0 / (1.0 + path_len))

                # 构建上下文文本
                context = self._build_entity_context(node_data, G, node_id, paths)

                results.append(GraphRetrievalResult(
                    entity_id=node_id,
                    entity_name=node_data.get("name", ""),
                    entity_type=node_data.get("entity_type", ""),
                    score=round(score, 4),
                    traversal_path=paths.get(node_id, [node_id]),
                    path_relations=self._extract_path_relations(G, paths.get(node_id, [])),
                    context_text=context,
                    description=node_data.get("description", ""),
                ))

        return results

    def _build_entity_context(
        self,
        node_data: dict,
        G,
        node_id: str,
        paths: dict,
    ) -> str:
        """为单个实体构建上下文描述"""
        name = node_data.get("name", "")
        etype = node_data.get("entity_type", "")
        desc = node_data.get("description", "")
        path = paths.get(node_id, [node_id])

        lines = [f"实体: {name} (类型: {etype})"]
        if desc:
            lines.append(f"描述: {desc}")

        # 路径信息
        if len(path) > 1:
            path_names = [G.nodes[pid].get("name", pid) for pid in path if pid in G]
            lines.append(f"关联路径: {' → '.join(path_names)}")

        # 直接邻居摘要
        neighbors_out = list(G.successors(node_id))[:3]
        neighbors_in = list(G.predecessors(node_id))[:3]
        if neighbors_out:
            n_names = [G.nodes[n].get("name", n) for n in neighbors_out if n in G]
            if n_names:
                lines.append(f"关联实体: {', '.join(n_names)}")
        if neighbors_in:
            n_names = [G.nodes[n].get("name", n) for n in neighbors_in if n in G]
            if n_names:
                lines.append(f"被关联: {', '.join(n_names)}")

        return "\n".join(lines)

    def _extract_path_relations(
        self, G, path: List[str]
    ) -> List[str]:
        """提取路径上的关系类型序列"""
        relations = []
        for i in range(len(path) - 1):
            edge = G.get_edge_data(path[i], path[i + 1])
            if edge:
                relations.append(edge.get("relation_type", "关联"))
            else:
                # 可能反向
                edge = G.get_edge_data(path[i + 1], path[i])
                if edge:
                    relations.append(edge.get("relation_type", "关联"))
                else:
                    relations.append("关联")
        return relations

    # ---------- 便捷方法 ----------

    async def get_entity_context(
        self,
        entity_id: str,
        kb_id: str,
        db: AsyncSession,
        hops: int = 1,
    ) -> Optional[dict]:
        """获取实体及其邻居上下文（用于 API）"""
        return await GraphService.get_neighbors(db, entity_id, kb_id, hops)
