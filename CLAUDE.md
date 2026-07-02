# CLAUDE.md — KnowledgeGraph v3.0

> 智能教学知识图谱管理平台 · Claude Code 项目指南

## 项目概述

基于 **FastAPI + Vue 3** 的全栈知识图谱应用。核心能力：文档上传与异步处理、实体-关系知识图谱构建、混合检索（向量 + BM25 + 图谱多跳）、ReAct Agent 多步推理问答、SSE 流式响应。

- **后端**: Python 3.11+ / FastAPI / SQLAlchemy 2.0 异步 / SQLite WAL / LanceDB / NetworkX
- **前端**: Vue 3 / Vite / Element Plus (绿色主题) / D3.js Canvas 图谱渲染
- **AI**: DeepSeek V4 (OpenAI SDK 兼容) / BGE 本地嵌入 / ReAct Agent / 三层记忆

## 常用命令

```bash
# ── 环境准备 ──
cd backend && pip install -r requirements.txt   # 安装后端依赖
cd frontend && npm install                       # 安装前端依赖

# ── 启动开发 ──
start.bat                    # Windows 一键启动（自动清理端口 → 后端 8013 → 前端 3000）
make dev                     # 同时启动后端和前端（后台进程）
make dev-backend             # 仅启动后端（前台）

# ── Docker ──
docker-compose up -d         # 启动全部服务（后端 8013 + 前端 3000）
docker-compose down          # 停止服务

# ── 测试 ──
cd backend && pytest                         # 运行所有测试（asyncio_mode=auto）
cd backend && pytest tests/ -v               # 详细输出
cd backend && pytest tests/ -k "test_name"   # 运行特定测试

# ── 代码质量 ──
make lint                    # Ruff 检查 + 格式检查（不修改文件）
make format                  # Ruff 自动修复 + 格式化
make typecheck               # mypy 类型检查（ignore_missing_imports=true）
cd frontend && npm run lint  # ESLint 前端检查

# ── 清理 ──
make clean                   # 清理所有缓存（__pycache__/.pytest_cache/.ruff_cache/.mypy_cache/node_modules/.cache）
```

## 架构

