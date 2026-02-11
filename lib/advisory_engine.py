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
ENABLE_INLINE_PREFETCH_WORKER = os.getenv("SPARK_ADVISORY_PREFETCH_INLINE", "1") != "0"
try:
    INLINE_PREFETCH_MAX_JOBS = max(
        1, int(os.getenv("SPARK_ADVISORY_PREFETCH_INLINE_MAX_JOBS", "1") or 1)
    )
except Exception:
    INLINE_PREFETCH_MAX_JOBS = 1


def _parse_bool(value: Any, default: bool) -> bool:
    if isinstance(value, bool):
        return value
    text = str(value or "").strip().lower()
    if text in {"1", "true", "yes", "on"}:
        return True
    if text in {"0", "false", "no", "off"}:
        return False
    return bool(default)


def apply_engine_config(cfg: Dict[str, Any]) -> Dict[str, List[str]]:
    """Apply advisory engine runtime tuneables."""
    global ENGINE_ENABLED
    global MAX_ENGINE_MS
    global INCLUDE_MIND_IN_MEMORY
    global ENABLE_PREFETCH_QUEUE
    global ENABLE_INLINE_PREFETCH_WORKER
    global INLINE_PREFETCH_MAX_JOBS

    applied: List[str] = []
    warnings: List[str] = []
    if not isinstance(cfg, dict):
        return {"applied": applied, "warnings": warnings}

    if "enabled" in cfg:
        ENGINE_ENABLED = _parse_bool(cfg.get("enabled"), ENGINE_ENABLED)
        applied.append("enabled")

    if "max_ms" in cfg:
        try:
            MAX_ENGINE_MS = max(250.0, min(20000.0, float(cfg.get("max_ms"))))
            applied.append("max_ms")
        except Exception:
            warnings.append("invalid_max_ms")

    if "include_mind" in cfg:
        INCLUDE_MIND_IN_MEMORY = _parse_bool(cfg.get("include_mind"), INCLUDE_MIND_IN_MEMORY)
        applied.append("include_mind")

    if "prefetch_queue_enabled" in cfg:
        ENABLE_PREFETCH_QUEUE = _parse_bool(cfg.get("prefetch_queue_enabled"), ENABLE_PREFETCH_QUEUE)
        applied.append("prefetch_queue_enabled")

    if "prefetch_inline_enabled" in cfg:
        ENABLE_INLINE_PREFETCH_WORKER = _parse_bool(
            cfg.get("prefetch_inline_enabled"),
            ENABLE_INLINE_PREFETCH_WORKER,
        )
        applied.append("prefetch_inline_enabled")

    if "prefetch_inline_max_jobs" in cfg:
        try:
            INLINE_PREFETCH_MAX_JOBS = max(1, min(20, int(cfg.get("prefetch_inline_max_jobs") or 1)))
            applied.append("prefetch_inline_max_jobs")
        except Exception:
            warnings.append("invalid_prefetch_inline_max_jobs")

    return {"applied": applied, "warnings": warnings}


