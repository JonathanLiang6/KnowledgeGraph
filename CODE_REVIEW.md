# 🔍 KnowledgeGraph 项目全面审阅报告

> 审阅日期: 2026-06-18 | 分支: v2.2 | 审阅者: Claude Code

---

## 项目概况

| 维度 | 现状 |
|------|------|
| 分支 | `v2.2` |
| 后端 | FastAPI + SQLAlchemy 2.0 + LanceDB + DeepSeek |
| 前端 | Vue 3 + Vite + Canvas 图谱 |
| 后端代码行数 | ~8500 行 (含新旧两套) |
| 前端代码行数 | ~2300 行 |
| 测试覆盖 | **无** |
| Docker 支持 | **无** |
| 文档 | README / PROJECT_SUMMARY / Improve.md |

---

## 🔴 一、关键问题 (Critical)

### 1. 存在两套并行的后端代码

这是本项目最根本的问题。仓库中存在两个完全独立的代码体系:

| | 新架构 `backend/app/` | 旧架构 `backend/utils/` |
|---|---|---|
| 入口 | `app/main.py` (FastAPI lifespan) | `utils/main.py` (~1221行单体应用) |
| 路由结构 | `api/v1/endpoints/` (模块化) | 全部写在 `utils/main.py` 里 |
| 配置来源 | `app/core/config.py` (DeepSeek) | `utils/config.py` (智谱AI) |
| 数据存储 | SQLAlchemy + SQLite | 内存 dict + JSON 文件 |
| 实体提取 | `app/services/entity_extractor.py` | `utils/entity_extractor.py` |
| 状态 | **活跃开发中** | **遗留代码, 已废弃** |

**风险:** 新开发者无法判断哪个是真正的入口。两套代码的 LLM 提供商、端口号完全不同。

**修复:** 删除 `backend/utils/` 目录，以 `backend/app/` 为唯一代码源。
- `backend/utils/main.py` → 删除
- `backend/utils/config.py` → 删除
- `backend/utils/entity_extractor.py` → 删除
- `backend/utils/helpers.py` → 删除
- `backend/utils/__init__.py` → 删除

**状态:** ✅ 已修复

---

### 2. CORS 配置违反浏览器规范

**文件:** `backend/app/main.py:95-101`

`allow_origins=["*"]` 与 `allow_credentials=True` 同时使用。这是 W3C CORS 规范明确禁止的组合，现代浏览器会直接拒绝响应。**所有携带凭据的跨域请求静默失败。**

```python
# 错误:
allow_origins=["*"],
allow_credentials=True,

# 修复: 要么移除 allow_credentials，要么限制具体域名
allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
allow_credentials=True,
```

**状态:** ✅ 已修复

---

### 3. BM25 伪增量索引导致每次搜索重建全量索引

**文件:** `backend/app/services/hybrid_search.py:163-171`

`_ensure_index()` 在每次 `search()` 调用时重建完整的 BM25 矩阵。`_dirty` 标志和 `_pending_docs` 列表形同虚设。10000 篇文档的语料库，每次搜索都要重新分词和构建 BM25。

```python
# 问题: _ensure_index 在每次 search() 调用时全量重建
def _ensure_index(self):
    if not self._dirty:
        return
    tokenized = [Tokenizer.tokenize(text) for text in self.corpus]  # 全量重建
    self._bm25 = BM25Okapi(tokenized)

# 修复: 在 add_documents 时直接重建, search 时只检查就绪状态
def add_documents(self, doc_ids, texts, metadatas):
    self.corpus.extend(texts)
    self._rebuild_index()  # 添加文档时立即重建

def search(self, query, top_k):
    if self._bm25 is None:
        self._rebuild_index()  # 延迟初始化
    ...
```

**状态:** ✅ 已修复

---

### 4. `rag_service.py` 全局可变状态无线程同步

**文件:** `backend/app/services/rag_service.py:28-61`

`_graph_entity_index` 是模块级 dict，由 `_extract_query_entities()` (读) 和 `update_graph_index()` (写) 并发访问。在高并发下会触发 `RuntimeError: dictionary changed size during iteration`。

```python
# 修复: 添加 asyncio.Lock
_graph_index_lock = asyncio.Lock()

async def update_graph_index(self, entities, relationships):
    async with _graph_index_lock:
        # ... 更新 _graph_entity_index

async def _extract_query_entities(self, query):
    async with _graph_index_lock:
        # ... 读取 _graph_entity_index
```

**状态:** ✅ 已修复

---

### 5. LanceDB SQL 注入风险

**文件:** `backend/app/services/hybrid_search.py:311`

`self._table.delete(f"doc_id = '{doc_id}'")` — 如果 `doc_id` 含单引号，会产生格式错误的 SQL 或注入攻击。

```python
# 修复: 使用参数化查询
self._table.delete("doc_id = :doc_id", filter_args={"doc_id": doc_id})
```

**状态:** ✅ 已修复

---

### 6. 零测试覆盖

