"""Single-cycle bridge worker execution + heartbeat helpers.

Updated to use the new processing pipeline for adaptive batch sizing,
priority processing, queue consumption, and deep learning extraction.
"""

from __future__ import annotations

import json
import os
import time
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError
from pathlib import Path
from typing import Any, Callable, Dict, Optional, Tuple

from lib.bridge import update_spark_context
from lib.memory_capture import process_recent_memory_events
from lib.tastebank import parse_like_message, add_item
from lib.queue import read_recent_events, EventType
from lib.pattern_detection import process_pattern_events
from lib.validation_loop import process_validation_events, process_outcome_validation
from lib.prediction_loop import process_prediction_cycle
from lib.content_learner import learn_from_edit_event
from lib.chips import process_chip_events
from lib.chip_merger import merge_chip_insights
from lib.context_sync import sync_context
from lib.diagnostics import log_debug


BRIDGE_HEARTBEAT_FILE = Path.home() / ".spark" / "bridge_worker_heartbeat.json"

# --- OpenClaw notification integration ---
SPARK_OPENCLAW_NOTIFY = os.environ.get("SPARK_OPENCLAW_NOTIFY", "1").strip().lower() not in {
    "0", "false", "no", "off"
}
_NOTIFY_COOLDOWN_S = 300  # 5 minutes
_last_notify_time: float = 0.0
BRIDGE_STEP_TIMEOUT_S = float(os.environ.get("SPARK_BRIDGE_STEP_TIMEOUT_S", "45"))
BRIDGE_DISABLE_TIMEOUTS = os.environ.get("SPARK_BRIDGE_DISABLE_TIMEOUTS", "0").strip().lower() in {
    "1", "true", "yes", "on"
}


