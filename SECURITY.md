# 安全政策

## 报告安全漏洞

如果你在 KnowledgeGraph 项目中发现了安全漏洞，请通过以下方式报告：

- 提交一个 **保密的 Issue**（在 GitHub 新建 Issue 时选择 "Report a security vulnerability"）
- 或发送邮件至项目维护者

## 安全实践

- 所有 API 密钥通过环境变量管理，不硬编码在代码中
- `.env` 文件在 `.gitignore` 中，不会被提交
- 用户输入在后端进行验证和清理
- SQL 操作使用参数化查询（SQLAlchemy ORM）
- 文件上传有类型和大小限制
- CORS 配置仅允许开发来源
- HTTPS 用于所有生产环境通信

## 依赖安全

- 定期检查依赖更新
- 使用 `pip-audit` 或 `safety` 扫描 Python 依赖
- 前端依赖通过 npm audit 检查
