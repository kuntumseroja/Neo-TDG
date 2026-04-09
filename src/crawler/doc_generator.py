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
            self._section_business_domains(report),
            self._section_domain_contracts(report),
            self._section_sequence_flows(report),
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
            self._section_ui_components(report),
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
            pdf.multi_cell(w, h, self._ascii_safe(text), new_x=XPos.LMARGIN, new_y=YPos.NEXT, **kwargs)

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
        return (
            f"# {sln_name} - Technical Documentation\n\n"
            f"> Auto-generated by Lumen.AI Solution Crawler\n"
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
            if comp_id not in seen_nodes:
                diag_lines.append(f'    {comp_id}["{c.name}"]')
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
                        diag_lines.append(f'    {ctrl_id}(["{matched_ctrl}"])')
                        seen_nodes.add(ctrl_id)
                    edges.append(f"    {comp_id} -->|{self._ascii_safe(call)[:30]}| {ctrl_id}")
                else:
                    # Unmatched call: render as a leaf node so the user
                    # still sees the outbound dependency.
                    leaf_id = self._mermaid_id(call_norm)[:20] or "ext"
                    leaf_id = f"ext_{leaf_id}"
                    if leaf_id not in seen_nodes:
                        diag_lines.append(f'    {leaf_id}[/"{self._ascii_safe(call)[:40]}"/]')
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