def get_engine_config() -> Dict[str, Any]:
    return {
        "enabled": bool(ENGINE_ENABLED),
        "max_ms": float(MAX_ENGINE_MS),
        "include_mind": bool(INCLUDE_MIND_IN_MEMORY),
        "prefetch_queue_enabled": bool(ENABLE_PREFETCH_QUEUE),
        "prefetch_inline_enabled": bool(ENABLE_INLINE_PREFETCH_WORKER),
        "prefetch_inline_max_jobs": int(INLINE_PREFETCH_MAX_JOBS),
    }


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
    stage_ms: Dict[str, float] = {}

    def _mark(stage: str, t0: float) -> None:
        try:
            stage_ms[stage] = round((time.time() * 1000.0) - t0, 1)
        except Exception:
            pass

    try:
        from .advisory_state import (
            load_state,
            mark_advice_shown,
            record_tool_call,
            save_state,
            suppress_tool_advice,
        )
        from .advisory_memory_fusion import build_memory_bundle
        from .advisory_packet_store import (
            build_packet,
            lookup_exact,
            lookup_relaxed,
            record_packet_usage,
            save_packet,
        )
        from .advisor import advise_on_tool
        from .advisory_gate import evaluate, get_tool_cooldown_s
        from .advisory_synthesizer import synthesize
        from .advisory_emitter import emit_advisory

        state = load_state(session_id)
        record_tool_call(state, tool_name, tool_input, success=None, trace_id=trace_id)
        intent_info = _intent_context(state, tool_name)
        project_key = _project_key()
        session_context_key = _session_context_key(state, tool_name)
        intent_family = state.intent_family or "emergent_other"
        task_plane = state.task_plane or "build_delivery"

        t_memory = time.time() * 1000.0
        memory_bundle = build_memory_bundle(
            session_id=session_id,
            intent_text=state.user_intent or "",
            intent_family=intent_family,
            tool_name=tool_name,
            include_mind=INCLUDE_MIND_IN_MEMORY,
        )
        _mark("memory_bundle", t_memory)

        t_lookup = time.time() * 1000.0
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

        _mark("packet_lookup", t_lookup)

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
                    "stage_ms": stage_ms,
                },
            )
            return None

        t_gate = time.time() * 1000.0
        gate_result = evaluate(advice_items, state, tool_name, tool_input)
        _mark("gate", t_gate)
        if not gate_result.emitted:
            if packet_id:
                try:
                    record_packet_usage(packet_id, emitted=False, route=route)
                except Exception as e:
                    log_debug("advisory_engine", "AE_PKT_USAGE_NO_EMIT", e)

            # --- NO-EMIT FALLBACK ---
            # If the packet path failed the gate, try a bounded deterministic
            # fallback using baseline text for this intent family, instead of
            # returning None (which wastes the entire advisory opportunity).
            fallback_text = ""
            if route and route.startswith("packet"):
                elapsed_fb = (time.time() * 1000.0) - start_ms
                if elapsed_fb < MAX_ENGINE_MS - 200:  # only if budget remains
                    fallback_text = _baseline_text(intent_family).strip()
                    if fallback_text:
                        route = f"{route}_fallback"

            if not fallback_text:
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
                        "stage_ms": stage_ms,
                    },
                )
                return None

            # Emit the fallback deterministic text
            try:
                from .advisory_emitter import emit_advisory
                emit_advisory(gate_result, fallback_text, advice_items, authority="note")
            except Exception as e:
                log_debug("advisory_engine", "AE_FALLBACK_EMIT_FAILED", e)
            save_state(state)
            _log_engine_event(
                "fallback_emit",
                tool_name,
                len(advice_items),
                1,
                start_ms,
                extra={"route": route, "intent_family": intent_family, "packet_id": packet_id, "stage_ms": stage_ms},
            )
            return fallback_text

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

        t_synth = time.time() * 1000.0
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
        _mark("synth", t_synth)

        t_emit = time.time() * 1000.0
        emitted = emit_advisory(gate_result, synth_text, advice_items)
        _mark("emit", t_emit)
        if emitted:
            shown_ids = [d.advice_id for d in gate_result.emitted]
            mark_advice_shown(state, shown_ids)
            suppress_tool_advice(state, tool_name, duration_s=get_tool_cooldown_s())

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

            try:
                from .advice_feedback import record_advice_request

                record_advice_request(
                    session_id=session_id,
                    tool=tool_name,
                    advice_ids=shown_ids,
                    advice_texts=[str(getattr(a, "text", "") or "") for a in emitted_advice],
                    sources=[str(getattr(a, "source", "") or "") for a in emitted_advice],
                    trace_id=trace_id,
                    route=route,
                    packet_id=packet_id,
                    min_interval_s=120,
                )
            except Exception as e:
                log_debug("advisory_engine", "AE_ADVICE_FEEDBACK_REQUEST_FAILED", e)

            state.last_advisory_packet_id = str(packet_id or "")
            state.last_advisory_route = str(route or "")
            state.last_advisory_tool = str(tool_name or "")
            state.last_advisory_advice_ids = list(shown_ids[:20])
            state.last_advisory_at = time.time()

        if packet_id:
            try:
                record_packet_usage(packet_id, emitted=bool(emitted), route=route)
            except Exception as e:
                log_debug("advisory_engine", "AE_PKT_USAGE_POST_EMIT_FAILED", e)

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
                "stage_ms": stage_ms,
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
        from .advisory_state import (
            load_state,
            record_tool_call,
            resolve_recent_trace_id,
            save_state,
        )

        state = load_state(session_id)
        resolved_trace_id = trace_id or resolve_recent_trace_id(state, tool_name)
        record_tool_call(
            state,
            tool_name,
            tool_input,
            success=success,
            trace_id=resolved_trace_id,
        )

        if state.shown_advice_ids:
            _record_implicit_feedback(state, tool_name, success, resolved_trace_id)

        try:
            from .advisory_packet_store import record_packet_feedback

            last_packet_id = str(state.last_advisory_packet_id or "").strip()
            last_tool = str(state.last_advisory_tool or "").strip().lower()
            age_s = time.time() - float(state.last_advisory_at or 0.0)
            if (
                last_packet_id
                and last_tool
                and last_tool == str(tool_name or "").strip().lower()
                and age_s <= 900
            ):
                record_packet_feedback(
                    last_packet_id,
                    helpful=bool(success),
                    noisy=False,
                    followed=False,  # Don't assume advice was followed; only explicit feedback should set this
                    source="implicit_post_tool",
                )
        except Exception as e:
            log_debug("advisory_engine", "AE_PKT_FEEDBACK_POST_TOOL_FAILED", e)

        if tool_name in {"Edit", "Write"}:
            try:
                from .advisory_packet_store import invalidate_packets

                # Scope invalidation to packets matching the edited file,
                # not a blanket project-wide wipe.  Falls back to project
                # invalidation only if no file_path is available.
                file_hint = (tool_input or {}).get("file_path", "")
                if file_hint:
                    invalidate_packets(
                        project_key=_project_key(),
                        reason=f"post_tool_{tool_name.lower()}",
                        file_hint=file_hint,
                    )
                else:
                    invalidate_packets(
                        project_key=_project_key(),
                        reason=f"post_tool_{tool_name.lower()}",
                    )
            except Exception as e:
                log_debug("advisory_engine", "AE_PACKET_INVALIDATE_POST_EDIT_FAILED", e)

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
                    "confidence": max(0.75, float(intent_info.get("confidence", 0.75) or 0.75)),
                    "source": "baseline",
                    "context_match": 0.8,
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
            if ENABLE_INLINE_PREFETCH_WORKER:
                try:
                    from .advisory_prefetch_worker import process_prefetch_queue

                    process_prefetch_queue(
                        max_jobs=INLINE_PREFETCH_MAX_JOBS,
                        max_tools_per_job=3,
                    )
                except Exception as e:
                    log_debug("advisory_engine", "inline prefetch worker failed", e)
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
        recent = advisor._get_recent_advice_entry(
            tool_name,
            trace_id=trace_id,
            allow_task_fallback=False,
        )
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
    status = {
        "enabled": ENGINE_ENABLED,
        "max_ms": MAX_ENGINE_MS,
        "config": get_engine_config(),
    }

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
        from .advisory_prefetch_worker import get_worker_status

        status["prefetch_worker"] = get_worker_status()
    except Exception:
        status["prefetch_worker"] = {"error": "unavailable"}

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
