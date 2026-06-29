#!/usr/bin/env python3
"""
Root launcher script.
Run from the project root with:
    python main.py          # GUI mode
    python main.py --cli    # CLI mode
"""
import sys
import os

# Ensure the project root is on the Python path so that `src.*` imports work
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.main import _parse_args, _run_cli, _run_gui

if __name__ == "__main__":
    args = _parse_args()
    if args.cli:
        _run_cli(args)
    else:
        _run_gui()
