# Task: KT-Pro Document Style — Match the ESSA Reference Quality

**Status:** Open (execute as part of Phase 2 of `TASK_KT_PRO_UPGRADE.md`)
**Priority:** High — output quality is the product
**Owner:** _unassigned_
**Created:** 2026-04-24
**Estimated effort:** 2 days

> This file nails the **visual and structural quality bar** for every DOCX
> KT-Pro emits. The bar is the ESSA KT reference document bundled at
> `docs/reference/ESSA_KT_Document_reference.docx`. Claude Code must reach
> that quality — not a generic python-docx output.
>
> The reference build scripts are in `docs/reference/` and are verbatim the
> scripts that produced the ESSA document. They are JavaScript (docx-js) +
> Python (Pillow). This task translates them into a **pure Python** builder
> that slots into Neo-TDG at `src/crawler/docx_builder.py`.

---

## 1. Reference artefacts (read first)

```
docs/reference/
├── ESSA_KT_Document_reference.docx       # the quality target — open in Word
├── essa_build_reference.js               # working docx-js builder (source of truth)
├── essa_seq_diagram.py                   # Pillow sequence diagram
├── essa_other_diagrams.py                # context / module / topology diagrams
├── essa_design_diagrams.py               # current-vs-target / persona matrix / roadmap
├── fig_sequence.png                      # sample output — sequence diagram
├── fig_current_vs_target.png             # sample output — architecture comparison
└── fig_persona_matrix.png                # sample output — persona × variant matrix
```

Open `ESSA_KT_Document_reference.docx` in Word or LibreOffice before starting.
That is the target.

---

## 2. Style tokens (do not deviate)

### 2.1 Colors (hex, `#` omitted where used in Python)

| Token | Hex | Where used |
|---|---|---|
| `primary` | `0F6FC6` | H1 heading text, callout rule/label, table header fill |
| `primary_dark` | `1F4E79` | H2 heading text, figure captions (optional), running header |
| `text_default` | `333333` | H3, body text |
| `text_muted` | `666666` | figure captions, footer pagination, cover meta |
| `bg_callout` | `EAF3FB` | callout background shading |
| `bg_code` | `F2F2F2` | code block shading |
| `row_zebra` | `F7F9FC` | alternating table rows |
| `border_table` | `BFBFBF` | table cell borders |
| `red_warn` | `C00000` | callout label when the content is a warning |

### 2.2 Typography

| Element | Font | Size | Weight | Color |
|---|---|---|---|---|
| Body | Calibri | 11pt (22 half-points) | regular | `text_default` |
| H1 | Calibri | 17pt | bold | `primary` |
| H2 | Calibri | 14pt | bold | `primary_dark` |
| H3 | Calibri | 12pt | bold | `text_default` |
| Cover title | Calibri | 36–42pt | bold | `primary` |
| Cover subtitle | Calibri | 20pt | bold | `text_default` |
| Code block | Consolas | 9pt | regular | black (on `bg_code`) |
| Table header | Calibri | 10pt | bold | white (on `primary`) |
| Table cell | Calibri | 10pt | regular | `text_default` |
| Figure caption | Calibri | 9pt | italic | `text_muted` |
| Footer | Calibri | 9pt | regular | `text_muted` |
| Running header | Calibri | 9pt | italic | `text_muted` |

### 2.3 Page layout

- Page size **US Letter** (8.5 × 11 in). `python-docx` defaults to Letter —
  verify in `section.page_width`.
- Margins **1 inch** on all sides.
- Heading spacing: H1 `before=18pt after=8pt`, H2 `before=12pt after=6pt`,
  H3 `before=9pt after=5pt`.
- Paragraph spacing: `after=6pt`, line spacing `1.15`.

### 2.4 Structural sections (every DOCX must contain all, in this order)