```
KnowledgeGraph/
├── start.bat                  # Windows 一键启动（端口清理 + venv 激活 + 后端就绪等待）
├── Makefile                   # dev / test / lint / format / typecheck / clean
├── Dockerfile                 # python:3.11-slim，uvicorn 启动
├── docker-compose.yml         # backend (8013) + frontend (3000)，kg_data 持久卷
├── pyproject.toml             # Ruff (line-length=120) / pytest (asyncio_mode=auto) / mypy
├── README.md                  # 项目介绍、快速开始、技术栈
├── ROADMAP.md                 # GraphRAG → AgentRAG 演进路线图与技术决策记录
│
├── backend/
│   ├── .env                   # 环境变量（不入库），从 .env.example 复制
│   ├── .env.example           # 配置模板，不含真实密钥
│   ├── requirements.txt       # 完整依赖列表
│   ├── data/                  # 运行时数据（LanceDB 索引、SQLite 数据库）
│   ├── inputs/files/          # 上传文档存储目录
│   └── app/
│       ├── main.py                # FastAPI 入口 · lifespan 启动/关闭 · CORS · 版本 3.0.0
│       ├── api/v1/router.py       # 路由聚合 → /api/v1
│       │   ├── chat.py            # 问答：4 种模式 + SSE 流式 + Agent 推理
│       │   ├── graph.py           # 图谱：实体/关系/路径/邻居/社区/统计
│       │   ├── document.py        # 文档：上传/列表/去重/重新处理/删除
│       │   ├── knowledge_base.py  # 知识库：CRUD + 级联删除
│       │   ├── settings.py        # 系统设置读写
│       │   └── monitor.py         # 监控：健康状态/任务列表/处理进度
│       ├── core/
│       │   ├── config.py          # Config 类：全部配置从 .env 读取，_safe_int/_safe_float 容错
│       │   ├── database.py        # 异步 SQLAlchemy 引擎 + SQLite WAL + get_db 依赖注入
│       │   └── colors.py          # 20+ 实体类型配色映射
│       ├── models/                # ORM 模型（SQLAlchemy 2.0 异步）
│       │   ├── knowledge_base.py  # KnowledgeBase: id/name/description/created_at/updated_at
│       │   ├── document.py        # Document: 关联 kb_id，含 graph_data JSON 字段（向后兼容）
│       │   ├── graph_entity.py    # GraphEntity + GraphRelation：独立图存储表
│       │   └── system_setting.py  # SystemSetting: key-value 配置持久化
│       ├── schemas/               # Pydantic v2 请求/响应模型
│       │   ├── chat.py / document.py / graph.py / knowledge_base.py / settings.py
│       ├── services/
│       │   ├── rag_service.py         # RAG 编排：索引构建/混合搜索/全局搜索/查询路由/上下文构建
│       │   ├── hybrid_search.py       # LanceDB 向量 + BM25 关键词 → RRF 融合
│       │   ├── embedding_service.py   # BGE 本地嵌入（sentence-transformers + PyTorch）
│       │   ├── reranker_service.py    # BGE Cross-Encoder 重排序
│       │   ├── chunking_service.py    # 语义分块（父子块策略，parent-child）
│       │   ├── deepseek_client.py     # DeepSeek API 客户端（OpenAI SDK 兼容）
│       │   ├── char_stream.py         # 逐字符 SSE 流式拆分
│       │   ├── entity_extractor.py    # jieba 分词 + TF-IDF 实体抽取
│       │   ├── llm_refiner.py         # LLM 实体精炼
│       │   ├── extraction_service.py  # 两阶段抽取编排（jieba → LLM 精炼）
│       │   ├── graph_service.py       # 图构建/BFS/DFS/最短路径/Louvain 社区检测/统计/数据迁移
│       │   ├── graph_retriever.py     # 多跳图检索器：jieba 实体匹配 → 图遍历 → RRF 融合
│       │   ├── agent_service.py       # ReAct Agent 循环 (Thought→Action→Observation，最大 6 步)
│       │   ├── memory_service.py      # 三层记忆：WorkingMemory / EpisodicMemory / SemanticMemory
│       │   └── tools/                 # Agent 工具集（标准化 async 函数接口）
│       │       ├── __init__.py        # TOOL_REGISTRY + get_tools_description()
│       │       ├── vector_search.py   # 语义向量检索（适合模糊概念查询）
│       │       ├── graph_traverse.py  # 知识图谱多跳遍历（适合关系型/多步推理问题）
│       │       ├── entity_lookup.py   # 实体详情查询（了解特定概念/人物/事物）
│       │       └── bm25_search.py    # 关键词精确匹配检索（适合精确术语查询）
│       ├── tasks/
│       │   └── document_tasks.py      # 异步文档处理流水线（6 阶段 + 断点续传 + 并发控制）
│       ├── utils/
│       │   ├── file_parser.py         # 多格式解析：PDF/DOCX/PPTX/EPUB/TXT/Markdown
│       │   └── helpers.py             # 工具函数
│       └── tests/
│           ├── conftest.py            # async client fixture (httpx.AsyncClient)
│           ├── test_health.py         # 健康检查测试
│           ├── test_colors.py         # 颜色映射测试
│           └── test_hybrid_search.py  # 混合检索测试
│
└── frontend/
    ├── index.html                # Vite 入口
    ├── vite.config.js            # 端口 3000，代理 /api → localhost:8013
    └── src/
        ├── main.js               # Vue 应用入口
        ├── App.vue               # 根组件
        ├── api/                  # API 客户端层
        │   ├── index.js          # axios 实例 + 基础配置
        │   ├── chat.js           # 聊天 API（SSE 流式）
        │   ├── document.js       # 文档 CRUD API
        │   ├── graph.js          # 图谱数据 API
        │   └── knowledgeBase.js  # 知识库 CRUD API
        ├── router/index.js       # Vue Router: HomePage → KBLayout (子路由: Documents / GraphWorkspace / ChatStudio)
        ├── layouts/KBLayout.vue  # 知识库布局外壳（侧边栏 + 子路由出口）
        ├── composables/
        │   └── useGraphRenderer.js  # D3.js Canvas 力导向图渲染（非 SVG，大数据量性能优化）
        ├── styles/
        │   ├── variables.scss    # SCSS 变量（森林绿主题色板）
        │   ├── global.scss       # 全局样式
        │   └── transitions.scss  # 过渡动画
        └── views/
            ├── HomePage.vue      # 首页（项目介绍 + 知识库列表入口）
            ├── Documents.vue     # 文档管理（上传/列表/去重/处理状态）
            ├── GraphWorkspace.vue # 图谱工作台（D3 Canvas 可视化 + 实体面板 + 路径查询）
            └── ChatStudio.vue    # 问答工作室（4 种模式切换 + SSE 打字机 + Agent 推理过程）
```

