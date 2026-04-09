"""DI registration extractor.

Walks Startup.cs / Program.cs / *Extensions.cs files inside a .NET project
and captures container registrations made via the standard
``IServiceCollection`` extension methods. Returns a flat list of
``DIRegistration`` records.

Patterns recognized (regex; consistent with the existing crawler style):

  services.AddSingleton<IFoo, Foo>()
  services.AddScoped<IFoo, Foo>()
  services.AddTransient<IFoo, Foo>()
  services.AddSingleton<Foo>()                       (concrete-only)
  services.AddHttpClient("ServiceName")              (named client)
  services.AddHttpClient<IFoo, Foo>()
  services.AddHttpClient<IFoo, Foo>("ServiceName")
  services.AddDbContext<TaxDbContext>(...)
  services.AddMediatR(...)
  services.AddMassTransit(...)
"""

from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import List

from src.models.domain import DIRegistration

logger = logging.getLogger(__name__)


# Filenames most likely to contain DI registration code
_REGISTRATION_FILE_HINTS = (
    "startup.cs",
    "program.cs",
    "extensions.cs",            # *ServiceCollectionExtensions.cs
    "modulesetup.cs",
    "compositionroot.cs",
    "dependencyinjection.cs",
)

# Generic two-arg form: AddSingleton<IFoo, Foo>(...)
_DI_GENERIC_TWO_ARG = re.compile(
    r"\b(Add(?:Singleton|Scoped|Transient))\s*<\s*([\w.]+)\s*,\s*([\w.]+)\s*>",
)

# Generic one-arg form: AddSingleton<Foo>()  — concrete-only
_DI_GENERIC_ONE_ARG = re.compile(
    r"\b(Add(?:Singleton|Scoped|Transient))\s*<\s*([\w.]+)\s*>\s*\(",
)

# AddHttpClient with named client: AddHttpClient("Name")
_HTTPCLIENT_NAMED = re.compile(
    r'\bAddHttpClient(?:\s*<\s*([\w.]+)(?:\s*,\s*([\w.]+))?\s*>)?\s*\(\s*"([^"]+)"',
)

# AddHttpClient generic only: AddHttpClient<IFoo, Foo>()
_HTTPCLIENT_GENERIC = re.compile(
    r"\bAddHttpClient\s*<\s*([\w.]+)\s*,\s*([\w.]+)\s*>\s*\(",
)

# AddDbContext<Foo>(...)
_DBCONTEXT = re.compile(r"\bAddDbContext\s*<\s*([\w.]+)\s*>")

# Marker calls that don't have type args we can extract
_MARKER_CALLS = (
    ("AddMediatR", r"\bAddMediatR\s*\("),
    ("AddMassTransit", r"\bAddMassTransit\s*\("),
    ("AddAutoMapper", r"\bAddAutoMapper\s*\("),
    ("AddHangfire", r"\bAddHangfire\s*\("),
    ("AddQuartz", r"\bAddQuartz\s*\("),
)
_MARKER_PATTERNS = [(name, re.compile(pat)) for name, pat in _MARKER_CALLS]


def scan_project_di(project_dir: str | Path, project_name: str = "") -> List[DIRegistration]:
    """Scan a project directory for DI registrations."""
    root = Path(project_dir)
    if not root.exists() or not root.is_dir():
        return []

    registrations: List[DIRegistration] = []

    for cs_file in _candidate_files(root):
        try:
            content = cs_file.read_text(encoding="utf-8", errors="ignore")
        except OSError as exc:
            logger.warning("dependency_extractor: cannot read %s: %s", cs_file, exc)
            continue
        registrations.extend(_extract_from_file(content, cs_file, project_name))

    return registrations


def _candidate_files(root: Path):
    """Yield .cs files likely to contain DI registrations.

    Heuristic: prioritize files whose name matches the hints, but also
    include any *.cs whose content references ``IServiceCollection`` —
    bounded by a fast pre-filter to avoid scanning every file twice.
    """
    skip = {"bin", "obj", "node_modules", ".git", ".vs"}
    for path in root.rglob("*.cs"):
        parts_lower = {p.lower() for p in path.parts}
        if parts_lower & skip:
            continue
        name_lower = path.name.lower()
        if any(hint in name_lower for hint in _REGISTRATION_FILE_HINTS):
            yield path
            continue
        # Cheap pre-filter: only open files that mention IServiceCollection
        try:
            with path.open("rb") as f:
                head = f.read(4096)
            if b"IServiceCollection" in head or b"services.Add" in head:
                yield path
        except OSError:
            continue


def _extract_from_file(content: str, file_path: Path, project: str) -> List[DIRegistration]:
    out: List[DIRegistration] = []
    file_str = str(file_path)

    def _line_of(pos: int) -> int:
        return content.count("\n", 0, pos) + 1

    # Generic two-arg lifetime registrations
    for m in _DI_GENERIC_TWO_ARG.finditer(content):
        out.append(DIRegistration(
            project=project,
            source_file=file_str,
            line=_line_of(m.start()),
            method=m.group(1),
            service_type=m.group(2),
            implementation=m.group(3),
            raw=m.group(0),
        ))

    # Generic one-arg (concrete-only)
    for m in _DI_GENERIC_ONE_ARG.finditer(content):
        out.append(DIRegistration(
            project=project,
            source_file=file_str,
            line=_line_of(m.start()),
            method=m.group(1),
            service_type=m.group(2),
            implementation=m.group(2),
            raw=m.group(0),
        ))

    # Named HTTP clients
    for m in _HTTPCLIENT_NAMED.finditer(content):
        out.append(DIRegistration(
            project=project,
            source_file=file_str,
            line=_line_of(m.start()),
            method="AddHttpClient",
            service_type=m.group(1) or "",
            implementation=m.group(2) or "",
            named_client=m.group(3),
            raw=m.group(0),
        ))

    # Generic HTTP clients (no name)
    for m in _HTTPCLIENT_GENERIC.finditer(content):
        out.append(DIRegistration(
            project=project,
            source_file=file_str,
            line=_line_of(m.start()),
            method="AddHttpClient",
            service_type=m.group(1),
            implementation=m.group(2),
            raw=m.group(0),
        ))

    # DbContext
    for m in _DBCONTEXT.finditer(content):
        out.append(DIRegistration(
            project=project,
            source_file=file_str,
            line=_line_of(m.start()),
            method="AddDbContext",
            service_type=m.group(1),
            implementation=m.group(1),
            raw=m.group(0),
        ))

    # Markers (no extractable type arg)
    for marker_name, pattern in _MARKER_PATTERNS:
        for m in pattern.finditer(content):
            out.append(DIRegistration(
                project=project,
                source_file=file_str,
                line=_line_of(m.start()),
                method=marker_name,
                service_type="",
                implementation="",
                raw=m.group(0),
            ))

    return out