1. **Cover page** (title, subtitle, audience line, status line, date).
2. **Document Control** (two-column key/value table).
3. **Revision History** (four-column table).
4. **Contents** (static TOC — numbered list of the section titles).
5. **Body** — section 1 through N per the persona outline.
6. **References appendix** — list of cited files with line ranges.
7. **"Unknown unknowns" appendix** (see `TASK_KT_PRO_ORPHAN_MODE.md §2.5`).
8. **End-of-document mark** — centered italic "— End of Document —".

### 2.5 Header / Footer

- Header (right-aligned): `{tenant} — KT for {persona}`, italic, `text_muted`.
- Footer (centered): `Confidential — Internal KT  •  Page X / Y`, `text_muted`.

---

## 3. Minimum element gallery (every KT must use these)

Lift these straight from the reference:

- **Cover page** with centered large-title + italic subtitle + centered
  "Document Type / Audience / Status / Date" rows (see
  `essa_build_reference.js` lines searching for "Cover").
- **Key/value tables** (e.g. Document Control) — left column is bold field
  name, right column is value. Widths 2400 / 7360 DXA.
- **Multi-column tables** — header row with `primary` fill + white bold
  text; body rows with zebra `row_zebra`. Use DXA widths that sum to 9760
  (US Letter content width = 9360, with some slack).
- **Bulleted lists** using numbered config (never unicode `•` characters).
- **Numbered lists** for procedures.
- **Code blocks** — full-width paragraph with `bg_code` shading, Consolas.
- **Callouts** — full-width paragraph with `bg_callout` shading, bold
  coloured label, then body text. Used for operational notes, warnings
  (use `red_warn` label), and "Action for Ops" moments.
- **Figures** — centered `ImageRun` equivalent (embedded PNG), caption
  immediately below, italic + muted, formatted "`Figure X.Y — <caption>`".
  Include `alt text` on every image.
- **Page breaks** — always inside a paragraph (never standalone).

---

## 4. Complete `src/crawler/docx_builder.py` (starter implementation)

Drop this file into `src/crawler/`. It is a minimum viable implementation
that achieves the style bar. Extend it as Phase 2 progresses; do not
downgrade the defaults.

