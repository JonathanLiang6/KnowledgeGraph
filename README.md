# KnowledgeGraph v3.0

智能教学知识图谱管理平台 — 文档上传、知识抽取、图谱可视化、RAG 智能问答，一站式教学辅助系统。

## 核心功能

- **文档管理** — 支持 PDF / DOCX / PPTX / EPUB / Markdown / HTML / TXT 多格式上传，SHA256 去重，异步处理流水线（解析 → 实体抽取 → LLM 精炼 → 分块 → 向量化 → 索引）
- **知识图谱** — 自动构建实体-关系知识图谱，D3.js Canvas 力导向图可视化，实体关联透视
- **智能问答** — 三种检索模式（DeepSeek V4 直接问答 / RAG 向量检索 / RAG 混合检索），SSE 逐字符打字机流式输出，Markdown 渲染
- **混合检索** — LanceDB 向量检索 + BM25 关键词检索 + BGE-Reranker 重排序 + RRF 融合

## 技术栈

| 层级 | 技术 |
|------|------|
| 后端框架 | Python 3.11+ · FastAPI · Uvicorn |
| 数据库 | SQLAlchemy 2.0 (async) · SQLite (WAL) · LanceDB |
| AI / LLM | DeepSeek V4 API (OpenAI 兼容) · BAAI/bge-small-zh-v1.5 本地 Embedding · BGE-Reranker |
| 中文 NLP | jieba 分词 · TF-IDF 关键词提取 |
| 前端框架 | Vue 3 (Composition API) · Vite 5 · Element Plus |
| 可视化 | D3.js v7 · Canvas 2D 力导向图 |
| 部署 | Docker · docker-compose · Makefile |

## 快速开始

### 环境要求

- Python >= 3.11
- Node.js >= 18
- Git

### 1. 克隆项目

```bash
git clone <repo-url>
cd KnowledgeGraph
```

### 2. 后端配置

```bash
cd backend

# 创建虚拟环境
python -m venv venv
# Windows: venv\Scripts\activate
# Linux/Mac: source venv/bin/activate

# 安装依赖
pip install -r requirements.txt

# 配置 API 密钥
cp .env.example .env
# 编辑 .env，填入 DeepSeek API Key（必须）
```

### 3. 前端配置

```bash
cd frontend
npm install
```

### 4. 启动

**一键启动（Windows）：**
```bash
start.bat
```

**手动启动：**
```bash
# 终端 1: 启动后端 (端口 8013)
cd backend
uvicorn app.main:app --host 0.0.0.0 --port 8013 --reload

# 终端 2: 启动前端 (端口 3000)
cd frontend
npm run dev
```

浏览器访问 `http://localhost:3000`。

### Docker 部署

```bash
docker-compose up -d
```

## 项目结构

```
KnowledgeGraph/
├── backend/
│   ├── app/
│   │   ├── main.py                    # FastAPI 入口 + 生命周期管理
│   │   ├── api/v1/
│   │   │   ├── router.py              # 路由聚合
│   │   │   └── endpoints/             # auth, chat, document, graph, knowledge_base, monitor, settings
│   │   ├── core/                      # 配置 (config.py)、数据库 (database.py)、配色 (colors.py)
│   │   ├── models/                    # SQLAlchemy ORM: Document, KnowledgeBase, ChatHistory, SystemSetting
│   │   ├── schemas/                   # Pydantic v2 请求/响应模型
│   │   ├── services/                  # 核心业务逻辑
│   │   │   ├── rag_service.py         # RAG 流水线编排 (检索 + 上下文构建)
│   │   │   ├── deepseek_client.py     # DeepSeek V4 API 客户端 (Chat + Embedding)
│   │   │   ├── embedding_service.py   # 本地 BGE Embedding (纯 PyTorch)
│   │   │   ├── entity_extractor.py    # jieba + TF-IDF 实体抽取 (阶段一)
│   │   │   ├── llm_refiner.py         # LLM 实体精炼 (阶段二)
│   │   │   ├── extraction_service.py  # 两阶段抽取编排器
│   │   │   ├── chunking_service.py    # 语义分块 (父子块架构)
│   │   │   ├── hybrid_search.py       # LanceDB 向量 + BM25 关键词 + RRF 融合
│   │   │   ├── reranker_service.py    # BGE Cross-Encoder 重排序
│   │   │   └── char_stream.py         # 逐字符流式拆分与分类 (打字机 SSE)
│   │   ├── tasks/document_tasks.py    # 异步文档处理流水线
│   │   └── utils/                     # file_parser.py (多格式解析), helpers.py (哈希/安全)
│   ├── tests/                         # pytest 测试
│   ├── data/                          # SQLite DB + LanceDB 索引
│   ├── inputs/files/                  # 上传文件存储
│   └── prompts/                       # LLM Prompt 模板
├── frontend/
│   ├── src/
│   │   ├── views/                     # HomePage, Documents, GraphWorkspace, ChatStudio
│   │   ├── api/                       # Axios API 封装 (chat.js, document.js, graph.js, knowledgeBase.js)
│   │   ├── layouts/KBLayout.vue       # 知识库外壳布局
│   │   ├── composables/useGraphRenderer.js  # D3.js Canvas 图谱渲染引擎
│   │   ├── router/                    # Vue Router 配置
│   │   └── styles/                    # SCSS 变量 / 全局样式 / 过渡动画
│   └── vite.config.js                 # Vite 构建 + API 代理配置
├── docker-compose.yml
├── Dockerfile
├── Makefile
├── pyproject.toml                     # 项目元数据 + Ruff/Mypy 配置
└── start.bat                          # Windows 一键启动脚本
```

