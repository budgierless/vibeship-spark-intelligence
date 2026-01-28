"""Cursor output adapter (.cursorrules)."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from .common import write_marked_section


def write(context: str, project_dir: Optional[Path] = None) -> bool:
    root = project_dir or Path.cwd()
    path = root / ".cursorrules"
    return write_marked_section(path, context)
