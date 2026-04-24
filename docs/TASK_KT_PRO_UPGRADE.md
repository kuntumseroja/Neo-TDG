# Task: KT-Pro Upgrade — Persona-Aware, Evidence-Grounded, Multi-Variant KT Generation

**Status:** Open
**Priority:** High
**Owner:** _unassigned_
**Created:** 2026-04-24
**Branch target:** `main`
**Estimated effort:** 4–6 weeks engineering, delivered in 9 phases

> This file is the single source of instructions for Claude Code to execute the
> KT-Pro upgrade of Neo-TDG (Lumen.AI SDLC Knowledge Engine). Read **all of
> section 0** before touching code, then execute phases 1 → 9 in order. Each
> phase is independently shippable; stop at any phase boundary if priorities
> change.

---

## 0. Context and Ground Rules

### 0.1 What Neo-TDG already is

Streamlit + FastAPI hybrid app that crawls .NET/Angular solutions, ingests
artefacts into ChromaDB, and offers RAG chat with hybrid BM25+vector retrieval.
Written in Python 3.9+, uses Ollama for local LLM + embeddings. Designed to run
**air-gapped**.

### 0.2 What we are adding (KT-Pro)

1. **Personas** — six reader roles: Architect, Developer, Tester, Support L1,
   Support L2, Support L3.
2. **Evidence-grounded output** — every generated paragraph cites a `file:line`
   or a prior doc `§section`.
3. **Multi-variant document bundle** — one polished DOCX per persona per crawl.
4. **Optional Roslyn bridge** — air-gap-safe .NET 8 syntactic analyser for
   better C# parsing, with tree-sitter as pure-Python fallback.
5. **Code-symbol chunker** — chunks by class/method, not just markdown heading.
6. **Self-critique gate** — reviewer LLM pass before export.
7. **Tenant-aware prompts** — remove hard-coded `"CoreTax"` references.
8. **Offline diagram renderer** — coordinate with existing
   `docs/TASK_OFFLINE_DIAGRAM_RENDERER.md`.
9. **Evaluation harness** — regression tests for answer quality and citation
   correctness.

### 0.3 Absolute rules (do not violate)

- **No new egress.** Every new feature must work under `AIRGAP=1`. Consult
  `docs/TASK_AIRGAP_HARDENING.md` for the existing policy. If you must add a
  dependency, ship it self-contained (pre-baked container layer, self-contained
  .NET publish, vendored wheel).
- **Backward-compatible.** Every existing Streamlit page, every existing API
  route, every existing crawl report field MUST keep working. Persona features
  are additive — the default persona continues to behave as today if unspecified.
- **Follow existing conventions.** Match the code style in `src/` (snake_case,
  Pydantic models under `src/models/`, FastAPI routes under `src/api/routes/`).
  Extend `scripts/lumen.sh`; do not introduce a new supervisor.
- **No hard-coded tenant strings.** If you see `"CoreTax"` outside of fixtures
  and example rule files, parameterise it (see Phase 6).
- **Tests before merge.** Every phase has acceptance criteria and at least one
  test under `tests/`.

### 0.4 Execution order and phase dependencies

```
Phase 1 ── Personas + Citations ───────────┐
Phase 2 ── Multi-variant DOCX ────────────┐│
Phase 3 ── Roslyn bridge (optional)       ││
Phase 4 ── Tree-sitter fallback + chunker ││
Phase 5 ── Self-critique gate ────────────┤│
Phase 6 ── Tenant awareness ──────────────┤│
Phase 7 ── Offline diagram renderer ──────┘│
Phase 8 ── Eval harness ───────────────────┤
Phase 9 ── Security hardening ─────────────┘
```

Phases 1, 6, 9 are highest priority and should land first. Phases 3 and 4 are
parallelizable. Phase 7 may already be in flight per the existing TASK file —
coordinate, do not duplicate.

### 0.5 Global acceptance criteria (validated after every phase)

- [ ] `pytest -q` passes.
- [ ] `ruff check src/ tests/` passes (or existing linter config).
- [ ] `AIRGAP=1 streamlit run app.py` starts without outbound network.
- [ ] No new entry in the egress inventory of `TASK_AIRGAP_HARDENING.md`.
- [ ] Existing crawler, ingest, rag-chat, sdlc pages still work end-to-end
      against a reference solution (`examples/` or `essa/` folder in the repo).

---

## Phase 1 — Personas and Citation Enforcement

