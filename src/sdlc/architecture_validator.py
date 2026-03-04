"""Architecture rule validation against crawl reports."""

import logging
from pathlib import Path
from typing import List, Optional

import yaml

from src.models.crawler import CrawlReport
from src.models.sdlc import ValidationReport, Violation

logger = logging.getLogger(__name__)

# Default architecture rules
_DEFAULT_RULES = {
    "layer_dependencies": {
        "Domain": {"allowed_refs": [], "forbidden_refs": ["Infrastructure", "Presentation"]},
        "Application": {"allowed_refs": ["Domain"], "forbidden_refs": ["Infrastructure", "Presentation"]},
        "Infrastructure": {"allowed_refs": ["Domain", "Application"], "forbidden_refs": []},
        "Presentation": {"allowed_refs": ["Application", "Domain"], "forbidden_refs": ["Infrastructure"]},
    },
    "naming_conventions": {
        "Domain": {"must_not_contain": ["Controller", "Repository", "DbContext"]},
        "Application": {"must_contain_one_of": ["Handler", "Service", "Command", "Query", "Validator"]},
        "Infrastructure": {"must_contain_one_of": ["Repository", "DbContext", "Migration", "Client"]},
        "Presentation": {"must_contain_one_of": ["Controller", "Endpoint", "Hub"]},
    },
    "pattern_compliance": {
        "commands_need_validators": True,
        "handlers_need_interfaces": False,
        "max_coupling_threshold": 10,
    },
}


class ArchitectureValidator:
    """Validate a crawled solution against architecture rules."""

    def __init__(
        self,
        rules_path: Optional[str] = None,
        crawl_report: Optional[CrawlReport] = None,
    ):
        self.rules = self._load_rules(rules_path) if rules_path else _DEFAULT_RULES
        self.report = crawl_report

    def validate(self) -> ValidationReport:
        """Run all architecture validations and return a report."""
        if not self.report:
            return ValidationReport(
                violations=[Violation(
                    rule="prerequisites",
                    severity="error",
                    description="No crawl report available. Crawl a solution first.",
                )]
            )

        violations = []
        violations.extend(self.check_layer_dependencies())
        violations.extend(self.check_naming_conventions())
        violations.extend(self.check_pattern_compliance())

        errors = sum(1 for v in violations if v.severity == "error")
        warnings = sum(1 for v in violations if v.severity == "warning")
        total = len(self.rules.get("layer_dependencies", {})) + \
                len(self.rules.get("naming_conventions", {})) + \
                len(self.rules.get("pattern_compliance", {}))

        return ValidationReport(
            total_rules_checked=max(total, len(violations)),
            violations=violations,
            passed=max(total - errors - warnings, 0),
            failed=errors,
            warnings=warnings,
        )

    def check_layer_dependencies(self) -> List[Violation]:
        """Check that projects only reference allowed layers."""
        violations = []
        layer_rules = self.rules.get("layer_dependencies", {})

        # Build project-to-layer map
        layer_map = {p.name: p.layer for p in self.report.projects}

        for project in self.report.projects:
            if project.layer not in layer_rules:
                continue

            rules = layer_rules[project.layer]
            forbidden = rules.get("forbidden_refs", [])

            for ref in project.references:
                ref_layer = layer_map.get(ref, "Unknown")
                if ref_layer in forbidden:
                    violations.append(Violation(
                        rule=f"layer_dependency_{project.layer}",
                        severity="error",
                        file=project.path,
                        description=(
                            f"{project.name} ({project.layer}) references "
                            f"{ref} ({ref_layer}), which is forbidden."
                        ),
                        suggested_fix=(
                            f"Remove the direct reference from {project.layer} to {ref_layer}. "
                            f"Use dependency inversion (interfaces in Domain/Application, "
                            f"implementations in Infrastructure)."
                        ),
                    ))

        return violations

    def check_naming_conventions(self) -> List[Violation]:
        """Check project naming conventions per layer."""
        violations = []
        naming_rules = self.rules.get("naming_conventions", {})

        for project in self.report.projects:
            if project.layer not in naming_rules:
                continue

            rules = naming_rules[project.layer]

            # Check must_not_contain
            for forbidden in rules.get("must_not_contain", []):
                if forbidden.lower() in project.name.lower():
                    violations.append(Violation(
                        rule=f"naming_{project.layer}",
                        severity="warning",
                        file=project.path,
                        description=(
                            f"{project.name} in {project.layer} layer "
                            f"should not contain '{forbidden}' in its name."
                        ),
                        suggested_fix=f"Consider renaming or moving this project to the appropriate layer.",
                    ))

        return violations

    def check_pattern_compliance(self) -> List[Violation]:
        """Check CQRS/DDD pattern compliance."""
        violations = []
        patterns = self.rules.get("pattern_compliance", {})

        # Check coupling threshold
        max_coupling = patterns.get("max_coupling_threshold", 10)
        dep_edges = self.report.dependency_graph.get("edges", [])

        # Count references per project
        ref_counts = {}
        for edge in dep_edges:
            src = edge.get("source", "")
            ref_counts[src] = ref_counts.get(src, 0) + 1

        for project_name, count in ref_counts.items():
            if count > max_coupling:
                violations.append(Violation(
                    rule="coupling_threshold",
                    severity="warning",
                    file=project_name,
                    description=(
                        f"{project_name} has {count} outgoing references "
                        f"(threshold: {max_coupling}). High coupling detected."
                    ),
                    suggested_fix=(
                        f"Consider breaking this project into smaller modules "
                        f"or introducing abstraction layers to reduce coupling."
                    ),
                ))

        # Check that endpoints have controllers in Presentation layer
        for endpoint in self.report.endpoints:
            controller_project = self._find_project_for_file(endpoint.file)
            if controller_project and controller_project.layer not in ["Presentation", "Unknown"]:
                violations.append(Violation(
                    rule="controller_placement",
                    severity="warning",
                    file=endpoint.file,
                    description=(
                        f"Controller {endpoint.controller} is in {controller_project.layer} layer "
                        f"but should be in Presentation layer."
                    ),
                    suggested_fix="Move controllers to the Presentation/API layer.",
                ))

        return violations

    def _find_project_for_file(self, file_path: str):
        """Find which project a file belongs to."""
        file_path_normalized = file_path.replace("\\", "/").lower()
        for project in self.report.projects:
            project_dir = str(Path(project.path).parent).replace("\\", "/").lower()
            if project_dir in file_path_normalized:
                return project
        return None

    @staticmethod
    def _load_rules(rules_path: str) -> dict:
        """Load architecture rules from a YAML file."""
        path = Path(rules_path)
        if not path.exists():
            logger.warning(f"Rules file not found: {rules_path}, using defaults")
            return _DEFAULT_RULES
        with open(path) as f:
            rules = yaml.safe_load(f) or {}
        # Merge with defaults for any missing sections
        merged = {**_DEFAULT_RULES}
        merged.update(rules)
        return merged
