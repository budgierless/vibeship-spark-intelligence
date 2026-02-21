"""OpenClaw output adapter: write Spark context to ~/.openclaw/workspace/SPARK_CONTEXT.md."""

from __future__ import annotations

import os
import time
from pathlib import Path
from typing import Optional

from ..openclaw_paths import discover_openclaw_workspaces
from .common import write_json, write_marked_section

FALLBACK_ADVISORY_FILE = Path.home() / ".spark" / "llm_advisory.md"


def _resolve_workspaces() -> list[Path]:
    explicit = os.environ.get("SPARK_OPENCLAW_WORKSPACE") or os.environ.get("OPENCLAW_WORKSPACE")
    if explicit:
        return [Path(explicit).expanduser()]
    return discover_openclaw_workspaces(include_nonexistent=True)


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

    # Latest Activity (from bridge heartbeat)
    try:
        from ..bridge_cycle import read_bridge_heartbeat
        hb = read_bridge_heartbeat()
        if hb:
            hb_ts = hb.get("ts", 0)
            hb_stats = hb.get("stats", {})
            age_min = (time.time() - hb_ts) / 60 if hb_ts else None
            activity_parts = []
            if age_min is not None:
                activity_parts.append(f"Last cycle: {age_min:.0f}m ago")
            pp = int(hb_stats.get("pattern_processed") or 0)
            if pp:
                activity_parts.append(f"Patterns: {pp}")
            cl = int(hb_stats.get("content_learned") or 0)
            if cl:
                activity_parts.append(f"Content learned: {cl}")
            cm = (hb_stats.get("chip_merge") or {})
            merged = int(cm.get("merged") or 0)
            if merged:
                activity_parts.append(f"Insights merged: {merged}")
            errs = hb_stats.get("errors") or []
            if errs:
                activity_parts.append(f"Errors: {', '.join(errs)}")
            if activity_parts:
                sections.append("## ⚡ Latest Activity\n" + " | ".join(activity_parts))
    except Exception:
        pass  # graceful — don't break context generation

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


def write(context: str, config: Optional[dict] = None, advisory_payload: Optional[dict] = None) -> bool:
    """Write Spark context into OpenClaw workspace as SPARK_CONTEXT.md.

    Uses marker-bounded sections so the file can coexist with other content.
    Caps output at ~2KB to avoid bloating agent context.
    """
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

    ok = False
    for workspace in _resolve_workspaces():
        path = workspace / "SPARK_CONTEXT.md"
        result = write_marked_section(
            path,
            formatted,
            create_header="# Spark Intelligence Context",
            marker_start="<!-- SPARK:BEGIN -->",
            marker_end="<!-- SPARK:END -->",
        )
        # Keep advisory visible in profile workspaces even when only the fallback
        # advisory file was updated in this cycle.
        if FALLBACK_ADVISORY_FILE.exists():
            advisory_path = workspace / "SPARK_ADVISORY.md"
            src_mtime = FALLBACK_ADVISORY_FILE.stat().st_mtime
            dst_mtime = advisory_path.stat().st_mtime if advisory_path.exists() else 0.0
            if src_mtime > dst_mtime:
                advisory_path.parent.mkdir(parents=True, exist_ok=True)
                advisory_path.write_text(
                    FALLBACK_ADVISORY_FILE.read_text(encoding="utf-8", errors="replace"),
                    encoding="utf-8",
                )
        if advisory_payload is not None:
            write_json(workspace / "SPARK_ADVISORY_PAYLOAD.json", advisory_payload)
        ok = ok or bool(result)
    return ok
