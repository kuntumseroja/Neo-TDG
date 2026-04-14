# Task: Air-Gap & Security Hardening

**Status:** Open
**Priority:** Medium
**Owner:** _unassigned_
**Created:** 2026-04-14
**Branch target:** `main`
**Estimated effort:** 0.5 – 1 day

---

## 1. Background

An audit of `main` (commit `6a5ca5d`) found **5 outbound egress points**. The
product ships an air-gap policy enforcer (`src/sdlc/architecture_validator.py :
check_airgap_policy`) that Lumen.AI itself does not comply with. This task
closes that gap so the app can run in a disconnected / regulated environment
(e.g. on-prem Indonesian government, tax authority, financial sector).

## 2. Egress inventory

| # | Host | Where | Severity | Purpose |
|---|------|-------|----------|---------|
| 1 | `kroki.io` (HTTPS) | `src/crawler/doc_generator.py:315` | **HIGH** — hits on every PDF export | Mermaid → PNG rendering for PDF embedding |
| 2 | `fonts.googleapis.com` | `src/ui/theme.py:78` | **MEDIUM** — every browser page-load | IBM Plex Sans / Mono fonts |
| 3 | `chromadb.telemetry.product.posthog` | auto-imported by `chromadb` | **MEDIUM** — every session start | Anonymised usage telemetry |
| 4 | `huggingface.co` | `src/knowledge/embeddings.py:102` via `SentenceTransformer(...)` | **LOW** — first run only, if model not cached | Sentence-transformers model download |
| 5 | `github.com` | `src/ui/page_crawler.py:132` `git clone` | **LOW** — user-initiated, optional | GitHub repo ingestion (explicit button) |

Local-only (no egress — OK for air-gap):
- Ollama at `http://localhost:11434`
- ChromaDB persistent client (filesystem)

Not present on `main` (already good): no OpenAI / Anthropic / Groq / Together
SDKs, no API keys in source, no `.env` committed.

## 3. Security observations (out of scope but log for follow-up)

- **Zip-Slip**: `src/ui/page_crawler.py : _extract_uploaded_zip` calls
  `zf.extractall(tmp_dir)` without member-path validation. A malicious ZIP can
  write outside `tmp_dir`. **Must-fix** before any public deployment.
- **Prompt injection via crawled code**: `.cs` files are embedded verbatim into
  LLM prompts (doc generator, RAG). Low real-world risk, but worth flagging.
- **SSRF via `OLLAMA_BASE_URL`**: env-configurable; low risk in single-tenant.

## 4. Proposed changes

All changes behind a single `AIRGAP=1` env flag so the default developer
experience is unchanged. When `AIRGAP=1`:

### 4.1 kroki.io → local no-op
`_fetch_mermaid_png` returns `b""` immediately; PDF keeps mermaid as fenced
code blocks. Optionally add an offline renderer later via `mermaid-cli` if
Node.js is available in the deployment image.

### 4.2 Self-bundle IBM Plex fonts
Drop the `@import url('https://fonts.googleapis.com/...')` line. Bundle the
5 needed woff2 files (~120 kB total) under `src/ui/fonts/` and reference via
`@font-face` local URL.

### 4.3 Disable ChromaDB telemetry
Set `os.environ["ANONYMIZED_TELEMETRY"] = "False"` **before** the first
`import chromadb` in `app.py`. Idempotent, no code path changes downstream.

### 4.4 Pre-cache or remove sentence-transformers
Current default is already Ollama embeddings — sentence-transformers is a
**fallback-only** path. In `AIRGAP=1` mode, raise a clear error if Ollama is
unreachable rather than silently hitting HuggingFace. Optionally pre-bake
`all-MiniLM-L6-v2` into the container image for shops that can't run Ollama.

### 4.5 Hide GitHub clone tab
In `page_crawler.py`, gate the GitHub tab behind `not AIRGAP`. Local Path and
ZIP upload remain.

### 4.6 Fix Zip-Slip (do this regardless of AIRGAP)
Validate each `ZipInfo.filename` against `tmp_dir` after `Path.resolve()`
before extraction.

