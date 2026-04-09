"""Deep solution crawler for .sln/.csproj discovery."""

import re
import logging
from pathlib import Path
from typing import List, Dict, Optional
from datetime import datetime

from src.models.crawler import (
    CrawlReport, ProjectInfo, EndpointInfo, ConsumerInfo,
    SchedulerInfo, IntegrationPoint, DataModel, PackageRef,
)
from src.crawler.scheduler_discovery import discover_schedulers
from src.crawler.integration_discovery import discover_integrations
from src.crawler.config_analyzer import scan_project_configs
from src.crawler.dependency_extractor import scan_project_di
from src.crawler.code_analyzer import scan_project_symbols
from src.crawler.domain_mapper import build_domain_map

logger = logging.getLogger(__name__)

# Layer classification keywords
_LAYER_KEYWORDS = {
    "Domain": ["domain", "core", "model", "entity"],
    "Application": ["application", "command", "query", "handler", "usecase"],
    "Infrastructure": ["infrastructure", "persistence", "data", "repository", "migration"],
    "Presentation": ["presentation", "api", "web", "controller", "host"],
    "Tests": ["test", "tests", "spec", "specs", "unittest", "integrationtest"],
    "Shared": ["shared", "common", "contracts", "dto", "crosscutting"],
}

# Regex patterns for C# endpoint discovery
_CONTROLLER_PATTERN = re.compile(
    r"class\s+(\w+Controller)\s*(?::\s*[\w<>, ]+)?", re.MULTILINE
)
_HTTP_ATTR_PATTERN = re.compile(
    r'\[(Http(Get|Post|Put|Delete|Patch))(?:\("([^"]*?)"\))?\]', re.MULTILINE
)
_ROUTE_ATTR_PATTERN = re.compile(
    r'\[Route\("([^"]*?)"\)\]', re.MULTILINE
)
_AUTHORIZE_PATTERN = re.compile(r"\[Authorize", re.MULTILINE)
_CONSUMER_PATTERN = re.compile(
    r"class\s+(\w+)\s*:\s*(?:.*?)IConsumer<(\w+)>", re.MULTILINE
)
_DBCONTEXT_PATTERN = re.compile(
    r"class\s+(\w+)\s*:\s*(?:.*?)DbContext", re.MULTILINE
)
_DBSET_PATTERN = re.compile(
    r"DbSet<(\w+)>\s+(\w+)", re.MULTILINE
)
_SAGA_PATTERN = re.compile(
    r"class\s+(\w+)\s*:\s*.*?(?:MassTransitStateMachine|Saga)<(\w+)>", re.MULTILINE
)


