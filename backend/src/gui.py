"""
gui.py
------
Premium Tkinter GUI for the PDF Password Protector.

Features
--------
* Dark theme with modern colour palette
* Folder/file pickers for input, output, and Excel file
* Live scrolling log display
* Animated progress bar
* Real-time stats (encrypted / missing / failed / total)
* Start / Stop buttons
* Summary dialog on completion
* Settings panel (workers, skip encrypted, overwrite)
"""

from __future__ import annotations

import queue
import threading
import tkinter as tk
import tkinter.filedialog as fd
import tkinter.messagebox as mb
import tkinter.ttk as ttk
from datetime import datetime
from pathlib import Path

from src.excel_reader import ExcelReader
from src.logger import get_logger, setup_logging
from src.pdf_encryptor import PdfEncryptor
from src.processor import BatchProcessor
from src.utils import ProcessingResult, RunSummary, Timer, ensure_dirs, write_csv_report

logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# Colour palette
# ---------------------------------------------------------------------------
COLORS = {
    "bg": "#0f1117",
    "bg_card": "#1a1d2e",
    "bg_input": "#12141f",
    "accent": "#6c63ff",
    "accent_light": "#8b85ff",
    "accent_dark": "#4a43cc",
    "success": "#22c55e",
    "warning": "#f59e0b",
    "error": "#ef4444",
    "info": "#38bdf8",
    "text": "#e2e8f0",
    "text_muted": "#64748b",
    "border": "#2d3148",
    "progress_bg": "#1e2235",
}

FONTS = {
    "title": ("Segoe UI", 20, "bold"),
    "subtitle": ("Segoe UI", 11),
    "label": ("Segoe UI", 10),
    "input": ("Segoe UI", 10),
    "mono": ("Consolas", 9),
    "stat": ("Segoe UI", 22, "bold"),
    "stat_lbl": ("Segoe UI", 9),
    "btn": ("Segoe UI", 10, "bold"),
    "btn_sm": ("Segoe UI", 9),
}


# ---------------------------------------------------------------------------
# Helper widgets
# ---------------------------------------------------------------------------


class _PathRow(tk.Frame):
    """A label + entry + browse button row for selecting a path."""

    def __init__(
        self,
        parent: tk.Widget,
        label: str,
        mode: str = "dir",  # "dir" | "file"
        filetypes: list | None = None,
        **kwargs,
    ) -> None:
        super().__init__(parent, bg=COLORS["bg_card"], **kwargs)
        self._mode = mode
        self._filetypes = filetypes or []

        tk.Label(
            self,
            text=label,
            font=FONTS["label"],
            bg=COLORS["bg_card"],
            fg=COLORS["text_muted"],
            width=16,
            anchor="w",
        ).pack(side="left", padx=(0, 8))

        self._var = tk.StringVar()
        entry = tk.Entry(
            self,
            textvariable=self._var,
            font=FONTS["input"],
            bg=COLORS["bg_input"],
            fg=COLORS["text"],
            insertbackground=COLORS["text"],
            relief="flat",
            bd=0,
            highlightthickness=1,
            highlightcolor=COLORS["accent"],
            highlightbackground=COLORS["border"],
        )
        entry.pack(side="left", fill="x", expand=True, ipady=6, padx=(0, 8))

        btn = tk.Button(
            self,
            text="Browse…",
            font=FONTS["btn_sm"],
            bg=COLORS["accent_dark"],
            fg=COLORS["text"],
            activebackground=COLORS["accent"],
            activeforeground=COLORS["text"],
            relief="flat",
            bd=0,
            cursor="hand2",
            padx=10,
            pady=4,
            command=self._browse,
        )
        btn.pack(side="left")

    def _browse(self) -> None:
        if self._mode == "dir":
            path = fd.askdirectory(title="Select folder")
        else:
            path = fd.askopenfilename(title="Select file", filetypes=self._filetypes)
        if path:
            self._var.set(path)

    @property
    def value(self) -> str:
        return self._var.get().strip()

    @value.setter
    def value(self, v: str) -> None:
        self._var.set(v)


class _StatCard(tk.Frame):
    """Displays a single large number with a label below it."""

    def __init__(self, parent: tk.Widget, label: str, color: str, **kwargs) -> None:
        super().__init__(parent, bg=COLORS["bg_card"], **kwargs)
        self._count_var = tk.StringVar(value="0")

        tk.Label(
            self,
            textvariable=self._count_var,
            font=FONTS["stat"],
            bg=COLORS["bg_card"],
            fg=color,
        ).pack()
        tk.Label(
            self,
            text=label,
            font=FONTS["stat_lbl"],
            bg=COLORS["bg_card"],
            fg=COLORS["text_muted"],
        ).pack()

    def set(self, value: int) -> None:
        self._count_var.set(str(value))


