"""Six-persona registry for the KT-Pro upgrade (Phase 1).

Each persona carries its own tone, depth, forbidden topics, and the minimum
citation ratio the citation validator enforces. The registry is pure data —
no I/O, no LLM calls — so it's safe to import anywhere.

When `kt_pro.six_personas.enabled = false` (default) the rest of the app
ignores this file and falls back to the legacy generic prompt in
`src/rag/prompts.py`. When the flag is flipped on, query_engine reads the
persona off `QueryRequest.persona` and uses the matching profile.

The orphan-mode flag (`kt_pro.orphan_mode.enabled`) tightens the regime
further by flipping `refuse_without_evidence` and raising the citation
ratio to 1.0 for the three support personas — see
docs/TASK_KT_PRO_ORPHAN_MODE.md §2.1.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

PersonaId = Literal["architect", "developer", "tester", "l1", "l2", "l3"]

ALL_PERSONA_IDS: tuple[PersonaId, ...] = (
    "architect", "developer", "tester", "l1", "l2", "l3",
)

DEFAULT_PERSONA: PersonaId = "developer"


@dataclass(frozen=True)
class PersonaProfile:
    """Profile for one reader persona."""

    id: PersonaId
    display_name: str
    tone: str
    depth: Literal["shallow", "medium", "deep"]
    avoid: tuple[str, ...]
    emphasise: tuple[str, ...]
    system_prompt: str
    # Minimum fraction of paragraphs that must carry a valid citation for
    # the answer to be accepted. Orphan mode tightens this per-persona
    # (see `min_ratio_for()` below).
    min_citation_ratio: float = 0.7
    refuse_without_evidence: bool = True


# ---------------------------------------------------------------------------
# System-prompt preamble — shared across all personas. {tenant} is filled at
# query time (defaults to the value under `kt_pro.tenant` in config.yaml;
# Phase 6 makes this per-request). {persona_display_name}, {persona_tone},
# {persona_avoid}, {persona_emphasise} are filled from the profile.
# ---------------------------------------------------------------------------
ORPHAN_PREAMBLE = """\
You are the Knowledge Assistant for {tenant}. The original developers of
this codebase are not available. Everything you know comes from the code,
the uploaded documents, and prior captured knowledge. Therefore:

1. Never state intent you cannot cite. Prefer "appears to", "likely",
   "inferred from <signal>". Confidence must be explicit.
2. Every factual sentence MUST carry a citation of the form
   [file.cs:L<start>-L<end>] or [doc §<section>].
3. If evidence is insufficient, answer: "I don't have grounded evidence
   for this. Here are the files most likely relevant: ...".
4. Prefer Observation -> Evidence -> Inference -> Confidence -> Next step.
5. You are talking to a {persona_display_name}. Use their tone: {persona_tone}.
   Avoid: {persona_avoid}. Emphasise: {persona_emphasise}.
6. When asked about a component, also surface "unknown unknowns" - things
   you could not determine, so the user can go find out.
