# Sandbox Operator Guide

> **Audience:** engineers shipping a branch-build of Lumen.AI alongside the
> live production instance without contaminating its data.

## What a sandbox gives you

A sandbox is an isolated Lumen.AI instance:

| Concern            | Production                    | Sandbox `<name>`                                    |
| ------------------ | ----------------------------- | --------------------------------------------------- |
| Knowledge root     | `knowledge_base/`             | `knowledge_base/sandbox/<name>/`                    |
| ChromaDB path      | `knowledge_base/chroma/`      | `knowledge_base/sandbox/<name>/chroma/`             |
| ChromaDB collection| `techdocgen_knowledge`        | `techdocgen_knowledge__sandbox_<name>`              |
| Conversations DB   | `knowledge_base/conversations.db` | `knowledge_base/sandbox/<name>/conversations.db` |
| Streamlit port     | `8503`                        | `8513` (prod + 10)                                  |
| FastAPI port       | `8080`                        | `8090` (prod + 10)                                  |
| Roslyn port        | `5050`                        | `5060` (prod + 10)                                  |

All of this is resolved at import time by [`src/ops/sandbox.py`](../src/ops/sandbox.py)
from a single env var: `SANDBOX_NAME`. Unset ⇒ production behaviour. Set ⇒
every stateful path/port shifts to the sandbox namespace.

## Quickstart

```bash
# 1. Cold-start a new sandbox (empty knowledge base)
./scripts/lumen.sh sandbox start kt-pro-phase-1
# → http://localhost:8513

# 2. OR: seed it from production first
./scripts/lumen.sh sandbox snapshot kt-pro-phase-1
./scripts/lumen.sh sandbox start    kt-pro-phase-1

# 3. Work on the branch. Production (:8503) is untouched.

# 4. Compare
./scripts/lumen.sh sandbox diff     kt-pro-phase-1
# or visit the Sandbox Diff page in the sandbox UI.

# 5. When happy, promote (stops both, snapshots prod, swaps state)
./scripts/lumen.sh sandbox stop     kt-pro-phase-1
./scripts/lumen.sh stop
./scripts/lumen.sh sandbox promote  kt-pro-phase-1
./scripts/lumen.sh start
```

## Naming

Sandbox names match `^[a-z0-9][a-z0-9_-]{0,40}$`. Reserve prefixes for
intent:

* `feat-<phase>` — KT-Pro feature branches (e.g. `feat-phase-1`, `feat-phase-7`)
* `exp-<topic>`  — throwaway experiments
* `bugfix-<id>`  — reproducing reported issues
* `ci`           — the CI guard sandbox (baked into `.github/workflows/ci.yml`)

## Lifecycle commands

All delegate through `./scripts/lumen.sh sandbox <sub> <name>`:

| Sub       | Script                        | What it does                                           |
| --------- | ----------------------------- | ------------------------------------------------------ |
| `start`   | `scripts/sandbox_start.sh`    | Boot Streamlit under `SANDBOX_NAME=<name>` on `:8513`. |
| `stop`    | `scripts/sandbox_stop.sh`     | Kill that Streamlit, clean up PID.                     |
| `snapshot`| `scripts/sandbox_snapshot.sh` | `rsync` prod knowledge base → sandbox dir.             |
| `promote` | `scripts/sandbox_promote.sh`  | Back up prod to a tarball, then swap sandbox → prod.   |
| `diff`    | `scripts/sandbox_diff.py`     | Markdown table of stats delta (chunks/docs/services).  |
| `status`  | (inline)                      | List all sandboxes under `knowledge_base/sandbox/`.    |

`promote` refuses to run if either port `:8503` or `:8513` is in use — stop
both Streamlits first. It writes `knowledge_base/prod_backup_<ts>.tar` before
overwriting; rollback is `tar -xf <backup> -C knowledge_base/`.

## Isolation guarantees (and their limits)

What the design guarantees:

* No code outside `src/ops/sandbox.py` knows the literal prod paths or ports.
  A CI grep enforces this — see the rule in `.github/workflows/ci.yml`.
* `bootstrap()` refuses to start a sandbox whose `chroma_dir` resolves to the
  prod chroma dir (defence in depth for symlink games).
* Tests in `tests/test_sandbox_isolation.py` lock in the path/port/suffix
  contract — they must stay green.
* `assert_not_touching_prod()` uses `psutil` (when available) to audit open
  files at runtime.

What the design does **not** protect against:

* A human editing files directly under `knowledge_base/chroma/` while a
  sandbox is running. Use the scripts.
* Ollama is a shared resource. A sandbox uses the same Ollama endpoint as
  prod; concurrent heavy loads compete for GPU/CPU.
* Disk quota — sandbox chroma dirs are full copies, not CoW snapshots. One
  sandbox per feature branch, clean up when you merge.

## Cleaning up

```bash
./scripts/lumen.sh sandbox stop <name>
rm -rf knowledge_base/sandbox/<name>
```

The `knowledge_base/sandbox/` tree is `.gitignore`d, so leftovers never end
up in a commit.

## Troubleshooting

**"Port 8513 already in use."**  Another sandbox is running. `./scripts/lumen.sh sandbox status` to list them, then stop the stray.

**"Sandbox `<name>` already running."**  Stale PID file. `./scripts/lumen.sh sandbox stop <name>` will clean it up; if that doesn't work, `pgrep -f "SANDBOX_NAME=<name>"` to find the process.

**"Sandbox's Chroma collection is empty after snapshot."**  Chroma persists collection metadata in SQLite inside `chroma/`. The snapshot script copies the whole dir, but the collection name stored on disk is the production name; the sandbox module reads it under the suffixed name. This works because `get_or_create_collection(name)` opens the *suffixed* collection, which Chroma materialises as empty on first access. To get prod data visible in the sandbox, re-ingest, or use the diff page's read-through to prod (planned Phase 8).

**"Promote said 'nothing to promote'."**  Check `knowledge_base/sandbox/<name>/chroma/` is non-empty. A cold-start sandbox with no ingests has nothing to promote.
