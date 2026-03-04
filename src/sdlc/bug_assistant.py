"""Bug resolution assistant using RAG + flow analysis."""

import re
import logging
from typing import List, Optional

from src.models.sdlc import BugAnalysis, ProbableCause, FixSuggestion, TestCase

logger = logging.getLogger(__name__)


class BugAssistant:
    """Analyze bugs, suggest root causes, and recommend fixes."""

    def __init__(self, rag_engine=None, crawler=None):
        self.rag = rag_engine
        self.crawler = crawler

    def analyze_bug(
        self, description: str, stack_trace: str = None
    ) -> BugAnalysis:
        """
        Analyze a bug from description and optional stack trace.

        1. Parse stack trace to identify affected files/methods
        2. RAG query for related components and flows
        3. Identify probable root causes
        4. Suggest fixes with code locations
        5. Generate verification test cases
        """
        affected = []
        if stack_trace:
            affected = self._parse_stack_trace(stack_trace)

        # Build a comprehensive query
        query_parts = [f"Bug: {description}"]
        if affected:
            query_parts.append(f"Affected components: {', '.join(affected[:5])}")
        if stack_trace:
            # Include key lines from stack trace
            key_lines = [l.strip() for l in stack_trace.split("\n") if "at " in l][:5]
            query_parts.append(f"Stack trace: {'; '.join(key_lines)}")

        full_query = "\n".join(query_parts)

        # Query RAG for context
        causes = []
        fixes = []
        test_cases = []
        severity = "medium"
        summary = description[:200]

        if self.rag:
            try:
                # Get component context
                result = self.rag.query(
                    question=f"What components and flows are related to: {full_query}",
                    mode="find",
                )

                # Analyze for root cause
                cause_result = self.rag.query(
                    question=(
                        f"Given this bug report, what are the most likely root causes?\n\n"
                        f"{full_query}\n\n"
                        f"Context from knowledge base:\n{result.answer[:1000]}"
                    ),
                    mode="explain",
                )

                # Parse LLM response for structured data
                summary = self._extract_summary(cause_result.answer, description)
                causes = self._parse_causes(cause_result.answer, affected)
                severity = self._assess_severity(description, stack_trace, affected)

                # Get fix suggestions
                fix_result = self.rag.query(
                    question=(
                        f"Suggest specific code fixes for this bug:\n{full_query}\n\n"
                        f"Root cause analysis:\n{cause_result.answer[:800]}"
                    ),
                    mode="explain",
                )
                fixes = self._parse_fixes(fix_result.answer)

                # Generate test cases
                test_result = self.rag.query(
                    question=(
                        f"Suggest test cases to verify this bug is fixed:\n{description}\n"
                        f"Affected: {', '.join(affected[:5])}"
                    ),
                    mode="test",
                )
                test_cases = self._parse_test_cases(test_result.answer)

            except Exception as e:
                logger.error(f"RAG analysis failed: {e}")
                summary = f"Analysis incomplete (RAG error): {description[:200]}"

        if not causes:
            # Fallback: create basic cause from description
            causes = [ProbableCause(
                description=f"Issue in: {description[:100]}",
                confidence=0.5,
                component=affected[0] if affected else "unknown",
            )]

        return BugAnalysis(
            summary=summary,
            affected_components=affected,
            probable_causes=causes,
            severity=severity,
            suggested_fixes=fixes,
            test_cases=test_cases,
        )

    def _parse_stack_trace(self, stack_trace: str) -> List[str]:
        """Extract affected file paths and method names from a stack trace."""
        components = []

        # .NET stack trace pattern: at Namespace.Class.Method(params) in file:line
        for match in re.finditer(
            r"at\s+([\w.]+)\s*\(", stack_trace
        ):
            full_name = match.group(1)
            # Take last two segments (Class.Method)
            parts = full_name.split(".")
            if len(parts) >= 2:
                components.append(f"{parts[-2]}.{parts[-1]}")
            else:
                components.append(full_name)

        # File paths
        for match in re.finditer(r"in\s+([^\s:]+\.cs)", stack_trace):
            components.append(match.group(1))

        return list(dict.fromkeys(components))[:10]  # Deduplicate, max 10

    def _extract_summary(self, analysis: str, fallback: str) -> str:
        """Extract a summary from the LLM analysis."""
        # Take first sentence or paragraph
        lines = analysis.strip().split("\n")
        for line in lines:
            line = line.strip().strip("*-# ")
            if len(line) > 20:
                return line[:200]
        return fallback[:200]

    def _parse_causes(self, analysis: str, affected: List[str]) -> List[ProbableCause]:
        """Parse probable causes from LLM analysis text."""
        causes = []
        lines = analysis.split("\n")
        for line in lines:
            line = line.strip().strip("*- ")
            if not line or len(line) < 10:
                continue
            # Look for numbered or bulleted cause descriptions
            if re.match(r"^\d+[\.\)]|^-|^\*", line) or "cause" in line.lower():
                component = ""
                for comp in affected:
                    if comp.lower() in line.lower():
                        component = comp
                        break
                causes.append(ProbableCause(
                    description=line[:200],
                    confidence=0.6,
                    component=component,
                ))
                if len(causes) >= 5:
                    break
        return causes

    def _parse_fixes(self, analysis: str) -> List[FixSuggestion]:
        """Parse fix suggestions from LLM analysis text."""
        fixes = []
        lines = analysis.split("\n")
        for line in lines:
            line = line.strip().strip("*- ")
            if not line or len(line) < 10:
                continue
            if re.match(r"^\d+[\.\)]|^-|^\*", line) or "fix" in line.lower():
                fixes.append(FixSuggestion(
                    description=line[:200],
                    risk_level="medium",
                ))
                if len(fixes) >= 5:
                    break
        return fixes

    def _parse_test_cases(self, analysis: str) -> List[TestCase]:
        """Parse test case suggestions from LLM analysis text."""
        cases = []
        lines = analysis.split("\n")
        for line in lines:
            line = line.strip().strip("*- ")
            if not line or len(line) < 10:
                continue
            if re.match(r"^\d+[\.\)]|^-|^\*|^test", line, re.IGNORECASE):
                cases.append(TestCase(
                    name=line[:80],
                    description=line[:200],
                    type="unit",
                ))
                if len(cases) >= 5:
                    break
        return cases

    @staticmethod
    def _assess_severity(
        description: str, stack_trace: Optional[str], affected: List[str]
    ) -> str:
        """Assess bug severity from signals."""
        desc_lower = description.lower()
        critical_keywords = ["crash", "data loss", "security", "production", "outage", "corruption"]
        high_keywords = ["error", "exception", "fail", "broken", "timeout"]

        if any(kw in desc_lower for kw in critical_keywords):
            return "critical"
        if stack_trace and len(affected) > 3:
            return "high"
        if any(kw in desc_lower for kw in high_keywords):
            return "high"
        return "medium"
