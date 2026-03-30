# API 配置指南

本指南将帮助您配置知识图谱系统所需的 API 密钥和相关参数，确保系统能够正常运行。

## 1. 智谱AI API 配置

### 1.1 获取 API 密钥

1. 访问 [智谱AI开放平台](https://open.bigmodel.cn/)
2. 注册或登录账号
3. 进入 "控制台" -> "API密钥管理"
4. 点击 "创建密钥"
5. 复制生成的 API 密钥

### 1.2 配置方式

#### 方式一：通过 .env 文件配置（推荐）

1. 在 `ragtest` 目录下创建 `.env` 文件
2. 填写以下内容：

```env
# 智谱AI API配置
API_KEY=your-api-key  # 替换为您的API密钥
API_BASE_URL=https://open.bigmodel.cn/api/messages
MODEL=glm-4

# Neo4j数据库配置
NEO4J_URI=bolt://localhost:7687
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=your-password  # 替换为您的Neo4j密码
```

#### 方式二：通过系统设置页面配置

1. 启动系统后，访问 `http://localhost:5173/settings`
2. 在 "API配置" 标签页中填写 API 密钥和相关参数
3. 点击 "保存配置" 按钮

## 2. 其他 API 配置选项

### 2.1 模型选择

智谱AI提供多种模型选择：

- `glm-4`：最新的通用大语言模型
- `glm-3.5`：平衡性能和速度的模型
- `glm-3`：轻量级模型，适合快速响应

### 2.2 API 基础 URL

默认 API 基础 URL 为：`https://open.bigmodel.cn/api/messages`

如果智谱AI更新了 API 端点，请相应修改此配置。

### 2.3 请求超时

默认请求超时时间为 30 秒。如果您的网络环境较差，可以适当增加此值。

## 3. 数据库配置

### 3.1 Neo4j 配置

1. 安装并启动 Neo4j 服务
2. 访问 `http://localhost:7474` 设置初始密码
3. 在 `.env` 文件中配置以下参数：

```env
NEO4J_URI=bolt://localhost:7687
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=your-password  # 替换为您设置的密码
```

## 4. 环境变量优先级

系统会按照以下优先级读取配置：

1. 系统设置页面配置
2. `.env` 文件配置
3. 默认配置

## 5. 安全注意事项

### 5.1 API 密钥保护

- **不要**将 API 密钥硬编码在代码中
- **不要**将包含 API 密钥的 `.env` 文件提交到版本控制系统
- **不要**在公共场合分享您的 API 密钥
- 定期更新 API 密钥

### 5.2 开源项目注意事项

如果您计划在 GitHub 上开源此项目：

1. 在 `.gitignore` 文件中添加 `.env`
2. 提供 `.env.example` 文件作为配置模板
3. 在 README.md 中说明如何配置 API 密钥
4. 提醒用户不要提交包含真实 API 密钥的配置文件

## 6. 故障排除

### 6.1 API 调用失败

- 检查 API 密钥是否正确
- 检查网络连接是否正常
- 检查 API 密钥是否过期
- 检查 API 调用频率是否超过限制

### 6.2 数据库连接失败

- 检查 Neo4j 服务是否运行
- 检查数据库连接参数是否正确
- 检查数据库密码是否正确

## 7. 配置模板

### 7.1 .env.example 模板

```env
# 智谱AI API配置
API_KEY=your-api-key  # 请替换为您的API密钥
API_BASE_URL=https://open.bigmodel.cn/api/messages
MODEL=glm-4

# Neo4j数据库配置
NEO4J_URI=bolt://localhost:7687
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=your-password  # 请替换为您的Neo4j密码
```

### 7.2 .gitignore 配置

确保在 `.gitignore` 文件中添加：

```gitignore
# 环境配置文件
.env

# 依赖目录
node_modules/
__pycache__/

# 构建输出
dist/
build/

# 日志文件
*.log
```

## 8. 常见问题

### 8.1 Q: API 密钥在哪里获取？
A: 请访问 [智谱AI开放平台](https://open.bigmodel.cn/) 获取 API 密钥。

### 8.2 Q: 我可以使用其他大语言模型吗？
A: 目前系统默认支持智谱AI模型，如需使用其他模型，需要修改后端代码。

### 8.3 Q: 如何查看 API 调用历史和费用？
A: 请登录智谱AI开放平台，在控制台查看 API 调用历史和费用。

### 8.4 Q: API 密钥过期了怎么办？
A: 请在智谱AI开放平台重新创建 API 密钥，并更新配置文件。

---

**版本**：1.0.0
**最后更新**：2026-03-30