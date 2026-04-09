"""Business domain mapper.

Clusters projects, namespaces, code symbols and DI registrations into
``BusinessDomain`` records, and derives directed ``DomainContract`` edges
between them.

Heuristics, in order of precedence:

  1. Explicit hint mapping from config (``crawler.deep_analysis.domain_hints``)
     — a dict ``{ "DomainName": ["NamespacePrefix", ...] }``.
  2. Project name → domain. Strip common layer suffixes
     (.Domain, .Application, .Infrastructure, ...) and group siblings.
  3. Top-level namespace segment after the company prefix.

Contracts are inferred by joining ``DIRegistration`` (named HTTP clients,
DbContexts, MediatR/MassTransit consumers) with ``ConfigurationNode``
entries whose key path matches the named client.
"""

from __future__ import annotations

import logging
import re
from collections import defaultdict
from typing import Dict, List, Optional

from src.models.crawler import CrawlReport
from src.models.domain import BusinessDomain, DomainContract

logger = logging.getLogger(__name__)


_LAYER_SUFFIXES = (
    ".Domain", ".Application", ".Infrastructure", ".Persistence",
    ".Api", ".Web", ".Worker", ".Host", ".Tests", ".Test", ".Contracts",
    ".Shared", ".Common", ".Grpc", ".Consumer", ".Consumers",
)


# ── Public API ────────────────────────────────────────────────────────────


def build_domain_map(report: CrawlReport, hints: Optional[Dict[str, List[str]]] = None) -> None:
    """Populate ``report.business_domains`` and ``report.domain_contracts``.

    Mutates ``report`` in-place. Idempotent: existing entries are replaced.
    """
    hints = hints or {}

    # 1. Cluster projects → domains
    domains = _cluster_projects(report, hints)

    # 2. Attach namespaces, aggregates, events, endpoints from code symbols
    _attach_symbols(domains, report)

    # 3. Attach endpoints (route strings) by walking endpoints + projects
    _attach_endpoints(domains, report)

    # 4. Build contracts: join DI registrations + config nodes
    contracts = _build_contracts(report, domains)

    # 5. Resolve target_domain on each contract; populate inbound/outbound lists
    _link_contracts(contracts, domains)

    report.business_domains = list(domains.values())
    report.domain_contracts = contracts


# ── Step 1 ─ Cluster projects into domains ──────────────────────────────


def _cluster_projects(report: CrawlReport, hints: Dict[str, List[str]]) -> Dict[str, BusinessDomain]:
    domains: Dict[str, BusinessDomain] = {}

    for project in report.projects:
        domain_name = _domain_name_for_project(project.name, hints)
        domain = domains.setdefault(
            domain_name,
            BusinessDomain(name=domain_name, projects=[], namespaces=[]),
        )
        if project.name not in domain.projects:
            domain.projects.append(project.name)

    return domains


def _domain_name_for_project(project_name: str, hints: Dict[str, List[str]]) -> str:
    # Hint match: any prefix in hints whose value matches the project name?
    for hint_domain, prefixes in hints.items():
        for prefix in prefixes:
            if project_name.startswith(prefix):
                return hint_domain

    # Strip layer suffixes (longest match first to handle nested cases)
    name = project_name
    changed = True
    while changed:
        changed = False
        for suffix in sorted(_LAYER_SUFFIXES, key=len, reverse=True):
            if name.endswith(suffix):
                name = name[: -len(suffix)]
                changed = True
                break

    # If the result still has dots (e.g. "CoreTax.Invoices"), take the
    # last segment as the domain name.
    if "." in name:
        name = name.rsplit(".", 1)[-1]

    return name or project_name


# ── Step 2 ─ Attach symbol-level info ────────────────────────────────────


def _attach_symbols(domains: Dict[str, BusinessDomain], report: CrawlReport) -> None:
    project_to_domain = {p: d.name for d in domains.values() for p in d.projects}

    for project in report.projects:
        domain_name = project_to_domain.get(project.name)
        if not domain_name:
            continue
        domain = domains[domain_name]

        for sym in project.code_symbols:
            ns_root = _root_namespace(sym.namespace)
            if ns_root and ns_root not in domain.namespaces:
                domain.namespaces.append(ns_root)
            if sym.is_aggregate_root and sym.name not in domain.aggregates:
                domain.aggregates.append(sym.name)
            if sym.is_domain_event and sym.name not in domain.domain_events:
                domain.domain_events.append(sym.name)


def _root_namespace(ns: str) -> str:
    if not ns:
        return ""
    parts = ns.split(".")
    # Drop the company prefix when there are >=3 segments (e.g. CoreTax.Invoices.Domain → Invoices)
    if len(parts) >= 3:
        return parts[1]
    return parts[0]


# ── Step 3 ─ Attach endpoints ────────────────────────────────────────────


