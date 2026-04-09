"""Documentation-to-knowledge ingestion pipeline."""

import hashlib
import logging
from pathlib import Path
from typing import List, Optional

from src.knowledge.vector_store import VectorKnowledgeStore
from src.models.crawler import CrawlReport

logger = logging.getLogger(__name__)


class DocumentIngestionPipeline:
    """
    Bridges TechDocGen output into the Vector Knowledge Store.

    Ingests:
    - Generated markdown documentation
    - Service catalog data (as endpoint chunks)
    - DDD documentation (as domain_model chunks)
    - Dependency maps (as dependency chunks)
    - Crawl reports (as structured chunks)
    """

    def __init__(self, store: VectorKnowledgeStore, config: dict = None):
        self.store = store
        self.config = config or {}

    def ingest_markdown_file(
        self,
        file_path: str,
        metadata: dict = None,
        doc_id: str = None,
    ) -> int:
        """Read a markdown file and ingest into vector store."""
        path = Path(file_path)
        if not path.exists():
            logger.warning(f"File not found: {file_path}")
            return 0

        content = path.read_text(encoding="utf-8", errors="ignore")
        if not content.strip():
            return 0

        base_metadata = {
            "source_file": str(path.name),
            **(metadata or {}),
        }

        if not doc_id:
            doc_id = hashlib.md5(str(path).encode()).hexdigest()

        return self.store.ingest_document(content, base_metadata, doc_id)

    def ingest_markdown_directory(
        self,
        dir_path: str,
        glob_pattern: str = "**/*.md",
        metadata: dict = None,
        progress_callback=None,
    ) -> dict:
        """Recursively ingest all markdown files in a directory."""
        directory = Path(dir_path)
        if not directory.exists():
            logger.warning(f"Directory not found: {dir_path}")
            return {"total_chunks": 0, "files_processed": 0}

        files = sorted(directory.glob(glob_pattern))
        total_chunks = 0
        files_processed = 0

        for i, file_path in enumerate(files):
            try:
                doc_id = hashlib.md5(str(file_path).encode()).hexdigest()
                file_meta = {
                    "source_file": str(file_path.name),
                    **(metadata or {}),
                }
                # Try to infer service name from path
                service_name = self._infer_service_name(file_path)
                if service_name:
                    file_meta["service_name"] = service_name

                chunks = self.ingest_markdown_file(
                    str(file_path), file_meta, doc_id
                )
                total_chunks += chunks
                files_processed += 1
                logger.info(f"Ingested {file_path.name}: {chunks} chunks")

                if progress_callback:
                    progress_callback(i + 1, len(files), str(file_path.name))
            except Exception as e:
                logger.error(f"Failed to ingest {file_path}: {e}")

        return {
            "total_chunks": total_chunks,
            "files_processed": files_processed,
            "total_files": len(files),
        }

    def ingest_service_catalog(self, catalog: dict, service_name: str = "") -> int:
        """Convert service catalog dict to chunks and ingest."""
        chunks_created = 0

        # Ingest endpoints
        endpoints = catalog.get("endpoints", [])
        if endpoints:
            content_parts = ["## API Endpoints\n"]
            for ep in endpoints:
                verbs = ", ".join(ep.get("http_verbs", []))
                route = ep.get("route", "")
                controller = ep.get("controller", "")
                method = ep.get("method", "")
                content_parts.append(
                    f"- **{verbs} {route}** — `{controller}.{method}()`"
                )
            content = "\n".join(content_parts)
            doc_id = f"catalog_endpoints_{service_name}"
            chunks_created += self.store.ingest_document(
                content,
                {"service_name": service_name, "chunk_type": "endpoint", "source_file": "service_catalog"},
                doc_id,
            )

        # Ingest endpoint flows
        flows = catalog.get("endpoint_flows", [])
        if flows:
            content_parts = ["## Endpoint Flows\n"]
            for flow in flows:
                verbs = ", ".join(flow.get("http_verbs", []))
                route = flow.get("route", "")
                steps = flow.get("steps", [])
                content_parts.append(f"### {verbs} {route}")
                for step in steps:
                    content_parts.append(f"  - {step}")
                content_parts.append("")
            content = "\n".join(content_parts)
            doc_id = f"catalog_flows_{service_name}"
            chunks_created += self.store.ingest_document(
                content,
                {"service_name": service_name, "chunk_type": "flow", "source_file": "service_catalog"},
                doc_id,
            )

        # Ingest API spec
        api_spec = catalog.get("api_spec", [])
        if api_spec:
            content_parts = ["## API Specification\n"]
            content_parts.append("| Controller | Method | HTTP | Route | Components | Steps |")
            content_parts.append("|---|---|---|---|---|---|")
            for spec in api_spec:
                verbs = ", ".join(spec.get("http_verbs", []))
                components = ", ".join(spec.get("components", []))
                steps = " → ".join(spec.get("steps", []))
                content_parts.append(
                    f"| {spec.get('controller', '')} | {spec.get('method', '')} | "
                    f"{verbs} | {spec.get('route', '')} | {components} | {steps} |"
                )
            content = "\n".join(content_parts)
            doc_id = f"catalog_apispec_{service_name}"
            chunks_created += self.store.ingest_document(
                content,
                {"service_name": service_name, "chunk_type": "endpoint", "source_file": "api_spec"},
                doc_id,
            )

        return chunks_created

    def ingest_ddd_documentation(self, ddd_docs: dict, service_name: str = "") -> int:
        """Convert DDD documentation dict to chunks and ingest."""
        chunks_created = 0

        for key in ["bounded_contexts", "domain_event_catalogue", "ubiquitous_language"]:
            content = ddd_docs.get(key, "")
            if content and isinstance(content, str) and len(content.strip()) > 10:
                doc_id = f"ddd_{key}_{service_name}"
                chunks_created += self.store.ingest_document(
                    content,
                    {"service_name": service_name, "chunk_type": "domain_model", "source_file": f"ddd_{key}"},
                    doc_id,
                )

        # Ingest mermaid diagrams as flow chunks
        for key in ["context_map_mermaid", "domain_model_mermaid", "solution_structure_mermaid"]:
            diagram = ddd_docs.get(key, "")
            if diagram and isinstance(diagram, str) and len(diagram.strip()) > 10:
                doc_id = f"ddd_{key}_{service_name}"
                chunks_created += self.store.ingest_document(
                    f"## {key.replace('_', ' ').title()}\n\n```mermaid\n{diagram}\n```",
                    {"service_name": service_name, "chunk_type": "flow", "source_file": f"ddd_{key}"},
                    doc_id,
                )

        return chunks_created

    def ingest_dependency_map(self, dep_map: dict, service_name: str = "") -> int:
        """Convert dependency map to chunks and ingest."""
        chunks_created = 0

        # Ingest nodes
        nodes = dep_map.get("nodes", [])
        if nodes:
            content_parts = ["## Project Dependencies\n"]
            for node in nodes:
                content_parts.append(
                    f"- **{node.get('id', '')}** ({node.get('language', '')}): "
                    f"{node.get('dependency_count', 0)} deps, {node.get('dependent_count', 0)} dependents"
                )
            content = "\n".join(content_parts)
            doc_id = f"depmap_nodes_{service_name}"
            chunks_created += self.store.ingest_document(
                content,
                {"service_name": service_name, "chunk_type": "dependency", "source_file": "dependency_map"},
                doc_id,
            )

        # Ingest external dependencies
        ext_deps = dep_map.get("external_dependencies", {})
        if ext_deps:
            content_parts = ["## External Dependencies\n"]
            for file_path, deps in ext_deps.items():
                if deps:
                    content_parts.append(f"### {file_path}")
                    for dep in deps:
                        content_parts.append(f"  - {dep}")
            content = "\n".join(content_parts)
            doc_id = f"depmap_external_{service_name}"
            chunks_created += self.store.ingest_document(
                content,
                {"service_name": service_name, "chunk_type": "dependency", "source_file": "external_deps"},
                doc_id,
            )

        return chunks_created

    def ingest_crawl_report(self, report: CrawlReport) -> int:
        """Ingest a CrawlReport as structured chunks."""
        chunks_created = 0
        svc = report.solution

        # Projects
        if report.projects:
            content_parts = [f"## Solution: {svc}\n### Projects\n"]
            for p in report.projects:
                refs = ", ".join(p.references) if p.references else "none"
                content_parts.append(
                    f"- **{p.name}** [{p.layer}] ({p.framework}) — refs: {refs}"
                )
            doc_id = f"crawl_projects_{svc}"
            chunks_created += self.store.ingest_document(
                "\n".join(content_parts),
                {"service_name": svc, "chunk_type": "architecture", "source_file": "crawl_report"},
                doc_id,
            )

        # Endpoints
        if report.endpoints:
            content_parts = ["## Discovered Endpoints\n"]
            for ep in report.endpoints:
                auth = " [Auth]" if ep.auth_required else ""
                content_parts.append(
                    f"- **{ep.method} {ep.route}**{auth} — `{ep.controller}` ({ep.file}:{ep.line})"
                )
            doc_id = f"crawl_endpoints_{svc}"
            chunks_created += self.store.ingest_document(
                "\n".join(content_parts),
                {"service_name": svc, "chunk_type": "endpoint", "source_file": "crawl_report"},
                doc_id,
            )

        # Consumers
        if report.consumers:
            content_parts = ["## Message Consumers\n"]
            for c in report.consumers:
                content_parts.append(
                    f"- **{c.consumer_class}** consumes `{c.message_type}` (queue: {c.queue})"
                )
            doc_id = f"crawl_consumers_{svc}"
            chunks_created += self.store.ingest_document(
                "\n".join(content_parts),
                {"service_name": svc, "chunk_type": "component", "source_file": "crawl_report"},
                doc_id,
            )

        # Schedulers
        if report.schedulers:
            content_parts = ["## Scheduled Jobs\n"]
            for s in report.schedulers:
                content_parts.append(
                    f"- **{s.job_name}** — cron: `{s.cron_expression}` — handler: `{s.handler_class}`"
                )
            doc_id = f"crawl_schedulers_{svc}"
            chunks_created += self.store.ingest_document(
                "\n".join(content_parts),
                {"service_name": svc, "chunk_type": "component", "source_file": "crawl_report"},
                doc_id,
            )

        # Integrations
        if report.integrations:
            content_parts = ["## Integration Points\n"]
            for ip in report.integrations:
                content_parts.append(
                    f"- [{ip.type}] {ip.source_service} → {ip.target} ({ip.contract})"
                )
            doc_id = f"crawl_integrations_{svc}"
            chunks_created += self.store.ingest_document(
                "\n".join(content_parts),
                {"service_name": svc, "chunk_type": "dependency", "source_file": "crawl_report"},
                doc_id,
            )

        # Data models
        if report.data_models:
            content_parts = ["## Data Models (EF Core)\n"]
            for dm in report.data_models:
                props = ", ".join(dm.properties[:10]) if dm.properties else ""
                content_parts.append(
                    f"- **{dm.name}** (DbContext: {dm.db_context}) — {props}"
                )
            doc_id = f"crawl_datamodels_{svc}"
            chunks_created += self.store.ingest_document(
                "\n".join(content_parts),
                {"service_name": svc, "chunk_type": "domain_model", "source_file": "crawl_report"},
                doc_id,
            )

        # Deep-analysis chunks (only present when crawler.deep_analysis.enabled)
        chunks_created += self.ingest_configurations(report)
        chunks_created += self.ingest_di_graph(report)
        chunks_created += self.ingest_business_domains(report)

        logger.info(f"Ingested crawl report for '{svc}': {chunks_created} chunks")
        return chunks_created

    # ── Deep-analysis ingestion ──────────────────────────────────────────

    def ingest_configurations(self, report: CrawlReport) -> int:
        """Ingest ConfigurationNode entries grouped by project + environment."""
        chunks = 0
        svc = report.solution
        for project in report.projects:
            if not project.configurations:
                continue
            # Group by environment for clearer chunks
            by_env: dict = {}
            for cfg in project.configurations:
                by_env.setdefault(cfg.environment or "default", []).append(cfg)

            for env, items in by_env.items():
                lines = [f"## Configuration — {project.name} ({env})\n"]
                for cfg in items:
                    env_var = f" → ${{{cfg.references_env_var}}}" if cfg.references_env_var else ""
                    lines.append(
                        f"- `{cfg.key}` *[{cfg.kind}]* = `{cfg.value}`{env_var}"
                    )
                doc_id = f"crawl_config_{svc}_{project.name}_{env}"
                chunks += self.store.ingest_document(
                    "\n".join(lines),
                    {
                        "service_name": svc,
                        "project_name": project.name,
                        "environment": env,
                        "chunk_type": "configuration",
                        "source_file": "config_analyzer",
                    },
                    doc_id,
                )
        return chunks

    def ingest_di_graph(self, report: CrawlReport) -> int:
        """Ingest DI registrations as one chunk per project."""
        chunks = 0
        svc = report.solution
        for project in report.projects:
            if not project.di_registrations:
                continue
            lines = [f"## Dependency Injection — {project.name}\n"]
            for reg in project.di_registrations:
                impl = f" → `{reg.implementation}`" if reg.implementation else ""
                client = f' (named "{reg.named_client}")' if reg.named_client else ""
                lines.append(
                    f"- `{reg.method}` `{reg.service_type}`{impl}{client} "
                    f"({reg.source_file}:{reg.line})"
                )
            doc_id = f"crawl_di_{svc}_{project.name}"
            chunks += self.store.ingest_document(
                "\n".join(lines),
                {
                    "service_name": svc,
                    "project_name": project.name,
                    "chunk_type": "di_registration",
                    "source_file": "dependency_extractor",
                },
                doc_id,
            )
        return chunks

    def ingest_business_domains(self, report: CrawlReport) -> int:
        """Ingest business domains and cross-domain contracts."""
        chunks = 0
        svc = report.solution

        for domain in report.business_domains:
            lines = [
                f"## Business Domain — {domain.name}\n",
                f"**Projects:** {', '.join(domain.projects) or '—'}",
                f"**Namespaces:** {', '.join(domain.namespaces) or '—'}",
                f"**Aggregates:** {', '.join(domain.aggregates) or '—'}",
                f"**Domain Events:** {', '.join(domain.domain_events) or '—'}",
                f"**Endpoints:** {len(domain.endpoints)}",
                f"**Inbound contracts from:** {', '.join(domain.inbound_contracts) or '—'}",
                f"**Outbound contracts to:** {', '.join(domain.outbound_contracts) or '—'}",
            ]
            if domain.endpoints:
                lines.append("\n### Endpoints")
                for ep in domain.endpoints[:50]:
                    lines.append(f"- `{ep}`")
            doc_id = f"crawl_domain_{svc}_{domain.name}"
            chunks += self.store.ingest_document(
                "\n".join(lines),
                {
                    "service_name": svc,
                    "domain_name": domain.name,
                    "chunk_type": "business_domain",
                    "source_file": "domain_mapper",
                },
                doc_id,
            )

        if report.domain_contracts:
            lines = ["## Domain Contracts\n"]
            for c in report.domain_contracts:
                url = f" @ {c.config_url}" if c.config_url else ""
                lines.append(
                    f"- [{c.transport}] **{c.source_domain or c.source_project}** "
                    f"→ **{c.target_domain or c.target_service}** "
                    f"(`{c.interface}`){url}"
                )
            doc_id = f"crawl_contracts_{svc}"
            chunks += self.store.ingest_document(
                "\n".join(lines),
                {
                    "service_name": svc,
                    "chunk_type": "domain_contract",
                    "source_file": "domain_mapper",
                },
                doc_id,
            )
        return chunks

    def full_rebuild(self, docs_dir: str, metadata: dict = None) -> dict:
        """Drop all data and re-ingest everything from a directory."""
        self.store.rebuild_index()
        return self.ingest_markdown_directory(docs_dir, metadata=metadata)

    @staticmethod
    def _infer_service_name(file_path: Path) -> str:
        """Try to infer a service name from a file path."""
        parts = file_path.parts
        # Look for common service name patterns
        for part in reversed(parts):
            if part.endswith("_technical_docs") or part.endswith("_docs"):
                return part.replace("_technical_docs", "").replace("_docs", "")
        # Use parent directory name
        if len(parts) >= 2:
            return parts[-2]
        return ""
