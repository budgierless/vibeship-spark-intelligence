"""Shared helpers for Spark output adapters (lightweight)."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Optional


MARKER_START = "<!-- SPARK_LEARNINGS_START -->"
MARKER_END = "<!-- SPARK_LEARNINGS_END -->"


def _ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def write_marked_section(
    path: Path,
    content: str,
    *,
    marker_start: str = MARKER_START,
    marker_end: str = MARKER_END,
    create_header: Optional[str] = None,
) -> bool:
    """Write a marker-bounded section into a file.

    If markers exist, replace the section. Otherwise, append.
    """
    if content is None or not str(content).strip():
        # Safety guard: never truncate a file with empty content.
        return False
    _ensure_parent(path)
    existing = path.read_text(encoding="utf-8") if path.exists() else ""

    block = f"{marker_start}\n{content}\n{marker_end}"

    if marker_start in existing and marker_end in existing:
        pattern = f"{re.escape(marker_start)}.*?{re.escape(marker_end)}"
        updated = re.sub(pattern, block, existing, flags=re.DOTALL)
    else:
        if not existing and create_header:
            existing = create_header + "\n"
        if existing and not existing.endswith("\n"):
            existing += "\n"
        updated = existing + ("\n" if existing else "") + block

    path.write_text(updated, encoding="utf-8")
    return True


def write_text(path: Path, content: str) -> bool:
    _ensure_parent(path)
    path.write_text(content, encoding="utf-8")
    return True
