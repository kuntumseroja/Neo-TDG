"""Doxygen-style per-symbol code documentation generator.

Walks the source files of every project discovered by the SolutionCrawler
plus the Angular components on the same `CrawlReport`, extracts type
declarations, member signatures, and the doc comments attached to them,
and renders the result as a single Markdown document.

Supported languages:
  * C#  — XML doc comments (`/// <summary>...</summary>`) + member sigs
  * TypeScript / Angular — JSDoc `/** ... */` + class / function sigs

Output is intentionally text-only (no AST round-trip): we want a fast,
deterministic rendering that the existing PDF generator and the RAG
ingestion pipeline can both consume without any new dependencies.

The Markdown produced here is reusable by `CrawlDocGenerator.generate_pdf`
because that helper only requires a markdown string — so PDF parity is
free.
"""

from __future__ import annotations

import logging
import re
from collections import defaultdict
from pathlib import Path
from typing import List, Optional, Tuple

from src.models.crawler import CrawlReport

logger = logging.getLogger(__name__)


# ── C# extraction patterns ────────────────────────────────────────────────

_CS_NAMESPACE = re.compile(r"^\s*namespace\s+([\w.]+)\s*[;{]", re.MULTILINE)

_CS_MODIFIERS = (
    "public", "internal", "protected", "private",
    "static", "virtual", "override", "abstract", "sealed",
    "async", "partial", "readonly", "new", "extern", "unsafe",
)
_CS_MODIFIER_RE = re.compile(
    r"^\s*(?:" + "|".join(_CS_MODIFIERS) + r")\b"
)

_CS_TYPE_DECL = re.compile(
    r"\b(class|interface|record|struct|enum)\s+([A-Za-z_]\w*)"
)

_CS_METHOD_OR_PROP = re.compile(
    r"\b([A-Za-z_][\w<>?\[\],. ]*?)\s+([A-Za-z_]\w*)\s*(\([^)]*\)|\{|=>)"
)


def _collect_cs_doc_above(lines: List[str], idx: int) -> str:
    """Walk upward from `idx` collecting any contiguous `///` lines
    (skipping blank lines stops the walk)."""
    doc_lines: List[str] = []
    i = idx - 1
    while i >= 0:
        stripped = lines[i].lstrip()
        if stripped.startswith("///"):
            doc_lines.append(lines[i])
            i -= 1
            continue
        break
    if not doc_lines:
        return ""
    doc_lines.reverse()
    return "\n".join(doc_lines)


# ── TypeScript / Angular extraction patterns ──────────────────────────────

# Capture a JSDoc block immediately followed by a declaration.
_TS_DOC_BLOCK = re.compile(
    r"(/\*\*[\s\S]*?\*/)?\s*"
    r"(@(?:Component|Injectable|NgModule|Directive|Pipe)\s*\([\s\S]*?\)\s*)?"
    r"(export\s+(?:abstract\s+)?(?:class|interface|function|const|enum)\s+[A-Za-z_]\w*[^\n{=;]*)",
)

_TS_DECL = re.compile(
    r"export\s+(?:abstract\s+)?(class|interface|function|const|enum)\s+([A-Za-z_]\w*)"
)

_TS_DECORATOR = re.compile(r"@(Component|Injectable|NgModule|Directive|Pipe)")


# ── Helpers ───────────────────────────────────────────────────────────────


def _strip_xml_doc(block: Optional[str]) -> str:
    """Turn a `/// <summary>...</summary>` block into plain prose."""
    if not block:
        return ""
    text = re.sub(r"^[ \t]*///[ \t]?", "", block, flags=re.MULTILINE)
    # Pull <summary> body if present, otherwise keep all the doc text.
    summary_match = re.search(
        r"<summary>([\s\S]*?)</summary>", text, re.IGNORECASE
    )
    if summary_match:
        body = summary_match.group(1)
    else:
        body = text
    # Drop XML-ish tags but keep their inner text.
    body = re.sub(r"<[^>]+>", "", body)
    return " ".join(line.strip() for line in body.splitlines() if line.strip())


def _strip_jsdoc(block: Optional[str]) -> str:
    """Turn a `/** ... */` JSDoc block into plain prose."""
    if not block:
        return ""
    text = re.sub(r"^/\*\*", "", block.strip())
    text = re.sub(r"\*/$", "", text)
    lines = []
    for raw in text.splitlines():
        line = raw.strip()
        if line.startswith("*"):
            line = line[1:].strip()
        # Skip pure JSDoc tag lines (we keep the prose lines).
        if line.startswith("@"):
            continue
        if line:
            lines.append(line)
    return " ".join(lines)


def _trim_signature(line: str) -> str:
    """Collapse whitespace in a captured declaration line so the rendered
    table stays narrow."""
    sig = " ".join(line.split())
    # Drop trailing junk like `{` so signatures look clean.
    sig = sig.rstrip("{ \t")
    return sig


def _is_skipped_dir(path: Path) -> bool:
    parts_lower = {p.lower() for p in path.parts}
    return bool(parts_lower & {"bin", "obj", "node_modules", ".git", ".vs"})


