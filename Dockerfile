# ============================================================
# KnowledgeGraph v4.0 — Multi-stage Docker Build (non-root)
# ============================================================
# Stage 1: Build frontend
FROM node:20-alpine AS frontend-builder
WORKDIR /frontend
COPY frontend/package.json frontend/package-lock.json* ./
RUN npm ci --silent
COPY frontend/ .
RUN npm run build

# Stage 2: Production runtime
FROM python:3.11-slim
LABEL org.opencontainers.image.title="KnowledgeGraph"
LABEL org.opencontainers.image.version="4.0.0"

WORKDIR /app

# System deps for building Python packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc g++ curl \
    && rm -rf /var/lib/apt/lists/*

# Python dependencies (pip layer caching)
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Application code
COPY backend/ .

# Production frontend from stage 1
COPY --from=frontend-builder /frontend/dist /app/static

# Non-root runtime user (v4.1: 移除容器内提权面)
RUN useradd --create-home --shell /bin/bash appuser

# Data directories (populated via volumes at runtime)
RUN mkdir -p data inputs/files && chown -R appuser:appuser /app/data /app/inputs /home/appuser

# 模型/缓存下载目录指向可写位置
ENV HOME=/home/appuser

USER appuser

EXPOSE 8013

HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8013/health || exit 1

CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8013"]
