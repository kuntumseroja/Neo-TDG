"""
Compatibility bridge for importing from the existing TechDocGen project.

Uses importlib to load TechDocGen modules directly by path, avoiding
conflicts with Neo-TDG's own 'src' package.
"""
import sys
import importlib
import importlib.util
from pathlib import Path

# Resolve the TechDocGen root relative to this file
# Neo-TDG/src/compat.py -> ../../TechDocGen
_TECHDOCGEN_ROOT = Path(__file__).resolve().parent.parent.parent / "TechDocGen"

if not _TECHDOCGEN_ROOT.exists():
    raise ImportError(
        f"TechDocGen not found at {_TECHDOCGEN_ROOT}. "
        "Expected at ../TechDocGen/ relative to Neo-TDG/"
    )


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


# Load TechDocGen modules with unique prefixed names to avoid conflicts
_base_llm_mod = _load_tdg_module("tdg.llm.base_llm", "src/llm/base_llm.py")
_ollama_llm_mod = _load_tdg_module("tdg.llm.ollama_llm", "src/llm/ollama_llm.py")
_mcp_llm_mod = _load_tdg_module("tdg.llm.mcp_llm", "src/llm/mcp_llm.py")
_llm_factory_mod = _load_tdg_module("tdg.llm.llm_factory", "src/llm/llm_factory.py")
_config_mod = _load_tdg_module("tdg.config", "src/config.py")

BaseLLM = _base_llm_mod.BaseLLM
OllamaLLM = _ollama_llm_mod.OllamaLLM
LLMFactory = _llm_factory_mod.LLMFactory
TDGConfig = _config_mod.Config

# Optional modules — load if available, skip if missing
try:
    _csharp_mod = _load_tdg_module("tdg.parsers.csharp_parser", "src/parsers/csharp_parser.py")
    CSharpParser = _csharp_mod.CSharpParser
except Exception:
    CSharpParser = None

try:
    _solution_mod = _load_tdg_module("tdg.parsers.solution_parser", "src/parsers/solution_parser.py")
    SolutionParser = _solution_mod.SolutionParser
    CsprojParser = _solution_mod.CsprojParser
except Exception:
    SolutionParser = None
    CsprojParser = None

try:
    _folder_mod = _load_tdg_module("tdg.readers.folder_reader", "src/readers/folder_reader.py")
    FolderReader = _folder_mod.FolderReader
except Exception:
    FolderReader = None

try:
    _git_mod = _load_tdg_module("tdg.readers.git_reader", "src/readers/git_reader.py")
    GitReader = _git_mod.GitReader
except Exception:
    GitReader = None

try:
    _dep_mod = _load_tdg_module("tdg.dependency_analyzer", "src/dependency_analyzer.py")
    DependencyAnalyzer = _dep_mod.DependencyAnalyzer
except Exception:
    DependencyAnalyzer = None

try:
    _svc_mod = _load_tdg_module("tdg.service_catalog", "src/service_catalog.py")
    build_service_catalog = _svc_mod.build_service_catalog
except Exception:
    build_service_catalog = None

try:
    _ddd_mod = _load_tdg_module("tdg.ddd_documentation", "src/ddd_documentation.py")
    build_ddd_documentation = _ddd_mod.build_ddd_documentation
except Exception:
    build_ddd_documentation = None

try:
    _disc_mod = _load_tdg_module("tdg.solution_discovery", "src/solution_discovery.py")
    discover_from_solution = _disc_mod.discover_from_solution
except Exception:
    discover_from_solution = None

try:
    _cg_mod = _load_tdg_module("tdg.call_graph_analyzer", "src/call_graph_analyzer.py")
    build_csharp_class_call_graphs = _cg_mod.build_csharp_class_call_graphs
except Exception:
    build_csharp_class_call_graphs = None

try:
    _mt_mod = _load_tdg_module("tdg.flow_extractors.mass_transit", "src/flow_extractors/mass_transit.py")
    MassTransitFlowExtractor = _mt_mod.MassTransitFlowExtractor
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