def _run_step(name: str, fn: Callable[..., Any], *args: Any, timeout_s: Optional[float] = None, **kwargs: Any) -> Tuple[bool, Any, str]:
    """
    Run a bridge sub-step with a soft timeout.

    Returns:
      (ok, result, error_message)
    """
    timeout = BRIDGE_STEP_TIMEOUT_S if timeout_s is None else float(timeout_s)
    if BRIDGE_DISABLE_TIMEOUTS or timeout <= 0:
        try:
            return True, fn(*args, **kwargs), ""
        except Exception as e:
            return False, None, str(e)

    pool = ThreadPoolExecutor(max_workers=1, thread_name_prefix=f"spark_{name}")
    future = pool.submit(fn, *args, **kwargs)
    try:
        return True, future.result(timeout=timeout), ""
    except FuturesTimeoutError:
        future.cancel()
        return False, None, f"timeout after {timeout:.0f}s"
    except Exception as e:
        return False, None, str(e)
    finally:
        pool.shutdown(wait=False, cancel_futures=True)


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
    # Disable fastembed to prevent 8GB+ memory spike from ONNX model loading.
    # Embeddings are optional; prediction/outcome matching falls back to keyword matching.
    import os
    os.environ.setdefault("SPARK_EMBEDDINGS", "0")

    stats: Dict[str, Any] = {
        "timestamp": time.time(),
        "context_updated": False,
        "memory": {},
        "tastebank_saved": False,
        "pattern_processed": 0,
        "validation": {},
        "outcome_validation": {},
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
        ok, _result, error = _run_step("context", update_spark_context, query=query)
        if ok:
            stats["context_updated"] = True
        else:
            stats["errors"].append("context")
            log_debug("bridge_worker", f"context update failed ({error})", None)

        # --- Memory capture ---
        ok, memory_stats, error = _run_step("memory", process_recent_memory_events, limit=memory_limit)
        if ok:
            stats["memory"] = memory_stats or {}
        else:
            stats["errors"].append("memory")
            log_debug("bridge_worker", f"memory capture failed ({error})", None)

        # --- Run the processing pipeline ---
        pipeline_metrics = None
        try:  # keep import error handling separate
            from lib.pipeline import run_processing_cycle
            ok, pipeline_metrics, error = _run_step("pipeline", run_processing_cycle)
            if ok and pipeline_metrics is not None:
                stats["pattern_processed"] = pipeline_metrics.events_processed
                stats["pipeline"] = pipeline_metrics.to_dict()
            else:
                stats["errors"].append("pipeline")
                log_debug("bridge_worker", f"pipeline processing failed ({error})", None)
        except Exception as e:
            stats["errors"].append("pipeline")
            log_debug("bridge_worker", "pipeline processing failed", e)
        # Fallback to old pattern detection if pipeline fails
        if pipeline_metrics is None:
            ok, fallback_count, error = _run_step("patterns_fallback", process_pattern_events, limit=pattern_limit)
            if ok:
                stats["pattern_processed"] = int(fallback_count or 0)
            else:
                stats["errors"].append("patterns_fallback")
                log_debug("bridge_worker", f"fallback pattern detection failed ({error})", None)

        # --- Get events (single source, used by all downstream) ---
        if pipeline_metrics and getattr(pipeline_metrics, "processed_events", None):
            events = pipeline_metrics.processed_events
            # Release reference from metrics to prevent memory accumulation
            pipeline_metrics.processed_events = []
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
        ok, validation_stats, error = _run_step("validation", process_validation_events, limit=pattern_limit)
        if ok:
            stats["validation"] = validation_stats or {}
        else:
            stats["errors"].append("validation")
            log_debug("bridge_worker", f"validation loop failed ({error})", None)

        # Explicit outcome-linked validation loop (was previously CLI-only).
        ok, outcome_stats, error = _run_step("outcome_validation", process_outcome_validation, limit=pattern_limit)
        if ok:
            stats["outcome_validation"] = outcome_stats or {}
        else:
            stats["errors"].append("outcome_validation")
            log_debug("bridge_worker", f"outcome validation failed ({error})", None)

        ok, prediction_stats, error = _run_step("prediction", process_prediction_cycle, limit=pattern_limit)
        if ok:
            stats["prediction"] = prediction_stats or {}
        else:
            stats["errors"].append("prediction")
            log_debug("bridge_worker", f"prediction loop failed ({error})", None)

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
        ok, chip_stats, error = _run_step("chips", process_chip_events, chip_events, project_path)
        if ok:
            stats["chips"] = chip_stats or {}
        else:
            stats["errors"].append("chips")
            log_debug("bridge_worker", f"chip processing failed ({error})", None)

        # --- Engagement Pulse: check for pending snapshots ---
        def _poll_engagement_pulse():
            from lib.engagement_tracker import get_engagement_tracker
            tracker = get_engagement_tracker()
            pending = tracker.get_pending_snapshots()
            tracker.cleanup_old(max_age_days=7)
            return {"pending_snapshots": len(pending), "tracked": len(tracker.tracked)}

        ok, pulse_stats, error = _run_step("engagement_pulse", _poll_engagement_pulse)
        if ok:
            stats["engagement_pulse"] = pulse_stats or {}
        else:
            stats["errors"].append("engagement_pulse")

        # --- Chip merger ---
        ok, merge_stats, error = _run_step(
            "chip_merge",
            merge_chip_insights,
            min_confidence=0.7,
            min_quality_score=0.7,
            limit=20,
        )
        if ok:
            stats["chip_merge"] = {
                "processed": merge_stats.get("processed", 0),
                "merged": merge_stats.get("merged", 0),
                "skipped_low_quality": merge_stats.get("skipped_low_quality", 0),
                "by_chip": merge_stats.get("by_chip", {}),
            }
        else:
            stats["errors"].append("chip_merge")
            log_debug("bridge_worker", f"chip merge failed ({error})", None)

        # --- Context sync ---
        ok, sync_result, error = _run_step("sync", sync_context)
        if ok:
            stats["sync"] = {
                "selected": getattr(sync_result, "selected", 0),
                "promoted": getattr(sync_result, "promoted_selected", 0),
                "targets": getattr(sync_result, "targets", {}),
            }
        else:
            stats["errors"].append("sync")
            log_debug("bridge_worker", f"context sync failed ({error})", None)

        # --- Auto-tuner: periodic source boost optimization ---
        try:
            from lib.auto_tuner import AutoTuner
            tuner = AutoTuner()
            if tuner.should_run():
                # Phase 1: Source boost optimization (existing)
                report = tuner.run()
                # Phase 2: Broader system health recommendations
                health = tuner.measure_system_health()
                recs = tuner.compute_recommendations(health)
                tune_mode = tuner._config.get("mode", "suggest")
                applied = tuner.apply_recommendations(recs, mode=tune_mode)
                stats["auto_tuner"] = {
                    "changes": len(report.changes),
                    "skipped": len(report.skipped),
                    "health_recs": len(recs),
                    "health_applied": len(applied),
                }
        except Exception as e:
            log_debug("bridge_worker", f"auto-tuner failed ({e})", None)

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

        # --- Memory cleanup (prevent accumulation across cycles) ---
        # Clear event references to allow GC
        events = None
        user_prompt_events = None
        edit_write_events = None
        chip_events = None
        pipeline_metrics = None
        try:
            # Clear aggregator session pattern cache to prevent unbounded growth
            from lib.pattern_detection.aggregator import get_aggregator
            agg = get_aggregator()
            if hasattr(agg, '_session_patterns'):
                # Keep only last 5 sessions
                keys = list(agg._session_patterns.keys())
                if len(keys) > 5:
                    for k in keys[:-5]:
                        del agg._session_patterns[k]
        except Exception:
            pass
        import gc
        gc.collect()

    # --- OpenClaw notification (event-driven push) ---
    if SPARK_OPENCLAW_NOTIFY:
        _maybe_notify_openclaw(stats)

    return stats


def _maybe_notify_openclaw(stats: Dict[str, Any]) -> None:
    """Push a wake event to OpenClaw if this cycle found something significant."""
    global _last_notify_time

    now = time.time()
    if now - _last_notify_time < _NOTIFY_COOLDOWN_S:
        return

    findings: list[str] = []

    # Check pipeline / pattern processing
    pattern_count = int(stats.get("pattern_processed") or 0)
    if pattern_count > 0:
        findings.append(f"{pattern_count} patterns processed")

    # Check chip merge for high-quality merges
    chip_merge = stats.get("chip_merge") or {}
    merged = int(chip_merge.get("merged") or 0)
    if merged > 0:
        findings.append(f"{merged} insights merged")

    # Check auto-tuner adjustments
    auto_tuner = stats.get("auto_tuner") or {}
    tuner_changes = int(auto_tuner.get("changes") or 0) + int(auto_tuner.get("health_applied") or 0)
    if tuner_changes > 0:
        findings.append(f"auto-tuner made {tuner_changes} adjustments")

    # Check validation for contradictions / surprises
    validation = stats.get("validation") or {}
    surprises = int(validation.get("surprises") or 0)
    if surprises > 0:
        findings.append(f"{surprises} contradictions detected")

    # Check content learning
    content_learned = int(stats.get("content_learned") or 0)
    if content_learned >= 3:
        findings.append(f"{content_learned} content patterns learned")

    if not findings:
        return

    try:
        from lib.openclaw_notify import notify_agent, wake_agent

        summary = "Spark bridge cycle: " + ", ".join(findings)
        notify_agent(summary, priority="normal")
        wake_agent(
            f"🔮 Spark found something — read SPARK_CONTEXT.md and SPARK_NOTIFICATIONS.md. Summary: {summary}"
        )
        _last_notify_time = now
    except Exception as e:
        log_debug("bridge_worker", f"openclaw notify failed: {e}", None)


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
                "outcome_validation": stats.get("outcome_validation") or {},
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
