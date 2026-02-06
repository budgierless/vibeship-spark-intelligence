"""
Advisory Engine: orchestrator for direct-path advisory and predictive packets.
"""

from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from .diagnostics import log_debug

ENGINE_ENABLED = os.getenv("SPARK_ADVISORY_ENGINE", "1") != "0"
ENGINE_LOG = Path.home() / ".spark" / "advisory_engine.jsonl"
ENGINE_LOG_MAX = 500
MAX_ENGINE_MS = float(os.getenv("SPARK_ADVISORY_MAX_MS", "4000"))
INCLUDE_MIND_IN_MEMORY = os.getenv("SPARK_ADVISORY_INCLUDE_MIND", "0") == "1"
ENABLE_PREFETCH_QUEUE = os.getenv("SPARK_ADVISORY_PREFETCH_QUEUE", "1") != "0"


def _project_key() -> str:
    try:
        from .memory_banks import infer_project_key

        key = infer_project_key()
        if key:
            return str(key)
    except Exception:
        pass
    return "unknown_project"


def _intent_context(state, tool_name: str) -> Dict[str, Any]:
    from .advisory_intent_taxonomy import map_intent

    prompt = state.user_intent or ""
    intent = map_intent(prompt, tool_name=tool_name)
    state.intent_family = intent.get("intent_family", "emergent_other")
    state.intent_confidence = float(intent.get("confidence", 0.0) or 0.0)
    state.task_plane = intent.get("task_plane", "build_delivery")
    state.intent_reason = intent.get("reason", "fallback")
    return intent


def _session_context_key(state, tool_name: str) -> str:
    from .advisory_intent_taxonomy import build_session_context_key
    from .advisory_state import get_recent_tool_sequence

    return build_session_context_key(
        task_phase=state.task_phase,
        intent_family=state.intent_family,
        tool_name=tool_name,
        recent_tools=get_recent_tool_sequence(state, n=5),
    )


def _packet_to_advice(packet: Dict[str, Any]) -> List[Any]:
    from .advisor import Advice

    advice_rows = packet.get("advice_items") or []
    out: List[Any] = []
    for row in advice_rows[:8]:
        if not isinstance(row, dict):
            continue
        text = str(row.get("text") or "").strip()
        if not text:
            continue
        out.append(
            Advice(
                advice_id=str(row.get("advice_id") or f"{packet.get('packet_id', 'pkt')}_item_{len(out)}"),
                insight_key=str(row.get("insight_key") or packet.get("packet_id") or ""),
                text=text,
                confidence=float(row.get("confidence") or 0.6),
                source=str(row.get("source") or "packet"),
                context_match=float(row.get("context_match") or 0.8),
                reason=str(row.get("reason") or ""),
            )
        )
    if out:
        return out

    text = str(packet.get("advisory_text") or "").strip()
    if not text:
        return []
    return [
        Advice(
            advice_id=f"{packet.get('packet_id', 'pkt')}_fallback",
            insight_key=str(packet.get("packet_id") or "packet"),
            text=text,
            confidence=0.7,
            source="packet",
            context_match=0.8,
            reason="packet_cached_advisory",
        )
    ]


def _advice_to_rows(advice_items: List[Any], max_rows: int = 6) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for item in advice_items[:max_rows]:
        rows.append(
            {
                "advice_id": str(getattr(item, "advice_id", "") or f"aid_{len(rows)}"),
                "insight_key": str(getattr(item, "insight_key", "") or ""),
                "text": str(getattr(item, "text", "") or ""),
                "confidence": float(getattr(item, "confidence", 0.5) or 0.5),
                "source": str(getattr(item, "source", "advisor") or "advisor"),
                "context_match": float(getattr(item, "context_match", 0.5) or 0.5),
                "reason": str(getattr(item, "reason", "") or ""),
            }
        )
    return rows


