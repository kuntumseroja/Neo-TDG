"""Knowledge store management API routes."""

import threading
from fastapi import APIRouter, Request, HTTPException
from pydantic import BaseModel
from typing import Optional

router = APIRouter()


class IngestRequest(BaseModel):
    path: str  # File or directory path
    metadata: dict = {}
    doc_id: Optional[str] = None


class RebuildRequest(BaseModel):
    docs_dir: str
    metadata: dict = {}


@router.get("/knowledge/stats")
async def knowledge_stats(request: Request):
    """Get knowledge store statistics."""
    store = request.app.state.store
    return store.get_stats()


@router.post("/knowledge/ingest")
async def ingest_document(req: IngestRequest, request: Request):
    """Ingest a markdown file or directory into the knowledge store."""
    pipeline = request.app.state.pipeline
    from pathlib import Path

    path = Path(req.path)
    if path.is_file():
        chunks = pipeline.ingest_markdown_file(
            str(path), req.metadata, req.doc_id,
        )
        return {"status": "ok", "chunks_created": chunks}
    elif path.is_dir():
        result = pipeline.ingest_markdown_directory(str(path), metadata=req.metadata)
        return {"status": "ok", **result}
    else:
        raise HTTPException(status_code=404, detail=f"Path not found: {req.path}")


@router.post("/knowledge/rebuild")
async def rebuild_knowledge(req: RebuildRequest, request: Request):
    """Rebuild the knowledge store from scratch."""
    pipeline = request.app.state.pipeline

    def run_rebuild():
        pipeline.full_rebuild(req.docs_dir, metadata=req.metadata)

    thread = threading.Thread(target=run_rebuild, daemon=True)
    thread.start()

    return {"status": "started", "message": "Rebuild in progress"}


@router.delete("/knowledge/document/{doc_id}")
async def delete_document(doc_id: str, request: Request):
    """Delete a document from the knowledge store."""
    store = request.app.state.store
    success = store.delete_document(doc_id)
    if success:
        return {"status": "ok", "deleted": doc_id}
    raise HTTPException(status_code=404, detail=f"Document not found: {doc_id}")


@router.get("/knowledge/documents")
async def list_documents(request: Request):
    """List all document IDs in the knowledge store."""
    store = request.app.state.store
    return {"documents": store.get_all_doc_ids()}
