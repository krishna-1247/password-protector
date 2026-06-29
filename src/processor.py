"""
processor.py
------------
Multi-threaded batch processor that orchestrates reading the Excel mapping
and calling :class:`PdfEncryptor` for each entry.

Uses ``concurrent.futures.ThreadPoolExecutor`` which is ideal here because
the workload is I/O-bound (disk reads/writes) rather than CPU-bound.
"""

from __future__ import annotations

import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Callable, List, Optional

from src.excel_reader import ExcelRow
from src.pdf_encryptor import PdfEncryptor
from src.utils import ProcessingResult
from src.logger import get_logger

logger = get_logger(__name__)

ProgressCallback = Callable[[int, int, str], None]


class BatchProcessor:
    """
    Processes a list of :class:`ExcelRow` entries in parallel.

    Parameters
    ----------
    encryptor:
        A configured :class:`PdfEncryptor` instance.
    max_workers:
        Number of concurrent threads.  For SSDs, 4–8 is usually optimal;
        for spinning disks, 1–2 avoids seek thrashing.
    """

    def __init__(
        self,
        encryptor: PdfEncryptor,
        max_workers: int = 4,
    ) -> None:
        self._encryptor = encryptor
        self._max_workers = max_workers

    def run(
        self,
        rows: List[ExcelRow],
        progress_callback: Optional[ProgressCallback] = None,
        stop_event: Optional[threading.Event] = None,
    ) -> List[ProcessingResult]:
        """
        Encrypt all PDFs described by *rows*.

        Parameters
        ----------
        rows:
            Validated Excel rows; each contains a filename and password.
        progress_callback:
            ``(done, total, current_filename) -> None`` called after each
            file completes.
        stop_event:
            When set, processing stops after the current batch of futures
            completes (files already submitted to the pool will finish).

        Returns
        -------
        List[ProcessingResult]
            One result per input row, in completion order.
        """
        total = len(rows)
        results: List[ProcessingResult] = []
        done_count = 0
        lock = threading.Lock()

        logger.info("Starting batch: %d files, %d workers", total, self._max_workers)

        with ThreadPoolExecutor(max_workers=self._max_workers) as pool:
            future_to_row = {
                pool.submit(self._encryptor.encrypt, row.filename, row.password): row
                for row in rows
            }

            for future in as_completed(future_to_row):
                if stop_event and stop_event.is_set():
                    logger.warning("Stop requested — cancelling remaining futures.")
                    for f in future_to_row:
                        f.cancel()
                    break

                row = future_to_row[future]
                try:
                    result = future.result()
                except Exception as exc:
                    # Should not normally happen; encryptor catches its own errors
                    logger.error("Unhandled exception for '%s': %s", row.filename, exc)
                    result = ProcessingResult(row.filename, "failed", str(exc))

                with lock:
                    results.append(result)
                    done_count += 1
                    if progress_callback:
                        progress_callback(done_count, total, row.filename)

        logger.info("Batch complete: %d/%d processed", len(results), total)
        return results
