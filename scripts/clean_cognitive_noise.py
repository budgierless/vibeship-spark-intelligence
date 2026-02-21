#!/usr/bin/env python3
"""Deprecated shim. Use scripts/maintenance/one_time/clean_cognitive_noise.py."""

from __future__ import annotations

import runpy
from pathlib import Path

if __name__ == "__main__":
    target = Path(__file__).resolve().parent / "maintenance" / "one_time" / "clean_cognitive_noise.py"
    runpy.run_path(str(target), run_name="__main__")
