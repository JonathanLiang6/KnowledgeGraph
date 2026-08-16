"""
图谱服务核心链路测试 (v4.1)

覆盖：图谱构建入图、NetworkX 加载、路径查询、缓存失效、悬空边容错。
运行在临时数据库上（conftest 隔离）；每个用例使用唯一 kb/实体 ID 避免主键冲突。
"""
import itertools

import pytest

from app.models.graph_entity import GraphEntity, GraphRelation

_seq = itertools.count(1)


async def _seed_graph(db):
    """构造 A→B→C 三节点链 + A→C 直连边（每用例唯一前缀）"""
    n = next(_seq)
    kb = f"kb-t{n}"
    a, b, c = f"a{n}", f"b{n}", f"c{n}"
    db.add_all([
        GraphEntity(id=a, kb_id=kb, name=f"机器学习{n}", entity_type="概念"),
        GraphEntity(id=b, kb_id=kb, name=f"神经网络{n}", entity_type="概念"),
        GraphEntity(id=c, kb_id=kb, name=f"深度学习{n}", entity_type="概念"),
    ])
    db.add_all([
        GraphRelation(id=f"r1-{n}", kb_id=kb, source_id=a, target_id=b,
                      relation_type="包含", source_doc_id="doc-1"),
        GraphRelation(id=f"r2-{n}", kb_id=kb, source_id=b, target_id=c,
                      relation_type="属于", source_doc_id="doc-1"),
        GraphRelation(id=f"r3-{n}", kb_id=kb, source_id=a, target_id=c,
                      relation_type="相关", source_doc_id="doc-1"),
    ])
    await db.commit()
    return kb, a, b, c


@pytest.mark.anyio
async def test_load_networkx_builds_graph(db_session):
    kb, a, b, c = await _seed_graph(db_session)
    from app.services.graph_service import GraphService

    G = await GraphService.load_networkx(db_session, kb)
    assert G.number_of_nodes() == 3
    assert G.number_of_edges() == 3
    assert G.nodes[a]["name"].startswith("机器学习")
    assert G.has_edge(a, c)


@pytest.mark.anyio
async def test_load_networkx_kb_isolation(db_session):
    """图加载必须只含目标 KB 的节点"""
    kb, a, _, _ = await _seed_graph(db_session)
    db_session.add(GraphEntity(id=f"x{kb}", kb_id=kb + "-other", name="无关实体", entity_type="概念"))
    await db_session.commit()

    from app.services.graph_service import GraphService

    G1 = await GraphService.load_networkx(db_session, kb)
    G2 = await GraphService.load_networkx(db_session, kb + "-other")
    assert f"x{kb}" not in G1
    assert set(G2.nodes) == {f"x{kb}"}


@pytest.mark.anyio
async def test_find_paths_returns_routes(db_session):
    kb, a, b, c = await _seed_graph(db_session)
    from app.services.graph_service import GraphService

    GraphService._invalidate_nx_cache(kb)
    paths = await GraphService.find_paths(db_session, a, c, kb, max_hops=2)
    assert isinstance(paths, list) and paths, "应至少找到一条路径"
    # 至少存在直连（1 跳）与 A→B→C 两跳两条路径
    assert any(p["length"] == 1 for p in paths)
    assert any(p["length"] == 2 for p in paths)


@pytest.mark.anyio
async def test_dangling_edge_not_loaded(db_session):
    """悬空边（指向不存在实体）加载时应被跳过而非报错"""
    kb, a, _, _ = await _seed_graph(db_session)
    db_session.add(GraphRelation(id=f"dr-{kb}", kb_id=kb,
                                 source_id=a, target_id=a + "-missing",
                                 relation_type="悬空"))
    await db_session.commit()

    from app.services.graph_service import GraphService

    G = await GraphService.load_networkx(db_session, kb)
    assert not G.has_edge(a, a + "-missing")


@pytest.mark.anyio
async def test_cache_invalidate_on_new_load(db_session):
    """缓存失效后再加载应反映新增节点"""
    kb, a, _, _ = await _seed_graph(db_session)
    from app.services.graph_service import GraphService

    G = await GraphService.load_networkx(db_session, kb)
    assert G.number_of_nodes() == 3

    GraphService._invalidate_nx_cache(kb)
    db_session.add(GraphEntity(id=f"d{kb}", kb_id=kb, name="新节点", entity_type="概念"))
    await db_session.commit()

    G2 = await GraphService.load_networkx(db_session, kb)
    assert G2.number_of_nodes() == 4
