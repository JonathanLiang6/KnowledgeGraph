.PHONY: install dev test lint clean

# 安装依赖
install:
	cd backend && pip install -r requirements.txt
	cd frontend && npm install

# 启动开发环境
dev:
	cd backend && python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8013 &
	cd frontend && npm run dev

# 仅启动后端
dev-backend:
	cd backend && python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8013

# 运行测试
test:
	cd backend && python -m pytest tests/ -v

# 代码检查
lint:
	cd backend && python -m ruff check app/

# 清理
clean:
	find backend -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find backend -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null || true
	rm -rf frontend/node_modules/.cache 2>/dev/null || true
