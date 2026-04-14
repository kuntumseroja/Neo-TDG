"""
Document generator for crawl reports.

Generates comprehensive Markdown and PDF documentation from CrawlReport data.
"""

import re
import logging
from datetime import datetime
from collections import defaultdict
from typing import List, Dict

from src.models.crawler import CrawlReport

logger = logging.getLogger(__name__)


def _describe_llm(llm) -> str:
    """Return a short model label for the report header.

    Examples: ``llama3.2``, ``deepseek-coder:6.7b``, ``gemma2:9b``. When no
    LLM is configured we return a sentinel string so the header still reads
    naturally ("...using no LLM (deterministic only)").
    """
    if llm is None:
        return "no LLM (deterministic only)"
    return str(getattr(llm, "model", None) or "unknown model")


class CrawlDocGenerator:
    """Generate technical documentation from a CrawlReport."""

    def __init__(self, llm=None):
        """
        Args:
            llm: Optional BaseLLM instance — used only to stamp the model
                name/version into the report header. Doc generation itself
                is deterministic and does not call the LLM.
        """
        self.llm = llm

    # Available structure templates. UI selector exposes these by key.
    STRUCTURES = {
        "standard": "Standard (full crawl report)",
        "architecture": "Architecture Doc (DDD / Clean Architecture)",
    }

    def generate_markdown(
        self, report: CrawlReport, structure: str = "standard"
    ) -> str:
        """Generate markdown documentation in the requested structure.

        Args:
            report: The crawl report.
            structure: One of `STRUCTURES.keys()`. Defaults to `standard`,
                which produces the original full report. `architecture`
                produces an 8-section DDD/Clean-Architecture document.
        """
        if structure == "architecture":
            return self._generate_architecture_doc(report)
        return self._generate_standard(report)

    def _generate_standard(self, report: CrawlReport) -> str:
        """Original full report — every section the crawler can produce."""
        sections = [
            self._section_title(report),
            self._section_overview(report),
            self._section_business_domains(report),
            self._section_domain_contracts(report),
            self._section_sequence_flows(report),
            self._section_code_flow(report),
            self._section_architecture_diagram(report),
            self._section_projects(report),
            self._section_configurations(report),
            self._section_di_registrations(report),
            self._section_code_symbols(report),
            self._section_endpoints(report),
            self._section_consumers(report),
            self._section_schedulers(report),
            self._section_integrations(report),
            self._section_data_models(report),
            self._section_er_diagram(report),
            self._section_ui_components(report),
            self._section_dependency_graph(report),
        ]
        return "\n\n".join(s for s in sections if s)

    def _generate_architecture_doc(self, report: CrawlReport) -> str:
        """Architecture Doc structure — DDD + Clean Architecture template.

        Layout:
          1. Bounded Context Definition
          2. Context Map
          3. Domain Model (entities, value objects, aggregates, repos, factories, class diagram)
          4. Domain Event Catalogue
          5. Clean Architecture Diagram
          6. Sequence Diagram (controller → read model)
          7. Event Stream (synchronous & asynchronous)
          8. Glossary (Ubiquitous Language — CoreTax)
        """
        sections = [
            self._arch_title(report),
            self._arch_1_bounded_contexts(report),
            self._arch_2_context_map(report),
            self._arch_3_domain_model(report),
            self._arch_4_domain_event_catalogue(report),
            self._arch_5_clean_architecture(report),
            self._arch_6_sequence_diagrams(report),
            self._arch_7_event_stream(report),
            self._arch_8_glossary(report),
        ]
        return "\n\n".join(s for s in sections if s)

    def generate_pdf(self, markdown_content: str) -> bytes:
        """Convert markdown documentation to PDF using fpdf2."""
        try:
            from fpdf import FPDF
            from fpdf.enums import XPos, YPos
        except ImportError:
            logger.error("fpdf2 not installed. Run: pip install fpdf2")
            raise

        pdf = FPDF()
        pdf.set_auto_page_break(auto=True, margin=15)
        pdf.add_page()

        def _mc(w, h, text, **kwargs):
            """multi_cell wrapper that always resets X to left margin."""
            pdf.multi_cell(w, h, self._ascii_safe(text), new_x=XPos.LMARGIN, new_y=YPos.NEXT, **kwargs)

        lines = markdown_content.split("\n")
        in_code_block = False
        in_mermaid_block = False
        mermaid_buffer: List[str] = []
        table_rows = []

        for line in lines:
            # Code block toggle
            if line.strip().startswith("```"):
                if in_code_block:
                    # Closing fence
                    if in_mermaid_block:
                        self._render_mermaid_image(pdf, "\n".join(mermaid_buffer))
                        mermaid_buffer = []
                        in_mermaid_block = False
                    in_code_block = False
                    pdf.ln(2)
                else:
                    # Opening fence — detect language
                    lang = line.strip()[3:].strip().lower()
                    in_code_block = True
                    if lang == "mermaid":
                        in_mermaid_block = True
                        mermaid_buffer = []
                    else:
                        pdf.set_font("Courier", size=7)
                        pdf.set_fill_color(240, 240, 240)
                continue

            if in_code_block:
                if in_mermaid_block:
                    mermaid_buffer.append(line)
                    continue
                pdf.set_font("Courier", size=7)
                pdf.set_fill_color(240, 240, 240)
                text = line.rstrip()
                if len(text) > 120:
                    text = text[:120] + "..."
                pdf.cell(0, 4, self._ascii_safe(text), new_x=XPos.LMARGIN, new_y=YPos.NEXT, fill=True)
                continue

            # Table rows
            if line.strip().startswith("|"):
                cols = [c.strip() for c in line.strip().strip("|").split("|")]
                if all(set(c.strip()) <= set("-: ") for c in cols):
                    continue
                table_rows.append(cols)
                continue
            else:
                if table_rows:
                    self._render_table(pdf, table_rows)
                    table_rows = []

            stripped = line.strip()
            if not stripped:
                pdf.ln(3)
                continue

            # Ensure X is at left margin before rendering
            pdf.set_x(pdf.l_margin)

            # Headings
            if stripped.startswith("# "):
                pdf.ln(5)
                pdf.set_font("Helvetica", "B", 18)
                _mc(0, 8, stripped[2:])
                pdf.ln(3)
            elif stripped.startswith("## "):
                pdf.ln(4)
                pdf.set_font("Helvetica", "B", 14)
                _mc(0, 7, stripped[3:])
                pdf.ln(2)
            elif stripped.startswith("### "):
                pdf.ln(3)
                pdf.set_font("Helvetica", "B", 12)
                _mc(0, 6, stripped[4:])
                pdf.ln(1)
            elif stripped.startswith("#### "):
                pdf.ln(2)
                pdf.set_font("Helvetica", "B", 10)
                _mc(0, 5, stripped[5:])
            elif stripped.startswith("> "):
                pdf.set_font("Helvetica", "I", 9)
                pdf.set_text_color(100, 100, 100)
                _mc(0, 5, stripped[2:])
                pdf.set_text_color(0, 0, 0)
            elif stripped.startswith("- ") or stripped.startswith("* "):
                pdf.set_font("Helvetica", size=9)
                text = self._clean_md(stripped[2:])
                _mc(0, 5, "  * " + text)
            else:
                pdf.set_font("Helvetica", size=9)
                text = self._clean_md(stripped)
                _mc(0, 5, text)

        # Flush remaining table
        if table_rows:
            self._render_table(pdf, table_rows)

        return pdf.output()

    def _render_table(self, pdf, rows: list):
        """Render a markdown table as PDF cells."""
        if not rows:
            return

        num_cols = len(rows[0])
        page_width = pdf.w - pdf.l_margin - pdf.r_margin
        col_width = page_width / max(num_cols, 1)

        # Header row
        pdf.set_x(pdf.l_margin)
        if rows:
            pdf.set_font("Helvetica", "B", 8)
            pdf.set_fill_color(220, 220, 220)
            for col in rows[0]:
                text = self._clean_md(col)[:30]
                pdf.cell(col_width, 5, text, border=1, fill=True)
            pdf.ln()
            pdf.set_x(pdf.l_margin)

        # Data rows
        pdf.set_font("Helvetica", size=7)
        for row in rows[1:]:
            pdf.set_x(pdf.l_margin)
            for i, col in enumerate(row):
                text = self._clean_md(col)[:35]
                pdf.cell(col_width, 4.5, text, border=1)
            pdf.ln()
        pdf.set_x(pdf.l_margin)

        pdf.ln(3)

    # ── Mermaid → PNG rendering ────────────────────────────────────────

    _MERMAID_PNG_CACHE: Dict[str, bytes] = {}

    def _render_mermaid_image(self, pdf, mermaid_src: str):
        """Fetch a PNG of the given mermaid source from kroki.io and embed
        it into the PDF. Falls back to rendering the source as a code
        block if the network call fails (so offline runs still work)."""
        from fpdf.enums import XPos, YPos

        png = self._fetch_mermaid_png(mermaid_src)
        if png:
            try:
                import io
                bio = io.BytesIO(png)
                page_w = pdf.w - pdf.l_margin - pdf.r_margin
                # Trigger an auto page-break if there isn't enough vertical room.
                if pdf.get_y() + 60 > pdf.h - pdf.b_margin:
                    pdf.add_page()
                pdf.image(bio, x=pdf.l_margin, w=page_w)
                pdf.ln(3)
                return
            except Exception as e:
                logger.warning(f"PDF mermaid image embed failed: {e}")

        # Fallback: render the source as a code block so we still show
        # *something* even if kroki is unreachable.
        pdf.set_font("Courier", size=7)
        pdf.set_fill_color(240, 240, 240)
        for src_line in mermaid_src.splitlines():
            text = src_line.rstrip()
            if len(text) > 120:
                text = text[:120] + "..."
            pdf.cell(0, 4, self._ascii_safe(text), new_x=XPos.LMARGIN, new_y=YPos.NEXT, fill=True)
        pdf.ln(2)

    @classmethod
    def _fetch_mermaid_png(cls, mermaid_src: str) -> bytes:
        """Render mermaid → PNG via kroki.io. Cached per source string.
        Returns empty bytes on any failure."""
        if not mermaid_src.strip():
            return b""
        if mermaid_src in cls._MERMAID_PNG_CACHE:
            return cls._MERMAID_PNG_CACHE[mermaid_src]
        try:
            import base64
            import zlib
            import urllib.request
            # Kroki URL-safe deflate+base64 encoding
            compressed = zlib.compress(mermaid_src.encode("utf-8"), 9)
            encoded = base64.urlsafe_b64encode(compressed).decode("ascii")
            url = f"https://kroki.io/mermaid/png/{encoded}"
            req = urllib.request.Request(
                url, headers={"User-Agent": "Lumen.AI-DocGen/1.0"}
            )
            with urllib.request.urlopen(req, timeout=12) as resp:
                data = resp.read()
            if data and data[:8] == b"\x89PNG\r\n\x1a\n":
                cls._MERMAID_PNG_CACHE[mermaid_src] = data
                return data
            logger.warning("Kroki returned non-PNG payload")
        except Exception as e:
            logger.warning(f"Kroki mermaid render failed: {e}")
        cls._MERMAID_PNG_CACHE[mermaid_src] = b""
        return b""

    # Unicode chars not representable in fpdf2's built-in latin-1 helvetica.
    # Keep this list narrow — anything else falls back to "?".
    _PDF_UNICODE_MAP = {
        "\u2014": "-",   # em dash
        "\u2013": "-",   # en dash
        "\u2212": "-",   # minus
        "\u2192": "->",  # right arrow
        "\u2190": "<-",  # left arrow
        "\u2194": "<->",
        "\u21d2": "=>",
        "\u2018": "'",
        "\u2019": "'",
        "\u201c": '"',
        "\u201d": '"',
        "\u2026": "...", # ellipsis
        "\u00a0": " ",   # nbsp
        "\u2022": "*",   # bullet
        "\u2705": "[x]",
        "\u274c": "[ ]",
    }

    def _ascii_safe(self, text: str) -> str:
        """Replace common unicode punctuation/arrows with ASCII so fpdf2's
        built-in helvetica (latin-1) doesn't blow up. Anything still
        outside latin-1 is replaced with '?'."""
        if not text:
            return text
        for u, a in self._PDF_UNICODE_MAP.items():
            if u in text:
                text = text.replace(u, a)
        return text.encode("latin-1", errors="replace").decode("latin-1")

    def _clean_md(self, text: str) -> str:
        """Remove markdown formatting from text."""
        text = re.sub(r"\*\*(.+?)\*\*", r"\1", text)
        text = re.sub(r"\*(.+?)\*", r"\1", text)
        text = re.sub(r"`(.+?)`", r"\1", text)
        text = re.sub(r"\[(.+?)\]\(.+?\)", r"\1", text)
        return self._ascii_safe(text)

    # ── Markdown Section Builders ──────────────────────────────────────

    def _section_title(self, report: CrawlReport) -> str:
        sln_name = report.solution.replace("\\", "/").split("/")[-1]
        from src import __version__ as lumen_version
        llm_label = _describe_llm(self.llm)
        return (
            f"# {sln_name} - Technical Documentation\n\n"
            f"> Generated by **Lumen.AI Solution Crawler** v{lumen_version} using `{llm_label}`\n"
            f"> Crawled at: {report.crawled_at.strftime('%Y-%m-%d %H:%M:%S')}"
        )

    def _section_overview(self, report: CrawlReport) -> str:
        layers = defaultdict(int)
        frameworks = set()
        total_configs = 0
        total_di = 0
        total_symbols = 0
        for p in report.projects:
            layers[p.layer or "Unknown"] += 1
            if p.framework:
                frameworks.add(p.framework)
            total_configs += len(getattr(p, "configurations", []) or [])
            total_di += len(getattr(p, "di_registrations", []) or [])
            total_symbols += len(getattr(p, "code_symbols", []) or [])

        layer_rows = "\n".join(f"| {layer} | {count} |" for layer, count in sorted(layers.items()))

        return (
            f"## Solution Overview\n\n"
            f"| Metric | Value |\n"
            f"|--------|-------|\n"
            f"| Total Projects | {len(report.projects)} |\n"
            f"| Business Domains | {len(getattr(report, 'business_domains', []) or [])} |\n"
            f"| Domain Contracts | {len(getattr(report, 'domain_contracts', []) or [])} |\n"
            f"| API Endpoints | {len(report.endpoints)} |\n"
            f"| Message Consumers | {len(report.consumers)} |\n"
            f"| Scheduled Jobs | {len(report.schedulers)} |\n"
            f"| External Integrations | {len(report.integrations)} |\n"
            f"| Data Models | {len(report.data_models)} |\n"
            f"| Angular UI Components | {len(report.ui_components)} |\n"
            f"| Configuration Keys | {total_configs} |\n"
            f"| DI Registrations | {total_di} |\n"
            f"| Code Symbols | {total_symbols} |\n"
            f"| Frameworks | {', '.join(sorted(frameworks)) or 'N/A'} |\n\n"
            f"### Layer Distribution\n\n"
            f"| Layer | Projects |\n"
            f"|-------|----------|\n"
            f"{layer_rows}"
        )

    def _section_architecture_diagram(self, report: CrawlReport) -> str:
        layers = defaultdict(list)
        for p in report.projects:
            layers[p.layer or "Unknown"].append(p.name)

        lines = ["```mermaid", "graph TD"]
        for layer, projects in sorted(layers.items()):
            safe_layer = layer.replace(" ", "_").replace("-", "_")
            lines.append(f'    subgraph {safe_layer}["{layer} Layer"]')
            for proj in projects:
                safe_name = self._mermaid_id(proj)
                lines.append(f'        {safe_name}["{proj}"]')
            lines.append("    end")

        # Project-to-project references (the dependency_graph builder uses
        # source/target keys, not from/to)
        for edge in report.dependency_graph.get("edges", []) or []:
            src = self._mermaid_id(edge.get("source", ""))
            tgt = self._mermaid_id(edge.get("target", ""))
            if src and tgt:
                lines.append(f"    {src} --> {tgt}")

        lines.append("```")
        return "## Architecture Diagram\n\n" + "\n".join(lines)

    def _section_projects(self, report: CrawlReport) -> str:
        if not report.projects:
            return ""

        parts = ["## Project Details"]
        for p in report.projects:
            parts.append(f"\n### {p.name}")
            parts.append(f"- **Layer**: {p.layer or 'Unknown'}")
            parts.append(f"- **Framework**: {p.framework or 'N/A'}")
            parts.append(f"- **Path**: `{p.path}`")

            if p.references:
                parts.append(f"\n**Project References**: {', '.join(p.references)}")

            if p.nuget_packages:
                parts.append("\n| Package | Version |")
                parts.append("|---------|---------|")
                for pkg in p.nuget_packages:
                    parts.append(f"| {pkg.name} | {pkg.version} |")

        return "\n".join(parts)

    def _section_endpoints(self, report: CrawlReport) -> str:
        if not report.endpoints:
            return ""

        # Group by controller
        by_controller = defaultdict(list)
        for ep in report.endpoints:
            by_controller[ep.controller].append(ep)

        parts = [
            "## API Endpoints\n",
            f"Total: **{len(report.endpoints)}** endpoints across **{len(by_controller)}** controllers\n",
            "| Method | Route | Controller | Auth | File |",
            "|--------|-------|------------|------|------|",
        ]
        for ctrl in sorted(by_controller.keys()):
            for ep in by_controller[ctrl]:
                auth = "Yes" if ep.auth_required else "No"
                parts.append(f"| **{ep.method}** | `{ep.route}` | {ep.controller} | {auth} | {ep.file}:{ep.line} |")

        return "\n".join(parts)

    def _section_consumers(self, report: CrawlReport) -> str:
        if not report.consumers:
            return ""

        parts = [
            "## Message Consumers\n",
            f"Total: **{len(report.consumers)}** consumers\n",
            "| Consumer Class | Message Type | Queue | File |",
            "|---------------|--------------|-------|------|",
        ]
        for c in report.consumers:
            parts.append(f"| {c.consumer_class} | `{c.message_type}` | {c.queue or 'auto'} | {c.file} |")

        return "\n".join(parts)

    def _section_schedulers(self, report: CrawlReport) -> str:
        if not report.schedulers:
            return ""

        parts = [
            "## Scheduled Jobs\n",
            f"Total: **{len(report.schedulers)}** scheduled jobs\n",
            "| Job Name | Schedule | Handler | File |",
            "|----------|----------|---------|------|",
        ]
        for s in report.schedulers:
            cron = s.cron_expression or "N/A"
            parts.append(f"| {s.job_name} | `{cron}` | {s.handler_class} | {s.file} |")

        return "\n".join(parts)

    def _section_integrations(self, report: CrawlReport) -> str:
        if not report.integrations:
            return ""

        by_type = defaultdict(list)
        for i in report.integrations:
            by_type[i.type].append(i)

        parts = [
            "## External Integrations\n",
            f"Total: **{len(report.integrations)}** integration points\n",
        ]

        for itype in sorted(by_type.keys()):
            parts.append(f"\n### {itype.upper()}")
            parts.append("| Source | Target | Contract | File |")
            parts.append("|--------|--------|----------|------|")
            for i in by_type[itype]:
                parts.append(f"| {i.source_service} | {i.target} | {i.contract} | {i.file} |")

        return "\n".join(parts)

    def _section_ui_components(self, report: CrawlReport) -> str:
        """Angular front-end inventory: components, modules, routes, API
        calls, plus a Mermaid graph wiring components to the back-end
        endpoints they hit."""
        ui = report.ui_components or []
        if not ui:
            return ""

        # Group by module for the table
        by_module = defaultdict(list)
        for c in ui:
            by_module[c.module or "(root)"].append(c)

        parts = [
            "## Angular Front-End\n",
            f"Total: **{len(ui)}** components across **{len(by_module)}** modules.\n",
            "| Module | Component | Selector | Routes | API Calls | File |",
            "|--------|-----------|----------|--------|-----------|------|",
        ]
        for module in sorted(by_module.keys()):
            for c in sorted(by_module[module], key=lambda x: x.name):
                routes = ", ".join(c.routes[:3]) or "-"
                if len(c.routes) > 3:
                    routes += f" (+{len(c.routes) - 3})"
                api_calls = ", ".join(f"`{a}`" for a in c.api_calls[:3]) or "-"
                if len(c.api_calls) > 3:
                    api_calls += f" (+{len(c.api_calls) - 3})"
                parts.append(
                    f"| {module} | **{c.name}** | `{c.selector or '-'}` | "
                    f"{routes} | {api_calls} | {c.component_file} |"
                )

        # Wiring diagram: Component → API path → backend Controller
        # Build endpoint → controller lookup keyed by route fragment.
        ep_lookup = []
        for ep in report.endpoints:
            route = (ep.route or "").strip("/").lower()
            if route:
                ep_lookup.append((route, ep.controller, ep.method))

        diag_lines = ["```mermaid", "graph LR"]
        seen_nodes = set()
        edges = []
        for c in ui:
            if not c.api_calls:
                continue
            comp_id = self._mermaid_id(c.name)
            comp_label = self._mermaid_label(c.name)
            if comp_id not in seen_nodes:
                diag_lines.append(f'    {comp_id}["{comp_label}"]')
                seen_nodes.add(comp_id)
            for call in c.api_calls[:5]:
                call_norm = call.strip("/").lower()
                if not call_norm:
                    continue
                # Match against endpoints by suffix containment.
                matched_ctrl = None
                for ep_route, ep_ctrl, _ep_method in ep_lookup:
                    if ep_route and (ep_route in call_norm or call_norm in ep_route):
                        matched_ctrl = ep_ctrl
                        break
                if matched_ctrl:
                    ctrl_id = self._mermaid_id(matched_ctrl)
                    if ctrl_id not in seen_nodes:
                        diag_lines.append(
                            f'    {ctrl_id}(["{self._mermaid_label(matched_ctrl)}"])'
                        )
                        seen_nodes.add(ctrl_id)
                    edge_label = self._mermaid_label(call, 24)
                    edges.append(f"    {comp_id} -->|{edge_label}| {ctrl_id}")
                else:
                    # Unmatched call: render as a leaf node so the user
                    # still sees the outbound dependency.
                    leaf_id = self._mermaid_id(call_norm)[:20] or "ext"
                    leaf_id = re.sub(r"[^A-Za-z0-9_]", "_", leaf_id)
                    leaf_id = f"ext_{leaf_id}"
                    if leaf_id not in seen_nodes:
                        diag_lines.append(
                            f'    {leaf_id}[/"{self._mermaid_label(call)}"/]'
                        )
                        seen_nodes.add(leaf_id)
                    edges.append(f"    {comp_id} --> {leaf_id}")
        diag_lines.extend(edges)
        diag_lines.append("```")

        if edges:
            parts.append("\n### UI → API Wiring\n")
            parts.extend(diag_lines)

        return "\n".join(parts)

    def _section_data_models(self, report: CrawlReport) -> str:
        if not report.data_models:
            return ""

        parts = [
            "## Data Models\n",
            f"Total: **{len(report.data_models)}** entities\n",
            "| Entity | DbContext | Properties | File |",
            "|--------|-----------|------------|------|",
        ]
        for dm in report.data_models:
            props = ", ".join(dm.properties[:5])
            if len(dm.properties) > 5:
                props += f" (+{len(dm.properties) - 5} more)"
            parts.append(f"| **{dm.name}** | {dm.db_context} | {props} | {dm.file} |")

        return "\n".join(parts)

    def _section_code_flow(self, report: CrawlReport) -> str:
        """Render narrative 'Code Flow' walkthroughs for representative
        entry points (controllers/endpoints).

        Each flow follows the structure:
          Introduction → Following the flow → Things to note
        and embeds real code snippets pulled from the source files.
        """
        if not report.endpoints:
            return ""

        from pathlib import Path as _Path

        # Group endpoints by controller, prefer authorized routes first
        by_ctrl: Dict[str, List] = {}
        for ep in report.endpoints:
            by_ctrl.setdefault(ep.controller, []).append(ep)

        # Pick up to 4 representative controllers (those with auth bubble up)
        ranked = sorted(
            by_ctrl.items(),
            key=lambda kv: (
                0 if any(e.auth_required for e in kv[1]) else 1,
                -len(kv[1]),
                kv[0],
            ),
        )[:4]
        if not ranked:
            return ""

        # Build a quick map of consumer message types so we can call out
        # async fan-out triggered by the controller body.
        consumer_msgs = {c.message_type: c.consumer_class for c in report.consumers}

        # Map endpoint controllers → owning business domain (if any)
        ep_to_domain: Dict[str, str] = {}
        for d in getattr(report, "business_domains", None) or []:
            for ep in getattr(d, "endpoints", []) or []:
                ep_to_domain[getattr(ep, "controller", "")] = d.name

        intro = [
            "## Code Flow",
            "",
            "### Introduction",
            "",
            "This section describes the runtime flow through the system for "
            "the most important entry points discovered in this solution. "
            "Each walkthrough follows a single request from the HTTP boundary "
            "down through the layers it touches, so you can understand how "
            "the different parts come together to create the full picture.",
            "",
            "The flows below were selected automatically: authenticated "
            "endpoints and controllers with the highest endpoint count are "
            "prioritized as they tend to represent the primary use cases.",
        ]

        flows: List[str] = []
        for ctrl_name, eps in ranked:
            primary = eps[0]
            # Try to read the controller file and extract the action body
            snippet, action_method, file_label = self._extract_action_snippet(
                primary.file, primary.line
            )

            # Detect downstream message types referenced in the snippet
            triggered = []
            for msg, cons in consumer_msgs.items():
                if msg and msg in snippet:
                    triggered.append((msg, cons))

            domain_name = ep_to_domain.get(ctrl_name, "")

            flow_parts = [
                f"### Flow: {ctrl_name}",
                "",
                "#### Introduction",
                "",
                f"This flow begins when a client issues an **{primary.method} "
                f"`{primary.route or '/'}`** request handled by "
                f"`{ctrl_name}`"
                + (f" in the **{domain_name}** domain" if domain_name else "")
                + ". "
                + (
                    "The endpoint is protected and requires the caller to "
                    "be authenticated."
                    if primary.auth_required
                    else "The endpoint is currently unauthenticated."
                ),
                "",
                "#### Following the flow",
                "",
                f"The entry point lives in `{file_label}`"
                + (f" around line {primary.line}" if primary.line else "")
                + ". The action method below is where the flow begins; from "
                "here it dispatches to the application/services layer:",
                "",
                "```csharp",
                snippet or f"// Source for {action_method or 'action'} not available",
                "```",
                "",
            ]

            # If the same controller exposes more endpoints, list them so the
            # reader knows the surrounding API surface.
            if len(eps) > 1:
                flow_parts.append(
                    f"`{ctrl_name}` exposes **{len(eps)}** endpoints in total. "
                    "Other routes on the same controller follow the same "
                    "general flow:"
                )
                flow_parts.append("")
                for e in eps[:6]:
                    flow_parts.append(
                        f"- `{e.method} {e.route or '/'}`"
                        + (" _(auth required)_" if e.auth_required else "")
                    )
                if len(eps) > 6:
                    flow_parts.append(f"- _… +{len(eps) - 6} more_")
                flow_parts.append("")

            # Mention message-bus fan-out if we detected any
            if triggered:
                flow_parts.append(
                    "The action also publishes messages onto the bus, "
                    "which are picked up asynchronously by the following "
                    "consumers:"
                )
                flow_parts.append("")
                for msg, cons in triggered[:5]:
                    flow_parts.append(f"- `{msg}` → handled by `{cons}`")
                flow_parts.append("")

            # Things to note ------------------------------------------------
            notes: List[str] = []
            if primary.auth_required:
                notes.append(
                    "**Authorization** is enforced at the controller level — "
                    "any change here must preserve the `[Authorize]` "
                    "contract or the endpoint will silently become public."
                )
            else:
                notes.append(
                    "This route is **unauthenticated**. Confirm whether "
                    "that is intentional before exposing it on the public "
                    "edge."
                )
            if triggered:
                notes.append(
                    "The flow is **partially asynchronous**: messages "
                    "published from the action are processed out-of-band "
                    "by the consumers listed above. Failures in those "
                    "consumers will not surface in the HTTP response."
                )
            if domain_name:
                notes.append(
                    f"This flow belongs to the **{domain_name}** business "
                    "domain. Cross-domain changes should be reviewed "
                    "against that domain's contracts."
                )
            notes.append(
                f"Typical callers: anything that talks to "
                f"`{primary.route or '/'}` — front-end clients, partner "
                "integrations, or internal jobs depending on the route."
            )

            flow_parts.append("#### Things to note")
            flow_parts.append("")
            for n in notes:
                flow_parts.append(f"- {n}")
            flow_parts.append("")

            flows.append("\n".join(flow_parts))

        return "\n".join(intro) + "\n\n" + "\n".join(flows)

    def _extract_action_snippet(self, file_path: str, line: int) -> tuple:
        """Read the source file and return (snippet, method_name, file_label).

        Walks forward from `line` to find the next method declaration and
        extracts its body using brace balancing. Falls back to a few lines
        of context if no clean method is found.
        """
        from pathlib import Path as _Path

        if not file_path:
            return "", "", ""
        p = _Path(file_path)
        try:
            content = p.read_text(encoding="utf-8", errors="ignore")
        except Exception as e:
            logger.debug(f"_extract_action_snippet read failed for {file_path}: {e}")
            return "", "", file_path

        try:
            file_label = str(p.relative_to(_Path.cwd()))
        except Exception:
            file_label = p.name

        lines = content.splitlines()
        # Compute char offset of each line
        offsets = []
        cur = 0
        for ln in lines:
            offsets.append(cur)
            cur += len(ln) + 1

        start_idx = max(0, (line or 1) - 1)
        # Walk down from `start_idx` to find a method-like declaration
        method_re = re.compile(
            r"^\s*(?:public|private|protected|internal)\s+(?:async\s+)?"
            r"(?:static\s+|virtual\s+|override\s+)?[\w<>?\[\],. ]+\s+"
            r"(\w+)\s*\([^)]*\)"
        )
        for j in range(start_idx, min(start_idx + 25, len(lines))):
            m = method_re.match(lines[j])
            if not m:
                continue
            method_name = m.group(1)
            # Find the opening brace from this line forward
            join_pos = offsets[j] if j < len(offsets) else 0
            tail = content[join_pos:]
            brace = tail.find("{")
            semi = tail.find(";")
            if brace == -1 or (semi != -1 and semi < brace):
                # expression-bodied or interface decl
                snippet = "\n".join(lines[j:j + 4])
                return snippet, method_name, file_label
            # Walk balanced braces
            depth = 0
            end_off = None
            for k in range(join_pos + brace, len(content)):
                ch = content[k]
                if ch == "{":
                    depth += 1
                elif ch == "}":
                    depth -= 1
                    if depth == 0:
                        end_off = k
                        break
            if end_off is None:
                snippet = "\n".join(lines[j:j + 12])
                return snippet, method_name, file_label
            snippet = content[join_pos:end_off + 1]
            # Cap snippet length so the doc doesn't blow up
            if len(snippet) > 1800:
                snippet = snippet[:1800].rstrip() + "\n    // ... truncated"
            return snippet, method_name, file_label

        # Fallback: a small window of context
        end = min(len(lines), start_idx + 12)
        return "\n".join(lines[start_idx:end]), "", file_label

    def _section_er_diagram(self, report: CrawlReport) -> str:
        """Render an Entity-Relationship diagram (Mermaid erDiagram) plus
        per-entity attribute and relationship breakdown."""
        if not report.data_models:
            return ""

        # Group entities by DbContext for clarity
        by_ctx: Dict[str, List] = {}
        for dm in report.data_models:
            by_ctx.setdefault(dm.db_context or "Default", []).append(dm)

        entity_names = {dm.name for dm in report.data_models}

        def _safe_attr_type(t: str) -> str:
            """Mermaid erDiagram attribute types must be alphanumeric — sanitize."""
            t = re.sub(r"<[^>]+>", "", t)
            t = t.replace("?", "").replace("[]", "Array").strip()
            t = re.sub(r"[^A-Za-z0-9_]", "", t) or "string"
            return t

        parts = [
            "## Entity-Relationship Diagram\n",
            f"Auto-derived from **{len(report.data_models)}** EF Core entities "
            f"across **{len(by_ctx)}** DbContext(s). Relationships are inferred "
            "from navigation properties (`ICollection<X>`, single-entity refs) "
            "and `<Entity>Id` foreign-key conventions.\n",
            "```mermaid",
            "erDiagram",
        ]

        # Emit attributes
        for dm in report.data_models:
            parts.append(f"    {dm.name} {{")
            shown = 0
            for prop in dm.properties[:15]:
                # prop is "Type Name" or just "Name"
                bits = prop.rsplit(" ", 1)
                if len(bits) == 2:
                    ptype, pname = bits
                else:
                    ptype, pname = "string", bits[0]
                parts.append(f"        {_safe_attr_type(ptype)} {re.sub(r'[^A-Za-z0-9_]', '', pname)}")
                shown += 1
            if shown == 0:
                parts.append("        string id")
            parts.append("    }")

        # Emit relationships (dedupe per ordered pair)
        seen = set()
        for dm in report.data_models:
            for rel in dm.relationships:
                if ":" not in rel:
                    continue
                kind, target = rel.split(":", 1)
                if target not in entity_names or target == dm.name:
                    continue
                key = (dm.name, target, kind)
                if key in seen:
                    continue
                seen.add(key)
                if kind == "1..*":
                    parts.append(f'    {dm.name} ||--o{{ {target} : "has many"')
                elif kind == "*..1":
                    parts.append(f'    {dm.name} }}o--|| {target} : "belongs to"')
                else:
                    parts.append(f'    {dm.name} ||--|| {target} : "related"')

        parts.append("```")

        # Per-DbContext attribute breakdown table
        for ctx, dms in by_ctx.items():
            parts.append(f"\n### `{ctx}`\n")
            parts.append("| Entity | Attributes | Relationships |")
            parts.append("|--------|------------|---------------|")
            for dm in dms:
                attrs = ", ".join(dm.properties[:8]) or "—"
                if len(dm.properties) > 8:
                    attrs += f" (+{len(dm.properties) - 8} more)"
                rels = ", ".join(dm.relationships[:6]) or "—"
                parts.append(f"| **{dm.name}** | {attrs} | {rels} |")

        return "\n".join(parts)

    # ── Deep-Analysis Section Builders ─────────────────────────────────

    def _section_business_domains(self, report: CrawlReport) -> str:
        domains = getattr(report, "business_domains", None) or []
        if not domains:
            return ""

        parts = [
            "## Business Domains\n",
            f"Total: **{len(domains)}** business domains discovered by clustering "
            f"projects, namespaces, aggregates and domain events.\n",
        ]
        for d in domains:
            parts.append(f"\n### {d.name}")
            if getattr(d, "description", ""):
                parts.append(f"_{d.description}_\n")
            if d.projects:
                parts.append(f"- **Projects** ({len(d.projects)}): {', '.join(d.projects)}")
            if d.namespaces:
                ns = ", ".join(sorted(d.namespaces)[:8])
                if len(d.namespaces) > 8:
                    ns += f" (+{len(d.namespaces) - 8} more)"
                parts.append(f"- **Namespaces**: {ns}")
            if d.aggregates:
                parts.append(f"- **Aggregate Roots** ({len(d.aggregates)}): "
                             f"{', '.join(d.aggregates[:10])}"
                             + (f" (+{len(d.aggregates) - 10})" if len(d.aggregates) > 10 else ""))
            if d.domain_events:
                parts.append(f"- **Domain Events** ({len(d.domain_events)}): "
                             f"{', '.join(d.domain_events[:10])}"
                             + (f" (+{len(d.domain_events) - 10})" if len(d.domain_events) > 10 else ""))
            if d.endpoints:
                parts.append(f"- **Endpoints**: {len(d.endpoints)}")
            inbound = getattr(d, "inbound_contracts", []) or []
            outbound = getattr(d, "outbound_contracts", []) or []
            if inbound or outbound:
                parts.append(f"- **Contracts**: {len(inbound)} inbound, {len(outbound)} outbound")

        return "\n".join(parts)

    def _section_sequence_flows(self, report: CrawlReport) -> str:
        """Per-domain sequence diagrams showing how components interact at runtime.

        For each business domain that has any inbound endpoints OR outbound
        contracts, render a Mermaid sequenceDiagram with:
          Client → Controllers (grouped) → outbound services (http/rabbit/grpc/...)
          Consumers ← MessageBus (for queue-driven flows)
        Falls back to a single solution-wide sequence if no business domains
        were discovered (deep_analysis disabled).
        """
        domains = getattr(report, "business_domains", None) or []
        contracts = getattr(report, "domain_contracts", None) or []

        # Helpers ---------------------------------------------------------
        def _safe(s):
            return (str(s or "").replace('"', "'")).strip() or "?"

        def _alias(prefix, name, used):
            base = self._mermaid_id(name) or prefix
            alias = f"{prefix}_{base}"
            i = 0
            while alias in used:
                i += 1
                alias = f"{prefix}_{base}_{i}"
            used.add(alias)
            return alias

        def _diagram_for(title, controllers_in_scope, outbound_in_scope, consumers_in_scope):
            """Render one sequenceDiagram block."""
            if not controllers_in_scope and not outbound_in_scope and not consumers_in_scope:
                return ""
            used = set()
            parts = [f"### {title}", "```mermaid", "sequenceDiagram", "    autonumber"]
            client_alias = _alias("Client", "ext", used)
            parts.append(f'    actor {client_alias} as "Client"')

            # Controllers as participants
            ctrl_aliases = {}
            for ctrl_name in sorted(controllers_in_scope):
                alias = _alias("Ctrl", ctrl_name, used)
                ctrl_aliases[ctrl_name] = alias
                parts.append(f'    participant {alias} as "{_safe(ctrl_name)}"')

            # Outbound services (target_service grouped by transport)
            ext_aliases = {}
            for tgt, transport in sorted(outbound_in_scope):
                key = (tgt, transport)
                if key in ext_aliases:
                    continue
                alias = _alias("Ext", f"{tgt}_{transport}", used)
                ext_aliases[key] = alias
                label = f"{_safe(tgt)} ({transport})" if transport else _safe(tgt)
                parts.append(f'    participant {alias} as "{label}"')

            # Message bus / consumers (queue-driven flows)
            bus_alias = None
            consumer_aliases = {}
            if consumers_in_scope:
                bus_alias = _alias("Bus", "messagebus", used)
                parts.append(f'    participant {bus_alias} as "Message Bus"')
                for c in sorted(consumers_in_scope, key=lambda x: x[0]):
                    cons_class, msg_type = c
                    alias = _alias("Cons", cons_class, used)
                    consumer_aliases[c] = alias
                    parts.append(f'    participant {alias} as "{_safe(cons_class)}"')

            # Interactions: Client → each controller → each outbound
            for ctrl_name in sorted(controllers_in_scope):
                ctrl_alias = ctrl_aliases[ctrl_name]
                ep_count = controllers_in_scope[ctrl_name]
                parts.append(
                    f'    {client_alias}->>{ctrl_alias}: HTTP request '
                    f'({ep_count} endpoint{"s" if ep_count != 1 else ""})'
                )
                # All outbound from this scope go through the controller
                for (tgt, transport), ext_alias in ext_aliases.items():
                    arrow = "->>"  # solid for sync, dashed for async
                    note = transport or "call"
                    if transport.lower() in ("rabbitmq", "kafka", "queue"):
                        arrow = "-->>"  # async
                    parts.append(f'    {ctrl_alias}{arrow}{ext_alias}: {note}')
                    if arrow == "->>":
                        parts.append(f'    {ext_alias}-->>{ctrl_alias}: response')
                parts.append(f'    {ctrl_alias}-->>{client_alias}: HTTP response')

            # Consumers: Bus → Consumer
            for (cons_class, msg_type), cons_alias in consumer_aliases.items():
                parts.append(f'    {bus_alias}-->>{cons_alias}: {_safe(msg_type)}')
                parts.append(f'    {cons_alias}->>{cons_alias}: handle({_safe(msg_type)})')

            parts.append("```")
            return "\n".join(parts)

        sections = ["## Sequence Flows\n",
                    "End-to-end runtime interactions discovered by joining "
                    "controllers, DI'd named clients, configured service URLs, "
                    "and message consumers. One diagram per business domain.\n"]

        any_diagram = False

        if domains:
            # Build per-domain views
            # Map controller name → endpoint count (per domain)
            for d in domains:
                domain_projects = set(d.projects or [])
                controllers_in_scope = defaultdict(int)
                for ep in report.endpoints:
                    # Heuristic: attribute endpoint to a domain via the project
                    # whose source folder matches its file path.
                    file_path = (ep.file or "")
                    matched = any(p in file_path for p in domain_projects)
                    if matched and ep.controller:
                        controllers_in_scope[ep.controller] += 1
                # Outbound: domain_contracts whose source matches this domain
                outbound = set()
                for c in contracts:
                    src_dom = getattr(c, "source_domain", "") or ""
                    src_proj = getattr(c, "source_project", "") or ""
                    if src_dom == d.name or src_proj in domain_projects:
                        outbound.add(
                            (getattr(c, "target_service", "") or "?",
                             getattr(c, "transport", "") or "")
                        )
                # Consumers attached to projects in this domain
                consumers_in_scope = []
                for c in report.consumers:
                    if any(p in (c.file or "") for p in domain_projects):
                        consumers_in_scope.append((c.consumer_class, c.message_type))

                diag = _diagram_for(
                    f"Domain — {d.name}",
                    controllers_in_scope,
                    outbound,
                    consumers_in_scope,
                )
                if diag:
                    sections.append(diag)
                    any_diagram = True
        else:
            # Fallback: one solution-wide diagram
            controllers_in_scope = defaultdict(int)
            for ep in report.endpoints:
                if ep.controller:
                    controllers_in_scope[ep.controller] += 1
            outbound = set()
            for c in contracts:
                outbound.add(
                    (getattr(c, "target_service", "") or "?",
                     getattr(c, "transport", "") or "")
                )
            # If no contracts, fall back to integrations
            if not outbound:
                for i in report.integrations:
                    outbound.add((i.target or i.type, i.type))
            consumers_in_scope = [
                (c.consumer_class, c.message_type) for c in report.consumers
            ]
            diag = _diagram_for(
                "Solution-wide Flow",
                controllers_in_scope,
                outbound,
                consumers_in_scope,
            )
            if diag:
                sections.append(diag)
                any_diagram = True

        if not any_diagram:
            return ""
        return "\n\n".join(sections)

    def _section_domain_contracts(self, report: CrawlReport) -> str:
        contracts = getattr(report, "domain_contracts", None) or []
        if not contracts:
            return ""

        parts = [
            "## Domain Contracts\n",
            f"Total: **{len(contracts)}** cross-domain integration contracts "
            f"(joined from DI registrations + configuration URLs).\n",
            "| Source Domain | Target Service | Transport | Interface | Config URL | Registered At |",
            "|---------------|----------------|-----------|-----------|------------|----------------|",
        ]
        for c in contracts:
            src_domain = getattr(c, "source_domain", "") or ""
            target = getattr(c, "target_service", "") or ""
            transport = getattr(c, "transport", "") or ""
            iface = getattr(c, "interface", "") or ""
            cfg = getattr(c, "config_url", "") or ""
            reg_file = getattr(c, "registration_file", "") or ""
            reg_line = getattr(c, "registration_line", 0) or 0
            reg = f"{reg_file}:{reg_line}" if reg_file else ""
            parts.append(
                f"| {src_domain} | {target} | {transport} | `{iface}` | "
                f"`{cfg}` | {reg} |"
            )
        return "\n".join(parts)

    def _section_configurations(self, report: CrawlReport) -> str:
        rows = []
        for p in report.projects:
            for cfg in getattr(p, "configurations", None) or []:
                rows.append((p.name, cfg))
        if not rows:
            return ""

        # Group by kind
        by_kind = defaultdict(list)
        for proj_name, cfg in rows:
            kind = getattr(cfg, "kind", "") or "setting"
            by_kind[kind].append((proj_name, cfg))

        parts = [
            "## Configuration\n",
            f"Total: **{len(rows)}** configuration keys across "
            f"**{len({p for p, _ in rows})}** projects "
            f"(parsed from `appsettings*.json`, `launchSettings.json`, `web.config`, `app.config`).\n",
        ]

        for kind in sorted(by_kind.keys()):
            entries = by_kind[kind]
            parts.append(f"\n### {kind.replace('_', ' ').title()} ({len(entries)})")
            parts.append("| Project | Key | Value | Source | Env Var |")
            parts.append("|---------|-----|-------|--------|---------|")
            for proj_name, cfg in entries:
                key = getattr(cfg, "key", "") or ""
                val = getattr(cfg, "value", "") or ""
                if isinstance(val, str) and len(val) > 60:
                    val = val[:57] + "..."
                src_file = getattr(cfg, "source_file", "") or ""
                env = getattr(cfg, "references_env_var", "") or ""
                parts.append(
                    f"| {proj_name} | `{key}` | `{val}` | {src_file} | {env} |"
                )
        return "\n".join(parts)

    def _section_di_registrations(self, report: CrawlReport) -> str:
        rows = []
        for p in report.projects:
            for reg in getattr(p, "di_registrations", None) or []:
                rows.append((p.name, reg))
        if not rows:
            return ""

        parts = [
            "## Dependency Injection Graph\n",
            f"Total: **{len(rows)}** DI registrations discovered "
            f"(`AddSingleton`, `AddScoped`, `AddTransient`, `AddHttpClient`, `AddDbContext`, `AddMediatR`, `AddMassTransit`).\n",
            "| Project | Method | Service | Implementation | Named Client | Source |",
            "|---------|--------|---------|----------------|--------------|--------|",
        ]
        for proj_name, reg in rows:
            method = getattr(reg, "method", "") or ""
            svc = getattr(reg, "service_type", "") or ""
            impl = getattr(reg, "implementation", "") or ""
            named = getattr(reg, "named_client", "") or ""
            src_file = getattr(reg, "source_file", "") or ""
            line = getattr(reg, "line", 0) or 0
            parts.append(
                f"| {proj_name} | `{method}` | `{svc}` | `{impl}` | {named} | {src_file}:{line} |"
            )
        return "\n".join(parts)

    def _section_code_symbols(self, report: CrawlReport) -> str:
        rows = []
        for p in report.projects:
            for sym in getattr(p, "code_symbols", None) or []:
                rows.append((p.name, sym))
        if not rows:
            return ""

        # Bucket DDD-tagged symbols
        aggregates, events, vos, repos, controllers, others = [], [], [], [], [], []
        for proj_name, sym in rows:
            if getattr(sym, "is_aggregate_root", False):
                aggregates.append((proj_name, sym))
            elif getattr(sym, "is_domain_event", False):
                events.append((proj_name, sym))
            elif getattr(sym, "is_value_object", False):
                vos.append((proj_name, sym))
            elif getattr(sym, "is_repository", False):
                repos.append((proj_name, sym))
            elif getattr(sym, "is_controller", False):
                controllers.append((proj_name, sym))
            else:
                others.append((proj_name, sym))

        parts = [
            "## Code Symbols (DDD)\n",
            f"Total: **{len(rows)}** types extracted from C# source "
            f"(classes, interfaces, records, structs, enums) with DDD heuristics applied.\n",
            "| Bucket | Count |\n|--------|-------|",
            f"| Aggregate Roots | {len(aggregates)} |",
            f"| Domain Events | {len(events)} |",
            f"| Value Objects | {len(vos)} |",
            f"| Repositories | {len(repos)} |",
            f"| Controllers | {len(controllers)} |",
            f"| Other Types | {len(others)} |",
        ]

        def _bucket(title: str, bucket: list, limit: int = 30):
            if not bucket:
                return
            parts.append(f"\n### {title} ({len(bucket)})")
            parts.append("| Type | Namespace | Project | Source |")
            parts.append("|------|-----------|---------|--------|")
            for proj_name, sym in bucket[:limit]:
                name = getattr(sym, "name", "") or ""
                ns = getattr(sym, "namespace", "") or ""
                src_file = getattr(sym, "file", "") or ""
                line = getattr(sym, "line", 0) or 0
                parts.append(f"| `{name}` | `{ns}` | {proj_name} | {src_file}:{line} |")
            if len(bucket) > limit:
                parts.append(f"\n_... and {len(bucket) - limit} more_")

        _bucket("Aggregate Roots", aggregates)
        _bucket("Domain Events", events)
        _bucket("Value Objects", vos)
        _bucket("Repositories", repos)
        _bucket("Controllers", controllers)

        return "\n".join(parts)

    @staticmethod
    def _mermaid_id(name: str) -> str:
        """Sanitize an arbitrary string into a Mermaid-safe node id."""
        if not name:
            return ""
        return (
            str(name)
            .replace(".", "_")
            .replace("-", "_")
            .replace(" ", "_")
            .replace("/", "_")
            .replace("\\", "_")
        )

    @staticmethod
    def _mermaid_label(text: str, max_len: int = 40) -> str:
        """Sanitize a string for use inside a Mermaid node label.

        Mermaid's parser breaks on `"`, `<`, `>`, parentheses, brackets,
        braces, pipes and backslashes inside the label payload — even
        when wrapped in quoted forms like `[" ... "]`. We strip them
        defensively so kroki + streamlit-mermaid both render the diagram.
        """
        if not text:
            return ""
        s = str(text)
        # Replace characters Mermaid treats as syntax inside node labels
        for ch in '"<>()[]{}|\\`':
            s = s.replace(ch, " ")
        s = " ".join(s.split())  # collapse whitespace
        if len(s) > max_len:
            s = s[: max_len - 1] + "…"
        return s

    def _section_dependency_graph(self, report: CrawlReport) -> str:
        # Pull nodes from the crawler's dependency_graph if present, otherwise
        # synthesize them from report.projects so the section never silently
        # disappears.
        raw_nodes = report.dependency_graph.get("nodes") or []
        raw_edges = report.dependency_graph.get("edges") or []

        # _build_dependency_graph emits nodes as {"id": name, "layer": layer}
        # but earlier callers may pass plain strings — handle both shapes.
        node_layer = {}
        for n in raw_nodes:
            if isinstance(n, dict):
                nid = n.get("id", "")
                if nid:
                    node_layer[nid] = n.get("layer", "Unknown") or "Unknown"
            elif isinstance(n, str):
                node_layer[n] = "Unknown"
        # Fallback / augmentation from project list
        for p in report.projects:
            if p.name and p.name not in node_layer:
                node_layer[p.name] = p.layer or "Unknown"

        # Project → project references (compile-time)
        ref_edges = []
        for e in raw_edges:
            if not isinstance(e, dict):
                continue
            src = e.get("source") or e.get("from") or ""
            tgt = e.get("target") or e.get("to") or ""
            if src and tgt:
                ref_edges.append((src, tgt))

        # Cross-service runtime contracts (HTTP/RabbitMQ/etc.) discovered by
        # the deep analyzer — overlay as dotted edges so the user sees the
        # actual runtime topology, not just .csproj references.
        contract_edges = []
        for c in getattr(report, "domain_contracts", None) or []:
            src = getattr(c, "source_project", "") or getattr(c, "source_domain", "")
            tgt = getattr(c, "target_service", "")
            transport = getattr(c, "transport", "") or ""
            if src and tgt:
                contract_edges.append((src, tgt, transport))

        if not node_layer and not ref_edges and not contract_edges:
            return ""

        # Group nodes by layer for visual subgraphs
        by_layer = defaultdict(list)
        for name, layer in node_layer.items():
            by_layer[layer].append(name)

        lines = [
            "## Dependency Graph\n",
            "Compile-time references are solid arrows. Runtime cross-service "
            "contracts (HTTP / RabbitMQ / gRPC etc.) discovered by the deep "
            "analyzer are dotted arrows.\n",
            "```mermaid",
            "graph LR",
        ]

        # Subgraphs by layer
        for layer in sorted(by_layer.keys()):
            safe_layer = self._mermaid_id(layer) or "Unknown"
            lines.append(f'    subgraph layer_{safe_layer}["{layer}"]')
            for name in sorted(by_layer[layer]):
                nid = self._mermaid_id(name)
                lines.append(f'        {nid}["{name}"]')
            lines.append("    end")

        # Make sure every contract endpoint also has a node, even if it
        # doesn't appear in the project list (external services).
        for src, tgt, _ in contract_edges:
            for n in (src, tgt):
                if n and n not in node_layer:
                    nid = self._mermaid_id(n)
                    lines.append(f'    {nid}(["{n}"])')
                    node_layer[n] = "External"

        # Compile-time edges
        for src, tgt in ref_edges:
            s = self._mermaid_id(src)
            t = self._mermaid_id(tgt)
            if s and t:
                lines.append(f"    {s} --> {t}")

        # Runtime contract edges (dotted, labeled by transport)
        for src, tgt, transport in contract_edges:
            s = self._mermaid_id(src)
            t = self._mermaid_id(tgt)
            if s and t:
                label = f"|{transport}|" if transport else ""
                lines.append(f"    {s} -.->{label} {t}")

        lines.append("```")

        # Append a textual edge list for accessibility / when Mermaid fails
        if ref_edges or contract_edges:
            lines.append("\n### Edges\n")
            lines.append("| Source | Target | Kind |")
            lines.append("|--------|--------|------|")
            for src, tgt in ref_edges:
                lines.append(f"| {src} | {tgt} | reference |")
            for src, tgt, transport in contract_edges:
                kind = f"contract ({transport})" if transport else "contract"
                lines.append(f"| {src} | {tgt} | {kind} |")

        return "\n".join(lines)

    # ──────────────────────────────────────────────────────────────────
    # Architecture Doc (DDD / Clean Architecture) — 8 sections
    # ──────────────────────────────────────────────────────────────────

    # Per-layer narrative used when explaining each project. Keeps the
    # doc readable for stakeholders who don't already know Clean Arch.
    _LAYER_DESCRIPTION = {
        "Domain": (
            "Pure business model. Holds entities, value objects, aggregates "
            "and domain events. Has **no dependencies** on other layers."
        ),
        "Application": (
            "Use-case orchestration. Coordinates the domain layer, defines "
            "command/query handlers, and exposes interfaces (ports) that "
            "infrastructure adapters implement."
        ),
        "Infrastructure": (
            "External adapters: persistence (EF Core / DbContext), "
            "messaging (RabbitMQ / MassTransit), HTTP clients, file "
            "storage, third-party SDKs. Implements interfaces declared "
            "in Application/Domain."
        ),
        "Presentation": (
            "Inbound delivery layer — typically ASP.NET Core Web API "
            "controllers, gRPC services or background hosts. Translates "
            "HTTP/transport concerns into Application calls."
        ),
        "Worker": (
            "Long-running host process. Subscribes to message queues, "
            "runs scheduled jobs, and dispatches work to the Application "
            "layer."
        ),
        "Contracts": (
            "Public message contracts shared across services — DTOs, "
            "events, and integration interfaces. Decouples producers "
            "from consumers."
        ),
        "Shared": (
            "Cross-cutting utilities reused by multiple projects "
            "(logging, telemetry, common types). Should remain free "
            "of business rules."
        ),
        "Tests": "Unit / integration test projects. Excluded from runtime topology.",
        "Uncategorized": "Layer not detected — review the project's role manually.",
        "Unknown": "Layer not detected — review the project's role manually.",
    }

    @staticmethod
    def _summarize_symbols(symbols: list, max_per_kind: int = 5) -> Dict[str, List[str]]:
        """Bucket code symbols by DDD role / kind for narrative inclusion."""
        buckets: Dict[str, List[str]] = defaultdict(list)
        for s in symbols or []:
            name = getattr(s, "name", "") or ""
            if not name:
                continue
            if getattr(s, "is_aggregate_root", False):
                buckets["Aggregates"].append(name)
            elif getattr(s, "is_value_object", False):
                buckets["Value Objects"].append(name)
            elif getattr(s, "is_domain_event", False):
                buckets["Domain Events"].append(name)
            elif getattr(s, "is_repository", False):
                buckets["Repositories"].append(name)
            elif getattr(s, "is_controller", False):
                buckets["Controllers"].append(name)
            else:
                kind = (getattr(s, "kind", "") or "Other").title()
                buckets[f"{kind}s"].append(name)
        # de-dup and trim
        return {k: sorted(set(v))[:max_per_kind] for k, v in buckets.items()}

    @staticmethod
    def _read_code_snippet(file_path: str, max_lines: int = 18) -> str:
        """Return the first `max_lines` lines of a source file (best-effort).

        Used to embed a representative C# snippet next to each project so
        the doc reads more like a real architecture write-up than a flat
        list of names. Silently returns empty string on any I/O error.
        """
        if not file_path:
            return ""
        try:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as fh:
                lines = []
                for i, line in enumerate(fh):
                    if i >= max_lines:
                        lines.append("// ... truncated ...")
                        break
                    lines.append(line.rstrip())
            # Drop leading using/blank/namespace boilerplate so the snippet
            # actually shows the type definition.
            while lines and (
                lines[0].startswith("using ")
                or lines[0].startswith("//")
                or not lines[0].strip()
            ):
                lines.pop(0)
            return "\n".join(lines).strip()
        except Exception:
            return ""

    def _representative_file_for(self, project) -> str:
        """Pick the most descriptive source file for a project: first the
        aggregate root or controller, otherwise the first symbol's file."""
        symbols = list(project.code_symbols or [])
        if not symbols:
            return ""
        # Prefer aggregates → controllers → repositories → first symbol
        priority = (
            [s for s in symbols if getattr(s, "is_aggregate_root", False)]
            + [s for s in symbols if getattr(s, "is_controller", False)]
            + [s for s in symbols if getattr(s, "is_repository", False)]
            + symbols
        )
        for s in priority:
            f = getattr(s, "file", "")
            if f:
                return f
        return ""

    def _arch_title(self, report: CrawlReport) -> str:
        """Custom title for the architecture-doc structure."""
        from src import __version__ as lumen_version
        sln_name = report.solution.replace("\\", "/").split("/")[-1].replace(".sln", "")
        # Project may be e.g. "CoreTax.sln" → use stem; fall back to "CoreTax"
        title_stem = sln_name or "CoreTax"
        llm_label = _describe_llm(self.llm)
        return (
            f"# {title_stem} - Architecture Documentation\n\n"
            f"> Generated by **Lumen.AI Solution Crawler** v{lumen_version} using `{llm_label}`\n"
            f"> Crawled at: {report.crawled_at.strftime('%Y-%m-%d %H:%M:%S')}\n\n"
            "This document follows the **Domain-Driven Design** (Eric Evans) and "
            "**Clean Architecture** (Robert C. Martin) conventions. Each section "
            "is generated from the actual code discovered during the crawl — "
            "definitions, diagrams and code snippets are derived from real "
            "projects, not boilerplate."
        )

    def _arch_1_bounded_contexts(self, report: CrawlReport) -> str:
        """1. Bounded Context Definition — per project, with description + code snippet."""
        lines = ["## 1. Bounded Context Definition", ""]
        lines.append(
            "A **bounded context** is the boundary within which a particular "
            "domain model applies and the **ubiquitous language** is "
            "consistent. Each project below represents (or contributes to) "
            "a bounded context within the solution."
        )
        lines.append("")

        if not report.projects:
            lines.append("_No projects discovered._")
            return "\n".join(lines)

        # If business_domains are available, group projects under their domain;
        # otherwise group by Clean-Architecture layer.
        domains = report.business_domains or []
        proj_by_name = {p.name: p for p in report.projects}

        if domains:
            for d in domains:
                dname = getattr(d, "name", "Domain")
                ddesc = getattr(d, "description", "") or ""
                lines.append(f"### {dname}")
                if ddesc:
                    lines.append(f"_{ddesc}_")
                    lines.append("")
                for proj_name in (getattr(d, "projects", []) or []):
                    proj = proj_by_name.get(proj_name)
                    if proj:
                        lines.extend(self._render_project_block(proj))
                    else:
                        lines.append(f"#### `{proj_name}`")
                        lines.append("_Project metadata not captured by crawler._")
                        lines.append("")
            # Also include any project not assigned to a domain
            assigned = {pn for d in domains for pn in (getattr(d, "projects", []) or [])}
            unassigned = [p for p in report.projects if p.name not in assigned]
            if unassigned:
                lines.append("### Unassigned Projects")
                lines.append("")
                for p in unassigned:
                    lines.extend(self._render_project_block(p))
            return "\n".join(lines)

        # Fallback: group by layer with narrative
        grouped: Dict[str, List] = defaultdict(list)
        for p in report.projects:
            grouped[p.layer or "Uncategorized"].append(p)
        order = ["Domain", "Application", "Infrastructure", "Presentation",
                 "Worker", "Contracts", "Shared", "Tests", "Uncategorized", "Unknown"]
        for layer in sorted(grouped.keys(),
                            key=lambda x: order.index(x) if x in order else 99):
            lines.append(f"### {layer} Layer")
            blurb = self._LAYER_DESCRIPTION.get(layer)
            if blurb:
                lines.append(f"_{blurb}_")
            lines.append("")
            for proj in sorted(grouped[layer], key=lambda p: p.name):
                lines.extend(self._render_project_block(proj))
        return "\n".join(lines)

    def _render_project_block(self, project) -> List[str]:
        """Render a single project: heading, description, key types, snippet."""
        out: List[str] = []
        out.append(f"#### `{project.name}`")
        layer_blurb = self._LAYER_DESCRIPTION.get(project.layer or "", "")
        meta_bits = []
        if project.layer:
            meta_bits.append(f"**Layer:** {project.layer}")
        if project.framework:
            meta_bits.append(f"**Framework:** {project.framework}")
        if project.references:
            refs = ", ".join(f"`{r}`" for r in project.references[:6])
            meta_bits.append(f"**References:** {refs}")
        if meta_bits:
            out.append(" • ".join(meta_bits))
            out.append("")
        if layer_blurb:
            out.append(layer_blurb)
            out.append("")

        # Symbol summary by DDD role
        buckets = self._summarize_symbols(project.code_symbols)
        if buckets:
            out.append("**Key types:**")
            for kind, names in buckets.items():
                if names:
                    quoted = ", ".join(f"`{n}`" for n in names)
                    out.append(f"- _{kind}_: {quoted}")
            out.append("")

        # Code snippet from the most representative file
        rep_file = self._representative_file_for(project)
        snippet = self._read_code_snippet(rep_file) if rep_file else ""
        if snippet:
            # Show file path relative to the project root for readability
            rel = rep_file
            try:
                proj_dir = project.path
                if proj_dir and rep_file.startswith(proj_dir):
                    rel = rep_file[len(proj_dir):].lstrip("/\\")
            except Exception:
                pass
            out.append(f"_Representative source — `{rel}`:_")
            out.append("```csharp")
            out.append(snippet)
            out.append("```")
            out.append("")
        return out

    @staticmethod
    def _ddd_pattern_for(transport: str) -> str:
        """Map a transport / contract type to a DDD strategic pattern label."""
        t = (transport or "").lower()
        if t in ("http", "rest", "https"):
            return "Partnership (REST)"
        if t == "grpc":
            return "Customer-Supplier (gRPC)"
        if t in ("rabbitmq", "kafka", "azure-servicebus", "sqs", "sns", "event"):
            return "Upstream (Events)"
        if t in ("file", "shared-db", "shareddb"):
            return "Shared Kernel"
        return transport or "Conformist"

    def _arch_2_context_map(self, report: CrawlReport) -> str:
        """2. Context Map — two views: a service-level architecture diagram
        and a DDD strategic-pattern graph between bounded contexts."""
        lines = ["## 2. Context Map", ""]
        lines.append(
            "A **Context Map** shows how bounded contexts relate across the "
            "solution. Two views are provided: (1) a service-level "
            "architecture showing each context as an independent .NET "
            "service, and (2) a DDD strategic-pattern graph annotating the "
            "kind of relationship between contexts (Partnership, "
            "Customer-Supplier, Upstream/Downstream, Shared Kernel, "
            "Anti-Corruption Layer)."
        )
        lines.append("")

        contracts = report.domain_contracts or []
        domains = report.business_domains or []

        if not contracts and not domains:
            lines.append("_No domain contracts or business domains discovered._")
            return "\n".join(lines)

        # --- View 1: architecture-beta service diagram ----------------
        if domains:
            lines.append("### Service View (Architecture)")
            lines.append("")
            sln_stem = (
                report.solution.replace("\\", "/").split("/")[-1]
                .replace(".sln", "")
                or "Solution"
            )
            group_id = re.sub(r"[^A-Za-z0-9_]", "_", sln_stem).lower() or "api"
            lines.append("```mermaid")
            lines.append("architecture-beta")
            lines.append(f"    group {group_id}(logos:dotnet) [{sln_stem}]")
            lines.append("")
            svc_ids: Dict[str, str] = {}
            for d in domains:
                dname = getattr(d, "name", "") or ""
                if not dname:
                    continue
                sid = re.sub(r"[^A-Za-z0-9_]", "_", dname).lower()[:24] or "svc"
                # Ensure uniqueness
                base = sid
                i = 1
                while sid in svc_ids.values():
                    i += 1
                    sid = f"{base}{i}"
                svc_ids[dname] = sid
                lines.append(
                    f"    service {sid}(logos:dotnet) [{dname} Context] "
                    f"in {group_id}"
                )
            lines.append("")
            seen_svc_edges = set()
            for c in contracts:
                src = getattr(c, "source_domain", "") or getattr(c, "source", "")
                tgt = getattr(c, "target_domain", "") or getattr(c, "target", "")
                if not (src and tgt) or src not in svc_ids or tgt not in svc_ids:
                    continue
                key = (svc_ids[src], svc_ids[tgt])
                if key in seen_svc_edges:
                    continue
                seen_svc_edges.add(key)
                lines.append(f"    {svc_ids[src]}:R -- L:{svc_ids[tgt]}")
            lines.append("```")
            lines.append("")

        # --- View 2: DDD strategic-pattern graph ----------------------
        if domains:
            lines.append("### Bounded Context DDD Map")
            lines.append("")
            lines.append("```mermaid")
            lines.append("graph TD")
            lines.append("    %% Define Contexts")
            bc_ids: Dict[str, str] = {}
            for d in domains:
                dname = getattr(d, "name", "") or ""
                if not dname:
                    continue
                bid = re.sub(r"[^A-Za-z0-9_]", "_", dname) + "BC"
                bc_ids[dname] = bid
                lines.append(f'    {bid}["{dname} Context"]')
            lines.append("")
            lines.append("    %% Define Relationships with DDD Patterns")
            seen_ddd_edges = set()
            for c in contracts:
                src = getattr(c, "source_domain", "") or getattr(c, "source", "")
                tgt = getattr(c, "target_domain", "") or getattr(c, "target", "")
                trans = getattr(c, "transport", "") or getattr(c, "type", "")
                if not (src and tgt) or src not in bc_ids or tgt not in bc_ids:
                    continue
                pattern = self._ddd_pattern_for(trans)
                key = (bc_ids[src], bc_ids[tgt], pattern)
                if key in seen_ddd_edges:
                    continue
                seen_ddd_edges.add(key)
                lines.append(
                    f'    {bc_ids[src]} -- "{pattern}" --> {bc_ids[tgt]}'
                )
            # Styling: colour the first two contexts for visual anchor
            if bc_ids:
                dnames = list(bc_ids.keys())
                lines.append("")
                lines.append("    %% Styling")
                if len(dnames) >= 1:
                    lines.append(
                        f"    style {bc_ids[dnames[0]]} "
                        "fill:#f9f,stroke:#333,stroke-width:2px"
                    )
                if len(dnames) >= 2:
                    lines.append(
                        f"    style {bc_ids[dnames[1]]} "
                        "fill:#ccf,stroke:#333,stroke-width:2px"
                    )
            lines.append("```")
            lines.append("")

            # Legend
            lines.append("**DDD Relationship Patterns used above:**")
            lines.append("")
            lines.append(
                "- **Partnership (REST)** — two contexts cooperate via "
                "synchronous HTTP contracts; they succeed or fail together."
            )
            lines.append(
                "- **Customer-Supplier (gRPC)** — upstream supplier exposes "
                "a strongly-typed contract that the downstream customer depends on."
            )
            lines.append(
                "- **Upstream (Events)** — publishes domain events; "
                "downstream contexts subscribe asynchronously."
            )
            lines.append(
                "- **Shared Kernel** — two contexts share a small, explicitly "
                "agreed-upon model (e.g. shared DB or file)."
            )
            lines.append(
                "- **Conformist** — downstream conforms to an upstream model "
                "it cannot influence."
            )
            lines.append("")

        # --- Cross-Context Contracts table ----------------------------
        if contracts:
            lines.append("### Cross-Context Contracts")
            lines.append("")
            lines.append("| Source | Target | Transport | DDD Pattern | Contract |")
            lines.append("|--------|--------|-----------|-------------|----------|")
            for c in contracts:
                src = getattr(c, "source_domain", "") or getattr(c, "source", "")
                tgt = getattr(c, "target_domain", "") or getattr(c, "target", "")
                trans = getattr(c, "transport", "") or getattr(c, "type", "")
                contract = getattr(c, "contract", "") or getattr(c, "message_type", "")
                pattern = self._ddd_pattern_for(trans)
                lines.append(
                    f"| {src or '—'} | {tgt or '—'} | {trans or '—'} "
                    f"| {pattern} | {contract or '—'} |"
                )
        return "\n".join(lines)

    _DDD_ROLE_BLURB = {
        "Entities": (
            "An **Entity** has a distinct identity that persists across state "
            "changes. Two entities are equal only if their identifiers match, "
            "even if all other attributes are identical."
        ),
        "Value Objects": (
            "A **Value Object** has no identity — it is defined entirely by "
            "its attributes. It is immutable; equality is structural."
        ),
        "Aggregates": (
            "An **Aggregate** is a cluster of domain objects treated as a "
            "single consistency boundary. External code interacts only with "
            "the aggregate root, which enforces invariants for the whole cluster."
        ),
        "Repositories": (
            "A **Repository** encapsulates the persistence of an aggregate, "
            "hiding storage concerns behind a collection-like interface "
            "over the domain."
        ),
        "Factories": (
            "A **Factory** encapsulates the complex construction of an "
            "aggregate or entity, ensuring the resulting object is valid "
            "from the moment of creation."
        ),
    }

    def _render_symbol_block(self, proj_name: str, sym) -> List[str]:
        """Render a single DDD symbol: heading, project, properties, code snippet."""
        out: List[str] = []
        nm = getattr(sym, "name", "") or "Unknown"
        out.append(f"#### `{nm}`")
        meta = [f"**Project:** `{proj_name}`"]
        kind = getattr(sym, "kind", "")
        if kind:
            meta.append(f"**Kind:** {kind}")
        out.append(" • ".join(meta))
        out.append("")

        props = getattr(sym, "properties", []) or []
        if not props:
            members = getattr(sym, "members", []) or []
            props = [getattr(m, "name", str(m)) for m in members][:8]
        if props:
            quoted = ", ".join(f"`{p}`" for p in list(props)[:8])
            out.append(f"**Members:** {quoted}")
            out.append("")

        f = getattr(sym, "file", "") or ""
        snippet = self._read_code_snippet(f) if f else ""
        if snippet:
            rel = f.replace("\\", "/").split("/")[-1]
            out.append(f"_Source — `{rel}`:_")
            out.append("```csharp")
            out.append(snippet)
            out.append("```")
            out.append("")
        return out

    def _arch_3_domain_model(self, report: CrawlReport) -> str:
        """3. Domain Model — entities, value objects, aggregates, repos, factories, class diagram."""
        lines = ["## 3. Domain Model", ""]
        lines.append(
            "The domain model captures the heart of the business. The types "
            "below were extracted from the Domain layer and classified by "
            "DDD role using naming conventions and tactical attributes."
        )
        lines.append("")

        # Classify code symbols by DDD role using name heuristics.
        entities: List = []
        value_objects: List = []
        aggregates: List = []
        repositories: List = []
        factories: List = []

        for p in report.projects:
            for sym in (p.code_symbols or []):
                kind = (getattr(sym, "kind", "") or "").lower()
                name = getattr(sym, "name", "") or ""
                role = (getattr(sym, "ddd_role", "") or "").lower()
                lower = name.lower()
                if kind not in ("class", "struct", "record", "interface"):
                    continue
                if role == "aggregateroot" or "aggregate" in lower:
                    aggregates.append((p.name, sym))
                elif role == "valueobject" or lower.endswith("vo") or "value" in lower:
                    value_objects.append((p.name, sym))
                elif role == "repository" or lower.endswith("repository") or lower.endswith("repo"):
                    repositories.append((p.name, sym))
                elif role == "factory" or lower.endswith("factory"):
                    factories.append((p.name, sym))
                elif role == "entity" or kind in ("class", "record"):
                    entities.append((p.name, sym))

        # Also fall back to data_models if no code symbols.
        if not entities and report.data_models:
            entities = [(dm.db_context or "DbContext", dm) for dm in report.data_models]

        def _section(title: str, items: List, per_item_cap: int = 8) -> List[str]:
            sub = [f"### {title}", ""]
            blurb = self._DDD_ROLE_BLURB.get(title, "")
            if blurb:
                sub.append(blurb)
                sub.append("")
            if not items:
                sub.append(f"_No {title.lower()} discovered._")
                sub.append("")
                return sub
            for proj, item in items[:per_item_cap]:
                sub.extend(self._render_symbol_block(proj, item))
            if len(items) > per_item_cap:
                sub.append(
                    f"_…and {len(items) - per_item_cap} more "
                    f"{title.lower()} — full list available in the crawl JSON._"
                )
                sub.append("")
            return sub

        lines.extend(_section("Entities", entities))
        lines.extend(_section("Value Objects", value_objects))
        lines.extend(_section("Aggregates", aggregates))
        lines.extend(_section("Repositories", repositories))
        lines.extend(_section("Factories", factories))

        # Class diagram for top entities + aggregates (cap at 12 to keep readable)
        diagram_targets = (aggregates + entities)[:12]
        if diagram_targets:
            lines.append("### Class Diagram")
            lines.append("")
            lines.append("```mermaid")
            lines.append("classDiagram")

            def _clean_member(raw: str) -> str:
                """Convert 'Id (int)' → 'int Id', 'Name : string' → 'string Name',
                strip anything mermaid's classDiagram grammar will reject."""
                s = str(raw).strip()
                # 'Name (Type)' pattern
                m = re.match(r"^([A-Za-z_][A-Za-z0-9_]*)\s*\(([^)]+)\)$", s)
                if m:
                    return f"{m.group(2).strip()} {m.group(1).strip()}"
                # 'Name: Type' pattern
                if ":" in s:
                    nm, _, ty = s.partition(":")
                    return f"{ty.strip()} {nm.strip()}"
                # strip anything weird — keep alnum/underscore only
                return re.sub(r"[^A-Za-z0-9_ ]+", "_", s)

            for _, item in diagram_targets:
                nm = getattr(item, "name", "")
                if not nm:
                    continue
                safe = re.sub(r"[^A-Za-z0-9_]", "_", nm)
                lines.append(f"  class {safe} {{")
                props = getattr(item, "properties", []) or []
                if not props:
                    members = getattr(item, "members", []) or []
                    props = [getattr(m, "name", str(m)) for m in members]
                for p in (props or [])[:8]:
                    lines.append(f"    +{_clean_member(p)}")
                lines.append("  }")
            # Aggregate → entity composition where we can detect it
            for _, agg in aggregates[:6]:
                anm = getattr(agg, "name", "")
                if not anm:
                    continue
                a_safe = re.sub(r"[^A-Za-z0-9_]", "_", anm)
                for _, ent in entities[:6]:
                    enm = getattr(ent, "name", "")
                    if enm and enm != anm:
                        e_safe = re.sub(r"[^A-Za-z0-9_]", "_", enm)
                        lines.append(f"  {a_safe} *-- {e_safe}")
                        break
            lines.append("```")
        return "\n".join(lines)

    def _arch_4_domain_event_catalogue(self, report: CrawlReport) -> str:
        """4. Domain Event Catalogue — derived from MassTransit consumers."""
        lines = ["## 4. Domain Event Catalogue", ""]
        lines.append(
            "A **domain event** represents something meaningful that has "
            "happened in the domain. Events are published by aggregates and "
            "handled asynchronously by consumers, enabling loose coupling "
            "between bounded contexts."
        )
        lines.append("")
        consumers = report.consumers or []
        if not consumers:
            lines.append("_No domain events / message consumers discovered._")
            return "\n".join(lines)

        # Summary table first
        lines.append("### Summary")
        lines.append("")
        lines.append("| Event / Message | Consumer | Queue |")
        lines.append("|-----------------|----------|-------|")
        for c in consumers:
            msg = (c.message_type or "").split(".")[-1]
            consumer = (c.consumer_class or "").split(".")[-1]
            lines.append(
                f"| {msg or '—'} | {consumer or '—'} | {c.queue or '—'} |"
            )
        lines.append("")

        # Per-consumer detail with code snippet
        lines.append("### Consumer Details")
        lines.append("")
        for c in consumers[:12]:
            msg_short = (c.message_type or "").split(".")[-1] or "Event"
            consumer_short = (c.consumer_class or "").split(".")[-1] or "Consumer"
            lines.append(f"#### `{msg_short}` → `{consumer_short}`")
            meta = []
            if c.queue:
                meta.append(f"**Queue:** `{c.queue}`")
            if c.message_type:
                meta.append(f"**Message:** `{c.message_type}`")
            if meta:
                lines.append(" • ".join(meta))
                lines.append("")
            lines.append(
                f"When a `{msg_short}` event is published to the message bus, "
                f"`{consumer_short}` receives and processes it, triggering "
                f"the associated domain behavior."
            )
            lines.append("")
            snippet = self._read_code_snippet(c.file) if c.file else ""
            if snippet:
                rel = (c.file or "").replace("\\", "/").split("/")[-1]
                lines.append(f"_Source — `{rel}`:_")
                lines.append("```csharp")
                lines.append(snippet)
                lines.append("```")
                lines.append("")
        if len(consumers) > 12:
            lines.append(
                f"_…and {len(consumers) - 12} more consumers — "
                f"see the summary table above._"
            )
        return "\n".join(lines)

    def _classify_layer_artifacts(
        self, report: CrawlReport
    ) -> Dict[str, Dict[str, bool]]:
        """Detect which kinds of artifacts each Clean-Arch layer actually
        contains in this solution. Returns {layer: {artifact_key: True}}.

        Artifact keys roughly follow Clean Architecture conventions:
          - Presentation: Controllers, Filters, ViewModels
          - Application:  Commands, Queries, Services, Interfaces, DTOs
          - Domain:       Entities, ValueObjects, DomainServices, DomainEvents, Exceptions
          - Infrastructure: Persistence, Identity, Messaging, ExternalApis
          - Worker:       Consumers, Schedulers
        """
        out: Dict[str, Dict[str, bool]] = defaultdict(dict)
        for p in report.projects:
            layer = p.layer or "Unknown"
            for s in (p.code_symbols or []):
                name = (getattr(s, "name", "") or "")
                lname = name.lower()
                role = (getattr(s, "ddd_role", "") or "").lower()
                if getattr(s, "is_controller", False) or lname.endswith("controller"):
                    out[layer]["Controllers"] = True
                if "filter" in lname or "middleware" in lname:
                    out[layer]["Filters"] = True
                if lname.endswith("viewmodel") or lname.endswith("vm"):
                    out[layer]["ViewModels"] = True
                if lname.endswith("command") or lname.endswith("commandhandler"):
                    out[layer]["Commands"] = True
                if lname.endswith("query") or lname.endswith("queryhandler"):
                    out[layer]["Queries"] = True
                if lname.endswith("service") and layer == "Application":
                    out[layer]["Services"] = True
                if lname.endswith("service") and layer == "Domain":
                    out[layer]["DomainServices"] = True
                if lname.endswith("dto") or lname.endswith("response") or lname.endswith("request"):
                    if layer == "Application":
                        out[layer]["DTOs"] = True
                if getattr(s, "is_repository", False) or lname.endswith("repository"):
                    if (getattr(s, "kind", "") or "").lower() == "interface":
                        out.setdefault("Application", {})["Interfaces"] = True
                    else:
                        out.setdefault("Infrastructure", {})["Persistence"] = True
                if role == "valueobject" or lname.endswith("vo"):
                    out[layer]["ValueObjects"] = True
                if role == "aggregateroot" or role == "entity":
                    out[layer]["Entities"] = True
                if getattr(s, "is_domain_event", False) or "event" in lname and layer == "Domain":
                    out[layer]["DomainEvents"] = True
                if lname.endswith("exception"):
                    out[layer]["Exceptions"] = True
                if "dbcontext" in lname or "efcontext" in lname:
                    out.setdefault("Infrastructure", {})["Persistence"] = True
                if "identity" in lname or "jwt" in lname or "auth" in lname:
                    out.setdefault("Infrastructure", {})["Identity"] = True
                if "client" in lname and layer == "Infrastructure":
                    out[layer]["ExternalApis"] = True
        # Worker-layer artifacts come from consumers/schedulers
        if report.consumers:
            out.setdefault("Worker", {})["Consumers"] = True
        if report.schedulers:
            out.setdefault("Worker", {})["Schedulers"] = True
        # Messaging in infra if we found any async integrations
        for ig in (report.integrations or []):
            t = (getattr(ig, "type", "") or "").lower()
            if t in {"rabbitmq", "kafka", "azure-servicebus"}:
                out.setdefault("Infrastructure", {})["Messaging"] = True
        return out

    # Display labels for artifact nodes + fallback ordering
    _LAYER_ARTIFACT_DISPLAY = {
        "Presentation": [
            ("Controllers", "Controllers / Endpoints"),
            ("ViewModels", "ViewModels"),
            ("Filters", "Action Filters / Middlewares"),
        ],
        "Application": [
            ("Commands", "Commands (CQRS)"),
            ("Queries", "Queries (CQRS)"),
            ("Services", "Application Services"),
            ("Interfaces", "Repository Interfaces"),
            ("DTOs", "DTOs"),
        ],
        "Domain": [
            ("Entities", "Domain Entities / Aggregates"),
            ("ValueObjects", "Value Objects"),
            ("DomainServices", "Domain Services"),
            ("DomainEvents", "Domain Events"),
            ("Exceptions", "Domain Exceptions"),
        ],
        "Infrastructure": [
            ("Persistence", "Persistence / EF Core DbContext"),
            ("Identity", "Identity / JWT Auth"),
            ("Messaging", "Messaging / MassTransit"),
            ("ExternalApis", "External APIs / Logging"),
        ],
        "Worker": [
            ("Consumers", "Message Consumers"),
            ("Schedulers", "Schedulers / Background Jobs"),
        ],
    }

    _LAYER_SUBTITLE = {
        "Presentation": ".NET Web API / Angular",
        "Application": "Core / Use Cases",
        "Domain": "Core / Entities",
        "Infrastructure": "External Concerns",
        "Worker": "Background / Message Handlers",
    }

    def _arch_5_clean_architecture(self, report: CrawlReport) -> str:
        """5. Clean Architecture Diagram — layer subgraphs with artifact nodes.

        Dependency arrows all point inward toward the Domain core,
        matching the canonical Clean Architecture rule.
        """
        lines = ["## 5. Clean Architecture Diagram", ""]
        lines.append(
            "The solution follows the **Clean Architecture** style: the "
            "Domain layer sits at the core with no outward dependencies; "
            "all other layers depend inward. The diagram below shows the "
            "kinds of artifacts discovered in each layer and the allowed "
            "dependency directions — all arrows point toward the Domain core."
        )
        lines.append("")

        # Project → layer mapping (still useful as a separate table)
        layered: Dict[str, List[str]] = defaultdict(list)
        for p in report.projects:
            layered[p.layer or "Unknown"].append(p.name)
        if not layered:
            lines.append("_No project layer information available._")
            return "\n".join(lines)

        # Detect which artifact kinds exist per layer
        artifacts = self._classify_layer_artifacts(report)

        # Build mermaid graph
        lines.append("```mermaid")
        lines.append("graph TD")

        layer_ids: Dict[str, str] = {}

        def _emit_layer(layer_key: str) -> str:
            projects_here = layered.get(layer_key, [])
            if not projects_here and not artifacts.get(layer_key):
                return ""
            sg_id = re.sub(r"[^A-Za-z0-9_]", "_", layer_key) + "_L"
            subtitle = self._LAYER_SUBTITLE.get(layer_key, "")
            label = f"{layer_key} Layer"
            if subtitle:
                label += f" ({subtitle})"
            lines.append(f'  subgraph {sg_id} ["{label}"]')
            # Emit artifact nodes for this layer
            emitted_any = False
            for key, display in self._LAYER_ARTIFACT_DISPLAY.get(layer_key, []):
                if artifacts.get(layer_key, {}).get(key):
                    node_id = f"{sg_id}_{key}"
                    lines.append(f'    {node_id}["{display}"]')
                    emitted_any = True
            # If no typed artifacts were detected, fall back to project names
            if not emitted_any:
                for n in sorted(projects_here):
                    safe = re.sub(r"[^A-Za-z0-9_]", "_", n)
                    lines.append(f'    {sg_id}_{safe}["{n}"]')
            lines.append("  end")
            return sg_id

        pres_id = _emit_layer("Presentation")
        app_id = _emit_layer("Application")
        dom_id = _emit_layer("Domain")
        infra_id = _emit_layer("Infrastructure")
        worker_id = _emit_layer("Worker")

        # Dependency arrows — all point inward toward Domain
        if pres_id and app_id:
            lines.append(f"  {pres_id} --> {app_id}")
        if app_id and dom_id:
            lines.append(f"  {app_id} --> {dom_id}")
        if infra_id and app_id:
            lines.append(f"  {infra_id} --> {app_id}")
        if infra_id and dom_id:
            lines.append(f"  {infra_id} --> {dom_id}")
        if worker_id and app_id:
            lines.append(f"  {worker_id} --> {app_id}")
        lines.append("")
        lines.append(
            "  %% All arrows point inward toward the Domain core "
            "(Clean Architecture dependency rule)"
        )
        lines.append("```")
        lines.append("")

        # Narrative list of what was actually found per layer
        lines.append("### Artifacts Discovered per Layer")
        lines.append("")
        for layer_key in ["Presentation", "Application", "Domain",
                          "Infrastructure", "Worker"]:
            found = [
                display
                for key, display in self._LAYER_ARTIFACT_DISPLAY.get(layer_key, [])
                if artifacts.get(layer_key, {}).get(key)
            ]
            if not found and not layered.get(layer_key):
                continue
            lines.append(f"- **{layer_key}**: "
                         + (", ".join(found) if found else "_no typed artifacts detected_"))
        lines.append("")

        # Keep the project → layer assignment table for traceability
        order = ["Domain", "Application", "Infrastructure", "Presentation",
                 "Worker", "Shared", "Tests", "Unknown"]
        ordered_layers = sorted(
            layered.items(),
            key=lambda kv: order.index(kv[0]) if kv[0] in order else 99,
        )
        lines.append("### Project → Layer Assignment")
        lines.append("")
        lines.append("| Layer | Projects |")
        lines.append("|-------|----------|")
        for layer, names in ordered_layers:
            lines.append(f"| {layer} | {', '.join(sorted(names))} |")
        return "\n".join(lines)

    def _arch_6_sequence_diagrams(self, report: CrawlReport) -> str:
        """6. Sequence Diagram (Controller → Read Model)."""
        lines = ["## 6. Sequence Diagram (Controller → Read Model)", ""]
        endpoints = report.endpoints or []
        if not endpoints:
            lines.append("_No HTTP endpoints discovered to trace._")
            return "\n".join(lines)

        # Pick up to 3 representative endpoints (prefer GET — read-side flows)
        gets = [e for e in endpoints if e.method.upper() == "GET"]
        sample = (gets or endpoints)[:3]

        for ep in sample:
            ctrl = (ep.controller or "Controller").split(".")[-1]
            req = (ep.request_model or "").split(".")[-1] or "Request"
            resp = (ep.response_model or "").split(".")[-1] or "ReadModel"
            lines.append(f"### {ep.method} {ep.route}")
            lines.append("")
            lines.append(
                f"Handled by **`{ctrl}`**, this endpoint takes a `{req}` "
                f"and returns a `{resp}`. The request flows from the "
                f"presentation layer through the application layer down to "
                f"the domain and repository, reading from the database on "
                f"the way back out."
            )
            lines.append("")
            ep_file = getattr(ep, "file", "") or ""
            snippet = self._read_code_snippet(ep_file) if ep_file else ""
            if snippet:
                rel = ep_file.replace("\\", "/").split("/")[-1]
                lines.append(f"_Controller source — `{rel}`:_")
                lines.append("```csharp")
                lines.append(snippet)
                lines.append("```")
                lines.append("")
            lines.append("```mermaid")
            lines.append("sequenceDiagram")
            lines.append("  participant Client")
            lines.append(f"  participant {ctrl}")
            lines.append("  participant Application")
            lines.append("  participant Domain")
            lines.append("  participant Repository")
            lines.append("  participant Database")
            lines.append(f"  Client->>{ctrl}: {ep.method} {ep.route} ({req})")
            lines.append(f"  {ctrl}->>Application: Handle({req})")
            lines.append("  Application->>Domain: invoke business rule")
            lines.append("  Application->>Repository: query")
            lines.append("  Repository->>Database: SELECT")
            lines.append("  Database-->>Repository: rows")
            lines.append(f"  Repository-->>Application: {resp}")
            lines.append(f"  Application-->>{ctrl}: {resp}")
            lines.append(f"  {ctrl}-->>Client: 200 OK ({resp})")
            lines.append("```")
            lines.append("")
        return "\n".join(lines)

    def _render_integration_block(self, ig) -> List[str]:
        """Per-integration narrative + code snippet."""
        out: List[str] = []
        src = getattr(ig, "source_service", "") or "—"
        tgt = getattr(ig, "target", "") or "—"
        transport = getattr(ig, "type", "") or "—"
        contract = getattr(ig, "contract", "") or ""
        out.append(f"#### `{src}` → `{tgt}` ({transport})")
        if contract:
            out.append(f"**Contract:** `{contract}`")
            out.append("")
        out.append(
            f"`{src}` communicates with `{tgt}` over `{transport}`"
            + (f", exchanging `{contract}`." if contract else ".")
        )
        out.append("")
        f = getattr(ig, "file", "") or ""
        snippet = self._read_code_snippet(f) if f else ""
        if snippet:
            rel = f.replace("\\", "/").split("/")[-1]
            out.append(f"_Source — `{rel}`:_")
            out.append("```csharp")
            out.append(snippet)
            out.append("```")
            out.append("")
        return out

    def _arch_7_event_stream(self, report: CrawlReport) -> str:
        """7. Event Stream — synchronous (HTTP/gRPC) and asynchronous (queues)."""
        lines = ["## 7. Event Stream", ""]
        lines.append(
            "Bounded contexts interact via two complementary styles: "
            "**synchronous** calls (HTTP / gRPC) for request/response where "
            "the caller needs an immediate answer, and **asynchronous** "
            "messaging (queues / topics) for fire-and-forget events where "
            "loose coupling and temporal decoupling matter more than latency."
        )
        lines.append("")
        sync_transports = {"http", "grpc"}
        async_transports = {"rabbitmq", "kafka", "azure-servicebus", "sqs", "sns"}

        sync_items = []
        async_items = []
        for ig in (report.integrations or []):
            t = (ig.type or "").lower()
            if t in sync_transports:
                sync_items.append(ig)
            elif t in async_transports:
                async_items.append(ig)

        lines.append("### Synchronous (Request/Response)")
        lines.append("")
        if sync_items:
            lines.append("| Source | Target | Transport | Contract |")
            lines.append("|--------|--------|-----------|----------|")
            for ig in sync_items:
                lines.append(
                    f"| {ig.source_service or '—'} | {ig.target or '—'} | "
                    f"{ig.type} | {ig.contract or '—'} |"
                )
            lines.append("")
            for ig in sync_items[:8]:
                lines.extend(self._render_integration_block(ig))
        else:
            lines.append("_No synchronous integrations discovered._")
        lines.append("")

        lines.append("### Asynchronous (Event-Driven)")
        lines.append("")
        consumers = report.consumers or []
        if async_items or consumers:
            lines.append("| Source / Producer | Target / Consumer | Transport | Message |")
            lines.append("|-------------------|-------------------|-----------|---------|")
            for ig in async_items:
                lines.append(
                    f"| {ig.source_service or '—'} | {ig.target or '—'} | "
                    f"{ig.type} | {ig.contract or '—'} |"
                )
            for c in consumers:
                short_msg = (c.message_type or "").split(".")[-1] or "—"
                short_consumer = (c.consumer_class or "").split(".")[-1] or "—"
                lines.append(
                    f"| (publisher) | {short_consumer} | rabbitmq ({c.queue or 'default'}) "
                    f"| {short_msg} |"
                )
            lines.append("")
            for ig in async_items[:8]:
                lines.extend(self._render_integration_block(ig))

            if consumers:
                lines.append("#### Async Consumers (Detail)")
                lines.append("")
                lines.append(
                    "Consumers subscribe to queues and process messages "
                    "published by other services. See section 4 for the "
                    "full event catalogue with code snippets."
                )
                lines.append("")
        else:
            lines.append("_No asynchronous events / consumers discovered._")
        return "\n".join(lines)

    def _arch_8_glossary(self, report: CrawlReport) -> str:
        """8. Glossary (Ubiquitous Language) — terms collected from domain artifacts."""
        lines = ["## 8. Glossary (Ubiquitous Language — CoreTax)", ""]
        terms: Dict[str, str] = {}

        # Pull domain names + descriptions
        for d in (report.business_domains or []):
            name = getattr(d, "name", "")
            desc = getattr(d, "description", "") or ""
            if name and name not in terms:
                terms[name] = desc or f"Bounded context covering {name}-related capabilities."

        # Pull aggregate / entity names from code symbols
        for p in report.projects:
            for sym in (p.code_symbols or []):
                kind = (getattr(sym, "kind", "") or "").lower()
                role = (getattr(sym, "ddd_role", "") or "").lower()
                name = getattr(sym, "name", "") or ""
                if not name or name in terms:
                    continue
                if role in ("aggregateroot", "entity", "valueobject"):
                    terms[name] = f"{role.title()} in `{p.name}`."
                elif kind in ("class", "record") and len(terms) < 60:
                    terms[name] = f"Type defined in `{p.name}`."

        # Pull message types as domain events
        for c in (report.consumers or []):
            short = (c.message_type or "").split(".")[-1]
            if short and short not in terms:
                terms[short] = "Domain event / integration message."

        if not terms:
            lines.append("_No domain vocabulary discovered._")
            return "\n".join(lines)

        lines.append("| Term | Definition |")
        lines.append("|------|------------|")
        for term in sorted(terms.keys(), key=str.lower):
            definition = terms[term].replace("|", "\\|")
            lines.append(f"| **{term}** | {definition} |")
        return "\n".join(lines)
