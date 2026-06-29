"""
logger.py
---------
Centralised logging setup for the PDF Password Protector application.

Provides:
  - Timestamped log files inside the logs/ directory.
  - Console (stream) handler with colour-coded severity labels.
  - A single ``get_logger`` factory used by every module.
"""

from __future__ import annotations

import logging
import sys
from datetime import datetime
from pathlib import Path

# ---------------------------------------------------------------------------
# ANSI colour codes (no-op on Windows terminals that do not support them;
# the StreamHandler falls back gracefully).
# ---------------------------------------------------------------------------
_COLOURS = {
    logging.DEBUG: "\033[36m",  # Cyan
    logging.INFO: "\033[32m",  # Green
    logging.WARNING: "\033[33m",  # Yellow
    logging.ERROR: "\033[31m",  # Red
    logging.CRITICAL: "\033[35m",  # Magenta
}
_RESET = "\033[0m"


class _ColouredFormatter(logging.Formatter):
    """A formatter that adds ANSI colour codes to the level name."""

    def format(self, record: logging.LogRecord) -> str:  # noqa: A003
        colour = _COLOURS.get(record.levelno, "")
        record.levelname = f"{colour}{record.levelname:<8}{_RESET}"
        return super().format(record)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def setup_logging(log_dir: Path, log_level: int = logging.DEBUG) -> Path:
    """
    Initialise the root logger with a file handler and a console handler.

    Parameters
    ----------
    log_dir:
        Directory where the log file will be written.  Created if absent.
    log_level:
        Minimum severity level (default: DEBUG so that the file captures
        everything; the console handler uses INFO).

    Returns
    -------
    Path
        Absolute path to the created log file.
    """
    log_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = log_dir / f"pdf_protector_{timestamp}.log"

    root = logging.getLogger()
    root.setLevel(log_level)

    # Prevent duplicate handlers when setup_logging is called more than once
    root.handlers.clear()

    file_fmt = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(file_fmt)
    root.addHandler(file_handler)

    console_fmt = _ColouredFormatter(
        fmt="%(asctime)s | %(levelname)s | %(message)s",
        datefmt="%H:%M:%S",
    )
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(console_fmt)
    root.addHandler(console_handler)

    return log_file


def get_logger(name: str) -> logging.Logger:
    """
    Return a named child logger.

    Parameters
    ----------
    name:
        Typically ``__name__`` of the calling module.
    """
    return logging.getLogger(name)
