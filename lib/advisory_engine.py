"""
Advisory Engine: The core orchestrator for Spark's acted-on advisory system.

This is the single entry point called from observe.py hooks.
It orchestrates the full pipeline:

  State → Retrieval → Gate → Synthesize → Emit

Two tiers:
- Tier 1 (Zero-AI): Works immediately with no external dependencies.
  Uses existing advisor retrieval + programmatic synthesis + stdout emission.

- Tier 2 (AI-Enhanced): Adds LLM-powered synthesis and intent extraction.
  Uses Ollama (local) or cloud APIs. Falls back to Tier 1 seamlessly.

The engine is designed to be FAST. Hooks must complete quickly.
All slow operations (AI synthesis) have tight timeouts.
"""

from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Dict, List, Optional, Any

from .diagnostics import log_debug

# ============= Configuration =============

ENGINE_ENABLED = os.getenv("SPARK_ADVISORY_ENGINE", "1") != "0"
ENGINE_LOG = Path.home() / ".spark" / "advisory_engine.jsonl"
ENGINE_LOG_MAX = 500

# Performance budget: max total time for advisory pipeline per hook call
MAX_ENGINE_MS = float(os.getenv("SPARK_ADVISORY_MAX_MS", "4000"))  # 4 seconds


# ============= Engine Entry Points =============

def on_pre_tool(
    session_id: str,
    tool_name: str,
    tool_input: Optional[dict] = None,
    trace_id: Optional[str] = None,
) -> Optional[str]:
    """
    Called at PreToolUse: retrieve advice, filter, synthesize, emit.

    This is the main advisory pipeline. Returns the emitted text (if any)
    for diagnostics, or None if nothing was emitted.
    """
    if not ENGINE_ENABLED:
        return None

    start_ms = time.time() * 1000

    try:
        # 1. Load session state
        from .advisory_state import (
            load_state, save_state, record_tool_call,
            mark_advice_shown, suppress_tool_advice,
        )
        state = load_state(session_id)

        # Record this tool call (pre-outcome)
        record_tool_call(state, tool_name, tool_input, success=None, trace_id=trace_id)

        # 2. Retrieve advice from existing advisor
        from .advisor import advise_on_tool
        advice_items = advise_on_tool(
            tool_name,
            tool_input or {},
            context=state.user_intent,
            trace_id=trace_id,
        )

        if not advice_items:
            save_state(state)
            return None

        # 3. Run through the gate
        from .advisory_gate import evaluate
        gate_result = evaluate(advice_items, state, tool_name, tool_input)

        if not gate_result.emitted:
            save_state(state)
            _log_engine_event("no_emit", tool_name, len(advice_items), 0, start_ms)
            return None

        # 4. Annotate advice items with authority for synthesizer
        advice_by_id = {getattr(a, "advice_id", ""): a for a in advice_items}
        emitted_advice = []
        for d in gate_result.emitted:
            item = advice_by_id.get(d.advice_id)
            if item:
                # Attach gate authority to item for synthesizer
                item._authority = d.authority
                emitted_advice.append(item)

        # 5. Synthesize
        from .advisory_synthesizer import synthesize
        synth_text = ""

        # Check time budget before attempting synthesis
        elapsed_ms = (time.time() * 1000) - start_ms
        remaining_ms = MAX_ENGINE_MS - elapsed_ms

        if remaining_ms > 500:  # Need at least 500ms for synthesis
            synth_text = synthesize(
                emitted_advice,
                phase=gate_result.phase,
                user_intent=state.user_intent,
                tool_name=tool_name,
            )

        # 6. Emit to stdout
        from .advisory_emitter import emit_advisory
        emitted = emit_advisory(gate_result, synth_text, advice_items)

        # 7. Update state: mark shown
        if emitted:
            shown_ids = [d.advice_id for d in gate_result.emitted]
            mark_advice_shown(state, shown_ids)

            # Suppress same tool for cooldown to prevent flooding
            suppress_tool_advice(state, tool_name, duration_s=30)

        # 8. Save state
        save_state(state)

        elapsed_ms = (time.time() * 1000) - start_ms
        _log_engine_event(
            "emitted" if emitted else "synth_empty",
            tool_name,
            len(advice_items),
            len(gate_result.emitted),
            start_ms,
        )

        return synth_text if emitted else None

    except Exception as e:
        log_debug("advisory_engine", f"on_pre_tool failed for {tool_name}", e)
        return None


def on_post_tool(
    session_id: str,
    tool_name: str,
    success: bool,
    tool_input: Optional[dict] = None,
    trace_id: Optional[str] = None,
    error: Optional[str] = None,
) -> None:
    """
    Called at PostToolUse/PostToolUseFailure: update state with outcome.

    This closes the implicit feedback loop:
    - If advice was emitted and tool succeeded → implicit positive signal
    - If advice was emitted and tool failed → implicit negative signal
    """
    if not ENGINE_ENABLED:
        return

    try:
        from .advisory_state import load_state, save_state, record_tool_call

        state = load_state(session_id)

        # Record outcome
        record_tool_call(state, tool_name, tool_input, success=success, trace_id=trace_id)

        # Implicit feedback: check if we recently gave advice for this tool
        if state.shown_advice_ids:
            _record_implicit_feedback(state, tool_name, success, trace_id)

        save_state(state)

    except Exception as e:
        log_debug("advisory_engine", f"on_post_tool failed for {tool_name}", e)


