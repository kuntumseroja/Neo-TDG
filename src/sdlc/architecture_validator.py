"""Architecture rule validation against crawl reports.

Supports both the legacy 3-section ruleset and the production-scale
``production_secure_rules.yaml`` format which adds secure-coding pattern
scanning, air-gap policy checks, controller authorization verification,
and crypto/supply-chain guidance.
"""

import logging
import re
from pathlib import Path
from typing import List, Optional, Set

import yaml

from src.models.crawler import CrawlReport
from src.models.sdlc import ValidationReport, Violation

logger = logging.getLogger(__name__)

# Hard cap on files scanned per rule to keep validation responsive even on
# large solutions. Override via rules.scan_limits.max_files.
_DEFAULT_MAX_SCAN_FILES = 2000
_DEFAULT_MAX_FILE_BYTES = 500_000  # 500 KB — skip huge generated files

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
        # Production-scale checks — only run when the corresponding
        # sections are present in the ruleset. The legacy coretax_rules.yaml
        # will skip all of these and produce its original output.
        if "secure_coding" in self.rules:
            violations.extend(self.check_secure_coding())
        if "airgap_policy" in self.rules:
            violations.extend(self.check_airgap_policy())
        if "cryptography" in self.rules:
            violations.extend(self.check_cryptography())
        if "pattern_compliance" in self.rules and \
                self.rules["pattern_compliance"].get("controllers_need_authorize"):
            violations.extend(self.check_controller_authorization())

        errors = sum(1 for v in violations if v.severity == "error")
        warnings = sum(1 for v in violations if v.severity == "warning")
        total = (
            len(self.rules.get("layer_dependencies", {}))
            + len(self.rules.get("naming_conventions", {}))
            + len(self.rules.get("pattern_compliance", {}))
            + len(self.rules.get("secure_coding", {}).get("forbidden_apis", []))
            + len(self.rules.get("airgap_policy", {}).get("forbidden_code_patterns", []))
            + (1 if self.rules.get("cryptography") else 0)
        )

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

    # ── Production-scale checks ─────────────────────────────────────────

    def check_secure_coding(self) -> List[Violation]:
        """Scan C# source for forbidden API usage patterns.

        Uses the ``secure_coding.forbidden_apis`` list from the ruleset.
        Each entry supports ``pattern``, ``severity``, ``reason`` and
        optional ``asvs`` / ``owasp`` references which are folded into the
        violation description for auditor traceability.
        """
        violations: List[Violation] = []
        entries = self.rules.get("secure_coding", {}).get("forbidden_apis", []) or []
        if not entries:
            return violations

        compiled = []
        for entry in entries:
            pat = entry.get("pattern")
            if not pat:
                continue
            try:
                compiled.append((re.compile(pat), entry))
            except re.error as e:
                logger.warning(f"Invalid secure_coding regex {pat!r}: {e}")

        if not compiled:
            return violations

        for file_path, content in self._iter_source_files({".cs"}):
            for rx, entry in compiled:
                m = rx.search(content)
                if not m:
                    continue
                line_no = content[: m.start()].count("\n") + 1
                refs = []
                if entry.get("asvs"):
                    refs.append(f"ASVS {entry['asvs']}")
                if entry.get("owasp"):
                    refs.append(f"OWASP {entry['owasp']}")
                ref_str = f" [{' · '.join(refs)}]" if refs else ""
                violations.append(Violation(
                    rule=f"secure_coding_forbidden_api",
                    severity=entry.get("severity", "warning"),
                    file=f"{file_path}:{line_no}",
                    description=(
                        f"Forbidden API `{m.group(0)[:80]}` matched "
                        f"pattern `{entry['pattern']}`{ref_str}: "
                        f"{entry.get('reason', 'Violates secure coding standard')}"
                    ),
                    suggested_fix=entry.get("reason", "Replace with an approved equivalent."),
                ))
        return violations

    def check_airgap_policy(self) -> List[Violation]:
        """Enforce the air-gap policy — detect public URLs and SaaS telemetry SDKs."""
        violations: List[Violation] = []
        policy = self.rules.get("airgap_policy", {}) or {}
        entries = policy.get("forbidden_code_patterns", []) or []
        forbidden_hosts = policy.get("forbidden_outbound_hosts", []) or []

        compiled = []
        for entry in entries:
            pat = entry.get("pattern")
            if not pat:
                continue
            try:
                compiled.append((re.compile(pat), entry))
            except re.error as e:
                logger.warning(f"Invalid airgap regex {pat!r}: {e}")

        host_rx = None
        if forbidden_hosts:
            host_patterns = [
                re.escape(h).replace(r"\*", r"[A-Za-z0-9\-.]*") for h in forbidden_hosts
            ]
            host_rx = re.compile(
                r"https?://(" + "|".join(host_patterns) + r")", re.IGNORECASE
            )

        for file_path, content in self._iter_source_files({".cs", ".json", ".yaml", ".yml", ".config"}):
            for rx, entry in compiled:
                m = rx.search(content)
                if m:
                    line_no = content[: m.start()].count("\n") + 1
                    violations.append(Violation(
                        rule="airgap_forbidden_pattern",
                        severity=entry.get("severity", "warning"),
                        file=f"{file_path}:{line_no}",
                        description=(
                            f"Air-gap violation: `{m.group(0)[:80]}` — "
                            f"{entry.get('reason', 'Forbidden in air-gapped deployments')}"
                        ),
                        suggested_fix="Use the internal mirror / internal service endpoint.",
                    ))
            if host_rx:
                m = host_rx.search(content)
                if m:
                    line_no = content[: m.start()].count("\n") + 1
                    violations.append(Violation(
                        rule="airgap_forbidden_host",
                        severity="error",
                        file=f"{file_path}:{line_no}",
                        description=(
                            f"Hardcoded reference to forbidden outbound host: "
                            f"`{m.group(0)[:120]}`"
                        ),
                        suggested_fix=(
                            "Route through the internal proxy/mirror. "
                            "Air-gapped clusters have no egress to public hosts."
                        ),
                    ))
        return violations

    def check_cryptography(self) -> List[Violation]:
        """Flag forbidden cryptographic primitives listed in cryptography.forbidden."""
        violations: List[Violation] = []
        forbidden = self.rules.get("cryptography", {}).get("forbidden", []) or []
        if not forbidden:
            return violations

        # Build a single regex that matches any forbidden primitive as a
        # word boundary so we don't match inside unrelated identifiers.
        tokens = []
        for item in forbidden:
            token = str(item).split(" ")[0]  # "RSA-PKCS1v1.5 (signing)" → "RSA-PKCS1v1.5"
            tokens.append(re.escape(token).replace(r"\-", r"[-_]?"))
        if not tokens:
            return violations
        combined = re.compile(r"\b(" + "|".join(tokens) + r")\b")

        for file_path, content in self._iter_source_files({".cs"}):
            m = combined.search(content)
            if not m:
                continue
            line_no = content[: m.start()].count("\n") + 1
            violations.append(Violation(
                rule="crypto_forbidden_primitive",
                severity="error",
                file=f"{file_path}:{line_no}",
                description=(
                    f"Forbidden cryptographic primitive `{m.group(0)}` found. "
                    f"Ruleset prohibits: {', '.join(str(x) for x in forbidden[:6])}…"
                ),
                suggested_fix=(
                    "Replace with an approved primitive from "
                    "`cryptography.approved_symmetric/asymmetric/hash`."
                ),
            ))
        return violations

    def check_controller_authorization(self) -> List[Violation]:
        """Every endpoint must be covered by `[Authorize]` or `[AllowAnonymous]`."""
        violations: List[Violation] = []
        scanned: Set[str] = set()

        for endpoint in self.report.endpoints:
            fp = endpoint.file
            if not fp or fp in scanned:
                continue
            scanned.add(fp)
            content = self._read_file(fp)
            if not content:
                continue
            has_authorize = "[Authorize" in content or "[AllowAnonymous" in content
            is_health_like = bool(re.search(r"/(health|metrics|swagger|openapi)", endpoint.route, re.I))
            if has_authorize or is_health_like:
                continue
            violations.append(Violation(
                rule="controller_needs_authorize",
                severity="error",
                file=fp,
                description=(
                    f"{endpoint.method} {endpoint.route} on "
                    f"{endpoint.controller} has no [Authorize] / [AllowAnonymous] attribute."
                ),
                suggested_fix=(
                    "Add [Authorize(Policy = \"…\")] at the controller or action "
                    "level, or mark explicitly [AllowAnonymous] for public health "
                    "probes. Implicitly-anonymous endpoints are forbidden."
                ),
            ))
        return violations

    # ── File-system helpers ─────────────────────────────────────────────

    def _iter_source_files(self, suffixes: Set[str]):
        """Yield ``(path, content)`` tuples for every file under any crawled
        project root that matches ``suffixes``, respecting size and count
        limits. Safe on large solutions — bails out after ``max_files``.
        """
        limits = self.rules.get("scan_limits", {}) or {}
        max_files = int(limits.get("max_files", _DEFAULT_MAX_SCAN_FILES))
        max_bytes = int(limits.get("max_file_bytes", _DEFAULT_MAX_FILE_BYTES))

        roots: Set[Path] = set()
        for project in self.report.projects:
            try:
                p = Path(project.path)
                if p.is_file():
                    roots.add(p.parent)
                elif p.is_dir():
                    roots.add(p)
            except Exception:
                continue

        scanned = 0
        for root in roots:
            if not root.exists():
                continue
            for path in root.rglob("*"):
                if scanned >= max_files:
                    return
                if not path.is_file():
                    continue
                if path.suffix.lower() not in suffixes:
                    continue
                # Skip obvious generated/vendored noise
                parts_lower = {p.lower() for p in path.parts}
                if parts_lower & {"bin", "obj", "node_modules", ".git", "wwwroot"}:
                    continue
                try:
                    if path.stat().st_size > max_bytes:
                        continue
                    content = path.read_text(encoding="utf-8", errors="ignore")
                except Exception:
                    continue
                scanned += 1
                yield str(path), content

    def _read_file(self, file_path: str) -> str:
        try:
            p = Path(file_path)
            if not p.exists() or p.stat().st_size > _DEFAULT_MAX_FILE_BYTES:
                return ""
            return p.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            return ""

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
