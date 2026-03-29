#!/usr/bin/env bash
# ESE Development — start backend + frontend in one command
# Usage: ./scripts/dev.sh

set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

# Check .env
if [ ! -f "$PROJECT_DIR/.env" ]; then
  if [ -f "$PROJECT_DIR/.env.example" ]; then
    cp "$PROJECT_DIR/.env.example" "$PROJECT_DIR/.env"
    echo "[ESE] Created .env from .env.example — edit it to add your OPENAI_API_KEY"
  else
    echo "[ESE] Warning: No .env file found. LLM features will use fallback mode."
  fi
fi

# Install Python deps if needed
if ! python -c "import ese" 2>/dev/null; then
  echo "[ESE] Installing Python dependencies..."
  cd "$PROJECT_DIR" && pip install -e ".[dev]" --quiet
fi

# Install frontend deps if needed
if [ ! -d "$PROJECT_DIR/frontend/node_modules" ]; then
  echo "[ESE] Installing frontend dependencies..."
  cd "$PROJECT_DIR/frontend" && npm install --silent
fi

echo ""
echo "  ╔══════════════════════════════════════╗"
echo "  ║  ESE — Emergent Simulation Engine    ║"
echo "  ║  Backend:  http://localhost:8000      ║"
echo "  ║  Frontend: http://localhost:5173      ║"
echo "  ╚══════════════════════════════════════╝"
echo ""

# Start backend in background
cd "$PROJECT_DIR"
python -m ese.api.server &
BACKEND_PID=$!

# Start frontend
cd "$PROJECT_DIR/frontend"
npm run dev &
FRONTEND_PID=$!

# Cleanup on exit
trap "kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; echo '[ESE] Stopped.'" EXIT

# Wait for either to exit
wait
