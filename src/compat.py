"""
Compatibility bridge for importing from the existing TechDocGen project.

When TechDocGen is available (local dev), loads from there.
When NOT available (cloud deployment), falls back to Neo-TDG's standalone providers.
"""
import sys
import importlib
import importlib.util
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

# Resolve the TechDocGen root relative to this file
# Neo-TDG/src/compat.py -> ../../TechDocGen
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


# ── LLM Core (always available) ──────────────────────────────────────────────

if _USE_TECHDOCGEN:
    try:
        _base_llm_mod = _load_tdg_module("tdg.llm.base_llm", "src/llm/base_llm.py")
        _ollama_llm_mod = _load_tdg_module("tdg.llm.ollama_llm", "src/llm/ollama_llm.py")
        _llm_factory_mod = _load_tdg_module("tdg.llm.llm_factory", "src/llm/llm_factory.py")
        _config_mod = _load_tdg_module("tdg.config", "src/config.py")

        BaseLLM = _base_llm_mod.BaseLLM
        OllamaLLM = _ollama_llm_mod.OllamaLLM
        _TDGLLMFactory = _llm_factory_mod.LLMFactory
        TDGConfig = _config_mod.Config

        # Wrap TDG factory to also support cloud providers
        from src.llm.factory import LLMFactory as _StandaloneLLMFactory

        class LLMFactory:
            """Hybrid factory: tries TechDocGen first, falls back to standalone."""

            @staticmethod
            def create(provider_name: str, config: dict):
                if provider_name in ("groq", "openai", "together"):
                    return _StandaloneLLMFactory.create(provider_name, config)
                try:
                    return _TDGLLMFactory.create(provider_name, config)
                except Exception:
                    return _StandaloneLLMFactory.create(provider_name, config)

        logger.info("Using TechDocGen LLM modules (with cloud provider support)")

    except Exception as e:
        logger.warning(f"TechDocGen LLM load failed: {e}, using standalone providers")
        _USE_TECHDOCGEN = False

if not _USE_TECHDOCGEN:
    # ── Standalone mode (cloud deployment) ────────────────────────────────
    from src.llm.base import BaseLLM
    from src.llm.ollama_llm import OllamaLLM
    from src.llm.factory import LLMFactory

    TDGConfig = None
    logger.info("Using standalone Neo-TDG LLM providers (cloud mode)")


# ── Optional TechDocGen modules (graceful fallback to None) ──────────────────

try:
    _mcp_llm_mod = _load_tdg_module("tdg.llm.mcp_llm", "src/llm/mcp_llm.py") if _USE_TECHDOCGEN else None
except Exception:
    _mcp_llm_mod = None

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
