#!/usr/bin/env bash
# =============================================================================
# sandbox_snapshot.sh — snapshot prod state into a sandbox for testing
# =============================================================================
# Copies production knowledge_base into a fresh sandbox so a branch build can
# exercise real data without risk. The ChromaDB collection is left under its
# production name on disk; the sandbox module applies a suffix at runtime so
# the two never collide.
#
# Usage:  ./scripts/sandbox_snapshot.sh <name>
#
# Safety: will REFUSE if the target sandbox already has content (protects from
#         accidental overwrite of a hot branch's state).
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

if [ ! -d "$PROD_DIR/chroma" ]; then
  echo "No production chroma dir at $PROD_DIR/chroma — nothing to snapshot." >&2
  exit 1
fi

if [ -d "$SANDBOX_DIR/chroma" ] && [ -n "$(ls -A "$SANDBOX_DIR/chroma" 2>/dev/null)" ]; then
  echo "Sandbox '$NAME' already has chroma data at $SANDBOX_DIR/chroma" >&2
  echo "Refusing to overwrite. Delete the sandbox dir first if this is intentional." >&2
  exit 1
fi

mkdir -p "$SANDBOX_DIR"
echo "▶ Snapshotting prod → sandbox '$NAME'"
echo "  src: $PROD_DIR"
echo "  dst: $SANDBOX_DIR"

# Copy chroma dir
rsync -a --delete "$PROD_DIR/chroma/" "$SANDBOX_DIR/chroma/"

# Copy conversations db if present (sqlite file, ok to copy hot — sandbox is cold)
if [ -f "$PROD_DIR/conversations.db" ]; then
  cp "$PROD_DIR/conversations.db" "$SANDBOX_DIR/conversations.db"
fi

# Copy ingest staging
if [ -d "$PROD_DIR/ingest" ]; then
  rsync -a "$PROD_DIR/ingest/" "$SANDBOX_DIR/ingest/"
fi

cat >"$SANDBOX_DIR/SNAPSHOT_META" <<EOF
sandbox_name: $NAME
snapshot_at:  $(date -u +%Y-%m-%dT%H:%M:%SZ)
source:       $PROD_DIR
git_head:     $(git -C "$ROOT_DIR" rev-parse HEAD 2>/dev/null || echo unknown)
git_branch:   $(git -C "$ROOT_DIR" rev-parse --abbrev-ref HEAD 2>/dev/null || echo unknown)
EOF

echo "✓ Snapshot complete. Launch with: ./scripts/sandbox_start.sh $NAME"
