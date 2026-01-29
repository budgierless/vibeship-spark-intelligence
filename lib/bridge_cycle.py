"""Single-cycle bridge worker execution + heartbeat helpers."""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any, Dict, Optional

from lib.bridge import update_spark_context
from lib.memory_capture import process_recent_memory_events
from lib.tastebank import parse_like_message, add_item
from lib.queue import read_recent_events, EventType
from lib.pattern_detection import process_pattern_events
from lib.diagnostics import log_debug


BRIDGE_HEARTBEAT_FILE = Path.home() / ".spark" / "bridge_worker_heartbeat.json"


def run_bridge_cycle(
    *,
    query: Optional[str] = None,
    memory_limit: int = 60,
    pattern_limit: int = 200,
) -> Dict[str, Any]:
    """Run one bridge_worker cycle and return stats."""
    stats: Dict[str, Any] = {
        "timestamp": time.time(),
        "context_updated": False,
        "memory": {},
        "tastebank_saved": False,
        "pattern_processed": 0,
        "errors": [],
    }

    try:
        update_spark_context(query=query)
        stats["context_updated"] = True
    except Exception as e:
        stats["errors"].append("context")
        log_debug("bridge_worker", "context update failed", e)

    try:
        stats["memory"] = process_recent_memory_events(limit=memory_limit)
    except Exception as e:
        stats["errors"].append("memory")
        log_debug("bridge_worker", "memory capture failed", e)

    try:
        events = read_recent_events(40)
        for e in reversed(events[-10:]):
            if e.event_type != EventType.USER_PROMPT:
                continue
            payload = (e.data or {}).get("payload") or {}
            if payload.get("role") != "user":
                continue
            txt = str(payload.get("text") or "").strip()
            parsed = parse_like_message(txt)
            if parsed:
                add_item(**parsed)
                stats["tastebank_saved"] = True
                break
    except Exception as e:
        stats["errors"].append("tastebank")
        log_debug("bridge_worker", "tastebank capture failed", e)

    try:
        stats["pattern_processed"] = process_pattern_events(limit=pattern_limit)
    except Exception as e:
        stats["errors"].append("patterns")
        log_debug("bridge_worker", "pattern detection failed", e)

    return stats


def write_bridge_heartbeat(stats: Dict[str, Any]) -> bool:
    """Write a heartbeat file so other services can detect liveness."""
    try:
        BRIDGE_HEARTBEAT_FILE.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "ts": time.time(),
            "stats": {
                "context_updated": bool(stats.get("context_updated")),
                "pattern_processed": int(stats.get("pattern_processed") or 0),
                "memory": stats.get("memory") or {},
                "errors": stats.get("errors") or [],
            },
        }
        BRIDGE_HEARTBEAT_FILE.write_text(json.dumps(payload), encoding="utf-8")
        return True
    except Exception as e:
        log_debug("bridge_worker", "heartbeat write failed", e)
        return False


def read_bridge_heartbeat() -> Optional[Dict[str, Any]]:
    """Read bridge worker heartbeat (if any)."""
    if not BRIDGE_HEARTBEAT_FILE.exists():
        return None
    try:
        return json.loads(BRIDGE_HEARTBEAT_FILE.read_text(encoding="utf-8"))
    except Exception as e:
        log_debug("bridge_worker", "heartbeat read failed", e)
        return None


def bridge_heartbeat_age_s() -> Optional[float]:
    """Return heartbeat age in seconds, or None if missing."""
    data = read_bridge_heartbeat()
    if not data:
        return None
    try:
        ts = float(data.get("ts") or 0.0)
    except Exception:
        return None
    if ts <= 0:
        return None
    return max(0.0, time.time() - ts)
