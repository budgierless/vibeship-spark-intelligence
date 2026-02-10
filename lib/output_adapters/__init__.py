"""Output adapters for platform-specific context injection."""

from .claude_code import write as write_claude_code
from .cursor import write as write_cursor
from .windsurf import write as write_windsurf
from .clawdbot import write as write_clawdbot
from .openclaw import write as write_openclaw
from .exports import write_exports

__all__ = [
    "write_claude_code",
    "write_cursor",
    "write_windsurf",
    "write_clawdbot",
    "write_openclaw",
    "write_exports",
]