def on_user_prompt(
    session_id: str,
    prompt_text: str,
) -> None:
    """
    Called at UserPromptSubmit: capture user intent.

    User intent is the MOST VALUABLE signal for retrieval relevance.
    It tells us what the developer is trying to accomplish, not just
    what tool they're using.
    """
    if not ENGINE_ENABLED:
        return

    try:
        from .advisory_state import load_state, save_state, record_user_intent
        state = load_state(session_id)
        record_user_intent(state, prompt_text)
        save_state(state)
    except Exception as e:
        log_debug("advisory_engine", "on_user_prompt failed", e)


# ============= Implicit Feedback =============

def _record_implicit_feedback(
    state,
    tool_name: str,
    success: bool,
    trace_id: Optional[str],
) -> None:
    """
    Record implicit feedback based on tool outcome.

    If advice was recently shown and the tool succeeded,
    that's a soft positive signal. Not as strong as explicit
    feedback or recovery detection, but still valuable over time.
    """
    try:
        from .advisor import get_advisor

        advisor = get_advisor()
        recent = advisor._get_recent_advice_entry(tool_name)

        if not recent or not recent.get("advice_ids"):
            return

        # Only count if advice was shown to Claude (via our engine)
        shown_ids = set(state.shown_advice_ids or [])
        matching_ids = [
            aid for aid in recent.get("advice_ids", [])
            if aid in shown_ids
        ]

        if not matching_ids:
            return

        # Implicit signal: advice was in Claude's context + outcome observed
        for aid in matching_ids[:3]:
            advisor.report_outcome(
                aid,
                was_followed=True,  # It was in context, assume considered
                was_helpful=success,  # Success = helpful, failure = not sufficient
                notes=f"implicit_feedback:{'success' if success else 'failure'}:{tool_name}",
                trace_id=trace_id,
            )

        log_debug(
            "advisory_engine",
            f"Implicit feedback: {len(matching_ids)} items, "
            f"{'positive' if success else 'negative'} for {tool_name}",
            None,
        )

    except Exception as e:
        log_debug("advisory_engine", "implicit feedback failed", e)


# ============= Diagnostics =============

def _log_engine_event(
    event: str,
    tool_name: str,
    advice_count: int,
    emitted_count: int,
    start_ms: float,
) -> None:
    """Log engine event for diagnostics."""
    try:
        elapsed_ms = (time.time() * 1000) - start_ms
        ENGINE_LOG.parent.mkdir(parents=True, exist_ok=True)
        entry = {
            "ts": time.time(),
            "event": event,
            "tool": tool_name,
            "retrieved": advice_count,
            "emitted": emitted_count,
            "elapsed_ms": round(elapsed_ms, 1),
        }
        with open(ENGINE_LOG, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry) + "\n")

        # Rotate
        _rotate_engine_log()
    except Exception:
        pass


def _rotate_engine_log() -> None:
    """Keep engine log bounded."""
    try:
        if not ENGINE_LOG.exists():
            return
        content = ENGINE_LOG.read_text(encoding="utf-8")
        lines = content.strip().split("\n")
        if len(lines) > ENGINE_LOG_MAX:
            keep = lines[-ENGINE_LOG_MAX:]
            ENGINE_LOG.write_text("\n".join(keep) + "\n", encoding="utf-8")
    except Exception:
        pass


def get_engine_status() -> Dict[str, Any]:
    """Get engine status for diagnostics and Pulse dashboard."""
    status = {
        "enabled": ENGINE_ENABLED,
        "max_ms": MAX_ENGINE_MS,
    }

    # Get synthesizer status
    try:
        from .advisory_synthesizer import get_synth_status
        status["synthesizer"] = get_synth_status()
    except Exception:
        status["synthesizer"] = {"error": "unavailable"}

    # Get emitter status
    try:
        from .advisory_emitter import get_emission_stats
        status["emitter"] = get_emission_stats()
    except Exception:
        status["emitter"] = {"error": "unavailable"}

    # Recent engine events
    try:
        if ENGINE_LOG.exists():
            lines = ENGINE_LOG.read_text(encoding="utf-8").strip().split("\n")
            recent = []
            for line in lines[-10:]:
                try:
                    recent.append(json.loads(line))
                except Exception:
                    pass
            status["recent_events"] = recent
            status["total_events"] = len(lines)

            # Compute emission rate
            emitted = sum(1 for l in lines[-100:] if '"emitted"' in l)
            total = min(len(lines), 100)
            status["emission_rate"] = round(emitted / max(total, 1), 3)
        else:
            status["recent_events"] = []
            status["total_events"] = 0
            status["emission_rate"] = 0.0
    except Exception:
        pass

    return status