### 1.1 Goal

Turn `src/rag/prompts.py` from a single hard-coded prompt into a persona
registry, and force every answer to carry citations.

### 1.2 Files to create

```
src/rag/personas.py         # NEW — PersonaRegistry + PersonaProfile
src/rag/citation_validator.py  # NEW — regex + structural checks
```

### 1.3 Files to modify

```
src/rag/prompts.py          # use PersonaRegistry; stop hard-coding CoreTax
src/rag/query_engine.py     # accept persona field on QueryRequest
src/rag/conversation.py     # add persona column to messages table
src/models/knowledge.py     # add persona Literal to QueryRequest
src/ui/page_rag_chat.py     # persona picker in the sidebar
src/api/routes/*.py         # accept persona in /query payload
```

### 1.4 PersonaRegistry design

`src/rag/personas.py`:

```python
from dataclasses import dataclass
from typing import Literal

PersonaId = Literal["architect", "developer", "tester", "l1", "l2", "l3"]

@dataclass(frozen=True)
class PersonaProfile:
    id: PersonaId
    display_name: str
    tone: str                   # e.g. "strategic, trade-off oriented"
    depth: Literal["shallow", "medium", "deep"]
    avoid: list[str]            # topics/styles to avoid (e.g. ["internal code detail"] for L1)
    emphasise: list[str]        # topics to emphasise
    system_prompt: str          # full prompt, {tenant} placeholder allowed
    output_schema: dict         # minimal JSON schema the LLM must return

PERSONAS: dict[PersonaId, PersonaProfile] = {
    "architect":  PersonaProfile(...),
    "developer":  PersonaProfile(...),
    "tester":     PersonaProfile(...),
    "l1":         PersonaProfile(...),
    "l2":         PersonaProfile(...),
    "l3":         PersonaProfile(...),
}

def get(persona: PersonaId) -> PersonaProfile:
    return PERSONAS[persona]
```

