# Task: KT-Pro Sandbox — Safe Parallel Test Environment

**Status:** Open (execute BEFORE `TASK_KT_PRO_UPGRADE.md`)
**Priority:** High
**Owner:** _unassigned_
**Created:** 2026-04-24
**Branch target:** `main`
**Estimated effort:** 1–2 days

> This file sets up an **isolated sandbox** so the KT-Pro upgrade can be built
> and validated **without touching production state** — production's ChromaDB
> vector index, its SQLite conversation history, its generated docs, its
> ingested BRDs, and its Streamlit session all stay intact.
>
> Run this task FIRST. Do the upgrade work inside the sandbox. Promote to
> production only after the smoke test in `TASK_KT_PRO_UPGRADE.md §10.1`
> passes and a human has reviewed sandbox output.

---

## 1. Why we need a sandbox (the risks we are defending against)

Neo-TDG / Lumen.AI is a **knowledge platform**, not a report generator. Three
kinds of state would be expensive to lose or corrupt:

1. **Production ChromaDB** under `knowledge_base/chroma/` — accumulated
   embeddings of internal docs, crawled solutions and user-uploaded BRDs.
   Re-ingesting is slow (especially on air-gapped tenants with local Ollama
   embeddings) and some source PDFs may not be re-uploadable.
2. **Conversation memory** in `knowledge_base/conversations.db` — every Q/A
   the users have already had. Lose it and audit + follow-up context is gone.
3. **Generated docs** in `docs/` — the current deterministic Markdown/PDF
   artefacts, some of which may already be referenced from Jira or Confluence.

Plus the human risk: users are asking questions against this knowledge right
now. A breaking change in prompts, chunking, or persona routing would silently
degrade answers before anyone notices.

**Sandbox rule of thumb:** you can nuke the sandbox at any time. You can
never nuke production.

---

## 2. Design — the `SANDBOX_NAME` namespace pattern

Every stateful path and every listening port becomes a function of a single
env var `SANDBOX_NAME`. When unset, the app behaves exactly as today. When
set (e.g. `SANDBOX_NAME=kt-pro-v1`), every piece of state moves under a
sandbox-specific subfolder with its own ports and its own ChromaDB
collection.

```
knowledge_base/
├── chroma/                              # PROD collection store
├── conversations.db                     # PROD chat history
└── sandbox/
    ├── kt-pro-v1/
    │   ├── chroma/                      # SANDBOX collection store
    │   ├── conversations.db             # SANDBOX chat history
    │   └── ingest/                      # Sandbox-only uploads (BRD copies)
    └── kt-pro-v2/                       # another parallel sandbox, if needed
```

```
Sandbox ports (offset by +10 from production):
  Streamlit UI        8513     (prod 8503)
  FastAPI             8090     (prod 8080)
  Roslyn bridge       5060     (prod 5050, if run)
  Ollama              11434    (SHARED with prod, read-only)
```

Ollama is intentionally shared — embeddings and model weights are expensive
and read-only from the app's perspective, so there is no corruption risk. Do
not run two Ollama servers.

---

## 3. Files to create

```
src/ops/sandbox.py                      # NEW — resolves all paths + collection names
scripts/sandbox_start.sh                # NEW — launch sandbox instance
scripts/sandbox_stop.sh                 # NEW
scripts/sandbox_snapshot.sh             # NEW — copy a PROD snapshot into sandbox (read-only)
scripts/sandbox_promote.sh              # NEW — promote a validated sandbox to prod (with backup)
scripts/sandbox_diff.py                 # NEW — A/B compare answers between prod and sandbox
src/ui/page_sandbox_diff.py             # NEW — Streamlit page for A/B comparison (sandbox only)
tests/test_sandbox_isolation.py         # NEW
docs/SANDBOX.md                         # NEW — short operator guide
```

## 4. Files to modify

```
app.py                                  # call sandbox.bootstrap() before any stateful import
src/knowledge/vector_store.py           # collection_name respects sandbox prefix
src/rag/conversation.py                 # db path from sandbox.paths()
src/pipeline/ingestion.py               # ingest dir + auto-ingest paths from sandbox.paths()
src/api/server.py                       # port from sandbox.ports()
scripts/start.sh                        # delegate to sandbox_start.sh when SANDBOX_NAME is set
scripts/lumen.sh                        # add `sandbox` sub-command
config.yaml                             # add sandbox defaults
```

