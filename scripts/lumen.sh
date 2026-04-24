#!/usr/bin/env bash
# =============================================================================
# Lumen.AI — Service Lifecycle Manager
# =============================================================================
# Manages the Lumen.AI application stack:
#   1. Streamlit app   (Lumen.AI UI, default :8503)
#   2. ChromaDB        (embedded — no separate process, managed in-app)
#
# Ollama is NOT managed by this script. It is treated as an external
# dependency: the status command probes it for visibility only, and you
# are expected to start/stop it yourself (e.g. `ollama serve`).
#
# Usage:
#   ./scripts/lumen.sh start
#   ./scripts/lumen.sh stop
#   ./scripts/lumen.sh restart
#   ./scripts/lumen.sh status
#   ./scripts/lumen.sh logs
# =============================================================================

set -euo pipefail

# ── Config ───────────────────────────────────────────────────────────────────
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
RUN_DIR="$ROOT_DIR/.run"
LOG_DIR="$ROOT_DIR/logs"
mkdir -p "$RUN_DIR" "$LOG_DIR"

STREAMLIT_PORT="${LUMEN_STREAMLIT_PORT:-8503}"
STREAMLIT_APP="${LUMEN_STREAMLIT_APP:-app.py}"
STREAMLIT_PID="$RUN_DIR/streamlit.pid"
STREAMLIT_LOG="$LOG_DIR/streamlit.log"

# Ollama is probed for status visibility only — never started/stopped here.
OLLAMA_HOST="${OLLAMA_HOST:-127.0.0.1:11434}"

# Auto-detect a Python interpreter that actually has `streamlit` installed.
# Honors LUMEN_PYTHON override; otherwise probes the common candidates in
# order and picks the first that imports streamlit successfully. This
# avoids the common macOS pitfall where `python3` points at a fresh
# Homebrew Python that doesn't have the project's deps.
detect_python() {
  if [ -n "${LUMEN_PYTHON:-}" ]; then
    echo "$LUMEN_PYTHON"
    return
  fi
  local candidates=(
    /usr/bin/python3
    python3.11
    python3.12
    python3.10
    python3.9
    python3
    python
  )
  for p in "${candidates[@]}"; do
    local bin
    bin=$(command -v "$p" 2>/dev/null) || continue
    if "$bin" -c "import streamlit" 2>/dev/null; then
      echo "$bin"
      return
    fi
  done
  echo ""
}
PYTHON_BIN="$(detect_python)"

# ── Colors ───────────────────────────────────────────────────────────────────
if [ -t 1 ]; then
  C_RESET="\033[0m"; C_DIM="\033[2m"; C_BOLD="\033[1m"
  C_GREEN="\033[32m"; C_RED="\033[31m"; C_YELLOW="\033[33m"; C_BLUE="\033[34m"
else
  C_RESET=""; C_DIM=""; C_BOLD=""; C_GREEN=""; C_RED=""; C_YELLOW=""; C_BLUE=""
fi

log()  { printf "${C_DIM}[%s]${C_RESET} %s\n" "$(date +%H:%M:%S)" "$*"; }
ok()   { printf "  ${C_GREEN}✓${C_RESET} %s\n" "$*"; }
warn() { printf "  ${C_YELLOW}!${C_RESET} %s\n" "$*"; }
err()  { printf "  ${C_RED}✗${C_RESET} %s\n" "$*" >&2; }
hdr()  { printf "${C_BOLD}${C_BLUE}▶ %s${C_RESET}\n" "$*"; }

# ── Helpers ──────────────────────────────────────────────────────────────────
pid_alive() {
  local pid=$1
  [ -n "$pid" ] && kill -0 "$pid" 2>/dev/null
}

read_pid() {
  local file=$1
  [ -f "$file" ] && cat "$file" 2>/dev/null || echo ""
}