# ── Generator ─────────────────────────────────────────────────────────────


class CodeDocGenerator:
    """Render Doxygen-style per-symbol code docs from a `CrawlReport`."""

    def __init__(self, max_files_per_project: int = 200):
        self.max_files_per_project = max_files_per_project

    # Public entry points -------------------------------------------------

    def generate_markdown(self, report: CrawlReport) -> str:
        """Build the full code-documentation markdown."""
        sln_name = report.solution.replace("\\", "/").split("/")[-1]
        parts: List[str] = [
            f"# {sln_name} - Code Documentation\n",
            f"> Auto-generated by Lumen.AI Code Documentation Generator\n",
            "> Doxygen-style per-symbol API reference for every C# and "
            "Angular/TypeScript file discovered in this solution.",
        ]

        # ── C# projects ──────────────────────────────────────────────
        cs_section = self._cs_section(report)
        if cs_section:
            parts.append(cs_section)

        # ── Angular / TypeScript ─────────────────────────────────────
        ts_section = self._ts_section(report)
        if ts_section:
            parts.append(ts_section)

        if len(parts) <= 3:
            parts.append(
                "\n_No C# or TypeScript source files were discovered for "
                "this solution. Make sure the crawl pointed at a directory "
                "that contains `.cs` and/or `.ts` files._\n"
            )
        return "\n\n".join(parts)

    def generate_pdf(self, markdown_content: str) -> bytes:
        """Convenience: reuse the existing unicode-safe PDF renderer."""
        from src.crawler.doc_generator import CrawlDocGenerator
        return CrawlDocGenerator().generate_pdf(markdown_content)

    # Section builders ----------------------------------------------------

    def _cs_section(self, report: CrawlReport) -> str:
        per_project: List[Tuple[str, List[str]]] = []
        total_files = 0
        total_types = 0

        for project in report.projects:
            project_dir = Path(project.path).parent if project.path else None
            if not project_dir or not project_dir.exists():
                continue

            cs_files: List[Path] = []
            for f in sorted(project_dir.rglob("*.cs")):
                if _is_skipped_dir(f):
                    continue
                cs_files.append(f)
                if len(cs_files) >= self.max_files_per_project:
                    break

            if not cs_files:
                continue

            project_chunks: List[str] = [
                f"### Project: `{project.name}`",
                f"_{len(cs_files)} file(s) scanned. Layer: **{project.layer or 'Unknown'}**._",
            ]

            project_type_count = 0
            for cs_file in cs_files:
                try:
                    content = cs_file.read_text(encoding="utf-8", errors="ignore")
                except Exception as e:
                    logger.warning(f"Could not read {cs_file}: {e}")
                    continue

                file_chunk, type_count = self._render_cs_file(content, cs_file, project_dir)
                if file_chunk:
                    project_chunks.append(file_chunk)
                    project_type_count += type_count

            if project_type_count == 0:
                # Nothing documentable in this project — drop it from the
                # output to keep noise down.
                continue

            total_files += len(cs_files)
            total_types += project_type_count
            per_project.append((project.name, project_chunks))

        if not per_project:
            return ""

        header = [
            "## C# Source Documentation",
            f"Scanned **{total_files}** `.cs` files across "
            f"**{len(per_project)}** projects, documented "
            f"**{total_types}** types.",
        ]
        body: List[str] = []
        for _name, chunks in per_project:
            body.extend(chunks)
        return "\n\n".join(header + body)

    def _render_cs_file(
        self, content: str, file_path: Path, project_dir: Path
    ) -> Tuple[str, int]:
        """Render one .cs file as a Markdown chunk. Returns (chunk, type_count)."""
        ns_match = _CS_NAMESPACE.search(content)
        namespace = ns_match.group(1) if ns_match else ""

        # Two-pass: walk lines, identify each declaration line by its
        # leading modifier, then look upward for any contiguous /// block.
        lines = content.splitlines()
        type_entries: List[Tuple[str, str, str, List[Tuple[str, str]]]] = []
        current_type: Optional[List] = None  # [kind, name, summary, members]

        for i, raw_line in enumerate(lines):
            if not _CS_MODIFIER_RE.match(raw_line):
                continue
            decl_line = raw_line.strip()
            doc_block = _collect_cs_doc_above(lines, i)

            type_decl = _CS_TYPE_DECL.search(decl_line)
            if type_decl:
                kind = type_decl.group(1)
                name = type_decl.group(2)
                summary = _strip_xml_doc(doc_block)
                if current_type is not None:
                    type_entries.append(tuple(current_type))  # type: ignore
                current_type = [kind, name, summary, []]
                continue

            # Member of the current type.
            if current_type is None:
                continue
            if not _CS_METHOD_OR_PROP.search(decl_line):
                continue
            sig = _trim_signature(decl_line)
            if not sig or len(sig) > 220:
                continue
            current_type[3].append((sig, _strip_xml_doc(doc_block)))

        if current_type is not None:
            type_entries.append(tuple(current_type))  # type: ignore

        if not type_entries:
            return "", 0

        try:
            rel = file_path.relative_to(project_dir)
        except ValueError:
            rel = file_path

        lines = [f"#### `{rel}`"]
        if namespace:
            lines.append(f"_Namespace: `{namespace}`_")
        for kind, name, summary, members in type_entries:
            lines.append(f"\n**{kind} {name}**")
            if summary:
                lines.append(f"> {summary}")
            if members:
                lines.append("")
                lines.append("| Member | Summary |")
                lines.append("|--------|---------|")
                for sig, msum in members[:40]:
                    sig_clean = sig.replace("|", "\\|")
                    msum_clean = (msum or "—").replace("|", "\\|")
                    lines.append(f"| `{sig_clean}` | {msum_clean} |")
                if len(members) > 40:
                    lines.append(f"| _… +{len(members) - 40} more …_ | |")

        return "\n".join(lines), len(type_entries)

    # ── Angular / TypeScript ────────────────────────────────────────

    def _ts_section(self, report: CrawlReport) -> str:
        """Render an Angular/TypeScript section.

        We start from `report.ui_components` (the auto-discovered Angular
        component files) and walk every `.ts` / `.service.ts` /
        `.module.ts` file under the same root directory so that services,
        modules, guards and pipes are documented too.
        """
        ui = report.ui_components or []
        if not ui:
            return ""

        # Collect Angular roots from component file paths.
        roots: List[Path] = []
        for c in ui:
            if not c.component_file:
                continue
            comp_path = Path(c.component_file)
            # Walk up to find the nearest `src/` ancestor (typical Angular
            # layout) or fall back to the immediate parent dir.
            root = None
            for ancestor in comp_path.parents:
                if ancestor.name == "src":
                    root = ancestor
                    break
            if root is None:
                root = comp_path.parent
            if root not in roots:
                roots.append(root)

        if not roots:
            return ""

        ts_files: List[Path] = []
        for root in roots:
            try:
                for f in sorted(root.rglob("*.ts")):
                    if _is_skipped_dir(f):
                        continue
                    if f.name.endswith(".spec.ts") or f.name.endswith(".d.ts"):
                        continue
                    ts_files.append(f)
            except Exception as e:
                logger.warning(f"Could not walk Angular root {root}: {e}")

        if not ts_files:
            return ""

        # Group by parent dir for a tidier table of contents.
        by_dir = defaultdict(list)
        for f in ts_files[: 25 * len(roots) + 200]:  # safety cap
            by_dir[f.parent].append(f)

        header = [
            "## Angular / TypeScript Source Documentation",
            f"Scanned **{len(ts_files)}** `.ts` files across "
            f"**{len(by_dir)}** folders.",
        ]

        body: List[str] = []
        rendered_types = 0
        for folder in sorted(by_dir.keys()):
            folder_chunks: List[str] = [f"### `{folder.name}/`"]
            folder_type_count = 0
            for ts_file in by_dir[folder]:
                try:
                    content = ts_file.read_text(encoding="utf-8", errors="ignore")
                except Exception as e:
                    logger.warning(f"Could not read {ts_file}: {e}")
                    continue
                chunk, count = self._render_ts_file(content, ts_file)
                if chunk:
                    folder_chunks.append(chunk)
                    folder_type_count += count
            if folder_type_count > 0:
                rendered_types += folder_type_count
                body.extend(folder_chunks)

        if rendered_types == 0:
            return ""
        header[1] += f" Documented **{rendered_types}** types/functions."
        return "\n\n".join(header + body)

    def _render_ts_file(self, content: str, file_path: Path) -> Tuple[str, int]:
        entries: List[Tuple[str, str, str, str]] = []
        # entries: (kind, name, decorator, summary)
        for m in _TS_DOC_BLOCK.finditer(content):
            doc_block = m.group(1)
            decorator = (m.group(2) or "").strip()
            decl = m.group(3).strip()

            decl_match = _TS_DECL.search(decl)
            if not decl_match:
                continue
            kind = decl_match.group(1)
            name = decl_match.group(2)

            decorator_name = ""
            if decorator:
                dec_match = _TS_DECORATOR.search(decorator)
                if dec_match:
                    decorator_name = "@" + dec_match.group(1)

            summary = _strip_jsdoc(doc_block)
            entries.append((kind, name, decorator_name, summary))

        if not entries:
            return "", 0

        lines = [f"#### `{file_path.name}`"]
        lines.append("")
        lines.append("| Kind | Name | Decorator | Summary |")
        lines.append("|------|------|-----------|---------|")
        for kind, name, decorator, summary in entries[:60]:
            sumtxt = (summary or "—").replace("|", "\\|")
            lines.append(
                f"| {kind} | **{name}** | {decorator or '—'} | {sumtxt} |"
            )
        if len(entries) > 60:
            lines.append(f"| _… +{len(entries) - 60} more …_ | | | |")
        return "\n".join(lines), len(entries)