---

## 5. `src/ops/sandbox.py` — single source of truth

```python
"""Resolve all stateful paths and ports from SANDBOX_NAME.

Import this at the very top of app.py, BEFORE importing any module that
touches the filesystem or opens sockets. Every other module must read
paths/ports through sandbox.paths() / sandbox.ports() — never hard-code."""
from __future__ import annotations
import os
from dataclasses import dataclass
from pathlib import Path

@dataclass(frozen=True)
class Paths:
    knowledge_root: Path
    chroma_dir: Path
    conversations_db: Path
    ingest_dir: Path
    output_dir: Path
    logs_dir: Path
    run_dir: Path

@dataclass(frozen=True)
class Ports:
    streamlit: int
    fastapi: int
    roslyn: int

@dataclass(frozen=True)
class SandboxContext:
    name: str | None          # None = production
    paths: Paths
    ports: Ports
    collection_suffix: str    # "" for prod, "__sandbox_<name>" otherwise

def context() -> SandboxContext:
    name = os.environ.get("SANDBOX_NAME")
    repo = Path(__file__).resolve().parents[2]  # repo root
    if name is None:
        return SandboxContext(
            name=None,
            paths=Paths(
                knowledge_root = repo / "knowledge_base",
                chroma_dir     = repo / "knowledge_base" / "chroma",
                conversations_db = repo / "knowledge_base" / "conversations.db",
                ingest_dir     = repo / "knowledge_base" / "ingest",
                output_dir     = repo / "docs",
                logs_dir       = repo / "logs",
                run_dir        = repo / ".run",
            ),
            ports=Ports(streamlit=8503, fastapi=8080, roslyn=5050),
            collection_suffix="",
        )
    base = repo / "knowledge_base" / "sandbox" / name
    return SandboxContext(
        name=name,
        paths=Paths(
            knowledge_root   = base,
            chroma_dir       = base / "chroma",
            conversations_db = base / "conversations.db",
            ingest_dir       = base / "ingest",
            output_dir       = base / "docs_output",
            logs_dir         = base / "logs",
            run_dir          = base / "run",
        ),
        ports=Ports(streamlit=8513, fastapi=8090, roslyn=5060),
        collection_suffix=f"__sandbox_{name}",
    )

def bootstrap() -> SandboxContext:
    ctx = context()
    for p in [ctx.paths.knowledge_root, ctx.paths.chroma_dir,
              ctx.paths.ingest_dir, ctx.paths.output_dir,
              ctx.paths.logs_dir, ctx.paths.run_dir]:
        p.mkdir(parents=True, exist_ok=True)
    if ctx.name:
        # Guard: never let sandbox write to prod ChromaDB
        prod_chroma = Path(__file__).resolve().parents[2] / "knowledge_base" / "chroma"
        if ctx.paths.chroma_dir.resolve() == prod_chroma.resolve():
            raise RuntimeError("Sandbox chroma_dir must differ from prod")
    return ctx
```

**Required discipline** (enforced by a CI grep):

- No file under `src/` uses string literal `"knowledge_base/chroma"` or
  `"conversations.db"` or `"docs/"` or `"8503"` / `"8080"` / `"5050"` other
  than inside this `sandbox.py` file.

---

## 6. Wiring existing modules to `sandbox`

### 6.1 `app.py`

```python
# at the very top, before any `import chromadb` or other stateful import
from src.ops import sandbox
SANDBOX = sandbox.bootstrap()
import streamlit as st
st.set_page_config(
    page_title=f"Lumen.AI" + (f" — {SANDBOX.name}" if SANDBOX.name else ""),
    ...
)
if SANDBOX.name:
    st.warning(f"🧪 SANDBOX MODE — {SANDBOX.name}. Production state is untouched.")
```

### 6.2 `vector_store.py`

```python
def __init__(self, config):
    ctx = sandbox.context()
    base_name = config["knowledge_store"].get("collection_name", "techdocgen_knowledge")
    self.collection_name = base_name + ctx.collection_suffix
    self.persist_dir = str(ctx.paths.chroma_dir)
    ...
```

### 6.3 `conversation.py`

```python
def __init__(self, db_path: str | None = None):
    self.db_path = db_path or str(sandbox.context().paths.conversations_db)
    ...
```

