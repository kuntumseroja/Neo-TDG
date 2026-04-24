"""Compose six per-persona DOCX (+ optional PDF) from a CrawlReport.

Stitches together:
  * `CrawlReport` — structured crawl output (projects, endpoints, …)
  * `ValidationReport` — `architecture_validator` violations
  * `RAGQueryEngine` — persona-aware answers for narrative sections
  * `DocxBuilder` — the python-docx styling layer
  * `persona_outlines.outline_for(...)` — the per-persona section list

Gated on the `kt_pro.docx_bundle.enabled` feature flag at the caller. This
module itself has no flag check — if you call `compose_all()`, you get the
bundle.

PDF conversion is opportunistic: we call `soffice --headless --convert-to
pdf` when it's on PATH, otherwise we log one warning and return DOCX only.
Air-gap safe — no outbound calls from this module itself.

See docs/TASK_KT_PRO_UPGRADE.md §Phase 2.
"""
from __future__ import annotations

import logging
import re
import shutil
import subprocess
from pathlib import Path
from typing import Optional

from src.crawler.docx_builder import DocxBuilder
from src.crawler.persona_outlines import OutlineItem, outline_for
from src.models.crawler import CrawlReport
from src.models.sdlc import ValidationReport
from src.rag.personas import PERSONAS, PersonaId

logger = logging.getLogger(__name__)


_DEFAULT_PERSONAS: tuple[PersonaId, ...] = (
    "architect", "developer", "tester", "l1", "l2", "l3",
)


def compose_all(
    report: CrawlReport,
    validation: Optional[ValidationReport],
    *,
    tenant: str,
    out_dir: str,
    rag_engine=None,
    personas: Optional[list[PersonaId]] = None,
    render_pdf: bool = True,
) -> list[Path]:
    """Build one DOCX (and optionally PDF) per persona.

    Args:
        report: The crawl result. Required.
        validation: Optional `ValidationReport` (rules / secure-coding
            output). When None, `source="rules"` sections render a short
            placeholder instead of violations.
        tenant: Display string in the header (e.g. "CoreTax").
        out_dir: Output directory. Created if missing.
        rag_engine: Any object with a `.query(question, persona=...)`
            method returning an object with `.answer` and `.sources`
            (duck-typed against `RAGQueryEngine`). When None, `rag`
            sections get a one-line fallback so the bundle still renders.
        personas: Restrict to a subset — defaults to all six.
        render_pdf: When True and `soffice` is on PATH, also emit PDFs.

    Returns:
        List of produced file paths (DOCX + PDF intermixed, in the order
        the personas were composed).
    """
    target_personas = tuple(personas) if personas else _DEFAULT_PERSONAS
    out_root = Path(out_dir)
    out_root.mkdir(parents=True, exist_ok=True)

    produced: list[Path] = []
    pdf_available = render_pdf and shutil.which("soffice") is not None
    pdf_warned = False

    for persona in target_personas:
        if persona not in PERSONAS:
            logger.warning("Skipping unknown persona: %s", persona)
            continue

        docx_path = _compose_one(
            persona=persona,
            report=report,
            validation=validation,
            tenant=tenant,
            out_dir=out_root,
            rag_engine=rag_engine,
        )
        produced.append(docx_path)

        if render_pdf and not pdf_available and not pdf_warned:
            logger.warning(
                "LibreOffice (`soffice`) not on PATH — skipping PDF "
                "conversion. DOCX artefacts still produced."
            )
            pdf_warned = True

        if pdf_available:
            pdf_path = _convert_to_pdf(docx_path)
            if pdf_path is not None:
                produced.append(pdf_path)

    return produced


# ---------------------------------------------------------------------------
# One-persona build
# ---------------------------------------------------------------------------

def _compose_one(
    *,
    persona: PersonaId,
    report: CrawlReport,
    validation: Optional[ValidationReport],
    tenant: str,
    out_dir: Path,
    rag_engine,
) -> Path:
    profile = PERSONAS[persona]
    solution_name = _solution_stem(report.solution)

    builder = DocxBuilder(
        title=f"{tenant} Knowledge Transfer",
        subtitle=f"For {profile.display_name}",
        tenant=tenant,
        persona=profile.display_name,
    )

    outline = outline_for(persona)
    citations: list[str] = []

    for item in outline:
        try:
            _render_section(
                item=item,
                builder=builder,
                report=report,
                validation=validation,
                persona=persona,
                rag_engine=rag_engine,
                citations=citations,
            )
        except Exception as e:  # pragma: no cover — defensive
            logger.warning(
                "Section '%s' for persona '%s' failed: %s — rendering stub",
                item.id, persona, e,
            )
            builder.h2(item.title)
            builder.p(f"_Section rendering failed: {e}_")

    if citations:
        builder.citations(_dedupe_preserve_order(citations))

    filename = f"{tenant}_{persona}_KT.docx"
    return Path(builder.save(str(out_dir / filename)))


