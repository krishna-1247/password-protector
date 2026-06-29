"""
jobs.py
-------
FastAPI router for all job-related endpoints.

Routes
------
POST   /api/v1/upload           Upload PDFs + Excel; create job
POST   /api/v1/process/{jobId}  Start encryption (background)
GET    /api/v1/status/{jobId}   Poll job status + progress
GET    /api/v1/download/{jobId} Stream encrypted ZIP
DELETE /api/v1/cleanup/{jobId}  Manually delete temp files
"""

from __future__ import annotations

import re
import tempfile
import uuid
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, File, HTTPException, UploadFile
from fastapi.responses import FileResponse

from app.core.config import settings
from app.models.schemas import (
    CleanupResponse,
    ProcessRequest,
    StatusResponse,
    UploadResponse,
)
from app.services.encryption_service import run_encryption_job
from app.services.job_store import job_store

router = APIRouter(prefix="/api/v1", tags=["jobs"])

# Shared thread pool for background processing tasks
_executor = ThreadPoolExecutor(max_workers=4, thread_name_prefix="enc-worker")

# Allowed upload extensions
_ALLOWED_PDF_EXT = {".pdf"}
_ALLOWED_EXCEL_EXT = {".xlsx", ".xls", ".csv"}

# Filename sanitiser — keep only safe characters
_SAFE_NAME = re.compile(r"[^\w.\-]")


def _sanitise(name: str) -> str:
    """Strip unsafe characters from an uploaded filename."""
    name = Path(name).name  # prevent path traversal
    return _SAFE_NAME.sub("_", name)


def _validate_size(file: UploadFile, max_bytes: int) -> None:
    """Raise 413 if the declared content-length exceeds the limit."""
    if file.size and file.size > max_bytes:
        raise HTTPException(
            status_code=413,
            detail=f"File '{file.filename}' exceeds {settings.max_upload_mb} MB limit.",
        )


# ---------------------------------------------------------------------------
# POST /upload
# ---------------------------------------------------------------------------


@router.post("/upload", response_model=UploadResponse, status_code=201)
async def upload_files(
    pdfs: list[UploadFile] = File(..., description="One or more PDF files"),
    excel: UploadFile = File(..., description="Excel or CSV mapping file"),
) -> UploadResponse:
    """
    Accept multiple PDFs and one Excel/CSV file.
    Creates a job temp directory and saves uploads there.
    Returns a ``jobId`` for subsequent API calls.
    """
    # ── Validate Excel type ─────────────────────────────────────────────
    excel_ext = Path(excel.filename or "").suffix.lower()
    if excel_ext not in _ALLOWED_EXCEL_EXT:
        raise HTTPException(
            status_code=415,
            detail=f"Excel file must be .xlsx, .xls, or .csv (got '{excel_ext}').",
        )
    _validate_size(excel, settings.max_upload_bytes)

    # ── Validate PDF types ──────────────────────────────────────────────
    if not pdfs:
        raise HTTPException(status_code=400, detail="At least one PDF file is required.")
    if len(pdfs) > settings.max_pdf_count:
        raise HTTPException(
            status_code=400,
            detail=f"Too many PDFs (max {settings.max_pdf_count}).",
        )
    for pdf in pdfs:
        if Path(pdf.filename or "").suffix.lower() not in _ALLOWED_PDF_EXT:
            raise HTTPException(
                status_code=415,
                detail=f"Only PDF files are accepted (got '{pdf.filename}').",
            )
        _validate_size(pdf, settings.max_upload_bytes)

    # ── Create temp dir and job ─────────────────────────────────────────
    job_id = str(uuid.uuid4())
    tmp_root = Path(settings.tmp_root) if settings.tmp_root else None
    tmp_dir = Path(tempfile.mkdtemp(prefix=f"job-{job_id[:8]}-", dir=tmp_root))
    uploads_dir = tmp_dir / "uploads"
    uploads_dir.mkdir(parents=True, exist_ok=True)

    job = job_store.create(job_id, tmp_dir)

    # ── Save uploads ────────────────────────────────────────────────────
    safe_excel_name = _sanitise(excel.filename or "mapping.xlsx")
    excel_path = tmp_dir / safe_excel_name
    content = await excel.read()
    excel_path.write_bytes(content)

    saved_pdfs: list[str] = []
    for pdf in pdfs:
        safe_name = _sanitise(pdf.filename or "file.pdf")
        dest = uploads_dir / safe_name
        content = await pdf.read()
        dest.write_bytes(content)
        saved_pdfs.append(safe_name)

    # Store excel path on job for later
    job._excel_path = excel_path  # type: ignore[attr-defined]

    return UploadResponse(
        job_id=job_id,
        file_count=len(saved_pdfs),
        excel_filename=safe_excel_name,
        message=f"Uploaded {len(saved_pdfs)} PDF(s) and 1 Excel file. Ready to process.",
    )


