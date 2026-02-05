"""Single-cycle bridge worker execution + heartbeat helpers.

Updated to use the new processing pipeline for adaptive batch sizing,
priority processing, queue consumption, and deep learning extraction.
"""

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


BRIDGE_HEARTBEAT_FILE = Path.home() / ".spark" / "bridge_worker_heartbeat.json"


def run_bridge_cycle(
    *,
    query: Optional[str] = None,
    memory_limit: int = 60,
    pattern_limit: int = 200,
) -> Dict[str, Any]:
    """Run one bridge_worker cycle and return stats.

    Uses the new processing pipeline for event consumption and deep learning,
    while keeping all existing subsystems (memory, tastebank, chips, etc.).

    Performance: Uses batch/deferred save mode on CognitiveLearner and
    MetaRalph to avoid writing large JSON files on every individual
    insight/roast (the #1 cause of CPU/memory leakage in the loop).
    """
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

    # --- Enable batch mode on heavy-I/O singletons ---
    # This defers all disk writes until end_batch(), preventing
    # hundreds of 500KB+ read-write cycles per bridge cycle.
    try:
        from lib.cognitive_learner import get_cognitive_learner
        cognitive = get_cognitive_learner()
        cognitive.begin_batch()
    except Exception:
        cognitive = None

    try:
        from lib.meta_ralph import get_meta_ralph
        meta_ralph = get_meta_ralph()
        meta_ralph.begin_batch()
    except Exception:
        meta_ralph = None

    try:
        # --- Context update ---
        try:
            update_spark_context(query=query)
            stats["context_updated"] = True
        except Exception as e:
            stats["errors"].append("context")
            log_debug("bridge_worker", "context update failed", e)

        # --- Memory capture ---
        try:
            stats["memory"] = process_recent_memory_events(limit=memory_limit)
        except Exception as e:
            stats["errors"].append("memory")
            log_debug("bridge_worker", "memory capture failed", e)

        # --- Run the processing pipeline ---
        pipeline_metrics = None
        try:
            from lib.pipeline import run_processing_cycle
            pipeline_metrics = run_processing_cycle()
            stats["pattern_processed"] = pipeline_metrics.events_processed
            stats["pipeline"] = pipeline_metrics.to_dict()
        except Exception as e:
            stats["errors"].append("pipeline")
            log_debug("bridge_worker", "pipeline processing failed", e)
            # Fallback to old pattern detection if pipeline fails
            try:
                stats["pattern_processed"] = process_pattern_events(limit=pattern_limit)
            except Exception as e2:
                stats["errors"].append("patterns_fallback")
                log_debug("bridge_worker", "fallback pattern detection failed", e2)

        # --- Get events (single source, used by all downstream) ---
        if pipeline_metrics and getattr(pipeline_metrics, "processed_events", None):
            events = pipeline_metrics.processed_events
        else:
            events = read_recent_events(40)

        # --- Single-pass event classification ---
        # Instead of iterating events 5+ separate times, classify once
        # and build all derived lists in one pass.
        user_prompt_events = []
        edit_write_events = []
        chip_events = []
        project_path = None

        for ev in events:
            et = ev.event_type
            tool = (ev.tool_name or "").strip()

            # Tastebank + cognitive signals: user prompts
            if et == EventType.USER_PROMPT:
                user_prompt_events.append(ev)

            # Content learning + cognitive signals: Edit/Write
            if et == EventType.POST_TOOL and tool in ("Edit", "Write"):
                edit_write_events.append(ev)

            # Chip events: all events
            chip_events.append({
                "event_type": et.value if hasattr(et, 'value') else str(et),
                "tool_name": ev.tool_name,
                "tool_input": ev.tool_input or {},
                "data": ev.data or {},
                "cwd": (ev.data or {}).get("cwd"),
            })

            # Project path: first cwd found
            if project_path is None:
                cwd = (ev.data or {}).get("cwd")
                if cwd:
                    project_path = str(cwd)

        # --- Tastebank (uses classified user_prompt_events) ---
        try:
            for e in reversed(user_prompt_events[-10:]):
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

        # --- Validation and prediction loops ---
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

        # --- Content learning (uses classified edit_write_events) ---
        try:
            content_count = 0
            for ev in edit_write_events:
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

        # --- Cognitive signal extraction (uses classified lists) ---
        try:
            from lib.cognitive_signals import extract_cognitive_signals
            for ev in user_prompt_events:
                payload = (ev.data or {}).get("payload") or {}
                txt = str(payload.get("text") or "").strip()
                if txt and len(txt) >= 10:
                    ev_trace = (ev.data or {}).get("trace_id")
                    extract_cognitive_signals(txt, ev.session_id, trace_id=ev_trace)
            for ev in edit_write_events:
                ti = ev.tool_input or {}
                content = ti.get("content") or ti.get("new_string") or ""
                if content and len(content) > 50:
                    ev_trace = (ev.data or {}).get("trace_id")
                    extract_cognitive_signals(content, ev.session_id, trace_id=ev_trace)
        except Exception as e:
            stats["errors"].append("cognitive_signals")
            log_debug("bridge_worker", "cognitive signal extraction failed", e)

        # --- Chip processing (uses pre-built chip_events list) ---
        try:
            stats["chips"] = process_chip_events(chip_events, project_path)
        except Exception as e:
            stats["errors"].append("chips")
            log_debug("bridge_worker", "chip processing failed", e)

        # --- Chip merger ---
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

        # --- Context sync ---
        try:
            sync_result = sync_context()
            stats["sync"] = {
                "selected": getattr(sync_result, "selected", 0),
                "promoted": getattr(sync_result, "promoted_selected", 0),
                "targets": getattr(sync_result, "targets", {}),
            }
        except Exception as e:
            stats["errors"].append("sync")
            log_debug("bridge_worker", "context sync failed", e)

    finally:
        # --- Flush all deferred saves (single write per file) ---
        if cognitive:
            try:
                cognitive.end_batch()
            except Exception as e:
                log_debug("bridge_worker", "cognitive flush failed", e)
        if meta_ralph:
            try:
                meta_ralph.end_batch()
            except Exception as e:
                log_debug("bridge_worker", "meta_ralph flush failed", e)

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
