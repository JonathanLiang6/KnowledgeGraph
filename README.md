# KnowledgeGraph v4.0

> 个人知识库管理平台 — 将非结构化文档转化为结构化知识图谱，提供拓扑导航、混合检索、Agent 多步推理与知识覆盖诊断。

[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?logo=python)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.109+-009688?logo=fastapi)](https://fastapi.tiangolo.com)
[![Vue](https://img.shields.io/badge/Vue-3.4-4FC08D?logo=vuedotjs)](https://vuejs.org)
[![License](https://img.shields.io/badge/license-MIT-blue)](LICENSE)

## 目录

- [功能概览](#功能概览)
- [快速开始](#快速开始)
- [架构设计](#架构设计)
- [API 参考](#api-参考)
- [配置项](#配置项)
- [开发指南](#开发指南)
- [项目结构](#项目结构)

## 功能概览

### 拓扑导航台
沉浸式"个人知识宇宙"入口。基于 D3.js 力导向图的层级知识库管理，支持自由增删节点、调整父子从属关系，单击进入知识库，右键弹出管理菜单。根节点固定于画布中央，分支节点（金色）与知识库节点（绿色）视觉区分。

### 文档管理
支持 **PDF / DOCX / PPTX / EPUB / Markdown / HTML / TXT / 图片 (JPG/PNG/WebP)** 多格式上传。上传流程经过文件类型白名单校验 → MIME 魔数检测 → SHA256 去重 → 流式写入磁盘。后台异步处理流水线包含 6 个阶段：文件解析 → 文本清洗 → 语义分块 → 实体抽取 → 向量嵌入 → 索引构建，支持断点续传与并发控制。文件按知识库名称分文件夹存储，方便人工管理。

### 知识图谱
文档上传后自动构建实体-关系知识图谱。采用**双轨存储**架构：`graph_entities` / `graph_relations` 独立表作为主力存储，`Document.graph_data` JSON 字段向后兼容。实体对齐采用同名同类型自动合并，关系去重基于 (source, target, relation_type) 三元组。图计算基于 NetworkX：支持 BFS/DFS 多跳遍历、最短路径查询、Louvain 社区检测。前端使用 D3.js Canvas 渲染，支持 1000+ 节点流畅交互。

### 智能问答

| 模式 | 说明 |
|------|------|
| **知识库问答** (rag-hybrid) | 向量检索 + BM25 + 图谱多跳 → RRF 融合 → BGE-Reranker 重排序 → LLM 生成 |
| **Agent 推理** (rag-agent) | ReAct 循环 (Thought→Action→Observation)，最多 6 步，自主调用 6 种工具 |

SSE 流式输出，Markdown 实时渲染（`requestAnimationFrame` 节流，避免逐字解析卡顿），打字机效果光标。

### Agent 工具集

| 工具 | 功能 |
|------|------|
| `vector_search` | 语义向量检索，适合模糊概念查询 |
| `graph_traverse` | 知识图谱多跳遍历，适合关系型推理 |
| `entity_lookup` | 实体详情查询，了解特定概念/人物 |
| `bm25_search` | 关键词精确匹配，适合术语查询 |
| `web_search` | 联网搜索 (DuckDuckGo)，本地不足时自动回退 |
| `analyze_coverage` | 知识覆盖诊断，识别强项与薄弱领域 |

### 记忆系统（kb_id 隔离）

| 层级 | 存储 | 生命周期 | 隔离策略 |
|------|------|----------|----------|
| 工作记忆 | 内存列表 | 单次 Agent 调用 | `{kb_id}::{session_id}` |
| 情景记忆 | 内存字典 | 单次会话 (TTL 30min) | 同上 |
| 语义记忆 | GraphEntity/GraphRelation 表 | 跨会话持久化 | `kb_id` 列 |

### 知识覆盖诊断
基于内置的 100+ 关键词→分类映射表，将实体归类到 15 个领域（编程语言、深度学习、机器学习、NLP、计算机视觉、数据库等）。前端使用 **ECharts Treemap** 矩形树图渲染：方块面积 = 实体数量，颜色深浅 = 最后更新时间（红色 = 超过 30 天未更新）。

### 联网搜索 (Q8)
Agent 模式下可开启联网搜索开关。系统 Prompt 注入两条硬性规则：
- **置信度回退**：本地检索最高相似度 < 0.6 且知识库无相关内容 → 自动调用 `web_search`
- **时效触发**：问题含"今天""最新""2026""新闻"等关键词 → 优先联网
- 联网内容仅注入当前工作记忆，严禁自动写入长期向量库

### 图像感知 (Q3)
上传图片自动提取文字与语义信息：**PaddleOCR** 识别中文文字区域，**BLIP** (Salesforce) 生成英文内容摘要。结果为 `[OCR文字]：{text}。[图片描述]：{caption}` 的拼接文本，复用现有分块与向量化流水线。

## 快速开始

### 环境要求

- **Python** >= 3.11
- **Node.js** >= 18
- **Windows** / Linux / macOS

### 1. 后端

```bash
cd backend

# 虚拟环境
python -m venv venv
venv\Scripts\activate          # Windows
# source venv/bin/activate     # Linux/macOS

# 安装依赖
pip install -r requirements.txt

# 配置 API 密钥
cp .env.example .env
# 编辑 .env，至少填入 DEEPSEEK_API_KEY
```

### 2. 前端

```bash
cd frontend
npm install
```

### 3. 启动

**Windows 一键启动：**
```bash
start.bat
```

**手动启动：**
```bash
# 终端 1 — 后端 (端口 8013)
cd backend
uvicorn app.main:app --host 0.0.0.0 --port 8013 --reload

# 终端 2 — 前端 (端口 3000)
cd frontend
npm run dev
```

浏览器访问 **http://localhost:3000**。API 文档见 **http://localhost:8013/docs** (Swagger UI)。

### Docker

```bash
docker-compose up -d
```

## 架构设计

### 检索融合 (RRF)

```
用户查询
  ├── 向量检索 (LanceDB, W=0.7)      ─┐
  ├── BM25 关键词检索 (W=0.3)         ─┤
  └── 图谱多跳检索 (W=0.3)            ─┘
                  ↓
           RRF 融合排序
                  ↓
        BGE Cross-Encoder 重排序
                  ↓
             最终结果集 (Top K)
```

### Agent 推理循环

```
User Query → [Planner / Thought]
                  ↓
            [Tool Selector]
                  ↓
            [Tool Executor] → Observation
                  ↓                    ↑
            [Reflector] ─── 信息不足 ──┘
                  ↓ (信息充分)
            [Final Answer]
```

### 文档处理流水线

```
Upload → Validate → Parse → Clean → Chunk → Extract → Embed → Index
  │        │         │       │       │        │        │       │
  │        │     PDF/DOCX   HTML   语义分块  jieba+TF-IDF  BGE   LanceDB
  │        │     PPTX/EPUB  去标签  父子块   LLM精炼
  │        │     MD/TXT/IMG  规范化
  │        │
  │    MIME魔数检测
  │    扩展名白名单
  │    大小限制 (50MB)
  │
  SHA256去重
  流式写盘
```

## API 参考

所有接口前缀 `/api/v1`，完整文档见 `/docs`。

### 知识库

| 方法 | 路径 | 说明 |
|------|------|------|
| `GET` | `/knowledge-bases` | 列表（含文档数聚合） |
| `POST` | `/knowledge-bases` | 创建 |
| `GET` | `/knowledge-bases/{id}` | 详情 |
| `PUT` | `/knowledge-bases/{id}` | 更新 |
| `DELETE` | `/knowledge-bases/{id}` | 删除（级联：文档 + 文件 + 索引） |

### 文档

| 方法 | 路径 | 说明 |
|------|------|------|
| `GET` | `/documents` | 列表（支持 kb_id/status 筛选、分页） |
| `POST` | `/documents/upload` | 上传单个文档（异步处理） |
| `POST` | `/documents/upload/batch` | 批量上传（≤20 个） |
| `GET` | `/documents/check-duplicate` | SHA256 查重 |
| `GET` | `/documents/stats/overview` | 统计概览 |
| `GET` | `/documents/{id}` | 详情 |
| `DELETE` | `/documents/{id}` | 删除 |
| `POST` | `/documents/{id}/reprocess` | 重新处理 |

### 问答

| 方法 | 路径 | 说明 |
|------|------|------|
| `GET` | `/chat/models` | 可用模式列表 |
| `POST` | `/chat/completions` | 聊天补全（OpenAI 兼容，SSE 流式） |
| `GET` | `/chat/agent/clear` | 清除 Agent 会话记忆 |

请求体示例：

```json
{
  "model": "rag-agent",
  "messages": [{"role": "user", "content": "什么是ReAct Agent？"}],
  "kb_id": "767a2ae6-...",
  "stream": true,
  "enable_web": false
}
```

### 图谱

| 方法 | 路径 | 说明 |
|------|------|------|
| `GET` | `/graph/data` | 图谱数据（节点 + 边 + 图例） |
| `GET` | `/graph/stats` | 统计（节点数、边数、密度、社区数） |
| `GET` | `/graph/entity/{id}` | 实体详情 |
| `GET` | `/graph/entity/{id}/neighbors` | 邻居子图（BFS，1-3 跳） |
| `GET` | `/graph/paths` | 两实体间路径查询 |
| `GET` | `/graph/communities` | Louvain 社区检测 |
| `GET` | `/graph/communities/{id}` | 社区详情 |
| `POST` | `/graph/cleanup-orphans` | 清理孤立节点 |

### 拓扑导航

| 方法 | 路径 | 说明 |
|------|------|------|
| `GET` | `/topology` | 全量节点 + 边 |
| `POST` | `/topology/nodes` | 创建节点 |
| `PUT` | `/topology/nodes/{id}` | 更新节点（名称/图标/kb_id/坐标） |
| `DELETE` | `/topology/nodes/{id}` | 删除节点（不级联删 KB） |
| `POST` | `/topology/edges` | 创建连接 |
| `DELETE` | `/topology/edges/{id}` | 删除连接 |

### 分析 & 监控

| 方法 | 路径 | 说明 |
|------|------|------|
| `GET` | `/analytics/kb/{kb_id}/coverage` | 知识覆盖分析 |
| `GET` | `/monitor/status` | 系统运行状态 |
| `GET` | `/monitor/tasks` | 处理任务列表 |
| `GET` | `/health` | 健康检查 |

## 配置项

所有配置通过 `backend/.env` 环境变量设置，模板见 `.env.example`。

### 核心配置

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `DEEPSEEK_API_KEY` | — | **必填** DeepSeek API 密钥 |
| `DEEPSEEK_API_BASE` | `https://api.deepseek.com/v1` | API 地址 |
| `DEEPSEEK_CHAT_MODEL` | `deepseek-chat` | 对话模型 |

### 嵌入与检索

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `EMBEDDING_MODEL` | `BAAI/bge-small-zh-v1.5` | 本地 Embedding 模型 |
| `EMBEDDING_DIM` | `512` | 向量维度 |
| `RERANKER_MODEL` | `BAAI/bge-reranker-base` | 重排序模型 |
| `HYBRID_SEARCH_TOP_K` | `20` | 检索返回数量 |
| `RERANK_TOP_K` | `5` | 重排序保留数量 |
| `VECTOR_WEIGHT` | `0.7` | RRF 向量权重 |
| `BM25_WEIGHT` | `0.3` | RRF BM25 权重 |

### 文档处理

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `CHUNK_SIZE` | `800` | 分块大小（字符） |
| `CHUNK_OVERLAP` | `100` | 分块重叠量 |
| `MAX_FILE_SIZE_MB` | `50` | 上传上限 |
| `MAX_CONCURRENT_DOC_PROCESSING` | `3` | 并行处理数 |
| `DOC_PROCESSING_TIMEOUT` | `30` | 单文档超时（分钟） |

### Agent 与图谱

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `AGENT_MAX_STEPS` | `6` | Agent 最大推理步数 |
| `AGENT_TEMPERATURE` | `0.3` | Agent LLM 温度 |
| `GRAPH_TRAVERSAL_MAX_HOPS` | `3` | 图遍历最大跳数 |
| `GRAPH_TRAVERSAL_MAX_NODES` | `50` | 图遍历最大节点数 |
| `GRAPH_COMMUNITY_MIN_SIZE` | `3` | 最小社区规模 |

> 完整配置项见 `backend/app/core/config.py`。

## 开发指南

### 项目结构

```
KnowledgeGraph/
├── start.bat                          # Windows 一键启动
├── Makefile                           # dev / test / format / clean
├── Dockerfile                         # python:3.11-slim 多阶段构建
├── docker-compose.yml                 # backend:8013 + frontend:3000
├── pyproject.toml                     # Ruff / pytest 配置
│
├── backend/
│   ├── .env.example                   # 环境变量模板
│   ├── requirements.txt               # Python 依赖
│   ├── deploy_docs.py                 # 示例文档部署脚本
│   ├── setup_sample_data.py           # 示例数据初始化
│   ├── data/                          # SQLite + LanceDB 索引（不入库）
│   ├── inputs/files/                  # 上传文件（按 KB 名称分目录）
│   │   ├── 初中化学/
│   │   ├── 大学化学/
│   │   ├── AI Agent/
│   │   └── RAG/
│   ├── tests/                         # pytest (asyncio_mode=auto)
│   └── app/
│       ├── main.py                    # FastAPI 入口 · lifespan · CORS · 版本 3.2.0
│       ├── api/v1/
│       │   ├── router.py              # 路由聚合
│       │   └── endpoints/
│       │       ├── chat.py            # 问答：SSE 流式 + Agent 推理 + 联网搜索
│       │       ├── document.py        # 文档：上传/列表/去重/重新处理/删除
│       │       ├── graph.py           # 图谱：实体/关系/路径/邻居/社区/统计/清理
│       │       ├── knowledge_base.py  # 知识库：CRUD + 级联删除
│       │       ├── topology.py        # 拓扑：节点 CRUD + 边管理 + 重复根节点清理
│       │       ├── analytics.py       # 分析：知识覆盖诊断
│       │       ├── settings.py        # 系统设置读写
│       │       └── monitor.py         # 监控：健康状态/任务列表/处理进度
│       ├── core/
│       │   ├── config.py              # 全部配置从 .env 读取，安全回退
│       │   ├── database.py            # 异步 SQLAlchemy 引擎 + SQLite WAL + get_db 注入
│       │   └── colors.py              # 20+ 实体类型配色映射
│       ├── models/                    # ORM (SQLAlchemy 2.0 Mapped)
│       │   ├── knowledge_base.py      # KnowledgeBase
│       │   ├── document.py            # Document + DocumentStatus 枚举
│       │   ├── graph_entity.py        # GraphEntity + GraphRelation
│       │   ├── topology.py            # TopologyNode + TopologyEdge
│       │   └── system_setting.py      # SystemSetting (key-value)
│       ├── schemas/                   # Pydantic v2 请求/响应模型
│       ├── services/                  # 核心业务逻辑
│       │   ├── rag_service.py         # RAG 编排：索引构建/混合搜索/全局搜索/上下文构建
│       │   ├── hybrid_search.py       # LanceDB 向量 + BM25 关键词 → RRF 融合
│       │   ├── embedding_service.py   # BGE 本地嵌入
│       │   ├── reranker_service.py    # BGE Cross-Encoder 重排序
│       │   ├── chunking_service.py    # 语义分块（父子块策略）
│       │   ├── deepseek_client.py     # DeepSeek API 客户端
│       │   ├── char_stream.py         # 逐字符 SSE 流式拆分
│       │   ├── entity_extractor.py    # jieba + TF-IDF 实体抽取
│       │   ├── llm_refiner.py         # LLM 实体精炼
│       │   ├── extraction_service.py  # 两阶段抽取编排
│       │   ├── graph_service.py       # 图构建/BFS/DFS/最短路径/Louvain/孤立节点清理
│       │   ├── graph_retriever.py     # 多跳图检索器
│       │   ├── agent_service.py       # ReAct Agent 循环 (Thought→Action→Observation, ≤6步)
│       │   ├── memory_service.py      # 三层记忆：Working/Episodic/Semantic
│       │   ├── analytics_service.py   # 知识覆盖分析（100+ 关键词映射）
│       │   └── tools/                 # Agent 工具集（标准化 async 接口）
│       │       ├── __init__.py        # TOOL_REGISTRY + get_tools_description(enable_web)
│       │       ├── vector_search.py   # 语义向量检索
│       │       ├── graph_traverse.py  # 知识图谱多跳遍历
│       │       ├── entity_lookup.py   # 实体详情查询
│       │       ├── bm25_search.py     # 关键词精确匹配
│       │       ├── web_search.py      # DuckDuckGo 联网搜索
│       │       └── analyze_coverage.py # 知识覆盖诊断
│       ├── tasks/
│       │   └── document_tasks.py      # 异步文档处理流水线（6阶段）
│       └── utils/
│           ├── file_parser.py         # 多格式解析：PDF/DOCX/PPTX/EPUB/图片(OCR+Caption)
│           └── helpers.py             # 哈希/编码检测/MIME 检测/流式保存
│
└── frontend/
    ├── index.html
    ├── vite.config.js                 # 端口 3000，代理 /api → localhost:8013
    ├── public/brain.svg               # 首页大脑图标
    └── src/
        ├── main.js                    # Vue 入口
        ├── App.vue
        ├── router/index.js            # / → TopologyView, /kb/:id → KBLayout
        ├── api/                       # Axios 封装
        │   ├── index.js               # 基础实例 + 拦截器
        │   ├── chat.js                # 聊天 API (SSE 流式)
        │   ├── document.js            # 文档 CRUD
        │   ├── graph.js               # 图谱数据
        │   ├── knowledgeBase.js       # 知识库 CRUD
        │   └── topology.js            # 拓扑导航 CRUD
        ├── composables/
        │   ├── useTopologyRenderer.js # D3 力导向图 Canvas 渲染 (v3.2)
        │   └── useGraphRenderer.js    # D3 Canvas 图谱渲染
        ├── layouts/KBLayout.vue       # 知识库布局外壳 + 知识体检弹窗
        ├── views/
        │   ├── TopologyView.vue       # 拓扑导航启动台 (v3.2)
        │   ├── Documents.vue          # 文档管理
        │   ├── GraphWorkspace.vue     # 图谱可视化工作台
        │   └── ChatStudio.vue         # 问答工作室 (流式 MD 渲染 + 联网开关)
        └── styles/                    # SCSS 变量/全局样式/过渡动画
```

### 常用命令

```bash
# 测试
cd backend && pytest

# 清理
make clean         # 清理所有缓存

# 前端
cd frontend && npm run build
```

### 编码规范

- **Python**：Ruff (`line-length=120`, `target-version=py311`)，`snake_case` 命名
- **异步**：所有路由、数据库操作、服务方法使用 `async/await`
- **Pydantic v2**：`model_validate` / `model_dump`，废弃 v1 API
- **API**：OpenAI 兼容格式，SSE `text/event-stream` 流式响应
- **前端**：Vue 3 Composition API，SCSS 森林绿主题
- **Git**：`main` 分支，功能分支 `vX.Y`，`.env` / `data/` / `__pycache__` 不入库

## 版本历史

| 版本 | 主要变更 |
|------|---------|
| **v4.0** | 拓扑导航台 (D3力导向图+层级管理)、Agent联网搜索、多模态图像处理、知识覆盖诊断、文件按KB名称分目录、流式Markdown实时渲染、kb_id全链路隔离、.gitignore优化 |
| v3.1 | Agent工作记忆接入、RRF融合统一、N+1批量查询、BFS去重、全局搜索并发化、会话TTL、Docker多阶段构建 |
| v2.7 | 前端森林绿主题升级、深色Hero、SSE流式修复 |
| v2.5 | SSE行缓冲区修复 |
| v2.4 | SHA256去重、批量上传、WAL模式 |
| v2.3 | 混合检索 (LanceDB+BM25+BGE-Reranker+RRF) |
| v2.2 | GraphRAG实体扩展检索、两阶段抽取 |
| v1.0 | FastAPI重构、D3.js Canvas图谱、智能问答 |
