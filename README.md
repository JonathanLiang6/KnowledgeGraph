# KnowledgeGraph v3.0

**教学知识图谱智能问答系统** — 文档解析 · 实体抽取 · 图谱可视化 · 流式问答

将非结构化教学文档自动构建为结构化知识图谱，通过 Canvas 力导向图探索实体关系，基于 GraphRAG + 混合检索实现智能问答。

---

## 界面预览

| 页面 | 说明 |
|------|------|
| **首页** | 深色森林 Hero · 知识库卡片网格 · 统计面板 |
| **知识图谱** | D3.js Canvas 力导向布局 · 类型筛选 · 关联跳转 |
| **智能问答** | SSE 流式输出 · 多模式检索 · Markdown 渲染 |
| **文档管理** | 批量上传 · 进度追踪 · 状态筛选 |

> 配色方案：**森林绿主题** (`#2D8C4E`) — 参考 Material Design 3 + Linear 设计语言

---

## 技术栈

| 层 | 技术 |
|----|------|
| **后端** | FastAPI + Uvicorn (Python 3.11+) |
| **前端** | Vue 3 + Vite 5 + Element Plus 2.5 |
| **图谱** | D3.js v7 (Canvas 2D) |
| **LLM** | DeepSeek V4 (OpenAI 兼容) |
| **嵌入** | BAAI/bge-small-zh-v1.5 (512d) |
| **重排序** | BAAI/bge-reranker-base |
| **向量库** | LanceDB |
| **稀疏检索** | BM25 (rank-bm25) |
| **数据库** | SQLAlchemy 2.0 + SQLite (WAL) |
| **NLP** | jieba + spaCy |

---

## 快速开始

### 前置要求

- Python 3.11+
- Node.js 18+
- DeepSeek API Key

### 1. 配置

```bash
cp backend/.env.example backend/.env
# 编辑 backend/.env，填入 DEEPSEEK_API_KEY
```

### 2. 安装

```bash
# 后端
cd backend && pip install -r requirements.txt

# 前端
cd frontend && npm install
```

### 3. 一键启动

```bash
# Windows: 双击 start.bat
# 自动清理端口 -> 启动后端(8013) -> 等待就绪 -> 启动前端(3000)
# 关闭前端窗口后自动停止后端
```

或手动启动：

```bash
# 终端1: 后端
cd backend && uvicorn app.main:app --host 0.0.0.0 --port 8013 --reload

# 终端2: 前端
cd frontend && npm run dev
```

### 4. 访问

| 服务 | 地址 |
|------|------|
| 前端 | http://localhost:3000 |
| API 文档 | http://localhost:8013/docs |
| ReDoc | http://localhost:8013/redoc |

---

## 核心特性

### 混合 RAG 检索
- 向量语义 + BM25 关键词并行检索
- BGE-Reranker 重排序
- 父子块架构：子块索引 -> 父块还原完整上下文

### 知识图谱
- 两阶段实体提取：NLP 粗筛 -> LLM 精炼
- 9 种语义关系自动识别
- Canvas 力导向可视化，支持缩放/拖拽/节点点击
- 类型筛选 + 虚线桥接关联

### 文档处理
- PDF / DOCX / PPTX / TXT / Markdown / EPUB
- 异步流水线：上传 -> 解析 -> 分块 -> 提取 -> 索引
- 实时进度追踪
- SHA256 去重

### 流式问答
- SSE 流式输出（行缓冲防截断）
- 多模式：混合检索 / 向量检索 / 直接问答
- 按知识库独立保存对话历史
- Markdown 渲染 + 代码块展示

---

## API 概览

基础路径: `/api/v1`

| 模块 | 端点 | 说明 |
|------|------|------|
| **Chat** | `POST /chat/completions` | 问答 (支持 SSE stream=true) |
| **Knowledge Base** | `GET/POST /knowledge-bases` | 列表 / 创建 |
| | `GET/PUT/DELETE /knowledge-bases/{id}` | 详情 / 更新 / 删除 |
| **Document** | `GET /documents` | 文档列表 |
| | `POST /documents/upload` | 上传 |
| | `DELETE /documents/{id}` | 删除 |
| | `GET /documents/stats/overview` | 统计 |
| **Graph** | `GET /graph/data` | 图谱节点+边 |
| | `GET /graph/entity/{id}` | 实体详情 |
| **Settings** | `GET/PUT /settings` | 系统设置 |
| **Monitor** | `GET /monitor/tasks` | 任务状态 |
| | `GET /monitor/stats` | 系统统计 |

---

## Docker

```bash
docker-compose up -d
# 后端 :8013  /  前端 :5173
```

---

## 项目结构

```
KnowledgeGraph/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI 入口
│   │   ├── api/v1/endpoints/    # chat, document, graph, kb, settings, monitor
│   │   ├── core/                # config, database, colors
│   │   ├── models/              # SQLAlchemy 模型
│   │   ├── schemas/             # Pydantic Schema
│   │   ├── services/            # deepseek, embedding, hybrid_search, rag, reranker
│   │   ├── tasks/               # document_tasks (异步流水线)
│   │   └── utils/               # file_parser, helpers
│   ├── prompts/                 # LLM 提示词
│   ├── tests/                   # pytest
│   ├── requirements.txt
│   └── .env.example
├── frontend/
│   ├── src/
│   │   ├── api/                 # Axios 接口封装
│   │   ├── composables/         # useGraphRenderer (D3 Canvas)
│   │   ├── layouts/             # KBLayout
│   │   ├── router/              # Vue Router
│   │   ├── stores/              # Pinia
│   │   ├── styles/              # variables / global / transitions (SCSS)
│   │   └── views/               # HomePage / ChatStudio / GraphWorkspace / Documents
│   ├── index.html
│   ├── vite.config.js
│   └── package.json
├── start.bat                    # 一键启动脚本 (Windows)
├── start.sh                     # 一键启动脚本 (Linux/macOS)
├── docker-compose.yml
├── Dockerfile
├── Makefile
├── pyproject.toml
└── README.md
```

---

## 版本历史

| 版本 | 内容 |
|------|------|
| **v3.0** | 项目整理 · 完整 README · .gitignore 完善 · 清理冗余文件 |
| **v2.7** | 前端森林绿主题全面升级 · SSE 流式行缓冲修复 · Element Plus 绿色主题 |
| **v2.6** | 一键启动脚本 (start.bat) · 端口自动清理 · 后端就绪等待 |
| **v2.5** | 前端动效增强 · 深色 Hero · 卡片重设计 · 聊天逻辑重写 |
| **v2.4** | 项目整理 · Bug 修复 · 数据库迁移 |
| **v2.3** | 混合检索 + 重排序实现 |
| **v2.2** | GraphRAG 集成 · Canvas 图谱增强 |
| **v2.1** | RAG 管道稳定版 |
| **v2.0** | 知识库中心化重构 |

---

## License

MIT
