#!/usr/bin/env bash
# =============================================================================
# sandbox_start.sh — launch a branch build alongside production
# =============================================================================
# A sandbox is an isolated Lumen.AI instance: its own knowledge_base directory,
# its own ChromaDB collection suffix, and a +10 port offset. Production state
# is never touched.
#
# Usage:
#   ./scripts/sandbox_start.sh <name>
#
# Example:
#   ./scripts/sandbox_start.sh kt-pro-phase-1
#
# State root:  knowledge_base/sandbox/<name>/
# Streamlit:   http://localhost:8513   (prod 8503 + 10)
# FastAPI:     http://localhost:8090   (prod 8080 + 10)
# =============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

NAME="${1:-}"
if [ -z "$NAME" ]; then
  echo "Usage: $0 <sandbox-name>" >&2
  exit 1
fi
if [[ ! "$NAME" =~ ^[a-z0-9][a-z0-9_-]{0,40}$ ]]; then
  echo "Sandbox name must be lowercase alnum/dash/underscore (<=41 chars): got '$NAME'" >&2
  exit 1
fi

export SANDBOX_NAME="$NAME"
export LUMEN_STREAMLIT_PORT=8513
export LUMEN_STREAMLIT_APP="app.py"

SANDBOX_RUN_DIR="$ROOT_DIR/knowledge_base/sandbox/$NAME/run"
SANDBOX_LOG_DIR="$ROOT_DIR/knowledge_base/sandbox/$NAME/logs"
mkdir -p "$SANDBOX_RUN_DIR" "$SANDBOX_LOG_DIR"

PID_FILE="$SANDBOX_RUN_DIR/streamlit.pid"
LOG_FILE="$SANDBOX_LOG_DIR/streamlit.log"

if [ -f "$PID_FILE" ] && kill -0 "$(cat "$PID_FILE")" 2>/dev/null; then
  echo "Sandbox '$NAME' already running (pid $(cat "$PID_FILE"))" >&2
  exit 1
fi

# Locate an interpreter with streamlit
PYTHON_BIN="${LUMEN_PYTHON:-}"
if [ -z "$PYTHON_BIN" ]; then
  for p in /usr/bin/python3 python3.12 python3.11 python3.10 python3 python; do
    if command -v "$p" >/dev/null 2>&1 && "$p" -c "import streamlit" 2>/dev/null; then
      PYTHON_BIN="$(command -v "$p")"; break
    fi
  done
fi
if [ -z "$PYTHON_BIN" ]; then
  echo "No Python interpreter with streamlit found. Set LUMEN_PYTHON." >&2
  exit 1
fi

cd "$ROOT_DIR"
echo "▶ Starting sandbox '$NAME'"
echo "  SANDBOX_NAME=$SANDBOX_NAME"
echo "  state dir:   knowledge_base/sandbox/$NAME/"
echo "  streamlit:   http://localhost:$LUMEN_STREAMLIT_PORT"
echo "  log:         $LOG_FILE"

nohup "$PYTHON_BIN" -m streamlit run "$LUMEN_STREAMLIT_APP" \
  --server.port "$LUMEN_STREAMLIT_PORT" \
  --server.headless true \
  >"$LOG_FILE" 2>&1 &
echo $! >"$PID_FILE"

# Wait for health
for _ in $(seq 1 30); do
  if curl -fsS -o /dev/null "http://localhost:${LUMEN_STREAMLIT_PORT}/_stcore/health" 2>/dev/null; then
    echo "✓ Sandbox '$NAME' healthy (pid $(cat "$PID_FILE"))"
    exit 0
  fi
  sleep 1
done
echo "✗ Sandbox '$NAME' failed to become healthy — tail $LOG_FILE" >&2
exit 1
