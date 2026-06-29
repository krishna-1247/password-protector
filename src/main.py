"""
main.py
-------
Entry point for the PDF Password Protector application.

Supports two modes:
  1. GUI mode  (default)   — opens a Tkinter desktop window.
  2. CLI mode              — ``python main.py --cli`` for headless operation.

Usage
-----
    # GUI
    python main.py

    # CLI (all arguments optional; defaults are taken from config.py or
    # current working directory)
    python main.py --cli \
        --input  input/ \
        --output output/ \
        --excel  passwords.xlsx \
        --workers 4 \
        --skip-encrypted \
        --no-overwrite
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


def _run_cli(args: argparse.Namespace) -> None:
    """Execute the CLI processing pipeline."""
    # Local imports keep GUI dependencies out of CLI path
    from src.logger import setup_logging
    from src.excel_reader import ExcelReader
    from src.pdf_encryptor import PdfEncryptor
    from src.utils import RunSummary, Timer, ensure_dirs, write_csv_report
    from src.processor import BatchProcessor

    log_dir = Path(args.log_dir)
    log_file = setup_logging(log_dir)
    from src.logger import get_logger
    logger = get_logger(__name__)
    logger.info("Log file: %s", log_file)

    input_dir  = Path(args.input).resolve()
    output_dir = Path(args.output).resolve()
    excel_path = Path(args.excel).resolve()

    ensure_dirs(input_dir, output_dir, log_dir)

    # --- Read Excel ----------------------------------------------------------
    logger.info("Reading mapping file: %s", excel_path)
    reader = ExcelReader(excel_path)
    try:
        excel_result = reader.read()
    except (FileNotFoundError, ValueError) as exc:
        logger.critical("Cannot read Excel file: %s", exc)
        sys.exit(1)

    if not excel_result.valid_rows:
        logger.critical("No valid rows found in Excel file. Aborting.")
        sys.exit(1)

    # --- Process -------------------------------------------------------------
    encryptor = PdfEncryptor(
        input_dir=input_dir,
        output_dir=output_dir,
        skip_encrypted=args.skip_encrypted,
        overwrite=not args.no_overwrite,
    )

    processor = BatchProcessor(
        encryptor=encryptor,
        max_workers=args.workers,
    )

    summary = RunSummary(total=len(excel_result.valid_rows))

    import threading
    stop_event = threading.Event()

    def _cli_progress(done: int, total: int, filename: str) -> None:
        pct = done / total * 100 if total else 0
        bar_len = 30
        filled = int(bar_len * done / total) if total else 0
        bar = "#" * filled + "-" * (bar_len - filled)
        print(f"\r  [{bar}] {pct:5.1f}%  {done}/{total}  {filename[:40]:<40}", end="", flush=True)

    with Timer() as t:
        results = processor.run(
            excel_result.valid_rows,
            progress_callback=_cli_progress,
        )

    print()  # newline after progress bar
    summary.elapsed_sec = t.elapsed
    for r in results:
        summary.add(r)

    # --- Report --------------------------------------------------------------
    print(summary.pretty())

    from datetime import datetime
    csv_path = log_dir / f"report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    write_csv_report(results, csv_path)
    logger.info("CSV report: %s", csv_path)


def _run_gui() -> None:
    """Launch the Tkinter GUI."""
    from src.gui import PDFProtectorApp
    import tkinter as tk
    root = tk.Tk()
    app = PDFProtectorApp(root)
    root.mainloop()


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="pdf-protector",
        description="Bulk PDF Password Protector",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--cli", action="store_true", help="Run in headless CLI mode")
    parser.add_argument("--input",  default="input",        metavar="DIR",  help="Input folder (default: input/)")
    parser.add_argument("--output", default="output",       metavar="DIR",  help="Output folder (default: output/)")
    parser.add_argument("--excel",  default="passwords.xlsx", metavar="FILE", help="Excel/CSV mapping file")
    parser.add_argument("--log-dir", default="logs",        metavar="DIR",  help="Log directory (default: logs/)")
    parser.add_argument("--workers", type=int, default=4,   metavar="N",    help="Parallel worker threads (default: 4)")
    parser.add_argument("--skip-encrypted", action="store_true", help="Skip PDFs that are already encrypted")
    parser.add_argument("--no-overwrite",   action="store_true", help="Do not overwrite existing output files")
    return parser.parse_args()


if __name__ == "__main__":
    args = _parse_args()
    if args.cli:
        _run_cli(args)
    else:
        _run_gui()
