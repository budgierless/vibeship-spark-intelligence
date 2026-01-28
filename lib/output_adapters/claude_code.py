"""Claude Code output adapter (CLAUDE.md)."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from .common import write_marked_section


def write(context: str, project_dir: Optional[Path] = None) -> bool:
    root = project_dir or Path.cwd()
    path = root / "CLAUDE.md"
    return write_marked_section(path, context, create_header="# CLAUDE")