# ---------------------------------------------------------------------------
# Section resolvers
# ---------------------------------------------------------------------------

def _render_section(
    *,
    item: OutlineItem,
    builder: DocxBuilder,
    report: CrawlReport,
    validation: Optional[ValidationReport],
    persona: PersonaId,
    rag_engine,
    citations: list[str],
) -> None:
    """Dispatch one outline item to the right resolver and emit to the doc."""
    builder.h2(item.title)

    if item.source == "computed":
        _render_computed(item.id, report, builder)
        return

    if item.source == "rules":
        _render_rules(validation, builder, required=item.required)
        return

    if item.source == "report":
        _render_computed(item.id, report, builder)
        return

    if item.source == "rag":
        _render_rag(
            item=item,
            report=report,
            persona=persona,
            rag_engine=rag_engine,
            builder=builder,
            citations=citations,
        )
        return

    builder.p(f"_Unknown outline source: {item.source}_")


def _render_computed(section_id: str, report: CrawlReport, builder: DocxBuilder) -> None:
    """Render the report-derived sections (deterministic, no LLM)."""
    if section_id in {"system_context", "component_model", "solution_layout"}:
        if not report.projects:
            builder.p("No projects discovered.")
            return
        builder.table(
            header=["Project", "Layer", "Framework", "Refs"],
            rows=[
                [p.name, p.layer or "-", p.framework or "-",
                 ", ".join(p.references) or "-"]
                for p in report.projects
            ],
            widths=[2.2, 1.3, 1.3, 2.0],
        )
        return

    if section_id == "tech_stack":
        pkgs: dict[str, str] = {}
        for p in report.projects:
            for pkg in p.nuget_packages:
                pkgs.setdefault(pkg.name, pkg.version)
        if not pkgs:
            builder.p("No NuGet references recorded.")
            return
        builder.table(
            header=["Package", "Version"],
            rows=[[name, ver or "-"] for name, ver in sorted(pkgs.items())],
            widths=[3.5, 1.5],
        )
        return

    if section_id == "api_reference":
        if not report.endpoints:
            builder.p("No HTTP endpoints discovered.")
            return
        builder.table(
            header=["Method", "Route", "Controller", "Auth"],
            rows=[
                [e.method, e.route, e.controller, "yes" if e.auth_required else "no"]
                for e in report.endpoints
            ],
            widths=[0.8, 2.8, 1.7, 0.6],
        )
        return

    if section_id == "data_model":
        if not report.data_models:
            builder.p("No EF Core data models discovered.")
            return
        builder.table(
            header=["Entity", "DbContext", "Relationships"],
            rows=[
                [dm.name, dm.db_context or "-",
                 ", ".join(dm.relationships) or "-"]
                for dm in report.data_models
            ],
            widths=[2.0, 2.0, 2.5],
        )
        return

    if section_id == "fixtures":
        test_projs = [p for p in report.projects if p.layer == "Tests"]
        if not test_projs:
            builder.p("No test projects discovered in the crawl.")
            return
        builder.p(f"Found {len(test_projs)} test project(s).")
        for p in test_projs:
            builder.bullet(f"{p.name} ({p.framework})")
        return

    builder.p(f"_No computed renderer registered for '{section_id}'._")


def _render_rules(
    validation: Optional[ValidationReport],
    builder: DocxBuilder,
    *,
    required: bool,
) -> None:
    if validation is None or not validation.violations:
        if required:
            builder.p("No architecture-rule violations recorded.")
        else:
            builder.p("_Validation report not supplied — section skipped._")
        return
    builder.table(
        header=["Severity", "Rule", "File", "Description"],
        rows=[
            [v.severity, v.rule, v.file or "-", v.description]
            for v in validation.violations[:40]
        ],
        widths=[0.9, 1.6, 2.2, 2.5],
    )


