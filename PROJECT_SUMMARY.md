# KnowledgeGraph 项目完整总结

---

## 一、项目概述

**KnowledgeGraph** 是一个基于 **GraphRAG（微软图检索增强生成）** 和 **智谱AI大语言模型** 构建的知识图谱智能问答系统。该系统提供文档管理、知识图谱可视化和智能问答三大核心功能，旨在帮助用户更好地理解和利用文档中的知识。

**项目定位**：将非结构化文档转换为结构化知识图谱，并通过自然语言交互进行智能问答。

---

## 二、技术架构

### 2.1 技术栈

| 层级 | 技术 | 版本要求 | 说明 |
|------|------|----------|------|
| **后端框架** | FastAPI + uvicorn | Python 3.10-3.12 | 高性能异步Web框架 |
| **知识图谱** | GraphRAG | 最新 | 微软图检索增强生成框架 |
| **向量数据库** | LanceDB | 最新 | 嵌入向量存储与检索 |
| **AI模型** | 智谱AI (GLM-4-Flash) | API调用 | 国产大语言模型 |
| **NLP处理** | jieba / NLTK / spaCy | 最新 | 中文分词和NLP处理 |
| **文档解析** | PyPDF2 / python-docx | 最新 | PDF和Word文档解析 |
| **前端框架** | Vue 3 | 3.x | 渐进式JavaScript框架 |
| **UI组件库** | Element Plus | 最新 | Vue 3 UI组件库 |
| **状态管理** | Pinia | 最新 | Vue 3状态管理 |
| **图谱可视化** | D3.js + ECharts | 最新 | 数据驱动绘图 |
| **Markdown渲染** | marked + highlight.js | 最新 | Markdown解析和代码高亮 |
| **构建工具** | Vite | 6.x | 现代前端构建工具 |

### 2.2 系统架构图

```
┌─────────────────────────────────────────────────────────────────┐
│                         前端 (Vue 3 + Vite)                      │
│  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌───────┐ │
│  │  Home   │  │  Chat   │  │ Graph   │  │Documents│  │Settings│ │
│  └────┬────┘  └────┬────┘  └────┬────┘  └────┬────┘  └───┬───┘ │
└───────┼─────────────┼───────────┼─────────────┼─────────────┼──────┘
        │             │           │             │             │
        └──────────────┴───────────┴─────────────┴─────────────┘
                                 │
                    ┌────────────┴────────────┐
                    │    HTTP API (REST)     │
                    │  http://localhost:8012  │
                    └────────────┬────────────┘
                                 │
┌────────────────────────────────┴────────────────────────────────┐
│                         后端 (FastAPI + Python)                  │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │                    FastAPI 应用                          │   │
│  │  ┌────────────┐  ┌────────────┐  ┌────────────────┐    │   │
│  │  │ /v1/chat   │  │ /api/      │  │ /api/documents │    │   │
│  │  │ completions│  │ graph/data │  │ /upload        │    │   │
│  │  └────────────┘  └────────────┘  └────────────────┘    │   │
│  └──────────────────────────────────────────────────────────┘   │
│  ┌─────────────────┐  ┌─────────────────┐  ┌──────────────┐   │
│  │ GraphRAG 查询   │  │ 实体提取器      │  │ 智谱AI API   │   │
│  │ - local_search  │  │ EntityExtractor │  │ 调用模块     │   │
│  │ - global_search │  │ - jieba分词    │  │              │   │
│  │ - full_search   │  │ - 关系抽取     │  │              │   │
│  └─────────────────┘  └─────────────────┘  └──────────────┘   │
└─────────────────────────────────────────────────────────────────┘
                                 │
                    ┌────────────┴────────────┐
                    │        数据存储         │
                    │  ┌────────┐  ┌───────┐ │
                    │  │Parquet │  │ JSON  │ │
                    │  │ 文件   │  │ 文件  │ │
                    │  └────────┘  └───────┘ │
                    │  ┌────────────────────┐ │
                    │  │ LLM 响应缓存      │ │
                    │  └────────────────────┘ │
                    └─────────────────────────┘
```

---

## 三、目录结构详解

