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
from lib.validation_loop import process_validation_events
from lib.prediction_loop import process_prediction_cycle
from lib.content_learner import learn_from_edit_event
from lib.chips import process_chip_events
from lib.chip_merger import merge_chip_insights
from lib.context_sync import sync_context
from lib.diagnostics import log_debug
from lib.advisor import report_outcome


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
        "validation": {},
        "prediction": {},
        "content_learned": 0,
        "chips": {},
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

    events = read_recent_events(40)
    try:
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

    try:
        stats["validation"] = process_validation_events(limit=pattern_limit)
    except Exception as e:
        stats["errors"].append("validation")
        log_debug("bridge_worker", "validation loop failed", e)

    try:
        stats["prediction"] = process_prediction_cycle(limit=pattern_limit)
    except Exception as e:
        stats["errors"].append("prediction")
        log_debug("bridge_worker", "prediction loop failed", e)

    # Content learning from Edit/Write events
    try:
        content_count = 0
        for ev in events:
            if ev.event_type != EventType.POST_TOOL:
                continue
            tool = (ev.tool_name or "").strip()
            if tool not in ("Edit", "Write"):
                continue
            tool_input = ev.tool_input or {}
            payload = (ev.data or {}).get("payload") or {}
            file_path = (
                tool_input.get("file_path")
                or tool_input.get("path")
                or payload.get("file_path")
                or payload.get("path")
                or ""
            )
            content = (
                tool_input.get("new_string")
                or tool_input.get("content")
                or payload.get("new_string")
                or payload.get("content")
                or ""
            )
            if file_path and content and len(content) > 50:
                patterns = learn_from_edit_event(file_path, content)
                if patterns:
                    content_count += len(patterns)
        stats["content_learned"] = content_count
    except Exception as e:
        stats["errors"].append("content_learning")
        log_debug("bridge_worker", "content learning failed", e)

    # Outcome reporting - close the advice feedback loop
    try:
        outcome_count = 0
        for ev in events:
            tool = (ev.tool_name or "").strip()
            if not tool:
                continue
            trace_id = (ev.data or {}).get("trace_id")
            if ev.event_type == EventType.POST_TOOL:
                report_outcome(tool, success=True, advice_helped=True, trace_id=trace_id)
                outcome_count += 1
            elif ev.event_type == EventType.POST_TOOL_FAILURE:
                report_outcome(tool, success=False, advice_helped=False, trace_id=trace_id)
                outcome_count += 1
        stats["outcomes_reported"] = outcome_count
    except Exception as e:
        stats["errors"].append("outcome_reporting")
        log_debug("bridge_worker", "outcome reporting failed", e)

    # Chip processing - domain-specific insights
    try:
        # Convert events to dict format for chip processing
        chip_events = []
        for ev in events:
            chip_events.append({
                "event_type": ev.event_type.value if hasattr(ev.event_type, 'value') else str(ev.event_type),
                "tool_name": ev.tool_name,
                "tool_input": ev.tool_input or {},
                "data": ev.data or {},
                "cwd": (ev.data or {}).get("cwd"),
            })
        # Extract project path from events if available
        project_path = None
        for ev in events:
            cwd = (ev.data or {}).get("cwd")
            if cwd:
                project_path = str(cwd)
                break
        stats["chips"] = process_chip_events(chip_events, project_path)
    except Exception as e:
        stats["errors"].append("chips")
        log_debug("bridge_worker", "chip processing failed", e)

    # Chip merger - promote high-value chip insights to cognitive system
    try:
        merge_stats = merge_chip_insights(min_confidence=0.7, limit=20)
        stats["chip_merge"] = {
            "processed": merge_stats.get("processed", 0),
            "merged": merge_stats.get("merged", 0),
            "by_chip": merge_stats.get("by_chip", {}),
        }
    except Exception as e:
        stats["errors"].append("chip_merge")
        log_debug("bridge_worker", "chip merge failed", e)

    # Context sync - promote insights to CLAUDE.md and sync to Mind
    try:
        sync_result = sync_context()
        # sync_result is a SyncStats object
        stats["sync"] = {
            "selected": getattr(sync_result, "selected", 0),
            "promoted": getattr(sync_result, "promoted_selected", 0),
            "targets": getattr(sync_result, "targets", {}),
        }
    except Exception as e:
        stats["errors"].append("sync")
        log_debug("bridge_worker", "context sync failed", e)

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
                "content_learned": int(stats.get("content_learned") or 0),
                "memory": stats.get("memory") or {},
                "validation": stats.get("validation") or {},
                "chips": stats.get("chips") or {},
                "chip_merge": stats.get("chip_merge") or {},
                "sync": stats.get("sync") or {},
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
