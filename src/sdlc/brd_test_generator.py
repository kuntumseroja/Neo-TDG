"""BRD-to-TestCase generator.

Parses a Business Requirements Document (PDF or DOCX), extracts
structured requirements via LLM, then generates traceable test cases
with full coverage. Results can be ingested into the knowledge store.
"""

import hashlib
import io
import logging
import re
from pathlib import Path
from typing import List, Optional, Tuple

from src.models.sdlc import (
    BRDRequirement,
    BRDTestReport,
    GeneratedTestCase,
)

logger = logging.getLogger(__name__)


# ── Document parsing ─────────────────────────────────────────────────

def extract_text_from_pdf(raw: bytes) -> str:
    """Extract text from PDF bytes via pypdf."""
    from pypdf import PdfReader

    reader = PdfReader(io.BytesIO(raw))
    pages = []
    for i, page in enumerate(reader.pages, 1):
        text = page.extract_text() or ""
        if text.strip():
            pages.append(f"[Page {i}]\n{text.strip()}")
    return "\n\n".join(pages)


def extract_text_from_docx(raw: bytes) -> str:
    """Extract text from DOCX bytes via python-docx.

    Extracts paragraphs AND tables (common in BRD docs for requirement
    matrices). Tables are rendered as pipe-delimited rows.
    """
    from docx import Document as DocxDocument

    doc = DocxDocument(io.BytesIO(raw))
    parts: list[str] = []

    for element in doc.element.body:
        tag = element.tag.split("}")[-1]  # strip namespace
        if tag == "p":
            # Paragraph
            para = element
            text_parts = []
            for run in para.iter():
                if run.text:
                    text_parts.append(run.text)
            line = "".join(text_parts).strip()
            if line:
                parts.append(line)
        elif tag == "tbl":
            # Table — render as pipe-delimited markdown
            for table in doc.tables:
                for row in table.rows:
                    cells = [cell.text.strip() for cell in row.cells]
                    parts.append("| " + " | ".join(cells) + " |")
                parts.append("")
                break  # only first unprocessed table per tbl element

    return "\n".join(parts)


def extract_text(filename: str, raw: bytes) -> str:
    """Route to the correct extractor based on file extension."""
    suffix = Path(filename).suffix.lower()
    if suffix == ".pdf":
        return extract_text_from_pdf(raw)
    elif suffix in (".docx", ".doc"):
        return extract_text_from_docx(raw)
    elif suffix in (".md", ".txt"):
        return raw.decode("utf-8", errors="ignore")
    else:
        raise ValueError(f"Unsupported file type: {suffix}")


# ── Prompts ──────────────────────────────────────────────────────────

_EXTRACT_REQUIREMENTS_PROMPT = """\
You are a senior QA analyst. Analyze the following Business Requirements Document (BRD) \
and extract ALL testable requirements.

For each requirement, output EXACTLY this format (one per block, separated by blank lines):

REQ_ID: REQ-001
TITLE: <short title>
DESCRIPTION: <detailed description of the requirement>
PRIORITY: <low|medium|high|critical>
CATEGORY: <functional|non-functional|security|performance|ux>

Rules:
- Number requirements sequentially: REQ-001, REQ-002, ...
- Include both functional AND non-functional requirements.
- Extract implicit requirements (e.g., "the system must validate..." implies a validation requirement).
- For security-related items, set CATEGORY to "security".
- For performance/SLA items, set CATEGORY to "performance".
- Be thorough — miss nothing.

BRD DOCUMENT:
{brd_text}
"""

_GENERATE_TESTCASES_PROMPT = """\
You are a senior QA test engineer. Generate comprehensive test cases for the following requirements.

For EACH requirement, generate 2-5 test cases covering: positive flow, negative flow, boundary/edge cases, \
and security (if applicable).

Output EXACTLY this format for each test case (separated by blank lines):

TC_ID: TC-001
REQ_ID: REQ-001
TITLE: <test case title>
TYPE: <functional|negative|boundary|security|performance>
PRIORITY: <low|medium|high|critical>
PRECONDITIONS: <what must be true before the test>
STEPS:
1. <step one>
2. <step two>
3. <step three>
EXPECTED: <expected result>

Rules:
- Number test cases sequentially: TC-001, TC-002, ...
- Each test case MUST reference a REQ_ID from the requirements list.
- Include at least one negative test per requirement.
- For security requirements, include penetration/injection test scenarios.
- Steps should be detailed enough for a junior tester to execute.
- Be thorough — aim for full coverage.

REQUIREMENTS:
{requirements_text}
"""