Write the six `system_prompt` strings using the tone rules from
`docs/DESIGN_NOTES_KTPRO.md` (create this file as a short cheat-sheet if it
doesn't exist). Each prompt **must**:

- refer to `{tenant}` instead of "CoreTax" (Phase 6 fills this in).
- require `[file.cs:L12-L34]` or `[doc §x.y]` citations for every factual
  sentence.
- specify the persona-appropriate depth and forbidden topics (L1 sees no raw
  code; Architect sees no deep debugging tactics).

### 1.5 CitationValidator

`src/rag/citation_validator.py`:

```python
import re
from dataclasses import dataclass

CITE_PATTERN = re.compile(r"\[(?P<src>[^\]]+?:L\d+(?:-L\d+)?|doc §[\d.]+)\]")

@dataclass
class ValidationResult:
    ok: bool
    paragraphs_total: int
    paragraphs_cited: int
    reasons: list[str]

def validate(answer: str, *, min_ratio: float = 0.7) -> ValidationResult:
    """
    Splits answer into paragraphs, counts how many contain at least one valid
    citation, returns ok=True when ratio >= min_ratio.
    Reasons list each uncited paragraph index.
    """
    ...
```

Wire this into `query_engine.query()`:

- After the LLM returns, call `validate()`.
- If `ok is False`, do **one** retry with an appended "MISSING CITATIONS —
  please re-answer citing each factual sentence" instruction.
- If the retry also fails, return the answer but set
  `response.warnings.append("low_citation_rate")` and surface that in the UI.

### 1.6 Conversation schema change

Add a `persona TEXT` column to the `messages` table. Use a migration-lite
pattern — at startup check `PRAGMA table_info(messages)` and `ALTER TABLE
messages ADD COLUMN persona TEXT` if missing. Persist the asker's persona with
every message.

### 1.7 UI change

In `src/ui/page_rag_chat.py`, add a `st.sidebar.selectbox` labelled
"**Persona**" with the six options. Persist selection in
`st.session_state.persona`. Pass it to `QueryRequest`.

### 1.8 Acceptance criteria

- [ ] `src/rag/personas.py` exports `PERSONAS` with six entries, each with a
      non-empty `system_prompt`.
- [ ] `QueryRequest.persona` defaults to `"developer"` if omitted (so old
      clients keep working).
- [ ] `/api/query` accepts `{"persona": "architect"}` and returns a tone-matched
      answer.
- [ ] `citation_validator.validate()` unit test passes for both compliant and
      non-compliant samples (`tests/test_citation_validator.py`).
- [ ] A single user-flow smoke test: ask the same question as `architect` vs
      `l1` — assert the two answers differ in length and depth
      (`tests/test_persona_query.py`, use a mocked LLM).

---

## Phase 2 — Multi-variant DOCX Bundle per Crawl

### 2.1 Goal

Every successful crawl produces one polished `.docx` + `.pdf` per persona — six
DOCX, six PDF — built from the existing `CrawlReport`, the
`ValidationReport` from `architecture_validator`, and rendered diagrams.

### 2.2 Dependencies

Add to `requirements.txt`:

```
python-docx>=1.1.0
Pillow>=10.0.0
```

No other additions. LibreOffice headless is optional and must be auto-detected
for PDF export; if absent, emit DOCX only and log a warning.

### 2.3 Files to create

```
src/crawler/persona_composer.py    # NEW — orchestrator
src/crawler/docx_builder.py        # NEW — python-docx helpers (h1/h2/bullet/table/image/figure)
src/crawler/persona_outlines.py    # NEW — one outline per persona → CrawlReport slice
tests/test_persona_composer.py     # NEW
```

### 2.4 Files to modify

```
src/crawler/doc_generator.py       # keep — still used for Markdown output
src/crawler/solution_crawler.py    # after crawl completes, call persona_composer.compose_all()
src/api/routes/crawl.py            # return list of generated artefacts in response
src/ui/page_crawler.py             # "Download KT bundle" section with six download buttons
```

### 2.5 docx_builder.py

Port the helpers from the ESSA KT reference (see
`docs/reference/essa_build.js` if preserved, otherwise re-derive). Functions
required:

```python
class DocxBuilder:
    def __init__(self, title: str, subtitle: str, tenant: str, persona: str) -> None: ...
    def h1(self, text: str) -> None: ...
    def h2(self, text: str) -> None: ...
    def h3(self, text: str) -> None: ...
    def p(self, text: str) -> None: ...
    def bullet(self, text: str) -> None: ...
    def numbered(self, text: str) -> None: ...
    def code_block(self, text: str) -> None: ...
    def callout(self, label: str, text: str, color: str = "0F6FC6") -> None: ...
    def table(self, header: list[str], rows: list[list[str]], widths: list[int]) -> None: ...
    def figure(self, png_path: str, caption: str, *, width_px: int = 620) -> None: ...
    def save(self, out_path: str) -> str: ...   # returns out_path
```

Style defaults: Calibri body 11pt, Heading 1 navy (#0F6FC6), Heading 2 dark
navy (#1F4E79), grey code-block shading. Header shows "`{tenant} — KT for
{persona}`". Footer shows page `X of Y`.

### 2.6 Outlines

`src/crawler/persona_outlines.py` exposes `outline_for(persona)` returning a
typed list of sections. Minimum sections per persona:

- **Architect** — Executive Summary, System Context, Component Model, Tech
  Stack & NFRs, ADRs (from code + rules), Risk Register, Recommendations.
- **Developer** — Overview, Solution Layout, Module Walkthrough, API
  Reference, Data Model, Extension Recipes, FAQ.
- **Tester** — Scope, Test Plan, Scenarios (given/when/then), Data &
  Fixtures, Regression Checklist, Coverage hints.
- **L1** — Quick Reference Card (1 page), Health Check Steps, Common User
  Complaints, Escalation path.
- **L2** — Runbook (start/stop/restart), Triage Playbook, Monitoring &
  Alerts, Log reading guide, Escalation path.
- **L3** — Deep-dive, Debugging procedures, Hotfix SOP, Extension recipes,
  Known risks.

Each outline item is a dataclass:

```python
@dataclass
class OutlineItem:
    id: str                 # "exec_summary"
    title: str              # "Executive Summary"
    source: Literal["report", "rules", "rag", "computed"]
    query: str | None       # RAG query when source="rag"
    max_tokens: int = 800
    required: bool = True
```

### 2.7 persona_composer.compose_all

```python
def compose_all(
    report: CrawlReport,
    validation: ValidationReport,
    *,
    tenant: str,
    out_dir: str,
    personas: list[PersonaId] | None = None,
    render_pdf: bool = True,
) -> list[Path]:
    """
    For each persona, build an in-memory draft (list[SectionDraft]) by:
      1. resolving each OutlineItem against report / validation / RAG,
      2. passing the resolved context to the LLM with persona prompt,
      3. collecting citations,
      4. rendering a DocxBuilder document,
      5. optionally converting to PDF via LibreOffice if available.
    Returns the list of output paths.
    """
```

### 2.8 PDF conversion

Use `subprocess.run(["soffice", "--headless", "--convert-to", "pdf", ...])`.
If `shutil.which("soffice")` is None, log a warning and return DOCX only. Do
not depend on `fpdf2` for the new bundle — keep fpdf2 only for the legacy
Markdown-derived PDF.

### 2.9 UI

In `page_crawler.py`, after a successful crawl, render six download buttons
in a 2×3 grid. File names: `{tenant}_{persona}_KT.docx`,
`{tenant}_{persona}_KT.pdf`.

### 2.10 Acceptance criteria

- [ ] `compose_all()` produces six DOCX when invoked on the bundled `essa/`
      reference solution.
- [ ] Each DOCX validates with `python-docx`'s `Document(path)` round-trip.
- [ ] Each DOCX contains at least one figure (if diagrams are available) and
      at least one table, plus a citations/references appendix.
- [ ] Running with `soffice` installed produces six PDFs; running without it
      still produces six DOCX and logs a single warning.
- [ ] `AIRGAP=1` mode works — no outbound calls during composition.

---

## Phase 3 — Roslyn Bridge (Optional, Air-gap-safe)

### 3.1 Goal

Add an optional, self-contained .NET 8 sidecar that performs **syntactic-only**
Roslyn analysis (no MSBuildWorkspace, no NuGet restore at runtime). Python
client in `src/crawler/roslyn_bridge.py` falls back to the existing regex
analyser if the sidecar is unreachable.

### 3.2 Create the sidecar

```
tools/roslyn-bridge/
├── RoslynBridge.csproj
├── Program.cs
├── Analyzer.cs
├── Dockerfile
└── README.md
```

`RoslynBridge.csproj` targets `net8.0`, adds `Microsoft.CodeAnalysis.CSharp`
(syntactic analysis only — do NOT add `Microsoft.CodeAnalysis.Workspaces.MSBuild`
in V1 to keep airgap story simple).

`Program.cs` exposes one endpoint:

```
POST /analyze  { "slnDir": "<abs path>", "excludeGlobs": [...] }
→ 200 { "files": [ { "path": "...", "namespaces": [...], "types": [...],
                     "methods": [...], "attributes": [...] } ], "tookMs": 123 }
```

Bind to `127.0.0.1:5050` only. Refuse to start if `AIRGAP=1` and any outbound
connection attempt would be made (startup probe; see Phase 9.3).

### 3.3 Build and ship recipe

Document in `tools/roslyn-bridge/README.md`:

```bash
# Build on a CONNECTED machine, run on an AIRGAPPED target
dotnet publish -c Release -r linux-x64 --self-contained true \
  -p:PublishSingleFile=true \
  -p:IncludeNativeLibrariesForSelfExtract=true \
  -p:EnableCompressionInSingleFile=true
# Output: bin/Release/net8.0/linux-x64/publish/roslyn-bridge (~60-90 MB)
```

`Dockerfile`:

```dockerfile
FROM mcr.microsoft.com/dotnet/sdk:8.0 AS build
WORKDIR /src
COPY . .
RUN dotnet publish -c Release -r linux-x64 --self-contained true \
    -p:PublishSingleFile=true -o /out

FROM mcr.microsoft.com/dotnet/runtime-deps:8.0
COPY --from=build /out/roslyn-bridge /app/roslyn-bridge
EXPOSE 5050
ENTRYPOINT ["/app/roslyn-bridge"]
```

### 3.4 Python client

`src/crawler/roslyn_bridge.py`:

```python
import os, requests, logging
log = logging.getLogger(__name__)
BRIDGE_URL = os.environ.get("ROSLYN_BRIDGE_URL", "http://127.0.0.1:5050")

def is_available(timeout: float = 0.5) -> bool:
    try:
        r = requests.get(f"{BRIDGE_URL}/healthz", timeout=timeout)
        return r.status_code == 200
    except Exception:
        return False

def analyze(sln_dir: str, exclude: list[str] | None = None, timeout: int = 300) -> dict:
    r = requests.post(f"{BRIDGE_URL}/analyze",
                      json={"slnDir": sln_dir, "excludeGlobs": exclude or []},
                      timeout=timeout)
    r.raise_for_status()
    return r.json()
```

### 3.5 Wire into solution_crawler

In `solution_crawler.py` after the regex pass:

```python
if is_available():
    try:
        roslyn = analyze(sln_dir, exclude=["**/bin/**", "**/obj/**"])
        report = merge_roslyn(report, roslyn)   # add symbol-accurate fields; do not overwrite existing
    except Exception as e:
        log.warning("roslyn-bridge failed, falling back to regex: %s", e)
```

`merge_roslyn` MUST be additive. Existing fields in `CrawlReport` stay
exactly as they are; new fields go under `report.roslyn` namespace so tests
don't break.

### 3.6 Lifecycle integration

Extend `scripts/lumen.sh`:

```bash
ROSLYN_BIN="${ROSLYN_BIN:-./tools/roslyn-bridge/bin/Release/net8.0/linux-x64/publish/roslyn-bridge}"

start_roslyn() {
    [ -x "$ROSLYN_BIN" ] || { echo "roslyn-bridge not built — skipping"; return; }
    nohup "$ROSLYN_BIN" >> logs/roslyn.log 2>&1 &
    echo $! > .run/roslyn.pid
}
stop_roslyn() {
    [ -f .run/roslyn.pid ] && kill "$(cat .run/roslyn.pid)" 2>/dev/null || true
    rm -f .run/roslyn.pid
}
status_roslyn() {
    [ -f .run/roslyn.pid ] && kill -0 "$(cat .run/roslyn.pid)" 2>/dev/null && echo "roslyn-bridge: up" || echo "roslyn-bridge: down"
}
```

Call `start_roslyn` from the existing `start` function and `stop_roslyn` from
`stop`. Wire `status_roslyn` into `lumen.sh status`.

### 3.7 Acceptance criteria

- [ ] `dotnet publish -c Release -r linux-x64 --self-contained` succeeds.
- [ ] `./roslyn-bridge` starts, responds to `GET /healthz`.
- [ ] `roslyn_bridge.analyze()` on a small fixture (e.g. `essa/ConsoleApp1`)
      returns namespaces, types, methods, attributes.
- [ ] When bridge is down, `solution_crawler` still completes; only a warning
      is logged.
- [ ] Outbound network check: `AIRGAP=1` + bridge running, no non-loopback
      socket open (verify with `ss -tnp` in a test).

---

## Phase 4 — Tree-sitter Fallback + Code-Symbol Chunker

### 4.1 Goal

For tenants who cannot install .NET, provide a pure-Python syntactic analyser
using `tree-sitter-c-sharp`. Additionally, add a code-symbol-aware chunker so
RAG chunks respect class/method boundaries rather than just markdown headings.

### 4.2 Dependencies

```
# requirements.txt additions
tree-sitter>=0.21.0
tree-sitter-languages>=1.10.2   # bundles compiled grammars; no network at runtime
```

Verify `tree-sitter-languages` ships compiled wheels for linux-x64, linux-arm64
and darwin-arm64. If not, vendor the compiled .so files under
`src/knowledge/vendored/tree_sitter/` and load them explicitly.

### 4.3 Files to create

```
src/crawler/treesitter_bridge.py       # NEW — parallel API to roslyn_bridge
src/knowledge/symbol_chunker.py        # NEW — CodeSymbolChunker
tests/test_symbol_chunker.py           # NEW
```

### 4.4 treesitter_bridge.py

Same public shape as the Roslyn client:

```python
def is_available() -> bool: ...
def analyze(sln_dir: str, exclude: list[str] | None = None) -> dict: ...
```

Walk `.cs` and `.ts` files, parse with tree-sitter, emit the same JSON shape
the Roslyn bridge returns. `config.yaml` gains:

```yaml
crawler:
  deep_analysis:
    csharp_engine: "auto"   # auto | roslyn | tree_sitter | regex
```

`auto` prefers roslyn → tree_sitter → regex in that order.

### 4.5 CodeSymbolChunker

`src/knowledge/symbol_chunker.py`:

```python
class CodeSymbolChunker:
    """
    Emits one chunk per top-level symbol (class / method) with metadata:
      { file: str, symbol: str, kind: "class"|"method"|"interface"|"record",
        start_line: int, end_line: int, xmldoc: str|None }
    Falls back to MarkdownChunker for non-code files.
    """
    def chunk(self, file_path: str, content: str) -> list[dict]: ...
```

Register in `src/pipeline/ingestion.py`:

```python
if path.suffix in {".cs", ".ts", ".tsx"}:
    chunks = code_chunker.chunk(path, content)
else:
    chunks = markdown_chunker.chunk(path, content)
```

### 4.6 Acceptance criteria

- [ ] `CodeSymbolChunker` on `essa/Opc.Ua/ServerConnector.cs` produces at
      least one chunk per public method with `start_line` and `end_line`
      matching the source.
- [ ] Chunk metadata in ChromaDB includes `symbol`, `start_line`, `end_line`.
- [ ] Falling back to `tree_sitter` when Roslyn is unavailable works without
      config changes.
- [ ] Pure Python test — no network required — passes in `AIRGAP=1`.

---

## Phase 5 — Self-Critique Gate

### 5.1 Goal

Before any DOCX is exported, a reviewer LLM reads the draft + evidence JSON
and returns a verdict. Only CITED + COMPLETE drafts are exported; others are
either retried once or flagged for human review.

### 5.2 Files to create

```
src/rag/self_critique.py       # NEW
tests/test_self_critique.py    # NEW
```

### 5.3 Contract

```python
@dataclass
class CritiqueVerdict:
    overall: Literal["pass", "rework", "fail"]
    sections: list[dict]   # per-section {id, status: CITED|UNCITED|THIN|INCONSISTENT, notes}
    missing_citations: list[str]
    suggested_fixes: list[str]

def critique(
    draft: list[SectionDraft],
    evidence: dict,
    *,
    persona: PersonaId,
    llm,
) -> CritiqueVerdict: ...
```

System prompt:

```
You are a strict technical reviewer. For each section in the draft, confirm:
  1. Every factual sentence has at least one citation of form [file.cs:Lx-Ly] or [doc §x.y].
  2. The section is COMPLETE (not missing required subsections for the persona).
  3. Terminology is consistent across sections.
Return JSON only, matching schema { overall, sections[], missing_citations[], suggested_fixes[] }.
```

### 5.4 Integration

In `persona_composer.compose_all()`, after building the `list[SectionDraft]`
for a persona and before rendering the DOCX:

1. Run `critique(draft, evidence, persona, llm)`.
2. If `overall == "pass"` → render.
3. If `overall == "rework"` → rerun drafting ONCE for the offending sections
   only (preserve the good sections).
4. If `overall == "fail"` after retry → render with a `[DRAFT — needs human
   review]` watermark in the header.

### 5.5 Acceptance criteria

- [ ] Unit test with a fake LLM returning a fail verdict — assert the composer
      watermarks the document.
- [ ] Integration test: crawl `essa/`, compose Architect DOCX, self-critique
      runs and logs sections reviewed.
- [ ] `AIRGAP=1` compliant (uses the configured local LLM).

---

## Phase 6 — Tenant Awareness

### 6.1 Goal

Remove hard-coded `"CoreTax"` strings. Support multiple tenants at runtime
with per-tenant vocabulary and glossary.

### 6.2 Files to modify

```
src/rag/prompts.py          # use {tenant} placeholder
src/rag/personas.py         # PersonaProfile.system_prompt uses {tenant}
src/ui/page_rag_chat.py     # tenant picker (read from config)
config.yaml                 # add tenants:[] and default_tenant
src/models/knowledge.py     # add tenant field to QueryRequest
```

### 6.3 config.yaml additions

```yaml
tenants:
  default:
    display_name: "Lumen"
    short_name: "lumen"
    vocabulary:
      Service: "Service"
    glossary: []            # optional: list[{term, definition}]
  coretax:
    display_name: "CoreTax"
    short_name: "CoreTax"
    vocabulary:
      Service: "Application"
default_tenant: "default"
```

### 6.4 Acceptance criteria

- [ ] `grep -R "CoreTax" src/` returns **zero matches** outside of
      `tests/fixtures/`, `examples/`, `architecture_rules/` (rule files are a
      legitimate tenant artefact and may reference the tenant name).
- [ ] Tenant picker visible in the sidebar; changing tenant immediately
      re-tailors the next chat answer.
- [ ] The DOCX bundle (Phase 2) embeds `{tenant.display_name}` in the header
      and title page.

---

## Phase 7 — Offline Diagram Renderer (Coordinate)

### 7.1 Goal

Ensure every generated DOCX/PDF contains rendered diagram PNGs without calling
`kroki.io` or any external service.

### 7.2 Coordination

Read `docs/TASK_OFFLINE_DIAGRAM_RENDERER.md` first. If that task is already in
flight, align with its approach and **do not reimplement**. If not yet
started, implement the minimal version below.

### 7.3 Minimum implementation

```
src/crawler/diagram_renderer.py    # NEW or extend existing
```

Rendering order (first one available wins):

1. `@mermaid-js/mermaid-cli` (`mmdc`) if installed — best quality. Fully
   offline when bundled with a headless Chromium pre-cached in the container.
2. `plantuml.jar` if installed — Java runtime, offline.
3. `d2` binary if installed.
4. **Pillow fallback** — render a simple "boxes and arrows" sequence diagram
   directly from a small ADT, so a diagram is NEVER missing. Reuse the shape
   from `docs/reference/seq_diagram.py` if preserved.

Always return a PNG path. Log which backend rendered each diagram.

### 7.4 Acceptance criteria

- [ ] `diagram_renderer.render(mermaid_source)` returns a PNG path.
- [ ] With all external renderers uninstalled, Pillow fallback still produces
      a PNG (possibly less pretty, but complete).
- [ ] No call to `kroki.io` or any other external host under `AIRGAP=1`.

---

## Phase 8 — Evaluation Harness

### 8.1 Goal

A golden-set regression test so prompt or model changes don't silently break
answer quality or citation correctness.

### 8.2 Files to create

```
tests/eval/
├── goldens.yaml                # 20–30 Q/A pairs per persona
├── test_rag_eval.py
└── README.md
```

### 8.3 goldens.yaml shape

```yaml
- id: essa_ops_runbook_01
  persona: l2
  tenant: default
  fixture: essa             # points to examples/essa
  question: "How do I restart the essa API pool?"
  must_contain: ["AppPool", "recycle", "appcmd"]
  must_cite: ["README.md", "scripts/"]
  max_tokens: 400
```

### 8.4 Metric functions

```python
def retrieval_precision_at_k(retrieved, expected_files, k=5) -> float: ...
def citation_accuracy(answer: str, repo_root: Path) -> float:
    # Parses [file:line] citations, verifies the file exists and the line range is valid
    ...
def keyword_coverage(answer: str, must_contain: list[str]) -> float: ...
```

### 8.5 CI integration

- `pytest -q tests/eval` runs on every PR.
- Baseline metrics stored in `tests/eval/baseline.json`; fail CI if any metric
  drops by more than 5 percentage points.

### 8.6 Acceptance criteria

- [ ] `tests/eval` runs in < 5 minutes against a local LLM.
- [ ] CI fails if citation_accuracy drops below 0.8.

---

## Phase 9 — Security Hardening

This phase merges outstanding items from `docs/TASK_AIRGAP_HARDENING.md` that
directly touch the new surface area, plus a couple of new items. Coordinate
with that task; do not duplicate fixes.

### 9.1 Zip-Slip

Fix `_extract_uploaded_zip` in `src/ui/page_crawler.py`:

```python
def _safe_extract(zf: ZipFile, dest: Path) -> None:
    dest_resolved = dest.resolve()
    for member in zf.infolist():
        target = (dest / member.filename).resolve()
        if not str(target).startswith(str(dest_resolved)):
            raise ValueError(f"Zip-slip blocked: {member.filename}")
    zf.extractall(dest)
```

### 9.2 AIRGAP enforcement in new modules

Every new module MUST support `AIRGAP=1`:

- `roslyn-bridge` — binds to `127.0.0.1`, refuses to open non-loopback sockets.
- `persona_composer` — no outbound calls.
- `self_critique` — uses the configured local LLM.
- `diagram_renderer` — Pillow fallback guarantees no external dependency.

### 9.3 Startup self-check

Add `src/ops/airgap_probe.py`:

```python
def assert_airgap() -> None:
    if os.environ.get("AIRGAP") != "1":
        return
    # Try to open a non-loopback TCP connection — MUST fail.
    import socket
    s = socket.socket(); s.settimeout(0.5)
    try:
        s.connect(("8.8.8.8", 53))
        raise RuntimeError("AIRGAP violation — outbound reachable")
    except (socket.timeout, OSError):
        pass  # desired
    finally:
        s.close()
```

Call `assert_airgap()` at `app.py` startup and at `roslyn-bridge` startup.

### 9.4 Forbid hard-coded secrets / URLs in new code

Add a `pre-commit` check (or a CI grep) that fails if any file under
`src/crawler/persona_composer.py`, `src/crawler/docx_builder.py`,
`src/rag/personas.py`, `src/rag/self_critique.py`, `tools/roslyn-bridge/**`
matches `https?://[^/].*` except loopback or inside docstrings.

### 9.5 Acceptance criteria

- [ ] Zip-Slip test: craft a malicious zip, assert extraction raises.
- [ ] `AIRGAP=1 ./scripts/start.sh` starts all services; airgap probe logs
      `"airgap verified"`.
- [ ] Grep / pre-commit check in place.

---

## 10. Deliverables & verification checklist (end of engagement)

- [ ] `src/rag/personas.py`, `src/rag/citation_validator.py` in place.
- [ ] `src/crawler/persona_composer.py`, `docx_builder.py`,
      `persona_outlines.py` in place.
- [ ] `tools/roslyn-bridge/` project builds on a connected box; self-contained
      binary runs on the airgap target.
- [ ] `src/crawler/roslyn_bridge.py` and `src/crawler/treesitter_bridge.py`
      both present, both fall back cleanly.
- [ ] `src/knowledge/symbol_chunker.py` registered in ingestion for `.cs/.ts`.
- [ ] `src/rag/self_critique.py` gates DOCX export.
- [ ] `config.yaml` has `tenants:` section; no `"CoreTax"` strings in
      production code paths.
- [ ] Offline diagram renderer produces PNGs in `AIRGAP=1`.
- [ ] `tests/eval/` harness runs in CI with a baseline.
- [ ] `docs/TASK_AIRGAP_HARDENING.md` items that touched this work are closed
      and referenced here.
- [ ] `README.md` updated: "Personas", "KT bundle", "Roslyn bridge (optional)"
      sections added.
- [ ] `scripts/lumen.sh start` brings up Python app + Roslyn bridge together;
      `stop` tears both down.

### 10.1 Smoke test script

Add `scripts/smoke_kt_pro.sh`:

```bash
#!/usr/bin/env bash
set -euo pipefail
export AIRGAP=1
./scripts/start.sh

# 1. Health check
curl -sf http://127.0.0.1:8503/_stcore/health >/dev/null
curl -sf http://127.0.0.1:8080/healthz >/dev/null
curl -sf http://127.0.0.1:5050/healthz >/dev/null || echo "roslyn-bridge not started (optional)"

# 2. Run crawl on bundled essa/ reference
curl -sf -X POST http://127.0.0.1:8080/crawl \
  -H 'Content-Type: application/json' \
  -d '{"sln_path":"./essa/essa.sln","tenant":"default"}' \
  | jq '.artifacts | length' | grep -q 12   # 6 DOCX + 6 PDF

# 3. Persona query
for p in architect developer tester l1 l2 l3; do
  curl -sf -X POST http://127.0.0.1:8080/query \
    -H 'Content-Type: application/json' \
    -d "{\"persona\":\"$p\",\"question\":\"summarise this solution\"}" \
    | jq -e '.answer and (.citations | length > 0)'
done

./scripts/stop.sh
echo "SMOKE OK"
```

Running `scripts/smoke_kt_pro.sh` successfully is the final sign-off for the
whole upgrade.

---

## 11. Rollback plan

Every phase ships behind a feature flag in `config.yaml`:

```yaml
kt_pro:
  personas: true
  citation_enforcement: true
  multi_variant_docs: true
  roslyn_bridge: false       # opt-in because of runtime dep
  tree_sitter: true
  self_critique: true
  tenant_overrides: true
  offline_diagrams: true
  eval_harness_in_ci: true
```

Setting a flag to `false` must restore the previous behaviour exactly. Test
this in `tests/test_feature_flags.py`.

---

## 12. Style / workflow conventions for Claude Code executing this file

- Commit after each phase; message prefix `feat(kt-pro/phase-N): …`.
- When a step here conflicts with an ambiguous tenant rule, **ask the user**
  (Indonesian government / tax / finance tenants have strong airgap + audit
  requirements — prefer the stricter option).
- If a library version is unavailable offline, pin to the nearest version
  already present in `knowledge_base/` or `.venv/` rather than opening egress.
- Keep this file updated — flip `[ ]` to `[x]` as items complete, add notes
  under each phase if an implementation decision differs from the plan.
- Final deliverable is this file fully checked, the `smoke_kt_pro.sh` passing,
  and a short PR description summarising the nine phases.

— END OF TASK —