项目中不存在 `tests/` 目录。对于一个正在活跃重构的系统，这是不可持续的。

**修复:** 创建 `backend/tests/` 目录结构，至少包含 API 冒烟测试和核心服务测试。

**状态:** ✅ 基础结构已创建

---

## 🟠 二、高优先级 (High)

### 7. 嵌入计算执行两次 + 同步阻塞事件循环

**文件:** `backend/app/tasks/document_tasks.py:344-377`

- `_stage_embedding` 生成嵌入后丢弃结果
- `_stage_indexing` 重新生成完全相同的嵌入 (浪费 2x CPU)
- `_stage_indexing` 使用同步 `EmbeddingService.encode()` 阻塞整个事件循环

```python
# 修复前 (_stage_indexing):
embeddings = EmbeddingService.encode(child_texts)  # 同步阻塞 + 重复计算

# 修复后:
embeddings = await EmbeddingService.encode_async(child_texts)  # 异步非阻塞
```
同时将 `_stage_embedding` 的结果传递给 `_stage_indexing`，消除重复计算。

**状态:** ✅ 已修复

---

### 8. RAG 上下文是空壳 — 未执行实际检索

**文件:** `backend/app/api/v1/endpoints/chat.py:129-187`

`_build_rag_messages` 只获取文档元数据（摘要行），从未检索与用户查询语义相关的实际文本块。`rag-local` 和 `rag-hybrid` 模式实际上等同于 `deepseek-chat` 模式。

```python
# 修复: 集成 HybridSearchService 执行实际检索
hybrid = HybridSearchService()
search_results = await hybrid.search(query=user_query, top_k=top_k)
# 从搜索结果中构建上下文
```

**状态:** ✅ 已修复

---

### 9. 流式聊天忽略 `temperature` 和 `max_tokens`

**文件:** `backend/app/api/v1/endpoints/chat.py:115`

非流式路径传递 `temperature` 和 `max_tokens`，但流式路径忽略了它们，回退到默认值。

```python
# 修复前:
async for chunk in DeepSeekClient.chat_stream(messages=messages):

# 修复后:
async for chunk in DeepSeekClient.chat_stream(
    messages=messages,
    temperature=request.temperature,
    max_tokens=request.max_tokens,
):
```

**状态:** ✅ 已修复

---

### 10. `content_chunks` 内存积累

**文件:** `backend/app/api/v1/endpoints/document.py:67-78`

文件上传验证时把整个文件内容累积在 `content_chunks` 列表中，但从未使用。49MB 并发上传即可大量消耗内存。

```python
# 修复: 删除 content_chunks, 仅跟踪 total_size
total_size = 0
while True:
    chunk = await file.read(chunk_size)
    if not chunk:
        break
    total_size += len(chunk)
    if total_size > max_size:
        raise HTTPException(...)
```

**状态:** ✅ 已修复

---

### 11. 文件去重扫描整个磁盘

**文件:** `backend/app/api/v1/endpoints/document.py:426-436`

`check_duplicate` 为磁盘上每个文件计算完整 SHA256。100个 10MB 文件 = 1GB 磁盘读取。

```python
# 修复: 添加 file_hash 数据库列, 直接查询
existing = await db.execute(
    select(Document).where(Document.file_hash == file_hash)
)
```

**状态:** ✅ 已修复

---

### 12. `colors.py` 与 `settings.yaml` 实体类型语言不一致

- `colors.py` 用**中文**键 (`概念`, `理论`, `方法`...)
- `settings.yaml` 用**英文**类型 (`concept`, `topic`, `method`...)

所有提取的实体都会落回到 fallback 调色板。

**修复:** 在 `colors.py` 中添加英文→中文映射 + 中英双语键。

**状态:** ✅ 已修复

---

### 13. `get_color_for_type` 与 `get_legend` 的 fallback 策略不一致

**文件:** `backend/app/core/colors.py`

前者使用调用者提供的 index，后者使用内部计数器。同一个未知类型可能在不同上下文中获得不同颜色。

```python
# 修复: 基于 hash(entity_type) 的确定性映射
def _get_fallback_color(entity_type: str) -> str:
    idx = hash(entity_type) % len(FALLBACK_COLORS)
    return FALLBACK_COLORS[idx]
```

**状态:** ✅ 已修复

---

## 🟡 三、中等优先级 (Medium)