def _render_rag(
    *,
    item: OutlineItem,
    report: CrawlReport,
    persona: PersonaId,
    rag_engine,
    builder: DocxBuilder,
    citations: list[str],
) -> None:
    if rag_engine is None or not item.query:
        builder.p(
            "_RAG engine unavailable — this section would normally be "
            "composed from the knowledge store under the "
            f"`{persona}` persona._"
        )
        return
    try:
        resp = rag_engine.query(item.query, persona=persona)
    except Exception as e:
        logger.warning("RAG query failed for section '%s': %s", item.id, e)
        builder.p(f"_RAG query failed: {e}_")
        return

    answer = getattr(resp, "answer", "") or ""
    refused = bool(getattr(resp, "refused", False))
    if refused:
        builder.callout(
            "Evidence gap",
            "The knowledge store did not yield grounded evidence for this "
            "section. Follow the hints below or ingest more docs.",
            color="8A3FFC",
        )

    _emit_markdown(answer, builder)

    # Capture citations for the references appendix.
    for cite in _extract_citations(answer):
        citations.append(cite)
    for s in getattr(resp, "sources", []) or []:
        path = getattr(s, "file_path", None) or getattr(s, "path", None)
        if path:
            citations.append(str(path))


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_MD_BULLET = re.compile(r"^\s*[-*+]\s+(.*)$")
_MD_NUMBER = re.compile(r"^\s*\d+\.\s+(.*)$")
_MD_HEADING = re.compile(r"^(#{1,3})\s+(.*)$")
_CODE_FENCE = re.compile(r"^```")
_CITATION = re.compile(r"\[[^\]\n]+?:L\d+(?:-L\d+)?\]|\[doc §[\d.]+\]")


def _emit_markdown(text: str, builder: DocxBuilder) -> None:
    """Minimal markdown -> DOCX renderer.

    We intentionally don't pull in a full markdown parser — LLM output from
    the personas is shallow markdown (headings, bullets, code fences, plain
    paragraphs). Anything unhandled falls through as a paragraph.
    """
    if not text:
        builder.p("_No content produced._")
        return

    lines = text.splitlines()
    i = 0
    while i < len(lines):
        line = lines[i]
        if _CODE_FENCE.match(line):
            # Collect until closing fence
            block: list[str] = []
            i += 1
            while i < len(lines) and not _CODE_FENCE.match(lines[i]):
                block.append(lines[i])
                i += 1
            if block:
                builder.code_block("\n".join(block))
            i += 1  # consume closing fence
            continue

        head = _MD_HEADING.match(line)
        if head:
            depth = len(head.group(1))
            label = head.group(2).strip()
            if depth == 1:
                builder.h2(label)  # already nested under h2 — demote
            elif depth == 2:
                builder.h3(label)
            else:
                builder.h3(label)
            i += 1
            continue

        bullet = _MD_BULLET.match(line)
        if bullet:
            builder.bullet(bullet.group(1).strip())
            i += 1
            continue

        numbered = _MD_NUMBER.match(line)
        if numbered:
            builder.numbered(numbered.group(1).strip())
            i += 1
            continue

        if line.strip():
            # Gather a paragraph (consecutive non-special lines).
            para_lines = [line.strip()]
            i += 1
            while i < len(lines) and lines[i].strip() and not _looks_special(lines[i]):
                para_lines.append(lines[i].strip())
                i += 1
            builder.p(" ".join(para_lines))
        else:
            i += 1


def _looks_special(line: str) -> bool:
    return bool(
        _CODE_FENCE.match(line)
        or _MD_HEADING.match(line)
        or _MD_BULLET.match(line)
        or _MD_NUMBER.match(line)
    )


def _extract_citations(text: str) -> list[str]:
    return _CITATION.findall(text or "")


def _dedupe_preserve_order(items: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for it in items:
        if it and it not in seen:
            seen.add(it)
            out.append(it)
    return out


def _solution_stem(solution: str) -> str:
    name = solution.replace("\\", "/").rsplit("/", 1)[-1]
    return name[:-4] if name.lower().endswith(".sln") else name


def _convert_to_pdf(docx_path: Path) -> Optional[Path]:
    """Run LibreOffice headless to convert DOCX -> PDF alongside the source."""
    try:
        proc = subprocess.run(
            [
                "soffice", "--headless", "--convert-to", "pdf",
                "--outdir", str(docx_path.parent), str(docx_path),
            ],
            capture_output=True, text=True, timeout=120,
        )
    except (subprocess.TimeoutExpired, FileNotFoundError) as e:
        logger.warning("soffice conversion error for %s: %s", docx_path.name, e)
        return None
    if proc.returncode != 0:
        logger.warning(
            "soffice conversion failed for %s: %s",
            docx_path.name, proc.stderr.strip() or proc.stdout.strip(),
        )
        return None
    pdf_path = docx_path.with_suffix(".pdf")
    return pdf_path if pdf_path.exists() else None