### 6.4 `server.py`

```python
def run():
    ctx = sandbox.context()
    uvicorn.run(app, host=config["api"]["host"], port=ctx.ports.fastapi)
```

### 6.5 `ingestion.py`

Default auto-ingest watch dir → `sandbox.context().paths.ingest_dir`.

### 6.6 `config.yaml`

Add:

```yaml
sandbox:
  default_name: null             # null = prod
  list: ["kt-pro-v1"]             # known sandboxes; UI may list these
  allow_promote: false            # must be true to run sandbox_promote.sh
  snapshot_from_prod:
    chroma: true                  # copy prod chroma at snapshot-time
    conversations: false          # do NOT copy chat history by default (privacy)
    ingest_manifest: true         # list of files prod has ingested, not the files themselves
```

---

## 7. Launch / lifecycle scripts

### 7.1 `scripts/sandbox_start.sh`

```bash
#!/usr/bin/env bash
set -euo pipefail
: "${SANDBOX_NAME:?SANDBOX_NAME is required (e.g. kt-pro-v1)}"
export SANDBOX_NAME

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

# Python venv (reuse prod's)
source .venv/bin/activate

# Ensure sandbox dirs exist
python -c "from src.ops import sandbox; sandbox.bootstrap()"

# Start FastAPI (sandbox port)
nohup python -m uvicorn src.api.server:app --host 0.0.0.0 --port 8090 \
    >> knowledge_base/sandbox/$SANDBOX_NAME/logs/api.log 2>&1 &
echo $! > knowledge_base/sandbox/$SANDBOX_NAME/run/api.pid

# Start Streamlit (sandbox port)
nohup streamlit run app.py --server.port 8513 --server.headless true \
    >> knowledge_base/sandbox/$SANDBOX_NAME/logs/streamlit.log 2>&1 &
echo $! > knowledge_base/sandbox/$SANDBOX_NAME/run/streamlit.pid

# Optionally roslyn-bridge on 5060 if built
ROSLYN_BIN="${ROSLYN_BIN:-./tools/roslyn-bridge/bin/Release/net8.0/linux-x64/publish/roslyn-bridge}"
if [ -x "$ROSLYN_BIN" ]; then
    ROSLYN_PORT=5060 nohup "$ROSLYN_BIN" \
        >> knowledge_base/sandbox/$SANDBOX_NAME/logs/roslyn.log 2>&1 &
    echo $! > knowledge_base/sandbox/$SANDBOX_NAME/run/roslyn.pid
fi

echo "SANDBOX $SANDBOX_NAME started"
echo "  UI:       http://localhost:8513"
echo "  API:      http://localhost:8090"
echo "  Roslyn:   http://localhost:5060 (if built)"
echo "Production is unaffected: UI 8503, API 8080."
```

### 7.2 `scripts/sandbox_stop.sh`

```bash
#!/usr/bin/env bash
set -euo pipefail
: "${SANDBOX_NAME:?SANDBOX_NAME is required}"
BASE="knowledge_base/sandbox/$SANDBOX_NAME/run"
for svc in streamlit api roslyn; do
  if [ -f "$BASE/$svc.pid" ]; then
    kill "$(cat $BASE/$svc.pid)" 2>/dev/null || true
    rm -f "$BASE/$svc.pid"
  fi
done
echo "SANDBOX $SANDBOX_NAME stopped"
```

### 7.3 `scripts/lumen.sh` — add sandbox sub-command

```
Usage:
  ./scripts/lumen.sh start                  # production
  ./scripts/lumen.sh stop                   # production
  ./scripts/lumen.sh sandbox <name> start   # sandbox
  ./scripts/lumen.sh sandbox <name> stop
  ./scripts/lumen.sh sandbox <name> status
  ./scripts/lumen.sh sandbox list
```

---

## 8. Seeding the sandbox with production data (read-only snapshot)

Do NOT symlink prod's ChromaDB into sandbox. Copy it, with a timestamp, so
sandbox writes can't leak into prod.

### 8.1 `scripts/sandbox_snapshot.sh`

