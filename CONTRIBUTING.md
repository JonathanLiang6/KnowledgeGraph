# 贡献指南

感谢你对 KnowledgeGraph 项目的关注！本文档说明如何参与项目贡献。

## 开发环境

```bash
# 克隆仓库
git clone https://github.com/JonathanLiang6/KnowledgeGraph.git
cd KnowledgeGraph

# 安装后端依赖
cd backend && pip install -r requirements.txt

# 安装前端依赖
cd frontend && npm install

# 启动开发服务器
start.bat
```

## 代码规范

### Python
- 遵循 Ruff 规则（`line-length=120`, `target-version=py311`）
- 函数/变量命名：`snake_case`
- 类命名：`PascalCase`
- 所有路由处理器、数据库操作使用 `async/await`
- Pydantic v2：使用 `model_validate` / `model_dump`

### 前端
- Vue 3 + Composition API
- Element Plus 组件库
- 森林绿主题配色
- SCSS 变量管理

### 提交规范
- 中文描述 + 版本标签，格式：`vX.Y: 简要描述`
- 主分支 `main`，功能分支 `vX.Y`

## Pull Request 流程

1. Fork 本仓库
2. 创建功能分支：`git checkout -b feature/amazing-feature`
3. 提交修改：`git commit -m 'feat: 添加Amazing功能'`
4. 推送分支：`git push origin feature/amazing-feature`
5. 提交 Pull Request

## 版本号

遵循语义化版本（SemVer）：`MAJOR.MINOR.PATCH`
- `pyproject.toml` 和 `app/main.py` 中的版本号需同步更新
