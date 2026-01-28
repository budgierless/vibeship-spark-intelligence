"""Export-only outputs for hosted platforms (GPT/Gemini)."""

from __future__ import annotations

from pathlib import Path

from .common import write_text


def write_exports(context: str) -> bool:
    base = Path.home() / ".spark" / "exports"
    ok1 = write_text(base / "gpt_instructions.md", context)
    ok2 = write_text(base / "gemini_system.md", context)
    return bool(ok1 and ok2)
