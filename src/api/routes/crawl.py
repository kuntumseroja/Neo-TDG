"""Crawl API routes."""

import logging
import uuid
import threading
from pathlib import Path
from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import List, Optional

from src.ops import sandbox

logger = logging.getLogger(__name__)

router = APIRouter()

# Simple in-memory job tracking
_jobs: dict = {}


class CrawlRequest(BaseModel):
    sln_path: str
    ingest_to_knowledge: bool = True
    # Phase 2 — build per-persona DOCX bundle after crawl completes. Only
    # honoured when `kt_pro.docx_bundle.enabled` is true in config.yaml;
    # otherwise ignored silently (keeps old clients safe).
    build_kt_bundle: bool = False


def _docx_bundle_enabled(config: dict) -> bool:
    cfg = config or {}
    entry = (cfg.get("kt_pro") or {}).get("docx_bundle") or {}
    return bool(entry.get("enabled", False))


class CrawlStatusResponse(BaseModel):
    job_id: str
    status: str
    progress: float = 0.0
    files_processed: int = 0
    message: str = ""


@router.post("/crawl")
async def start_crawl(req: CrawlRequest, request: Request):
    """Start crawling a .sln solution."""
    crawler = request.app.state.crawler
    pipeline = request.app.state.pipeline
    rag_engine = getattr(request.app.state, "rag_engine", None)
    config = getattr(request.app.state, "config", {}) or {}
    tenant = (config.get("kt_pro") or {}).get("tenant", "CoreTax")

    job_id = str(uuid.uuid4())
    _jobs[job_id] = {
        "status": "running", "progress": 0.0, "files_processed": 0,
        "message": "Starting...", "artefacts": [],
    }

    def run_crawl():
        try:
            def progress_cb(current, total, name):
                _jobs[job_id]["progress"] = current / total if total else 0
                _jobs[job_id]["files_processed"] = current
                _jobs[job_id]["message"] = f"Processing: {name}"

            report = crawler.crawl(req.sln_path, progress_callback=progress_cb)
            _jobs[job_id]["message"] = f"Crawled {len(report.projects)} projects"

            if req.ingest_to_knowledge and pipeline:
                _jobs[job_id]["message"] = "Ingesting to knowledge store..."
                pipeline.ingest_crawl_report(report)

            if req.build_kt_bundle and _docx_bundle_enabled(config):
                try:
                    _jobs[job_id]["message"] = "Building KT bundle..."
                    from src.crawler.persona_composer import compose_all
                    out_dir = sandbox.context().paths.knowledge_root.parent / "kt_bundles" / job_id
                    produced = compose_all(
                        report=report,
                        validation=None,
                        tenant=tenant,
                        out_dir=str(out_dir),
                        rag_engine=rag_engine,
                    )
                    _jobs[job_id]["artefacts"] = [str(p) for p in produced]
                except Exception as bundle_err:
                    logger.warning("KT bundle build failed: %s", bundle_err)
                    _jobs[job_id]["bundle_error"] = str(bundle_err)

            _jobs[job_id]["status"] = "completed"
            _jobs[job_id]["progress"] = 1.0
            _jobs[job_id]["result"] = report.model_dump()
        except Exception as e:
            _jobs[job_id]["status"] = "failed"
            _jobs[job_id]["message"] = str(e)

    thread = threading.Thread(target=run_crawl, daemon=True)
    thread.start()

    return {"job_id": job_id, "status": "started"}


@router.get("/crawl/{job_id}/status", response_model=CrawlStatusResponse)
async def crawl_status(job_id: str):
    """Get the status of a crawl job."""
    if job_id not in _jobs:
        raise HTTPException(status_code=404, detail="Job not found")
    job = _jobs[job_id]
    return CrawlStatusResponse(
        job_id=job_id,
        status=job["status"],
        progress=job["progress"],
        files_processed=job["files_processed"],
        message=job["message"],
    )


@router.get("/crawl/{job_id}/result")
async def crawl_result(job_id: str):
    """Get the result of a completed crawl job."""
    if job_id not in _jobs:
        raise HTTPException(status_code=404, detail="Job not found")
    job = _jobs[job_id]
    if job["status"] != "completed":
        raise HTTPException(status_code=400, detail=f"Job status: {job['status']}")
    return job.get("result", {})


@router.get("/crawl/{job_id}/artefacts")
async def crawl_artefacts(job_id: str):
    """List the KT-bundle artefacts produced by a completed crawl job."""
    if job_id not in _jobs:
        raise HTTPException(status_code=404, detail="Job not found")
    job = _jobs[job_id]
    return {
        "artefacts": job.get("artefacts", []),
        "bundle_error": job.get("bundle_error"),
    }


@router.get("/crawl/{job_id}/artefact/{filename}")
async def crawl_artefact_download(job_id: str, filename: str):
    """Stream a single KT-bundle artefact back to the caller."""
    if job_id not in _jobs:
        raise HTTPException(status_code=404, detail="Job not found")
    job = _jobs[job_id]
    artefacts: List[str] = job.get("artefacts", []) or []
    for path_str in artefacts:
        path = Path(path_str)
        if path.name == filename and path.exists():
            return FileResponse(str(path), filename=path.name)
    raise HTTPException(status_code=404, detail="Artefact not found")
