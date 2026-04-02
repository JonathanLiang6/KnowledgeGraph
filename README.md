# 知识图谱辅助学习系统

一个基于 GraphRAG 的知识图谱辅助学习系统，支持智能问答、图谱可视化、文档管理等功能。

## 技术栈

- **前端**: Vue 3 + Element Plus + D3.js
- **后端**: FastAPI + Python + GraphRAG
- **数据库**: SQLite
- **大语言模型**: 智谱AI

## 快速开始

### 1. 环境准备

#### 后端环境

```bash
# 进入后端目录
cd backend

# 创建虚拟环境
python -m venv venv

# 激活虚拟环境
# Windows
venv\Scripts\activate
# Linux/Mac
# source venv/bin/activate

# 安装依赖
pip install -r requirements.txt
```

#### 前端环境

```bash
# 进入前端目录
cd frontend

# 安装依赖
npm install
```

### 2. 配置API密钥

1. 在 `backend` 目录下创建 `.env` 文件
2. 填写智谱AI API密钥

```env
# 智谱AI API配置
GRAPHRAG_API_BASE=https://open.bigmodel.cn/api/paas/v4
GRAPHRAG_CHAT_API_KEY=your-api-key-here  # 替换为实际的API密钥
GRAPHRAG_EMBEDDING_API_KEY=your-api-key-here  # 替换为实际的API密钥
GRAPHRAG_CHAT_MODEL=glm-4-flash
GRAPHRAG_EMBEDDING_MODEL=embedding-2
```

### 3. 启动服务

#### 后端服务

```bash
# 进入后端目录
cd backend

# 启动服务
python start_server.py
```

#### 前端服务

```bash
# 进入前端目录
cd frontend

# 启动开发服务器
npm run dev
```

### 4. 访问系统

- 前端：http://localhost:3000
- 后端API：http://localhost:8012

## 系统功能

### 1. 智能问答
- 基于知识图谱的智能问答
- 支持本地搜索、全局搜索和综合搜索
- 支持流式响应

### 2. 图谱可视化
- 交互式图谱展示
- 支持多种布局方式（力导向、环形、树形、网格）
- 实体详情查看
- 图谱缩放和拖拽

### 3. 文档管理
- 支持多种文件格式（txt、md、docx、pdf）
- 文档上传和管理
- 文档内容预览

### 4. 系统设置
- API配置管理
- 系统参数设置
- 数据统计信息

## API接口

### 智能问答接口

**POST /v1/chat/completions**

请求体：
```json
{
  "model": "graphrag-local-search:latest",
  "messages": [
    {
      "role": "user",
      "content": "什么是知识图谱？"
    }
  ],
  "stream": true
}
```

支持的模型：
- `graphrag-local-search:latest` - 本地搜索（基于实体和关系）
- `graphrag-global-search:latest` - 全局搜索（基于社区报告）
- `full-model:latest` - 综合搜索（本地+全局）

### 模型列表接口

**GET /v1/models**

返回可用的模型列表。

### 健康检查接口

**GET /health**

返回服务健康状态。

## 项目结构

```
KnowledgeGraph/
├── backend/           # 后端代码
│   ├── utils/         # 工具函数
│   ├── prompts/       # 提示词文件
│   ├── inputs/        # 输入数据
│   ├── requirements.txt  # 依赖文件
│   ├── settings.yaml  # GraphRAG配置
│   ├── .env           # 环境变量配置
│   └── start_server.py  # 启动脚本
├── frontend/          # 前端代码
│   ├── src/           # 源代码
│   ├── public/        # 静态资源
│   ├── package.json   # 依赖配置
│   └── vite.config.js # Vite配置
└── README.md          # 项目说明
```

## 配置说明

### 环境变量配置

| 配置项 | 说明 | 默认值 |
|--------|------|--------|
| GRAPHRAG_API_BASE | API基础地址 | https://open.bigmodel.cn/api/paas/v4 |
| GRAPHRAG_CHAT_API_KEY | 聊天API密钥 | - |
| GRAPHRAG_EMBEDDING_API_KEY | 嵌入API密钥 | - |
| GRAPHRAG_CHAT_MODEL | 聊天模型 | glm-4-flash |
| GRAPHRAG_EMBEDDING_MODEL | 嵌入模型 | embedding-2 |
| SERVER_HOST | 服务器主机 | 0.0.0.0 |
| SERVER_PORT | 服务器端口 | 8012 |
| LOG_LEVEL | 日志级别 | INFO |

### GraphRAG配置

配置文件：`backend/settings.yaml`

主要配置项：
- 语言模型配置
- 嵌入模型配置
- 文本分块配置
- 输入配置（支持的文件格式）
- 缓存配置
- 存储配置

## 使用指南

### 1. 智能问答

1. 打开前端页面：http://localhost:3000
2. 点击「智能问答」菜单
3. 在输入框中输入问题
4. 选择搜索模式（本地、全局或综合）
5. 点击「发送」按钮或按 Enter 键
6. 查看回答结果

### 2. 图谱可视化

1. 打开前端页面：http://localhost:3000
2. 点击「图谱可视化」菜单
3. 查看知识图谱
4. 可以：
   - 点击节点查看详情
   - 拖拽节点调整位置
   - 使用控制面板调整布局和筛选
   - 缩放视图查看不同层级

### 3. 文档管理

1. 打开前端页面：http://localhost:3000
2. 点击「文档管理」菜单
3. 上传文档（支持txt、md、docx、pdf）
4. 查看文档列表和详情

### 4. 系统设置

1. 打开前端页面：http://localhost:3000
2. 点击「系统设置」菜单
3. 配置API参数
4. 查看系统统计信息

## 常见问题

### 1. API密钥设置

**问题**：启动服务时提示「API密钥未设置」

**解决方法**：在 `backend/.env` 文件中设置正确的智谱AI API密钥。

### 2. 数据加载失败

**问题**：启动服务时提示「加载数据失败」

**解决方法**：确保 `backend/inputs/artifacts` 目录中存在必要的数据文件。

### 3. 依赖安装失败

**问题**：安装依赖时失败

**解决方法**：确保使用的是 Python 3.8+，并尝试更新 pip：
```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### 4. 端口占用

**问题**：启动服务时提示端口被占用

**解决方法**：修改 `backend/.env` 文件中的 `SERVER_PORT` 配置，使用其他端口。

## 开发与扩展

### 后端扩展

1. **添加新的API接口**：在 `backend/utils/main.py` 中添加新的路由
2. **修改搜索逻辑**：修改 `perform_local_search`、`perform_global_search` 函数
3. **添加新的数据源**：修改 `load_data` 函数

### 前端扩展

1. **添加新的组件**：在 `frontend/src/components` 中创建新组件
2. **修改页面布局**：修改相应的 Vue 页面文件
3. **添加新的功能**：在 `frontend/src/views` 中创建新页面

## 部署建议

### 开发环境

- 前端：`npm run dev`
- 后端：`python start_server.py`

### 生产环境

1. **前端构建**：
   ```bash
   cd frontend
   npm run build
   ```

2. **后端部署**：
   - 使用 Gunicorn 或 uWSGI 作为 WSGI 服务器
   - 配置 Nginx 作为反向代理
   - 设置环境变量和安全配置

## 许可证

MIT License

## 联系方式

如有问题或建议，请联系项目维护者。
