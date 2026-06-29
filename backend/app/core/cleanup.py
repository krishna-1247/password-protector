"""
cleanup.py
----------
Background thread that periodically deletes expired job temp directories.
Runs as a daemon so it never blocks server shutdown.
"""

from __future__ import annotations

import logging
import threading

logger = logging.getLogger(__name__)


class CleanupScheduler:
    """
    Wakes every ``interval_seconds`` and calls ``job_store.purge_expired``.
    Started once at application startup via the FastAPI lifespan hook.
    """

    def __init__(self, interval_seconds: int = 300, ttl_minutes: int = 30) -> None:
        self._interval = interval_seconds
        self._ttl = ttl_minutes
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        self._thread = threading.Thread(target=self._run, daemon=True, name="cleanup-scheduler")
        self._thread.start()
        logger.info(
            "Cleanup scheduler started (interval=%ds, TTL=%dmin)",
            self._interval,
            self._ttl,
        )

    def stop(self) -> None:
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=5)

    def _run(self) -> None:
        while not self._stop.wait(timeout=self._interval):
            try:
                from app.services.job_store import job_store

                purged = job_store.purge_expired(self._ttl)
                if purged:
                    logger.info("Cleanup: purged %d expired job(s)", purged)
            except Exception as exc:
                logger.error("Cleanup error: %s", exc)
