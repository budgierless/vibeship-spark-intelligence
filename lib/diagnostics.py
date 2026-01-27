"""Lightweight debug logging utilities for Spark."""

from __future__ import annotations

import os
import sys
import traceback
from typing import Optional


_DEBUG_VALUES = {"1", "true", "yes", "on"}


def debug_enabled() -> bool:
    """Return True when SPARK_DEBUG is set to a truthy value."""
    return os.environ.get("SPARK_DEBUG", "").strip().lower() in _DEBUG_VALUES


def log_debug(component: str, message: str, exc: Optional[BaseException] = None) -> None:
    """Emit a debug log line to stderr when SPARK_DEBUG is enabled."""
    if not debug_enabled():
        return
    try:
        line = f"[SPARK][{component}] {message}"
        if exc is not None:
            line = f"{line}: {exc}"
        sys.stderr.write(line + "\n")
        if exc is not None:
            tb = "".join(traceback.format_exception(type(exc), exc, exc.__traceback__))
            sys.stderr.write(tb + "\n")
    except Exception:
        # Never fail logging.
        return