## 关键设计决策

### 配置管理
- 所有配置通过 `backend/.env` 环境变量读取，零硬编码
- `backend/.env.example` 是模板文件，包含所有可配置项的默认值，不含真实密钥
- `.env` 已在 `.gitignore` 中，不会被提交
- `config.py` 的 `_safe_int()` / `_safe_float()` 对格式错误有容错回退（记录警告并使用默认值）
- 关键配置项：`DEEPSEEK_API_KEY`、`DEEPSEEK_CHAT_MODEL`、`EMBEDDING_MODEL`、`EMBEDDING_DIM`、`AGENT_MAX_STEPS`、`MAX_CONCURRENT_DOCUMENT_PROCESSING`

### 数据库
- **SQLAlchemy 2.0** 异步引擎（`AsyncSession`），**SQLite + WAL 模式**（支持并发读写）
- `get_db()` — FastAPI 依赖注入，自动管理请求级会话生命周期
- `async_session_factory` — 模块级工厂，用于后台任务和 Agent（不能使用 Depends）
- 数据库文件：`backend/data/kg.db`，连接字符串从 `DATABASE_URL` 环境变量读取

### 图存储（Phase 1 GraphRAG）
- **双轨存储**：`Document.graph_data`（JSON 字段，向后兼容旧数据）+ `GraphEntity` / `GraphRelation`（独立表，主力）
- 启动时自动从 Document JSON 迁移到独立表（`migrate_graph_data()`）
- **NetworkX** 用于内存图计算（BFS/DFS/最短路径/Louvain 社区检测），**SQLAlchemy** 用于持久化
- 模块级 LRU 缓存 `_nx_cache`，按知识库 ID 缓存 NetworkX 图对象
- 写锁机制（`_kb_write_locks`）防止同一知识库并发写入冲突
- 实体对齐：同名同类型实体自动合并（规则匹配），可扩展 LLM 辅助对齐

### 检索融合 (RRF — Reciprocal Rank Fusion)
```
用户查询
  ├── 向量检索 (LanceDB, weight=0.7)  ─┐
  ├── BM25 关键词检索 (weight=0.3)     ─┤
  └── 图谱多跳检索 (weight=0.3)        ─┘
              ↓
         RRF 融合排序
              ↓
    BGE Cross-Encoder Reranker 重排序
              ↓
         最终结果集
```
- 查询路由：摘要类关键词（"总结"/"概览"/"全部"）→ global_search (Map-Reduce)；事实类关键词（"什么"/"如何"/"定义"/"比较"）→ local_search