```
KnowledgeGraph/
├── backend/                              # 后端代码根目录
│   ├── cache/                           # LLM API调用缓存
│   │   ├── claim_extraction/            # 声明提取缓存
│   │   ├── community_reporting/         # 社区报告缓存
│   │   ├── entity_extraction/           # 实体提取缓存
│   │   ├── summarize_descriptions/      # 描述摘要缓存
│   │   └── text_embedding/              # 文本嵌入缓存
│   ├── data/                            # 持久化数据存储
│   │   ├── documents.json               # 文档索引数据
│   │   └── settings.json                # 系统配置数据
│   ├── inputs/                          # 输入数据目录
│   │   ├── artifacts/                   # GraphRAG生成的Parquet数据
│   │   │   └── stats.json               # 统计数据
│   │   ├── files/                       # 用户上传的源文件
│   │   │   └── 复分解反应.md             # 示例文档
│   │   └── reports/                     # 系统运行日志
│   │       └── logs.json
│   ├── prompts/                         # LLM提示词模板
│   │   ├── claim_extraction.txt         # 声明提取提示词
│   │   ├── community_report.txt         # 社区报告生成提示词
│   │   ├── entity_extraction.txt        # 实体提取提示词
│   │   └── summarize_descriptions.txt   # 描述摘要提示词
│   ├── utils/                           # 核心工具模块
│   │   ├── __init__.py
│   │   ├── config.py                    # 配置管理（读取.env）
│   │   ├── entity_extractor.py          # 实体与关系提取核心逻辑
│   │   ├── helpers.py                   # 通用工具函数
│   │   └── main.py                      # FastAPI主应用（核心入口）
│   ├── venv/                            # Python虚拟环境
│   ├── .env.example                     # 环境变量示例文件
│   ├── requirements.txt                 # Python依赖列表
│   ├── settings.yaml                    # GraphRAG配置文件
│   └── start_server.py                  # 服务启动脚本
│
├── frontend/                            # 前端代码根目录
│   ├── src/
│   │   ├── router/
│   │   │   └── index.js                 # Vue Router路由配置
│   │   ├── styles/
│   │   │   └── index.scss               # 全局样式
│   │   ├── views/                       # 页面组件
│   │   │   ├── Home.vue                 # 首页（系统概览）
│   │   │   ├── Chat.vue                 # 智能问答页面
│   │   │   ├── Graph.vue                # 图谱可视化页面
│   │   │   ├── Documents.vue            # 文档管理页面
│   │   │   └── Settings.vue             # 系统设置页面
│   │   ├── App.vue                      # 根组件（布局+导航）
│   │   └── main.js                      # 前端入口文件
│   ├── index.html                       # HTML模板
│   ├── package.json                     # 前端依赖配置
│   ├── vite.config.js                   # Vite构建配置
│   └── .eslintrc.cjs                    # ESLint代码检查配置
│
└── PROJECT_SUMMARY.md                   # 项目总结文档（本文件）
```

---

## 四、核心模块详解

### 4.1 后端核心模块

#### 4.1.1 `utils/main.py` - FastAPI主应用

这是后端的核心文件，包含所有API端点定义：

**主要API端点：**

| 端点 | HTTP方法 | 功能描述 |
|------|----------|----------|
| `/v1/chat/completions` | POST | 知识问答（支持多种搜索模式） |
| `/v1/models` | GET | 获取可用模型列表 |
| `/api/graph/data` | GET | 获取图谱数据（节点和边） |
| `/api/documents` | GET | 获取文档列表 |
| `/api/documents` | POST | 添加新文档 |
| `/api/documents/{id}` | DELETE | 删除文档 |
| `/api/documents/upload` | POST | 上传文档 |
| `/api/documents/{id}/process` | POST | 处理文档 |
| `/api/settings` | GET | 获取系统设置 |
| `/api/settings` | POST | 保存系统设置 |
| `/api/overview` | GET | 获取系统概览数据 |
| `/health` | GET | 健康检查 |

**四种搜索模式：**

