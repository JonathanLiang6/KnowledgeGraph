# 知识图谱系统

基于 GraphRAG 技术的知识图谱系统，使用智谱AI进行实体和关系提取，SQLite作为数据库存储。

## 项目特性

- **智能问答**：基于知识图谱的智能问答系统，支持上下文理解
- **图谱可视化**：交互式知识图谱可视化展示，支持多种布局
- **文档管理**：支持多种格式文档的上传、处理和管理
- **系统设置**：灵活的系统配置和API管理
- **响应式设计**：支持多设备访问

## 技术栈

- **前端**：Vue 3 + Element Plus + D3.js
- **后端**：FastAPI + Python
- **数据库**：SQLite
- **AI服务**：智谱AI (GLM-4系列模型)
- **知识图谱**：GraphRAG

## 快速开始

### 环境要求

- Node.js 16+ （前端）
- Python 3.8+ （后端）

### 安装步骤

1. **克隆项目**

```bash
git clone <repository-url>
cd KnowledgeGraph
```

2. **安装前端依赖**

```bash
cd frontend
npm install
```

3. **安装后端依赖**

```bash
cd ../backend
pip install -r requirements.txt
```

4. **配置环境变量**

创建 `.env` 文件，配置以下内容：

```env
# 智谱AI API配置
GRAPHRAG_CHAT_API_KEY=your-api-key
GRAPHRAG_API_BASE=https://open.bigmodel.cn/api/paas/v4
GRAPHRAG_CHAT_MODEL=glm-4-air
GRAPHRAG_EMBEDDING_MODEL=embedding-3

# 系统配置
GRAPHRAG_INPUT_DIR=input
GRAPHRAG_OUTPUT_DIR=output
```

5. **启动服务**

分别启动前后端服务：

```bash
# 启动后端
cd backend
python -m uvicorn utils.main:app --reload

# 启动前端（新终端）
cd frontend
npm run dev
```

访问 http://localhost:3000 即可使用系统。

## 项目结构

```
KnowledgeGraph/
├── frontend/              # 前端项目
│   ├── src/
│   │   ├── views/         # 页面组件
│   │   ├── router/        # 路由配置
│   │   └── styles/        # 样式文件
│   ├── package.json       # 前端依赖
│   └── vite.config.js     # Vite配置
├── backend/               # 后端项目
│   ├── utils/             # 工具函数
│   ├── prompts/           # 提示词模板
│   └── requirements.txt   # Python依赖
├── .gitignore             # Git忽略文件
└── README.md              # 项目说明
```

## 核心功能

### 1. 智能问答
- 基于知识图谱的智能问答
- 支持上下文理解
- 消息历史记录
- 答案复制和反馈功能

### 2. 图谱可视化
- 交互式知识图谱展示
- 节点搜索和过滤
- 多种布局选项（力导向、环形、树形、网格）
- 图谱导出功能

### 3. 文档管理
- 支持 PDF、Word、TXT、Markdown 等格式
- 文档上传和处理
- 处理状态跟踪
- 文档详情查看

### 4. 系统设置
- API配置管理（智谱AI）
- 系统参数调整（批处理大小、文本块大小等）
- 数据统计查看
- 缓存管理

## 开发指南

### 前端开发

```bash
cd frontend
npm run dev  # 启动开发服务器，默认端口3000
```

### 后端开发

```bash
cd backend
python -m uvicorn utils.main:app --reload  # 启动开发服务器，默认端口8000
```

## API接口

### 文件管理
- `POST /api/files/upload` - 上传文件
- `GET /api/files/list` - 获取文件列表
- `GET /api/files/{file_id}` - 获取文件详情
- `DELETE /api/files/{file_id}` - 删除文件
- `POST /api/files/{file_id}/process` - 处理文件
- `GET /api/files/{file_id}/download` - 下载文件

### 系统设置
- `GET /api/settings` - 获取系统设置
- `POST /api/settings` - 保存系统设置
- `POST /api/settings/clear-cache` - 清除缓存
- `GET /api/settings/stats` - 获取数据统计

### 图谱数据
- `GET /api/graph/data` - 获取图谱数据
- `GET /api/graph/search` - 搜索图谱实体

## 部署

1. **构建前端**

```bash
cd frontend
npm run build
```

2. **部署后端**

```bash
cd backend
pip install -r requirements.txt
python -m uvicorn utils.main:app --host 0.0.0.0 --port 8000
```

## 配置说明

### API配置

| 配置项 | 说明 | 默认值 |
|--------|------|--------|
| GRAPHRAG_CHAT_API_KEY | 智谱AI API密钥 | - |
| GRAPHRAG_API_BASE | API基础地址 | https://open.bigmodel.cn/api/paas/v4 |
| GRAPHRAG_CHAT_MODEL | 对话模型 | glm-4-air |
| GRAPHRAG_EMBEDDING_MODEL | 嵌入模型 | embedding-3 |

### 系统参数

| 参数 | 说明 | 默认值 |
|------|------|--------|
| batchSize | 批处理大小 | 5 |
| chunkSize | 文本块大小 | 1000 |
| overlapRatio | 重叠比例 | 0.1 |
| entityThreshold | 实体阈值 | 0.7 |

## 许可证

MIT License

## 贡献

欢迎提交 Issue 和 Pull Request！