```bash
#!/usr/bin/env bash
set -euo pipefail
: "${SANDBOX_NAME:?SANDBOX_NAME is required}"

SRC_CHROMA="knowledge_base/chroma"
DST_BASE="knowledge_base/sandbox/$SANDBOX_NAME"
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"

mkdir -p "$DST_BASE/chroma" "$DST_BASE/snapshots"

# 1. Copy prod chroma
echo "[snapshot] copying prod chroma ($(du -sh $SRC_CHROMA | cut -f1)) ..."
cp -r "$SRC_CHROMA"/. "$DST_BASE/chroma"/

# 2. Record snapshot metadata
cat > "$DST_BASE/snapshots/$STAMP.json" <<EOF
{
  "snapshot_at": "$STAMP",
  "source": "$SRC_CHROMA",
  "prod_chroma_size": "$(du -sb $SRC_CHROMA | cut -f1)",
  "rename_policy": "collections will be re-namespaced with suffix __sandbox_$SANDBOX_NAME at next read"
}
EOF

# 3. Do NOT copy conversations.db by default (user privacy).
#    Operator can opt-in with: SNAPSHOT_CONVERSATIONS=1 ./scripts/sandbox_snapshot.sh
if [ "${SNAPSHOT_CONVERSATIONS:-0}" = "1" ]; then
    cp knowledge_base/conversations.db "$DST_BASE/conversations.db"
fi

echo "[snapshot] done. Sandbox $SANDBOX_NAME seeded from prod at $STAMP"
```

### 8.2 Collection re-namespacing

When `vector_store` opens a collection with suffix `__sandbox_<name>` and the
underlying Chroma folder still holds the prod collection name, renaming is
needed. Implement `migrate_collections_in_place()`:

```python
def migrate_collections_in_place(suffix: str):
    """Rename every collection in the Chroma store to add `suffix`, once."""
    import chromadb
    client = chromadb.PersistentClient(path=str(sandbox.context().paths.chroma_dir))
    for col in client.list_collections():
        if not col.name.endswith(suffix):
            new_name = col.name + suffix
            # Chroma 0.4+ supports .modify(name=...)
            col.modify(name=new_name)
```

Run once at sandbox startup if a `.needs_namespace_migration` marker file is
present (the snapshot script drops this marker).

### 8.3 Ingesting NEW BRDs into sandbox only

User uploads via `page_knowledge.py` are always written to
`sandbox.context().paths.ingest_dir`. In sandbox mode that's the sandbox
folder; in prod mode it's the prod folder. BRDs uploaded during sandbox
testing stay in the sandbox ChromaDB and do NOT pollute prod — because:

1. The upload handler writes to the sandbox ingest dir.
2. The ingestion pipeline reads from the sandbox ingest dir.
3. The vector_store writes to the sandbox chroma dir with the sandbox suffix.

### 8.4 Pulling prod BRDs into sandbox

If the operator wants the sandbox to have *everything* prod has (same BRDs,
same crawled solutions), run `sandbox_snapshot.sh`. That copies the vector
store. There is no need to re-embed the raw source files.

---

## 9. A/B answer comparison

### 9.1 `scripts/sandbox_diff.py`

CLI that asks the same question to prod (:8080) and sandbox (:8090) and
prints a side-by-side diff of:

- the answer text,
- the citation list,
- the retrieved chunk IDs,
- response time,
- tokens used.

```bash
$ python scripts/sandbox_diff.py \
    --sandbox kt-pro-v1 \
    --personas architect,developer,l2 \
    --questions-file tests/eval/goldens.yaml \
    --out diff_report.md
```

Writes a markdown report into `knowledge_base/sandbox/<name>/diffs/`.

### 9.2 `src/ui/page_sandbox_diff.py`

Visible only when `SANDBOX_NAME` is set. Two chat panes side by side:

- Left: queries prod via HTTP to `localhost:8080` (read-only — prod is **not**
  mutated because `/query` only reads).
- Right: queries sandbox locally.
- A "Diff" button shows text diff + set-diff of citations.

This page is the primary human-review tool during the KT-Pro validation.

---

## 10. Guardrails (CI + runtime)

### 10.1 Runtime guardrails

Add to `src/ops/sandbox.py`:

