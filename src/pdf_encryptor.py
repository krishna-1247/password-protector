"""
pdf_encryptor.py
----------------
Core PDF encryption logic built on top of ``pypdf``.

Design decisions
~~~~~~~~~~~~~~~~
* Each public method is stateless and accepts only what it needs.
* Encryption uses AES-256 (owner password = user password so the file can
  be opened with just the single password from the Excel sheet).
* Already-encrypted PDFs are detected up-front; behaviour is configurable
  via ``skip_encrypted``.
* Every exception is caught and returned as a structured result, so the
  caller never has to deal with unexpected raises.
"""

from __future__ import annotations

import time
from pathlib import Path
from typing import Callable, Optional

from pypdf import PdfReader, PdfWriter
from pypdf.errors import PdfReadError

from src.logger import get_logger
from src.utils import ProcessingResult

logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# PdfEncryptor
# ---------------------------------------------------------------------------

class PdfEncryptor:
    """
    Encrypts a single PDF file using a given password.

    Parameters
    ----------
    input_dir:
        Directory that contains the source PDF files.
    output_dir:
        Directory where encrypted PDFs will be written.
    skip_encrypted:
        When ``True``, PDFs that are already password-protected are skipped
        instead of being treated as errors.
    overwrite:
        When ``True``, overwrite existing files in the output directory.
    progress_callback:
        Optional callable ``(filename: str) -> None`` invoked just before
        each file is processed (useful for progress bars).
    """

    def __init__(
        self,
        input_dir: Path,
        output_dir: Path,
        skip_encrypted: bool = True,
        overwrite: bool = True,
        progress_callback: Optional[Callable[[str], None]] = None,
    ) -> None:
        self._input_dir = input_dir
        self._output_dir = output_dir
        self._skip_encrypted = skip_encrypted
        self._overwrite = overwrite
        self._progress_callback = progress_callback

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def encrypt(self, filename: str, password: str) -> ProcessingResult:
        """
        Locate *filename* in the input directory, encrypt it with *password*,
        and save the result to the output directory.

        Parameters
        ----------
        filename:
            PDF filename (basename only, e.g. ``"Rahul.pdf"``).
        password:
            Encryption password string.

        Returns
        -------
        ProcessingResult
            Structured outcome of the operation.
        """
        if self._progress_callback:
            self._progress_callback(filename)

        t_start = time.perf_counter()
        result = self._do_encrypt(filename, password)
        result.elapsed_ms = (time.perf_counter() - t_start) * 1000
        return result

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _do_encrypt(self, filename: str, password: str) -> ProcessingResult:
        src_path = self._input_dir / filename
        dst_path = self._output_dir / filename

        # ── Check source exists ────────────────────────────────────────
        if not src_path.exists():
            logger.warning("Missing: '%s'", filename)
            return ProcessingResult(filename, "missing", f"Not found in {self._input_dir}")

        # ── Skip if destination already exists and overwrite is off ────
        if dst_path.exists() and not self._overwrite:
            logger.info("Skipped (output exists): '%s'", filename)
            return ProcessingResult(filename, "skipped", "Output already exists")

        # ── Attempt to read the PDF ────────────────────────────────────
        try:
            reader = PdfReader(str(src_path))
        except PdfReadError as exc:
            logger.error("Corrupted/unsupported PDF '%s': %s", filename, exc)
            return ProcessingResult(filename, "failed", f"PdfReadError: {exc}")
        except Exception as exc:
            logger.error("Unexpected error reading '%s': %s", filename, exc)
            return ProcessingResult(filename, "failed", f"ReadError: {exc}")

        # ── Check if already encrypted ─────────────────────────────────
        if reader.is_encrypted:
            if self._skip_encrypted:
                logger.info("Skipped (already encrypted): '%s'", filename)
                return ProcessingResult(
                    filename, "skipped", "Already encrypted — skipped"
                )
            # Try to decrypt with the provided password; if it fails, bail out
            try:
                if not reader.decrypt(password):
                    logger.warning(
                        "Already encrypted with a different password: '%s'", filename
                    )
                    return ProcessingResult(
                        filename,
                        "failed",
                        "Already encrypted with a different password",
                    )
            except Exception as exc:
                logger.error("Cannot decrypt existing PDF '%s': %s", filename, exc)
                return ProcessingResult(
                    filename, "failed", f"DecryptError: {exc}"
                )

        # ── Validate: must have at least one page ──────────────────────
        try:
            page_count = len(reader.pages)
        except Exception as exc:
            logger.error("Cannot read pages from '%s': %s", filename, exc)
            return ProcessingResult(filename, "failed", f"PageReadError: {exc}")

        if page_count == 0:
            logger.warning("Empty PDF (0 pages): '%s'", filename)
            return ProcessingResult(filename, "failed", "PDF has 0 pages")

        # ── Write encrypted output ─────────────────────────────────────
        try:
            writer = PdfWriter()

            # Clone all pages (preserves content + metadata)
            for page in reader.pages:
                writer.add_page(page)

            # Clone document metadata
            if reader.metadata:
                writer.add_metadata(dict(reader.metadata))

            # Encrypt with AES-256; owner password = user password
            writer.encrypt(
                user_password=password,
                owner_password=password,
                use_128bit=False,   # use AES-256
            )

            self._output_dir.mkdir(parents=True, exist_ok=True)
            with dst_path.open("wb") as fh:
                writer.write(fh)

        except Exception as exc:
            logger.error("Failed to encrypt '%s': %s", filename, exc)
            # Remove partial output if it was created
            if dst_path.exists():
                try:
                    dst_path.unlink()
                except OSError:
                    pass
            return ProcessingResult(filename, "failed", f"EncryptError: {exc}")

        logger.info(
            "Encrypted: '%s' (%d page%s)",
            filename, page_count, "s" if page_count != 1 else "",
        )
        return ProcessingResult(
            filename, "success", f"Encrypted {page_count} page(s)"
        )
