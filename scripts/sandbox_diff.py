#!/usr/bin/env python3
"""Diff a sandbox's knowledge store against production.

Offline, read-only. Prints a markdown table of:
  * chunk count delta
  * document count delta
  * service list delta (added / removed)
  * chunk-type histogram delta

Usage:
    python scripts/sandbox_diff.py <sandbox-name>
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))


def _stats_for(env_name: str | None) -> dict:
    """Load store stats under the given SANDBOX_NAME (None == production)."""
    if env_name is None:
        os.environ.pop("SANDBOX_NAME", None)
    else:
        os.environ["SANDBOX_NAME"] = env_name

    from src.ops import sandbox as sbx
    sbx._reset_for_tests()  # clear lru_cache so env change takes effect
    sbx.bootstrap()

    # Minimal import chain — avoid pulling in Streamlit
    from src.knowledge.vector_store import VectorKnowledgeStore
    from src.knowledge.embeddings import create_embedding_provider
    import yaml

    with open(REPO / "config.yaml") as f:
        config = yaml.safe_load(f) or {}

    ctx = sbx.context()
    try:
        provider = create_embedding_provider(config)
    except Exception:
        # Embedding provider may be offline; stats doesn't need it but ctor does.
        # Fall back to a dummy that never gets called.
        class _Dummy:
            def embed_texts(self, xs): return [[0.0] for _ in xs]
        provider = _Dummy()

    store = VectorKnowledgeStore(
        persist_dir=str(ctx.paths.knowledge_root),
        embedding_provider=provider,
        collection_name=config.get("knowledge_store", {}).get(
            "collection_name", "techdocgen_knowledge"
        ),
    )
    return store.get_stats()


def _fmt_set(s: set) -> str:
    return ", ".join(sorted(s)) if s else "—"


def main(name: str) -> int:
    print(f"# Sandbox diff: `{name}` vs production\n")
    prod = _stats_for(None)
    sbx = _stats_for(name)

    def row(label: str, p, s):
        print(f"| {label} | {p} | {s} | {s - p if isinstance(p, int) else ''} |")

    print("| Metric | Production | Sandbox | Δ |")
    print("|---|---:|---:|---:|")
    row("Chunks",    prod.get("total_chunks", 0),    sbx.get("total_chunks", 0))
    row("Documents", prod.get("total_documents", 0), sbx.get("total_documents", 0))
    print()

    prod_svcs = set(prod.get("services", []))
    sbx_svcs  = set(sbx.get("services", []))
    print("## Services")
    print(f"- Added in sandbox:   {_fmt_set(sbx_svcs - prod_svcs)}")
    print(f"- Removed in sandbox: {_fmt_set(prod_svcs - sbx_svcs)}")
    print()

    all_types = set(prod.get("chunk_types", {})) | set(sbx.get("chunk_types", {}))
    if all_types:
        print("## Chunk types")
        print("| Type | Production | Sandbox | Δ |")
        print("|---|---:|---:|---:|")
        for t in sorted(all_types):
            p = prod.get("chunk_types", {}).get(t, 0)
            s = sbx.get("chunk_types", {}).get(t, 0)
            print(f"| {t} | {p} | {s} | {s - p} |")
    return 0


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: sandbox_diff.py <sandbox-name>", file=sys.stderr)
        raise SystemExit(2)
    raise SystemExit(main(sys.argv[1]))