port_in_use() {
  local port=$1
  if command -v lsof >/dev/null 2>&1; then
    lsof -iTCP:"$port" -sTCP:LISTEN -P -n >/dev/null 2>&1
  else
    (echo > "/dev/tcp/127.0.0.1/$port") >/dev/null 2>&1
  fi
}

wait_http_ok() {
  local url=$1 tries=${2:-30}
  for _ in $(seq 1 "$tries"); do
    if curl -fsS -o /dev/null "$url" 2>/dev/null; then return 0; fi
    sleep 1
  done
  return 1
}

# ── Streamlit ────────────────────────────────────────────────────────────────
start_streamlit() {
  hdr "Starting Lumen.AI Streamlit app"
  if port_in_use "$STREAMLIT_PORT"; then
    warn "Port $STREAMLIT_PORT already in use — assuming Streamlit is up"
    curl -fsS -o /dev/null "http://localhost:${STREAMLIT_PORT}/_stcore/health" \
      && ok "Streamlit healthy at http://localhost:${STREAMLIT_PORT}" \
      || err "Port $STREAMLIT_PORT busy but /_stcore/health failed"
    return 0
  fi
  if [ -z "$PYTHON_BIN" ]; then
    err "No Python interpreter with streamlit installed could be found."
    err "Tried: /usr/bin/python3, python3.{9,10,11,12}, python3, python"
    err "Install streamlit into one of them (e.g. /usr/bin/python3 -m pip install streamlit)"
    err "or set LUMEN_PYTHON=/path/to/python and retry."
    return 1
  fi
  cd "$ROOT_DIR"
  log "Using interpreter: $PYTHON_BIN ($("$PYTHON_BIN" --version 2>&1))"
  log "Launching streamlit run $STREAMLIT_APP → $STREAMLIT_LOG"
  nohup "$PYTHON_BIN" -m streamlit run "$STREAMLIT_APP" \
    --server.port "$STREAMLIT_PORT" \
    --server.headless true \
    >"$STREAMLIT_LOG" 2>&1 &
  echo $! > "$STREAMLIT_PID"
  if wait_http_ok "http://localhost:${STREAMLIT_PORT}/_stcore/health" 30; then
    ok "Streamlit up (pid $(cat "$STREAMLIT_PID")) → http://localhost:${STREAMLIT_PORT}"
  else
    err "Streamlit failed to become healthy — see $STREAMLIT_LOG"
    return 1
  fi
}

stop_streamlit() {
  hdr "Stopping Streamlit"
  local pid; pid=$(read_pid "$STREAMLIT_PID")
  if pid_alive "$pid"; then
    kill "$pid" 2>/dev/null || true
    sleep 1
    pid_alive "$pid" && kill -9 "$pid" 2>/dev/null || true
    ok "Streamlit stopped (pid $pid)"
  else
    local found
    found=$(pgrep -f "streamlit run $STREAMLIT_APP" 2>/dev/null || true)
    if [ -n "$found" ]; then
      warn "No PID file, killing stray: $found"
      echo "$found" | xargs kill 2>/dev/null || true
    else
      ok "Streamlit not running"
    fi
  fi
  rm -f "$STREAMLIT_PID"
}

# ── Status ───────────────────────────────────────────────────────────────────
status() {
  hdr "Lumen.AI Service Status"
  printf "  %-12s %-10s %-10s %s\n" "SERVICE" "STATE" "PID" "ENDPOINT"
  printf "  %-12s %-10s %-10s %s\n" "-------" "-----" "---" "--------"

  # Streamlit (managed)
  local spid sstate
  spid=$(read_pid "$STREAMLIT_PID")
  if curl -fsS -o /dev/null "http://localhost:${STREAMLIT_PORT}/_stcore/health" 2>/dev/null; then
    sstate="${C_GREEN}UP${C_RESET}"
  else
    sstate="${C_RED}DOWN${C_RESET}"
  fi
  printf "  %-12s ${sstate}%-10s${C_RESET} %-10s %s\n" "streamlit" "" "${spid:-—}" "http://localhost:${STREAMLIT_PORT}"

  # ChromaDB (embedded)
  printf "  %-12s ${C_DIM}%-10s${C_RESET} %-10s %s\n" "chromadb" "EMBEDDED" "—" "in-process (PersistentClient)"

  # Ollama (external — probe only, not managed)
  local ostate
  if curl -fsS -o /dev/null "http://${OLLAMA_HOST}/api/version" 2>/dev/null; then
    ostate="${C_GREEN}UP${C_RESET}"
  else
    ostate="${C_YELLOW}DOWN${C_RESET}"
  fi
  printf "  %-12s ${ostate}%-10s${C_RESET} %-10s %s ${C_DIM}(external)${C_RESET}\n" \
    "ollama" "" "—" "http://${OLLAMA_HOST}"
}

