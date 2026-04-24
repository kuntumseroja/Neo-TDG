# Task: KT-Pro Orphan-Code Mode — Designing for the No-Original-Owner Case

**Status:** Open (execute alongside `TASK_KT_PRO_UPGRADE.md`)
**Priority:** High — this is the primary business requirement
**Owner:** _unassigned_
**Created:** 2026-04-24
**Branch target:** `main`
**Estimated effort:** 5–8 additional days on top of the main upgrade

> Lumen.AI / Neo-TDG primarily serves teams who have **inherited** a codebase
> — the original developers have left, no documentation exists, only source
> code and maybe a BRD. This file makes the product behave accordingly. It
> does NOT replace `TASK_KT_PRO_UPGRADE.md`; it **amends** it with stricter
> guarantees and three new capabilities. Execute in sandbox
> (`TASK_KT_PRO_SANDBOX.md`) as always.

---

## 1. The reframing

A report generator for the original team can be optimistic — the reader can
mentally correct small inaccuracies. A knowledge system for an **inheritor
team** cannot. One confidently-wrong answer during an incident destroys
platform trust. Design priorities change:

| Principle | Original-team product | Inheritor product (this one) |
|---|---|---|
| Citations | nice-to-have | **non-negotiable** — refuse without evidence |
| Confidence | hidden | **explicit per paragraph** — HIGH / MED / LOW |
| First chat turn | "ask me anything" | **zero-question briefing** per persona |
| Wrong answers | acceptable if rare | catastrophic — erode platform trust |
| Institutional memory | the team has it | **must be captured** via write-back |
| BRD | context for design | **gap-analysis target** — BRD vs code drift is gold |
| Tone | declarative | **observational** — "appears to", "likely", "inferred from naming" |

**Golden rule:** it is always better to say *"I don't know — here is where to
look"* than to guess. For orphaned code, "I don't know" is not a failure, it
is a feature.

---

## 2. Amendments to `TASK_KT_PRO_UPGRADE.md`

Apply these edits before running the phases in the main upgrade file.

### 2.1 Phase 1 — harden citation enforcement

Change `src/rag/citation_validator.py` so that:

- Default `min_ratio` is **1.0** for L1/L2/L3 personas (every paragraph cited).
- Default `min_ratio` is **0.9** for Architect / Developer / Tester personas.
- Add a `refuse_without_evidence: bool = True` flag on `PersonaProfile`.
- When a retry also fails to meet the ratio, **do not** return the answer with
  a warning. Return a structured refusal instead:

```python
{
  "answer": None,
  "refused": True,
  "reason": "Insufficient grounded evidence. See 'hints'.",
  "hints": [
    {"file": "src/core/Taxpayer.cs", "why": "matches topic 'taxpayer validation'"},
    {"file": "docs/BRD_TaxpayerRegistration.pdf", "section": "§3.2"},
  ],
  "suggested_prompts": [
    "Show me the code in src/core/Taxpayer.cs that handles validation",
    "Compare validation logic in code with BRD §3.2"
  ]
}
```

The UI (`page_rag_chat.py`) renders this refusal with the hints as
clickable shortcuts. A refusal is a useful answer — it points the inheritor
at the right file to read.

### 2.2 Phase 1 — confidence tags on every paragraph

Extend the section draft schema (`SectionDraft` in Phase 2 of main upgrade)
with a per-paragraph `confidence` field:

```python
class Paragraph(TypedDict):
    text: str
    citations: list[str]          # ["file.cs:L10-L20", "doc §4.1"]
    confidence: Literal["HIGH", "MED", "LOW"]
    confidence_reason: str        # e.g. "backed by xmldoc", "inferred from naming"
```

Rules for assigning confidence:

- **HIGH** — the claim is directly quoted or mirrored from xmldoc, a README,
  an ADR, or a uploaded BRD.
- **MED** — the claim is derived from strong signals (class name matches
  convention, attribute is present, DI registration visible).