def _baseline_text(intent_family: str) -> str:
    defaults = {
        "auth_security": "Validate auth inputs server-side and redact sensitive tokens from logs before changes.",
        "deployment_ops": "Prefer reversible deployment steps and verify rollback path before release actions.",
        "testing_validation": "Run focused tests after edits and confirm failures are reproducible before broad changes.",
        "schema_contracts": "Check schema or contract compatibility before editing interfaces or payload shapes.",
        "performance_latency": "Preserve response-time budget while editing and measure before and after hot-path changes.",
        "tool_reliability": "Review target files before edits and keep changes minimal when failure risk is high.",
        "knowledge_alignment": "Align edits with existing project patterns and docs before changing behavior.",
        "team_coordination": "Clarify ownership and next action before delegating or switching tracks.",
        "orchestration_execution": "Respect dependency order and unblock critical path items before low-priority work.",
        "stakeholder_alignment": "Prioritize changes that match agreed outcomes and surface tradeoffs early.",
        "research_decision_support": "Compare options against constraints and record decision rationale explicitly.",
        "emergent_other": "Use conservative, test-backed edits and verify assumptions before irreversible actions.",
    }
    return defaults.get(intent_family, defaults["emergent_other"])


def on_pre_tool(
    session_id: str,
    tool_name: str,
    tool_input: Optional[dict] = None,
    trace_id: Optional[str] = None,
) -> Optional[str]:
    if not ENGINE_ENABLED:
        return None

    start_ms = time.time() * 1000.0
    route = "live"
    packet_id = None

    try:
        from .advisory_state import (
            load_state,
            mark_advice_shown,
            record_tool_call,
            save_state,
            suppress_tool_advice,
        )
        from .advisory_memory_fusion import build_memory_bundle
        from .advisory_packet_store import build_packet, lookup_exact, lookup_relaxed, save_packet
        from .advisor import advise_on_tool
        from .advisory_gate import evaluate
        from .advisory_synthesizer import synthesize
        from .advisory_emitter import emit_advisory

        state = load_state(session_id)
        record_tool_call(state, tool_name, tool_input, success=None, trace_id=trace_id)
        intent_info = _intent_context(state, tool_name)
        project_key = _project_key()
        session_context_key = _session_context_key(state, tool_name)
        intent_family = state.intent_family or "emergent_other"
        task_plane = state.task_plane or "build_delivery"

        memory_bundle = build_memory_bundle(
            session_id=session_id,
            intent_text=state.user_intent or "",
            intent_family=intent_family,
            tool_name=tool_name,
            include_mind=INCLUDE_MIND_IN_MEMORY,
        )

        packet = lookup_exact(
            project_key=project_key,
            session_context_key=session_context_key,
            tool_name=tool_name,
            intent_family=intent_family,
        )
        if packet:
            route = "packet_exact"
        else:
            packet = lookup_relaxed(
                project_key=project_key,
                tool_name=tool_name,
                intent_family=intent_family,
                task_plane=task_plane,
            )
            if packet:
                route = "packet_relaxed"

        if packet:
            packet_id = str(packet.get("packet_id") or "")
            advice_items = _packet_to_advice(packet)
        else:
            advice_items = advise_on_tool(
                tool_name,
                tool_input or {},
                context=state.user_intent,
                trace_id=trace_id,
            )
            route = "live"

        if not advice_items:
            save_state(state)
            _log_engine_event(
                "no_advice",
                tool_name,
                0,
                0,
                start_ms,
                extra={
                    "route": route,
                    "intent_family": intent_family,
                    "task_plane": task_plane,
                    "memory_absent_declared": bool(memory_bundle.get("memory_absent_declared")),
                },
            )
            return None

        gate_result = evaluate(advice_items, state, tool_name, tool_input)
        if not gate_result.emitted:
            save_state(state)
            _log_engine_event(
                "no_emit",
                tool_name,
                len(advice_items),
                0,
                start_ms,
                extra={
                    "route": route,
                    "intent_family": intent_family,
                    "task_plane": task_plane,
                    "packet_id": packet_id,
                    "memory_absent_declared": bool(memory_bundle.get("memory_absent_declared")),
                },
            )
            return None

        advice_by_id = {str(getattr(item, "advice_id", "")): item for item in advice_items}
        emitted_advice = []
        for decision in gate_result.emitted:
            item = advice_by_id.get(decision.advice_id)
            if item is None:
                continue
            item._authority = decision.authority
            emitted_advice.append(item)

        elapsed_ms = (time.time() * 1000.0) - start_ms
        remaining_ms = MAX_ENGINE_MS - elapsed_ms

        synth_text = ""
        if packet and str(packet.get("advisory_text") or "").strip():
            synth_text = str(packet.get("advisory_text") or "").strip()
        elif remaining_ms > 500:
            synth_text = synthesize(
                emitted_advice,
                phase=gate_result.phase,
                user_intent=state.user_intent,
                tool_name=tool_name,
            )
        else:
            synth_text = synthesize(
                emitted_advice,
                phase=gate_result.phase,
                user_intent=state.user_intent,
                tool_name=tool_name,
                force_mode="programmatic",
            )

        emitted = emit_advisory(gate_result, synth_text, advice_items)
        if emitted:
            shown_ids = [d.advice_id for d in gate_result.emitted]
            mark_advice_shown(state, shown_ids)
            suppress_tool_advice(state, tool_name, duration_s=30)

            if route == "live":
                lineage_sources = []
                for source_name, meta in (memory_bundle.get("sources") or {}).items():
                    if int((meta or {}).get("count", 0)) > 0:
                        lineage_sources.append(source_name)
                packet_payload = build_packet(
                    project_key=project_key,
                    session_context_key=session_context_key,
                    tool_name=tool_name,
                    intent_family=intent_family,
                    task_plane=task_plane,
                    advisory_text=synth_text or _baseline_text(intent_family),
                    source_mode="live_ai" if synth_text else "live_deterministic",
                    advice_items=_advice_to_rows(emitted_advice or advice_items),
                    lineage={
                        "sources": lineage_sources,
                        "memory_absent_declared": bool(memory_bundle.get("memory_absent_declared")),
                        "trace_id": trace_id,
                    },
                    trace_id=trace_id,
                )
                packet_id = save_packet(packet_payload)

        save_state(state)

        _log_engine_event(
            "emitted" if emitted else "synth_empty",
            tool_name,
            len(advice_items),
            len(gate_result.emitted),
            start_ms,
            extra={
                "route": route,
                "intent_family": intent_family,
                "task_plane": task_plane,
                "packet_id": packet_id,
                "memory_absent_declared": bool(memory_bundle.get("memory_absent_declared")),
                "intent_confidence": float(intent_info.get("confidence", 0.0) or 0.0),
            },
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
    if not ENGINE_ENABLED:
        return

    try:
        from .advisory_state import load_state, record_tool_call, save_state

        state = load_state(session_id)
        record_tool_call(state, tool_name, tool_input, success=success, trace_id=trace_id)

        if state.shown_advice_ids:
            _record_implicit_feedback(state, tool_name, success, trace_id)

        if tool_name in {"Edit", "Write"}:
            try:
                from .advisory_packet_store import invalidate_packets

                invalidate_packets(project_key=_project_key(), reason=f"post_tool_{tool_name.lower()}")
            except Exception:
                pass

        save_state(state)
    except Exception as e:
        log_debug("advisory_engine", f"on_post_tool failed for {tool_name}", e)


def on_user_prompt(
    session_id: str,
    prompt_text: str,
) -> None:
    if not ENGINE_ENABLED:
        return

    try:
        from .advisory_state import load_state, record_user_intent, save_state
        from .advisory_packet_store import build_packet, enqueue_prefetch_job, save_packet

        state = load_state(session_id)
        record_user_intent(state, prompt_text)
        intent_info = _intent_context(state, tool_name="*")
        project_key = _project_key()
        session_context_key = _session_context_key(state, tool_name="*")
        intent_family = state.intent_family or "emergent_other"
        task_plane = state.task_plane or "build_delivery"
        save_state(state)

        baseline_packet = build_packet(
            project_key=project_key,
            session_context_key=session_context_key,
            tool_name="*",
            intent_family=intent_family,
            task_plane=task_plane,
            advisory_text=_baseline_text(intent_family),
            source_mode="baseline_deterministic",
            advice_items=[
                {
                    "advice_id": f"baseline_{intent_family}",
                    "insight_key": f"intent:{intent_family}",
                    "text": _baseline_text(intent_family),
                    "confidence": float(intent_info.get("confidence", 0.2) or 0.2),
                    "source": "baseline",
                    "context_match": 0.7,
                    "reason": "session_baseline",
                }
            ],
            lineage={"sources": ["baseline"], "memory_absent_declared": False},
        )
        save_packet(baseline_packet)

        if ENABLE_PREFETCH_QUEUE:
            enqueue_prefetch_job(
                {
                    "session_id": session_id,
                    "project_key": project_key,
                    "intent_family": intent_family,
                    "task_plane": task_plane,
                    "session_context_key": session_context_key,
                    "prompt_excerpt": (prompt_text or "")[:180],
                    "trace_id": None,
                }
            )
    except Exception as e:
        log_debug("advisory_engine", "on_user_prompt failed", e)


def _record_implicit_feedback(
    state,
    tool_name: str,
    success: bool,
    trace_id: Optional[str],
) -> None:
    try:
        from .advisor import get_advisor

        advisor = get_advisor()
        recent = advisor._get_recent_advice_entry(tool_name)
        if not recent or not recent.get("advice_ids"):
            return

        shown_ids = set(state.shown_advice_ids or [])
        matching_ids = [aid for aid in recent.get("advice_ids", []) if aid in shown_ids]
        if not matching_ids:
            return

        for aid in matching_ids[:3]:
            advisor.report_outcome(
                aid,
                was_followed=True,
                was_helpful=success,
                notes=f"implicit_feedback:{'success' if success else 'failure'}:{tool_name}",
                trace_id=trace_id,
            )

        log_debug(
            "advisory_engine",
            f"Implicit feedback: {len(matching_ids)} items, {'positive' if success else 'negative'} for {tool_name}",
            None,
        )
    except Exception as e:
        log_debug("advisory_engine", "implicit feedback failed", e)


def _log_engine_event(
    event: str,
    tool_name: str,
    advice_count: int,
    emitted_count: int,
    start_ms: float,
    extra: Optional[Dict[str, Any]] = None,
) -> None:
    try:
        elapsed_ms = (time.time() * 1000.0) - start_ms
        ENGINE_LOG.parent.mkdir(parents=True, exist_ok=True)
        entry = {
            "ts": time.time(),
            "event": event,
            "tool": tool_name,
            "retrieved": advice_count,
            "emitted": emitted_count,
            "elapsed_ms": round(elapsed_ms, 1),
        }
        if extra:
            entry.update(extra)
        with open(ENGINE_LOG, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry) + "\n")
        _rotate_engine_log()
    except Exception:
        pass


