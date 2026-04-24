"""Paragraph-level citation validator for RAG answers.

Splits an answer into paragraphs and checks each one for at least one valid
citation of the form:

  * `[src/foo/Bar.cs:L12]`     - file with single line
  * `[src/foo/Bar.cs:L12-L34]` - file with line range
  * `[doc §3.2]`                - document section reference

When the ratio of cited paragraphs drops below the persona's minimum, the
orchestrator (query_engine) retries once with an explicit "add citations"
nudge. If the retry also fails and the persona has
`refuse_without_evidence=True`, we return a structured refusal pointing the
user at the files that were retrieved (so "I don't know" still surfaces the
pile of documents worth reading).

See docs/TASK_KT_PRO_UPGRADE.md §1.5 and
docs/TASK_KT_PRO_ORPHAN_MODE.md §2.1.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Iterable


# A citation is either:
#   [something:L12]          or [something:L12-L34]
#   [doc §3.2]               (section numbers can have dotted depth)
#
# The "something" part is deliberately loose — file paths contain slashes,
# dots, dashes. We require at least one non-`]` character plus `:L<digits>`.
_FILE_CITE = r"\[[^\]\n]+?:L\d+(?:-L\d+)?\]"
_DOC_CITE = r"\[doc §[\d.]+\]"
CITE_PATTERN = re.compile(f"(?:{_FILE_CITE})|(?:{_DOC_CITE})")


@dataclass
class ValidationResult:
    """Outcome of validating a single answer."""

    ok: bool
    paragraphs_total: int
    paragraphs_cited: int
    reasons: list[str] = field(default_factory=list)

    @property
    def ratio(self) -> float:
        return (
            self.paragraphs_cited / self.paragraphs_total
            if self.paragraphs_total
            else 0.0
        )


@dataclass
class Refusal:
    """Structured refusal returned when evidence is insufficient.

    Serialises to a dict matching the shape in
    docs/TASK_KT_PRO_ORPHAN_MODE.md §2.1 so the UI can render clickable
    hints rather than a free-text "sorry I don't know".
    """

    reason: str
    hints: list[dict]
    suggested_prompts: list[str]

    def to_dict(self) -> dict:
        return {
            "answer": None,
            "refused": True,
            "reason": self.reason,
            "hints": self.hints,
            "suggested_prompts": self.suggested_prompts,
        }

    def to_markdown(self) -> str:
        """Render the refusal as a markdown block — safe for chat UIs that
        haven't yet been updated to render `refused=True` responses natively.
        """
        lines = [
            "**I don't have grounded evidence for this.**",
            "",
            f"_{self.reason}_",
            "",
        ]
        if self.hints:
            lines.append("**Files most likely relevant:**")
            for h in self.hints:
                file = h.get("file") or h.get("section", "?")
                why = h.get("why", "")
                ref = f"`{file}`"
                if why:
                    ref += f" — {why}"
                lines.append(f"- {ref}")
            lines.append("")
        if self.suggested_prompts:
            lines.append("**Try asking:**")
            for p in self.suggested_prompts:
                lines.append(f"- {p}")
        return "\n".join(lines)


def _split_paragraphs(text: str) -> list[str]:
    """Split answer into non-trivial paragraphs.

    Skips code fences (```...```) entirely — citations aren't expected
    inside them, and a code block full of an XML config shouldn't count as
    an uncited paragraph.
    """
    if not text:
        return []

    # Strip fenced code blocks before splitting so they don't create false
    # "uncited" paragraphs.
    fenced = re.sub(r"```.*?```", " ", text, flags=re.DOTALL)
    parts = re.split(r"\n\s*\n", fenced.strip())

    out: list[str] = []
    for p in parts:
        # Ignore stub headings / separator lines.
        stripped = p.strip()
        if not stripped:
            continue
        # A heading alone ("## Something") carries no factual claim; skip.
        if re.fullmatch(r"#+\s*\S.*", stripped) and "\n" not in stripped:
            continue
        # A bulleted list counts as one paragraph's worth of claims: we
        # want each bullet to cite, so explode list items into separate
        # paragraphs.
        if re.match(r"^\s*[-*+]\s", stripped) or re.match(r"^\s*\d+\.\s", stripped):
            for line in stripped.splitlines():
                line = line.strip()
                if line and not re.fullmatch(r"#+\s*.*", line):
                    out.append(line)
            continue
        out.append(stripped)
    return out


def _has_citation(paragraph: str) -> bool:
    return bool(CITE_PATTERN.search(paragraph))


def validate(answer: str, *, min_ratio: float = 0.7) -> ValidationResult:
    """Validate an answer's paragraph-level citation coverage.

    Args:
        answer: The LLM output, as a markdown string.
        min_ratio: Minimum fraction of paragraphs that must carry a
            citation. Values >= 1.0 require every paragraph to cite.

    Returns:
        A `ValidationResult`. `ok=True` iff `ratio >= min_ratio` (and
        there is at least one paragraph).
    """
    paragraphs = _split_paragraphs(answer)
    total = len(paragraphs)
    if total == 0:
        return ValidationResult(
            ok=False,
            paragraphs_total=0,
            paragraphs_cited=0,
            reasons=["empty_answer"],
        )

    cited = 0
    reasons: list[str] = []
    for i, p in enumerate(paragraphs):
        if _has_citation(p):
            cited += 1
        else:
            # Truncate for log-friendliness.
            preview = p[:80].replace("\n", " ")
            reasons.append(f"paragraph_{i}_uncited: {preview!r}")

    ratio = cited / total
    return ValidationResult(
        ok=ratio >= min_ratio,
        paragraphs_total=total,
        paragraphs_cited=cited,
        reasons=reasons,
    )


def build_refusal(chunks: Iterable, *, question: str) -> Refusal:
    """Build a structured refusal from the retrieved chunks.

    Uses the chunks the retrieval pipeline found - even when the LLM
    couldn't stitch them into a cited answer, the inheritor team can still
    benefit from "here's where to look".
    """
    hints: list[dict] = []
    seen: set[str] = set()
    for chunk in chunks:
        source = getattr(chunk, "source_file", "") or (
            getattr(chunk, "metadata", None)
            and getattr(chunk.metadata, "source_file", "")
        ) or ""
        if not source or source in seen:
            continue
        seen.add(source)

        service = ""
        chunk_type = ""
        meta = getattr(chunk, "metadata", None)
        if meta is not None:
            service = getattr(meta, "service_name", "") or ""
            chunk_type = getattr(meta, "chunk_type", "") or ""

        why_bits = []
        if chunk_type:
            why_bits.append(f"{chunk_type} chunk")
        if service:
            why_bits.append(f"service {service}")
        why = " · ".join(why_bits) if why_bits else "matched your query"

        hints.append({"file": source, "why": why})
        if len(hints) >= 5:
            break

    suggested = _build_suggested_prompts(question, hints)

    return Refusal(
        reason=(
            "Insufficient grounded evidence. The retrieved context did "
            "not contain enough citeable material to answer without "
            "speculating. The files below are the top candidates — open "
            "one to anchor a follow-up question."
        ),
        hints=hints,
        suggested_prompts=suggested,
    )


def _build_suggested_prompts(question: str, hints: list[dict]) -> list[str]:
    if not hints:
        return [
            f"Rephrase more narrowly: {question[:80]}",
            "Ingest more documentation into the knowledge base.",
        ]
    top_file = hints[0]["file"]
    out = [
        f"Show me the code in `{top_file}` that relates to my question.",
        f"Summarise what `{top_file}` does, citing its methods.",
    ]
    if len(hints) > 1:
        out.append(
            f"Compare `{top_file}` with `{hints[1]['file']}` — how do they interact?"
        )
    return out
