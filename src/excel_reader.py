"""
excel_reader.py
---------------
Reads and validates the Excel mapping file that pairs PDF filenames with
their encryption passwords.

Design decisions
~~~~~~~~~~~~~~~~
* All public methods return plain Python data structures (lists / dicts)
  so that callers stay decoupled from pandas internals.
* Validation is strict but non-fatal: invalid rows are logged and collected
  in a ``skipped`` list; the caller receives only clean rows.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import pandas as pd

from src.logger import get_logger

logger = get_logger(__name__)

# ---------------------------------------------------------------------------
# Typing aliases
# ---------------------------------------------------------------------------
FilenamePasswordMap = Dict[str, str]   # {filename: password}


# ---------------------------------------------------------------------------
# Data class for a single Excel row
# ---------------------------------------------------------------------------

@dataclass
class ExcelRow:
    """A validated row from the mapping spreadsheet."""

    filename: str    # e.g. "Rahul.pdf"
    password: str    # e.g. "ABCDE1234F"
    row_index: int   # 1-based index (header = 0, data starts at 1)


@dataclass
class ExcelReadResult:
    """Outcome of reading and validating the Excel file."""

    valid_rows: List[ExcelRow] = field(default_factory=list)
    skipped_rows: List[Tuple[int, str, str]] = field(default_factory=list)
    # ^ (row_index, raw_filename, reason)

    @property
    def filename_password_map(self) -> FilenamePasswordMap:
        """Convenience accessor: returns ``{filename: password}`` dict."""
        return {row.filename: row.password for row in self.valid_rows}


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Accepted column name variants (case-insensitive, strip whitespace)
_FILE_COLUMN_ALIASES = {"pdf file", "pdf_file", "filename", "file name", "file"}
_PASS_COLUMN_ALIASES = {
    "password", "pass", "pwd", "pan", "pan number",
    "password/pan", "encryption password",
}

# Characters that are illegal in Windows / POSIX filenames
_ILLEGAL_CHARS_RE = re.compile(r'[<>:"/\\|?*\x00-\x1f]')


# ---------------------------------------------------------------------------
# ExcelReader class
# ---------------------------------------------------------------------------

class ExcelReader:
    """
    Reads an Excel (.xlsx / .xls / .csv) file and produces a validated
    mapping of PDF filenames to passwords.

    Parameters
    ----------
    filepath:
        Path to the Excel / CSV mapping file.
    file_col:
        Override the auto-detected filename column name.
    pass_col:
        Override the auto-detected password column name.
    """

    def __init__(
        self,
        filepath: Path,
        file_col: Optional[str] = None,
        pass_col: Optional[str] = None,
    ) -> None:
        self._filepath = Path(filepath)
        self._file_col = file_col
        self._pass_col = pass_col

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def read(self) -> ExcelReadResult:
        """
        Parse the spreadsheet and return a :class:`ExcelReadResult`.

        Raises
        ------
        FileNotFoundError
            If the Excel file does not exist.
        ValueError
            If the required columns cannot be located.
        """
        self._validate_file_exists()
        df = self._load_dataframe()
        file_col, pass_col = self._detect_columns(df)
        logger.info(
            "Using columns -> file: '%s', password: '%s'", file_col, pass_col
        )
        return self._parse_rows(df, file_col, pass_col)

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _validate_file_exists(self) -> None:
        if not self._filepath.exists():
            raise FileNotFoundError(
                f"Excel/CSV mapping file not found: {self._filepath}"
            )

    def _load_dataframe(self) -> pd.DataFrame:
        suffix = self._filepath.suffix.lower()
        try:
            if suffix == ".csv":
                df = pd.read_csv(self._filepath, dtype=str, keep_default_na=False)
            else:
                df = pd.read_excel(
                    self._filepath, dtype=str, keep_default_na=False
                )
        except Exception as exc:
            raise ValueError(
                f"Failed to read mapping file '{self._filepath}': {exc}"
            ) from exc

        # Normalise column names: strip whitespace
        df.columns = [str(c).strip() for c in df.columns]
        logger.debug("Loaded %d rows from '%s'", len(df), self._filepath.name)
        return df

    def _detect_columns(self, df: pd.DataFrame) -> Tuple[str, str]:
        """
        Auto-detect which column holds filenames and which holds passwords.
        Raises ``ValueError`` if either cannot be found.
        """
        lower_map = {c.lower(): c for c in df.columns}

        file_col = self._file_col
        if file_col is None:
            for alias in _FILE_COLUMN_ALIASES:
                if alias in lower_map:
                    file_col = lower_map[alias]
                    break
        if file_col is None or file_col not in df.columns:
            raise ValueError(
                f"Cannot find a filename column in {list(df.columns)}. "
                f"Expected one of: {sorted(_FILE_COLUMN_ALIASES)}"
            )

        pass_col = self._pass_col
        if pass_col is None:
            for alias in _PASS_COLUMN_ALIASES:
                if alias in lower_map:
                    pass_col = lower_map[alias]
                    break
        if pass_col is None or pass_col not in df.columns:
            raise ValueError(
                f"Cannot find a password column in {list(df.columns)}. "
                f"Expected one of: {sorted(_PASS_COLUMN_ALIASES)}"
            )

        return file_col, pass_col

    def _parse_rows(
        self, df: pd.DataFrame, file_col: str, pass_col: str
    ) -> ExcelReadResult:
        result = ExcelReadResult()
        seen_filenames: dict[str, int] = {}

        file_col_idx = df.columns.get_loc(file_col)
        pass_col_idx = df.columns.get_loc(pass_col)

        for idx, row_data in enumerate(df.itertuples(index=False), start=1):
            raw_filename = str(row_data[file_col_idx]).strip()
            raw_password = str(row_data[pass_col_idx]).strip()

            # --- Validate filename ---
            if not raw_filename or raw_filename.lower() == "nan":
                result.skipped_rows.append((idx, raw_filename, "Empty filename"))
                logger.warning("Row %d skipped: empty filename", idx)
                continue

            if _ILLEGAL_CHARS_RE.search(raw_filename):
                result.skipped_rows.append(
                    (idx, raw_filename, "Filename contains illegal characters")
                )
                logger.warning(
                    "Row %d skipped: illegal chars in filename '%s'",
                    idx, raw_filename,
                )
                continue

            # Ensure .pdf extension
            normalised = raw_filename if raw_filename.lower().endswith(".pdf") \
                else raw_filename + ".pdf"

            # --- Check for duplicates ---
            if normalised.lower() in seen_filenames:
                orig_idx = seen_filenames[normalised.lower()]
                result.skipped_rows.append(
                    (
                        idx,
                        raw_filename,
                        f"Duplicate (first seen at row {orig_idx})",
                    )
                )
                logger.warning(
                    "Row %d skipped: duplicate filename '%s' (first at row %d)",
                    idx, normalised, orig_idx,
                )
                continue

            # --- Validate password ---
            if not raw_password or raw_password.lower() == "nan":
                result.skipped_rows.append((idx, raw_filename, "Empty password"))
                logger.warning(
                    "Row %d skipped: empty password for '%s'", idx, normalised
                )
                continue

            seen_filenames[normalised.lower()] = idx
            result.valid_rows.append(ExcelRow(normalised, raw_password, idx))

        logger.info(
            "Excel parse complete: %d valid, %d skipped",
            len(result.valid_rows),
            len(result.skipped_rows),
        )
        return result
