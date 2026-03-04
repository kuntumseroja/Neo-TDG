"""Explain and trace API routes."""

from fastapi import APIRouter, Request, HTTPException
from pydantic import BaseModel
from typing import Optional

router = APIRouter()


class ExplainRequest(BaseModel):
    file_path: str
    component: str = ""
    method: Optional[str] = None


class TraceRequest(BaseModel):
    entry_point: str
    depth: int = 10


class ImpactRequest(BaseModel):
    component: str


@router.post("/explain")
async def explain(req: ExplainRequest, request: Request):
    """Explain a component (class/method) using RAG context."""
    from src.crawler.component_explainer import ComponentExplainer

    explainer = ComponentExplainer(
        llm=request.app.state.llm,
        vector_store=request.app.state.store,
    )

    if req.method:
        result = explainer.explain_method(req.file_path, req.method)
    else:
        result = explainer.explain_class(req.file_path, req.component)

    return result.model_dump()


@router.post("/trace")
async def trace_flow(req: TraceRequest, request: Request):
    """Trace a flow from an entry point."""
    from src.crawler.flow_explainer import FlowExplainer

    # Get crawl report from latest crawl if available
    crawl_report = getattr(request.app.state, "last_crawl_report", None)

    explainer = FlowExplainer(
        crawl_report=crawl_report,
        llm=request.app.state.llm,
    )

    result = explainer.explain_flow(req.entry_point)
    return result.model_dump()


@router.post("/impact")
async def impact_analysis(req: ImpactRequest, request: Request):
    """Analyze the impact of changing a component."""
    engine = request.app.state.rag_engine
    if not engine:
        raise HTTPException(status_code=503, detail="RAG engine not initialized")

    result = engine.impact_analysis(req.component)
    return result.model_dump()