```python
def assert_not_touching_prod():
    ctx = context()
    if ctx.name is None:
        return
    # Verify no file handle open under knowledge_base/chroma/ that isn't under the sandbox
    import psutil, os
    prod = Path("knowledge_base/chroma").resolve()
    sbx  = ctx.paths.chroma_dir.resolve()
    for f in psutil.Process(os.getpid()).open_files():
        p = Path(f.path).resolve()
        try:
            p.relative_to(prod)
        except ValueError:
            continue
        # file is under prod/chroma; allowed only if also under sandbox (won't happen with our layout)
        try:
            p.relative_to(sbx)
        except ValueError:
            raise RuntimeError(f"Sandbox tried to open prod file: {p}")
```

Call `assert_not_touching_prod()` at Streamlit startup when `SANDBOX_NAME` is
set.

### 10.2 CI / pre-commit

A grep-based check that fails if any new code under `src/` introduces a
hard-coded stateful path or port:

```bash
grep -RInE "knowledge_base/chroma|conversations\.db|:8503|:8080|:5050" src/ \
    --exclude-dir=__pycache__ \
    | grep -v "src/ops/sandbox.py" \
    && echo "FAIL — hard-coded path/port in src/; route through src/ops/sandbox" && exit 1 \
    || echo "OK — no hard-coded state paths"
```

---

## 11. Promotion: sandbox → production

Only after:

- [ ] All `TASK_KT_PRO_UPGRADE.md` phase acceptance criteria pass.
- [ ] `scripts/smoke_kt_pro.sh` passes against the **sandbox** instance.
- [ ] A human has run `scripts/sandbox_diff.py` on at least 20 representative
      questions per persona and the answers are acceptable (citations valid,
      no regressions).
- [ ] `AIRGAP=1` smoke test passes.

### 11.1 `scripts/sandbox_promote.sh`

```bash
#!/usr/bin/env bash
set -euo pipefail
: "${SANDBOX_NAME:?SANDBOX_NAME is required}"

if ! grep -q 'allow_promote: *true' config.yaml; then
    echo "Set sandbox.allow_promote: true in config.yaml to enable promotion."
    exit 1
fi

# 1. Back up prod first
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
tar -cf "knowledge_base/prod_backup_$STAMP.tar" knowledge_base/chroma knowledge_base/conversations.db

# 2. Stop prod
./scripts/stop.sh

# 3. Promote code (git is the source of truth — no file copy needed for code).
#    Only promote DATA if you want sandbox's ingested content to become prod.
read -p "Promote sandbox vector data to prod? (y/N) " yn
if [ "$yn" = "y" ]; then
    rm -rf knowledge_base/chroma
    cp -r "knowledge_base/sandbox/$SANDBOX_NAME/chroma" knowledge_base/chroma
    python -c "from src.ops import sandbox; import chromadb; \
               c=chromadb.PersistentClient(path='knowledge_base/chroma'); \
               [col.modify(name=col.name.replace('__sandbox_$SANDBOX_NAME','')) for col in c.list_collections()]"
fi

# 4. Start prod
./scripts/start.sh
echo "PROMOTION complete. Backup at knowledge_base/prod_backup_$STAMP.tar"
```

Note: promotion is explicit and auditable. Default answer is **no** — the
most common case is to merge code to `main` and let prod pick up the new
behaviour on the **existing** vector data (not replace it).

---

## 12. Acceptance criteria (this task)

- [ ] `SANDBOX_NAME=kt-pro-v1 ./scripts/sandbox_start.sh` starts on
      `:8513 / :8090 / :5060` without touching prod files.
- [ ] With no `SANDBOX_NAME` set, `./scripts/start.sh` still starts prod on
      `:8503 / :8080 / :5050`.
- [ ] `tests/test_sandbox_isolation.py` asserts: when `SANDBOX_NAME=t1`,
      writing a chunk to the vector store creates files only under
      `knowledge_base/sandbox/t1/chroma/`, never under
      `knowledge_base/chroma/`.
- [ ] Uploading a BRD on `:8513` does not appear in prod chat answers on
      `:8503`.
- [ ] `scripts/sandbox_snapshot.sh` copies prod's chroma into the sandbox
      folder in < 1 min on a 1 GB index; conversation DB is NOT copied
      unless `SNAPSHOT_CONVERSATIONS=1`.
- [ ] `scripts/sandbox_diff.py` can run against both endpoints and produces a
      markdown report.
- [ ] `docs/SANDBOX.md` operator guide is present and readable by someone who
      has not seen the codebase.
- [ ] CI grep guardrail (§10.2) is enabled and blocks hard-coded state paths.