# ── Parsers for LLM output ──────────────────────────────────────────

def _parse_requirements(text: str) -> List[BRDRequirement]:
    """Parse LLM output into BRDRequirement objects."""
    reqs: list[BRDRequirement] = []
    # Split on REQ_ID: pattern
    blocks = re.split(r"(?=REQ_ID:\s*)", text.strip())
    for block in blocks:
        block = block.strip()
        if not block.startswith("REQ_ID:"):
            continue
        fields: dict = {}
        for line in block.split("\n"):
            line = line.strip()
            for key in ("REQ_ID", "TITLE", "DESCRIPTION", "PRIORITY", "CATEGORY"):
                if line.upper().startswith(key + ":"):
                    fields[key.lower()] = line.split(":", 1)[1].strip()
                    break
        if fields.get("req_id"):
            reqs.append(BRDRequirement(
                req_id=fields.get("req_id", ""),
                title=fields.get("title", ""),
                description=fields.get("description", ""),
                priority=fields.get("priority", "medium").lower(),
                category=fields.get("category", "functional").lower(),
            ))
    return reqs


def _parse_test_cases(text: str) -> List[GeneratedTestCase]:
    """Parse LLM output into GeneratedTestCase objects."""
    cases: list[GeneratedTestCase] = []
    blocks = re.split(r"(?=TC_ID:\s*)", text.strip())
    for block in blocks:
        block = block.strip()
        if not block.startswith("TC_ID:"):
            continue
        fields: dict = {}
        steps: list[str] = []
        in_steps = False
        for line in block.split("\n"):
            stripped = line.strip()
            if stripped.upper().startswith("STEPS:"):
                in_steps = True
                # Check if there's inline content after "STEPS:"
                rest = stripped.split(":", 1)[1].strip()
                if rest:
                    steps.append(rest)
                continue
            if in_steps:
                # Step lines start with a number or bullet
                if re.match(r"^\d+[\.\)]\s*", stripped):
                    steps.append(re.sub(r"^\d+[\.\)]\s*", "", stripped))
                    continue
                elif stripped.startswith("- "):
                    steps.append(stripped[2:])
                    continue
                else:
                    in_steps = False
            for key in ("TC_ID", "REQ_ID", "TITLE", "TYPE", "PRIORITY",
                        "PRECONDITIONS", "EXPECTED"):
                if stripped.upper().startswith(key + ":"):
                    fields[key.lower()] = stripped.split(":", 1)[1].strip()
                    break
        if fields.get("tc_id"):
            cases.append(GeneratedTestCase(
                tc_id=fields.get("tc_id", ""),
                requirement_id=fields.get("req_id", ""),
                title=fields.get("title", ""),
                preconditions=fields.get("preconditions", ""),
                steps=steps or [],
                expected_result=fields.get("expected", ""),
                priority=fields.get("priority", "medium").lower(),
                type=fields.get("type", "functional").lower(),
            ))
    return cases


# ── Main generator class ────────────────────────────────────────────

