"""OpenClaw output adapter: write Spark context to ~/.openclaw/workspace/SPARK_CONTEXT.md."""

from __future__ import annotations

import os
import time
from pathlib import Path
from typing import Optional

from .common import write_marked_section


def _resolve_workspace() -> Path:
    explicit = os.environ.get("SPARK_OPENCLAW_WORKSPACE") or os.environ.get("OPENCLAW_WORKSPACE")
    if explicit:
        return Path(explicit).expanduser()
    return Path.home() / ".openclaw" / "workspace"


def _format_context(context: str, config: Optional[dict] = None) -> str:
    """Wrap raw context in a clean, actionable template for the agent."""
    config = config or {}
    stats = config.get("stats", {})

    sections = []

    # Main insights
    sections.append(context.rstrip())

    # Session stats (if available)
    events_count = stats.get("events_processed")
    insights_count = stats.get("insights_count")
    last_sync = stats.get("last_sync")
    if any(v is not None for v in [events_count, insights_count, last_sync]):
        parts = []
        if events_count is not None:
            parts.append(f"Events processed: {events_count}")
        if insights_count is not None:
            parts.append(f"Active insights: {insights_count}")
        if last_sync is not None:
            parts.append(f"Last sync: {last_sync}")
        sections.append("## 📊 Session Stats\n" + " | ".join(parts))

    # Self-report quick reference
    sections.append("""## 💬 How to Self-Report

Write a JSON file to `~/.openclaw/workspace/spark_reports/` and Spark picks it up automatically.

**Quick ref** (use the `write` tool):
```json
{"kind": "decision", "intent": "...", "reasoning": "...", "confidence": 0.9}
{"kind": "outcome", "result": "...", "lesson": "..."}
{"kind": "preference", "liked": "...", "disliked": "..."}
```

Or if `lib/self_report.py` is importable:
```python
from lib.self_report import report
report("decision", intent="use caching", reasoning="reduce latency", confidence=0.85)
```""")

    return "\n\n".join(sections)


def write(context: str, config: Optional[dict] = None) -> bool:
    """Write Spark context into OpenClaw workspace as SPARK_CONTEXT.md.

    Uses marker-bounded sections so the file can coexist with other content.
    Caps output at ~2KB to avoid bloating agent context.
    """
    workspace = _resolve_workspace()
    path = workspace / "SPARK_CONTEXT.md"

    # Format with template
    formatted = _format_context(context, config)

    # Cap to ~2KB
    max_bytes = 2048
    if len(formatted.encode("utf-8")) > max_bytes:
        lines = formatted.splitlines(keepends=True)
        trimmed = []
        size = 0
        for line in lines:
            line_bytes = len(line.encode("utf-8"))
            if size + line_bytes > max_bytes:
                break
            trimmed.append(line)
            size += line_bytes
        formatted = "".join(trimmed).rstrip() + "\n... [truncated to ~2KB]"

    return write_marked_section(
        path,
        formatted,
        create_header="# Spark Intelligence Context",
        marker_start="<!-- SPARK:BEGIN -->",
        marker_end="<!-- SPARK:END -->",
    )