### Agent 推理（Phase 2 AgentRAG）
- **自定义 ReAct 循环**（非 LangGraph），最大 `AGENT_MAX_STEPS` 步（默认 6）
- 每步输出：`Thought` → `Action`（工具名 + 参数）→ `Observation`（工具返回）
- **4 个工具**：`vector_search` / `graph_traverse` / `entity_lookup` / `bm25_search`
- 工具注册表 `TOOL_REGISTRY`：统一接口 `async def tool(db, kb_id, **kwargs) -> str`
- **SSE 流式推送**，前端实时展示推理过程（Thought/Action/Observation 卡片）
- `REACT_SYSTEM_PROMPT` 动态注入工具描述，Agent 自主选择调用工具或给出最终答案

### 三层记忆系统
| 层级 | 类 | 生命周期 | 存储 |
|------|-----|---------|------|
| **工作记忆** (WorkingMemory) | Agent 当前推理循环的中间步骤 | 单次 Agent 调用 | 内存列表 |
| **情景记忆** (EpisodicMemory) | 对话会话级摘要和关键实体 | 单次对话 | 内存 + 可选持久化 |
| **语义记忆** (SemanticMemory) | 知识图谱结构化知识 | 跨会话持久 | GraphEntity/GraphRelation 表 |

### 文档处理流水线
- **6 阶段异步流水线**：文件解析 → 文本清洗 → 语义分块 → 实体抽取 → 向量嵌入 → 图构建
- **断点续传**：每阶段完成后更新 `Document.processing_status`，重启后从上次成功阶段恢复
- **并发控制**：`asyncio.Semaphore` 限制同时处理的文档数
- **超时保护**：每阶段独立超时，防止单文档卡死整个流水线
- SHA256 去重：上传时计算文件哈希，已存在则跳过

### 前端
- **Vite** 开发服务器端口 **3000**，代理 `/api` → `localhost:8013`
- **Element Plus (El-Plus)** 组件库，**森林绿主题**（SCSS 变量 + El-Plus CSS 变量覆盖）
- **D3.js Canvas** 力导向图渲染（非 SVG），适用于大数据量节点（1000+ 实体流畅渲染）
- **Vue Router**：`HomePage` → `KBLayout`（侧边栏布局外壳）→ 子路由 `Documents` / `GraphWorkspace` / `ChatStudio`
- **SSE 流式**：`char_stream.py` 逐字符拆分，前端打字机效果显示

### 问答 4 种模式
| 模式 | 端点参数 | 说明 |
|------|---------|------|
| **deepseek-chat** | `mode=deepseek-chat` | 纯 LLM 对话，不检索知识库 |
| **rag-hybrid** | `mode=rag-hybrid` | 混合检索 + RRF + Reranker + LLM 生成 |
| **rag-global** | `mode=rag-global` | Map-Reduce 全局搜索（社区摘要聚合） |
| **agent** | `mode=agent` | ReAct Agent 多步推理，自主调用工具 |

## 项目规范

- **Python**: 遵循 Ruff 规则（`line-length=120`, `target-version=py311`），mypy 类型检查
- **命名**: 函数/变量 `snake_case`，类 `PascalCase`，文件 `snake_case`
- **异步**: 所有路由处理器、数据库操作、服务方法使用 `async/await`
- **API 风格**: OpenAI 兼容格式（`/chat/completions`），SSE 流式响应（`text/event-stream`）
- **Pydantic v2**: 使用 `model_validate` / `model_dump`，废弃 v1 的 `from_orm` / `dict`
- **错误处理**: 路由层用 `HTTPException`，后台任务用 `try/except` + `logger.error`，不静默吞异常
- **版本号**: 语义化版本（`MAJOR.MINOR.PATCH`），`pyproject.toml` 和 `main.py` 需同步更新
- **Git**: 主分支 `main`，功能分支 `vX.Y`，`.env` / `data/` / `__pycache__` 不入库
- **提交**: 中文描述 + 版本标签，格式 `vX.Y: 简要描述`
