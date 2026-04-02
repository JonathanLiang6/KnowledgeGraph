# 知识图谱智能问答系统

一个基于 GraphRAG 和智谱AI 的知识图谱智能问答系统，支持文档管理、知识图谱可视化和智能问答功能。

## ✨ 功能特性

### 1. 智能问答
- 支持三种搜索模式：本地搜索、全局搜索、综合搜索
- 基于知识图谱的精准问答
- 支持 Markdown 格式回答
- 对话历史记录和导出功能

### 2. 图谱可视化
- 交互式知识图谱展示
- 支持多种布局方式（力导向、环形、树形、网格）
- 实体详情查看和关系探索
- 图谱缩放、拖拽和导出

### 3. 文档管理
- 支持多种文件格式（PDF、Word、TXT、Markdown）
- 文档上传和自动解析
- 文档内容预览
- 文档处理状态追踪

### 4. 系统设置
- API 配置管理
- 系统参数设置
- 数据统计信息展示

## 🛠️ 技术栈

### 后端
| 技术 | 说明 |
|------|------|
| FastAPI | 高性能 Web 框架 |
| GraphRAG | 微软知识图谱框架 |
| LanceDB | 向量数据库 |
| 智谱AI | 大语言模型 API |
| Pandas | 数据处理 |
| jieba/NLTK/spaCy | NLP 处理 |

### 前端
| 技术 | 说明 |
|------|------|
| Vue 3 | 前端框架 |
| Element Plus | UI 组件库 |
| Pinia | 状态管理 |
| D3.js | 图谱可视化 |
| ECharts | 图表库 |
| marked | Markdown 渲染 |

## 📁 项目结构

```
KnowledgeGraph/
├── backend/                    # 后端代码
│   ├── cache/                  # LLM 调用缓存
│   ├── data/                   # 持久化数据
│   │   ├── documents.json      # 文档列表
│   │   └── settings.json       # 系统设置
│   ├── inputs/                 # 输入数据
│   │   ├── artifacts/          # GraphRAG 生成的数据
│   │   └── reports/            # 日志报告
│   ├── prompts/                # LLM 提示词模板
│   ├── utils/                  # 工具模块
│   │   ├── config.py           # 配置管理
│   │   ├── helpers.py          # 工具函数
│   │   └── main.py             # FastAPI 主应用
│   ├── .env.example            # 环境变量示例
│   ├── requirements.txt        # Python 依赖
│   ├── settings.yaml           # GraphRAG 配置
│   └── start_server.py         # 启动脚本
├── frontend/                   # 前端代码
│   ├── src/
│   │   ├── router/             # 路由配置
│   │   ├── styles/             # SCSS 样式
│   │   ├── views/              # 页面组件
│   │   │   ├── Home.vue        # 首页
│   │   │   ├── Chat.vue        # 智能问答
│   │   │   ├── Graph.vue       # 图谱可视化
│   │   │   ├── Documents.vue   # 文档管理
│   │   │   └── Settings.vue    # 系统设置
│   │   ├── App.vue             # 根组件
│   │   └── main.js             # 入口文件
│   ├── index.html
│   ├── package.json
│   └── vite.config.js
└── README.md
```

## 🚀 快速开始

### 环境要求
- Python 3.8+
- Node.js 16+
- 智谱AI API 密钥

### 1. 克隆项目

```bash
git clone <repository-url>
cd KnowledgeGraph
```

### 2. 后端配置

```bash
# 进入后端目录
cd backend

# 创建虚拟环境
python -m venv venv

# 激活虚拟环境
# Windows:
venv\Scripts\activate
# Linux/Mac:
# source venv/bin/activate

# 安装依赖
pip install -r requirements.txt

# 配置环境变量
copy .env.example .env
# 编辑 .env 文件，填写你的智谱AI API密钥
```

### 3. 前端配置

```bash
# 进入前端目录
cd frontend

# 安装依赖
npm install

# 启动开发服务器
npm run dev
```

### 4. 启动服务

```bash
# 在后端目录启动服务
cd backend
python start_server.py
```

### 5. 访问系统

- 前端界面：http://localhost:3000
- 后端 API：http://localhost:8012
- API 文档：http://localhost:8012/docs

## ⚙️ 配置说明

### 环境变量 (.env)