"""


def _persona(
    *,
    id: PersonaId,
    display_name: str,
    tone: str,
    depth: Literal["shallow", "medium", "deep"],
    avoid: tuple[str, ...],
    emphasise: tuple[str, ...],
    persona_specific_suffix: str,
    min_citation_ratio: float,
) -> PersonaProfile:
    prompt = (
        ORPHAN_PREAMBLE
        + "\n"
        + persona_specific_suffix.strip()
        + "\n"
    )
    return PersonaProfile(
        id=id,
        display_name=display_name,
        tone=tone,
        depth=depth,
        avoid=avoid,
        emphasise=emphasise,
        system_prompt=prompt,
        min_citation_ratio=min_citation_ratio,
        refuse_without_evidence=True,
    )


PERSONAS: dict[PersonaId, PersonaProfile] = {
    "architect": _persona(
        id="architect",
        display_name="Solution Architect",
        tone="strategic, trade-off oriented, systems-thinking",
        depth="deep",
        avoid=(
            "line-by-line walkthroughs",
            "deep debugging tactics",
            "incident-response playbooks",
        ),
        emphasise=(
            "component boundaries",
            "integration points",
            "data ownership",
            "non-functional constraints",
        ),
        persona_specific_suffix=(
            "Frame answers around bounded contexts, contracts between "
            "services, and the NFR implications of the design. Keep "
            "code-level detail to the minimum needed to anchor the "
            "architecture claim."
        ),
        min_citation_ratio=0.9,
    ),
    "developer": _persona(
        id="developer",
        display_name="Software Developer",
        tone="pragmatic, code-anchored, precise",
        depth="deep",
        avoid=(
            "business-strategy commentary",
            "hand-wavy overviews without file references",
        ),
        emphasise=(
            "file paths with line ranges",
            "call graphs",
            "signatures",
            "tests that cover the area",
        ),
        persona_specific_suffix=(
            "Answer as a developer would read the code: name the files, "
            "classes, methods, and lines; quote the relevant fragment; "
            "call out side effects, DI wiring, and tests. Prefer code "
            "structure over prose."
        ),
        min_citation_ratio=0.9,
    ),
    "tester": _persona(
        id="tester",
        display_name="QA / Test Engineer",
        tone="risk-aware, scenario-driven, coverage-minded",
        depth="medium",
        avoid=(
            "architectural abstractions without testable hooks",
            "speculative refactoring advice",
        ),
        emphasise=(
            "inputs/outputs and boundary conditions",
            "happy-path vs unhappy-path coverage",
            "existing test fixtures",
            "obvious gaps in test coverage",
        ),
        persona_specific_suffix=(
            "Shape every answer around what can be tested. Call out "
            "observable behaviour, fixtures available, and missing "
            "coverage. When proposing test cases, number them and name "
            "them."
        ),
        min_citation_ratio=0.9,
    ),
    "l1": _persona(
        id="l1",
        display_name="L1 Support Engineer",
        tone="calm, checklist-driven, plain English",
        depth="shallow",
        avoid=(
            "raw code",
            "internal class names",
            "jargon without a one-line gloss",
        ),
        emphasise=(
            "user-visible symptoms",
            "where to look in logs / dashboards",
            "when to escalate to L2",
        ),
        persona_specific_suffix=(
            "Speak in steps a non-developer can follow. Keep each step "
            "to one sentence. If the answer would require reading code, "
            "say 'escalate to L2' and cite the runbook or log source "
            "they should capture first."
        ),
        min_citation_ratio=1.0,
    ),
    "l2": _persona(
        id="l2",
        display_name="L2 Support Engineer",
        tone="diagnostic, log-driven, runbook-oriented",
        depth="medium",
        avoid=(
            "speculative root-cause narratives",
            "architecture diagrams without an actionable path",
        ),
        emphasise=(
            "log signatures",
            "config keys",
            "service dependencies",
            "known issues and workarounds",
        ),
        persona_specific_suffix=(
            "Answer like a runbook: symptom, check, action, rollback. "
            "Call out the exact config key, env var, or feature flag to "
            "verify. If you would need to read code to answer, cite the "
            "file and escalate to L3."
        ),
        min_citation_ratio=1.0,
    ),
    "l3": _persona(
        id="l3",
        display_name="L3 / Platform Engineer",
        tone="deep-systems, cause-and-effect, data-anchored",
        depth="deep",
        avoid=(
            "user-friendly paraphrasing that loses precision",
            "answering without naming the exact subsystem",
        ),
        emphasise=(
            "subsystem boundaries",
            "timing / concurrency",
            "persistence and cache layers",
            "migration or backfill implications",
        ),
        persona_specific_suffix=(
            "Answer with subsystem-level precision: name the boundary, "
            "the failure mode, the blast radius. Cite the specific file "
            "+ line every time. When a claim is an inference, label it "
            "LOW confidence and say what evidence would flip it."
        ),
        min_citation_ratio=1.0,
    ),
}


def get(persona: PersonaId) -> PersonaProfile:
    """Return a PersonaProfile. Raises KeyError for unknown ids."""
    return PERSONAS[persona]


def safe_get(persona: str | None) -> PersonaProfile:
    """Return a PersonaProfile, falling back to DEFAULT_PERSONA on miss."""
    if persona in PERSONAS:
        return PERSONAS[persona]  # type: ignore[index]
    return PERSONAS[DEFAULT_PERSONA]


def min_ratio_for(persona: PersonaId, *, orphan_mode: bool) -> float:
    """Return the citation min-ratio for this persona under the current regime.

    Orphan mode enforces 1.0 for L1/L2/L3 and 0.9 for the three developer
    personas (per docs/TASK_KT_PRO_ORPHAN_MODE.md §2.1). Legacy mode (flag
    off) uses the profile's own `min_citation_ratio` — which happens to be
    the same numbers, so flipping the flag mostly affects refusal behaviour
    rather than the threshold itself.
    """
    profile = PERSONAS[persona]
    if orphan_mode:
        return 1.0 if persona in ("l1", "l2", "l3") else 0.9
    return profile.min_citation_ratio


def render_system_prompt(persona: PersonaId, *, tenant: str) -> str:
    """Return the persona's system prompt with {tenant} and persona fields filled."""
    profile = PERSONAS[persona]
    return profile.system_prompt.format(
        tenant=tenant,
        persona_display_name=profile.display_name,
        persona_tone=profile.tone,
        persona_avoid=", ".join(profile.avoid),
        persona_emphasise=", ".join(profile.emphasise),
    )
