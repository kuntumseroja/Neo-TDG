"""Crawl API routes."""

import uuid
import threading
from fastapi import APIRouter, Request, HTTPException
from pydantic import BaseModel
from typing import Optional

router = APIRouter()

# Simple in-memory job tracking
_jobs: dict = {}


class CrawlRequest(BaseModel):
    sln_path: str
    ingest_to_knowledge: bool = True


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

    job_id = str(uuid.uuid4())
    _jobs[job_id] = {"status": "running", "progress": 0.0, "files_processed": 0, "message": "Starting..."}

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