---

## 13. Recommended test plan for the KT-Pro upgrade itself

Once the sandbox is up:

1. **Empty sandbox.** Start sandbox with no snapshot. Upload one BRD, run one
   crawl on `essa/`. Confirm everything stays in sandbox folder.
2. **Snapshot from prod.** Run `sandbox_snapshot.sh` (without conversations).
   Ask five representative questions on sandbox — answers should match prod's
   today (baseline). This proves the copy worked.
3. **Turn on Phase 1 feature flag (personas).** Compare sandbox answers vs
   prod answers per persona using `sandbox_diff.py`. Confirm tone changes as
   expected and citations appear.
4. **Iterate phase by phase.** For each phase in `TASK_KT_PRO_UPGRADE.md`,
   implement → restart sandbox → run the eval harness → review diff report
   → sign off.
5. **Final smoke test.** Run `scripts/smoke_kt_pro.sh` with
   `TARGET=http://localhost:8090` (sandbox). All 12 artefacts must appear for
   a fresh crawl.
6. **Soak test.** Leave sandbox running for 24 h. Confirm no file writes
   outside the sandbox folder (check `lsof` output or `inotifywatch` log).
7. **Promote.** Merge code to `main`, let prod pick up the new code; **do
   not** copy sandbox vector data unless a specific reason justifies it.

---

## 14. FAQs

**Q: Can sandbox and prod share one Ollama?**
A: Yes. Ollama is read-only from the app's perspective (models are pulled
once, then inference doesn't mutate state). Sharing avoids duplicating ~5 GB
of model weights.

**Q: Can a user's uploaded BRD be in both sandbox and prod?**
A: Yes — upload to prod for real use, then snapshot prod into sandbox to
mirror. The sandbox copy has no back-link to prod; further edits in sandbox
stay in sandbox.

**Q: What about the crawler's Git clone (GitHub) path?**
A: Already gated by AIRGAP. If a sandbox user clicks Git clone, it uses the
sandbox's ingest dir. Air-gapped tenants have this tab hidden.

**Q: Can I run TWO sandboxes at once (e.g., kt-pro-v1 and kt-pro-v2)?**
A: Yes, but you need to move the ports further (e.g. v1 on :8513/:8090/:5060,
v2 on :8523/:8100/:5070). Extend `sandbox.py : ports()` to add an offset
based on sandbox name hash, or hard-code a small list in `config.yaml`.

**Q: What if Phase 3 Roslyn bridge crashes in sandbox?**
A: The crawler falls back to tree-sitter or regex per
`TASK_KT_PRO_UPGRADE.md §4`. Prod is not affected.

**Q: How do I wipe a sandbox?**
A: `./scripts/sandbox_stop.sh && rm -rf knowledge_base/sandbox/kt-pro-v1`.
Prod is never touched.

**Q: What if I accidentally upload a BRD in sandbox mode that should have
gone to prod?**
A: Use `scripts/sandbox_promote.sh` with `SNAPSHOT_CONVERSATIONS=0` — or
simpler, re-upload the BRD in prod. The point of sandbox is that its state is
disposable.

---

## 15. Deliverables checklist (for Claude Code to tick)

- [ ] `src/ops/sandbox.py` with `Paths`, `Ports`, `SandboxContext`,
      `context()`, `bootstrap()`, `assert_not_touching_prod()`.
- [ ] `vector_store`, `conversation`, `ingestion`, `server` modified to read
      paths/ports from `sandbox.context()`.
- [ ] `app.py` calls `sandbox.bootstrap()` at top.
- [ ] `scripts/sandbox_start.sh`, `sandbox_stop.sh`, `sandbox_snapshot.sh`,
      `sandbox_promote.sh` present and executable.
- [ ] `scripts/lumen.sh sandbox ...` sub-command works.
- [ ] `scripts/sandbox_diff.py` runs and produces a markdown diff.
- [ ] `src/ui/page_sandbox_diff.py` visible only in sandbox mode.
- [ ] `tests/test_sandbox_isolation.py` passes.
- [ ] `docs/SANDBOX.md` operator guide present.
- [ ] CI grep guardrail enabled.
- [ ] Changes merged to `main` BEFORE starting `TASK_KT_PRO_UPGRADE.md`
      implementation.

— END OF TASK —
