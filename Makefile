.PHONY: help install dev dev-backend test format clean docker-build docker-up docker-down

# ── 帮助 ───────────────────────────────────────────────────────
help:
	@echo "KnowledgeGraph v3.1 — 可用目标:"
	@echo ""
	@echo "  开发:"
	@echo "    make install       安装所有依赖"
	@echo "    make dev           启动开发环境（后端 + 前端）"
	@echo "    make dev-backend   仅启动后端"
	@echo ""
	@echo "  测试:"
	@echo "    make test          运行 pytest"
	@echo ""
	@echo "  Docker:"
	@echo "    make docker-build  构建 Docker 镜像"
	@echo "    make docker-up     启动 Docker 服务"
	@echo "    make docker-down   停止 Docker 服务"
	@echo ""
	@echo "  清理:"
	@echo "    make clean         清理所有缓存"

# ── 安装依赖 ─────────────────────────────────────────────────
install:
	cd backend && pip install -r requirements.txt
	cd frontend && npm install

# ── 启动开发环境 ─────────────────────────────────────────────
dev:
	@trap 'kill 0; echo "  All stopped."' EXIT; \
	cd backend && python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8013 & \
	cd frontend && npm run dev; \
	wait

# 仅启动后端
dev-backend:
	cd backend && python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8013

# ── 测试 ─────────────────────────────────────────────────────
test:
	cd backend && python -m pytest tests/ -v

# ── Docker ────────────────────────────────────────────────────
docker-build:
	docker build -t knowledge-graph:latest .

docker-up:
	docker-compose up -d

docker-down:
	docker-compose down

# ── 清理 ─────────────────────────────────────────────────────
clean:
	@echo "Cleaning Python cache..."
	@python -c "import os, shutil; [shutil.rmtree(os.path.join(r,d), ignore_errors=True) for r,_,fs in os.walk('backend') for d in fs if d == '__pycache__']" 2>/dev/null; true
	@python -c "import os; [os.remove(os.path.join(r,f)) for r,_,fs in os.walk('backend') for f in fs if f.endswith('.pyc')]" 2>/dev/null; true
	@python -c "import shutil; shutil.rmtree('backend/.pytest_cache', ignore_errors=True)" 2>/dev/null; true
	@python -c "import shutil; shutil.rmtree('backend/.ruff_cache', ignore_errors=True)" 2>/dev/null; true
	@python -c "import shutil; shutil.rmtree('backend/.mypy_cache', ignore_errors=True)" 2>/dev/null; true
	@echo "Cleaning frontend cache..."
	@python -c "import shutil; shutil.rmtree('frontend/node_modules/.cache', ignore_errors=True)" 2>/dev/null; true
	@echo "Done."