| 模型ID | 模式名称 | 数据源 | 适用场景 |
|--------|----------|--------|----------|
| `graphrag-local-search:latest` | 本地搜索 | 实体表、关系表 | 具体、明确的问题 |
| `graphrag-global-search:latest` | 全局搜索 | 社区报告表 | 需要全局概览的问题 |
| `full-model:latest` | 综合搜索 | 本地+全局 | 需要综合分析的问题 |
| `gpt-4o:latest` | 直接调用 | 智谱AI | 通用知识问答 |

#### 4.1.2 `utils/entity_extractor.py` - 实体提取器

基于**标题边界区间匹配**的实体提取策略：

```python
class EntityExtractor:
    def extract(self, text):
        # 1. 按标题划分内容块 (Markdown标题 # ## ### 等)
        # 2. 对每块内容进行分词 (jieba)
        # 3. 提取关键词 (TF-IDF)
        # 4. 基于共现和模式匹配提取关系
        # 5. 返回实体、关系、颜色映射
```

**支持的实体类型（24种）：**
- 概念(concept)、主题(topic)、术语(term)、定义(definition)
- 示例(example)、方法(method)、流程(process)、原理(principle)
- 理论(theory)、应用(application)、特性(characteristic)等

**支持的关系类型（9种）：**
- 包含、因果、从属、对立、依赖、影响、属性、关联、对比

#### 4.1.3 `utils/config.py` - 配置管理

从 `.env` 文件读取环境变量：

```python
# 智谱AI API配置
GRAPHRAG_API_BASE=https://open.bigmodel.cn/api/paas/v4
GRAPHRAG_CHAT_API_KEY=your-api-key-here
GRAPHRAG_CHAT_MODEL=glm-4-flash
GRAPHRAG_EMBEDDING_MODEL=embedding-2

# 服务器配置
SERVER_HOST=0.0.0.0
SERVER_PORT=8012
```

#### 4.1.4 `settings.yaml` - GraphRAG配置

定义GraphRAG索引构建参数：
- LLM参数：模型、最大token、重试次数
- 嵌入模型：批处理大小
- 文本分块：块大小800字符，重叠100字符
- 实体提取：最大提取轮数5轮
- 搜索配置：本地/全局搜索参数

### 4.2 前端核心模块

#### 4.2.1 路由配置 (`router/index.js`)

```javascript
/           → Home.vue      (首页)
/chat       → Chat.vue      (智能问答)
/graph      → Graph.vue     (图谱可视化)
/documents  → Documents.vue (文档管理)
/settings   → Settings.vue  (系统设置)
```

#### 4.2.2 主要页面组件

| 组件 | 功能描述 |
|------|----------|
| **Home.vue** | 系统首页，展示功能卡片、统计概览、最近活动 |
| **Chat.vue** | 智能问答界面，支持四种搜索模式、Markdown渲染、对话历史 |
| **Graph.vue** | D3.js实现的交互式知识图谱，支持4种布局（力导向/环形/树形/网格） |
| **Documents.vue** | 文档上传、列表展示、处理进度追踪 |
| **Settings.vue** | API配置、GraphRAG参数调整、系统设置管理 |

---

## 五、数据流与处理流程

### 5.1 文档处理流程

```
用户上传文档 (PDF/Word/TXT/MD)
         ↓
    文档解析 (read_file_content)
         ↓
    实体提取 (EntityExtractor.extract)
         ↓
    关系抽取 (_extract_relationships)
         ↓
    图谱优化 (optimize_graph)
         ↓
    数据持久化 (build_knowledge_graph)
```

### 5.2 问答处理流程

```
用户输入问题
       ↓
选择搜索模式
  ├── 本地搜索 (local_search)
  │      ↓
  │   加载实体/关系数据
  │      ↓
  │   检索相关实体
  │      ↓
  │   结合上下文调用智谱AI
  │
  ├── 全局搜索 (global_search)
  │      ↓
  │   加载社区报告
  │      ↓
  │   整合报告摘要
  │      ↓
  │   调用智谱AI
  │
  ├── 综合搜索 (full-model)
  │      ↓
  │   并行执行本地+全局
  │      ↓
  │   合并结果
  │
  └── 直接调用 (gpt-4o)
         ↓
      调用智谱AI
       ↓
  返回Markdown格式回答
```

