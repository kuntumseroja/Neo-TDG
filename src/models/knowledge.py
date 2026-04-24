"""Knowledge store data models."""

from pydantic import BaseModel, Field
from typing import List, Literal, Optional
from datetime import datetime


class ChunkMetadata(BaseModel):
    """Metadata attached to each stored chunk."""
    service_name: str = ""
    probis_domain: str = ""
    chunk_type: str = "general"  # overview|architecture|component|flow|dependency|endpoint|domain_model
    language: str = ""
    git_commit: str = ""
    last_updated: datetime = Field(default_factory=datetime.utcnow)
    source_file: str = ""
    heading_path: str = ""  # e.g., "## Architecture > ### Components"
    doc_id: str = ""  # Parent document identifier


class ChunkResult(BaseModel):
    """A single chunk returned from vector store query."""
    content: str
    metadata: ChunkMetadata = Field(default_factory=ChunkMetadata)
    score: float = 0.0
    source_file: str = ""
    chunk_id: str = ""


class SourceReference(BaseModel):
    """Reference to a source used in a RAG response."""
    file_path: str
    service_name: str = ""
    chunk_type: str = ""
    relevance_score: float = 0.0


class RAGResponse(BaseModel):
    """Response from the RAG query engine."""
    answer: str
    sources: List[SourceReference] = Field(default_factory=list)
    confidence: str = "medium"  # high|medium|low
    related_topics: List[str] = Field(default_factory=list)
    diagram: Optional[str] = None  # Mermaid source
    mode: str = "explain"
    conversation_id: Optional[str] = None
    # Persona that produced this answer (Phase 1; optional for legacy clients).
    persona: Optional[str] = None
    # Soft warnings surfaced by the pipeline (e.g. "low_citation_rate").
    warnings: List[str] = Field(default_factory=list)
    # Orphan-mode structured refusal. When refused=True, `answer` is a
    # human-readable markdown block and the fields below give the UI the
    # raw shape so it can render clickable hints.
    refused: bool = False
    refusal_reason: Optional[str] = None
    hints: List[dict] = Field(default_factory=list)
    suggested_prompts: List[str] = Field(default_factory=list)


PersonaId = Literal["architect", "developer", "tester", "l1", "l2", "l3"]


class QueryRequest(BaseModel):
    """Request to the RAG engine. Shared by the Streamlit UI and HTTP routes."""
    question: str
    mode: str = "explain"  # explain|find|trace|impact|test
    filters: Optional[dict] = None
    conversation_id: Optional[str] = None
    # Phase 1 — persona is optional; when six-persona flag is off the
    # engine ignores it and falls back to the legacy prompt.
    persona: Optional[PersonaId] = None
