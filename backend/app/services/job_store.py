"""
job_store.py
------------
Thread-safe in-memory job registry.

No database is used. All state is held in a plain Python dict protected by
a threading.Lock. This is appropriate because:
- FastAPI runs in a single process (Uvicorn with one worker by default)
- Processing is offloaded to ThreadPoolExecutor, not separate processes
- State never needs to survive a server restart (jobs are ephemeral)
"""

from __future__ import annotations

import shutil
import threading
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Literal

from app.models.schemas import FileResult, JobStats

JobStatus = Literal["pending", "processing", "completed", "failed"]


@dataclass
class JobState:
    """Full internal state of one encryption job."""

    job_id: str
    status: JobStatus = "pending"

    # Progress tracking
    progress: int = 0  # 0–100
    done: int = 0
    total: int = 0

    # Statistics
    stats: JobStats = field(default_factory=JobStats)
    results: list[FileResult] = field(default_factory=list)

    # Paths (all inside a single temp dir)
    tmp_dir: Path | None = None
    input_dir: Path | None = None
    output_dir: Path | None = None
    zip_path: Path | None = None

    # Metadata
    created_at: datetime = field(default_factory=datetime.utcnow)
    completed_at: datetime | None = None
    error: str | None = None

    # Internal lock for per-job progress updates
    _lock: threading.Lock = field(default_factory=threading.Lock, repr=False)

    def update_progress(self, done: int, total: int, filename: str) -> None:
        with self._lock:
            self.done = done
            self.total = total
            self.progress = int(done / total * 100) if total else 0

    def mark_completed(self, stats: JobStats, results: list[FileResult]) -> None:
        with self._lock:
            self.status = "completed"
            self.progress = 100
            self.stats = stats
            self.results = results
            self.completed_at = datetime.utcnow()

    def mark_failed(self, error: str) -> None:
        with self._lock:
            self.status = "failed"
            self.error = error
            self.completed_at = datetime.utcnow()

    def cleanup(self) -> bool:
        """Delete the temp directory. Returns True if deleted."""
        if self.tmp_dir and self.tmp_dir.exists():
            try:
                shutil.rmtree(self.tmp_dir)
                return True
            except OSError:
                return False
        return False


class JobStore:
    """
    Global in-memory store for all active jobs.
    Thread-safe via a single store-level lock for registry mutations;
    per-job progress updates use per-job locks.
    """

    def __init__(self) -> None:
        self._jobs: dict[str, JobState] = {}
        self._lock = threading.Lock()

    def create(self, job_id: str, tmp_dir: Path) -> JobState:
        state = JobState(
            job_id=job_id,
            tmp_dir=tmp_dir,
            input_dir=tmp_dir / "uploads",
            output_dir=tmp_dir / "encrypted",
        )
        with self._lock:
            self._jobs[job_id] = state
        return state

    def get(self, job_id: str) -> JobState | None:
        with self._lock:
            return self._jobs.get(job_id)

    def delete(self, job_id: str) -> bool:
        with self._lock:
            job = self._jobs.pop(job_id, None)
        if job:
            job.cleanup()
            return True
        return False

    def all_jobs(self) -> list[JobState]:
        with self._lock:
            return list(self._jobs.values())

    def purge_expired(self, ttl_minutes: int) -> int:
        """Remove jobs older than ttl_minutes. Returns count purged."""
        from datetime import timedelta

        cutoff = datetime.utcnow() - timedelta(minutes=ttl_minutes)
        expired = []
        with self._lock:
            for jid, job in self._jobs.items():
                # Only purge completed/failed jobs; keep pending/processing
                if job.status in ("completed", "failed") and job.created_at < cutoff:
                    expired.append(jid)
            for jid in expired:
                job = self._jobs.pop(jid)
                job.cleanup()
        return len(expired)


# Singleton — imported by routers and services
job_store = JobStore()
