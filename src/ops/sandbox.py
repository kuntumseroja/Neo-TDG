"""Resolve all stateful paths and ports from the SANDBOX_NAME env var.

Import this at the very top of app.py — BEFORE any module that touches the
filesystem or opens sockets. Every other module must read paths / ports
through ``sandbox.context()`` rather than hard-coding them; the CI guardrail
(grep for ``knowledge_base/chroma`` | ``conversations.db`` | port literals)
enforces the rule.

When ``SANDBOX_NAME`` is unset the process behaves exactly as production did
before this module existed. When ``SANDBOX_NAME=<name>`` is set, every piece
of state moves under ``knowledge_base/sandbox/<name>/`` with its own ChromaDB
collection-name suffix and port offset, so a branch build can run alongside
a live production instance without touching its data.
"""
from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class Paths:
    """Every stateful filesystem location the app writes to."""

    knowledge_root: Path
    chroma_dir: Path
    conversations_db: Path
    ingest_dir: Path
    output_dir: Path
    logs_dir: Path
    run_dir: Path
    snapshots_dir: Path


@dataclass(frozen=True)
class Ports:
    """Every TCP port the app listens on."""

    streamlit: int
    fastapi: int
    roslyn: int


@dataclass(frozen=True)
class SandboxContext:
    name: str | None
    paths: Paths
    ports: Ports
    collection_suffix: str

    @property
    def is_sandbox(self) -> bool:
        return self.name is not None


_PROD_PORTS = Ports(streamlit=8503, fastapi=8080, roslyn=5050)
_SANDBOX_PORT_OFFSET = 10


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


@lru_cache(maxsize=1)
def context() -> SandboxContext:
    """Active sandbox context, cached for the process lifetime."""
    name = os.environ.get("SANDBOX_NAME") or None
    repo = _repo_root()

    if name is None:
        return SandboxContext(
            name=None,
            paths=Paths(
                knowledge_root=repo / "knowledge_base",
                chroma_dir=repo / "knowledge_base" / "chroma",
                conversations_db=repo / "knowledge_base" / "conversations.db",
                ingest_dir=repo / "knowledge_base" / "ingest",
                output_dir=repo / "docs",
                logs_dir=repo / "logs",
                run_dir=repo / ".run",
                snapshots_dir=repo / "knowledge_base" / "snapshots",
            ),
            ports=_PROD_PORTS,
            collection_suffix="",
        )

    base = repo / "knowledge_base" / "sandbox" / name
    return SandboxContext(
        name=name,
        paths=Paths(
            knowledge_root=base,
            chroma_dir=base / "chroma",
            conversations_db=base / "conversations.db",
            ingest_dir=base / "ingest",
            output_dir=base / "docs_output",
            logs_dir=base / "logs",
            run_dir=base / "run",
            snapshots_dir=base / "snapshots",
        ),
        ports=Ports(
            streamlit=_PROD_PORTS.streamlit + _SANDBOX_PORT_OFFSET,
            fastapi=_PROD_PORTS.fastapi + _SANDBOX_PORT_OFFSET,
            roslyn=_PROD_PORTS.roslyn + _SANDBOX_PORT_OFFSET,
        ),
        collection_suffix=f"__sandbox_{name}",
    )


def paths() -> Paths:
    return context().paths


def ports() -> Ports:
    return context().ports


def bootstrap() -> SandboxContext:
    """Create every state directory and return the active context.

    Call this once, as the first import-time side effect of the app, so the
    filesystem is in a known-good shape before any service initialises.
    """
    ctx = context()
    for p in (
        ctx.paths.knowledge_root,
        ctx.paths.chroma_dir,
        ctx.paths.ingest_dir,
        ctx.paths.output_dir,
        ctx.paths.logs_dir,
        ctx.paths.run_dir,
        ctx.paths.snapshots_dir,
    ):
        p.mkdir(parents=True, exist_ok=True)

    if ctx.is_sandbox:
        prod_chroma = (_repo_root() / "knowledge_base" / "chroma").resolve()
        if ctx.paths.chroma_dir.resolve() == prod_chroma:
            raise RuntimeError(
                f"Sandbox '{ctx.name}' resolved to the production chroma dir. "
                "Refusing to start — sandbox state must never overlap prod."
            )
        logger.warning(
            "SANDBOX MODE: %s — state under %s — production is untouched.",
            ctx.name,
            ctx.paths.knowledge_root,
        )

    return ctx


def assert_not_touching_prod() -> None:
    """Runtime guard: fail loud if a sandbox process has a prod file open.

    Uses psutil when available. If psutil is absent the check degrades to a
    no-op — the CI grep guardrail and path-based routing are the primary
    defences; this is a defence in depth.
    """
    ctx = context()
    if not ctx.is_sandbox:
        return

    try:
        import psutil
    except ImportError:
        logger.debug("psutil not installed — skipping open-file audit")
        return

    prod_chroma = (_repo_root() / "knowledge_base" / "chroma").resolve()
    sbx_chroma = ctx.paths.chroma_dir.resolve()
    for f in psutil.Process(os.getpid()).open_files():
        p = Path(f.path).resolve()
        try:
            p.relative_to(prod_chroma)
        except ValueError:
            continue
        try:
            p.relative_to(sbx_chroma)
        except ValueError:
            raise RuntimeError(f"Sandbox tried to open prod file: {p}")


def _reset_for_tests() -> None:
    """Clear the cached context. Call only from tests that flip SANDBOX_NAME."""
    # Tolerate monkeypatched `context` (no cache_clear on a lambda).
    clear = getattr(context, "cache_clear", None)
    if callable(clear):
        clear()
