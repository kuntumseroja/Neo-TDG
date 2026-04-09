"""Configuration file analyzer.

Walks a project directory and parses configuration files commonly found in
.NET solutions, producing flat ``ConfigurationNode`` records:

  - appsettings.json
  - appsettings.{Environment}.json
  - launchSettings.json
  - web.config / app.config (XML)
  - *.runtimeconfig.json (skipped, build artifact)

The analyzer is intentionally tolerant: malformed JSON or XML is logged
and skipped, never raised. The aim is wide breadth, not strict validation.
"""

from __future__ import annotations

import json
import logging
import re
from pathlib import Path
from typing import Iterable, List, Optional
from xml.etree import ElementTree as ET

from src.models.domain import ConfigurationNode

logger = logging.getLogger(__name__)


# ── Constants ─────────────────────────────────────────────────────────────

# Filename → environment label, ordered most-specific first.
_APPSETTINGS_RE = re.compile(r"^appsettings(?:\.([A-Za-z0-9_-]+))?\.json$", re.IGNORECASE)

_LAUNCH_SETTINGS = "launchsettings.json"

_XML_CONFIGS = ("web.config", "app.config")

# Heuristics for classifying a key
_CONNECTION_STRING_KEYS = ("connectionstring", "connectionstrings")
_FEATURE_FLAG_KEYS = ("featuremanagement", "featureflags", "features")
_URL_HINT = ("url", "uri", "endpoint", "host", "baseaddress")

# Env var reference patterns inside config values
_ENV_PLACEHOLDER_PATTERNS = (
    re.compile(r"\$\{(?:env:)?([A-Z0-9_]+)\}", re.IGNORECASE),  # ${ENV:FOO} / ${FOO}
    re.compile(r"%([A-Z0-9_]+)%"),                              # %FOO%
    re.compile(r"\$env:([A-Z0-9_]+)", re.IGNORECASE),           # $env:FOO
)


# ── Public API ────────────────────────────────────────────────────────────


def scan_project_configs(project_dir: str | Path, project_name: str = "") -> List[ConfigurationNode]:
    """Discover and parse all known config files under ``project_dir``.

    Returns a flat list of ``ConfigurationNode``. Order is not guaranteed.
    """
    root = Path(project_dir)
    if not root.exists() or not root.is_dir():
        return []

    nodes: List[ConfigurationNode] = []

    for path in _iter_config_files(root):
        try:
            name_lower = path.name.lower()
            if name_lower == _LAUNCH_SETTINGS:
                nodes.extend(_parse_launch_settings(path, project_name))
            elif _APPSETTINGS_RE.match(path.name):
                env = _APPSETTINGS_RE.match(path.name).group(1) or ""
                nodes.extend(_parse_appsettings(path, env, project_name))
            elif name_lower in _XML_CONFIGS:
                nodes.extend(_parse_xml_config(path, project_name))
        except Exception as exc:  # noqa: BLE001 — analyzer must never raise
            logger.warning("config_analyzer: failed to parse %s: %s", path, exc)

    return nodes


# ── File discovery ────────────────────────────────────────────────────────


def _iter_config_files(root: Path) -> Iterable[Path]:
    """Yield config files under root, skipping bin/obj/node_modules."""
    skip = {"bin", "obj", "node_modules", ".git", ".vs"}
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        parts_lower = {p.lower() for p in path.parts}
        if parts_lower & skip:
            continue
        name_lower = path.name.lower()
        if name_lower == _LAUNCH_SETTINGS:
            yield path
        elif _APPSETTINGS_RE.match(path.name):
            yield path
        elif name_lower in _XML_CONFIGS:
            yield path


# ── Parsers ───────────────────────────────────────────────────────────────


def _parse_appsettings(path: Path, environment: str, project: str) -> List[ConfigurationNode]:
    raw = path.read_text(encoding="utf-8-sig", errors="ignore")
    if not raw.strip():
        return []
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        logger.warning("config_analyzer: invalid JSON in %s: %s", path, exc)
        return []

    nodes: List[ConfigurationNode] = []
    for key, value in _flatten(data):
        nodes.append(_make_node(key, value, str(path), environment, project))
    return nodes


