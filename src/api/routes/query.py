"""Query API routes."""

from fastapi import APIRouter, Request, HTTPException
from pydantic import BaseModel
from typing import Optional

router = APIRouter()


class QueryRequest(BaseModel):
    question: str
    mode: str = "explain"  # explain|find|trace|impact|test
    filters: Optional[dict] = None
    conversation_id: Optional[str] = None


class QueryResponse(BaseModel):
    answer: str
    sources: list = []
    confidence: str = "medium"
    related_topics: list = []
    diagram: Optional[str] = None
    conversation_id: Optional[str] = None


@router.post("/query", response_model=QueryResponse)
async def query(req: QueryRequest, request: Request):
    """Execute a RAG query against the knowledge base."""
    engine = request.app.state.rag_engine
    if not engine:
        raise HTTPException(status_code=503, detail="RAG engine not initialized (LLM unavailable)")

    result = engine.query(
        question=req.question,
        mode=req.mode,
        filters=req.filters,
        conversation_id=req.conversation_id,
    )

    return QueryResponse(
        answer=result.answer,
        sources=[s.model_dump() for s in result.sources],
        confidence=result.confidence,
        related_topics=result.related_topics,
        diagram=result.diagram,
        conversation_id=result.conversation_id,
    )
