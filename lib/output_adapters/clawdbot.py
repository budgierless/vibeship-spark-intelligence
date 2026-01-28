"""Clawdbot output adapter (configurable path)."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Optional

from .common import write_marked_section


def _load_config() -> Optional[dict]:
    cfg_path = Path.home() / ".clawdbot" / "moltbot.json"
    if not cfg_path.exists():
        return None
    try:
        return json.loads(cfg_path.read_text(encoding="utf-8"))
    except Exception:
        return None


def _resolve_workspace() -> Path:
    explicit = os.environ.get("SPARK_CLAWDBOT_WORKSPACE") or os.environ.get("CLAWDBOT_WORKSPACE")
    if explicit:
        return Path(explicit).expanduser()

    cfg = _load_config() or {}
    # Support both documented shapes: agent.workspace and agents.defaults.workspace
    ws = None
    if isinstance(cfg.get("agent"), dict):
        ws = cfg["agent"].get("workspace")
    if not ws and isinstance(cfg.get("agents"), dict):
        defaults = cfg["agents"].get("defaults")
        if isinstance(defaults, dict):
            ws = defaults.get("workspace")

    if ws:
        return Path(str(ws)).expanduser()

    profile = os.environ.get("CLAWDBOT_PROFILE")
    if profile and profile != "default":
        return Path.home() / f"clawd-{profile}"
    return Path.home() / "clawd"


def _resolve_paths() -> List[Path]:
    explicit = os.environ.get("SPARK_CLAWDBOT_CONTEXT_PATH") or os.environ.get("CLAWDBOT_CONTEXT_PATH")
    if explicit:
        return [Path(explicit).expanduser()]

    workspace = _resolve_workspace()
    if not workspace:
        return []
    return [
        workspace / "AGENTS.md",
        workspace / "SOUL.md",
    ]


def write(context: str) -> bool:
    paths = _resolve_paths()
    if not paths:
        return False
    ok = False
    for path in paths:
        header = None
        name = path.name.lower()
        if name == "agents.md":
            header = "# AGENTS"
        elif name == "soul.md":
            header = "# SOUL"
        ok = write_marked_section(path, context, create_header=header) or ok
    return ok