---

## 六、关键配置文件

### 6.1 环境变量 (.env)

```env
# 智谱AI API配置（必须配置）
GRAPHRAG_API_BASE=https://open.bigmodel.cn/api/paas/v4
GRAPHRAG_CHAT_API_KEY=<your-chat-api-key>
GRAPHRAG_EMBEDDING_API_KEY=<your-embedding-api-key>

# 模型配置
GRAPHRAG_CHAT_MODEL=glm-4-flash
GRAPHRAG_EMBEDDING_MODEL=embedding-2

# 服务配置
SERVER_PORT=8012
LOG_LEVEL=INFO
```

### 6.2 Python依赖 (requirements.txt)

```txt
fastapi
uvicorn
graphrag
lancedb
pandas
numpy
pyarrow
tiktoken
openai
pydantic
python-dotenv
pyyaml
aiohttp
python-multipart
jieba
nltk
spacy
PyPDF2
python-docx
```

---

## 七、启动方式

### 7.1 后端启动

```bash
# 进入后端目录
cd backend

# 安装依赖（首次运行）
pip install -r requirements.txt

# 复制环境变量模板并配置
cp .env.example .env
# 编辑 .env 文件，填写智谱AI API密钥

# 启动服务
python start_server.py
# 服务地址: http://localhost:8012
```

### 7.2 前端启动

```bash
# 进入前端目录
cd frontend

# 安装依赖（首次运行）
npm install

# 启动开发服务器
npm run dev
# 访问地址: http://localhost:3000
```

### 7.3 服务访问

| 服务 | 地址 | 说明 |
|------|------|------|
| 前端页面 | http://localhost:3000 | 用户界面 |
| 后端API | http://localhost:8012 | API接口 |
| API文档 | http://localhost:8012/docs | Swagger文档 |

---

## 八、系统特点总结

| 特点 | 说明 |
|------|------|
| **多模态问答** | 支持本地/全局/综合/直接调用四种搜索模式 |
| **交互式图谱** | D3.js实现，支持拖拽、缩放、多种布局 |
| **文档智能解析** | 自动提取实体和关系构建知识图谱 |
| **LLM缓存** | 避免重复API调用，提升性能 |
| **响应式设计** | 支持桌面和移动端 |
| **Markdown支持** | 问答支持完整的Markdown格式 |
| **对话历史** | 本地存储对话记录 |
| **国产大模型** | 使用智谱AI作为核心推理引擎 |
| **RESTful API** | 标准化API设计，支持流式响应 |

---

## 九、使用示例

### 9.1 API调用示例

**问答接口调用：**

```bash
curl -X POST http://localhost:8012/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "graphrag-local-search:latest",
    "messages": [
      {"role": "user", "content": "什么是知识图谱？"}
    ],
    "stream": false
  }'
```

**获取模型列表：**

```bash
curl http://localhost:8012/v1/models
```

**上传文档：**

```bash
curl -X POST http://localhost:8012/api/documents/upload \
  -F "file=@document.pdf"
```

### 9.2 前端使用流程

1. **打开首页** → 查看系统概览和统计数据
2. **进入问答页面** → 选择搜索模式，输入问题
3. **查看图谱** → 浏览知识图谱可视化
4. **管理文档** → 上传、处理、删除文档
5. **系统设置** → 配置API密钥和参数

---

## 十、注意事项

1. **API密钥配置**：必须在 `.env` 文件中正确配置智谱AI的API密钥
2. **数据目录**：确保 `backend/inputs/files/` 目录存在且有写入权限
3. **Python版本**：推荐使用 Python 3.10-3.12
4. **端口冲突**：默认端口为8012，若被占用可修改 `.env` 中的 `SERVER_PORT`
5. **网络要求**：需要网络连接以调用智谱AI API

---

## 十一、项目状态

- **当前版本**：2.0.0
- **开发状态**：功能完整，可正常运行
- **维护状态**：持续维护中

---

**项目地址**：`e:\Projects_of_Liang\SingleProject\Python_Liang\KnowledgeGraph`

---