# ---------------------------------------------------------------------------
# POST /process/{jobId}
# ---------------------------------------------------------------------------


@router.post("/process/{job_id}", status_code=202)
async def process_job(
    job_id: str,
    req: ProcessRequest = ProcessRequest(),
) -> dict:
    """
    Start the encryption pipeline for a previously uploaded job.
    Processing runs in a background thread — returns 202 Accepted immediately.
    """
    job = job_store.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail=f"Job '{job_id}' not found.")
    if job.status not in ("pending",):
        raise HTTPException(
            status_code=409,
            detail=f"Job is already '{job.status}' — cannot restart.",
        )

    excel_path: Path = getattr(job, "_excel_path", None)  # type: ignore[attr-defined]
    if excel_path is None or not excel_path.exists():
        raise HTTPException(status_code=400, detail="Excel file missing — re-upload.")

    # Launch in background thread pool (non-blocking)
    _executor.submit(
        run_encryption_job,
        job,
        excel_path,
        req.skip_encrypted,
        req.overwrite,
        req.max_workers,
    )

    return {"job_id": job_id, "status": "processing", "message": "Encryption started."}


# ---------------------------------------------------------------------------
# GET /status/{jobId}
# ---------------------------------------------------------------------------


@router.get("/status/{job_id}", response_model=StatusResponse)
async def get_status(job_id: str) -> StatusResponse:
    """Return current status, progress percentage, and statistics for a job."""
    job = job_store.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail=f"Job '{job_id}' not found.")

    return StatusResponse(
        job_id=job.job_id,
        status=job.status,
        progress=job.progress,
        done=job.done,
        total=job.total,
        stats=job.stats,
        error=job.error,
        created_at=job.created_at,
        completed_at=job.completed_at,
        results=job.results,
    )


# ---------------------------------------------------------------------------
# GET /download/{jobId}
# ---------------------------------------------------------------------------


@router.get("/download/{job_id}")
async def download_zip(job_id: str, background_tasks: BackgroundTasks) -> FileResponse:
    """
    Stream the encrypted ZIP file to the client.
    Schedules cleanup after the response is sent.
    """
    job = job_store.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail=f"Job '{job_id}' not found.")
    if job.status != "completed":
        raise HTTPException(
            status_code=409,
            detail=f"Job is '{job.status}' — download only available after completion.",
        )
    if job.zip_path is None or not job.zip_path.exists():
        raise HTTPException(
            status_code=404,
            detail="No encrypted PDFs were produced (all files may have been skipped/failed).",
        )

    # Schedule cleanup after response is sent
    background_tasks.add_task(_deferred_cleanup, job_id)

    return FileResponse(
        path=str(job.zip_path),
        media_type="application/zip",
        filename="encrypted_pdfs.zip",
    )


def _deferred_cleanup(job_id: str) -> None:
    """Called by BackgroundTasks after download response is sent."""
    job = job_store.get(job_id)
    if job:
        job.cleanup()
        # Keep job metadata in store (status/stats) but mark zip as deleted
        job.zip_path = None


# ---------------------------------------------------------------------------
# DELETE /cleanup/{jobId}
# ---------------------------------------------------------------------------


@router.delete("/cleanup/{job_id}", response_model=CleanupResponse)
async def cleanup_job(job_id: str) -> CleanupResponse:
    """Immediately delete all temporary files for a job."""
    job = job_store.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail=f"Job '{job_id}' not found.")

    deleted = job_store.delete(job_id)
    return CleanupResponse(
        job_id=job_id,
        message="Temporary files deleted." if deleted else "Nothing to delete.",
    )