def _attach_endpoints(domains: Dict[str, BusinessDomain], report: CrawlReport) -> None:
    """Map endpoints to domains by file → project → domain."""
    file_to_project: Dict[str, str] = {}
    for project in report.projects:
        for sym in project.code_symbols:
            file_to_project.setdefault(sym.file, project.name)

    project_to_domain = {p: d.name for d in domains.values() for p in d.projects}

    for ep in report.endpoints:
        project_name = file_to_project.get(ep.file)
        if not project_name:
            continue
        domain_name = project_to_domain.get(project_name)
        if not domain_name:
            continue
        label = f"{ep.method} {ep.route}".strip()
        if label not in domains[domain_name].endpoints:
            domains[domain_name].endpoints.append(label)


# ── Step 4 ─ Build contracts ─────────────────────────────────────────────


_NAMED_HTTP_CONFIG_KEY_RE = re.compile(r"\.([A-Za-z0-9_]+)$")


def _build_contracts(report: CrawlReport, domains: Dict[str, BusinessDomain]) -> List[DomainContract]:
    project_to_domain = {p: d.name for d in domains.values() for p in d.projects}
    contracts: List[DomainContract] = []

    # Index config nodes by leaf-key (case-insensitive). Used to resolve
    # named HTTP clients to their configured base URL.
    config_index: Dict[str, List[str]] = defaultdict(list)
    for project in report.projects:
        for cfg in project.configurations:
            leaf = cfg.key.rsplit(".", 1)[-1].lower()
            if cfg.value:
                config_index[leaf].append(cfg.value)

    for project in report.projects:
        source_domain = project_to_domain.get(project.name, project.name)

        for reg in project.di_registrations:
            if reg.method == "AddHttpClient":
                target = reg.named_client or reg.implementation or reg.service_type or "http-client"
                # Try to resolve a config URL: e.g. named_client="OrdersService"
                # → look for a key whose leaf is "OrdersServiceUrl" / "OrdersService.BaseUrl" / etc.
                config_url = _resolve_named_client_url(reg.named_client, config_index)
                contracts.append(DomainContract(
                    source_project=project.name,
                    source_domain=source_domain,
                    target_service=target,
                    transport="http",
                    interface=reg.service_type or "HttpClient",
                    config_url=config_url,
                    registration_file=reg.source_file,
                    registration_line=reg.line,
                ))
            elif reg.method == "AddDbContext":
                contracts.append(DomainContract(
                    source_project=project.name,
                    source_domain=source_domain,
                    target_service=reg.implementation or "DbContext",
                    transport="db",
                    interface=reg.implementation or "DbContext",
                    registration_file=reg.source_file,
                    registration_line=reg.line,
                ))
            elif reg.method == "AddMassTransit":
                contracts.append(DomainContract(
                    source_project=project.name,
                    source_domain=source_domain,
                    target_service="message-bus",
                    transport="rabbitmq",
                    interface="MassTransit",
                    registration_file=reg.source_file,
                    registration_line=reg.line,
                ))

        # Also fold in IntegrationPoints discovered by integration_discovery
        for ip in report.integrations:
            if not ip.file or _file_in_project(ip.file, project):
                contracts.append(DomainContract(
                    source_project=project.name,
                    source_domain=source_domain,
                    target_service=ip.target or "external",
                    transport=ip.type or "unknown",
                    interface=ip.contract or "",
                    registration_file=ip.file,
                ))

    return contracts


def _resolve_named_client_url(client_name: str, config_index: Dict[str, List[str]]) -> str:
    if not client_name:
        return ""
    candidates = (
        client_name.lower() + "url",
        client_name.lower() + "uri",
        client_name.lower() + "endpoint",
        "baseurl",
        "baseaddress",
    )
    for key in candidates:
        if key in config_index and config_index[key]:
            return config_index[key][0]
    # Substring fallback
    for leaf, vals in config_index.items():
        if client_name.lower() in leaf and vals:
            return vals[0]
    return ""


def _file_in_project(file_path: str, project) -> bool:
    """Best-effort check that a file path lives under the project directory."""
    from pathlib import Path
    try:
        proj_dir = str(Path(project.path).parent.resolve()).lower()
        return Path(file_path).resolve().as_posix().lower().startswith(proj_dir.lower())
    except Exception:
        return False


# ── Step 5 ─ Link contracts to target domains ───────────────────────────


def _link_contracts(contracts: List[DomainContract], domains: Dict[str, BusinessDomain]) -> None:
    domain_names = list(domains.keys())
    for contract in contracts:
        target_domain = _guess_target_domain(contract.target_service, domain_names)
        if target_domain:
            contract.target_domain = target_domain
            if contract.source_domain and contract.source_domain != target_domain:
                src = domains.get(contract.source_domain)
                tgt = domains.get(target_domain)
                if src and target_domain not in src.outbound_contracts:
                    src.outbound_contracts.append(target_domain)
                if tgt and contract.source_domain not in tgt.inbound_contracts:
                    tgt.inbound_contracts.append(contract.source_domain)


def _guess_target_domain(target: str, domain_names: List[str]) -> str:
    if not target:
        return ""
    target_lower = target.lower()
    # Exact / substring match against known domain names
    for name in domain_names:
        if name.lower() == target_lower or name.lower() in target_lower:
            return name
    return ""
