# 架构升级设计概要

> **注意:** 本文档是架构设计概要，列出愿景和目标。实际实现状态见 [CODE_REVIEW.md](CODE_REVIEW.md)。
> v2.3 已完成关键+高优先级修复，v2.4 完成中等+低优先级改进。

你是一位世界顶尖的 AI 工程师兼全栈架构师。现在需要你帮我将一个现有的、轻量级的知识图谱问答原型系统（FastAPI + GraphRAG + Vue 3），全方位重构并升级为一个**企业级、高颜值、兼具”图谱（GraphRAG）与传统检索（Hybrid RAG）”的专业知识库管理后台系统**。

## 🎯 核心重构与升级目标

### 1. 核心检索增强升级：打造专业的 RAG 管道 (Professional RAG)

目前的系统分块和检索过于单一。请重新设计数据流，使其具备现代专业 RAG 的核心特征：

- **高级分块策略 (Advanced Chunking)**：从单纯的代码按字符切分，升级为“语义分块 (Semantic Chunking)”或“父子块架构 (Parent-Child Chunks)”。LanceDB 中仅存储子块向量，但检索后还原为完整的父块上下文。
- **混合检索 (Hybrid Search)**：引入 LanceDB 的向量检索（密集检索）+ 传统 BM25（稀疏检索）的双路并行检索。
- **重排机制 (Reranking)**：设计一个重排层占位符（可调用智谱 AI 的 Rerank API 或本地 BGE-Reranker），对混合检索出的 Chunk 进行二次打分过滤，再送入 LLM。

### 2. 知识提取层升级：常规 NLP + LLM 混合分词抽取

目前系统仅依靠本地 `jieba` 进行关键词和关系匹配，准确率较低。请重构 `utils/entity_extractor.py`：

- **混合管道架构**：
  1. **第一阶段（常规 NLP 粗筛）**：利用 `jieba` / `spaCy` 提取文档中的基础实体名词、词性标注（POS）以及命名实体（NER），并计算 TF-IDF 权重。
  2. **第二阶段（LLM 精炼与对齐）**：将粗筛结果与上下文一并设计成 Prompt 送入智谱 AI（GLM-4-Flash）。让大模型进行指代消解（Coreference Resolution，合并“它”、“该公司”等指代）和三元组（实体-关系-实体）的语义核验。
- **动态图谱合并**：优化关系抽取逻辑，过滤掉低频、模糊的噪点边，确保生成的知识图谱具备高专业度。

### 3. 后端架构升级：API 接口变身为功能完备的“管理后台 (Admin Backoffice)”

抛弃原本松散的单体 `main.py` 结构，将其重构为标准的、模块化的多租户/多知识库企业级后台：

- **目录解耦**：使用 FastAPI 的 `APIRouter`，将路由严格划分到 `api/v1/endpoints/` 下，拆分为：`auth.py`（留空占位）、`knowledge_base.py`（知识库管理）、`document.py`（文档增删改查与状态）、`chat.py`（多模式问答流式输出）、`monitor.py`（后台系统监控）。
- **持久化升级**：彻底淘汰本地 `documents.json` 和 `settings.json`。引入 SQLAlchemy / SQLModel + SQLite（或 PostgreSQL 兼容架构），实现真正的数据库事务管理。设计知识库表（KnowledgeBase）、文档表（Document，含解析状态、字数、Token消耗）、系统配置表（SystemSetting）和聊天历史表（ChatHistory）。
- **真正的异步处理**：利用 FastAPI `BackgroundTasks` 或轻量级任务队列，将文档解析和 GraphRAG 索引构建完全移出主线程。提供 `/api/v1/monitor/tasks` 接口供前端实时轮询文档提取进度（如：解析中、NLP粗筛中、LLM图谱构建中、完成、失败）。

### 4. 前端视觉与可视化升级：极致美化、现代化 SaaS 风格

目前的前端较为简陋，请基于 Vue 3 + Vite + Element Plus (或 Tailwind CSS) 进行整容级视觉重构：

- **视觉风格**：采用极简主义的现代企业级 SaaS 阴影和渐变，支持**暗黑模式 (Dark Mode)** 开关。引入毛玻璃效果（Glassmorphism）、微交互动画和流畅的过渡效果。
- **布局重组（后台化）**：
  - **侧边栏导航**：仪表盘概览（Dashboard）、知识库管理（Multi-KB）、智能问答（Chat Studio）、图谱探索（Graph Workspace）、系统设置（Settings）。
  - **工作台视效**：问答界面参考 ChatGPT/Claude，支持打字机流式动画、Markdown 完美渲染、代码高亮、引用文献/来源分块（Chunk Sources）折叠悬浮卡片显示。
- **图谱渲染优化 (D3.js / Canvas)**：
  - 针对大数据量图谱，提供 D3.js 结合 **Canvas** 的渲染方案（或推荐成熟的 WebGL 图库），替换原有的纯 SVG 渲染，解决大规模节点拖拽卡顿问题。
  - 使用 Vue 3 的 `shallowRef` 或 `markRaw` 处理图谱实例和原始点边数据，严禁深度响应式追踪（Proxy）导致的内存暴涨。
  - 节点根据实体类型自动着色，支持点击高亮一阶连通边，并弹出华丽的右侧抽屉（Drawer）展示实体详情和关联文档。

请以专业、严谨、注释详尽的 Python 3.11+ 标准输出上述内容。
