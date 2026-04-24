#!/usr/bin/env bash
# =============================================================================
# sandbox_stop.sh — stop a running sandbox
# =============================================================================
# Usage:  ./scripts/sandbox_stop.sh <name>
# =============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

NAME="${1:-}"
if [ -z "$NAME" ]; then
  echo "Usage: $0 <sandbox-name>" >&2
  exit 1
fi

PID_FILE="$ROOT_DIR/knowledge_base/sandbox/$NAME/run/streamlit.pid"

if [ ! -f "$PID_FILE" ]; then
  # Fall back to port + process-name match
  stray=$(pgrep -f "SANDBOX_NAME=$NAME.*streamlit" 2>/dev/null || true)
  if [ -n "$stray" ]; then
    echo "No PID file; killing stray pids: $stray"
    echo "$stray" | xargs kill 2>/dev/null || true
    exit 0
  fi
  echo "Sandbox '$NAME' not running (no PID file)."
  exit 0
fi

PID=$(cat "$PID_FILE")
if kill -0 "$PID" 2>/dev/null; then
  kill "$PID" || true
  sleep 1
  kill -0 "$PID" 2>/dev/null && kill -9 "$PID" || true
  echo "✓ Sandbox '$NAME' stopped (pid $PID)"
else
  echo "Sandbox '$NAME' PID $PID already dead; cleaning up"
fi
rm -f "$PID_FILE"