| # | 问题 | 文件 | 状态 |
|---|------|------|------|
| 14 | 数据库启动失败后应用继续运行 | `main.py:36-39` | ⬜ 待修复 |
| 15 | `asyncio.sleep(3)` 硬编码脆弱 | `main.py:76` | ⬜ 待修复 |
| 16 | 30+ 处 `int(os.getenv(...))` 无 `ValueError` 保护 | `config.py` | ⬜ 待修复 |
| 17 | SQLite 未启用 WAL 模式 | `database.py` | ⬜ 待修复 |
| 18 | `get_db` 混用 `async with` + `session.close()` | `database.py:51-64` | ⬜ 待修复 |
| 19 | `graph_data` 列类型为 `Text` 而非 `JSON` | `models/document.py:61` | ⬜ 待修复 |
| 20 | 缺少 `ChatHistoryResponse` Schema | `schemas/chat.py` | ⬜ 待修复 |
| 21 | `DocumentResponse` 缺少 `graph_data` 字段 | `schemas/document.py` | ⬜ 待修复 |
| 22 | 数据库缺少 `kb_id`/`status` 索引 | `models/document.py` | ⬜ 待修复 |
| 23 | 前端发送逗号分隔字符串后端可能不解析 | `frontend/Documents.vue` | ⬜ 待修复 |
| 24 | `GraphWorkspace` 中 `currentNodeData` 非响应式 | 前端 | ⬜ 待修复 |
| 25 | `_task_store` 无限增长 | `monitor.py:14` | ⬜ 待修复 |
| 26 | 知识库删除不清理 LanceDB 向量 | `knowledge_base.py:119-147` | ⬜ 待修复 |
| 27 | DeepSeek 客户端重试非可重试错误 | `deepseek_client.py:54-77` | ⬜ 待修复 |
| 28 | `entity_extractor` 中 O(n²) 实体查找 | `entity_extractor.py:347-348` | ⬜ 待修复 |
| 29 | 重排序器延迟加载竞态条件 | `reranker_service.py:27` | ⬜ 待修复 |
| 30 | 设置 upsert 竞态条件 | `settings.py:97-107` | ⬜ 待修复 |

---

## 🟢 四、低优先级 / 改进建议

| # | 问题 | 状态 |
|---|------|------|
| 31 | 版本号散落各处 vs 分支 `v2.2` | ⬜ 待修复 |
| 32 | XSS风险: `v-html` 无 DOMPurify | ⬜ 待修复 |
| 33 | 未使用的 npm 依赖 (echarts, pinia, highlight.js) | ⬜ 待修复 |
| 34 | `formatDate` 在前端多个组件重复 | ⬜ 待修复 |
| 35 | `helpers.py` 中 `import time` 放在文件末尾 | ⬜ 待修复 |
| 36 | MD5 用于 ID 生成 | ⬜ 待修复 |
| 37 | CJK 正则范围过窄 | ⬜ 待修复 |
| 38 | PyPDF2 回退导入已废弃 | ⬜ 待修复 |
| 39 | `__init__.py` 空文件未导出公共 API | ⬜ 待修复 |
| 40 | 日志使用 eager f-string | ⬜ 待修复 |
| 41 | 配置应以依赖注入而非模块单例 | ⬜ 待修复 |
| 42 | 缺少 `Dockerfile` / `docker-compose.yml` | ⬜ 待修复 |
| 43 | 缺少 `pyproject.toml` | ⬜ 待修复 |
| 44 | 缺少 `Makefile` | ⬜ 待修复 |
| 45 | `Improve.md` 定位模糊 | ⬜ 待修复 |
| 46 | README 描述智谱AI但实际使用DeepSeek | ⬜ 待修复 |
| 47 | `lancedb>=0.6.0` 下限过低 | ⬜ 待修复 |

---

## 📊 评分卡

| 维度 | 评分 | 说明 |
|------|------|------|
| 架构设计 | B+ | 分层清晰, 两阶段提取, 混合搜索设计合理 |
| 代码质量 | B- | 存在双重代码库、不一致的模式 |
| 安全性 | C | 无认证、XSS风险、SQL注入风险、CORS配置错误 |
| 性能 | C+ | BM25伪增量、重复嵌入计算、缺少数据库索引 |
| 可维护性 | C | 双重代码库、零测试、版本号不一致 |
| 文档 | B | 内容丰富但与代码状态不同步 |

---

## 🎯 路线图

### 第一阶段 (v2.3) — 关键+高优先级修复
- [x] 删除 `backend/utils/` 遗留代码
- [x] 修复 CORS 配置
- [x] 修复 BM25 伪增量索引
- [x] 添加 RAG 图索引线程安全
- [x] 修复 LanceDB SQL 注入
- [x] 创建测试套件基础结构
- [x] 修复双嵌入计算 + 事件循环阻塞
- [x] 实现真正的 RAG 上下文检索
- [x] 修复流式参数传递
- [x] 修复 content_chunks 内存泄漏
- [x] 实现数据库文件去重
- [x] 统一实体类型分类
- [x] 修复颜色 fallback 一致性

### 第二阶段 (v2.4) — 中等优先级
- [ ] 数据库启动健康检查
- [ ] 环境变量解析健壮性
- [ ] SQLite WAL 模式
- [ ] 数据库索引优化
- [ ] Schema/Model 一致性
- [ ] 竞态条件修复
- [ ] O(n²) 算法优化

### 第三阶段 (v2.5) — 低优先级 + 工程化
- [ ] Docker 容器化
- [ ] 版本号统一
- [ ] 前端安全/性能优化
- [ ] 代码去重
- [ ] 文档更新
- [ ] 认证层实现