```python
"""DocxBuilder — ESSA-quality DOCX builder for KT-Pro.

Usage:
    b = DocxBuilder(
        title="ESSA Solution",
        subtitle="Knowledge Transfer for IT Operations",
        tenant="default",
        persona="l2",
    )
    b.cover(audience="Application Support (L1/L2) and L3 Developers",
            status="Draft v1.0", date="April 2026")
    b.h1("1. Executive Summary")
    b.p("ESSA is a C# / .NET gateway between an OPC UA server ...")
    b.h2("1.1 Why it matters")
    b.bullet("Industrial data gateway")
    b.bullet("Referenced by BI dashboards")
    b.callout("Operational note", "Every call opens a new session ...")
    b.table(header=["Project", "Type", "Purpose"],
            rows=[...],
            widths_dxa=[2400, 2200, 4760])
    b.figure("figures/fig_sequence.png",
             caption="Figure 4.1 — End-to-end sequence",
             alt_text="Seven-lane sequence diagram of POST /history-raw-data",
             width_inches=6.5)
    b.save("out/ESSA_L2_KT.docx")
"""
from __future__ import annotations
from pathlib import Path
from typing import Literal
from docx import Document
from docx.document import Document as DocType
from docx.shared import Pt, RGBColor, Inches, Emu
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_ALIGN_VERTICAL, WD_TABLE_ALIGNMENT
from docx.oxml.ns import qn, nsmap
from docx.oxml import OxmlElement

# ---- style tokens ------------------------------------------------------
PRIMARY       = RGBColor(0x0F, 0x6F, 0xC6)
PRIMARY_DARK  = RGBColor(0x1F, 0x4E, 0x79)
TEXT_DEFAULT  = RGBColor(0x33, 0x33, 0x33)
TEXT_MUTED    = RGBColor(0x66, 0x66, 0x66)
RED_WARN      = RGBColor(0xC0, 0x00, 0x00)
WHITE         = RGBColor(0xFF, 0xFF, 0xFF)

BG_CALLOUT = "EAF3FB"
BG_CODE    = "F2F2F2"
ROW_ZEBRA  = "F7F9FC"
TABLE_HDR  = "0F6FC6"
CELL_BORDER = "BFBFBF"

# ---- helpers -----------------------------------------------------------
def _set_cell_shading(cell, fill_hex: str) -> None:
    tcPr = cell._tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"), fill_hex)
    tcPr.append(shd)

def _set_paragraph_shading(para, fill_hex: str) -> None:
    pPr = para._p.get_or_add_pPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"), fill_hex)
    pPr.append(shd)

def _set_cell_borders(cell, color_hex: str = CELL_BORDER, sz: int = 4) -> None:
    tcPr = cell._tc.get_or_add_tcPr()
    tcBorders = OxmlElement("w:tcBorders")
    for edge in ("top", "left", "bottom", "right"):
        border = OxmlElement(f"w:{edge}")
        border.set(qn("w:val"), "single")
        border.set(qn("w:sz"), str(sz))
        border.set(qn("w:color"), color_hex)
        tcBorders.append(border)
    tcPr.append(tcBorders)

def _add_field(paragraph, instr_text: str) -> None:
    """Insert a Word field like PAGE, NUMPAGES."""
    run = paragraph.add_run()
    fldChar1 = OxmlElement("w:fldChar")
    fldChar1.set(qn("w:fldCharType"), "begin")
    instrText = OxmlElement("w:instrText")
    instrText.text = instr_text
    fldChar2 = OxmlElement("w:fldChar")
    fldChar2.set(qn("w:fldCharType"), "end")
    run._r.append(fldChar1); run._r.append(instrText); run._r.append(fldChar2)

def _set_cell_width(cell, width_twips: int) -> None:
    tcPr = cell._tc.get_or_add_tcPr()
    tcW = OxmlElement("w:tcW")
    tcW.set(qn("w:w"), str(width_twips))
    tcW.set(qn("w:type"), "dxa")
    tcPr.append(tcW)

# ---- builder -----------------------------------------------------------
class DocxBuilder:
    def __init__(self, title: str, subtitle: str, tenant: str, persona: str):
        self.doc: DocType = Document()
        self.title = title
        self.subtitle = subtitle
        self.tenant = tenant
        self.persona = persona
        self._setup_styles()
        self._setup_page()
        self._setup_numbering()
        self._setup_headers_footers()

    # ---- setup ----
    def _setup_styles(self) -> None:
        base = self.doc.styles["Normal"]
        base.font.name = "Calibri"
        base.font.size = Pt(11)
        base.font.color.rgb = TEXT_DEFAULT
        pf = base.paragraph_format
        pf.space_after = Pt(6)
        pf.line_spacing = 1.15

        def hdg(level: int, size_pt: int, color: RGBColor, before: int, after: int):
            s = self.doc.styles[f"Heading {level}"]
            s.font.name = "Calibri"; s.font.bold = True
            s.font.size = Pt(size_pt); s.font.color.rgb = color
            s.paragraph_format.space_before = Pt(before)
            s.paragraph_format.space_after  = Pt(after)
        hdg(1, 17, PRIMARY,      18, 8)
        hdg(2, 14, PRIMARY_DARK, 12, 6)
        hdg(3, 12, TEXT_DEFAULT,  9, 5)

    def _setup_page(self) -> None:
        for section in self.doc.sections:
            section.top_margin = section.bottom_margin = Inches(1)
            section.left_margin = section.right_margin = Inches(1)

    def _setup_numbering(self) -> None:
        # python-docx cannot define new numbering definitions cleanly without
        # editing the template. We rely on the built-in 'List Bullet' and
        # 'List Number' styles which do respect numbering via numbering.xml.
        pass

    def _setup_headers_footers(self) -> None:
        section = self.doc.sections[0]
        # Header — right-aligned, italic, muted
        header_para = section.header.paragraphs[0]
        header_para.alignment = WD_ALIGN_PARAGRAPH.RIGHT
        run = header_para.add_run(f"{self.tenant} — KT for {self.persona}")
        run.italic = True; run.font.size = Pt(9); run.font.color.rgb = TEXT_MUTED

        # Footer — centered, page X / Y
        footer_para = section.footer.paragraphs[0]
        footer_para.alignment = WD_ALIGN_PARAGRAPH.CENTER
        r0 = footer_para.add_run("Confidential — Internal KT  •  Page ")
        r0.font.size = Pt(9); r0.font.color.rgb = TEXT_MUTED
        _add_field(footer_para, "PAGE")
        r1 = footer_para.add_run(" / ")
        r1.font.size = Pt(9); r1.font.color.rgb = TEXT_MUTED
        _add_field(footer_para, "NUMPAGES")

    # ---- cover ----
    def cover(self, *, audience: str, status: str, date: str) -> None:
        d = self.doc
        # big title
        p = d.add_paragraph(); p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        r = p.add_run(self.title); r.bold = True; r.font.size = Pt(42)
        r.font.color.rgb = PRIMARY
        # spacer
        for _ in range(2): d.add_paragraph()
        # subtitle
        p = d.add_paragraph(); p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        r = p.add_run(self.subtitle); r.bold = True; r.font.size = Pt(20)
        r.font.color.rgb = TEXT_DEFAULT
        # meta rows
        for label, value in [
            ("Document Type", "Knowledge Transfer / Runbook"),
            ("Audience", audience),
            ("Status", status),
            ("Date", date),
        ]:
            p = d.add_paragraph(); p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            rb = p.add_run(f"{label}: "); rb.bold = True
            rt = p.add_run(value); rt.font.size = Pt(11)
        # page break after cover
        self.page_break()

    # ---- content ----
    def h1(self, text: str) -> None: self.doc.add_heading(text, level=1)
    def h2(self, text: str) -> None: self.doc.add_heading(text, level=2)
    def h3(self, text: str) -> None: self.doc.add_heading(text, level=3)

    def p(self, text: str, *, bold: bool = False, italic: bool = False) -> None:
        para = self.doc.add_paragraph()
        r = para.add_run(text); r.bold = bold; r.italic = italic

    def bullet(self, text: str) -> None:
        self.doc.add_paragraph(text, style="List Bullet")

    def bullet_bold(self, title: str, rest: str) -> None:
        para = self.doc.add_paragraph(style="List Bullet")
        rt = para.add_run(title); rt.bold = True
        para.add_run(rest)

    def numbered(self, text: str) -> None:
        self.doc.add_paragraph(text, style="List Number")

    def code(self, text: str) -> None:
        para = self.doc.add_paragraph()
        # preserve newlines
        for i, line in enumerate(text.splitlines()):
            if i > 0:
                para.add_run().add_break()
            r = para.add_run(line)
            r.font.name = "Consolas"; r.font.size = Pt(9)
        _set_paragraph_shading(para, BG_CODE)

    def callout(self, label: str, text: str, *, warn: bool = False) -> None:
        para = self.doc.add_paragraph()
        r0 = para.add_run(f"{label}:  "); r0.bold = True
        r0.font.color.rgb = RED_WARN if warn else PRIMARY
        para.add_run(text)
        _set_paragraph_shading(para, BG_CALLOUT)

    def table(self, *, header: list[str], rows: list[list[str]],
              widths_dxa: list[int], header_fill: str = TABLE_HDR,
              zebra: str = ROW_ZEBRA) -> None:
        assert len(widths_dxa) == len(header)
        t = self.doc.add_table(rows=1 + len(rows), cols=len(header))
        t.autofit = False
        t.alignment = WD_TABLE_ALIGNMENT.CENTER
        # header row
        hdr = t.rows[0]
        for i, h in enumerate(header):
            cell = hdr.cells[i]
            cell.text = ""
            p = cell.paragraphs[0]
            r = p.add_run(h); r.bold = True
            r.font.color.rgb = WHITE; r.font.size = Pt(10)
            _set_cell_shading(cell, header_fill)
            _set_cell_borders(cell)
            _set_cell_width(cell, widths_dxa[i])
            cell.vertical_alignment = WD_ALIGN_VERTICAL.CENTER
        # body rows
        for ri, row in enumerate(rows):
            tr = t.rows[ri + 1]
            fill = zebra if ri % 2 == 0 else None
            for i, val in enumerate(row):
                cell = tr.cells[i]
                cell.text = ""
                p = cell.paragraphs[0]
                r = p.add_run(str(val))
                r.font.size = Pt(10); r.font.color.rgb = TEXT_DEFAULT
                if fill:
                    _set_cell_shading(cell, fill)
                _set_cell_borders(cell)
                _set_cell_width(cell, widths_dxa[i])
                cell.vertical_alignment = WD_ALIGN_VERTICAL.CENTER

    def figure(self, image_path: str | Path, *, caption: str,
               alt_text: str, width_inches: float = 6.5) -> None:
        image_path = str(image_path)
        para = self.doc.add_paragraph()
        para.alignment = WD_ALIGN_PARAGRAPH.CENTER
        run = para.add_run()
        run.add_picture(image_path, width=Inches(width_inches))
        # alt text on the inline shape
        self._set_last_image_alt(alt_text)
        # caption
        cap = self.doc.add_paragraph()
        cap.alignment = WD_ALIGN_PARAGRAPH.CENTER
        r = cap.add_run(caption); r.italic = True
        r.font.size = Pt(9); r.font.color.rgb = TEXT_MUTED

    def _set_last_image_alt(self, alt_text: str) -> None:
        # find the last <w:drawing> and stuff in a <wp:docPr descr="...">
        body = self.doc.element.body
        docPrs = body.findall(".//" + qn("wp:docPr"))
        if docPrs:
            docPrs[-1].set("descr", alt_text)
            docPrs[-1].set("title", alt_text[:64])

    def page_break(self) -> None:
        p = self.doc.add_paragraph()
        p.add_run().add_break(break_type=7)  # WD_BREAK.PAGE

    # ---- lifecycle ----
    def save(self, out_path: str | Path) -> Path:
        out_path = Path(out_path)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        self.doc.save(out_path)
        return out_path
```

