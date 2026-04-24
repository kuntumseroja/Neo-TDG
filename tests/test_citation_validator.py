"""Tests for src.rag.citation_validator."""
from __future__ import annotations

from dataclasses import dataclass

import pytest

from src.rag.citation_validator import (
    CITE_PATTERN,
    Refusal,
    build_refusal,
    validate,
)


# --- Regex ----------------------------------------------------------------

@pytest.mark.parametrize("sample", [
    "[src/foo/Bar.cs:L12]",
    "[src/foo/Bar.cs:L12-L34]",
    "[Taxpayer/Registration.cs:L1-L500]",
    "[doc §3.2]",
    "[doc §10.1.4]",
])
def test_regex_matches_valid_citations(sample):
    assert CITE_PATTERN.search(sample), sample


@pytest.mark.parametrize("sample", [
    "[src/foo/Bar.cs]",           # no line number
    "[src/foo/Bar.cs:12-34]",     # missing L prefix
    "[§3.2]",                     # no 'doc'
    "(src/foo/Bar.cs:L12)",       # parentheses not brackets
])
def test_regex_rejects_invalid_citations(sample):
    assert not CITE_PATTERN.search(sample), sample


# --- Validator ------------------------------------------------------------

def test_validate_compliant_answer_at_high_ratio():
    answer = (
        "The taxpayer service validates IDs before persisting [src/Taxpayer.cs:L10-L22].\n\n"
        "Persistence uses the repository pattern [src/Taxpayer.cs:L40-L60]."
    )
    result = validate(answer, min_ratio=1.0)
    assert result.ok
    assert result.paragraphs_total == 2
    assert result.paragraphs_cited == 2


def test_validate_rejects_uncited_paragraph_at_ratio_one():
    answer = (
        "The taxpayer service validates IDs before persisting [src/Taxpayer.cs:L10-L22].\n\n"
        "Persistence uses the repository pattern and caches for 5 minutes."
    )
    result = validate(answer, min_ratio=1.0)
    assert not result.ok
    assert result.paragraphs_cited == 1
    assert any("uncited" in r for r in result.reasons)


def test_validate_accepts_partial_at_lower_ratio():
    answer = (
        "The taxpayer service validates IDs [src/Taxpayer.cs:L10].\n\n"
        "It also logs uncaught errors to stdout.\n\n"
        "Finally, DI wiring happens in Program.cs [src/Program.cs:L5-L8]."
    )
    # 2 / 3 = 0.67
    assert validate(answer, min_ratio=0.6).ok
    assert not validate(answer, min_ratio=0.8).ok


def test_validate_empty_answer_is_not_ok():
    result = validate("", min_ratio=0.7)
    assert not result.ok
    assert result.paragraphs_total == 0
    assert "empty_answer" in result.reasons


def test_validate_ignores_fenced_code_blocks():
    answer = (
        "Validation lives here [src/Taxpayer.cs:L10].\n\n"
        "```csharp\n"
        "public void Register(Taxpayer t) { ... }\n"
        "```\n\n"
        "Registration emits an audit log [src/Audit.cs:L42]."
    )
    # Two real paragraphs, both cited. Fenced block must not count.
    result = validate(answer, min_ratio=1.0)
    assert result.ok
    assert result.paragraphs_total == 2


def test_validate_explodes_bullet_list_into_paragraphs():
    answer = (
        "- First claim [a.cs:L1].\n"
        "- Second claim without a citation.\n"
        "- Third claim [b.cs:L3]."
    )
    result = validate(answer, min_ratio=1.0)
    assert result.paragraphs_total == 3
    assert result.paragraphs_cited == 2
    assert not result.ok


# --- Refusal object -------------------------------------------------------

@dataclass
class _FakeMeta:
    service_name: str = ""
    chunk_type: str = ""
    source_file: str = ""


@dataclass
class _FakeChunk:
    source_file: str
    metadata: _FakeMeta


def test_build_refusal_deduplicates_and_caps_hints():
    chunks = [
        _FakeChunk("src/Taxpayer.cs", _FakeMeta(service_name="TaxSvc", chunk_type="component")),
        _FakeChunk("src/Taxpayer.cs", _FakeMeta(service_name="TaxSvc", chunk_type="component")),
        _FakeChunk("src/Audit.cs",    _FakeMeta(service_name="AuditSvc", chunk_type="endpoint")),
        _FakeChunk("src/Billing.cs",  _FakeMeta()),
        _FakeChunk("src/A.cs",        _FakeMeta()),
        _FakeChunk("src/B.cs",        _FakeMeta()),
        _FakeChunk("src/C.cs",        _FakeMeta()),  # 7 distinct — expect cap at 5
    ]
    refusal = build_refusal(chunks, question="How does taxpayer audit work?")
    assert isinstance(refusal, Refusal)
    files = [h["file"] for h in refusal.hints]
    assert len(files) == 5
    # Dedup preserved order
    assert files[0] == "src/Taxpayer.cs"
    assert files.count("src/Taxpayer.cs") == 1


def test_refusal_to_dict_matches_schema():
    refusal = Refusal(
        reason="no evidence",
        hints=[{"file": "a.cs", "why": "component chunk"}],
        suggested_prompts=["try narrower"],
    )
    d = refusal.to_dict()
    assert d == {
        "answer": None,
        "refused": True,
        "reason": "no evidence",
        "hints": [{"file": "a.cs", "why": "component chunk"}],
        "suggested_prompts": ["try narrower"],
    }


def test_refusal_markdown_includes_hints():
    refusal = Refusal(
        reason="insufficient",
        hints=[{"file": "src/foo.cs", "why": "component chunk"}],
        suggested_prompts=["Rephrase"],
    )
    md = refusal.to_markdown()
    assert "don't have grounded evidence" in md
    assert "src/foo.cs" in md
    assert "Rephrase" in md
