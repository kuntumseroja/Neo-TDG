"""Pydantic data models for Neo-TDG."""

from .knowledge import ChunkMetadata, ChunkResult, SourceReference, RAGResponse
from .crawler import (
    CrawlReport, ProjectInfo, EndpointInfo, SchedulerInfo,
    IntegrationPoint, ConsumerInfo, UIComponent, DataModel, PackageRef,
)
from .flow import FlowExplanation, FlowStep
from .sdlc import (
    BugAnalysis, ProbableCause, FixSuggestion, TestCase,
    EdgeCase, ValidationReport, Violation,
)

__all__ = [
    "ChunkMetadata", "ChunkResult", "SourceReference", "RAGResponse",
    "CrawlReport", "ProjectInfo", "EndpointInfo", "SchedulerInfo",
    "IntegrationPoint", "ConsumerInfo", "UIComponent", "DataModel", "PackageRef",
    "FlowExplanation", "FlowStep",
    "BugAnalysis", "ProbableCause", "FixSuggestion", "TestCase",
    "EdgeCase", "ValidationReport", "Violation",
]