logs() {
  tail -f "$STREAMLIT_LOG"
}

# ── Sandbox (delegates to scripts/sandbox_*.sh) ──────────────────────────────
sandbox() {
  local sub="${1:-}" name="${2:-}"
  case "$sub" in
    start)     "$SCRIPT_DIR/sandbox_start.sh" "$name" ;;
    stop)      "$SCRIPT_DIR/sandbox_stop.sh"  "$name" ;;
    snapshot)  "$SCRIPT_DIR/sandbox_snapshot.sh" "$name" ;;
    promote)   "$SCRIPT_DIR/sandbox_promote.sh"  "$name" ;;
    diff)      "$PYTHON_BIN" "$SCRIPT_DIR/sandbox_diff.py" "$name" ;;
    status)
      hdr "Sandboxes under knowledge_base/sandbox/"
      for d in "$ROOT_DIR"/knowledge_base/sandbox/*/; do
        [ -d "$d" ] || continue
        local n; n="$(basename "$d")"
        local pid_file="$d/run/streamlit.pid"
        local state="stopped"
        [ -f "$pid_file" ] && kill -0 "$(cat "$pid_file")" 2>/dev/null && state="running"
        printf "  %-24s %s\n" "$n" "$state"
      done
      ;;
    *)
      cat <<EOF
Usage: $0 sandbox <subcommand> <name>

Subcommands:
  start <name>      Launch an isolated Streamlit on :8513 under SANDBOX_NAME
  stop  <name>      Stop a running sandbox
  snapshot <name>   Copy prod knowledge_base → sandbox for testing
  promote  <name>   Replace prod knowledge_base with sandbox state (manual)
  diff  <name>      Markdown diff of sandbox vs prod stats
  status            List all sandboxes and their state
EOF
      return 1
      ;;
  esac
}

# ── Dispatch ─────────────────────────────────────────────────────────────────
action=${1:-}

case "$action" in
  start)   start_streamlit ;;
  stop)    stop_streamlit ;;
  restart) stop_streamlit; sleep 1; start_streamlit ;;
  status)  status ;;
  logs)    logs ;;
  sandbox) shift; sandbox "$@" ;;
  *)
    cat <<EOF
${C_BOLD}Lumen.AI Service Manager${C_RESET}

Usage: $0 <command>

Commands:
  start      Start the Streamlit app
  stop       Stop the Streamlit app
  restart    Restart the Streamlit app
  status     Show service status (Streamlit + embedded Chroma; probes Ollama for visibility)
  logs       Tail the Streamlit log
  sandbox    Manage branch-isolated sandbox instances — see: $0 sandbox

Environment overrides:
  LUMEN_STREAMLIT_PORT  (default 8503)
  LUMEN_STREAMLIT_APP   (default app.py)
  LUMEN_PYTHON          (default python3)
  OLLAMA_HOST           (default 127.0.0.1:11434, probe-only)

Files:
  PID files  → $RUN_DIR
  Log files  → $LOG_DIR

Note: Ollama is NOT managed by this script. Start it separately with:
  ollama serve
EOF
    exit 1
    ;;
esac
