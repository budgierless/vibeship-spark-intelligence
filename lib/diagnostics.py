"""Lightweight debug logging utilities for Spark."""

from __future__ import annotations

import os
import sys
import traceback
from pathlib import Path
from typing import Optional, List


_DEBUG_VALUES = {"1", "true", "yes", "on"}
_LOG_SETUP = set()
_LOG_HANDLES: List[object] = []


def debug_enabled() -> bool:
    """Return True when SPARK_DEBUG is set to a truthy value."""
    return os.environ.get("SPARK_DEBUG", "").strip().lower() in _DEBUG_VALUES


def log_debug(component: str, message: str, exc: Optional[BaseException] = None) -> None:
    """Emit a debug log line to stderr when SPARK_DEBUG is enabled."""
    if not debug_enabled():
        return


class _Tee:
    def __init__(self, primary, secondary):
        self.primary = primary
        self.secondary = secondary

    def write(self, data):
        try:
            if self.primary:
                self.primary.write(data)
        except Exception:
            pass
        try:
            if self.secondary:
                self.secondary.write(data)
        except Exception:
            pass
        return len(data)

    def flush(self):
        try:
            if self.primary:
                self.primary.flush()
        except Exception:
            pass
        try:
            if self.secondary:
                self.secondary.flush()
        except Exception:
            pass

    def isatty(self):
        try:
            return bool(getattr(self.primary, "isatty", lambda: False)())
        except Exception:
            return False


def setup_component_logging(component: str) -> Optional[Path]:
    """Ensure logs are written to ~/.spark/logs even when not started by scripts."""
    if component in _LOG_SETUP:
        return None
    log_dir = Path(os.environ.get("SPARK_LOG_DIR") or (Path.home() / ".spark" / "logs"))
    try:
        log_dir.mkdir(parents=True, exist_ok=True)
    except Exception:
        return None

    log_file = log_dir / f"{component}.log"
    try:
        stdout_name = getattr(sys.stdout, "name", "")
        stderr_name = getattr(sys.stderr, "name", "")
        if stdout_name and stderr_name:
            if Path(stdout_name).resolve() == log_file.resolve() and Path(stderr_name).resolve() == log_file.resolve():
                _LOG_SETUP.add(component)
                return log_file
    except Exception:
        pass
    try:
        handle = open(log_file, "a", encoding="utf-8", errors="replace")
    except Exception:
        return None

    _LOG_HANDLES.append(handle)
    tee_enabled = os.environ.get("SPARK_LOG_TEE", "1").strip().lower() in _DEBUG_VALUES

    if tee_enabled:
        sys.stdout = _Tee(sys.stdout, handle)
        sys.stderr = _Tee(sys.stderr, handle)
    else:
        sys.stdout = handle
        sys.stderr = handle

    _LOG_SETUP.add(component)
    return log_file
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
