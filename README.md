# 知识图谱系统

基于 GraphRAG 技术的知识图谱系统，使用智谱AI进行实体和关系提取，Neo4j作为图数据库存储。

## 项目特性

- **智能问答**：基于知识图谱的智能问答系统
- **图谱可视化**：交互式知识图谱可视化展示
- **文档管理**：支持多种格式文档的上传、处理和管理
- **系统设置**：灵活的系统配置和API管理
- **响应式设计**：支持多设备访问

## 技术栈

- **前端**：Vue 3 + Element Plus + D3.js
- **后端**：FastAPI + Python
- **数据库**：Neo4j
- **AI服务**：智谱AI

## 快速开始

### 环境要求

- Node.js 16+ （前端）
- Python 3.8+ （后端）
- Neo4j 4.0+ （图数据库）

### 安装步骤

1. **克隆项目**

```bash
git clone <repository-url>
cd graphTest
```

2. **安装前端依赖**

```bash
cd frontend
npm install
```

3. **安装后端依赖**

```bash
cd ../ragtest
pip install -r requirements.txt
```

4. **配置环境变量**

创建 `.env` 文件，配置以下内容：

```env
# 智谱AI API配置
API_KEY=your-api-key
API_BASE_URL=https://open.bigmodel.cn/api/messages
MODEL=glm-4

# Neo4j数据库配置
NEO4J_URI=bolt://localhost:7687
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=your-password
```

5. **启动服务**

使用一键启动脚本：

```bash
# Windows
start.bat

# Linux/Mac
chmod +x start.sh
./start.sh
```

## 项目结构

```
graphTest/
├── frontend/           # 前端项目
│   ├── src/            # 源代码
│   │   ├── views/      # 页面组件
│   │   ├── router/     # 路由配置
│   │   └── styles/     # 样式文件
│   ├── package.json    # 前端依赖
│   └── vite.config.js  # Vite配置
├── ragtest/            # 后端项目
│   ├── utils/          # 工具函数
│   ├── models/         # 数据模型
│   └── api/            # API接口
├── start.bat           # Windows启动脚本
├── start.sh            # Linux/Mac启动脚本
└── README.md           # 项目说明
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
- 多种布局选项
- 图谱导出功能

### 3. 文档管理
- 支持 PDF、Word、TXT、Markdown 等格式
- 文档上传和处理
- 处理状态跟踪
- 文档详情查看

### 4. 系统设置
- API配置管理
- 系统参数调整
- 视觉设置
- 数据管理

## 开发指南

### 前端开发

```bash
cd frontend
npm run dev  # 启动开发服务器
```

### 后端开发

```bash
cd ragtest
uvicorn main:app --reload  # 启动开发服务器
```

## 部署

1. **构建前端**

```bash
cd frontend
npm run build
```

2. **部署后端**

可使用 Gunicorn + Nginx 部署后端服务。

## 许可证

MIT License

## 贡献

欢迎提交 Issue 和 Pull Request！