"""
encryption_service.py
---------------------
Bridges the existing BatchProcessor / PdfEncryptor with the web job context.

Runs synchronously inside a ThreadPoolExecutor worker thread so FastAPI's
event loop is never blocked.
"""

from __future__ import annotations

from pathlib import Path

from app.models.schemas import FileResult, JobStats
from app.services.job_store import JobState
from app.services.zip_service import create_zip
from src.excel_reader import ExcelReader
from src.pdf_encryptor import PdfEncryptor
from src.processor import BatchProcessor
from src.utils import ProcessingResult, RunSummary, Timer
from src.logger import get_logger

logger = get_logger(__name__)


def run_encryption_job(
    job: JobState,
    excel_path: Path,
    skip_encrypted: bool = True,
    overwrite: bool = True,
    max_workers: int = 4,
) -> None:
    """
    Execute the full encryption pipeline for a job.

    This function is called from a background thread. It mutates *job* state
    in place (thread-safe via JobState._lock).

    Parameters
    ----------
    job:
        The :class:`~app.services.job_store.JobState` to operate on.
    excel_path:
        Absolute path to the uploaded Excel/CSV mapping file.
    skip_encrypted:
        Passed through to :class:`~src.pdf_encryptor.PdfEncryptor`.
    overwrite:
        Passed through to :class:`~src.pdf_encryptor.PdfEncryptor`.
    max_workers:
        Thread pool size for parallel encryption.
    """
    try:
        job.status = "processing"
        job.output_dir.mkdir(parents=True, exist_ok=True)

        # ── 1. Read Excel ──────────────────────────────────────────────
        reader = ExcelReader(excel_path)
        try:
            excel_result = reader.read()
        except (FileNotFoundError, ValueError) as exc:
            job.mark_failed(f"Excel error: {exc}")
            return

        if not excel_result.valid_rows:
            job.mark_failed("No valid rows found in Excel/CSV file.")
            return

        total = len(excel_result.valid_rows)
        job.total = total

        # Log Excel rows
        logger.info("Excel read completed. Filenames parsed from mapping spreadsheet:")
        for r in excel_result.valid_rows:
            logger.info("  - Row %d: '%s'", r.row_index, r.filename)

        # Log upload folder contents
        uploaded_files = list(job.input_dir.iterdir()) if job.input_dir.exists() else []
        logger.info(
            "Upload directory contents for job %s: %s (Total uploaded PDFs: %d)",
            job.job_id,
            [f.name for f in uploaded_files],
            len(uploaded_files),
        )

        # ── 2. Run encryption ──────────────────────────────────────────
        encryptor = PdfEncryptor(
            input_dir=job.input_dir,
            output_dir=job.output_dir,
            skip_encrypted=skip_encrypted,
            overwrite=overwrite,
        )
        processor = BatchProcessor(encryptor=encryptor, max_workers=max_workers)

        def _progress(done: int, total: int, filename: str) -> None:
            job.update_progress(done, total, filename)

        with Timer() as t:
            raw_results: list[ProcessingResult] = processor.run(
                excel_result.valid_rows,
                progress_callback=_progress,
            )

        # ── 3. Build summary ───────────────────────────────────────────
        # Calculate statistics
        matched_count = sum(1 for r in raw_results if r.status == "success")
        missing_count = sum(1 for r in raw_results if r.status == "missing")
        failed_count = sum(1 for r in raw_results if r.status == "failed")
        skipped_count = sum(1 for r in raw_results if r.status == "skipped")
        logger.info(
            "Job %s processing finished. Statistics: Total Excel rows=%d, Matched=%d, Missing=%d, Failed=%d, Skipped=%d",
            job.job_id,
            total,
            matched_count,
            missing_count,
            failed_count,
            skipped_count,
        )
        summary = RunSummary(total=total, elapsed_sec=t.elapsed)
        file_results: list[FileResult] = []
        for r in raw_results:
            summary.add(r)
            file_results.append(
                FileResult(
                    filename=r.filename,
                    status=r.status,
                    message=r.message,
                    elapsed_ms=r.elapsed_ms,
                )
            )

        # Also add skipped-Excel rows as "skipped"
        for _, fn, reason in excel_result.skipped_rows:
            file_results.append(
                FileResult(filename=fn, status="skipped", message=reason, elapsed_ms=0)
            )

        stats = JobStats(
            total=summary.total,
            success=summary.success,
            missing=summary.missing,
            failed=summary.failed,
            skipped=summary.skipped,
            elapsed_sec=summary.elapsed_sec,
        )

        # ── 4. Create ZIP ──────────────────────────────────────────────
        zip_path = job.tmp_dir / "encrypted_pdfs.zip"
        try:
            create_zip(job.output_dir, zip_path)
            job.zip_path = zip_path
        except ValueError:
            # No PDFs encrypted — still mark completed with stats
            job.zip_path = None

        job.mark_completed(stats=stats, results=file_results)

    except Exception as exc:
        job.mark_failed(f"Unexpected error: {exc}")
