#!/usr/bin/env python3
"""Standalone entry point for PyInstaller builds."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

from local_commit.cli import main

if __name__ == "__main__":
    main()
