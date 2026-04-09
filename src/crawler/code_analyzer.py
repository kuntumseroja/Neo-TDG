"""C# code symbol extractor.

Lightweight regex-based pass over .cs files that records every top-level
type declaration (class / interface / record / struct / enum) along with
its namespace, base types, attributes and a small set of DDD-aware flags.

The output (``CodeSymbol``) feeds the ``domain_mapper`` (which clusters
symbols into business domains) and surfaces in the RAG store as
high-fidelity, file-level metadata.
"""

from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import List

from src.models.domain import CodeSymbol

logger = logging.getLogger(__name__)


# ── Regexes ───────────────────────────────────────────────────────────────

_NAMESPACE = re.compile(
    r"^\s*namespace\s+([\w.]+)\s*[;{]", re.MULTILINE
)

# Capture leading attributes (as a single block) + type declaration.
# Matches:  [Attr1] [Attr2(...)]\n public sealed class Foo : Base, IBar
_TYPE_DECL = re.compile(
    r"((?:^[ \t]*\[[^\]]+\][ \t]*\r?\n)*)"             # group(1) attribute lines (multiline)
    r"^[ \t]*"
    r"(?:public|internal|private|protected)?\s*"
    r"(?:abstract|sealed|static|partial|readonly|ref)?\s*"
    r"(?:abstract|sealed|static|partial|readonly|ref)?\s*"
    r"(class|interface|record(?:\s+struct)?|struct|enum)\s+"     # group(2) kind
    r"(\w+)"                                                       # group(3) name
    r"(?:\s*<[^>]+>)?"                                             # generic params (ignored)
    r"(?:\s*:\s*([^{\r\n]+))?",                                    # group(4) base list
    re.MULTILINE,
)

_ATTR_NAME = re.compile(r"\[([\w.]+)")

# DDD heuristics
_AGGREGATE_BASES = ("AggregateRoot", "Entity", "IAggregateRoot")
_VALUE_OBJECT_BASES = ("ValueObject", "IValueObject")
_DOMAIN_EVENT_BASES = ("INotification", "IDomainEvent", "DomainEvent", "IntegrationEvent")
_REPO_BASES = ("IRepository", "Repository", "IGenericRepository")
_CONTROLLER_BASES = ("ControllerBase", "Controller", "ApiController")


# ── Public API ────────────────────────────────────────────────────────────


def scan_project_symbols(project_dir: str | Path, project_name: str = "") -> List[CodeSymbol]:
    """Walk a project directory and extract every top-level C# type."""
    root = Path(project_dir)
    if not root.exists() or not root.is_dir():
        return []

    symbols: List[CodeSymbol] = []
    skip = {"bin", "obj", "node_modules", ".git", ".vs"}

    for cs_file in root.rglob("*.cs"):
        parts_lower = {p.lower() for p in cs_file.parts}
        if parts_lower & skip:
            continue
        try:
            content = cs_file.read_text(encoding="utf-8", errors="ignore")
        except OSError as exc:
            logger.warning("code_analyzer: cannot read %s: %s", cs_file, exc)
            continue
        symbols.extend(_extract_symbols(content, cs_file, project_name))

    return symbols


# ── Extraction ────────────────────────────────────────────────────────────


def _extract_symbols(content: str, file_path: Path, project: str) -> List[CodeSymbol]:
    out: List[CodeSymbol] = []

    # Take the first namespace declaration; nested namespaces are rare in
    # modern .NET, and the file-level namespace covers the common case.
    ns_match = _NAMESPACE.search(content)
    namespace = ns_match.group(1) if ns_match else ""

    file_str = str(file_path)

    for m in _TYPE_DECL.finditer(content):
        attr_block = m.group(1) or ""
        kind = m.group(2)
        name = m.group(3)
        base_list_raw = m.group(4) or ""

        # Normalize "record struct" → "record"
        if kind.startswith("record"):
            kind = "record"

        attributes = _ATTR_NAME.findall(attr_block)
        base_types = _split_bases(base_list_raw)

        line = content.count("\n", 0, m.start()) + 1

        symbol = CodeSymbol(
            name=name,
            kind=kind,
            namespace=namespace,
            project=project,
            file=file_str,
            line=line,
            base_types=base_types,
            attributes=attributes,
        )
        _apply_ddd_flags(symbol)
        out.append(symbol)

    return out


def _split_bases(raw: str) -> List[str]:
    if not raw.strip():
        return []
    # Strip generics and whitespace
    parts = []
    depth = 0
    current = []
    for ch in raw:
        if ch == "<":
            depth += 1
            current.append(ch)
        elif ch == ">":
            depth -= 1
            current.append(ch)
        elif ch == "," and depth == 0:
            parts.append("".join(current).strip())
            current = []
        else:
            current.append(ch)
    if current:
        parts.append("".join(current).strip())
    return [p for p in parts if p]


def _apply_ddd_flags(symbol: CodeSymbol) -> None:
    """Set DDD/MVC flags using base-type and naming heuristics."""
    base_short = [b.split("<", 1)[0] for b in symbol.base_types]

    # Aggregates
    if any(b in _AGGREGATE_BASES for b in base_short):
        symbol.is_aggregate_root = True

    # Value objects
    if any(b in _VALUE_OBJECT_BASES for b in base_short):
        symbol.is_value_object = True

    # Domain events
    if any(b in _DOMAIN_EVENT_BASES for b in base_short):
        symbol.is_domain_event = True
    if symbol.name.endswith("Event") or symbol.name.endswith("DomainEvent") or symbol.name.endswith("IntegrationEvent"):
        symbol.is_domain_event = True

    # Repositories
    if any(b in _REPO_BASES for b in base_short):
        symbol.is_repository = True
    if symbol.kind == "interface" and symbol.name.startswith("I") and symbol.name.endswith("Repository"):
        symbol.is_repository = True
    if symbol.kind == "class" and symbol.name.endswith("Repository"):
        symbol.is_repository = True

    # Controllers
    if any(b in _CONTROLLER_BASES for b in base_short):
        symbol.is_controller = True
    if symbol.name.endswith("Controller"):
        symbol.is_controller = True
