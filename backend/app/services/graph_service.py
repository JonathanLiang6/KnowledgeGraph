"""
图服务 - Phase 1 GraphRAG 核心

提供图谱的构建、查询、遍历、社区检测、实体对齐等所有图操作。
使用 NetworkX 进行内存图计算，SQLAlchemy 模型进行持久化。

架构：
- 写入路径: build_graph() → GraphEntity/GraphRelation 表 + 使 NetworkX 缓存失效
- 读取路径: load_networkx() → NetworkX 内存图（模块级 LRU 缓存）
- 算法: Louvain 社区检测、BFS/DFS 遍历、最短路径
"""
import logging
import asyncio
from collections import defaultdict, deque
from typing import Optional, List, Dict, Any, Tuple
from dataclasses import dataclass, field

import networkx as nx
from sqlalchemy import select, func, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import config
from app.models.graph_entity import GraphEntity, GraphRelation

logger = logging.getLogger(__name__)

# ============================================================
# 模块级 NetworkX 缓存
# ============================================================
# key: kb_id, value: (nx.DiGraph, version_counter)
_nx_cache: Dict[str, Tuple[nx.DiGraph, int]] = {}
_nx_cache_lock = asyncio.Lock()
# 每个 kb_id 的版本号，写操作时递增
_kb_versions: Dict[str, int] = defaultdict(int)
# 每个 kb_id 的写锁，防止并发写入产生重复实体
_kb_write_locks: Dict[str, asyncio.Lock] = {}


def _get_kb_write_lock(kb_id: str) -> asyncio.Lock:
    """获取指定 KB 的写锁（懒创建）"""
    if kb_id not in _kb_write_locks:
        _kb_write_locks[kb_id] = asyncio.Lock()
    return _kb_write_locks[kb_id]


# ============================================================
# 数据类
# ============================================================

@dataclass
class CommunityInfo:
    """社区信息"""
    id: str
    label: str = ""
    node_ids: List[str] = field(default_factory=list)
    node_count: int = 0
    top_entities: List[dict] = field(default_factory=list)
    description: str = ""


# ============================================================
# GraphService
# ============================================================

