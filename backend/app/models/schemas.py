"""
schemas.py
----------
Pydantic response/request models for the FastAPI job API.
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel

JobStatus = Literal["pending", "processing", "completed", "failed"]


class UploadResponse(BaseModel):
    job_id: str
    file_count: int
    excel_filename: str
    message: str


class ProcessRequest(BaseModel):
    skip_encrypted: bool = True
    overwrite: bool = True
    max_workers: int = 4


class FileResult(BaseModel):
    filename: str
    status: Literal["success", "missing", "failed", "skipped"]
    message: str
    elapsed_ms: float


class JobStats(BaseModel):
    total: int = 0
    success: int = 0
    missing: int = 0
    failed: int = 0
    skipped: int = 0
    elapsed_sec: float = 0.0


class StatusResponse(BaseModel):
    job_id: str
    status: JobStatus
    progress: int  # 0–100
    done: int
    total: int
    stats: JobStats
    error: str | None = None
    created_at: datetime
    completed_at: datetime | None = None
    results: list[FileResult] = []


class CleanupResponse(BaseModel):
    job_id: str
    message: str
