"""
Spark Processing Pipeline: Adaptive, priority-aware event processing.

Replaces the shallow "read last 40 events" approach with a production-grade
pipeline that:

1. Processes events in priority order (failures/prompts first)
2. Consumes processed events so the queue stays bounded
3. Adapts batch size based on queue depth (backpressure)
4. Extracts deep learnings from event batches (tool effectiveness,
   error patterns, session workflows)
5. Emits processing health metrics for observability
6. Auto-tunes processing frequency based on throughput

Design Principles:
- Never lose events (consume only after successful processing)
- Never slow down the hooks (all processing is async)
- Maximize learning yield per batch (smart aggregation)
- Keep queue depth stable (consume >= produce)
"""

from __future__ import annotations

import json
import time
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from lib.queue import (
    EventType,
    SparkEvent,
    EventPriority,
    classify_event_priority,
    consume_processed,
    count_events,
    read_events,
)
from lib.diagnostics import log_debug


# ============= Configuration =============

# Batch size bounds for auto-tuning
# DEFAULT_BATCH_SIZE is overridden by tuneables.json → values.queue_batch_size
MIN_BATCH_SIZE = 50
MAX_BATCH_SIZE = 1000
DEFAULT_BATCH_SIZE = 200


def _load_pipeline_config() -> None:
    """Load pipeline tuneables from ~/.spark/tuneables.json → "values" section."""
    global DEFAULT_BATCH_SIZE
    try:
        from pathlib import Path
        tuneables = Path.home() / ".spark" / "tuneables.json"
        if not tuneables.exists():
            return
        data = json.loads(tuneables.read_text(encoding="utf-8"))
        values = data.get("values") or {}
        if isinstance(values, dict) and "queue_batch_size" in values:
            batch = int(values["queue_batch_size"])
            DEFAULT_BATCH_SIZE = max(MIN_BATCH_SIZE, min(MAX_BATCH_SIZE, batch))
    except Exception:
        pass


_load_pipeline_config()

# Backpressure thresholds
QUEUE_HEALTHY = 200       # Below this, normal processing
QUEUE_ELEVATED = 500      # Increase batch size
QUEUE_CRITICAL = 2000     # Maximum batch size + drain mode

# Processing health metrics file
PIPELINE_STATE_FILE = Path.home() / ".spark" / "pipeline_state.json"
PIPELINE_METRICS_FILE = Path.home() / ".spark" / "pipeline_metrics.json"


@dataclass
class ProcessingMetrics:
    """Metrics from a single processing cycle."""
    cycle_start: float = 0.0
    cycle_duration_ms: float = 0.0
    events_read: int = 0
    events_processed: int = 0
    events_consumed: int = 0
    events_remaining: int = 0
    batch_size_used: int = 0

    # Learning yield
    patterns_detected: int = 0
    insights_created: int = 0
    tool_effectiveness_updates: int = 0
    error_patterns_found: int = 0
    session_workflows_analyzed: int = 0

    # Priority breakdown
    high_priority_processed: int = 0
    medium_priority_processed: int = 0
    low_priority_processed: int = 0

    # Health indicators
    queue_depth_before: int = 0
    queue_depth_after: int = 0
    processing_rate_eps: float = 0.0  # events per second
    backpressure_level: str = "healthy"

    errors: List[str] = field(default_factory=list)

    # The actual events processed this cycle.  Used by bridge_cycle to feed
    # downstream subsystems without re-reading the (now consumed) queue.
    # Intentionally excluded from to_dict() to keep serialized metrics small.
    processed_events: List[Any] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "cycle_start": self.cycle_start,
            "cycle_duration_ms": self.cycle_duration_ms,
            "events_read": self.events_read,
            "events_processed": self.events_processed,
            "events_consumed": self.events_consumed,
            "events_remaining": self.events_remaining,
            "batch_size_used": self.batch_size_used,
            "learning_yield": {
                "patterns_detected": self.patterns_detected,
                "insights_created": self.insights_created,
                "tool_effectiveness_updates": self.tool_effectiveness_updates,
                "error_patterns_found": self.error_patterns_found,
                "session_workflows_analyzed": self.session_workflows_analyzed,
            },
            "priority_breakdown": {
                "high": self.high_priority_processed,
                "medium": self.medium_priority_processed,
                "low": self.low_priority_processed,
            },
            "health": {
                "queue_depth_before": self.queue_depth_before,
                "queue_depth_after": self.queue_depth_after,
                "processing_rate_eps": round(self.processing_rate_eps, 1),
                "backpressure_level": self.backpressure_level,
            },
            "errors": self.errors,
        }


