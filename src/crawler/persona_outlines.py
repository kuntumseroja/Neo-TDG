"""Per-persona outlines for the KT bundle (Phase 2).

An outline is a list of `OutlineItem`s — each item names a section, the
`source` the composer should resolve it against (crawl report, validation
report, RAG, or computed from the report), and an optional RAG query.

Keeping outlines as pure data makes them easy to test, tweak per tenant
(future Phase 6), and render in a UI. The composer consumes this module
via `outline_for(persona)` — no other coupling.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Optional

from src.rag.personas import PersonaId

SectionSource = Literal["report", "rules", "rag", "computed"]


@dataclass(frozen=True)
class OutlineItem:
    """One section within a persona's document outline."""

    id: str
    title: str
    source: SectionSource
    query: Optional[str] = None
    max_tokens: int = 800
    required: bool = True


# ---------------------------------------------------------------------------
# Outline builders. Each returns a fresh tuple so callers can't mutate the
# canonical definition by accident.
# ---------------------------------------------------------------------------

def _architect_outline() -> tuple[OutlineItem, ...]:
    return (
        OutlineItem("exec_summary", "Executive Summary", source="rag",
                    query="Summarise the solution in 6-10 sentences for a "
                          "Solution Architect — purpose, major components, "
                          "integration boundaries."),
        OutlineItem("system_context", "System Context", source="computed"),
        OutlineItem("component_model", "Component Model", source="computed"),
        OutlineItem("tech_stack", "Tech Stack and NFRs", source="computed"),
        OutlineItem("adrs", "Architecture Decision Records", source="rag",
                    query="What architectural decisions are implied by the "
                          "code and configuration? Produce 3-6 ADR stubs "
                          "(Context / Decision / Consequence).",
                    max_tokens=1200),
        OutlineItem("risk_register", "Risk Register", source="rules",
                    required=False),
        OutlineItem("recommendations", "Recommendations", source="rag",
                    query="Given the current architecture, list 3-5 "
                          "concrete, cited recommendations for the next "
                          "quarter. Each must carry a file or rule "
                          "citation."),
    )


def _developer_outline() -> tuple[OutlineItem, ...]:
    return (
        OutlineItem("overview", "Overview", source="rag",
                    query="Give a developer onboarding overview of this "
                          "solution in 8-12 sentences, naming the entry "
                          "points and build commands."),
        OutlineItem("solution_layout", "Solution Layout", source="computed"),
        OutlineItem("module_walkthrough", "Module Walkthrough", source="rag",
                    query="Walk through each project: purpose, key "
                          "classes, entry points. Cite every claim with "
                          "a file path.",
                    max_tokens=1400),
        OutlineItem("api_reference", "API Reference", source="computed"),
        OutlineItem("data_model", "Data Model", source="computed"),
        OutlineItem("extension_recipes", "Extension Recipes", source="rag",
                    query="Produce three extension recipes: adding a new "
                          "endpoint, a new consumer, a new DbSet. For "
                          "each, list the files to touch in order and "
                          "cite existing examples."),
        OutlineItem("faq", "FAQ", source="rag",
                    query="List 5 common developer questions and answers "
                          "for this codebase, each with a citation.",
                    required=False),
    )


def _tester_outline() -> tuple[OutlineItem, ...]:
    return (
        OutlineItem("scope", "Scope", source="rag",
                    query="Describe the testable surface of this solution "
                          "in 4-6 sentences — HTTP endpoints, consumers, "
                          "schedulers."),
        OutlineItem("test_plan", "Test Plan", source="rag",
                    query="Produce a high-level test plan grouped by "
                          "layer (unit / integration / e2e). For each "
                          "layer list what to cover and what tools "
                          "already exist in the repo."),
        OutlineItem("scenarios", "Scenarios", source="rag",
                    query="Write 6 Given/When/Then scenarios for the "
                          "highest-risk endpoints in this solution. Cite "
                          "the controller file for each scenario.",
                    max_tokens=1200),
        OutlineItem("fixtures", "Data and Fixtures", source="computed"),
        OutlineItem("regression_checklist", "Regression Checklist",
                    source="rules", required=False),
        OutlineItem("coverage_hints", "Coverage Hints", source="rag",
                    query="Which components appear least covered by "
                          "existing tests? Cite two examples of tests "
                          "that exist and two components without "
                          "matching tests."),
    )