def _rotate_engine_log() -> None:
    try:
        if not ENGINE_LOG.exists():
            return
        lines = ENGINE_LOG.read_text(encoding="utf-8").splitlines()
        if len(lines) > ENGINE_LOG_MAX:
            keep = lines[-ENGINE_LOG_MAX:]
            ENGINE_LOG.write_text("\n".join(keep) + "\n", encoding="utf-8")
    except Exception:
        pass


def get_engine_status() -> Dict[str, Any]:
    status = {"enabled": ENGINE_ENABLED, "max_ms": MAX_ENGINE_MS}

    try:
        from .advisory_synthesizer import get_synth_status

        status["synthesizer"] = get_synth_status()
    except Exception:
        status["synthesizer"] = {"error": "unavailable"}

    try:
        from .advisory_emitter import get_emission_stats

        status["emitter"] = get_emission_stats()
    except Exception:
        status["emitter"] = {"error": "unavailable"}

    try:
        from .advisory_packet_store import get_store_status

        status["packet_store"] = get_store_status()
    except Exception:
        status["packet_store"] = {"error": "unavailable"}

    try:
        if ENGINE_LOG.exists():
            lines = ENGINE_LOG.read_text(encoding="utf-8").splitlines()
            recent = []
            for line in lines[-10:]:
                try:
                    recent.append(json.loads(line))
                except Exception:
                    continue
            status["recent_events"] = recent
            status["total_events"] = len(lines)
            emitted = sum(1 for row in lines[-100:] if '"event": "emitted"' in row)
            total = min(len(lines), 100)
            status["emission_rate"] = round(emitted / max(total, 1), 3)
        else:
            status["recent_events"] = []
            status["total_events"] = 0
            status["emission_rate"] = 0.0
    except Exception:
        pass

    return status
