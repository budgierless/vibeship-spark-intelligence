"""Helpers for resolving OpenClaw config/workspace paths."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Dict, List


OPENCLAW_DIR = Path.home() / ".openclaw"
OPENCLAW_CONFIG = OPENCLAW_DIR / "openclaw.json"
DEFAULT_WORKSPACE = OPENCLAW_DIR / "workspace"


def read_openclaw_config(path: Path = OPENCLAW_CONFIG) -> Dict:
    """Read OpenClaw config with BOM-safe JSON parsing."""
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8-sig"))
    except Exception:
        return {}
    return data if isinstance(data, dict) else {}


def _append_unique(paths: List[Path], seen: set, value: str) -> None:
    raw = str(value or "").strip()
    if not raw:
        return
    p = Path(raw).expanduser()
    key = str(p).lower()
    if key in seen:
        return
    seen.add(key)
    paths.append(p)


def discover_openclaw_workspaces(*, include_nonexistent: bool = False) -> List[Path]:
    """Discover OpenClaw workspaces that may need Spark context/advisory files."""
    explicit = os.environ.get("SPARK_OPENCLAW_WORKSPACE") or os.environ.get("OPENCLAW_WORKSPACE")
    if explicit:
        p = Path(explicit).expanduser()
        return [p] if include_nonexistent or p.exists() else []

    cfg = read_openclaw_config()
    candidates: List[Path] = []
    seen: set = set()

    defaults = ((cfg.get("agents") or {}).get("defaults") or {}) if isinstance(cfg.get("agents"), dict) else {}
    _append_unique(candidates, seen, defaults.get("workspace"))

    for row in list((cfg.get("agents") or {}).get("list") or []):
        if not isinstance(row, dict):
            continue
        _append_unique(candidates, seen, row.get("workspace"))

    # Runtime convention: OpenClaw creates profile workspaces like workspace-spark-speed.
    if OPENCLAW_DIR.exists():
        for p in sorted(OPENCLAW_DIR.glob("workspace*")):
            if p.is_dir():
                _append_unique(candidates, seen, str(p))

    _append_unique(candidates, seen, str(DEFAULT_WORKSPACE))

    if include_nonexistent:
        return candidates
    return [p for p in candidates if p.exists()]


def primary_openclaw_workspace() -> Path:
    workspaces = discover_openclaw_workspaces(include_nonexistent=True)
    if workspaces:
        return workspaces[0]
    return DEFAULT_WORKSPACE


def discover_openclaw_advisory_files() -> List[Path]:
    files: List[Path] = []
    for ws in discover_openclaw_workspaces(include_nonexistent=False):
        p = ws / "SPARK_ADVISORY.md"
        if p.exists():
            files.append(p)
    return files
