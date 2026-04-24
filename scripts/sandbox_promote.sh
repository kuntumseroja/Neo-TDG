#!/usr/bin/env bash
# =============================================================================
# sandbox_promote.sh — promote a sandbox's state back to production
# =============================================================================
# Replaces the production knowledge_base with the sandbox's. A backup tarball
# of the current prod state is written first (and named so .gitignore catches
# it). Manual promote only — intentionally not callable from lumen.sh.
#
# Usage:  ./scripts/sandbox_promote.sh <name>
#
# Safety:
#   * Refuses if prod Streamlit is running (port 8503 in use).
#   * Refuses if sandbox Streamlit is running (port 8513 in use).
#   * Writes prod_backup_<timestamp>.tar before overwriting.
# =============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

NAME="${1:-}"
if [ -z "$NAME" ]; then
  echo "Usage: $0 <sandbox-name>" >&2
  exit 1
fi

PROD_DIR="$ROOT_DIR/knowledge_base"
SANDBOX_DIR="$ROOT_DIR/knowledge_base/sandbox/$NAME"

if [ ! -d "$SANDBOX_DIR/chroma" ]; then
  echo "Sandbox '$NAME' has no chroma dir — nothing to promote." >&2
  exit 1
fi

port_busy() {
  local port=$1
  if command -v lsof >/dev/null 2>&1; then
    lsof -iTCP:"$port" -sTCP:LISTEN -P -n >/dev/null 2>&1
  else
    (echo > "/dev/tcp/127.0.0.1/$port") >/dev/null 2>&1
  fi
}

if port_busy 8503; then
  echo "Production Streamlit is running on :8503 — stop it first with ./scripts/lumen.sh stop" >&2
  exit 1
fi
if port_busy 8513; then
  echo "Sandbox Streamlit is running on :8513 — stop it first with ./scripts/sandbox_stop.sh $NAME" >&2
  exit 1
fi

echo "▶ Promoting sandbox '$NAME' → production"
echo "  sandbox: $SANDBOX_DIR"
echo "  prod:    $PROD_DIR"

# Backup prod
TS=$(date -u +%Y%m%d-%H%M%S)
BACKUP="$PROD_DIR/prod_backup_${TS}.tar"
echo "  backup → $BACKUP"
tar -cf "$BACKUP" -C "$PROD_DIR" chroma conversations.db 2>/dev/null || \
  tar -cf "$BACKUP" -C "$PROD_DIR" chroma 2>/dev/null || true

# Overwrite prod with sandbox (rsync --delete ensures no stale files)
rsync -a --delete "$SANDBOX_DIR/chroma/" "$PROD_DIR/chroma/"
if [ -f "$SANDBOX_DIR/conversations.db" ]; then
  cp "$SANDBOX_DIR/conversations.db" "$PROD_DIR/conversations.db"
fi

# Append promote audit to SANDBOX meta
echo "promoted_at: $(date -u +%Y-%m-%dT%H:%M:%SZ)" >> "$SANDBOX_DIR/SNAPSHOT_META" 2>/dev/null || true
echo "promoted_by: $(whoami)"                       >> "$SANDBOX_DIR/SNAPSHOT_META" 2>/dev/null || true

echo "✓ Promoted '$NAME' to production. Restart with: ./scripts/lumen.sh start"
echo "  Rollback:   tar -xf $BACKUP -C $PROD_DIR"
