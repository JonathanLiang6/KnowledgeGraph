# ============================================================
# KnowledgeGraph v3.1 — Multi-stage Docker Build
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
LABEL org.opencontainers.image.version="3.1.0"

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

# Data directories (populated via volumes at runtime)
RUN mkdir -p data inputs/files

EXPOSE 8013

HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8013/health || exit 1

CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8013"]
