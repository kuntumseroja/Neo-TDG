"""End-to-end smoke tests for Phase 1 persona-aware querying.

These tests don't touch a real LLM or vector store — they swap in stubs so
we can assert, deterministically, that:

* architect vs l1 end up with *different* system prompts (different tone,
  depth, avoid/emphasise tokens)
* with the `six_personas` flag OFF, the legacy CoreTax prompt is used
  verbatim and `response.persona` is None
* with orphan mode ON and a persona that sets `refuse_without_evidence`,
  a never-citing LLM produces a structured refusal rather than a
  low-citation-rate warning.
"""
from __future__ import annotations

from typing import List

import pytest

from src.models.knowledge import ChunkMetadata, ChunkResult
from src.rag.prompts import SYSTEM_PROMPT
from src.rag.query_engine import RAGQueryEngine


# --- Stubs ----------------------------------------------------------------

class _RecordingLLM:
    """LLM stub that records every call and replays a canned answer.

    `answers` is a list; each generate() pops the next one. When the list
    runs out it just returns the last answer forever. The retry path uses
    two generate() calls, so tests can supply two answers to exercise it.
    """

    def __init__(self, answers: List[str]):
        self.answers = list(answers)
        self.calls: List[dict] = []

    def generate(self, user_prompt: str, system_prompt: str = "") -> str:
        self.calls.append({"user": user_prompt, "system": system_prompt})
        if len(self.answers) > 1:
            return self.answers.pop(0)
        return self.answers[0]


class _StubStore:
    """Vector store stub that returns a fixed list of chunks."""

    def __init__(self, chunks: List[ChunkResult]):
        self._chunks = chunks

    def query(self, question: str, top_k: int = 20, filters=None):
        return list(self._chunks)


def _chunk(source_file: str, service: str = "TaxSvc", chunk_type: str = "component") -> ChunkResult:
    return ChunkResult(
        content=f"// source: {source_file}\npublic class Stub {{ }}",
        metadata=ChunkMetadata(
            service_name=service,
            chunk_type=chunk_type,
            source_file=source_file,
        ),
        score=0.9,
        source_file=source_file,
        chunk_id=source_file,
    )


def _engine(llm: _RecordingLLM, *, config: dict) -> RAGQueryEngine:
    store = _StubStore([_chunk("src/Taxpayer.cs"), _chunk("src/Audit.cs", service="AuditSvc")])
    return RAGQueryEngine(
        store=store,
        llm=llm,
        reranker=None,  # default reranker passes through when len <= top_k
        conversation_memory=None,
        config=config,
    )


_GOOD_ANSWER = (
    "The taxpayer service validates IDs before persisting "
    "[src/Taxpayer.cs:L10-L22].\n\n"
    "Audit records are emitted on every write [src/Audit.cs:L5-L30]."
)

_SIX_PERSONAS_ON = {"kt_pro": {"six_personas": {"enabled": True}}}
_ORPHAN_ON = {
    "kt_pro": {
        "six_personas": {"enabled": True},
        "orphan_mode": {"enabled": True},
    },
}


# --- Tests ----------------------------------------------------------------

def test_architect_and_l1_get_different_system_prompts():
    """Same question, different personas -> different system prompt.

    We don't test answer-length/depth (that's the LLM's job) — we test
    that the system prompt the LLM SEES is different, which is what
    actually drives length/depth at inference time.
    """
    llm_arch = _RecordingLLM([_GOOD_ANSWER])
    llm_l1 = _RecordingLLM([_GOOD_ANSWER])

    _engine(llm_arch, config=_SIX_PERSONAS_ON).query(
        "How does taxpayer audit work?", persona="architect",
    )
    _engine(llm_l1, config=_SIX_PERSONAS_ON).query(
        "How does taxpayer audit work?", persona="l1",
    )

    sys_arch = llm_arch.calls[0]["system"]
    sys_l1 = llm_l1.calls[0]["system"]

    assert sys_arch != sys_l1
    # Architect profile should name itself in its prompt.
    assert "Solution Architect" in sys_arch
    assert "L1 Support Engineer" in sys_l1
    # The preamble tokens are shared, the persona-specific suffixes are not.
    assert "bounded contexts" in sys_arch
    assert "bounded contexts" not in sys_l1
    assert "escalate to L2" in sys_l1
    assert "escalate to L2" not in sys_arch


