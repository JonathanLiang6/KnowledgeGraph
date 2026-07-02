#!/usr/bin/env bash
# ============================================================
# KnowledgeGraph v3.1 — Linux/macOS 一键启动脚本
# ============================================================
set -e

ROOT="$(cd "$(dirname "$0")" && pwd)"
BACKEND_PID=""

cleanup() {
    echo ""
    echo "  Shutting down ..."
    if [ -n "$BACKEND_PID" ] && kill -0 "$BACKEND_PID" 2>/dev/null; then
        kill "$BACKEND_PID" 2>/dev/null
        echo "  Backend stopped."
    fi
    echo "  All stopped."
    exit 0
}
trap cleanup INT TERM

echo ""
echo "  ============================================"
echo "    KnowledgeGraph v3.1 — Start Script"
echo "  ============================================"
echo ""

# ── 端口清理 ───────────────────────────────────────────────
echo "  [Clean] Checking ports ..."
if command -v lsof &>/dev/null; then
    PID_8013=$(lsof -ti :8013 2>/dev/null || true)
    if [ -n "$PID_8013" ]; then
        echo "         Killing PID $PID_8013 on port 8013"
        kill -9 "$PID_8013" 2>/dev/null || true
    fi
    PID_3000=$(lsof -ti :3000 2>/dev/null || true)
    if [ -n "$PID_3000" ]; then
        echo "         Killing PID $PID_3000 on port 3000"
        kill -9 "$PID_3000" 2>/dev/null || true
    fi
fi

# ── 启动后端 ───────────────────────────────────────────────
echo ""
echo "  [1/2] Starting Backend (port 8013) ..."

# 激活虚拟环境（如果存在）
if [ -f "$ROOT/backend/venv/bin/activate" ]; then
    source "$ROOT/backend/venv/bin/activate"
elif [ -f "$ROOT/backend/.venv/bin/activate" ]; then
    source "$ROOT/backend/.venv/bin/activate"
fi

cd "$ROOT/backend"
python -m uvicorn app.main:app --host 0.0.0.0 --port 8013 --reload --log-level info &
BACKEND_PID=$!

# 等待后端就绪
echo "  Waiting for backend ..."
MAX_WAIT=30
WAIT_COUNT=0
while [ $WAIT_COUNT -lt $MAX_WAIT ]; do
    if curl -s http://localhost:8013/health > /dev/null 2>&1; then
        echo "  Backend ready."
        break
    fi
    sleep 2
    WAIT_COUNT=$((WAIT_COUNT + 1))
done
if [ $WAIT_COUNT -ge $MAX_WAIT ]; then
    echo "  ERROR: Backend failed to start after 60 seconds."
    cleanup
    exit 1
fi

# ── 启动前端 ───────────────────────────────────────────────
echo ""
echo "  [2/2] Starting Frontend (port 3000)"
echo "  http://localhost:3000"
echo "  Ctrl+C to stop"
echo ""
cd "$ROOT/frontend"
npm run dev

cleanup