---

## 5. Diagram generation — mandatory minimum

Every KT must include at least these diagrams (render as PNG, embed via
`figure()`):

| Fig | Type | Source |
|---|---|---|
| 1 | **System Context** | tenant name, crawled solution, external integrations from `integration_discovery` |
| 2 | **Module Dependency Graph** | project references from `dependency_extractor` + NuGet graph |
| 3 | **Sequence diagram** | one per top endpoint (≥ 1 total) |
| 4 | **Deployment Topology** | IaC + Dockerfile (when present) |
| 5 | **Persona × Section Matrix** (appendix) | per-persona doc only |

Renderer order (first one available wins — same as
`TASK_KT_PRO_UPGRADE.md §7`):

1. `mmdc` (Mermaid CLI) if installed.
2. `plantuml.jar` if installed.
3. `d2` binary if installed.
4. **Pillow fallback** — verbatim port of
   `docs/reference/essa_seq_diagram.py` +
   `docs/reference/essa_other_diagrams.py` into
   `src/crawler/diagram_renderer_pillow.py`.

The Pillow fallback guarantees a diagram is never missing. Air-gapped
tenants will almost always hit this path; invest in it.

**Pillow renderer helpers that MUST exist** (copy signatures from
`essa_other_diagrams.py`):

- `rounded(draw, x, y, w, h, fill, outline=None, r=12)`
- `centered(draw, x, y, w, h, lines, color, fonts)`
- `arrow(draw, x1, y1, x2, y2, color, width, head, dashed)`
- `title(draw, canvas_width, text)`

