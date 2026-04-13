"""SDLC acceleration data models."""

from pydantic import BaseModel, Field
from typing import List, Optional
from .flow import FlowExplanation


class ProbableCause(BaseModel):
    """A probable cause for a bug."""
    description: str
    confidence: float = 0.0  # 0.0-1.0
    component: str = ""
    file: str = ""
    line: int = 0


class FixSuggestion(BaseModel):
    """Suggested fix for a bug."""
    description: str
    code_location: str = ""
    suggested_change: str = ""
    risk_level: str = "medium"  # low|medium|high


class BugAnalysis(BaseModel):
    """Complete bug analysis result."""
    summary: str
    affected_components: List[str] = Field(default_factory=list)
    probable_causes: List[ProbableCause] = Field(default_factory=list)
    affected_flow: Optional[FlowExplanation] = None
    severity: str = "medium"  # low|medium|high|critical
    suggested_fixes: List[FixSuggestion] = Field(default_factory=list)
    test_cases: List["TestCase"] = Field(default_factory=list)


class TestCase(BaseModel):
    """Generated test case."""
    name: str
    description: str = ""
    type: str = "unit"  # unit|integration|edge_case
    code: str = ""  # C# test code
    component_under_test: str = ""


class EdgeCase(BaseModel):
    """An edge case identified for testing."""
    name: str
    description: str = ""
    input_scenario: str = ""
    expected_behavior: str = ""
    component: str = ""


# ── QA / BRD-to-TestCase models ────────────────────────────────────────


class BRDRequirement(BaseModel):
    """A single requirement extracted from a BRD document."""
    req_id: str = ""
    title: str = ""
    description: str = ""
    priority: str = "medium"  # low|medium|high|critical
    category: str = ""  # functional|non-functional|security|performance|ux


class GeneratedTestCase(BaseModel):
    """A test case generated from a BRD requirement."""
    tc_id: str = ""
    requirement_id: str = ""
    title: str = ""
    preconditions: str = ""
    steps: List[str] = Field(default_factory=list)
    expected_result: str = ""
    priority: str = "medium"
    type: str = "functional"  # functional|negative|boundary|security|performance
    status: str = "draft"  # draft|review|approved


class BRDTestReport(BaseModel):
    """Full report: BRD → Requirements → Test Cases."""
    source_file: str = ""
    requirements: List[BRDRequirement] = Field(default_factory=list)
    test_cases: List[GeneratedTestCase] = Field(default_factory=list)
    traceability: dict = Field(default_factory=dict)  # req_id → [tc_ids]
    coverage_pct: float = 0.0


class Violation(BaseModel):
    """Architecture rule violation."""
    rule: str
    severity: str = "warning"  # info|warning|error
    file: str = ""
    description: str = ""
    suggested_fix: str = ""


class ValidationReport(BaseModel):
    """Architecture validation report."""
    total_rules_checked: int = 0
    violations: List[Violation] = Field(default_factory=list)
    passed: int = 0
    failed: int = 0
    warnings: int = 0
