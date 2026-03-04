"""Flow explanation data models."""

from pydantic import BaseModel, Field
from typing import List, Optional


class FlowStep(BaseModel):
    """A single step in a flow trace."""
    order: int
    component: str
    file: str = ""
    line: int = 0
    action: str = ""
    type: str = ""  # http_entry|command|handler|domain_logic|repository|event|consumer


class FlowExplanation(BaseModel):
    """Complete flow explanation with steps, diagram, and narrative."""
    title: str
    steps: List[FlowStep] = Field(default_factory=list)
    diagram: str = ""  # Mermaid sequence diagram source
    explanation: str = ""
    entry_point: str = ""


class ComponentExplanation(BaseModel):
    """Explanation of a single component (class/method)."""
    name: str
    type: str = ""  # class|method|handler|controller|consumer
    file: str = ""
    explanation: str = ""
    business_rules: List[str] = Field(default_factory=list)
    domain_events: List[str] = Field(default_factory=list)
    dependencies: List[str] = Field(default_factory=list)
    diagram: Optional[str] = None


class ValidationRule(BaseModel):
    """A business validation rule extracted from code."""
    name: str
    description: str = ""
    field: str = ""
    condition: str = ""
    file: str = ""
    line: int = 0
