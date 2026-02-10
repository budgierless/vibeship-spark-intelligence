"""OpenClaw output adapter: write Spark context to ~/.openclaw/workspace/SPARK_CONTEXT.md."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

from .common import write_marked_section


def _resolve_workspace() -> Path:
    explicit = os.environ.get("SPARK_OPENCLAW_WORKSPACE") or os.environ.get("OPENCLAW_WORKSPACE")
    if explicit:
        return Path(explicit).expanduser()
    return Path.home() / ".openclaw" / "workspace"


def write(context: str, config: Optional[dict] = None) -> bool:
    """Write Spark context into OpenClaw workspace as SPARK_CONTEXT.md.

    Uses marker-bounded sections so the file can coexist with other content.
    Caps output at ~2KB to avoid bloating agent context.
    """
    workspace = _resolve_workspace()
    path = workspace / "SPARK_CONTEXT.md"

    # Cap context to ~2KB
    max_bytes = 2048
    if len(context.encode("utf-8")) > max_bytes:
        # Truncate at line boundaries
        lines = context.splitlines(keepends=True)
        trimmed = []
        size = 0
        for line in lines:
            line_bytes = len(line.encode("utf-8"))
            if size + line_bytes > max_bytes:
                break
            trimmed.append(line)
            size += line_bytes
        context = "".join(trimmed).rstrip() + "\n... [truncated to ~2KB]"

    return write_marked_section(
        path,
        context,
        create_header="# Spark Intelligence Context",
        marker_start="<!-- SPARK:BEGIN -->",
        marker_end="<!-- SPARK:END -->",
    )