---

## 6. OOXML validation — avoid the known traps

The ESSA build hit one nasty bug worth flagging:

**Border-order bug.** docx-js emits child elements of `<w:pBdr>` in object
key order. If the schema expects `top → left → bottom → right` and you
pass them in a different order, Word opens the file but `xmllint --schema`
fails. `python-docx` generally does the right thing when you use `Cell`
borders, but if you drop raw OXML always emit in the canonical order.

Install a validator step:

```bash
pip install docx-validator   # optional — uses the ECMA-376 schemas
```

Or simpler: round-trip through `Document(path)` — if it raises, the file
is malformed.

Add `tests/test_docx_style.py`:

```python
def test_generated_docx_opens_and_has_required_sections(tmp_path):
    from src.crawler.docx_builder import DocxBuilder
    b = DocxBuilder("T", "S", "default", "l2")
    b.cover(audience="Ops", status="v1", date="2026-04-24")
    b.h1("1. Heading"); b.p("Body."); b.code("x = 1")
    b.callout("Note", "hello")
    b.table(header=["A","B"], rows=[["1","2"]], widths_dxa=[4800, 4800])
    out = b.save(tmp_path / "t.docx")
    # round-trip — will raise if malformed
    from docx import Document
    assert Document(str(out)).paragraphs
```

