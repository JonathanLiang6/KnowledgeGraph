# KnowledgeGraph

基于 **DeepSeek V4 + GraphRAG + Hybrid RAG** 的企业级知识图谱智能问答系统。

将非结构化文档自动转换为结构化知识图谱，通过自然语言交互进行智能问答，支持图谱可视化探索。

> 当前版本：**v2.4**

---

## 技术栈

| 层级 | 技术 | 说明 |
|------|------|------|
| **后端框架** | FastAPI + Uvicorn | Python 3.11+ 异步 Web |
| **LLM** | DeepSeek V4 (OpenAI 兼容 API) | 推理、实体提取、精炼 |
| **嵌入模型** | BAAI/bge-small-zh-v1.5 | 本地向量化，512 维 |
| **重排序** | BAAI/bge-reranker-base | 本地 Cross-Encoder 重排 |
| **向量库** | LanceDB | 嵌入式向量存储与检索 |
| **稀疏检索** | BM25 (rank-bm25) | 关键词并行检索 |
| **知识图谱** | Microsoft GraphRAG | 实体/关系提取、社区报告 |
| **数据库** | SQLAlchemy 2.0 + SQLite | 异步 ORM，WAL 模式 |
| **NLP** | jieba + spaCy | 中文分词、NER |
| **文档解析** | pypdf / python-docx / python-pptx | PDF、Word、PPT 解析 |
| **前端** | Vue 3 + Vite + Element Plus | SPA 管理后台 |
| **图谱渲染** | D3.js (Canvas) | 大规模节点力导向布局 |
| **状态管理** | Pinia | Vue 3 状态管理 |

---

## 核心特性

### 混合 RAG 检索
- **双路并行检索** — 向量语义检索 (LanceDB) + BM25 关键词检索，可配置权重
- **重排序** — 本地 BGE-Reranker 对候选块二次打分过滤
- **父子块架构** — 子块向量索引，检索后还原完整父块上下文

### 知识图谱
- **两阶段实体提取** — NLP 粗筛 (jieba/spaCy) → LLM 精炼 (DeepSeek)
- **关系抽取** — 自动识别 9 种语义关系（因果、包含、依赖等）
- **GraphRAG 集成** — 社区报告生成，支持本地/全局/综合搜索
- **Canvas 可视化** — D3.js + Canvas，支持 4 种布局，流畅交互

### 文档管理
- **多格式支持** — PDF、DOCX、PPTX、TXT、Markdown、EPUB
- **异步流水线** — 上传 → 解析 → 分块 → 提取 → 索引，后台任务执行
- **进度追踪** — 实时轮询处理状态（解析中 / NLP 粗筛 / LLM 提取 / 索引中）
- **SHA256 去重** — 数据库级文件哈希去重

### 对话问答
- **SSE 流式输出** — 打字机效果，Markdown 渲染 + 代码高亮
- **多模式** — GraphRAG 本地/全局/混合搜索 + 直接 LLM
- **引用溯源** — 回答附带来源分块引用
- **持久化历史** — SQLite 存储多轮对话

---

## 快速开始

### 环境要求

- Python 3.11+
- Node.js 18+
- 4GB+ 内存

### 1. 配置环境变量

```bash
cp backend/.env.example backend/.env
```

编辑 `backend/.env`，填入 DeepSeek API Key：

```env
DEEPSEEK_API_KEY=sk-your-deepseek-api-key
DEEPSEEK_API_BASE=https://api.deepseek.com/v1
DEEPSEEK_CHAT_MODEL=deepseek-chat
```

### 2. 安装依赖

```bash
make install
```

### 3. 启动

```bash
make dev
```

### 4. 访问

| 服务 | 地址 |
|------|------|
| 前端界面 | http://localhost:5173 |
| 后端 API | http://localhost:8013 |
| Swagger 文档 | http://localhost:8013/docs |

---

## Docker 部署

```bash
docker-compose up -d
```

| 容器 | 端口 |
|------|------|
| `kg-backend` | 8013 |
| `kg-frontend` | 5173 |

---

## API 概览

所有 API 前缀：`/api/v1`

| 模块 | 端点 | 说明 |
|------|------|------|
| **Chat** | `POST /chat/completions` | 问答（支持 SSE 流式） |
| | `GET /chat/history/{kb_id}` | 对话历史 |
| | `DELETE /chat/history/{kb_id}` | 清除历史 |
| **Knowledge Base** | `GET /knowledge-bases` | 知识库列表 |
| | `POST /knowledge-bases` | 创建知识库 |
| | `PUT /knowledge-bases/{id}` | 更新知识库 |
| | `DELETE /knowledge-bases/{id}` | 删除知识库 |
| **Document** | `GET /documents` | 文档列表 |
| | `POST /documents/upload` | 上传文档 |
| | `POST /documents/{id}/process` | 异步处理文档 |
| | `DELETE /documents/{id}` | 删除文档 |
| | `GET /documents/{id}/chunks` | 文档分块预览 |
| **Graph** | `GET /graph/data` | 图谱数据（节点+边） |
| | `GET /graph/entity/{id}` | 实体详情 |
| **Settings** | `GET /settings` | 系统设置 |
| | `PUT /settings` | 更新设置 |
| **Monitor** | `GET /monitor/tasks` | 任务队列状态 |
| | `GET /monitor/stats` | 系统统计 |

另有兼容端点：`/health`（健康检查）、`/api/overview`、`/api/settings`。

---

## 项目结构

```
KnowledgeGraph/
├── backend/
│   ├── app/
│   │   ├── main.py                 # FastAPI 应用入口 (lifespan)
│   │   ├── api/v1/
│   │   │   ├── router.py           # 路由聚合
│   │   │   └── endpoints/          # chat, document, graph, knowledge_base, settings, monitor, auth
│   │   ├── core/                   # config, database, colors
│   │   ├── models/                 # SQLAlchemy 模型
│   │   ├── schemas/                # Pydantic 请求/响应 Schema
│   │   ├── services/               # chunking, deepseek, embedding, entity_extractor,
│   │   │                           #   extraction, hybrid_search, llm_refiner, rag, reranker
│   │   ├── tasks/                  # document_tasks (异步处理流水线)
│   │   └── utils/                  # file_parser, helpers
│   ├── prompts/                    # LLM 提示词模板
│   ├── tests/                      # 后端测试
│   ├── .env.example
│   ├── requirements.txt
│   └── settings.yaml               # GraphRAG 配置
├── frontend/
│   ├── src/
│   │   ├── api/                    # API 调用模块
│   │   ├── composables/            # 组合式函数 (useGraphRenderer)
│   │   ├── layouts/                # KBLayout 布局
│   │   ├── router/                 # Vue Router 配置
│   │   ├── stores/                 # Pinia 状态
│   │   ├── styles/                 # SCSS 样式
│   │   └── views/                  # HomePage, ChatStudio, GraphWorkspace, Documents
│   └── package.json
├── docker-compose.yml
├── Dockerfile
├── Makefile
├── pyproject.toml
└── README.md
```

---

## Makefile 命令

| 命令 | 说明 |
|------|------|
| `make install` | 安装前后端依赖 |
| `make dev` | 并行启动前后端开发服务 |
| `make dev-backend` | 仅启动后端 (8013) |
| `make test` | 运行后端测试 (pytest) |
| `make lint` | 代码检查 (ruff) |
| `make clean` | 清理 `__pycache__` 等缓存 |
