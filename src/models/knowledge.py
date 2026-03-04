"""Knowledge store data models."""

from pydantic import BaseModel, Field
from typing import List, Optional
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