def _l1_outline() -> tuple[OutlineItem, ...]:
    return (
        OutlineItem("quick_ref", "Quick Reference Card", source="rag",
                    query="One-page plain-English summary for L1 support: "
                          "what this system does, where it runs, who "
                          "owns it. Max 10 bullets, each one sentence.",
                    max_tokens=500),
        OutlineItem("health_check", "Health Check Steps", source="rag",
                    query="List the step-by-step health checks an L1 can "
                          "perform without reading code. Cite any "
                          "config or endpoint they should hit.",
                    max_tokens=700),
        OutlineItem("common_complaints", "Common User Complaints",
                    source="rag",
                    query="List the top 5 likely user-visible failure "
                          "modes and the one-line mitigation for each.",
                    max_tokens=600),
        OutlineItem("escalation", "Escalation Path", source="rag",
                    query="Document when L1 should escalate to L2 or L3, "
                          "with examples.",
                    max_tokens=400, required=False),
    )


def _l2_outline() -> tuple[OutlineItem, ...]:
    return (
        OutlineItem("runbook", "Runbook", source="rag",
                    query="Runbook for this service: start / stop / "
                          "restart / rollback. Cite the exact config "
                          "key or script each step references."),
        OutlineItem("triage", "Triage Playbook", source="rag",
                    query="Triage playbook: symptom -> check -> action. "
                          "Cover the 6 most likely production incidents "
                          "implied by this codebase.",
                    max_tokens=1200),
        OutlineItem("monitoring", "Monitoring and Alerts", source="rag",
                    query="What log patterns, metrics, or health "
                          "endpoints should L2 watch? Cite their source "
                          "files or config entries.",
                    max_tokens=700),
        OutlineItem("logs", "Log Reading Guide", source="rag",
                    query="Explain the log format and key fields in "
                          "plain English, citing any logger "
                          "configuration in the repo.",
                    max_tokens=500, required=False),
        OutlineItem("escalation", "Escalation Path", source="rag",
                    query="When to escalate to L3 (platform / dev). "
                          "Provide two concrete examples.",
                    max_tokens=300, required=False),
    )


def _l3_outline() -> tuple[OutlineItem, ...]:
    return (
        OutlineItem("deep_dive", "Deep Dive", source="rag",
                    query="Subsystem-level deep dive: boundaries, "
                          "persistence, concurrency. Each claim must "
                          "cite a file+line or a configuration section.",
                    max_tokens=1600),
        OutlineItem("debugging", "Debugging Procedures", source="rag",
                    query="Step-by-step debugging procedures for the "
                          "most complex flows. Cite the relevant "
                          "services and DI wiring.",
                    max_tokens=1200),
        OutlineItem("hotfix_sop", "Hotfix SOP", source="rag",
                    query="Standard operating procedure for shipping a "
                          "hotfix: branching, testing, rollback. Cite "
                          "CI / deployment config where present.",
                    max_tokens=600),
        OutlineItem("extensions", "Extension Recipes", source="rag",
                    query="Two advanced extension recipes aimed at "
                          "platform engineers: a new persistence "
                          "adapter and a new queue. Cite examples.",
                    max_tokens=900, required=False),
        OutlineItem("risks", "Known Risks", source="rules", required=False),
    )


_OUTLINES: dict[PersonaId, tuple[OutlineItem, ...]] = {
    "architect": _architect_outline(),
    "developer": _developer_outline(),
    "tester": _tester_outline(),
    "l1": _l1_outline(),
    "l2": _l2_outline(),
    "l3": _l3_outline(),
}


def outline_for(persona: PersonaId) -> tuple[OutlineItem, ...]:
    """Return the canonical outline for a persona. Raises KeyError on miss."""
    return _OUTLINES[persona]
