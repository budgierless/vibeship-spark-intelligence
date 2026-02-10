"""Self-report protocol: let agents write structured reports for Spark to ingest.

Usage:
    from lib.self_report import report

    report("decision", intent="use caching", reasoning="reduce latency", confidence=0.85)
    report("outcome", result="cache hit rate 92%", lesson="TTL of 5m is optimal")
    report("preference", liked="concise summaries", disliked="verbose tool output")
"""

from __future__ import annotations

import json
import os
import time
from pathlib import Path

DEFAULT_REPORT_DIR = Path.home() / ".openclaw" / "workspace" / "spark_reports"

VALID_KINDS = {"decision", "outcome", "preference"}


def _report_dir(directory: str | Path | None = None) -> Path:
    if directory:
        return Path(directory)
    env = os.environ.get("SPARK_REPORT_DIR")
    if env:
        return Path(env)
    return DEFAULT_REPORT_DIR


def report(kind: str, *, directory: str | Path | None = None, **kwargs) -> Path:
    """Write a self-report JSON file. Returns the path written.

    Args:
        kind: One of "decision", "outcome", "preference".
        directory: Override report directory.
        **kwargs: Arbitrary payload fields for the report.

    Returns:
        Path to the written report file.
    """
    if kind not in VALID_KINDS:
        raise ValueError(f"Invalid report kind {kind!r}; expected one of {VALID_KINDS}")

    d = _report_dir(directory)
    d.mkdir(parents=True, exist_ok=True)

    ts = time.time()
    ts_str = time.strftime("%Y%m%d_%H%M%S", time.localtime(ts))
    filename = f"{kind}_{ts_str}_{int(ts * 1000) % 100000}.json"
    path = d / filename

    payload = {
        "kind": kind,
        "ts": ts,
        **kwargs,
    }
    path.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")
    return path