```env
# 智谱AI API 配置
GRAPHRAG_API_BASE=https://open.bigmodel.cn/api/paas/v4
GRAPHRAG_CHAT_API_KEY=your-api-key-here
GRAPHRAG_EMBEDDING_API_KEY=your-api-key-here
GRAPHRAG_CHAT_MODEL=glm-4-flash
GRAPHRAG_EMBEDDING_MODEL=embedding-2

# 服务器配置
SERVER_HOST=0.0.0.0
SERVER_PORT=8012
LOG_LEVEL=INFO
```

### GraphRAG 配置 (settings.yaml)

主要配置项：
- **LLM 配置**：模型类型、最大 token 数、重试次数
- **嵌入配置**：嵌入模型、批处理大小
- **文本分块**：块大小、重叠大小
- **实体类型**：支持的实体类型列表
- **搜索配置**：本地搜索和全局搜索参数

## 📖 使用指南

### 智能问答

1. 进入「智能问答」页面
2. 在输入框中输入问题
3. 选择搜索模式（本地/全局/综合）
4. 点击发送或按 Enter 键
5. 查看 AI 回答，支持复制和反馈

### 图谱可视化

1. 进入「图谱可视化」页面
2. 使用控制面板筛选实体类型和关系类型
3. 切换不同的布局方式
4. 点击节点查看详细信息
5. 拖拽节点调整位置，滚轮缩放视图

### 文档管理

1. 进入「文档管理」页面
2. 点击上传按钮选择文件
3. 系统自动解析文档并提取知识
4. 查看文档处理状态和统计信息

## 🔌 API 接口

### 智能问答

```http
POST /v1/chat/completions
Content-Type: application/json

{
  "model": "graphrag-local-search:latest",
  "messages": [
    {
      "role": "user",
      "content": "什么是知识图谱？"
    }
  ],
  "stream": false
}
```

支持的模型：
- `graphrag-local-search:latest` - 本地搜索（基于实体和关系）
- `graphrag-global-search:latest` - 全局搜索（基于社区报告）
- `full-model:latest` - 综合搜索（本地+全局）
- `gpt-4o:latest` - 直接调用大模型

### 获取模型列表

```http
GET /v1/models
```

### 获取图谱数据

```http
GET /api/graph/data
```

### 文档管理

```http
# 获取文档列表
GET /api/documents

# 上传文档
POST /api/documents/upload
Content-Type: multipart/form-data

# 处理文档
POST /api/documents/{doc_id}/process

# 删除文档
DELETE /api/documents/{doc_id}
```

### 系统设置

```http
# 获取设置
GET /api/settings

# 保存设置
POST /api/settings
Content-Type: application/json
```

## 📂 数据存储

| 类型 | 路径 | 说明 |
|------|------|------|
| 上传文档 | `backend/inputs/` | 用户上传的原始文件 |
| 图谱数据 | `backend/inputs/artifacts/` | GraphRAG 生成的 Parquet 文件 |
| 缓存数据 | `backend/cache/` | LLM 调用缓存 |
| 持久化数据 | `backend/data/` | documents.json, settings.json |
| 报告日志 | `backend/inputs/reports/` | 系统运行日志 |

## 🐛 常见问题

### 1. API 密钥未设置

**问题**：启动服务时提示「API 密钥未设置」

**解决**：在 `backend/.env` 文件中设置正确的智谱AI API 密钥

### 2. 数据加载失败

**问题**：启动服务时提示「加载数据失败」

**解决**：确保 `backend/inputs/artifacts` 目录中存在必要的 Parquet 数据文件

### 3. 依赖安装失败

**问题**：安装依赖时失败

**解决**：确保使用 Python 3.8+，并尝试更新 pip：
```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### 4. 端口占用

**问题**：启动服务时提示端口被占用

**解决**：修改 `backend/.env` 文件中的 `SERVER_PORT` 配置，使用其他端口

## 📝 开发计划

- [ ] 支持更多文档格式
- [ ] 添加用户认证功能
- [ ] 优化图谱布局算法
- [ ] 支持多语言问答
- [ ] 添加图谱编辑功能

## 📄 许可证

MIT License

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

## 📧 联系方式

如有问题或建议，请联系项目维护者。

---

**注意**：本项目仅供学习和研究使用，请遵守相关 API 服务条款。
