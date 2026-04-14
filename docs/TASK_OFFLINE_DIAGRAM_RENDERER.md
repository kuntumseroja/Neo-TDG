# Task: Offline Diagram Renderer (replace kroki.io)

**Status:** Open
**Priority:** Medium (blocks air-gap item 4.1)
**Owner:** _unassigned_
**Created:** 2026-04-14
**Related:** `docs/TASK_AIRGAP_HARDENING.md` (item 4.1)
**Branch target:** `main`
**Estimated effort:** 1 – 2 days (full native SVG path)

---

## 1. Background

Lumen.AI renders mermaid diagrams two different ways today:

- **Streamlit preview** → `streamlit_mermaid` (client-side JS, already offline
  once bundled into the image).
- **PDF export** → `src/crawler/doc_generator.py : _fetch_mermaid_png()` calls
  `https://kroki.io/mermaid/png/...` to rasterize mermaid to PNG.

The kroki.io call is the single biggest blocker to a fully air-gapped build
and is a primary driver of slow PDF export (one HTTPS round-trip per diagram,
up to 12 s timeout each). This task replaces it with a fully local renderer
that produces a diagram usable in **both HTML and PDF** without network.

## 2. Goals

- Zero outbound HTTP during doc generation.
- Same (or better) visual fidelity than kroki PNG.
- Vector-friendly — crisp at any PDF zoom level.
- No change to what the LLM generates. The generator keeps emitting mermaid;
  the renderer is responsible for turning it into something embeddable.
- Streamlit preview keeps working (no UX regression).

## 3. Options evaluated

| Option | Offline | HTML | PDF | Types supported | Weight | Notes |
|---|---|---|---|---|---|---|
| **Graphviz (`dot`)** | ✅ single binary ~5 MB | SVG | SVG (via svglib/reportlab) or PNG | graph, ER, class | needs binary in image | De-facto standard, every Linux repo has it |
| **D2 (`d2lang.com`)** | ✅ single Go binary ~15 MB | SVG | SVG/PNG | graph, sequence, class, ER, arch | single binary | Nicer defaults than dot |
| **mermaid-cli (`mmdc`)** | ✅ but needs Node + headless Chromium | works today | SVG/PNG | all Mermaid features | **~300 MB** | **Rejected** — too heavy for air-gap |
| **PlantUML** | ✅ JAR | PNG/SVG | PNG/SVG | Widest (C4, sequence, class, state, use-case) | ~10 MB JAR + JRE | Good fit only if Java already in stack |
| **`diagrams` (mingrammer)** | ✅ (needs Graphviz) | PNG/SVG | PNG/SVG | Cloud architecture icons | pip + Graphviz | Great for cloud icons, weak for sequence |
| **Matplotlib + schemdraw** | ✅ pure Python | SVG | native PDF via `backend_pdf` | flow only (no sequence) | already installed | Neutral, limited diagram range |
| **Direct SVG from Python** | ✅ zero deps | inline `<svg>` | `svglib` → `reportlab` | whatever we write | 0 MB extra | Maximum control, most code to write |

## 4. Recommendation

**Two-track strategy, mermaid stays the source of truth:**

### Track A — HTML preview (no change)
Keep `streamlit_mermaid`. Already offline. Ship as-is.

### Track B — PDF export: native Python SVG renderer for our own diagram types
Since Lumen.AI *owns the generator* (`_arch_*` methods in `doc_generator.py`),
we can emit **both** mermaid (for the HTML preview) **and** a structural
representation (layer→nodes, nodes→edges) that a tiny Python SVG writer turns
into an embeddable `<svg>` element.

Diagrams covered natively:
- Clean Architecture (`_arch_5_clean_architecture`) — grid of labeled
  rectangles with arrows, trivial SVG.
- Context Map / architecture-beta view (`_arch_2_context_map`) — same
  pattern.
- DDD strategic-pattern graph — labeled edges, simple.
- Dependency Graph (`_section_dependency_graph`) — layered grid already
  computed by the generator.

Diagrams **not** covered natively (kept as fenced mermaid code blocks in PDF,
full rendering only in HTML preview):
- Sequence diagrams (`_arch_6_sequence_diagrams`) — non-trivial layout.
- Class diagram (`_arch_3_domain_model : Class Diagram`) — non-trivial
  layout.