class SolutionCrawler:
    """Deep crawl of .sln solutions to discover all components."""

    def __init__(self, config: dict = None):
        self.config = config or {}
        self._scan_depth = self.config.get("scan_depth", 10)
        deep = self.config.get("deep_analysis", {}) or {}
        self._deep_enabled = bool(deep.get("enabled", False))
        self._deep_hints = deep.get("domain_hints", {}) or {}

    def crawl(self, sln_path: str, progress_callback=None) -> CrawlReport:
        """
        Starting from .sln, discover all projects and their components.
        """
        sln_file = Path(sln_path)

        # If a directory is given, auto-discover .sln file inside it
        if sln_file.is_dir():
            sln_files = list(sln_file.glob("*.sln"))
            if not sln_files:
                raise FileNotFoundError(f"No .sln file found in directory: {sln_path}")
            sln_file = sln_files[0]
            logger.info(f"Auto-discovered solution: {sln_file.name}")

        if not sln_file.exists():
            raise FileNotFoundError(f"Solution file not found: {sln_path}")

        sln_dir = sln_file.parent
        sln_content = sln_file.read_text(encoding="utf-8", errors="ignore")

        # Parse .sln to discover projects
        project_entries = self._parse_sln(sln_content)
        logger.info(f"Found {len(project_entries)} projects in {sln_file.name}")

        report = CrawlReport(solution=sln_file.name)

        all_cs_files = []

        for i, entry in enumerate(project_entries):
            csproj_path = sln_dir / entry["path"]
            if not csproj_path.exists():
                continue

            project_info = self._crawl_project(csproj_path, entry["name"])

            # Deep analysis (opt-in via crawler.deep_analysis.enabled)
            if self._deep_enabled:
                project_dir_for_deep = csproj_path.parent
                try:
                    project_info.configurations = scan_project_configs(
                        project_dir_for_deep, project_name=entry["name"]
                    )
                    project_info.di_registrations = scan_project_di(
                        project_dir_for_deep, project_name=entry["name"]
                    )
                    project_info.code_symbols = scan_project_symbols(
                        project_dir_for_deep, project_name=entry["name"]
                    )
                except Exception as e:
                    logger.warning(
                        f"Deep analysis failed for {entry['name']}: {e}"
                    )

            report.projects.append(project_info)

            # Gather C# files from project directory
            project_dir = csproj_path.parent
            cs_files = self._collect_cs_files(project_dir)
            all_cs_files.extend(cs_files)

            if progress_callback:
                progress_callback(i + 1, len(project_entries), entry["name"])

        # Analyze all C# files for components
        for cs_file in all_cs_files:
            try:
                content = cs_file.read_text(encoding="utf-8", errors="ignore")
                self._extract_endpoints(content, str(cs_file), report)
                self._extract_consumers(content, str(cs_file), report)
                self._extract_data_models(content, str(cs_file), report)
            except Exception as e:
                logger.warning(f"Error analyzing {cs_file}: {e}")

        # Discover schedulers and integrations
        for cs_file in all_cs_files:
            try:
                content = cs_file.read_text(encoding="utf-8", errors="ignore")
                report.schedulers.extend(discover_schedulers(content, str(cs_file)))
                report.integrations.extend(discover_integrations(content, str(cs_file)))
            except Exception as e:
                logger.warning(f"Error in discovery for {cs_file}: {e}")

        # Build dependency graph
        report.dependency_graph = self._build_dependency_graph(report.projects)

        # Deep analysis: cluster projects/symbols into business domains and
        # derive cross-domain contracts.
        if self._deep_enabled:
            try:
                build_domain_map(report, hints=self._deep_hints)
            except Exception as e:
                logger.warning(f"Domain mapping failed: {e}")

        logger.info(
            f"Crawl complete: {len(report.projects)} projects, "
            f"{len(report.endpoints)} endpoints, {len(report.consumers)} consumers, "
            f"{len(report.schedulers)} schedulers, {len(report.integrations)} integrations"
            + (
                f", {len(report.business_domains)} domains, {len(report.domain_contracts)} contracts"
                if self._deep_enabled
                else ""
            )
        )
        return report

    def _parse_sln(self, sln_content: str) -> List[dict]:
        """Parse .sln file to extract project entries."""
        pattern = re.compile(
            r'Project\("\{[^}]+\}"\)\s*=\s*"([^"]+)"\s*,\s*"([^"]+)"',
            re.MULTILINE,
        )
        projects = []
        for match in pattern.finditer(sln_content):
            name = match.group(1)
            path = match.group(2).replace("\\", "/")
            if path.endswith(".csproj"):
                projects.append({"name": name, "path": path})
        return projects

    def _crawl_project(self, csproj_path: Path, name: str) -> ProjectInfo:
        """Crawl a single .csproj and extract metadata."""
        content = csproj_path.read_text(encoding="utf-8", errors="ignore")

        # Extract target framework
        fw_match = re.search(r"<TargetFramework>(.*?)</TargetFramework>", content)
        framework = fw_match.group(1) if fw_match else ""

        # Extract project references
        refs = re.findall(r'<ProjectReference\s+Include="([^"]+)"', content)
        ref_names = [Path(r.replace("\\", "/")).stem for r in refs]

        # Extract NuGet packages
        packages = []
        for pkg_match in re.finditer(
            r'<PackageReference\s+Include="([^"]+)"(?:\s+Version="([^"]*)")?',
            content,
        ):
            packages.append(PackageRef(name=pkg_match.group(1), version=pkg_match.group(2) or ""))

        # Classify layer
        layer = self._classify_layer(name)

        return ProjectInfo(
            name=name,
            path=str(csproj_path),
            layer=layer,
            framework=framework,
            references=ref_names,
            nuget_packages=packages,
        )

    def _classify_layer(self, project_name: str) -> str:
        """Classify a project into an architecture layer based on its name."""
        name_lower = project_name.lower()
        for layer, keywords in _LAYER_KEYWORDS.items():
            if any(kw in name_lower for kw in keywords):
                return layer
        return "Unknown"

    def _collect_cs_files(self, project_dir: Path) -> List[Path]:
        """Collect all .cs files in a project directory."""
        cs_files = []
        for f in project_dir.rglob("*.cs"):
            # Skip bin/obj/node_modules
            parts_lower = [p.lower() for p in f.parts]
            if any(skip in parts_lower for skip in ["bin", "obj", "node_modules", ".git"]):
                continue
            cs_files.append(f)
        return cs_files

    def _extract_endpoints(self, content: str, file_path: str, report: CrawlReport):
        """Extract HTTP endpoints from C# controllers."""
        # Find controller class
        ctrl_match = _CONTROLLER_PATTERN.search(content)
        if not ctrl_match:
            return

        controller = ctrl_match.group(1)

        # Find class-level route
        class_route = ""
        route_match = _ROUTE_ATTR_PATTERN.search(content[:content.find("class ")] if "class " in content else content)
        if route_match:
            class_route = route_match.group(1)

        has_auth = bool(_AUTHORIZE_PATTERN.search(content))

        # Find HTTP method attributes
        for match in _HTTP_ATTR_PATTERN.finditer(content):
            http_method = match.group(2).upper()
            action_route = match.group(3) or ""
            route = f"{class_route}/{action_route}".strip("/")
            if not route:
                route = class_route

            # Find nearby method name
            after = content[match.end():]
            method_match = re.search(r"(?:public|private|protected)\s+\w+\s+(\w+)\s*\(", after)
            method_name = method_match.group(1) if method_match else ""

            # Get line number
            line = content[:match.start()].count("\n") + 1

            report.endpoints.append(EndpointInfo(
                route=route,
                method=http_method,
                controller=controller,
                file=file_path,
                line=line,
                auth_required=has_auth,
            ))

    def _extract_consumers(self, content: str, file_path: str, report: CrawlReport):
        """Extract MassTransit consumers and sagas."""
        for match in _CONSUMER_PATTERN.finditer(content):
            report.consumers.append(ConsumerInfo(
                consumer_class=match.group(1),
                message_type=match.group(2),
                file=file_path,
            ))
        for match in _SAGA_PATTERN.finditer(content):
            report.consumers.append(ConsumerInfo(
                consumer_class=match.group(1),
                message_type=match.group(2),
                queue=f"saga_{match.group(1).lower()}",
                file=file_path,
            ))

    def _extract_data_models(self, content: str, file_path: str, report: CrawlReport):
        """Extract EF Core data models."""
        ctx_match = _DBCONTEXT_PATTERN.search(content)
        if not ctx_match:
            return

        db_context = ctx_match.group(1)
        for set_match in _DBSET_PATTERN.finditer(content):
            entity_type = set_match.group(1)
            prop_name = set_match.group(2)
            report.data_models.append(DataModel(
                name=entity_type,
                db_context=db_context,
                properties=[prop_name],
                file=file_path,
            ))

    @staticmethod
    def _build_dependency_graph(projects: List[ProjectInfo]) -> dict:
        """Build a dependency graph from project references."""
        nodes = [{"id": p.name, "layer": p.layer} for p in projects]
        edges = []
        for p in projects:
            for ref in p.references:
                edges.append({"source": p.name, "target": ref})
        return {"nodes": nodes, "edges": edges}