## API 概览

所有 API 前缀为 `/api/v1`，完整文档见 `/docs` (Swagger UI)。

### 知识库 `/api/v1/knowledge-bases`

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/` | 列出所有知识库 |
| POST | `/` | 创建知识库 |
| GET | `/{id}` | 获取知识库详情 |
| PUT | `/{id}` | 更新知识库 |
| DELETE | `/{id}` | 删除知识库（级联删除文档和文件） |

### 文档 `/api/v1/documents`

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/` | 文档列表（支持按知识库、状态筛选，分页） |
| POST | `/upload` | 上传单个文档（异步处理） |
| POST | `/upload/batch` | 批量上传（最多 20 个） |
| GET | `/check-duplicate` | SHA256 查重 |
| GET | `/stats/overview` | 文档统计 |
| GET | `/{id}` | 文档详情 |
| DELETE | `/{id}` | 删除文档（级联删除文件和搜索索引） |
| POST | `/{id}/reprocess` | 重新处理文档 |

### 智能问答 `/api/v1/chat`

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/models` | 可用检索模式：`deepseek-chat` / `rag-local` / `rag-hybrid` |
| POST | `/completions` | 聊天补全（OpenAI 兼容格式，支持 SSE 流式） |

### 图谱 `/api/v1/graph`

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/data` | 获取图谱节点和边数据 |
| GET | `/entity/{id}` | 实体详情（含关联实体和来源文档） |

### 设置 `/api/v1/settings`

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/` | 获取系统参数、可视化设置、运行状态 |
| POST | `/` | 保存系统参数 |

### 监控 `/api/v1/monitor`

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/status` | 系统运行状态 |
| GET | `/tasks` | 正在处理的文档任务列表 |
| GET | `/tasks/{id}` | 单个任务进度 |

### 健康检查

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/health` | 服务健康状态 |

## 主要配置项

所有配置通过 `backend/.env` 环境变量设置：

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `DEEPSEEK_API_KEY` | — | **必填** DeepSeek API 密钥 |
| `DEEPSEEK_API_BASE` | `https://api.deepseek.com/v1` | API 地址 |
| `DEEPSEEK_CHAT_MODEL` | `deepseek-chat` | 对话模型 |
| `EMBEDDING_MODEL` | `BAAI/bge-small-zh-v1.5` | 本地 Embedding 模型 |
| `LLM_MAX_TOKENS` | `4096` | 最大回复 Token |
| `LLM_TEMPERATURE` | `0.0` | 生成温度 |
| `CHUNK_SIZE` | `800` | 文档分块大小（字符） |
| `MAX_FILE_SIZE_MB` | `50` | 上传文件大小上限 |
| `HYBRID_SEARCH_TOP_K` | `20` | 检索返回量 |
| `MAX_ENTITIES` | `30` | 图谱最大节点数 |
| `MAX_CONCURRENT_DOCUMENT_PROCESSING` | `3` | 文档并行处理数 |
| `DATABASE_URL` | `sqlite+aiosqlite:///data/knowledge_graph.db` | 数据库连接 |

完整配置项参见 `backend/app/core/config.py`。

## 开发

```bash
# 运行测试
cd backend && pytest
npm run lint                # 前端 ESLint
ruff check backend/         # Python 代码检查
mypy backend/app/           # Python 类型检查
```

## 版本历史

| 版本 | 主要变更 |
|------|---------|
| v3.0 | 逐字符打字机 SSE 流式输出、字符级类型分类推送、项目全面清理（删除无用文件 / 死代码 / 未使用依赖） |
| v2.7 | 前端森林绿主题全面升级、深色 Hero、卡片重设计、聊天重写、SSE 流式修复 |
| v2.6 | 一键启动脚本、端口清理、后端就绪等待 |
| v2.5 | SSE 行缓冲区修复（跨 chunk 内容不再丢失） |
| v2.4 | 文件去重 (SHA256)、文档批量上传、WAL 模式、重新处理 |
| v2.3 | 混合检索 (LanceDB + BM25 + BGE-Reranker + RRF) |
| v2.2 | GraphRAG 实体扩展检索、两阶段抽取、动态查重 |
| v2.1 | PPTX/EPUB 解析、文件大小限制、MIME 白名单、流式写入 |
| v1.0 | FastAPI 重构、D3.js Canvas 图谱、智能问答 |