This leaves 4 of the 6 diagram types with full vector rendering in both HTML
and PDF. The 2 that stay mermaid-only still render correctly in the Streamlit
preview (our richest surface) and appear as readable fenced code in the PDF
(same as today when kroki fails). Net improvement, zero regression.

### Fallback chain (if/when we want 100 % coverage)
If a deployment needs sequence + class diagrams rendered in PDF too, add an
**optional** Graphviz detection step:

```
if AIRGAP and which("dot"):
    use graphviz for sequence + class (via DOT translation)
elif AIRGAP and which("d2"):
    use D2
else:
    emit fenced mermaid code block in PDF
```

This keeps the default (air-gap image) small. Operators who can afford a
Graphviz binary get full coverage.

## 5. Acceptance criteria

- [ ] `AIRGAP=1 streamlit run app.py` → generating + downloading the
      Architecture Doc PDF performs **zero** outbound connections.
- [ ] PDF export time for an 8-diagram doc drops from ~20 s (kroki,
      network-dependent) to **< 2 s**.
- [ ] Clean-Arch, Context-Map, DDD-Map, Dependency-Graph render as
      vector SVG in the PDF (verified by opening the PDF and searching for
      `<svg` tags in the extracted content).
- [ ] HTML preview (`streamlit_mermaid` path) unchanged — same mermaid
      source, same look.
- [ ] No new pip dependency beyond `svglib` (pure Python, MIT, ~600 kB).
- [ ] Existing regression suite green (18 pytest + 9 smoke checks).
- [ ] New unit test: given a fabricated CleanArch structure,
      `_render_svg_cleanarch()` produces valid SVG with expected node/edge
      counts.

## 6. Implementation plan (when scheduled)

1. Add `src/crawler/svg_diagrams.py` with `render_cleanarch()`,
   `render_context_map()`, `render_ddd_map()`, `render_dependency_graph()`.
   Each takes the already-classified data structures (from
   `_classify_layer_artifacts()`, etc.) and returns an SVG string.
2. Layout: simple grid — layers as rows (Clean Arch) or columns (Context
   Map); fixed box width = longest label × avg char width + padding.
3. Arrows: straight lines + arrowhead marker; curved for same-layer
   back-refs (rare case).
4. Styling: match IBM Carbon palette already in `theme.py` for consistency
   with the Streamlit UI.
5. Embed into PDF: `svglib.svg2rlg(StringIO(svg_str))` → reportlab flowable
   → added to the current fpdf2 (or reportlab) document.
6. Detection: if `AIRGAP` is false AND kroki is reachable, keep current
   kroki path as a developer convenience. If `AIRGAP` is true, always use
   the local SVG renderer.
7. Add `tests/test_svg_diagrams.py`:
   - shape/count assertions,
   - snapshot test against a golden SVG file for regression visibility.

## 7. Risks / open questions

- **fpdf2 SVG support** is limited. If we keep fpdf2, may need to convert
  SVG → PNG via `cairosvg` (adds `libcairo` dep) or swap to `reportlab`
  which has first-class SVG via `svglib`. **Spike first.**
- **Font embedding in PDF SVG**: if we use IBM Plex in the SVG, the PDF
  needs the font embedded or text becomes unreadable. Easier path: render
  text as plain system-serif in SVG and accept the cosmetic difference, OR
  use `svglib`'s text-to-path conversion.
- **No auto-layout for sequence/class** is a conscious scope cut — if
  someone later needs them, the Graphviz fallback from §4 is the answer.

## 8. Non-goals

- Replacing Mermaid as the LLM output format. We continue to generate
  mermaid; only the rasterizer changes.
- Supporting arbitrary mermaid features beyond what `_arch_*` methods emit
  today. Our diagrams are a small, controlled subset.
- A full mermaid parser in Python. We bypass mermaid entirely in the PDF
  path — the structured data exists before mermaid is ever stringified.

## 9. Decision log

- **2026-04-14**: User asked for alternatives to mermaid that work inline in
  both HTML and PDF. Evaluated 7 options. Chose native Python SVG for our 4
  grid-style diagrams + keep mermaid in preview + fenced-code fallback in
  PDF for sequence/class. Graphviz kept as optional fallback path.
  Recorded as task, not prototyped.