def _load_pipeline_state() -> Dict:
    if PIPELINE_STATE_FILE.exists():
        try:
            return json.loads(PIPELINE_STATE_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {
        "last_batch_size": DEFAULT_BATCH_SIZE,
        "last_processing_rate": 0.0,
        "consecutive_empty_cycles": 0,
        "total_events_processed": 0,
        "total_insights_created": 0,
        "last_cycle_ts": 0.0,
    }


def _save_pipeline_state(state: Dict) -> None:
    PIPELINE_STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    PIPELINE_STATE_FILE.write_text(
        json.dumps(state, indent=2), encoding="utf-8"
    )


def _save_pipeline_metrics(metrics: ProcessingMetrics) -> None:
    """Append metrics to a rolling log (keeps last 100 entries)."""
    PIPELINE_METRICS_FILE.parent.mkdir(parents=True, exist_ok=True)
    entries: List[Dict] = []
    if PIPELINE_METRICS_FILE.exists():
        try:
            entries = json.loads(
                PIPELINE_METRICS_FILE.read_text(encoding="utf-8")
            )
        except Exception:
            entries = []
    entries.append(metrics.to_dict())
    # Keep last 100 entries for trend analysis
    entries = entries[-100:]
    PIPELINE_METRICS_FILE.write_text(
        json.dumps(entries, indent=2), encoding="utf-8"
    )


# ============= Adaptive Batch Sizing =============

def compute_batch_size(queue_depth: int, state: Dict) -> int:
    """Compute the optimal batch size based on queue depth and history.

    Strategy:
    - Healthy queue (< 200): Use default batch size
    - Elevated queue (200-500): Double batch size
    - Critical queue (500-2000): Quadruple batch size
    - Emergency (> 2000): Maximum batch size (drain mode)

    Also factors in previous processing rate to avoid overwhelming the system.
    """
    if queue_depth <= QUEUE_HEALTHY:
        base = DEFAULT_BATCH_SIZE
    elif queue_depth <= QUEUE_ELEVATED:
        base = DEFAULT_BATCH_SIZE * 2
    elif queue_depth <= QUEUE_CRITICAL:
        base = DEFAULT_BATCH_SIZE * 4
    else:
        base = MAX_BATCH_SIZE

    # If previous cycle was fast, allow bigger batches
    last_rate = state.get("last_processing_rate", 0.0)
    if last_rate > 500:  # More than 500 events/sec
        base = min(MAX_BATCH_SIZE, int(base * 1.5))

    return max(MIN_BATCH_SIZE, min(MAX_BATCH_SIZE, base))


def compute_backpressure_level(queue_depth: int) -> str:
    """Classify queue pressure level for observability."""
    if queue_depth <= QUEUE_HEALTHY:
        return "healthy"
    elif queue_depth <= QUEUE_ELEVATED:
        return "elevated"
    elif queue_depth <= QUEUE_CRITICAL:
        return "critical"
    else:
        return "emergency"


# ============= Deep Learning Extraction =============

def extract_tool_effectiveness(events: List[SparkEvent]) -> Dict[str, Any]:
    """Extract tool effectiveness metrics from a batch of events.

    This is the missing piece -- the current system has tool_effectiveness = 0
    despite thousands of events because nothing aggregates success/failure
    rates into actual learnings.

    Enhanced to:
    - Collect common error messages per tool for root-cause insights
    - Detect success-after-failure patterns (recovery signals)
    - Track tool combinations that predict success/failure

    Returns a dict with tool-level statistics and generated insights.
    """
    tool_stats: Dict[str, Dict[str, Any]] = defaultdict(
        lambda: {"success": 0, "failure": 0, "total": 0, "errors": []}
    )

    # Track tool sequences per session for recovery detection
    session_sequences: Dict[str, List[Tuple[str, bool]]] = defaultdict(list)

    for event in events:
        tool = (event.tool_name or "").strip()
        if not tool:
            continue

        if event.event_type == EventType.POST_TOOL:
            tool_stats[tool]["success"] += 1
            tool_stats[tool]["total"] += 1
            session_sequences[event.session_id].append((tool, True))
        elif event.event_type == EventType.POST_TOOL_FAILURE:
            tool_stats[tool]["failure"] += 1
            tool_stats[tool]["total"] += 1
            err = (event.error or "")[:150].strip()
            if err:
                tool_stats[tool]["errors"].append(err)
            session_sequences[event.session_id].append((tool, False))

    # Generate learnings from the stats
    insights: List[Dict[str, Any]] = []
    for tool, stats in tool_stats.items():
        if stats["total"] < 3:
            continue  # Need enough data

        success_rate = stats["success"] / stats["total"] if stats["total"] > 0 else 0

        # Low success rate with error details
        if success_rate < 0.5 and stats["total"] >= 5:
            # Summarize top errors
            error_counter = Counter(e[:80] for e in stats["errors"])
            top_errors = error_counter.most_common(3)
            error_summary = "; ".join(
                f"{err} ({cnt}x)" for err, cnt in top_errors
            ) if top_errors else "no error details"
            insights.append({
                "type": "low_success_rate",
                "tool": tool,
                "success_rate": round(success_rate, 2),
                "total": stats["total"],
                "insight": (
                    f"{tool} has {success_rate:.0%} success rate "
                    f"({stats['failure']}/{stats['total']} failures). "
                    f"Common errors: {error_summary}"
                ),
            })
        elif stats["failure"] >= 3:
            error_counter = Counter(e[:80] for e in stats["errors"])
            top_error = error_counter.most_common(1)
            error_hint = f" Most common: {top_error[0][0]}" if top_error else ""
            insights.append({
                "type": "recurring_failures",
                "tool": tool,
                "failures": stats["failure"],
                "success_rate": round(success_rate, 2),
                "insight": (
                    f"{tool} failed {stats['failure']}/{stats['total']} times "
                    f"({success_rate:.0%} success rate).{error_hint}"
                ),
            })

    # Detect recovery patterns (fail then succeed with same tool)
    recovery_count = 0
    for session_id, seq in session_sequences.items():
        for i in range(1, len(seq)):
            tool, success = seq[i]
            prev_tool, prev_success = seq[i - 1]
            if tool == prev_tool and success and not prev_success:
                recovery_count += 1

    if recovery_count >= 3:
        insights.append({
            "type": "recovery_pattern",
            "recovery_count": recovery_count,
            "insight": (
                f"Detected {recovery_count} recovery patterns "
                f"(tool fail then retry succeed) -- retrying often works"
            ),
        })

    return {
        "tool_stats": {
            k: {"success": v["success"], "failure": v["failure"],
                 "total": v["total"], "success_rate": round(
                     v["success"] / v["total"], 2) if v["total"] > 0 else 0}
            for k, v in tool_stats.items()
        },
        "insights": insights,
        "tools_tracked": len(tool_stats),
    }


def extract_error_patterns(events: List[SparkEvent]) -> Dict[str, Any]:
    """Extract recurring error patterns from failure events.

    Groups errors by tool + error signature to find systematic issues.
    """
    error_groups: Dict[str, List[str]] = defaultdict(list)

    for event in events:
        if event.event_type != EventType.POST_TOOL_FAILURE:
            continue
        tool = (event.tool_name or "unknown").strip()
        error = (event.error or "").strip()
        if not error:
            continue
        # Normalize error to first 100 chars for grouping
        error_key = f"{tool}:{error[:100]}"
        error_groups[error_key].append(error[:300])

    patterns: List[Dict[str, Any]] = []
    for key, errors in error_groups.items():
        if len(errors) >= 2:  # Recurring pattern
            tool, error_prefix = key.split(":", 1)
            patterns.append({
                "tool": tool,
                "error_pattern": error_prefix,
                "occurrences": len(errors),
                "insight": f"{tool} fails repeatedly with: {error_prefix[:80]}",
            })

    return {
        "error_patterns": patterns,
        "total_errors": sum(1 for e in events if e.event_type == EventType.POST_TOOL_FAILURE),
    }


def extract_session_workflows(events: List[SparkEvent]) -> Dict[str, Any]:
    """Analyze tool usage patterns within sessions.

    Identifies common sequences and anti-patterns like:
    - Edit without preceding Read (risky)
    - Multiple consecutive failures (struggling)
    - Effective tool chains (Read -> Edit -> Read verify)

    Deduplicates insights to avoid noise -- counts occurrences rather
    than emitting one insight per occurrence.
    """
    sessions: Dict[str, List[Tuple[str, str]]] = defaultdict(list)

    for event in events:
        tool = (event.tool_name or "").strip()
        if not tool:
            continue
        status = "ok" if event.event_type == EventType.POST_TOOL else "fail"
        sessions[event.session_id].append((tool, status))

    # Aggregate pattern counts instead of listing every occurrence
    struggling_sessions: List[Dict[str, Any]] = []
    risky_edit_by_predecessor: Counter = Counter()
    total_edits = 0
    safe_edits = 0

    for session_id, tools in sessions.items():
        if len(tools) < 3:
            continue

        # Detect consecutive failures (struggling)
        max_consecutive_fails = 0
        current_fails = 0
        for _, status in tools:
            if status == "fail":
                current_fails += 1
                max_consecutive_fails = max(max_consecutive_fails, current_fails)
            else:
                current_fails = 0

        if max_consecutive_fails >= 3:
            struggling_sessions.append({
                "session_id": session_id,
                "consecutive_failures": max_consecutive_fails,
            })

        # Count Edit-without-Read patterns (aggregated)
        for i, (tool, _) in enumerate(tools):
            if tool == "Edit":
                total_edits += 1
                if i > 0:
                    prev_tool = tools[i - 1][0]
                    if prev_tool != "Read":
                        risky_edit_by_predecessor[prev_tool] += 1
                    else:
                        safe_edits += 1
                else:
                    risky_edit_by_predecessor["(first_action)"] += 1

    workflow_insights: List[Dict[str, Any]] = []

    # Emit aggregated struggling insight
    if struggling_sessions:
        worst = max(s["consecutive_failures"] for s in struggling_sessions)
        workflow_insights.append({
            "type": "struggling",
            "sessions_affected": len(struggling_sessions),
            "worst_streak": worst,
            "insight": (
                f"{len(struggling_sessions)} session(s) had 3+ consecutive "
                f"failures (worst streak: {worst}). Consider different "
                f"approach when stuck."
            ),
        })

    # Emit aggregated risky-edit insight
    risky_total = sum(risky_edit_by_predecessor.values())
    if risky_total >= 2 and total_edits > 0:
        risky_pct = risky_total / total_edits
        top_predecessors = risky_edit_by_predecessor.most_common(3)
        pred_str = ", ".join(
            f"{pred} ({cnt}x)" for pred, cnt in top_predecessors
        )
        workflow_insights.append({
            "type": "risky_edit",
            "risky_count": risky_total,
            "total_edits": total_edits,
            "safe_count": safe_edits,
            "insight": (
                f"{risky_total}/{total_edits} Edits ({risky_pct:.0%}) "
                f"not preceded by Read. Preceded by: {pred_str}. "
                f"Always Read before Edit to avoid mismatch errors."
            ),
        })

    return {
        "sessions_analyzed": len(sessions),
        "workflow_insights": workflow_insights,
    }


def store_deep_learnings(
    tool_effectiveness: Dict[str, Any],
    error_patterns: Dict[str, Any],
    session_workflows: Dict[str, Any],
) -> int:
    """Store extracted learnings in the cognitive system.

    Returns the count of insights actually stored.
    """
    stored = 0

    try:
        from lib.cognitive_learner import get_cognitive_learner, CognitiveCategory
        learner = get_cognitive_learner()

        # Tool effectiveness insights
        for insight_data in tool_effectiveness.get("insights", []):
            result = learner.add_insight(
                category=CognitiveCategory.SELF_AWARENESS,
                insight=insight_data["insight"],
                context=f"tool_effectiveness:{insight_data['tool']}",
                confidence=0.7,
            )
            if result:
                stored += 1

        # Error pattern insights
        for pattern in error_patterns.get("error_patterns", []):
            result = learner.add_insight(
                category=CognitiveCategory.SELF_AWARENESS,
                insight=pattern["insight"],
                context=f"error_pattern:{pattern['tool']}",
                confidence=0.75,
            )
            if result:
                stored += 1

        # Workflow anti-pattern insights
        for insight_data in session_workflows.get("workflow_insights", []):
            if insight_data["type"] == "risky_edit":
                # This is a known pattern, boost it
                result = learner.add_insight(
                    category=CognitiveCategory.REASONING,
                    insight="Always Read a file before Edit to verify current content",
                    context=f"workflow_antipattern:{insight_data.get('session_id', '')}",
                    confidence=0.8,
                )
            elif insight_data["type"] == "struggling":
                result = learner.add_insight(
                    category=CognitiveCategory.META_LEARNING,
                    insight=insight_data["insight"],
                    context=f"workflow_struggle:{insight_data.get('session_id', '')}",
                    confidence=0.65,
                )
            else:
                result = None
            if result:
                stored += 1

    except Exception as e:
        log_debug("pipeline", "store_deep_learnings failed", e)

    return stored


# ============= Main Processing Pipeline =============

def run_processing_cycle(
    *,
    force_batch_size: Optional[int] = None,
) -> ProcessingMetrics:
    """Run one processing cycle with adaptive batch sizing.

    This is the production replacement for the shallow ``read_recent_events(40)``
    approach in ``bridge_cycle.py``.

    Flow:
    1. Check queue depth, compute batch size
    2. Read events (priority-ordered)
    3. Run pattern detection on the batch
    4. Extract deep learnings (tool effectiveness, errors, workflows)
    5. Store insights in cognitive system
    6. Consume processed events from queue
    7. Emit metrics

    Returns ProcessingMetrics with full observability data.
    """
    metrics = ProcessingMetrics(cycle_start=time.time())
    state = _load_pipeline_state()

    # 1. Check queue depth
    metrics.queue_depth_before = count_events()
    metrics.backpressure_level = compute_backpressure_level(
        metrics.queue_depth_before
    )

    # 2. Compute batch size
    if force_batch_size:
        batch_size = max(MIN_BATCH_SIZE, min(MAX_BATCH_SIZE, force_batch_size))
    else:
        batch_size = compute_batch_size(metrics.queue_depth_before, state)
    metrics.batch_size_used = batch_size

    # 3. Read events from the head of the queue (oldest first = FIFO)
    events = read_events(limit=batch_size, offset=0)
    metrics.events_read = len(events)

    if not events:
        state["consecutive_empty_cycles"] = state.get("consecutive_empty_cycles", 0) + 1
        _save_pipeline_state(state)
        metrics.cycle_duration_ms = (time.time() - metrics.cycle_start) * 1000
        _save_pipeline_metrics(metrics)
        return metrics

    state["consecutive_empty_cycles"] = 0

    # 4. Classify by priority and sort HIGH first for pattern detection
    for event in events:
        priority = classify_event_priority(event)
        if priority == EventPriority.HIGH:
            metrics.high_priority_processed += 1
        elif priority == EventPriority.MEDIUM:
            metrics.medium_priority_processed += 1
        else:
            metrics.low_priority_processed += 1

    # Sort so HIGH-priority events are processed first by pattern detection.
    # This ensures that user prompts and failures (the most valuable events)
    # get full attention even if we can only partially process a huge batch.
    processing_order = sorted(
        events,
        key=lambda e: classify_event_priority(e),
        reverse=True,
    )

    # 5. Run pattern detection (existing system) with priority ordering
    # Map hook_event names to aggregator "type" values for EIDOS step-wrapping.
    _HOOK_TO_AGG_TYPE = {
        "UserPromptSubmit": "user_message",
        "PostToolUse": "action_complete",
        "PostToolUseFailure": "failure",
    }

    pattern_cycle_ok = False
    try:
        from lib.pattern_detection.aggregator import get_aggregator
        aggregator = get_aggregator()

        for event in processing_order:
            hook_event = (event.data or {}).get("hook_event") or ""
            payload = (event.data or {}).get("payload")
            pattern_event = {
                "session_id": event.session_id,
                "hook_event": hook_event,
                "tool_name": event.tool_name,
                "tool_input": event.tool_input,
                "payload": payload,
            }

            # Provide the "type" key the aggregator expects for EIDOS
            agg_type = _HOOK_TO_AGG_TYPE.get(hook_event, "")
            if agg_type:
                pattern_event["type"] = agg_type

            # For user messages, map content so aggregator can create Steps
            if hook_event == "UserPromptSubmit" and isinstance(payload, dict):
                user_text = payload.get("text", "")
                if user_text:
                    pattern_event["content"] = user_text

            trace_id = (event.data or {}).get("trace_id")
            if trace_id:
                pattern_event["trace_id"] = trace_id
            if event.error:
                pattern_event["error"] = event.error

            patterns = aggregator.process_event(pattern_event)
            if patterns:
                aggregator.trigger_learning(patterns)
                metrics.patterns_detected += len(patterns)

        pattern_cycle_ok = True
        metrics.events_processed = len(events)
        metrics.processed_events = list(events)
    except Exception as e:
        metrics.errors.append(f"pattern_detection: {str(e)[:100]}")
        log_debug("pipeline", "pattern detection failed", e)

    if pattern_cycle_ok:
        # 6. Extract deep learnings (THE NEW PART)
        try:
            tool_eff = extract_tool_effectiveness(events)
            metrics.tool_effectiveness_updates = tool_eff.get("tools_tracked", 0)
        except Exception as e:
            tool_eff = {"insights": [], "tool_stats": {}, "tools_tracked": 0}
            metrics.errors.append(f"tool_effectiveness: {str(e)[:100]}")

        try:
            error_pats = extract_error_patterns(events)
            metrics.error_patterns_found = len(error_pats.get("error_patterns", []))
        except Exception as e:
            error_pats = {"error_patterns": [], "total_errors": 0}
            metrics.errors.append(f"error_patterns: {str(e)[:100]}")

        try:
            workflows = extract_session_workflows(events)
            metrics.session_workflows_analyzed = workflows.get("sessions_analyzed", 0)
        except Exception as e:
            workflows = {"sessions_analyzed": 0, "workflow_insights": []}
            metrics.errors.append(f"session_workflows: {str(e)[:100]}")

        # 7. Store deep learnings
        try:
            stored = store_deep_learnings(tool_eff, error_pats, workflows)
            metrics.insights_created = stored
        except Exception as e:
            metrics.errors.append(f"store_learnings: {str(e)[:100]}")
            log_debug("pipeline", "store deep learnings failed", e)

        # 8. Consume processed events from queue
        try:
            consumed = consume_processed(len(events))
            metrics.events_consumed = consumed
            # Reset the pattern detection offset since we've removed lines
            # from the head of the file.  Without this, the worker's saved
            # offset would point past the end of the (now shorter) file.
            if consumed > 0:
                try:
                    from lib.pattern_detection.worker import reset_offset
                    reset_offset()
                except Exception:
                    pass
        except Exception as e:
            metrics.errors.append(f"consume: {str(e)[:100]}")
            log_debug("pipeline", "consume_processed failed", e)
    else:
        metrics.errors.append("consume_skipped:pattern_detection_failed")

    # 9. Final stats
    metrics.events_remaining = count_events()
    metrics.queue_depth_after = metrics.events_remaining

    cycle_time = time.time() - metrics.cycle_start
    metrics.cycle_duration_ms = cycle_time * 1000
    if cycle_time > 0:
        metrics.processing_rate_eps = metrics.events_processed / cycle_time

    # 10. Update pipeline state for auto-tuning
    state["last_batch_size"] = batch_size
    state["last_processing_rate"] = metrics.processing_rate_eps
    state["total_events_processed"] = (
        state.get("total_events_processed", 0) + metrics.events_processed
    )
    state["total_insights_created"] = (
        state.get("total_insights_created", 0) + metrics.insights_created
    )
    state["last_cycle_ts"] = time.time()
    _save_pipeline_state(state)

    # 11. Save metrics for observability
    _save_pipeline_metrics(metrics)

    return metrics


def get_pipeline_health() -> Dict[str, Any]:
    """Get current pipeline health for monitoring.

    Returns a dict with queue depth, processing rate, backlog trend, etc.
    Suitable for the /status endpoint and watchdog checks.
    """
    queue_depth = count_events()
    state = _load_pipeline_state()

    # Load recent metrics for trend analysis
    trend = {"improving": False, "stable": True, "degrading": False}
    recent_rates: List[float] = []
    recent_yields: List[int] = []
    if PIPELINE_METRICS_FILE.exists():
        try:
            entries = json.loads(
                PIPELINE_METRICS_FILE.read_text(encoding="utf-8")
            )
            for entry in entries[-10:]:
                health = entry.get("health", {})
                rate = health.get("processing_rate_eps", 0)
                if rate > 0:
                    recent_rates.append(rate)
                ly = entry.get("learning_yield", {})
                recent_yields.append(ly.get("insights_created", 0))
        except Exception:
            pass

    if len(recent_rates) >= 3:
        first_half = sum(recent_rates[: len(recent_rates) // 2]) / max(
            1, len(recent_rates) // 2
        )
        second_half = sum(recent_rates[len(recent_rates) // 2 :]) / max(
            1, len(recent_rates) - len(recent_rates) // 2
        )
        if second_half > first_half * 1.1:
            trend = {"improving": True, "stable": False, "degrading": False}
        elif second_half < first_half * 0.8:
            trend = {"improving": False, "stable": False, "degrading": True}

    return {
        "queue_depth": queue_depth,
        "backpressure_level": compute_backpressure_level(queue_depth),
        "last_cycle_ts": state.get("last_cycle_ts", 0),
        "last_processing_rate": state.get("last_processing_rate", 0),
        "total_events_processed": state.get("total_events_processed", 0),
        "total_insights_created": state.get("total_insights_created", 0),
        "consecutive_empty_cycles": state.get("consecutive_empty_cycles", 0),
        "trend": trend,
        "avg_processing_rate": (
            round(sum(recent_rates) / len(recent_rates), 1) if recent_rates else 0
        ),
        "avg_learning_yield": (
            round(sum(recent_yields) / len(recent_yields), 1) if recent_yields else 0
        ),
    }


def compute_next_interval(metrics: ProcessingMetrics, base_interval: int = 30) -> int:
    """Compute the optimal interval before the next processing cycle.

    Auto-tunes based on:
    - Queue depth (shorter interval when backlogged)
    - Processing rate (can we handle faster cycles?)
    - Learning yield (slow down if nothing interesting)

    Returns interval in seconds.
    """
    if metrics.backpressure_level == "emergency":
        return 5   # Drain as fast as possible
    elif metrics.backpressure_level == "critical":
        return 10
    elif metrics.backpressure_level == "elevated":
        return 15
    elif metrics.events_read == 0:
        # Nothing to process, back off
        return min(120, base_interval * 2)
    else:
        return base_interval
