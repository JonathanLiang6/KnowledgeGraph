"""
事件循环性能修复测试 (v4.1)

覆盖：load_networkx 限量加载（#66）、find_paths 枚举熔断（#64）。
"""
import itertools

import pytest

from app.models.graph_entity import GraphEntity, GraphRelation

_seq = itertools.count(1000)


@pytest.mark.anyio
async def test_load_networkx_limit_returns_top_weight(db_session):
    """limit 下推：只加载权重 Top-N 实体，且不影响全量缓存"""
    n = next(_seq)
    kb = f"kb-lim{n}"
    db_session.add_all([
        GraphEntity(id=f"e{n}-{i}", kb_id=kb, name=f"实体{i}", entity_type="概念",
                    weight=0.1 * i)
        for i in range(1, 11)  # 权重 0.1 ~ 1.0
    ])
    await db_session.commit()

    from app.services.graph_service import GraphService

    G_limited = await GraphService.load_networkx(db_session, kb, limit=3)
    assert G_limited.number_of_nodes() == 3
    # 应为权重最高的三个
    assert {f"e{n}-{i}" for i in (8, 9, 10)} <= set(G_limited.nodes)

    # 全量加载不受限量加载影响
    G_full = await GraphService.load_networkx(db_session, kb)
    assert G_full.number_of_nodes() == 10


@pytest.mark.anyio
async def test_find_paths_enumeration_capped(db_session):
    """密集图枚举熔断：路径数远超上限时最多返回 20 条且不卡死"""
    n = next(_seq)
    kb = f"kb-cap{n}"
    src, dst = f"s{n}", f"t{n}"
    mids = [f"m{n}-{i}" for i in range(15)]
    ns = [f"n{n}-{j}" for j in range(15)]

    db_session.add(GraphEntity(id=src, kb_id=kb, name="源", entity_type="概念", weight=1.0))
    db_session.add(GraphEntity(id=dst, kb_id=kb, name="汇", entity_type="概念", weight=1.0))
    db_session.add_all(GraphEntity(id=m, kb_id=kb, name="中转", entity_type="概念", weight=0.5) for m in mids + ns)

    rels = []
    rid = 0
    for m in mids:
        rid += 1
        rels.append(GraphRelation(id=f"p{rid}", kb_id=kb, source_id=src, target_id=m, relation_type="连"))
    for m in mids:          # 完全二部图：15×15=225 条两跳路径
        for x in ns:
            rid += 1
            rels.append(GraphRelation(id=f"p{rid}", kb_id=kb, source_id=m, target_id=x, relation_type="连"))
    for x in ns:
        rid += 1
        rels.append(GraphRelation(id=f"p{rid}", kb_id=kb, source_id=x, target_id=dst, relation_type="连"))
    for m in mids:          # 直达边：15 条一跳路径
        rid += 1
        rels.append(GraphRelation(id=f"p{rid}", kb_id=kb, source_id=src, target_id=m, relation_type="直达"))

    db_session.add_all(rels)
    await db_session.commit()

    from app.services.graph_service import GraphService

    GraphService._invalidate_nx_cache(kb)
    paths = await GraphService.find_paths(db_session, src, dst, kb, max_hops=4)
    # 总路径数 240 > 200 熔断线，但返回值最多 20 条
    assert len(paths) <= 20
    assert paths, "至少应返回最短路径"
    assert paths[0]["length"] == 3  # 最短路径 src→m→n→dst，排序后在前
