"""Sandbox isolation contract tests.

These tests lock in the property that SANDBOX_NAME must never resolve to
any path or port that production uses. If this file starts failing, STOP —
a regression here means a branch build could clobber production state.
"""
from __future__ import annotations

import os
from pathlib import Path

import pytest


@pytest.fixture
def clear_env(monkeypatch):
    """Clear SANDBOX_NAME and the cached context."""
    monkeypatch.delenv("SANDBOX_NAME", raising=False)
    from src.ops import sandbox
    sandbox._reset_for_tests()
    yield
    sandbox._reset_for_tests()


def _fresh_ctx(monkeypatch, name: str | None):
    from src.ops import sandbox
    if name is None:
        monkeypatch.delenv("SANDBOX_NAME", raising=False)
    else:
        monkeypatch.setenv("SANDBOX_NAME", name)
    sandbox._reset_for_tests()
    return sandbox.context()


def test_prod_context_uses_bare_knowledge_base(monkeypatch, clear_env):
    ctx = _fresh_ctx(monkeypatch, None)
    assert ctx.name is None
    assert ctx.is_sandbox is False
    assert ctx.paths.knowledge_root.name == "knowledge_base"
    assert ctx.collection_suffix == ""
    assert ctx.ports.streamlit == 8503
    assert ctx.ports.fastapi == 8080


def test_sandbox_context_is_namespaced(monkeypatch, clear_env):
    ctx = _fresh_ctx(monkeypatch, "phase-1")
    assert ctx.is_sandbox is True
    assert ctx.name == "phase-1"
    assert "sandbox" in ctx.paths.knowledge_root.parts
    assert "phase-1" in ctx.paths.knowledge_root.parts
    assert ctx.collection_suffix == "__sandbox_phase-1"
    # Port offset +10 is a hard contract
    assert ctx.ports.streamlit == 8513
    assert ctx.ports.fastapi == 8090
    assert ctx.ports.roslyn == 5060


def test_sandbox_paths_never_overlap_prod(monkeypatch, clear_env):
    prod = _fresh_ctx(monkeypatch, None)
    sbx = _fresh_ctx(monkeypatch, "isolation-check")

    # Every sandbox path must be a strict descendant of the sandbox root,
    # never the same as or parent of a prod path.
    for p_path, s_path in [
        (prod.paths.chroma_dir, sbx.paths.chroma_dir),
        (prod.paths.conversations_db, sbx.paths.conversations_db),
        (prod.paths.ingest_dir, sbx.paths.ingest_dir),
    ]:
        assert p_path.resolve() != s_path.resolve(), (
            f"Sandbox path {s_path} collides with prod path {p_path}"
        )
        # Sandbox must be under knowledge_base/sandbox/<name>/
        assert "sandbox" in s_path.resolve().parts
        assert "isolation-check" in s_path.resolve().parts


def test_sandbox_ports_never_overlap_prod(monkeypatch, clear_env):
    prod = _fresh_ctx(monkeypatch, None)
    sbx = _fresh_ctx(monkeypatch, "port-check")
    for p_port, s_port in [
        (prod.ports.streamlit, sbx.ports.streamlit),
        (prod.ports.fastapi, sbx.ports.fastapi),
        (prod.ports.roslyn, sbx.ports.roslyn),
    ]:
        assert p_port != s_port, f"Port collision: prod={p_port} sbx={s_port}"
        assert s_port - p_port == 10


def test_bootstrap_refuses_sandbox_that_maps_to_prod_chroma(monkeypatch, clear_env, tmp_path):
    """Defence-in-depth: bootstrap must raise if chroma_dir resolves to prod."""
    from src.ops import sandbox as sbx_mod

    ctx = _fresh_ctx(monkeypatch, "decoy")
    # Simulate a context whose chroma_dir == prod chroma (should never happen
    # in practice, but the guard exists as belt-and-braces).
    prod_chroma = (Path(sbx_mod.__file__).resolve().parents[2] / "knowledge_base" / "chroma")

    class _BadCtx:
        name = "decoy"
        is_sandbox = True
        class paths:
            knowledge_root = ctx.paths.knowledge_root
            chroma_dir = prod_chroma
            ingest_dir = ctx.paths.ingest_dir
            output_dir = ctx.paths.output_dir
            logs_dir = ctx.paths.logs_dir
            run_dir = ctx.paths.run_dir
            snapshots_dir = ctx.paths.snapshots_dir
            conversations_db = ctx.paths.conversations_db

    monkeypatch.setattr(sbx_mod, "context", lambda: _BadCtx)
    with pytest.raises(RuntimeError, match="production chroma dir"):
        sbx_mod.bootstrap()


def test_vector_store_applies_collection_suffix(monkeypatch, clear_env, tmp_path):
    """VectorKnowledgeStore must suffix the collection when in a sandbox."""
    monkeypatch.setenv("SANDBOX_NAME", "suffix-check")
    from src.ops import sandbox as sbx_mod
    sbx_mod._reset_for_tests()

    from src.knowledge.vector_store import VectorKnowledgeStore

    class _StubProvider:
        def embed_texts(self, xs):
            return [[0.0] * 4 for _ in xs]

    store = VectorKnowledgeStore(
        persist_dir=str(tmp_path),
        embedding_provider=_StubProvider(),
        collection_name="techdocgen_knowledge",
    )
    assert store.collection_name == "techdocgen_knowledge__sandbox_suffix-check"