---

## 7. Optional — PDF conversion quality

Prefer **LibreOffice headless** over `fpdf2` for KT-Pro bundle PDFs:

```bash
soffice --headless --convert-to pdf --outdir ./out ./out/file.docx
```

Reasons: better table rendering, handles images cleanly, renders Consolas
code blocks without glyph gaps. Keep `fpdf2` only for the legacy
Markdown-only PDF the current pipeline already produces.

When `shutil.which("soffice") is None`:
- do NOT silently fall back to fpdf2 for the KT bundle (lower quality would
  be confusing);
- emit DOCX only, log a single warning pointing at the LibreOffice install
  instructions in `docs/SANDBOX.md` (or wherever the operator guide lives).

---

## 8. Acceptance criteria

- [ ] `src/crawler/docx_builder.py` present and imports cleanly.
- [ ] `tests/test_docx_style.py` passes.
- [ ] A generated DOCX for persona `l2` on the bundled `essa/` sample, when
      opened in Word, visually matches `docs/reference/ESSA_KT_Document_reference.docx`
      on these checkpoints:
    - Cover page looks the same shape (big blue title, subtitle, meta rows).
    - Running header right-aligned italic muted.
    - Footer centred with `Page X / Y` live fields.
    - H1 blue, H2 dark blue, H3 dark grey.
    - Tables: header row blue, white bold text, zebra-striped body, thin
      grey borders, cell padding readable.
    - At least one callout with blue label + light-blue background.
    - At least one code block grey-shaded Consolas.
    - At least one figure with centered image + italic muted caption.
- [ ] Image alt-text is set on every figure (accessibility + future RAG
      metadata).
- [ ] When rendered to PDF via LibreOffice the layout does not regress (no
      orphan figures, no blown-out tables).
- [ ] `ruff` / linter passes on the new file.

---

## 9. Dependencies to add

`requirements.txt`:

```
python-docx>=1.1.0
Pillow>=10.0.0
```

That's it. LibreOffice is a system-level dependency installed via apt on
the host (already assumed in the deployment guide). Mermaid CLI /
PlantUML / D2 remain optional; the Pillow fallback covers the air-gap case.

---

## 10. Where this plugs into the broader plan

- This TASK file is consumed by **Phase 2** of `TASK_KT_PRO_UPGRADE.md`
  (multi-variant DOCX bundle).
- The `DocxBuilder` is also used by **TASK_KT_PRO_ORPHAN_MODE.md §5** (Gap
  Analyser) to render the Gap Report.
- Style tokens are shared with the **Pillow diagram fallback** so diagrams
  match the doc palette.
- The PDF export path feeds into the smoke test in
  `TASK_KT_PRO_UPGRADE.md §10.1`.

— END OF TASK —
