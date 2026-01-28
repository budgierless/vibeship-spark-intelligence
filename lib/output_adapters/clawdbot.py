"""Clawdbot output adapter (configurable path)."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

from .common import write_marked_section


def _resolve_path() -> Optional[Path]:
    explicit = os.environ.get("SPARK_CLAWDBOT_CONTEXT_PATH") or os.environ.get("CLAWDBOT_CONTEXT_PATH")
    if explicit:
        return Path(explicit).expanduser()

    agent = os.environ.get("SPARK_CLAWDBOT_AGENT") or os.environ.get("CLAWDBOT_AGENT") or "main"
    base = Path.home() / ".clawdbot" / "agents" / agent
    if not base.exists():
        return None

    # If a known prompt/context file exists, prefer it.
    for name in (
        "system.md",
        "SYSTEM.md",
        "prompt.md",
        "PROMPT.md",
        "context.md",
        "SPARK_CONTEXT.md",
    ):
        candidate = base / name
        if candidate.exists():
            return candidate

    # Default to a dedicated Spark context file inside the agent dir.
    return base / "SPARK_CONTEXT.md"


def write(context: str) -> bool:
    path = _resolve_path()
    if not path:
        return False
    return write_marked_section(path, context)