def _parse_launch_settings(path: Path, project: str) -> List[ConfigurationNode]:
    """Extract launch profiles: ports, application URLs, environment variables."""
    raw = path.read_text(encoding="utf-8-sig", errors="ignore")
    if not raw.strip():
        return []
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        logger.warning("config_analyzer: invalid JSON in %s: %s", path, exc)
        return []

    nodes: List[ConfigurationNode] = []
    profiles = data.get("profiles", {}) if isinstance(data, dict) else {}
    if not isinstance(profiles, dict):
        return nodes

    for profile_name, profile in profiles.items():
        if not isinstance(profile, dict):
            continue
        env_vars = profile.get("environmentVariables", {})
        env_label = ""
        if isinstance(env_vars, dict):
            env_label = str(env_vars.get("ASPNETCORE_ENVIRONMENT", "")) or ""

        for key, value in _flatten(profile, prefix=f"profiles.{profile_name}"):
            node = _make_node(key, value, str(path), env_label, project)
            # Tag environment-variable subkeys explicitly
            if ".environmentVariables." in key:
                node.kind = "env_var"
            nodes.append(node)

    return nodes


def _parse_xml_config(path: Path, project: str) -> List[ConfigurationNode]:
    """Best-effort parser for legacy web.config / app.config files."""
    try:
        tree = ET.parse(path)
    except ET.ParseError as exc:
        logger.warning("config_analyzer: invalid XML in %s: %s", path, exc)
        return []

    nodes: List[ConfigurationNode] = []
    root = tree.getroot()

    # <appSettings><add key="X" value="Y" /></appSettings>
    for add in root.iter():
        tag = add.tag.split("}", 1)[-1].lower()  # strip xmlns
        if tag != "add":
            continue
        key = add.attrib.get("key") or add.attrib.get("name")
        value = add.attrib.get("value") or add.attrib.get("connectionString") or ""
        if not key:
            continue
        # Detect connection strings vs settings
        parent_path = _xml_ancestor_path(root, add)
        full_key = f"{parent_path}.{key}" if parent_path else key
        nodes.append(_make_node(full_key, value, str(path), "", project))

    return nodes


def _xml_ancestor_path(root: ET.Element, target: ET.Element) -> str:
    """Return dotted ancestor tag path for an XML element (best-effort)."""
    # ElementTree has no parent pointers; do a recursive search.
    def walk(node: ET.Element, trail: List[str]) -> Optional[List[str]]:
        for child in node:
            tag = child.tag.split("}", 1)[-1]
            if child is target:
                return trail
            found = walk(child, trail + [tag])
            if found is not None:
                return found
        return None

    trail = walk(root, [root.tag.split("}", 1)[-1]])
    return ".".join(trail) if trail else ""


# ── Helpers ───────────────────────────────────────────────────────────────


def _flatten(obj, prefix: str = ""):
    """Yield ``(dotted_key, str_value)`` pairs from a nested dict/list."""
    if isinstance(obj, dict):
        for k, v in obj.items():
            new_prefix = f"{prefix}.{k}" if prefix else str(k)
            yield from _flatten(v, new_prefix)
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            new_prefix = f"{prefix}[{i}]"
            yield from _flatten(v, new_prefix)
    else:
        yield prefix, "" if obj is None else str(obj)


def _make_node(key: str, value: str, source_file: str, environment: str, project: str) -> ConfigurationNode:
    kind = _classify(key, value)
    env_var = _extract_env_var(value)
    return ConfigurationNode(
        key=key,
        value=value,
        source_file=source_file,
        environment=environment,
        project=project,
        kind=kind,
        references_env_var=env_var,
    )


def _classify(key: str, value: str) -> str:
    key_lower = key.lower()
    if any(cs in key_lower for cs in _CONNECTION_STRING_KEYS):
        return "connection_string"
    if any(ff in key_lower for ff in _FEATURE_FLAG_KEYS):
        return "feature_flag"
    if any(u in key_lower for u in _URL_HINT):
        return "url"
    if value and (value.startswith("http://") or value.startswith("https://")):
        return "url"
    return "setting"


def _extract_env_var(value: str) -> Optional[str]:
    if not value:
        return None
    for pattern in _ENV_PLACEHOLDER_PATTERNS:
        m = pattern.search(value)
        if m:
            return m.group(1)
    return None
