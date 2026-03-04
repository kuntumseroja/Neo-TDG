"""
Document generator for crawl reports.

Generates comprehensive Markdown and PDF documentation from CrawlReport data.
"""

import re
import logging
from datetime import datetime
from collections import defaultdict
from typing import List

from src.models.crawler import CrawlReport

logger = logging.getLogger(__name__)


class CrawlDocGenerator:
    """Generate technical documentation from a CrawlReport."""

    def generate_markdown(self, report: CrawlReport) -> str:
        """Generate comprehensive markdown documentation from crawl results."""
        sections = [
            self._section_title(report),
            self._section_overview(report),
            self._section_architecture_diagram(report),
            self._section_projects(report),
            self._section_endpoints(report),
            self._section_consumers(report),
            self._section_schedulers(report),
            self._section_integrations(report),
            self._section_data_models(report),
            self._section_dependency_graph(report),
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
            pdf.multi_cell(w, h, text, new_x=XPos.LMARGIN, new_y=YPos.NEXT, **kwargs)

        lines = markdown_content.split("\n")
        in_code_block = False
        table_rows = []

        for line in lines:
            # Code block toggle
            if line.strip().startswith("```"):
                if in_code_block:
                    in_code_block = False
                    pdf.ln(2)
                else:
                    in_code_block = True
                    pdf.set_font("Courier", size=7)
                    pdf.set_fill_color(240, 240, 240)
                continue

            if in_code_block:
                pdf.set_font("Courier", size=7)
                pdf.set_fill_color(240, 240, 240)
                text = line.rstrip()
                if len(text) > 120:
                    text = text[:120] + "..."
                pdf.cell(0, 4, text, new_x=XPos.LMARGIN, new_y=YPos.NEXT, fill=True)
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

    def _clean_md(self, text: str) -> str:
        """Remove markdown formatting from text."""
        text = re.sub(r"\*\*(.+?)\*\*", r"\1", text)
        text = re.sub(r"\*(.+?)\*", r"\1", text)
        text = re.sub(r"`(.+?)`", r"\1", text)
        text = re.sub(r"\[(.+?)\]\(.+?\)", r"\1", text)
        return text

    # ── Markdown Section Builders ──────────────────────────────────────

    def _section_title(self, report: CrawlReport) -> str:
        sln_name = report.solution.replace("\\", "/").split("/")[-1]
        return (
            f"# {sln_name} - Technical Documentation\n\n"
            f"> Auto-generated by Neo-TDG Solution Crawler\n"
            f"> Crawled at: {report.crawled_at.strftime('%Y-%m-%d %H:%M:%S')}"
        )

    def _section_overview(self, report: CrawlReport) -> str:
        layers = defaultdict(int)
        frameworks = set()
        for p in report.projects:
            layers[p.layer or "Unknown"] += 1
            if p.framework:
                frameworks.add(p.framework)

        layer_rows = "\n".join(f"| {layer} | {count} |" for layer, count in sorted(layers.items()))

        return (
            f"## Solution Overview\n\n"
            f"| Metric | Value |\n"
            f"|--------|-------|\n"
            f"| Total Projects | {len(report.projects)} |\n"
            f"| API Endpoints | {len(report.endpoints)} |\n"
            f"| Message Consumers | {len(report.consumers)} |\n"
            f"| Scheduled Jobs | {len(report.schedulers)} |\n"
            f"| External Integrations | {len(report.integrations)} |\n"
            f"| Data Models | {len(report.data_models)} |\n"
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
            safe_layer = layer.replace(" ", "_")
            lines.append(f"    subgraph {safe_layer}[\"{layer} Layer\"]")
            for proj in projects:
                safe_name = proj.replace(".", "_").replace("-", "_")
                lines.append(f"        {safe_name}[\"{proj}\"]")
            lines.append("    end")

        # Add edges from dependency graph
        edges = report.dependency_graph.get("edges", [])
        for edge in edges:
            src = str(edge.get("from", "")).replace(".", "_").replace("-", "_")
            tgt = str(edge.get("to", "")).replace(".", "_").replace("-", "_")
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

    def _section_dependency_graph(self, report: CrawlReport) -> str:
        nodes = report.dependency_graph.get("nodes", [])
        edges = report.dependency_graph.get("edges", [])

        if not nodes and not edges:
            return ""

        lines = ["## Dependency Graph\n", "```mermaid", "graph LR"]

        for node in nodes:
            name = str(node).replace(".", "_").replace("-", "_")
            lines.append(f"    {name}[\"{node}\"]")

        for edge in edges:
            src = str(edge.get("from", "")).replace(".", "_").replace("-", "_")
            tgt = str(edge.get("to", "")).replace(".", "_").replace("-", "_")
            if src and tgt:
                lines.append(f"    {src} --> {tgt}")

        lines.append("```")
        return "\n".join(lines)
