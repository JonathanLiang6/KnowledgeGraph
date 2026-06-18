# ============================================================
# KnowledgeGraph v2.4 Dockerfile
# ============================================================
FROM python:3.11-slim

WORKDIR /app

# 系统依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc g++ curl \
    && rm -rf /var/lib/apt/lists/*

# Python 依赖
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 应用代码
COPY backend/ .

# 前端构建 (可选: 多阶段构建)
# FROM node:20-alpine AS frontend
# WORKDIR /frontend
# COPY frontend/ .
# RUN npm ci && npm run build

# 数据目录
RUN mkdir -p data inputs/files

EXPOSE 8013

CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8013"]
