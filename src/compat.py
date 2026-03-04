"""
Standalone module exports for Neo-TDG.

Provides LLM infrastructure (BaseLLM, OllamaLLM, LLMFactory) using
Neo-TDG's own standalone providers. No dependency on TechDocGen.

Optional modules (parsers, readers, analyzers) are only available
when TechDocGen is present in the parent directory — they gracefully
fall back to None when absent.
"""
import sys
import importlib
import importlib.util
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

# ── LLM Core (always available — standalone) ─────────────────────────────────

from src.llm.base import BaseLLM
from src.llm.ollama_llm import OllamaLLM
from src.llm.factory import LLMFactory

TDGConfig = None  # Not needed in standalone mode

logger.info("Using standalone Neo-TDG LLM providers (Ollama)")


# ── Optional TechDocGen modules (graceful fallback to None) ──────────────────
# These are only available when TechDocGen is present alongside Neo-TDG.
# They provide C#/.NET-specific parsing and analysis capabilities.

_TECHDOCGEN_ROOT = Path(__file__).resolve().parent.parent.parent / "TechDocGen"
_USE_TECHDOCGEN = _TECHDOCGEN_ROOT.exists()


def _load_tdg_module(module_name: str, file_path: str):
    """Load a TechDocGen module by absolute file path."""
    full_path = _TECHDOCGEN_ROOT / file_path
    if not full_path.exists():
        raise ImportError(f"TechDocGen module not found: {full_path}")
    spec = importlib.util.spec_from_file_location(module_name, str(full_path))
    mod = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = mod
    spec.loader.exec_module(mod)
    return mod


if _USE_TECHDOCGEN:
    logger.info(f"TechDocGen found at {_TECHDOCGEN_ROOT} — loading optional modules")
else:
    logger.info("TechDocGen not found — optional C#/.NET modules not available")

try:
    _csharp_mod = _load_tdg_module("tdg.parsers.csharp_parser", "src/parsers/csharp_parser.py") if _USE_TECHDOCGEN else None
    CSharpParser = _csharp_mod.CSharpParser if _csharp_mod else None
except Exception:
    CSharpParser = None

try:
    _solution_mod = _load_tdg_module("tdg.parsers.solution_parser", "src/parsers/solution_parser.py") if _USE_TECHDOCGEN else None
    SolutionParser = _solution_mod.SolutionParser if _solution_mod else None
    CsprojParser = _solution_mod.CsprojParser if _solution_mod else None
except Exception:
    SolutionParser = None
    CsprojParser = None

try:
    _folder_mod = _load_tdg_module("tdg.readers.folder_reader", "src/readers/folder_reader.py") if _USE_TECHDOCGEN else None
    FolderReader = _folder_mod.FolderReader if _folder_mod else None
except Exception:
    FolderReader = None

try:
    _git_mod = _load_tdg_module("tdg.readers.git_reader", "src/readers/git_reader.py") if _USE_TECHDOCGEN else None
    GitReader = _git_mod.GitReader if _git_mod else None
except Exception:
    GitReader = None

try:
    _dep_mod = _load_tdg_module("tdg.dependency_analyzer", "src/dependency_analyzer.py") if _USE_TECHDOCGEN else None
    DependencyAnalyzer = _dep_mod.DependencyAnalyzer if _dep_mod else None
except Exception:
    DependencyAnalyzer = None

try:
    _svc_mod = _load_tdg_module("tdg.service_catalog", "src/service_catalog.py") if _USE_TECHDOCGEN else None
    build_service_catalog = _svc_mod.build_service_catalog if _svc_mod else None
except Exception:
    build_service_catalog = None

try:
    _ddd_mod = _load_tdg_module("tdg.ddd_documentation", "src/ddd_documentation.py") if _USE_TECHDOCGEN else None
    build_ddd_documentation = _ddd_mod.build_ddd_documentation if _ddd_mod else None
except Exception:
    build_ddd_documentation = None

try:
    _disc_mod = _load_tdg_module("tdg.solution_discovery", "src/solution_discovery.py") if _USE_TECHDOCGEN else None
    discover_from_solution = _disc_mod.discover_from_solution if _disc_mod else None
except Exception:
    discover_from_solution = None

try:
    _cg_mod = _load_tdg_module("tdg.call_graph_analyzer", "src/call_graph_analyzer.py") if _USE_TECHDOCGEN else None
    build_csharp_class_call_graphs = _cg_mod.build_csharp_class_call_graphs if _cg_mod else None
except Exception:
    build_csharp_class_call_graphs = None

try:
    _mt_mod = _load_tdg_module("tdg.flow_extractors.mass_transit", "src/flow_extractors/mass_transit.py") if _USE_TECHDOCGEN else None
    MassTransitFlowExtractor = _mt_mod.MassTransitFlowExtractor if _mt_mod else None
except Exception:
    MassTransitFlowExtractor = None


__all__ = [
    "BaseLLM",
    "OllamaLLM",
    "LLMFactory",
    "TDGConfig",
    "CSharpParser",
    "SolutionParser",
    "CsprojParser",
    "FolderReader",
    "GitReader",
    "DependencyAnalyzer",
    "MassTransitFlowExtractor",
    "build_service_catalog",
    "build_ddd_documentation",
    "discover_from_solution",
    "build_csharp_class_call_graphs",
]
