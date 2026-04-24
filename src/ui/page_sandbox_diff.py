"""Sandbox A/B diff page — visible only when SANDBOX_NAME is set.

Shows a side-by-side comparison of the current sandbox's knowledge-store
stats against production, so reviewers can see at a glance what a branch
build has added / removed before promotion.
"""
from __future__ import annotations

import streamlit as st

from src.ops import sandbox


def render_sandbox_diff() -> None:
    ctx = sandbox.context()
    if not ctx.is_sandbox:
        st.info(
            "This page is only meaningful when running under a sandbox. "
            "Launch a sandbox with `./scripts/lumen.sh sandbox start <name>`."
        )
        return

    st.header(f"🧪 Sandbox vs Production — `{ctx.name}`")
    st.caption(
        f"Sandbox state: `{ctx.paths.knowledge_root}` · "
        f"Collection suffix: `{ctx.collection_suffix}`"
    )

    store = st.session_state.get("store")
    if not store:
        st.warning("Knowledge store not initialised yet.")
        return

    sbx_stats = store.get_stats()

    # Load prod stats from a parallel store instance (read-only).
    try:
        prod_stats = _load_prod_stats()
    except Exception as exc:
        st.error(f"Could not load production stats: {exc}")
        return

    col1, col2, col3 = st.columns(3)
    col1.metric(
        "Chunks (sandbox)",
        sbx_stats.get("total_chunks", 0),
        delta=sbx_stats.get("total_chunks", 0) - prod_stats.get("total_chunks", 0),
    )
    col2.metric(
        "Documents (sandbox)",
        sbx_stats.get("total_documents", 0),
        delta=sbx_stats.get("total_documents", 0) - prod_stats.get("total_documents", 0),
    )
    col3.metric(
        "Services (sandbox)",
        len(sbx_stats.get("services", [])),
        delta=len(sbx_stats.get("services", [])) - len(prod_stats.get("services", [])),
    )

    prod_svcs = set(prod_stats.get("services", []))
    sbx_svcs = set(sbx_stats.get("services", []))
    added = sorted(sbx_svcs - prod_svcs)
    removed = sorted(prod_svcs - sbx_svcs)

    st.subheader("Service deltas")
    left, right = st.columns(2)
    with left:
        st.markdown("**Added in sandbox**")
        st.write(added or "_none_")
    with right:
        st.markdown("**Removed from sandbox**")
        st.write(removed or "_none_")

    all_types = sorted(
        set(prod_stats.get("chunk_types", {})) | set(sbx_stats.get("chunk_types", {}))
    )
    if all_types:
        st.subheader("Chunk-type histogram")
        rows = []
        for t in all_types:
            p = prod_stats.get("chunk_types", {}).get(t, 0)
            s = sbx_stats.get("chunk_types", {}).get(t, 0)
            rows.append({"chunk_type": t, "prod": p, "sandbox": s, "delta": s - p})
        st.dataframe(rows, use_container_width=True, hide_index=True)


def _load_prod_stats() -> dict:
    """Read production stats by opening its chroma dir directly, read-only.

    We do not go through the sandbox module (which is pinned to the current
    context) — instead we point a fresh VectorKnowledgeStore at the prod path.
    No writes happen; this is purely stats.
    """
    from pathlib import Path
    from src.knowledge.vector_store import VectorKnowledgeStore
    from src.knowledge.embeddings import create_embedding_provider

    config = st.session_state.get("config", {})
    prod_root = Path(__file__).resolve().parents[2] / "knowledge_base"
    provider = create_embedding_provider(config)

    prod_store = VectorKnowledgeStore(
        persist_dir=str(prod_root),
        embedding_provider=provider,
        collection_name=config.get("knowledge_store", {}).get(
            "collection_name", "techdocgen_knowledge"
        ),
    )
    # vector_store applies the sandbox suffix inside __init__; strip it back off
    # so we hit the prod collection name. A bit of a hack — acceptable because
    # this page only runs in sandbox mode and only for stats.
    ctx = sandbox.context()
    if ctx.collection_suffix and prod_store.collection_name.endswith(ctx.collection_suffix):
        prod_name = prod_store.collection_name[: -len(ctx.collection_suffix)]
        prod_store._collection = prod_store._client.get_or_create_collection(
            name=prod_name,
            embedding_function=prod_store._embedding_fn,
            metadata={"hnsw:space": "cosine"},
        )
        prod_store.collection_name = prod_name
    return prod_store.get_stats()