# ---------------------------------------------------------------------------
# Main Application
# ---------------------------------------------------------------------------


class PDFProtectorApp:
    """
    The main Tkinter application window.

    Parameters
    ----------
    root:
        The root ``Tk`` instance.
    """

    def __init__(self, root: tk.Tk) -> None:
        self._root = root
        self._stop_event = threading.Event()
        self._log_queue: queue.Queue[str] = queue.Queue()
        self._result_queue: queue.Queue[ProcessingResult] = queue.Queue()
        self._summary: RunSummary | None = None
        self._worker_thread: threading.Thread | None = None
        self._is_running = False
        self._done_count = 0
        self._total_count = 0

        self._configure_root()
        self._build_ui()
        self._poll_queues()

    # ------------------------------------------------------------------
    # Window setup
    # ------------------------------------------------------------------

    def _configure_root(self) -> None:
        self._root.title("PDF Password Protector")
        self._root.configure(bg=COLORS["bg"])
        self._root.geometry("900x780")
        self._root.minsize(820, 680)
        self._root.resizable(True, True)

        # Centre on screen
        self._root.update_idletasks()
        w, h = 900, 780
        sw = self._root.winfo_screenwidth()
        sh = self._root.winfo_screenheight()
        self._root.geometry(f"{w}x{h}+{(sw-w)//2}+{(sh-h)//2}")

        # Custom ttk style for progress bar
        style = ttk.Style()
        style.theme_use("clam")
        style.configure(
            "Accent.Horizontal.TProgressbar",
            troughcolor=COLORS["progress_bg"],
            background=COLORS["accent"],
            bordercolor=COLORS["bg_card"],
            lightcolor=COLORS["accent_light"],
            darkcolor=COLORS["accent_dark"],
            thickness=14,
        )
        style.configure(
            "TCombobox",
            fieldbackground=COLORS["bg_input"],
            background=COLORS["bg_input"],
            foreground=COLORS["text"],
            selectbackground=COLORS["accent"],
            selectforeground=COLORS["text"],
        )

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        outer = tk.Frame(self._root, bg=COLORS["bg"])
        outer.pack(fill="both", expand=True, padx=20, pady=20)

        self._build_header(outer)
        self._build_paths_card(outer)
        self._build_settings_card(outer)
        self._build_stats_row(outer)
        self._build_progress_section(outer)
        self._build_log_area(outer)
        self._build_buttons(outer)

    def _build_header(self, parent: tk.Widget) -> None:
        hdr = tk.Frame(parent, bg=COLORS["bg"])
        hdr.pack(fill="x", pady=(0, 16))

        # Gradient-like accent strip
        accent = tk.Frame(hdr, bg=COLORS["accent"], width=4, height=52)
        accent.pack(side="left", fill="y", padx=(0, 14))

        info = tk.Frame(hdr, bg=COLORS["bg"])
        info.pack(side="left")

        tk.Label(
            info,
            text="PDF Password Protector",
            font=FONTS["title"],
            bg=COLORS["bg"],
            fg=COLORS["text"],
        ).pack(anchor="w")
        tk.Label(
            info,
            text="Bulk-encrypt thousands of PDFs using passwords from an Excel sheet",
            font=FONTS["subtitle"],
            bg=COLORS["bg"],
            fg=COLORS["text_muted"],
        ).pack(anchor="w")

    def _card(self, parent: tk.Widget) -> tk.Frame:
        """Return a styled card frame."""
        card = tk.Frame(
            parent,
            bg=COLORS["bg_card"],
            highlightthickness=1,
            highlightbackground=COLORS["border"],
        )
        card.pack(fill="x", pady=(0, 12))
        return card

    def _section_label(self, card: tk.Frame, text: str) -> None:
        tk.Label(
            card,
            text=text.upper(),
            font=("Segoe UI", 8, "bold"),
            bg=COLORS["bg_card"],
            fg=COLORS["accent"],
            pady=2,
        ).pack(anchor="w", padx=16, pady=(14, 0))

        sep = tk.Frame(card, bg=COLORS["border"], height=1)
        sep.pack(fill="x", padx=16, pady=(4, 10))

    def _build_paths_card(self, parent: tk.Widget) -> None:
        card = self._card(parent)
        self._section_label(card, "Paths")

        pad = {"padx": 16, "pady": 4, "fill": "x"}
        self._input_row = _PathRow(card, "Input Folder", mode="dir")
        self._output_row = _PathRow(card, "Output Folder", mode="dir")
        self._excel_row = _PathRow(
            card,
            "Excel / CSV File",
            mode="file",
            filetypes=[("Excel/CSV", "*.xlsx *.xls *.csv"), ("All", "*.*")],
        )
        self._log_dir_row = _PathRow(card, "Log Directory", mode="dir")

        # Set sensible defaults
        cwd = Path.cwd()
        self._input_row.value = str(cwd / "input")
        self._output_row.value = str(cwd / "output")
        self._excel_row.value = str(cwd / "passwords.xlsx")
        self._log_dir_row.value = str(cwd / "logs")

        for row in (self._input_row, self._output_row, self._excel_row, self._log_dir_row):
            row.pack(**pad)

        tk.Frame(card, bg=COLORS["bg_card"], height=10).pack()

    def _build_settings_card(self, parent: tk.Widget) -> None:
        card = self._card(parent)
        self._section_label(card, "Settings")

        row = tk.Frame(card, bg=COLORS["bg_card"])
        row.pack(fill="x", padx=16, pady=(0, 14))

        # Workers
        tk.Label(
            row,
            text="Parallel Workers:",
            font=FONTS["label"],
            bg=COLORS["bg_card"],
            fg=COLORS["text_muted"],
        ).pack(side="left")
        self._workers_var = tk.IntVar(value=4)
        workers_spin = tk.Spinbox(
            row,
            from_=1,
            to=32,
            textvariable=self._workers_var,
            width=4,
            font=FONTS["input"],
            bg=COLORS["bg_input"],
            fg=COLORS["text"],
            buttonbackground=COLORS["border"],
            relief="flat",
            bd=0,
            highlightthickness=1,
            highlightbackground=COLORS["border"],
        )
        workers_spin.pack(side="left", padx=(6, 24), ipady=4)

        # Checkboxes
        self._skip_encrypted_var = tk.BooleanVar(value=True)
        self._overwrite_var = tk.BooleanVar(value=True)

        for var, label in (
            (self._skip_encrypted_var, "Skip already-encrypted PDFs"),
            (self._overwrite_var, "Overwrite existing output files"),
        ):
            chk = tk.Checkbutton(
                row,
                text=label,
                variable=var,
                bg=COLORS["bg_card"],
                fg=COLORS["text"],
                activebackground=COLORS["bg_card"],
                activeforeground=COLORS["text"],
                selectcolor=COLORS["bg_input"],
                font=FONTS["label"],
            )
            chk.pack(side="left", padx=(0, 20))

    def _build_stats_row(self, parent: tk.Widget) -> None:
        stats_frame = tk.Frame(parent, bg=COLORS["bg"])
        stats_frame.pack(fill="x", pady=(0, 12))

        labels_colors = [
            ("Total", COLORS["info"]),
            ("Encrypted", COLORS["success"]),
            ("Skipped", COLORS["warning"]),
            ("Missing", COLORS["warning"]),
            ("Failed", COLORS["error"]),
        ]
        self._stat_total = None
        self._stat_encrypted = None
        self._stat_skipped = None
        self._stat_missing = None
        self._stat_failed = None

        cards = []
        for lbl, clr in labels_colors:
            c = tk.Frame(
                stats_frame,
                bg=COLORS["bg_card"],
                highlightthickness=1,
                highlightbackground=COLORS["border"],
            )
            c.pack(side="left", expand=True, fill="both", padx=(0, 8))
            sc = _StatCard(c, lbl, clr)
            sc.pack(padx=16, pady=14)
            cards.append(sc)

        (
            self._stat_total,
            self._stat_encrypted,
            self._stat_skipped,
            self._stat_missing,
            self._stat_failed,
        ) = cards

    def _build_progress_section(self, parent: tk.Widget) -> None:
        pcard = self._card(parent)
        inner = tk.Frame(pcard, bg=COLORS["bg_card"])
        inner.pack(fill="x", padx=16, pady=12)

        top = tk.Frame(inner, bg=COLORS["bg_card"])
        top.pack(fill="x", pady=(0, 6))

        tk.Label(
            top,
            text="Progress",
            font=FONTS["label"],
            bg=COLORS["bg_card"],
            fg=COLORS["text_muted"],
        ).pack(side="left")

        self._progress_label = tk.Label(
            top,
            text="Ready",
            font=FONTS["label"],
            bg=COLORS["bg_card"],
            fg=COLORS["text_muted"],
        )
        self._progress_label.pack(side="right")

        self._progress_var = tk.DoubleVar(value=0)
        self._progress_bar = ttk.Progressbar(
            inner,
            style="Accent.Horizontal.TProgressbar",
            variable=self._progress_var,
            maximum=100,
            mode="determinate",
        )
        self._progress_bar.pack(fill="x", ipady=2)

        self._status_var = tk.StringVar(value="Waiting to start…")
        tk.Label(
            inner,
            textvariable=self._status_var,
            font=FONTS["mono"],
            bg=COLORS["bg_card"],
            fg=COLORS["text_muted"],
        ).pack(anchor="w", pady=(4, 0))

    def _build_log_area(self, parent: tk.Widget) -> None:
        log_card = self._card(parent)
        self._section_label(log_card, "Live Log")

        log_frame = tk.Frame(log_card, bg=COLORS["bg_card"])
        log_frame.pack(fill="both", expand=True, padx=16, pady=(0, 14))

        scrollbar = tk.Scrollbar(log_frame, bg=COLORS["bg_card"])
        scrollbar.pack(side="right", fill="y")

        self._log_text = tk.Text(
            log_frame,
            font=FONTS["mono"],
            bg=COLORS["bg_input"],
            fg=COLORS["text"],
            insertbackground=COLORS["text"],
            relief="flat",
            bd=0,
            state="disabled",
            height=10,
            yscrollcommand=scrollbar.set,
            wrap="word",
        )
        self._log_text.pack(fill="both", expand=True)
        scrollbar.config(command=self._log_text.yview)

        # Colour tags
        self._log_text.tag_config("SUCCESS", foreground=COLORS["success"])
        self._log_text.tag_config("MISSING", foreground=COLORS["warning"])
        self._log_text.tag_config("FAILED", foreground=COLORS["error"])
        self._log_text.tag_config("INFO", foreground=COLORS["info"])
        self._log_text.tag_config("MUTED", foreground=COLORS["text_muted"])

    def _build_buttons(self, parent: tk.Widget) -> None:
        btn_row = tk.Frame(parent, bg=COLORS["bg"])
        btn_row.pack(fill="x", pady=(4, 0))

        self._start_btn = tk.Button(
            btn_row,
            text="▶  Start Encryption",
            font=FONTS["btn"],
            bg=COLORS["accent"],
            fg=COLORS["text"],
            activebackground=COLORS["accent_light"],
            activeforeground=COLORS["text"],
            relief="flat",
            bd=0,
            cursor="hand2",
            padx=24,
            pady=10,
            command=self._on_start,
        )
        self._start_btn.pack(side="left")

        self._stop_btn = tk.Button(
            btn_row,
            text="■  Stop",
            font=FONTS["btn"],
            bg=COLORS["bg_card"],
            fg=COLORS["error"],
            activebackground=COLORS["error"],
            activeforeground=COLORS["text"],
            relief="flat",
            bd=0,
            cursor="hand2",
            padx=20,
            pady=10,
            state="disabled",
            command=self._on_stop,
        )
        self._stop_btn.pack(side="left", padx=(10, 0))

        self._open_output_btn = tk.Button(
            btn_row,
            text="📂  Open Output",
            font=FONTS["btn_sm"],
            bg=COLORS["bg_card"],
            fg=COLORS["text_muted"],
            activebackground=COLORS["border"],
            activeforeground=COLORS["text"],
            relief="flat",
            bd=0,
            cursor="hand2",
            padx=14,
            pady=10,
            command=self._on_open_output,
        )
        self._open_output_btn.pack(side="right")

    # ------------------------------------------------------------------
    # Button handlers
    # ------------------------------------------------------------------

    def _on_start(self) -> None:
        if self._is_running:
            return

        # Validate paths
        input_dir = Path(self._input_row.value)
        output_dir = Path(self._output_row.value)
        excel_path = Path(self._excel_row.value)
        log_dir = Path(self._log_dir_row.value)

        if not input_dir.exists():
            mb.showerror("Invalid Path", f"Input folder does not exist:\n{input_dir}")
            return
        if not excel_path.exists():
            mb.showerror("Invalid Path", f"Excel/CSV file not found:\n{excel_path}")
            return

        self._stop_event.clear()
        self._is_running = True
        self._done_count = 0
        self._total_count = 0
        self._summary = None

        self._start_btn.config(state="disabled", bg=COLORS["accent_dark"])
        self._stop_btn.config(state="normal")
        self._progress_var.set(0)
        self._log_clear()
        self._reset_stats()
        self._status_var.set("Initialising…")

        self._worker_thread = threading.Thread(
            target=self._worker,
            args=(input_dir, output_dir, excel_path, log_dir),
            daemon=True,
        )
        self._worker_thread.start()

    def _on_stop(self) -> None:
        if self._is_running:
            self._stop_event.set()
            self._append_log("Stop requested — finishing current files…", "MISSING")
            self._stop_btn.config(state="disabled")

    def _on_open_output(self) -> None:
        import os
        import subprocess
        import sys

        path = Path(self._output_row.value)
        path.mkdir(parents=True, exist_ok=True)
        if sys.platform == "win32":
            os.startfile(path)
        else:
            subprocess.Popen(["xdg-open", str(path)])

    # ------------------------------------------------------------------
    # Worker thread
    # ------------------------------------------------------------------

    def _worker(
        self,
        input_dir: Path,
        output_dir: Path,
        excel_path: Path,
        log_dir: Path,
    ) -> None:
        try:
            ensure_dirs(input_dir, output_dir, log_dir)
            setup_logging(log_dir)

            self._append_log(f"Reading: {excel_path.name}", "INFO")

            reader = ExcelReader(excel_path)
            try:
                excel_result = reader.read()
            except (FileNotFoundError, ValueError) as exc:
                self._append_log(f"ERROR: {exc}", "FAILED")
                return

            total = len(excel_result.valid_rows)
            if total == 0:
                self._append_log("No valid rows found in the Excel file.", "FAILED")
                return

            # Report skipped Excel rows
            for idx, fn, reason in excel_result.skipped_rows:
                self._append_log(f"[Excel row {idx}] Skipped '{fn}': {reason}", "MISSING")

            self._total_count = total
            self._root.after(0, self._stat_total.set, total)
            self._append_log(f"Found {total} valid entries. Starting encryption…", "INFO")

            summary = RunSummary(total=total)

            encryptor = PdfEncryptor(
                input_dir=input_dir,
                output_dir=output_dir,
                skip_encrypted=self._skip_encrypted_var.get(),
                overwrite=self._overwrite_var.get(),
            )
            processor = BatchProcessor(
                encryptor=encryptor,
                max_workers=self._workers_var.get(),
            )

            with Timer() as t:
                results = processor.run(
                    excel_result.valid_rows,
                    progress_callback=self._on_progress,
                    stop_event=self._stop_event,
                )

            summary.elapsed_sec = t.elapsed
            for r in results:
                summary.add(r)
                self._result_queue.put(r)

            self._summary = summary

            # Save CSV report
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            csv_path = log_dir / f"report_{ts}.csv"
            write_csv_report(results, csv_path)
            self._append_log(f"Report saved → {csv_path.name}", "INFO")

        except Exception as exc:
            self._append_log(f"Fatal error: {exc}", "FAILED")
            logger.exception("Fatal GUI worker error")
        finally:
            self._root.after(0, self._on_done)

    def _on_progress(self, done: int, total: int, filename: str) -> None:
        pct = done / total * 100 if total else 0
        self._root.after(0, self._progress_var.set, pct)
        self._root.after(
            0,
            self._progress_label.config,
            {"text": f"{done} / {total}"},
        )
        self._root.after(
            0,
            self._status_var.set,
            f"Processing: {filename}",
        )

    def _on_done(self) -> None:
        self._is_running = False
        self._start_btn.config(state="normal", bg=COLORS["accent"])
        self._stop_btn.config(state="disabled")
        self._status_var.set("Finished!")
        self._progress_var.set(100)

        if self._summary:
            self._stat_total.set(self._summary.total)
            self._stat_encrypted.set(self._summary.success)
            self._stat_skipped.set(self._summary.skipped)
            self._stat_missing.set(self._summary.missing)
            self._stat_failed.set(self._summary.failed)
            self._append_log(f"\n{self._summary.pretty()}", "INFO")
            self._show_summary_dialog(self._summary)

    # ------------------------------------------------------------------
    # Queue polling (runs on main thread)
    # ------------------------------------------------------------------

    def _poll_queues(self) -> None:
        # Drain log queue
        while not self._log_queue.empty():
            msg, tag = self._log_queue.get_nowait()
            self._append_log_direct(msg, tag)

        # Drain result queue to update stats
        while not self._result_queue.empty():
            r: ProcessingResult = self._result_queue.get_nowait()
            tag = {
                "success": "SUCCESS",
                "missing": "MISSING",
                "failed": "FAILED",
                "skipped": "MUTED",
            }.get(r.status, "INFO")
            self._append_log_direct(f"  {r.status.upper():<8}  {r.filename}  — {r.message}", tag)

        # Schedule next poll
        self._root.after(80, self._poll_queues)

    # ------------------------------------------------------------------
    # Log helpers
    # ------------------------------------------------------------------

    def _append_log(self, message: str, tag: str = "INFO") -> None:
        """Thread-safe: enqueue for main thread."""
        self._log_queue.put((message, tag))

    def _append_log_direct(self, message: str, tag: str = "INFO") -> None:
        """Must be called from main thread."""
        ts = datetime.now().strftime("%H:%M:%S")
        self._log_text.config(state="normal")
        self._log_text.insert("end", f"[{ts}] {message}\n", tag)
        self._log_text.see("end")
        self._log_text.config(state="disabled")

    def _log_clear(self) -> None:
        self._log_text.config(state="normal")
        self._log_text.delete("1.0", "end")
        self._log_text.config(state="disabled")

    def _reset_stats(self) -> None:
        for card in (
            self._stat_total,
            self._stat_encrypted,
            self._stat_skipped,
            self._stat_missing,
            self._stat_failed,
        ):
            card.set(0)

    # ------------------------------------------------------------------
    # Summary dialog
    # ------------------------------------------------------------------

    def _show_summary_dialog(self, summary: RunSummary) -> None:
        dlg = tk.Toplevel(self._root)
        dlg.title("Encryption Complete")
        dlg.configure(bg=COLORS["bg"])
        dlg.resizable(False, False)
        dlg.grab_set()

        # Centre relative to root
        dlg.update_idletasks()
        rw, rh = self._root.winfo_width(), self._root.winfo_height()
        rx, ry = self._root.winfo_x(), self._root.winfo_y()
        dw, dh = 420, 380
        dlg.geometry(f"{dw}x{dh}+{rx+(rw-dw)//2}+{ry+(rh-dh)//2}")

        # Header strip
        hdr = tk.Frame(dlg, bg=COLORS["accent"], height=6)
        hdr.pack(fill="x")

        icon_lbl = tk.Label(
            dlg,
            text="✓" if summary.failed == 0 else "⚠",
            font=("Segoe UI", 48),
            bg=COLORS["bg"],
            fg=COLORS["success"] if summary.failed == 0 else COLORS["warning"],
        )
        icon_lbl.pack(pady=(16, 0))

        tk.Label(
            dlg,
            text="Batch Complete",
            font=FONTS["title"],
            bg=COLORS["bg"],
            fg=COLORS["text"],
        ).pack()

        tk.Label(
            dlg,
            text=f"Processed {summary.total} entries in {summary.elapsed_sec:.1f}s",
            font=FONTS["subtitle"],
            bg=COLORS["bg"],
            fg=COLORS["text_muted"],
        ).pack(pady=(2, 16))

        # Stats grid
        grid = tk.Frame(dlg, bg=COLORS["bg_card"])
        grid.pack(fill="x", padx=24, pady=(0, 16))

        rows_data = [
            ("Encrypted", summary.success, COLORS["success"]),
            ("Skipped", summary.skipped, COLORS["warning"]),
            ("Missing", summary.missing, COLORS["warning"]),
            ("Failed", summary.failed, COLORS["error"]),
        ]
        for i, (lbl, val, clr) in enumerate(rows_data):
            tk.Label(
                grid,
                text=lbl,
                font=FONTS["label"],
                bg=COLORS["bg_card"],
                fg=COLORS["text_muted"],
                anchor="w",
                padx=16,
                pady=6,
            ).grid(row=i, column=0, sticky="w")
            tk.Label(
                grid,
                text=str(val),
                font=("Segoe UI", 10, "bold"),
                bg=COLORS["bg_card"],
                fg=clr,
                padx=16,
            ).grid(row=i, column=1, sticky="e", padx=(0, 16))

        tk.Button(
            dlg,
            text="Close",
            font=FONTS["btn"],
            bg=COLORS["accent"],
            fg=COLORS["text"],
            activebackground=COLORS["accent_light"],
            relief="flat",
            bd=0,
            cursor="hand2",
            padx=30,
            pady=8,
            command=dlg.destroy,
        ).pack(pady=8)
