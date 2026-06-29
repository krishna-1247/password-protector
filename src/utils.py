"""
utils.py
--------
Utility helpers shared across the application.

Includes:
  - Sanitisation / validation of file-system paths.
  - A thread-safe progress counter.
  - CSV report writer.
  - Timing utilities.
"""

from __future__ import annotations

import csv
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import List

from src.logger import get_logger

logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class ProcessingResult:
    """Stores the outcome of encrypting a single PDF."""

    filename: str
    status: str          # "success" | "missing" | "failed" | "skipped"
    message: str = ""
    elapsed_ms: float = 0.0


@dataclass
class RunSummary:
    """Aggregate statistics for a processing run."""

    total: int = 0
    success: int = 0
    missing: int = 0
    failed: int = 0
    skipped: int = 0
    elapsed_sec: float = 0.0
    results: List[ProcessingResult] = field(default_factory=list)

    @property
    def processed(self) -> int:
        return self.success + self.failed + self.skipped

    def add(self, result: ProcessingResult) -> None:
        self.results.append(result)
        if result.status == "success":
            self.success += 1
        elif result.status == "missing":
            self.missing += 1
        elif result.status == "failed":
            self.failed += 1
        elif result.status == "skipped":
            self.skipped += 1

    def pretty(self) -> str:
        lines = [
            "=" * 50,
            "  PDF PASSWORD PROTECTOR -- SUMMARY",
            "=" * 50,
            f"  Total entries   : {self.total}",
            f"  Processed       : {self.processed}",
            f"  [OK] Encrypted  : {self.success}",
            f"  [--] Skipped    : {self.skipped}",
            f"  [!!] Missing    : {self.missing}",
            f"  [!!] Failed     : {self.failed}",
            f"  Time taken      : {self.elapsed_sec:.2f}s",
            "=" * 50,
        ]
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# Thread-safe counter (used by the multi-threaded processor)
# ---------------------------------------------------------------------------

class AtomicCounter:
    """An integer counter safe for concurrent increment from multiple threads."""

    def __init__(self, start: int = 0) -> None:
        self._value = start
        self._lock = threading.Lock()

    def increment(self, amount: int = 1) -> int:
        with self._lock:
            self._value += amount
            return self._value

    @property
    def value(self) -> int:
        with self._lock:
            return self._value


# ---------------------------------------------------------------------------
# CSV report writer
# ---------------------------------------------------------------------------

def write_csv_report(results: List[ProcessingResult], output_path: Path) -> None:
    """
    Persist processing results to a CSV file.

    Parameters
    ----------
    results:
        List of :class:`ProcessingResult` objects.
    output_path:
        Destination CSV file path; parent directories are created if absent.
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = ["filename", "status", "message", "elapsed_ms"]
    try:
        with output_path.open("w", newline="", encoding="utf-8") as fh:
            writer = csv.DictWriter(fh, fieldnames=fieldnames)
            writer.writeheader()
            for r in results:
                writer.writerow(
                    {
                        "filename": r.filename,
                        "status": r.status,
                        "message": r.message,
                        "elapsed_ms": f"{r.elapsed_ms:.1f}",
                    }
                )
        logger.info("CSV report saved -> %s", output_path)
    except OSError as exc:
        logger.error("Failed to write CSV report: %s", exc)


# ---------------------------------------------------------------------------
# Path helpers
# ---------------------------------------------------------------------------

def ensure_dirs(*paths: Path) -> None:
    """Create directories (and parents) if they do not exist."""
    for path in paths:
        path.mkdir(parents=True, exist_ok=True)
        logger.debug("Directory ready: %s", path)


def resolve_path(raw: str | Path) -> Path:
    """
    Expand environment variables and ``~`` in *raw*, then return an absolute
    :class:`~pathlib.Path`.
    """
    import os
    return Path(os.path.expandvars(os.path.expanduser(str(raw)))).resolve()


# ---------------------------------------------------------------------------
# Timing context manager
# ---------------------------------------------------------------------------

class Timer:
    """Simple wall-clock timer usable as a context manager."""

    def __init__(self) -> None:
        self._start: float = 0.0
        self.elapsed: float = 0.0

    def __enter__(self) -> "Timer":
        self._start = time.perf_counter()
        return self

    def __exit__(self, *_: object) -> None:
        self.elapsed = time.perf_counter() - self._start