class GraphService:
    """图操作服务 - 所有方法均为 classmethod，无状态"""

    # ---------- 图构建与持久化 ----------

    @classmethod
    async def build_graph(
        cls,
        db: AsyncSession,
        kb_id: str,
        nodes: List[dict],
        links: List[dict],
        doc_id: str,
    ) -> Dict[str, int]:
        """
        从提取结果构建/更新图谱。

        对每个实体做实体对齐（同名同类型同KB → 合并），
        对每条关系查重后插入。
        批量预取已有实体避免 N+1 查询。

        Returns:
            {"entities_added": int, "entities_merged": int, "relations_added": int}
        """
        stats = {"entities_added": 0, "entities_merged": 0, "relations_added": 0}

        if not nodes:
            return stats

        lock = _get_kb_write_lock(kb_id)
        async with lock:
            # 批量预取该 KB 下所有已有实体（避免 N+1 查询）
            existing_stmt = select(GraphEntity).where(GraphEntity.kb_id == kb_id)
            existing_result = await db.execute(existing_stmt)
            existing_entities: Dict[Tuple[str, str], GraphEntity] = {}
            for e in existing_result.scalars():
                key = (e.name, e.entity_type)
                existing_entities[key] = e

            # Step 1: 实体对齐与持久化
            node_id_map: Dict[str, str] = {}  # 原始 node_id -> 数据库 entity.id
            for node in nodes:
                entity_id, is_new = await cls._resolve_entity(
                    db, kb_id, node, doc_id, existing_entities
                )
                node_id_map[node.get("id", "")] = entity_id
                if is_new:
                    stats["entities_added"] += 1
                else:
                    stats["entities_merged"] += 1

            # Step 2: 关系持久化
            existing_pairs = await cls._get_existing_relation_pairs(db, kb_id)
            for link in links:
                src_id = node_id_map.get(link.get("source", ""))
                tgt_id = node_id_map.get(link.get("target", ""))
                if not src_id or not tgt_id:
                    continue
                pair_key = (src_id, tgt_id, link.get("relation", "关联"))
                if pair_key in existing_pairs:
                    continue  # 跳过重复关系
                await cls._persist_relation(db, kb_id, src_id, tgt_id, link, doc_id)
                existing_pairs.add(pair_key)
                stats["relations_added"] += 1

            await db.commit()

            # Step 3: 使 NetworkX 缓存失效
            cls._invalidate_nx_cache(kb_id)

        logger.info(
            f"图谱构建完成 kb={kb_id}: "
            f"+{stats['entities_added']}实体 {stats['entities_merged']}合并 "
            f"+{stats['relations_added']}关系"
        )
        return stats

    @classmethod
    async def _resolve_entity(
        cls,
        db: AsyncSession,
        kb_id: str,
        node: dict,
        doc_id: str,
        existing_entities: Dict[Tuple[str, str], GraphEntity] = None,
    ) -> Tuple[str, bool]:
        """
        实体对齐：同名同类型同KB → 合并；否则新建。

        优先从 pre-fetched existing_entities 字典查找，避免 N+1 查询。

        Returns:
            (entity_id, is_new) — entity_id 为已存在或新建的实体ID，is_new 表示是否新建
        """
        name = (node.get("name") or "").strip()
        entity_type = node.get("type") or node.get("entity_type") or "概念"
        if not name:
            entity = GraphEntity(
                kb_id=kb_id, name=f"entity_{node.get('id', 'unknown')}",
                entity_type=entity_type,
                weight=node.get("weight", 0.5),
                color=node.get("color", "#4F8CF7"),
                description=node.get("description", ""),
                source_doc_ids=[{"doc_id": doc_id}],
            )
            db.add(entity)
            await db.flush()
            return entity.id, True

        # 优先从预取字典查找
        if existing_entities is not None:
            existing = existing_entities.get((name, entity_type))
        else:
            # 回退到单独查询
            stmt = select(GraphEntity).where(
                and_(
                    GraphEntity.kb_id == kb_id,
                    GraphEntity.name == name,
                    GraphEntity.entity_type == entity_type,
                )
            )
            result = await db.execute(stmt)
            existing = result.scalar_one_or_none()

        if existing:
            # 合并：取最大权重、追加来源、保留更长描述
            new_weight = node.get("weight", 0.5)
            if new_weight > (existing.weight or 0):
                existing.weight = new_weight
            new_desc = node.get("description", "")
            if len(new_desc) > len(existing.description or ""):
                existing.description = new_desc
            new_color = node.get("color")
            if new_color and new_color != "#4F8CF7":
                existing.color = new_color

            # 追加来源文档
            sources = list(existing.source_doc_ids or [])
            existing_doc_ids = {s.get("doc_id") for s in sources if s.get("doc_id")}
            if doc_id not in existing_doc_ids:
                sources.append({"doc_id": doc_id, "sentence": new_desc[:200]})
                existing.source_doc_ids = sources

            return existing.id, False
        else:
            # 新建实体
            entity = GraphEntity(
                kb_id=kb_id,
                name=name,
                entity_type=entity_type,
                weight=node.get("weight", 0.5),
                color=node.get("color", "#4F8CF7"),
                description=node.get("description", ""),
                source_doc_ids=[{"doc_id": doc_id}],
            )
            db.add(entity)
            await db.flush()
            # 更新预取字典以支持同一批次的后续匹配
            if existing_entities is not None:
                existing_entities[(name, entity_type)] = entity
            return entity.id, True

    @classmethod
    async def _persist_relation(
        cls, db: AsyncSession, kb_id: str,
        source_id: str, target_id: str,
        link: dict, doc_id: str,
    ) -> None:
        """持久化一条关系边"""
        relation = GraphRelation(
            kb_id=kb_id,
            source_id=source_id,
            target_id=target_id,
            relation_type=link.get("relation", "关联"),
            description=link.get("description", ""),
            weight=link.get("value") or link.get("weight", 0.5),
            sentence=(link.get("sentence") or "")[:500],
            source_doc_id=doc_id,
        )
        db.add(relation)

    @classmethod
    async def _get_existing_relation_pairs(
        cls, db: AsyncSession, kb_id: str
    ) -> set:
        """获取指定 KB 中已存在的 (source_id, target_id, relation_type) 集合"""
        stmt = select(
            GraphRelation.source_id,
            GraphRelation.target_id,
            GraphRelation.relation_type,
        ).where(GraphRelation.kb_id == kb_id)
        result = await db.execute(stmt)
        return {(r.source_id, r.target_id, r.relation_type) for r in result}

    # ---------- NetworkX 图加载 ----------

    @classmethod
    async def load_networkx(
        cls, db: AsyncSession, kb_id: str
    ) -> nx.DiGraph:
        """
        从数据库加载 NetworkX 有向图（带缓存）。

        节点属性: name, entity_type, weight, description, color
        边属性: relation_type, weight, sentence, source_doc_id
        """
        async with _nx_cache_lock:
            if kb_id in _nx_cache:
                cached_graph, cached_version = _nx_cache[kb_id]
                if cached_version == _kb_versions.get(kb_id, 0):
                    return cached_graph

        # 加载实体
        stmt = select(GraphEntity).where(GraphEntity.kb_id == kb_id)
        result = await db.execute(stmt)
        entities = result.scalars().all()

        # 加载关系
        rel_stmt = select(GraphRelation).where(GraphRelation.kb_id == kb_id)
        rel_result = await db.execute(rel_stmt)
        relations = rel_result.scalars().all()

        G = nx.DiGraph()
        for e in entities:
            G.add_node(
                e.id,
                name=e.name,
                entity_type=e.entity_type,
                weight=e.weight or 0.5,
                description=e.description or "",
                color=e.color or "#4F8CF7",
            )
        for r in relations:
            if G.has_node(r.source_id) and G.has_node(r.target_id):
                G.add_edge(
                    r.source_id, r.target_id,
                    relation_type=r.relation_type,
                    weight=r.weight or 0.5,
                    sentence=r.sentence or "",
                    source_doc_id=r.source_doc_id or "",
                    edge_id=r.id,
                )

        async with _nx_cache_lock:
            version = _kb_versions.get(kb_id, 0)
            _nx_cache[kb_id] = (G, version)

        logger.debug(f"NetworkX 图已加载 kb={kb_id}: {G.number_of_nodes()}节点 {G.number_of_edges()}边")
        return G

    @classmethod
    def _invalidate_nx_cache(cls, kb_id: str) -> None:
        """使指定 KB 的 NetworkX 缓存失效"""
        _kb_versions[kb_id] = _kb_versions.get(kb_id, 0) + 1
        _nx_cache.pop(kb_id, None)

    # ---------- 图遍历 ----------

    @classmethod
    def traverse_graph(
        cls,
        G: nx.DiGraph,
        seed_ids: List[str],
        max_hops: int = None,
        max_nodes: int = None,
    ) -> dict:
        """
        通用 BFS 图遍历 — graph_retriever 和 get_neighbors 共享使用。

        Args:
            G: NetworkX 有向图
            seed_ids: 种子节点 ID 列表
            max_hops: 最大跳数（默认从配置读取）
            max_nodes: 最大访问节点数（默认从配置读取）

        Returns:
            {
                "visited_nodes": set(node_id),
                "traversed_edges": [(source, target, edge_data)],
                "paths": {node_id: [path_from_seed]},
            }
        """
        if max_hops is None:
            max_hops = config.GRAPH_TRAVERSAL_MAX_HOPS
        if max_nodes is None:
            max_nodes = config.GRAPH_TRAVERSAL_MAX_NODES

        visited: set = set()
        edges: List[Tuple[str, str, dict]] = []
        paths: dict = {}  # entity_id -> path from nearest seed
        queue = deque()

        for seed_id in seed_ids:
            if seed_id in G:
                visited.add(seed_id)
                paths[seed_id] = [seed_id]
                queue.append((seed_id, 0))

        while queue and len(visited) < max_nodes:
            current, depth = queue.popleft()
            if depth >= max_hops:
                continue

            for neighbor in G.successors(current):
                if neighbor not in visited and len(visited) < max_nodes:
                    visited.add(neighbor)
                    edge_data = G.get_edge_data(current, neighbor) or {}
                    edges.append((current, neighbor, edge_data))
                    paths[neighbor] = paths.get(current, []) + [neighbor]
                    queue.append((neighbor, depth + 1))

            for neighbor in G.predecessors(current):
                if neighbor not in visited and len(visited) < max_nodes:
                    visited.add(neighbor)
                    edge_data = G.get_edge_data(neighbor, current) or {}
                    edges.append((neighbor, current, edge_data))
                    paths[neighbor] = paths.get(current, []) + [neighbor]
                    queue.append((neighbor, depth + 1))

        return {
            "visited_nodes": visited,
            "traversed_edges": edges,
            "paths": paths,
        }

    @classmethod
    async def get_neighbors(
        cls,
        db: AsyncSession,
        entity_id: str,
        kb_id: Optional[str] = None,
        hops: int = 1,
    ) -> Optional[dict]:
        """
        获取实体的邻居子图（BFS 展开）。

        Returns:
            {"entity": {...}, "neighbors": [...], "subgraph": {"nodes": [...], "edges": [...]}}
        """
        G = await cls.load_networkx(db, kb_id) if kb_id else None
        if G is None or entity_id not in G:
            return await cls._get_neighbors_from_db(db, entity_id, hops)

        # 使用通用 BFS 遍历
        traversal = cls.traverse_graph(G, [entity_id], max_hops=hops)
        visited = traversal["visited_nodes"]
        all_edges = traversal["traversed_edges"]

        # 构建邻居列表
        neighbors = []
        for src, tgt, edge_data in all_edges:
            neighbor_id = tgt if src == entity_id else src
            if neighbor_id in G:
                neighbors.append({
                    "id": neighbor_id,
                    "name": G.nodes[neighbor_id].get("name", ""),
                    "type": G.nodes[neighbor_id].get("entity_type", ""),
                    "relation": edge_data.get("relation_type", "关联"),
                    "color": G.nodes[neighbor_id].get("color", "#4F8CF7"),
                    "weight": G.nodes[neighbor_id].get("weight", 0.5),
                })

        # 构建子图
        subgraph_nodes = []
        subgraph_edges = []
        for nid in visited:
            node_data = G.nodes[nid]
            subgraph_nodes.append({
                "id": nid,
                "name": node_data.get("name", ""),
                "type": node_data.get("entity_type", ""),
                "weight": node_data.get("weight", 0.5),
                "color": node_data.get("color", "#4F8CF7"),
            })
        for u, v, data in G.edges(data=True):
            if u in visited and v in visited:
                subgraph_edges.append({
                    "id": data.get("edge_id", ""),
                    "source": u,
                    "target": v,
                    "relation": data.get("relation_type", "关联"),
                    "value": data.get("weight", 0.5),
                    "sentence": data.get("sentence", ""),
                })

        return {
            "entity": {
                "id": entity_id,
                "name": entity.get("name", ""),
                "type": entity.get("entity_type", ""),
                "description": entity.get("description", ""),
                "weight": entity.get("weight", 0.5),
                "color": entity.get("color", "#4F8CF7"),
            },
            "neighbors": neighbors,
            "subgraph_nodes": subgraph_nodes,
            "subgraph_edges": subgraph_edges,
        }

    @classmethod
    async def _get_neighbors_from_db(
        cls, db: AsyncSession, entity_id: str, hops: int = 1
    ) -> Optional[dict]:
        """退化方案：直接从 DB 查询实体及其邻居"""
        stmt = select(GraphEntity).where(GraphEntity.id == entity_id)
        result = await db.execute(stmt)
        entity = result.scalar_one_or_none()
        if not entity:
            return None

        # 查询关联关系
        rel_stmt = select(GraphRelation).where(
            and_(
                GraphRelation.kb_id == entity.kb_id,
                or_(
                    GraphRelation.source_id == entity_id,
                    GraphRelation.target_id == entity_id,
                ),
            )
        )
        rel_result = await db.execute(rel_stmt)
        relations = rel_result.scalars().all()

        neighbor_ids = set()
        neighbors = []
        for r in relations:
            neighbor_id = r.target_id if r.source_id == entity_id else r.source_id
            neighbor_ids.add(neighbor_id)
            # 暂存关系映射
            neighbors.append({
                "neighbor_id": neighbor_id,
                "relation": r.relation_type,
            })

        # 批量查询所有邻居实体（一次查询替代 N 次）
        if neighbor_ids:
            n_stmt = select(GraphEntity).where(GraphEntity.id.in_(neighbor_ids))
            n_result = await db.execute(n_stmt)
            neighbor_entities = {e.id: e for e in n_result.scalars()}
        else:
            neighbor_entities = {}

        # 组装结果
        resolved_neighbors = []
        for n in neighbors:
            n_entity = neighbor_entities.get(n["neighbor_id"])
            if n_entity:
                resolved_neighbors.append({
                    "id": n_entity.id,
                    "name": n_entity.name,
                    "type": n_entity.entity_type,
                    "relation": n["relation"],
                    "color": n_entity.color,
                    "weight": n_entity.weight or 0.5,
                })

        return {
            "entity": {
                "id": entity.id,
                "name": entity.name,
                "type": entity.entity_type,
                "description": entity.description or "",
                "weight": entity.weight or 0.5,
                "color": entity.color,
            },
            "neighbors": resolved_neighbors,
            "subgraph_nodes": [],
            "subgraph_edges": [],
        }

    # ---------- 路径查询 ----------

    @classmethod
    async def find_paths(
        cls,
        db: AsyncSession,
        source_id: str,
        target_id: str,
        kb_id: str,
        max_hops: int = 3,
    ) -> List[dict]:
        """查询两个实体之间的所有路径（最多 max_hops 跳）"""
        G = await cls.load_networkx(db, kb_id)
        if source_id not in G or target_id not in G:
            return []

        paths = []
        try:
            for path in nx.all_simple_paths(G, source_id, target_id, cutoff=max_hops):
                relations = []
                total_weight = 0.0
                for i in range(len(path) - 1):
                    edge = G.get_edge_data(path[i], path[i + 1]) or {}
                    relations.append(edge.get("relation_type", "关联"))
                    total_weight += edge.get("weight", 0.5)
                paths.append({
                    "path": path,
                    "relations": relations,
                    "length": len(path) - 1,
                    "total_weight": round(total_weight, 4),
                })
        except nx.NetworkXNoPath:
            pass

        # 按路径长度和总权重排序
        paths.sort(key=lambda p: (p["length"], -p["total_weight"]))
        return paths[:20]  # 最多返回 20 条路径

    # ---------- 社区检测 ----------

    @classmethod
    async def detect_communities(
        cls,
        db: AsyncSession,
        kb_id: str,
        min_size: Optional[int] = None,
    ) -> List[dict]:
        """
        Louvain 社区检测。

        Returns:
            [{"id": "community_0", "label": "...", "node_ids": [...],
              "node_count": N, "top_entities": [...]}]
        """
        if min_size is None:
            min_size = config.GRAPH_COMMUNITY_MIN_SIZE

        G = await cls.load_networkx(db, kb_id)
        if G.number_of_nodes() < min_size:
            return []

        # Louvain 需要无向图
        G_undirected = G.to_undirected()

        try:
            from community import best_partition  # python-louvain
            partition = best_partition(G_undirected)
        except ImportError:
            # 回退：使用 NetworkX 内置的 greedy_modularity_communities
            from networkx.algorithms.community import greedy_modularity_communities
            communities_nx = list(greedy_modularity_communities(G_undirected))
            partition = {}
            for i, comm in enumerate(communities_nx):
                for node in comm:
                    partition[node] = i

        # 按社区分组
        communities: Dict[int, List[str]] = defaultdict(list)
        for node_id, comm_id in partition.items():
            communities[comm_id].append(node_id)

        result = []
        for comm_id, node_ids in communities.items():
            if len(node_ids) < min_size:
                continue
            # 取 top 5 权重最高的实体作为代表
            node_weights = [
                (nid, G.nodes[nid].get("weight", 0.5))
                for nid in node_ids
                if nid in G.nodes
            ]
            node_weights.sort(key=lambda x: x[1], reverse=True)
            top_entities = [
                {
                    "id": nid,
                    "name": G.nodes[nid].get("name", ""),
                    "type": G.nodes[nid].get("entity_type", ""),
                    "weight": w,
                }
                for nid, w in node_weights[:5]
            ]
            # 社区标签：取 top 2 实体名
            label_entities = [e["name"] for e in top_entities[:2]]
            label = " / ".join(label_entities) if label_entities else f"社区{comm_id}"

            result.append({
                "id": f"community_{comm_id}",
                "label": label,
                "node_ids": node_ids,
                "node_count": len(node_ids),
                "top_entities": top_entities,
                "description": "",
            })

        # 按节点数降序
        result.sort(key=lambda c: c["node_count"], reverse=True)
        return result

    @classmethod
    async def get_community_summary(
        cls,
        db: AsyncSession,
        community_id: str,
        kb_id: str,
    ) -> Optional[dict]:
        """获取单个社区的详细信息"""
        communities = await cls.detect_communities(db, kb_id)
        for comm in communities:
            if comm["id"] == community_id:
                G = await cls.load_networkx(db, kb_id)

                # 社区内节点详细信息
                nodes = []
                for nid in comm["node_ids"]:
                    if nid in G.nodes:
                        nodes.append({
                            "id": nid,
                            "name": G.nodes[nid].get("name", ""),
                            "type": G.nodes[nid].get("entity_type", ""),
                            "weight": G.nodes[nid].get("weight", 0.5),
                            "color": G.nodes[nid].get("color", "#4F8CF7"),
                            "description": G.nodes[nid].get("description", ""),
                        })

                # 社区内边
                node_set = set(comm["node_ids"])
                edges = []
                for u, v, data in G.edges(data=True):
                    if u in node_set and v in node_set:
                        edges.append({
                            "id": data.get("edge_id", ""),
                            "source": u,
                            "target": v,
                            "relation": data.get("relation_type", "关联"),
                            "value": data.get("weight", 0.5),
                        })

                # 社区密度
                sub = G.subgraph(node_set)
                density = nx.density(sub) if sub.number_of_nodes() > 1 else 0.0

                return {
                    "id": community_id,
                    "label": comm["label"],
                    "node_count": comm["node_count"],
                    "nodes": nodes,
                    "edges": edges,
                    "description": comm["description"],
                    "density": round(density, 4),
                }
        return None

    @classmethod
    def format_community_context(cls, community: dict) -> str:
        """将社区信息格式化为 LLM 上下文文本"""
        lines = [f"知识社区: {community.get('label', '')}"]
        lines.append(f"包含 {community.get('node_count', 0)} 个实体:")
        for ent in community.get("top_entities", []):
            lines.append(f"  - {ent['name']} ({ent['type']}, 权重: {ent['weight']:.2f})")
        return "\n".join(lines)

    # ---------- 图谱统计 ----------

    @classmethod
    async def get_graph_stats(
        cls,
        db: AsyncSession,
        kb_id: Optional[str] = None,
    ) -> dict:
        """获取图谱统计信息"""
        # DB 聚合查询
        entity_query = select(
            func.count(GraphEntity.id),
            func.count(func.distinct(GraphEntity.entity_type)),
        )
        relation_query = select(
            func.count(GraphRelation.id),
            func.count(func.distinct(GraphRelation.relation_type)),
        )
        if kb_id:
            entity_query = entity_query.where(GraphEntity.kb_id == kb_id)
            relation_query = relation_query.where(GraphRelation.kb_id == kb_id)

        e_result = await db.execute(entity_query)
        node_count, type_count = e_result.one()
        r_result = await db.execute(relation_query)
        edge_count, rel_type_count = r_result.one()

        # 类型分布
        type_dist_query = select(
            GraphEntity.entity_type, func.count(GraphEntity.id)
        ).group_by(GraphEntity.entity_type)
        if kb_id:
            type_dist_query = type_dist_query.where(GraphEntity.kb_id == kb_id)
        type_result = await db.execute(type_dist_query)
        entity_type_dist = {row[0]: row[1] for row in type_result}

        # 关系类型分布
        rel_dist_query = select(
            GraphRelation.relation_type, func.count(GraphRelation.id)
        ).group_by(GraphRelation.relation_type)
        if kb_id:
            rel_dist_query = rel_dist_query.where(GraphRelation.kb_id == kb_id)
        rel_result = await db.execute(rel_dist_query)
        relation_type_dist = {row[0]: row[1] for row in rel_result}

        # NetworkX 图密度
        density = 0.0
        avg_degree = 0.0
        isolated_count = 0
        community_count = 0
        if kb_id:
            try:
                G = await cls.load_networkx(db, kb_id)
                density = round(nx.density(G), 4) if G.number_of_nodes() > 1 else 0.0
                degrees = dict(G.degree())
                avg_degree = round(sum(degrees.values()) / max(len(degrees), 1), 2)
                isolated_count = sum(1 for d in degrees.values() if d == 0)
            except Exception:
                pass

            # 社区数
            try:
                communities = await cls.detect_communities(db, kb_id)
                community_count = len(communities)
            except Exception:
                pass

        # KB 数量
        kb_query = select(func.count(func.distinct(GraphEntity.kb_id)))
        kb_result = await db.execute(kb_query)
        kb_count = kb_result.scalar() or 0

        return {
            "node_count": node_count or 0,
            "edge_count": edge_count or 0,
            "entity_type_distribution": entity_type_dist,
            "relation_type_distribution": relation_type_dist,
            "density": density,
            "community_count": community_count,
            "avg_degree": avg_degree,
            "isolated_node_count": isolated_count,
            "kb_count": kb_count,
            "entity_type_count": type_count or 0,
            "relation_type_count": rel_type_count or 0,
        }

    # ---------- v3.2: 孤立节点清理 ----------

    @classmethod
    async def clean_orphan_nodes(
        cls,
        db: AsyncSession,
        kb_id: str,
    ) -> Dict[str, int]:
        """
        删除无法建立任何链接的孤立节点（包括弱链接）。

        对于指定 KB，检测所有出度和入度均为 0 的实体（即既没有作为 source
        也没有作为 target 出现在 graph_relations 中的 graph_entities），
        将其从 graph_entities 表中删除。

        Returns:
            {"deleted": int} — 已删除的孤立节点数
        """
        from sqlalchemy import delete as sql_delete, and_

        # 查找所有在该 KB 中有关系的实体 ID
        rel_source_stmt = select(GraphRelation.source_id).where(
            GraphRelation.kb_id == kb_id
        )
        rel_target_stmt = select(GraphRelation.target_id).where(
            GraphRelation.kb_id == kb_id
        )

        source_result = await db.execute(rel_source_stmt)
        target_result = await db.execute(rel_target_stmt)

        linked_ids = set()
        for row in source_result:
            linked_ids.add(row[0])
        for row in target_result:
            linked_ids.add(row[0])

        # 查找该 KB 中所有不在 linked_ids 中的实体
        orphan_stmt = select(GraphEntity.id).where(
            and_(
                GraphEntity.kb_id == kb_id,
                ~GraphEntity.id.in_(linked_ids) if linked_ids else True,
            )
        )
        orphan_result = await db.execute(orphan_stmt)
        orphan_ids = [row[0] for row in orphan_result]

        if not orphan_ids:
            logger.info(f"KB {kb_id}: 无孤立节点")
            return {"deleted": 0}

        # 删除孤立节点
        delete_stmt = sql_delete(GraphEntity).where(
            GraphEntity.id.in_(orphan_ids)
        )
        await db.execute(delete_stmt)
        await db.commit()

        # 使缓存失效
        cls._invalidate_nx_cache(kb_id)

        logger.info(f"KB {kb_id}: 清理 {len(orphan_ids)} 个孤立节点")
        return {"deleted": len(orphan_ids)}

    # ---------- 数据迁移 ----------

    @classmethod
    async def build_from_documents(
        cls,
        db: AsyncSession,
        kb_id: str,
    ) -> Dict[str, int]:
        """
        从现有 document.graph_data JSON 迁移到 GraphEntity/GraphRelation 表。

        检查 graph_entities 是否已有该 KB 的数据，若无则从文档的 graph_data 迁移。
        """
        from app.models.document import Document, DocumentStatus

        # 检查是否已有数据
        stmt = select(func.count(GraphEntity.id)).where(GraphEntity.kb_id == kb_id)
        result = await db.execute(stmt)
        if result.scalar() > 0:
            return {"entities_added": 0, "entities_merged": 0, "relations_added": 0}

        # 获取该 KB 下所有已完成的文档
        doc_stmt = select(Document).where(
            and_(
                Document.kb_id == kb_id,
                Document.status == DocumentStatus.DONE,
                Document.graph_data.isnot(None),
            )
        )
        doc_result = await db.execute(doc_stmt)
        docs = doc_result.scalars().all()

        total_stats = {"entities_added": 0, "entities_merged": 0, "relations_added": 0}
        for doc in docs:
            try:
                graph_data = doc.graph_data or {}
                stats = await cls.build_graph(
                    db, kb_id,
                    nodes=graph_data.get("nodes", []),
                    links=graph_data.get("links", []),
                    doc_id=doc.id,
                )
                for k in total_stats:
                    total_stats[k] += stats[k]
            except Exception as e:
                logger.warning(f"迁移文档图谱失败 doc={doc.id}: {e}")

        return total_stats