- **LOW** — the claim is pure structural inference (e.g. "this class
  *appears* to handle taxpayer registration because it has methods named
  `RegisterTaxpayer`"). Explicitly hedged.

Render in DOCX as a small coloured pill at the end of each paragraph: green
HIGH, amber MED, grey LOW. Render in chat as a subscript badge.

### 2.3 Phase 2 — add an "Inheritor Briefing" outline item

Prepend a **required** section to every persona's outline:

```python
OutlineItem(
    id="inheritor_briefing",
    title="If you just inherited this system — read this first",
    source="computed",
    max_tokens=1200,
    required=True,
)
```

The composer builds this section from:

- Top 5 findings from `ValidationReport` filtered by persona relevance.
- Top 3 "surprises" (hard-coded values, empty catch blocks, duplicated
  modules, hard-coded hostnames).
- A "services that must be running" list derived from `DIRegistration` +
  `SchedulerInfo` + `IntegrationPoint`.
- A "what breaks on restart" list (any process with non-trivial init time,
  any singleton, any cached session).
- A "last commit / last modified" distribution — helps the reader see which
  parts of the codebase are stable vs recently-touched.

### 2.4 Phase 5 — self-critique enforces the observation frame

Reviewer prompt gains:

```
For every paragraph, confirm it follows the shape:
  Observation → Evidence → Inference (optional) → Confidence
Reject paragraphs that claim intent without an evidence pointer.
Reject paragraphs that state inferences as facts.
```

### 2.5 Persona outlines gain an "Unknown unknowns" appendix

Every persona DOCX ends with a brief appendix listing facts the system
*could not* determine (e.g. "Could not infer the retention policy — no
configuration key, attribute or comment found"). This is the honest-bot
signature — makes it clear what's missing so the inheritor knows what still
needs archaeology.

---

## 3. New capability A — Provenance metadata on every chunk

### 3.1 Goal

Every chunk in ChromaDB and every claim in generated docs carries its
origin. For orphaned code this is almost always "inferred" — but labelling
it as such sets correct expectations.

### 3.2 Metadata schema additions

Extend the chunk metadata in `src/pipeline/ingestion.py`:

```python
metadata.update({
    "source_type": Literal["code", "generated_doc", "brd", "user_contribution", "incident_note", "rule"],
    "authorship":  Literal["inferred", "human_confirmed", "original_developer"],
    "confidence":  Literal["HIGH", "MED", "LOW"],
    "tenant":      str,
    "ingested_at": str,   # ISO 8601
    "source_sha":  str,   # git sha when known
    "persona_affinity": list[PersonaId],  # chunks can be tagged by relevance
})
```

### 3.3 Rules of thumb

- Raw `.cs` chunk → `source_type="code"`, `authorship="original_developer"`,
  `confidence="HIGH"` (the code itself is authoritative).
- Chunk from generated KT doc → `source_type="generated_doc"`,
  `authorship="inferred"`, `confidence` follows the paragraph tag.
- Chunk from uploaded BRD → `source_type="brd"`,
  `authorship="human_confirmed"`, `confidence="HIGH"` (trust the document).
- Chunk from a captured chat answer (see §5) → `source_type="user_contribution"`,
  `authorship="human_confirmed"`, `confidence` from the capturer's rating.

### 3.4 Retrieval uses the metadata

Extend `src/rag/reranker.py` to apply two new score terms:

- `persona_affinity_boost`: +0.2 when the chunk's `persona_affinity` list
  includes the asker's persona.
- `authorship_boost`: +0.1 for `original_developer`, +0.05 for
  `human_confirmed`, 0 for `inferred`.

Tune the weights in `config.yaml`:

```yaml
knowledge_store:
  reranker:
    weights:
      bm25: 0.4
      vector: 0.4
      persona_affinity: 0.15
      authorship: 0.05
```

### 3.5 Acceptance criteria

- [ ] Every newly-ingested chunk carries all seven metadata fields.
- [ ] A backfill migration script (`scripts/migrate_chunk_metadata.py`) tags
      existing chunks with safe defaults (`authorship="inferred"`,
      `confidence="MED"`, `persona_affinity=[]`).
- [ ] Reranker unit test: two identical-content chunks differing only by
      authorship — the `original_developer` one ranks higher.
- [ ] A retrieval query from persona L2 preferentially returns runbook-tagged
      chunks over architecture-tagged chunks when both are equally relevant
      (`tests/test_persona_retrieval.py`).

---

## 4. New capability B — Institutional Memory write-back

### 4.1 Goal

Every time a support engineer uses the chat to solve a real incident, the
solution must be capturable back into the knowledge base so the next engineer
benefits. Over months the accumulated "we hit this, here's the fix" notes
compensate for the missing original documentation.

### 4.2 Files to create

```
src/knowledge/write_back.py          # NEW — queue + persist
src/ui/components_writeback.py       # NEW — "Save this answer" button + review UI
src/api/routes/writeback.py          # NEW — POST /writeback
tests/test_writeback.py              # NEW
knowledge_base/institutional/        # NEW directory — markdown files
```

### 4.3 User flow

Below every chat answer a small button: **"Save this as institutional
knowledge"**. Clicking opens a modal with:

- Title (default: the original question)
- Tags (free-text, suggested from persona and chunk metadata)
- Scope: *this tenant only* | *everyone on this platform*
- Confidence: HIGH / MED / LOW (default MED)
- A textarea pre-filled with the answer — the engineer can edit or expand.

On save, `write_back.save()` writes a Markdown file to
`knowledge_base/institutional/<tenant>/<yyyy-mm-dd>_<slug>.md`, adds a row to
a `institutional_notes` SQLite table, and runs the ingest pipeline on the
new file. The chunk carries
`source_type="user_contribution"`, `authorship="human_confirmed"`.

### 4.4 Review queue

An admin page lists pending institutional notes awaiting review. Reviewer
can: approve (promote `authorship` to `human_confirmed`), edit, or reject.
Unreviewed notes default to `authorship="inferred"` so they don't
over-influence retrieval.

### 4.5 Optional auto-capture

A chat answer marked with thumbs-up twice by different users auto-promotes
to a pending institutional note with default confidence MED. Engineer then
just reviews rather than writing from scratch.

### 4.6 Acceptance criteria

- [ ] Button visible under every chat answer in
      `src/ui/page_rag_chat.py`.
- [ ] `POST /writeback` accepts a payload with title, body, tags, scope,
      confidence; writes MD file; triggers ingest.
- [ ] Saved notes appear in subsequent retrievals (verify via
      `tests/test_writeback.py` + an integration round-trip).
- [ ] Scope=tenant-only chunks never leak to other tenants' queries.
- [ ] Notes survive container restart (persisted to disk, not memory).

---

## 5. New capability C — Code-vs-BRD Gap Analyser

### 5.1 Goal

When a BRD is uploaded alongside a crawled solution, automatically produce a
**Gap Report** — a persona-aware diff between what the BRD asks for and what
the code actually does.

### 5.2 Files to create

```
src/sdlc/gap_analyser.py             # NEW
src/api/routes/gap.py                # NEW — POST /gap
src/ui/page_gap.py                   # NEW — Streamlit page
tests/test_gap_analyser.py           # NEW
```

### 5.3 Contract

```python
@dataclass
class GapItem:
    kind: Literal["missing_in_code", "missing_in_brd", "divergent", "unclear"]
    topic: str                       # e.g. "Taxpayer retention policy"
    brd_ref: str | None              # "BRD §3.2"
    code_ref: str | None             # "Taxpayer.cs:L42"
    observation: str
    confidence: Literal["HIGH", "MED", "LOW"]

@dataclass
class GapReport:
    tenant: str
    brd_id: str
    solution_id: str
    items: list[GapItem]
    generated_at: str
```

### 5.4 Algorithm

1. Ingest the BRD — chunk + embed as normal. Each BRD section becomes a
   chunk with `source_type="brd"`.
2. For each BRD section, ask the LLM to extract *requirements* as structured
   JSON: `{ id, topic, statement, kind: functional|nfr|data|security,
   traceable_to: [] }`.
3. For each extracted requirement, run a RAG query over the **code** chunks
   of the same tenant/solution asking "Does the code implement this?
   Answer with evidence only."
4. Classify the outcome:
   - Strong citation to code → `divergent` if numbers differ, else no gap.
   - No citation to code → `missing_in_code`.
   - Requirement unclear in BRD → `unclear`.
5. Also run the reverse: ask "Which code features have no matching BRD
   requirement?" — produce `missing_in_brd` items.
6. Render a Gap Report DOCX + chat-accessible summary.

### 5.5 UI

`page_gap.py` lets a user pick a BRD (from ingested docs) and a solution
(from crawled reports), runs the analyser, and renders the report as a
sortable table. Each item has a "show code" and "show BRD" button.

### 5.6 Persona filtering

Architect persona: all items.
Developer persona: `missing_in_code` + `divergent`.
Tester persona: `missing_in_code` + `unclear` (things they need test cases
for).
L2 persona: items tagged as NFR or operational.

### 5.7 Acceptance criteria

- [ ] `POST /gap` accepts `{brd_id, solution_id}` and returns a GapReport in
      under 90 seconds for a 50-page BRD against a 100-KLOC solution (on a
      local Ollama model).
- [ ] Every `GapItem` carries either `brd_ref` or `code_ref` (usually both
      when `kind=divergent`).
- [ ] Fixture-based unit test with a small BRD + small code sample produces
      a deterministic list of items.
- [ ] DOCX export uses the same `DocxBuilder` from Phase 2.

---

## 6. UI adjustments beyond the new pages

### 6.1 Chat opening screen — zero-question briefing

When a user opens the chat after a crawl, the system **proactively posts**
their persona's Inheritor Briefing as the first message (from the bot, not
the user). The user can either read it, ask follow-ups, or dismiss.

### 6.2 Answer structure in chat

Every non-trivial answer is formatted as:

```
**Observation.** <what the bot saw in the evidence>
**Evidence.** [file.cs:L12-L34] • [BRD §3.2]
**Inference.** <what the bot concludes — only if applicable>
**Confidence.** HIGH / MED / LOW  — <one-line reason>
**Next step.** <open a file, run a command, ask an ex-owner>
```

Implement as a small template in `src/rag/prompts.py` — the persona system
prompt requires this template.

### 6.3 "Read the code" shortcuts

Every citation in the UI is a link that opens the source file in a side
panel (or copies the path + line to the clipboard for air-gapped shops).
The point: never force the inheritor to re-find the file themselves.

### 6.4 Stack-trace entry point

Elevate `bug_assistant.py` to a **top-level quick action** on the landing
page: "Paste a stack trace". This is the most common arrival pattern for
support engineers who inherit a codebase. The existing tool already does
the work — just move it forward in the UX.

---

## 7. Prompt template — the "Orphan Code Assistant"

Replace the generic system prompt with an orphan-aware one (still persona
+ tenant tokenised):

```
You are the Knowledge Assistant for {tenant}. The original developers of
this codebase are not available. All you know comes from the code, the
uploaded documents, and prior captured knowledge. Therefore:

1. Never state intent you cannot cite. Prefer "appears to", "likely",
   "inferred from <signal>". Confidence must be explicit.
2. Every factual sentence MUST carry a citation of the form
   [file.cs:L<start>-L<end>] or [doc §<section>].
3. If evidence is insufficient, answer: "I don't have grounded evidence
   for this. Here are the files most likely relevant: ...".
4. Prefer Observation → Evidence → Inference → Confidence → Next step.
5. You are talking to a {persona.display_name}. Use their tone: {persona.tone}.
   Avoid: {persona.avoid}. Emphasise: {persona.emphasise}.
6. When asked about a component, also surface 'unknown unknowns' —
   things you could not determine, so the user can go find out.
```

Store this in `src/rag/personas.py` as the shared preamble; each persona
appends its specific voice.

---

## 8. Retrieval strategy updates for orphan code

### 8.1 Prefer the latest code chunks

Stale inferred documentation is dangerous. Retrieval should prefer:

1. `source_type="code"` (the ground truth) over `source_type="generated_doc"`
   when answering *"how does X work?"*
2. `source_type="brd"` when answering *"what is the requirement for X?"*
3. Captured `source_type="user_contribution"` (reviewed) over
   `generated_doc` for runbook-style questions.

Configure per query-mode in `src/rag/query_engine.py`:

```python
SOURCE_PREFERENCE = {
  "explain": ["generated_doc", "code", "user_contribution"],
  "find":    ["code", "generated_doc"],
  "trace":   ["code", "generated_doc"],
  "impact":  ["code", "brd", "generated_doc"],
  "test":    ["brd", "code", "user_contribution"],
}
```

### 8.2 Confidence-aware boosting

When multiple chunks score similarly, break ties by higher confidence. Do
NOT down-weight LOW chunks — they are still useful pointers; the LLM
downstream will mark them as low-confidence in the answer.

---

## 9. Testing strategy for orphan mode

### 9.1 Curated "orphan" fixture

Bundle a deliberately un-documented sample under `tests/fixtures/orphan_app/`
— a small .NET solution with *no* README, *no* ADR, *no* xmldoc — plus a
short BRD that has one contradiction with the code (e.g. retention policy).

### 9.2 Golden tests specific to orphan mode

Add a new test module `tests/eval/test_orphan_mode.py`:

- Ask five persona-specific questions, verify refusal occurs when the fixture
  doesn't contain evidence.
- Verify at least one `GapItem` of kind `divergent` is found between the
  fixture BRD and fixture code (the retention policy mismatch).
- Verify the Inheritor Briefing mentions the "unknown unknowns" from the
  fixture (because the fixture is deliberately scant).

### 9.3 Failure-mode tests

- Remove all xmldoc from a fixture → every generated paragraph is tagged
  LOW confidence.
- Remove the BRD → Gap Analyser returns an empty list with a clear message,
  not an error.
- Remove vector index → chat refuses with a clear "index empty" hint.

---

## 10. Ordering / execution notes for Claude Code

Execute in this order, all inside the sandbox
(`TASK_KT_PRO_SANDBOX.md`):

1. Land the amendments to Phase 1 / Phase 2 / Phase 5 of
   `TASK_KT_PRO_UPGRADE.md` (refusal mode, confidence tags, inheritor
   briefing).
2. §3 Provenance metadata (precedes everything — retrieval logic depends on
   it).
3. §4 Institutional memory write-back (small, high-leverage).
4. §5 Gap Analyser (independent — can be parallelised).
5. §6 UI + §7 prompt template updates.
6. §8 retrieval strategy tuning.
7. §9 tests.
8. Smoke — run `scripts/smoke_kt_pro.sh` + the orphan fixture golden tests.

---

## 11. Deliverables checklist

- [ ] `src/rag/citation_validator.py` enforces `refuse_without_evidence`.
- [ ] `Paragraph` schema has `confidence` + `confidence_reason`.
- [ ] Every persona outline starts with `inheritor_briefing`.
- [ ] Every persona DOCX ends with an "Unknown unknowns" appendix.
- [ ] Chunk metadata includes the seven new fields; reranker uses them.
- [ ] Write-back button + review queue in UI; notes round-trip the index.
- [ ] Gap Analyser produces a GapReport + DOCX for the fixture.
- [ ] Zero-question briefing is posted proactively on first chat turn.
- [ ] "Observation → Evidence → Inference → Confidence → Next step" format
      visible in answers.
- [ ] Stack-trace quick action on the landing page.
- [ ] `tests/fixtures/orphan_app/` + `tests/eval/test_orphan_mode.py`.
- [ ] README updated: a section titled "Designed for inherited codebases"
      explains the principles above to new users.

---

## 12. Non-goals

- **Reconstructing original developer intent.** Do not claim to know what
  the original team *meant*. Only state what the code does and surface
  inferences with confidence.
- **Replacing domain experts.** Business rules with no trace in code + BRD
  must still be learned from humans. The platform's role is to make that
  gap visible, not to paper over it.
- **Heavy static reasoning.** Keep symbolic analysis to what Roslyn /
  tree-sitter syntactic mode gives. Deep semantic analysis is out of scope
  for orphan mode — the ROI is in better grounding, not fancier analysis.

— END OF TASK —