### 4.7 Add an `AIRGAP=1` smoke test
Extend `tests/` with a test that sets `AIRGAP=1`, imports the app, asserts no
`urlopen`/`requests.post` to non-localhost hosts is attempted (monkey-patch
and fail the test if hit).

## 5. Performance impact analysis — **the question that prompted this doc**

Short answer: **neutral to slightly positive** for the end user. The
hardening removes blocking network waits from hot paths.

| Change | Before | After | Net impact |
|---|---|---|---|
| Disable kroki.io PNG | PDF export does N network round-trips to kroki.io (one per mermaid diagram), each 200 ms – 12 s timeout. On cold network can **block PDF generation for minutes**. | Zero RTT. Mermaid stays as fenced code in PDF. | **Faster** PDF export by ~N × 1–5 s. Visual fidelity of mermaid-in-PDF degrades (code block instead of rendered diagram). |
| Self-hosted fonts | Browser fetches Google Fonts on first load (~50–200 ms) + CDN lookup. | Fonts served from same origin as `app.py` — 1 fewer DNS + TLS handshake. | **Faster** first paint by ~50–150 ms. |
| Disable chroma telemetry | Background PostHog call at session start (~100–400 ms) + recurring pings. | No outbound calls. | **Faster** session init by ~100–400 ms, less network noise. |
| Remove sentence-transformers fallback | On first run without cache: multi-minute model download blocking. On cached run: 0. | Clear error vs silent hang. | **Same** on steady state, **fails fast** vs hanging on first run without network. |
| Hide GitHub tab | No performance effect — just removes an option. | — | Neutral. |
| Fix Zip-Slip | Same extraction speed. | Adds one `Path.resolve()` comparison per ZIP member (~μs). | Negligible. |

**Net: the app becomes slightly faster in every measurable hot path** (PDF
export, first paint, session init) and materially faster on PDF export when
the network is slow or blocked. The single UX regression is mermaid-in-PDF
rendering as code blocks instead of diagrams — acceptable for a regulated /
on-prem deployment.

> The Streamlit UI preview of the Architecture Doc (`checkbox_disclosure` +
> `streamlit_mermaid`) is **unaffected** — it renders client-side via the
> Mermaid JS library bundled with `streamlit_mermaid`. Only the PDF path uses
> kroki.io today.

## 6. Rollout plan

1. Add `AIRGAP` env parsing to `app.py` + `config.yaml` (`airgap: false`).
2. Implement 4.1 – 4.6 in a single feature branch.
3. Add test from 4.7.
4. Run full regression (the same 9 checks + 18 pytest cases as today).
5. Build an on-prem container image with `AIRGAP=1` baked in + sentence-
   transformers model pre-cached for shops that can't run Ollama.
6. Document in `README.md` under a new **Air-Gap Deployment** section.

## 7. Acceptance criteria

- [ ] `AIRGAP=1 streamlit run app.py` starts with zero outbound connections
      (verified via `lsof -i` / `strace` during first 60 s).
- [ ] PDF export with mermaid diagrams completes offline (diagrams appear as
      code blocks, no timeout).
- [ ] `check_airgap_policy` run against Lumen.AI's own repo reports **zero**
      violations.
- [ ] Regression suite green (pytest + 9 smoke checks).
- [ ] Zip-Slip patch accepted independently (security fix — do NOT gate on
      AIRGAP flag).
- [ ] README has an "Air-Gap Deployment" section with the list of local
      dependencies (Ollama, models, fonts).

## 8. Out of scope / follow-ups

- Offline mermaid rendering via `mermaid-cli` + headless Chromium (bigger
  lift — deferred until requested).
- SBOM generation + vulnerability scan for the on-prem image.
- Prompt-injection hardening on crawled source code.
- Signing the release container image.

---

**Decision log:** User asked 2026-04-14 whether hardening affects performance.
Analysis shows **neutral to positive** impact — removing blocking network I/O
only makes the app faster. Recorded here so the team can schedule
independently of Architecture Doc work.