class BRDTestCaseGenerator:
    """Orchestrates: BRD text → requirements extraction → test case generation."""

    def __init__(self, llm, rag_engine=None):
        self.llm = llm
        self.rag_engine = rag_engine

    def extract_requirements(self, brd_text: str) -> List[BRDRequirement]:
        """Step 1: Extract structured requirements from BRD text."""
        if not self.llm:
            raise RuntimeError("LLM required for requirement extraction")

        # Truncate very long BRDs to fit context window
        max_chars = 12000
        if len(brd_text) > max_chars:
            logger.warning(
                "BRD text truncated from %d to %d chars for LLM",
                len(brd_text), max_chars,
            )
            brd_text = brd_text[:max_chars] + "\n\n[... truncated ...]"

        prompt = _EXTRACT_REQUIREMENTS_PROMPT.format(brd_text=brd_text)
        system = (
            "You are a senior QA analyst specializing in requirement analysis "
            "for enterprise tax/financial systems. Be thorough and precise."
        )

        logger.info("Extracting requirements from BRD (%d chars)", len(brd_text))
        raw = self.llm.generate(prompt, system)
        reqs = _parse_requirements(raw)
        logger.info("Extracted %d requirements", len(reqs))
        return reqs

    def generate_test_cases(
        self, requirements: List[BRDRequirement]
    ) -> List[GeneratedTestCase]:
        """Step 2: Generate test cases from extracted requirements."""
        if not self.llm:
            raise RuntimeError("LLM required for test case generation")
        if not requirements:
            return []

        # Build a text summary of requirements for the prompt
        req_lines = []
        for r in requirements:
            req_lines.append(
                f"{r.req_id}: [{r.category.upper()}] [{r.priority.upper()}] "
                f"{r.title}\n  {r.description}"
            )
        req_text = "\n\n".join(req_lines)

        prompt = _GENERATE_TESTCASES_PROMPT.format(requirements_text=req_text)
        system = (
            "You are a senior QA test engineer specializing in enterprise "
            "tax/financial systems. Generate comprehensive, executable test cases."
        )

        logger.info(
            "Generating test cases for %d requirements", len(requirements)
        )
        raw = self.llm.generate(prompt, system)
        cases = _parse_test_cases(raw)
        logger.info("Generated %d test cases", len(cases))
        return cases

    def build_report(
        self,
        filename: str,
        requirements: List[BRDRequirement],
        test_cases: List[GeneratedTestCase],
    ) -> BRDTestReport:
        """Build the full traceability report."""
        # Traceability matrix: req_id → [tc_ids]
        trace: dict[str, list[str]] = {}
        for tc in test_cases:
            trace.setdefault(tc.requirement_id, []).append(tc.tc_id)

        covered = sum(1 for r in requirements if r.req_id in trace)
        coverage = (covered / len(requirements) * 100) if requirements else 0.0

        return BRDTestReport(
            source_file=filename,
            requirements=requirements,
            test_cases=test_cases,
            traceability=trace,
            coverage_pct=round(coverage, 1),
        )

    def to_markdown(self, report: BRDTestReport) -> str:
        """Render the report as Markdown for display / download / ingest."""
        lines = [
            f"# QA Test Cases — {report.source_file}",
            "",
            f"> Generated by **Lumen.AI BRD-to-TestCase** | "
            f"Requirements: **{len(report.requirements)}** | "
            f"Test Cases: **{len(report.test_cases)}** | "
            f"Coverage: **{report.coverage_pct}%**",
            "",
            "---",
            "",
            "## Requirements",
            "",
        ]
        for r in report.requirements:
            lines.append(
                f"### {r.req_id}: {r.title}\n"
                f"- **Category:** {r.category}\n"
                f"- **Priority:** {r.priority}\n"
                f"- **Description:** {r.description}\n"
            )

        lines.append("---\n\n## Test Cases\n")
        for tc in report.test_cases:
            steps_md = "\n".join(f"   {i+1}. {s}" for i, s in enumerate(tc.steps))
            lines.append(
                f"### {tc.tc_id}: {tc.title}\n"
                f"- **Requirement:** {tc.requirement_id}\n"
                f"- **Type:** {tc.type} | **Priority:** {tc.priority}\n"
                f"- **Preconditions:** {tc.preconditions}\n"
                f"- **Steps:**\n{steps_md}\n"
                f"- **Expected Result:** {tc.expected_result}\n"
            )

        lines.append("---\n\n## Traceability Matrix\n")
        lines.append("| Requirement | Test Cases | Count |")
        lines.append("|---|---|---|")
        for r in report.requirements:
            tcs = report.traceability.get(r.req_id, [])
            tc_str = ", ".join(tcs) if tcs else "_none_"
            lines.append(f"| {r.req_id}: {r.title} | {tc_str} | {len(tcs)} |")

        return "\n".join(lines)

    def generate_full(
        self, filename: str, raw: bytes
    ) -> Tuple[BRDTestReport, str]:
        """End-to-end: file bytes → report + markdown.

        Returns (BRDTestReport, markdown_string).
        """
        text = extract_text(filename, raw)
        if not text.strip():
            raise ValueError(
                "No extractable text in the document. "
                "Scanned PDFs (image-only) require OCR first."
            )
        reqs = self.extract_requirements(text)
        if not reqs:
            raise ValueError(
                "Could not extract any requirements from the BRD. "
                "The document may not contain structured requirements."
            )
        cases = self.generate_test_cases(reqs)
        report = self.build_report(filename, reqs, cases)
        md = self.to_markdown(report)
        return report, md