def test_six_personas_flag_off_uses_legacy_prompt_and_skips_validation():
    """Flag OFF — legacy CoreTax prompt, persona is None, no retry."""
    llm = _RecordingLLM(["Plain answer with no citations at all."])
    engine = _engine(llm, config={})  # empty config -> flag off

    resp = engine.query("What does the taxpayer service do?", persona="architect")

    # Exactly one call — no retry, no validation.
    assert len(llm.calls) == 1
    # Legacy prompt is used verbatim.
    assert llm.calls[0]["system"].startswith(SYSTEM_PROMPT.split("\n")[0][:40])
    assert "You are a CoreTax technical assistant" in llm.calls[0]["system"]
    # Persona didn't survive onto the response.
    assert resp.persona is None
    assert resp.refused is False
    assert resp.warnings == []


def test_uncited_answer_retries_once_then_warns_without_orphan_mode():
    """Flag on, orphan OFF — two bad drafts => low_citation_rate warning.

    Legacy fallback behaviour from TASK_KT_PRO_UPGRADE §1.5.
    """
    bad = "I think taxpayers are stored somewhere. They get audited later."
    llm = _RecordingLLM([bad, bad])  # two uncited drafts

    engine = _engine(llm, config=_SIX_PERSONAS_ON)
    resp = engine.query("How does taxpayer audit work?", persona="architect")

    assert len(llm.calls) == 2  # original + one retry
    assert "MISSING CITATIONS" in llm.calls[1]["user"]
    assert resp.refused is False
    assert "low_citation_rate" in resp.warnings


def test_uncited_answer_under_orphan_mode_produces_structured_refusal():
    """Flag on + orphan on — persisting uncited output => refusal object."""
    bad = "Taxpayers live in the database. They get audited later."
    llm = _RecordingLLM([bad, bad])

    engine = _engine(llm, config=_ORPHAN_ON)
    resp = engine.query("How does taxpayer audit work?", persona="l1")

    assert len(llm.calls) == 2
    assert resp.refused is True
    assert resp.refusal_reason
    assert resp.hints, "refusal must surface candidate files"
    # Hints should point at our stub chunks.
    assert any(h["file"] == "src/Taxpayer.cs" for h in resp.hints)
    # Markdown-rendered answer replaces the bad draft.
    assert "don't have grounded evidence" in resp.answer
    assert "refused_insufficient_evidence" in resp.warnings


def test_compliant_answer_accepts_without_retry():
    """A good first draft short-circuits the retry loop."""
    llm = _RecordingLLM([_GOOD_ANSWER])
    engine = _engine(llm, config=_SIX_PERSONAS_ON)

    resp = engine.query("How does taxpayer audit work?", persona="developer")

    assert len(llm.calls) == 1  # no retry
    assert resp.refused is False
    assert resp.warnings == []
    assert resp.persona == "developer"
    assert resp.answer == _GOOD_ANSWER


def test_unknown_persona_falls_back_to_default():
    """An unknown persona id doesn't explode — it maps to DEFAULT_PERSONA."""
    llm = _RecordingLLM([_GOOD_ANSWER])
    engine = _engine(llm, config=_SIX_PERSONAS_ON)

    resp = engine.query("How does taxpayer audit work?", persona="ceo")

    from src.rag.personas import DEFAULT_PERSONA
    assert resp.persona == DEFAULT_PERSONA


def test_prepare_and_finalize_honor_persona_flag():
    """The streaming split-path mirrors query() for persona + validation."""
    llm = _RecordingLLM([_GOOD_ANSWER])
    engine = _engine(llm, config=_SIX_PERSONAS_ON)

    prepared = engine.prepare_query(
        "How does taxpayer audit work?", persona="tester",
    )
    assert prepared["persona"] == "tester"
    assert "QA / Test Engineer" in prepared["system_prompt"]

    resp = engine.finalize_query(
        "How does taxpayer audit work?", _GOOD_ANSWER, prepared,
    )
    assert resp.refused is False
    assert resp.persona == "tester"
    assert resp.warnings == []
