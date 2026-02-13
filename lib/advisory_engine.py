"""
Advisory Engine: orchestrator for direct-path advisory and predictive packets.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from .diagnostics import log_debug
from .error_taxonomy import build_error_fields

ENGINE_ENABLED = os.getenv("SPARK_ADVISORY_ENGINE", "1") != "0"
ENGINE_LOG = Path.home() / ".spark" / "advisory_engine.jsonl"
ENGINE_LOG_MAX = 500
MAX_ENGINE_MS = float(os.getenv("SPARK_ADVISORY_MAX_MS", "4000"))
INCLUDE_MIND_IN_MEMORY = os.getenv("SPARK_ADVISORY_INCLUDE_MIND", "0") == "1"
ENABLE_PREFETCH_QUEUE = os.getenv("SPARK_ADVISORY_PREFETCH_QUEUE", "1") != "0"
ENABLE_INLINE_PREFETCH_WORKER = os.getenv("SPARK_ADVISORY_PREFETCH_INLINE", "1") != "0"
PACKET_FALLBACK_EMIT_ENABLED = os.getenv("SPARK_ADVISORY_PACKET_FALLBACK_EMIT", "0") == "1"
FALLBACK_RATE_GUARD_ENABLED = os.getenv("SPARK_ADVISORY_FALLBACK_RATE_GUARD", "1") != "0"
FALLBACK_RATE_GUARD_MAX_RATIO = float(
    os.getenv("SPARK_ADVISORY_FALLBACK_RATE_MAX_RATIO", "0.55")
)
try:
    FALLBACK_RATE_GUARD_WINDOW = max(
        10, int(os.getenv("SPARK_ADVISORY_FALLBACK_RATE_WINDOW", "80") or 80)
    )
except Exception:
    FALLBACK_RATE_GUARD_WINDOW = 80
MEMORY_SCOPE_DEFAULT = str(os.getenv("SPARK_MEMORY_SCOPE_DEFAULT", "session") or "session").strip() or "session"
ACTIONABILITY_ENFORCE = os.getenv("SPARK_ADVISORY_REQUIRE_ACTION", "1") != "0"
DELIVERY_STALE_SECONDS = float(os.getenv("SPARK_ADVISORY_STALE_S", "900"))
ADVISORY_TEXT_REPEAT_COOLDOWN_S = float(
    os.getenv("SPARK_ADVISORY_TEXT_REPEAT_COOLDOWN_S", "1800")
)
try:
    INLINE_PREFETCH_MAX_JOBS = max(
        1, int(os.getenv("SPARK_ADVISORY_PREFETCH_INLINE_MAX_JOBS", "1") or 1)
    )
except Exception:
    INLINE_PREFETCH_MAX_JOBS = 1


def _load_engine_config(path: Optional[Path] = None) -> Dict[str, Any]:
    """Load advisory engine tuneables from ~/.spark/tuneables.json."""
    tuneables = path or (Path.home() / ".spark" / "tuneables.json")
    if not tuneables.exists():
        return {}
    try:
        data = json.loads(tuneables.read_text(encoding="utf-8-sig"))
    except Exception:
        try:
            data = json.loads(tuneables.read_text(encoding="utf-8"))
        except Exception:
            return {}
    cfg = data.get("advisory_engine") or {}
    return cfg if isinstance(cfg, dict) else {}


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
    global PACKET_FALLBACK_EMIT_ENABLED
    global FALLBACK_RATE_GUARD_ENABLED
    global FALLBACK_RATE_GUARD_MAX_RATIO
    global FALLBACK_RATE_GUARD_WINDOW
    global INLINE_PREFETCH_MAX_JOBS
    global ACTIONABILITY_ENFORCE
    global DELIVERY_STALE_SECONDS
    global ADVISORY_TEXT_REPEAT_COOLDOWN_S

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

    if "packet_fallback_emit_enabled" in cfg:
        PACKET_FALLBACK_EMIT_ENABLED = _parse_bool(
            cfg.get("packet_fallback_emit_enabled"),
            PACKET_FALLBACK_EMIT_ENABLED,
        )
        applied.append("packet_fallback_emit_enabled")

    if "fallback_rate_guard_enabled" in cfg:
        FALLBACK_RATE_GUARD_ENABLED = _parse_bool(
            cfg.get("fallback_rate_guard_enabled"),
            FALLBACK_RATE_GUARD_ENABLED,
        )
        applied.append("fallback_rate_guard_enabled")

    if "fallback_rate_max_ratio" in cfg:
        try:
            FALLBACK_RATE_GUARD_MAX_RATIO = max(
                0.0,
                min(1.0, float(cfg.get("fallback_rate_max_ratio") or FALLBACK_RATE_GUARD_MAX_RATIO)),
            )
            applied.append("fallback_rate_max_ratio")
        except Exception:
            warnings.append("invalid_fallback_rate_max_ratio")

    if "fallback_rate_window" in cfg:
        try:
            FALLBACK_RATE_GUARD_WINDOW = max(
                10, min(500, int(cfg.get("fallback_rate_window") or FALLBACK_RATE_GUARD_WINDOW))
            )
            applied.append("fallback_rate_window")
        except Exception:
            warnings.append("invalid_fallback_rate_window")

    if "prefetch_inline_max_jobs" in cfg:
        try:
            INLINE_PREFETCH_MAX_JOBS = max(1, min(20, int(cfg.get("prefetch_inline_max_jobs") or 1)))
            applied.append("prefetch_inline_max_jobs")
        except Exception:
            warnings.append("invalid_prefetch_inline_max_jobs")

    if "actionability_enforce" in cfg:
        ACTIONABILITY_ENFORCE = _parse_bool(
            cfg.get("actionability_enforce"),
            ACTIONABILITY_ENFORCE,
        )
        applied.append("actionability_enforce")

    if "delivery_stale_s" in cfg:
        try:
            DELIVERY_STALE_SECONDS = max(
                30.0,
                min(86400.0, float(cfg.get("delivery_stale_s") or DELIVERY_STALE_SECONDS)),
            )
            applied.append("delivery_stale_s")
        except Exception:
            warnings.append("invalid_delivery_stale_s")

    if "advisory_text_repeat_cooldown_s" in cfg:
        try:
            ADVISORY_TEXT_REPEAT_COOLDOWN_S = max(
                0.0,
                min(86400.0, float(cfg.get("advisory_text_repeat_cooldown_s") or 0.0)),
            )
            applied.append("advisory_text_repeat_cooldown_s")
        except Exception:
            warnings.append("invalid_advisory_text_repeat_cooldown_s")

    return {"applied": applied, "warnings": warnings}


def get_engine_config() -> Dict[str, Any]:
    return {
        "enabled": bool(ENGINE_ENABLED),
        "max_ms": float(MAX_ENGINE_MS),
        "include_mind": bool(INCLUDE_MIND_IN_MEMORY),
        "prefetch_queue_enabled": bool(ENABLE_PREFETCH_QUEUE),
        "prefetch_inline_enabled": bool(ENABLE_INLINE_PREFETCH_WORKER),
        "packet_fallback_emit_enabled": bool(PACKET_FALLBACK_EMIT_ENABLED),
        "fallback_rate_guard_enabled": bool(FALLBACK_RATE_GUARD_ENABLED),
        "fallback_rate_max_ratio": float(FALLBACK_RATE_GUARD_MAX_RATIO),
        "fallback_rate_window": int(FALLBACK_RATE_GUARD_WINDOW),
        "prefetch_inline_max_jobs": int(INLINE_PREFETCH_MAX_JOBS),
        "actionability_enforce": bool(ACTIONABILITY_ENFORCE),
        "delivery_stale_s": float(DELIVERY_STALE_SECONDS),
        "advisory_text_repeat_cooldown_s": float(ADVISORY_TEXT_REPEAT_COOLDOWN_S),
    }


_BOOT_ENGINE_CFG = _load_engine_config()
if _BOOT_ENGINE_CFG:
    apply_engine_config(_BOOT_ENGINE_CFG)


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
    return _advice_to_rows_with_proof(advice_items, trace_id=None, max_rows=max_rows)


def _proof_refs_for_advice(item: Any, trace_id: Optional[str]) -> Dict[str, Any]:
    advice_id = str(getattr(item, "advice_id", "") or "")
    insight_key = str(getattr(item, "insight_key", "") or "")
    source = str(getattr(item, "source", "advisor") or "advisor")
    reason = str(getattr(item, "reason", "") or "").strip()
    refs: Dict[str, Any] = {
        "advice_id": advice_id,
        "insight_key": insight_key,
        "source": source,
    }
    if trace_id:
        refs["trace_id"] = str(trace_id)
    if reason:
        refs["reason"] = reason[:240]
    return refs


def _evidence_hash_for_row(*, advice_text: str, proof_refs: Dict[str, Any]) -> str:
    raw = {
        "text": str(advice_text or "").strip().lower(),
        "advice_id": str(proof_refs.get("advice_id") or ""),
        "insight_key": str(proof_refs.get("insight_key") or ""),
        "source": str(proof_refs.get("source") or ""),
        "trace_id": str(proof_refs.get("trace_id") or ""),
    }
    blob = json.dumps(raw, sort_keys=True, ensure_ascii=True)
    return hashlib.sha1(blob.encode("utf-8", errors="ignore")).hexdigest()[:20]


def _advice_to_rows_with_proof(
    advice_items: List[Any],
    *,
    trace_id: Optional[str],
    max_rows: int = 6,
) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for item in advice_items[:max_rows]:
        text = str(getattr(item, "text", "") or "")
        proof_refs = _proof_refs_for_advice(item, trace_id=trace_id)
        rows.append(
            {
                "advice_id": str(getattr(item, "advice_id", "") or f"aid_{len(rows)}"),
                "insight_key": str(getattr(item, "insight_key", "") or ""),
                "text": text,
                "confidence": float(getattr(item, "confidence", 0.5) or 0.5),
                "source": str(getattr(item, "source", "advisor") or "advisor"),
                "context_match": float(getattr(item, "context_match", 0.5) or 0.5),
                "reason": str(getattr(item, "reason", "") or ""),
                "proof_refs": proof_refs,
                "evidence_hash": _evidence_hash_for_row(advice_text=text, proof_refs=proof_refs),
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


def _text_fingerprint(text: str) -> str:
    cleaned = re.sub(r"\s+", " ", str(text or "").strip().lower())
    if not cleaned:
        return ""
    return hashlib.sha1(cleaned.encode("utf-8", errors="ignore")).hexdigest()[:16]


def _duplicate_repeat_state(state, advisory_text: str) -> Dict[str, Any]:
    now = time.time()
    fingerprint = _text_fingerprint(advisory_text)
    last_fingerprint = str(getattr(state, "last_advisory_text_fingerprint", "") or "")
    last_at = float(getattr(state, "last_advisory_at", 0.0) or 0.0)
    age_s = max(0.0, now - last_at) if last_at > 0 else None
    repeat = bool(
        fingerprint
        and ADVISORY_TEXT_REPEAT_COOLDOWN_S > 0
        and fingerprint == last_fingerprint
        and age_s is not None
        and age_s < ADVISORY_TEXT_REPEAT_COOLDOWN_S
    )
    return {
        "repeat": repeat,
        "fingerprint": fingerprint,
        "age_s": round(age_s, 2) if age_s is not None else None,
        "cooldown_s": float(ADVISORY_TEXT_REPEAT_COOLDOWN_S),
    }


def _provider_path_from_route(route: str) -> str:
    value = str(route or "").strip().lower()
    if value.startswith("packet"):
        return "packet_store"
    if value.startswith("live"):
        return "live_direct"
    if "fallback" in value:
        return "deterministic_fallback"
    if value == "post_tool":
        return "post_tool_feedback"
    if value == "user_prompt":
        return "prompt_prefetch"
    return "unknown"


def _diagnostics_envelope(
    *,
    session_id: str,
    trace_id: Optional[str],
    route: str,
    session_context_key: str = "",
    scope: Optional[str] = None,
    memory_bundle: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    bundle = memory_bundle if isinstance(memory_bundle, dict) else {}
    sources = bundle.get("sources") if isinstance(bundle.get("sources"), dict) else {}
    source_counts: Dict[str, int] = {}
    for name, meta in sources.items():
        if isinstance(meta, dict):
            source_counts[str(name)] = int(meta.get("count", 0) or 0)

    missing_sources = bundle.get("missing_sources")
    if not isinstance(missing_sources, list):
        missing_sources = [name for name, count in source_counts.items() if count <= 0]

    resolved_scope = str(scope or bundle.get("scope") or MEMORY_SCOPE_DEFAULT).strip() or "session"
    envelope: Dict[str, Any] = {
        "session_id": str(session_id or ""),
        "trace_id": str(trace_id or ""),
        "session_context_key": str(session_context_key or ""),
        "scope": resolved_scope,
        "provider_path": _provider_path_from_route(route),
        "source_counts": source_counts,
        "missing_sources": missing_sources,
    }
    if "memory_absent_declared" in bundle:
        envelope["memory_absent_declared"] = bool(bundle.get("memory_absent_declared"))
    return envelope


def _advice_source_counts(advice_items: Optional[List[Any]]) -> Dict[str, int]:
    counts: Dict[str, int] = {}
    for item in advice_items or []:
        try:
            source = str(getattr(item, "source", "") or "").strip().lower()
        except Exception:
            source = ""
        if not source:
            continue
        counts[source] = counts.get(source, 0) + 1
    return counts


def _default_action_command(tool_name: str, task_plane: str) -> str:
    tool = str(tool_name or "").strip().lower()
    plane = str(task_plane or "").strip().lower()
    if tool in {"edit", "write", "notebookedit"}:
        return "python -m pytest -q"
    if tool in {"read", "glob", "grep"}:
        return 'rg -n "TODO|FIXME" .'
    if tool == "bash":
        return "python scripts/status_local.py"
    if plane in {"build_delivery", "execution"}:
        return "python -m pytest -q"
    return "python scripts/status_local.py"


def _has_actionable_command(text: str) -> bool:
    body = str(text or "")
    if not body.strip():
        return False
    if re.search(r"`[^`]{3,}`", body):
        return True
    lowered = body.lower()
    if "next check:" in lowered or "next command:" in lowered:
        return True
    return False


def _ensure_actionability(text: str, tool_name: str, task_plane: str) -> Dict[str, Any]:
    original = str(text or "").strip()
    if not original:
        return {"text": "", "added": False, "command": ""}
    if not ACTIONABILITY_ENFORCE:
        return {"text": original, "added": False, "command": ""}
    if _has_actionable_command(original):
        return {"text": original, "added": False, "command": ""}

    command = _default_action_command(tool_name, task_plane)
    suffix = f" Next check: `{command}`."
    updated = f"{original}{suffix}"
    return {"text": updated, "added": True, "command": command}


def _derive_delivery_badge(
    events: List[Dict[str, Any]],
    *,
    now_ts: Optional[float] = None,
    stale_after_s: Optional[float] = None,
) -> Dict[str, Any]:
    now = float(now_ts if now_ts is not None else time.time())
    stale_s = float(stale_after_s if stale_after_s is not None else DELIVERY_STALE_SECONDS)
    relevant_events = {
        "emitted",
        "fallback_emit",
        "fallback_emit_failed",
        "no_emit",
        "no_advice",
        "duplicate_suppressed",
        "synth_empty",
        "engine_error",
        "post_tool_error",
        "user_prompt_error",
    }
    latest: Optional[Dict[str, Any]] = None
    for row in events:
        if not isinstance(row, dict):
            continue
        if str(row.get("event") or "") not in relevant_events:
            continue
        ts = float(row.get("ts") or 0.0)
        if latest is None or ts >= float(latest.get("ts") or 0.0):
            latest = row

    if latest is None:
        return {"state": "stale", "reason": "no_delivery_events", "age_s": None, "event": None}

    ts = float(latest.get("ts") or 0.0)
    age_s = max(0.0, now - ts) if ts > 0 else None
    if age_s is not None and age_s > stale_s:
        return {
            "state": "stale",
            "reason": "last_event_too_old",
            "age_s": round(age_s, 1),
            "event": latest.get("event"),
            "delivery_mode": latest.get("delivery_mode"),
        }

    event = str(latest.get("event") or "")
    mode = str(latest.get("delivery_mode") or "")
    if event == "emitted" and mode == "live":
        state = "live"
    elif event == "fallback_emit" or mode == "fallback":
        state = "fallback"
    else:
        state = "blocked"
    return {
        "state": state,
        "reason": event,
        "age_s": round(age_s, 1) if age_s is not None else None,
        "event": event,
        "delivery_mode": mode,
    }


def _fallback_guard_allows() -> Dict[str, Any]:
    if not FALLBACK_RATE_GUARD_ENABLED:
        return {
            "allowed": True,
            "reason": "guard_disabled",
            "ratio": None,
            "limit": float(FALLBACK_RATE_GUARD_MAX_RATIO),
            "delivered_recent": 0,
            "window": int(FALLBACK_RATE_GUARD_WINDOW),
        }
    if FALLBACK_RATE_GUARD_WINDOW <= 0:
        return {
            "allowed": True,
            "reason": "invalid_window",
            "ratio": None,
            "limit": float(FALLBACK_RATE_GUARD_MAX_RATIO),
            "delivered_recent": 0,
            "window": int(FALLBACK_RATE_GUARD_WINDOW),
        }

    fallback_count = 0
    emitted_count = 0
    try:
        if ENGINE_LOG.exists():
            lines = ENGINE_LOG.read_text(encoding="utf-8").splitlines()[-FALLBACK_RATE_GUARD_WINDOW:]
        else:
            lines = []
        for line in lines:
            raw = (line or "").strip()
            if not raw:
                continue
            try:
                row = json.loads(raw)
            except Exception:
                continue
            event = str(row.get("event") or "")
            if event == "fallback_emit":
                fallback_count += 1
            elif event == "emitted":
                emitted_count += 1
    except Exception:
        return {
            "allowed": True,
            "reason": "read_failed",
            "ratio": None,
            "limit": float(FALLBACK_RATE_GUARD_MAX_RATIO),
            "delivered_recent": 0,
            "window": int(FALLBACK_RATE_GUARD_WINDOW),
        }

    delivered = fallback_count + emitted_count
    min_sample = max(10, int(FALLBACK_RATE_GUARD_WINDOW * 0.25))
    if delivered < min_sample:
        return {
            "allowed": True,
            "reason": "insufficient_sample",
            "ratio": None,
            "limit": float(FALLBACK_RATE_GUARD_MAX_RATIO),
            "delivered_recent": int(delivered),
            "window": int(FALLBACK_RATE_GUARD_WINDOW),
        }

    ratio = float(fallback_count) / float(max(delivered, 1))
    allowed = ratio <= float(FALLBACK_RATE_GUARD_MAX_RATIO)
    return {
        "allowed": allowed,
        "reason": "ok" if allowed else "ratio_exceeded",
        "ratio": ratio,
        "limit": float(FALLBACK_RATE_GUARD_MAX_RATIO),
        "delivered_recent": int(delivered),
        "window": int(FALLBACK_RATE_GUARD_WINDOW),
    }


def on_pre_tool(
    session_id: str,
    tool_name: str,
    tool_input: Optional[dict] = None,
    trace_id: Optional[str] = None,
) -> Optional[str]:
    if not ENGINE_ENABLED:
        return None

    start_ms = time.time() * 1000.0
    resolved_trace_id = trace_id
    route = "live"
    packet_id = None
    stage_ms: Dict[str, float] = {}
    session_context_key = ""
    memory_bundle: Dict[str, Any] = {}
    intent_family = "emergent_other"
    task_plane = "build_delivery"
    advice_source_counts: Dict[str, int] = {}
    emitted_advice_source_counts: Dict[str, int] = {}

    def _mark(stage: str, t0: float) -> None:
        try:
            stage_ms[stage] = round((time.time() * 1000.0) - t0, 1)
        except Exception:
            pass

    def _diag(current_route: str) -> Dict[str, Any]:
        return _diagnostics_envelope(
            session_id=session_id,
            trace_id=resolved_trace_id,
            route=current_route,
            session_context_key=session_context_key,
            scope="session",
            memory_bundle=memory_bundle,
        )

    try:
        from .advisory_state import (
            load_state,
            mark_advice_shown,
            record_tool_call,
            resolve_recent_trace_id,
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
        resolved_trace_id = trace_id or resolve_recent_trace_id(state, tool_name)
        if not resolved_trace_id:
            try:
                from .exposure_tracker import infer_latest_trace_id

                resolved_trace_id = infer_latest_trace_id(session_id)
            except Exception:
                resolved_trace_id = None

        record_tool_call(state, tool_name, tool_input, success=None, trace_id=resolved_trace_id)
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
                include_mind=INCLUDE_MIND_IN_MEMORY,
                trace_id=resolved_trace_id,
            )
            route = "live"
        advice_source_counts = _advice_source_counts(advice_items)

        if not advice_items:
            save_state(state)
            _log_engine_event(
                "no_advice",
                tool_name,
                0,
                0,
                start_ms,
                extra={
                    **_diag(route),
                    "route": route,
                    "intent_family": intent_family,
                    "task_plane": task_plane,
                    "stage_ms": stage_ms,
                    "delivery_mode": "none",
                    "advice_source_counts": advice_source_counts,
                    "error_kind": "no_hit",
                    "error_code": "AE_NO_ADVICE",
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
            if PACKET_FALLBACK_EMIT_ENABLED and route and route.startswith("packet"):
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
                        **_diag(route),
                        "route": route,
                        "intent_family": intent_family,
                        "task_plane": task_plane,
                        "packet_id": packet_id,
                        "stage_ms": stage_ms,
                        "delivery_mode": "none",
                        "advice_source_counts": advice_source_counts,
                        "fallback_candidate_blocked": bool(route and route.startswith("packet") and not PACKET_FALLBACK_EMIT_ENABLED),
                        "error_kind": "policy",
                        "error_code": "AE_GATE_SUPPRESSED",
                    },
                )
                return None

            # Emit the fallback deterministic text
            action_meta = _ensure_actionability(fallback_text, tool_name, task_plane)
            fallback_text = str(action_meta.get("text") or fallback_text)
            fallback_guard = _fallback_guard_allows()
            if not fallback_guard.get("allowed"):
                save_state(state)
                _log_engine_event(
                    "no_emit",
                    tool_name,
                    len(advice_items),
                    0,
                    start_ms,
                    extra={
                        **_diag(route),
                        "route": route,
                        "intent_family": intent_family,
                        "task_plane": task_plane,
                        "packet_id": packet_id,
                        "stage_ms": stage_ms,
                        "delivery_mode": "none",
                        "advice_source_counts": advice_source_counts,
                        "error_kind": "policy",
                        "error_code": "AE_FALLBACK_RATE_LIMIT",
                        "fallback_guard_blocked": True,
                        "fallback_rate_recent": fallback_guard.get("ratio"),
                        "fallback_rate_limit": fallback_guard.get("limit"),
                        "fallback_delivered_recent": fallback_guard.get("delivered_recent"),
                        "fallback_window": fallback_guard.get("window"),
                    },
                )
                return None
            repeat_meta = _duplicate_repeat_state(state, fallback_text)
            if repeat_meta["repeat"]:
                save_state(state)
                _log_engine_event(
                    "duplicate_suppressed",
                    tool_name,
                    len(advice_items),
                    0,
                    start_ms,
                    extra={
                        **_diag(route),
                        "route": route,
                        "intent_family": intent_family,
                        "task_plane": task_plane,
                        "packet_id": packet_id,
                        "stage_ms": stage_ms,
                        "delivery_mode": "none",
                        "advice_source_counts": advice_source_counts,
                        "error_kind": "policy",
                        "error_code": "AE_DUPLICATE_SUPPRESSED",
                        "advisory_fingerprint": repeat_meta["fingerprint"],
                        "repeat_age_s": repeat_meta["age_s"],
                        "repeat_cooldown_s": repeat_meta["cooldown_s"],
                        "actionability_added": bool(action_meta.get("added")),
                        "actionability_command": action_meta.get("command"),
                    },
                )
                return None

            fallback_emitted = False
            fallback_error: Optional[Dict[str, Any]] = None
            try:
                from .advisory_emitter import emit_advisory
                fallback_emitted = bool(
                    emit_advisory(gate_result, fallback_text, advice_items, authority="note")
                )
                if fallback_emitted:
                    state.last_advisory_text_fingerprint = repeat_meta["fingerprint"]
            except Exception as e:
                log_debug("advisory_engine", "AE_FALLBACK_EMIT_FAILED", e)
                fallback_error = build_error_fields(str(e), "AE_FALLBACK_EMIT_FAILED")
            save_state(state)
            _log_engine_event(
                "fallback_emit" if fallback_emitted else "fallback_emit_failed",
                tool_name,
                len(advice_items),
                1 if fallback_emitted else 0,
                start_ms,
                extra={
                    **_diag(route),
                    "route": route,
                    "intent_family": intent_family,
                    "packet_id": packet_id,
                    "stage_ms": stage_ms,
                    "delivery_mode": "fallback" if fallback_emitted else "none",
                    "emitted_text_preview": fallback_text[:220],
                    "advice_source_counts": advice_source_counts,
                    "actionability_added": bool(action_meta.get("added")),
                    "actionability_command": action_meta.get("command"),
                    **(fallback_error or {}),
                },
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
        emitted_advice_source_counts = _advice_source_counts(emitted_advice)

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

        action_meta = _ensure_actionability(synth_text, tool_name, task_plane)
        synth_text = str(action_meta.get("text") or synth_text)
        repeat_meta = _duplicate_repeat_state(state, synth_text)
        if repeat_meta["repeat"]:
            if packet_id:
                try:
                    record_packet_usage(packet_id, emitted=False, route=f"{route}_repeat_suppressed")
                except Exception as e:
                    log_debug("advisory_engine", "AE_PKT_USAGE_REPEAT_SUPPRESS_FAILED", e)
            save_state(state)
            _log_engine_event(
                "duplicate_suppressed",
                tool_name,
                len(advice_items),
                len(gate_result.emitted),
                start_ms,
                extra={
                    **_diag(route),
                    "route": route,
                    "intent_family": intent_family,
                    "task_plane": task_plane,
                    "packet_id": packet_id,
                    "stage_ms": stage_ms,
                    "delivery_mode": "none",
                    "advice_source_counts": advice_source_counts,
                    "error_kind": "policy",
                    "error_code": "AE_DUPLICATE_SUPPRESSED",
                    "advisory_fingerprint": repeat_meta["fingerprint"],
                    "repeat_age_s": repeat_meta["age_s"],
                    "repeat_cooldown_s": repeat_meta["cooldown_s"],
                    "actionability_added": bool(action_meta.get("added")),
                    "actionability_command": action_meta.get("command"),
                },
            )
            return None

        t_emit = time.time() * 1000.0
        emitted = emit_advisory(gate_result, synth_text, advice_items)
        _mark("emit", t_emit)
        effective_text = str(synth_text or "").strip()
        if emitted and not effective_text:
            fragments: List[str] = []
            for item in emitted_advice[:3]:
                text = str(getattr(item, "text", "") or "").strip()
                if text:
                    fragments.append(text)
            if fragments:
                effective_text = " ".join(fragments)
        effective_action_meta = _ensure_actionability(effective_text, tool_name, task_plane) if emitted else {"text": effective_text, "added": False, "command": ""}
        effective_text = str(effective_action_meta.get("text") or effective_text)
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
                    advice_items=_advice_to_rows_with_proof(
                        emitted_advice or advice_items,
                        trace_id=resolved_trace_id,
                    ),
                    lineage={
                        "sources": lineage_sources,
                        "memory_absent_declared": bool(memory_bundle.get("memory_absent_declared")),
                        "trace_id": resolved_trace_id,
                    },
                    trace_id=resolved_trace_id,
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
                    trace_id=resolved_trace_id,
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
            state.last_advisory_text_fingerprint = repeat_meta["fingerprint"]

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
                **_diag(route),
                "route": route,
                "intent_family": intent_family,
                "task_plane": task_plane,
                "packet_id": packet_id,
                "intent_confidence": float(intent_info.get("confidence", 0.0) or 0.0),
                "stage_ms": stage_ms,
                "delivery_mode": "live" if emitted else "none",
                "emitted_text_preview": effective_text[:220],
                "advice_source_counts": emitted_advice_source_counts or advice_source_counts,
                "actionability_added": bool(action_meta.get("added")),
                "actionability_command": action_meta.get("command"),
                "effective_actionability_added": bool(effective_action_meta.get("added")),
                "effective_actionability_command": effective_action_meta.get("command"),
            },
        )
        return effective_text if emitted else None

    except Exception as e:
        log_debug("advisory_engine", f"on_pre_tool failed for {tool_name}", e)
        _log_engine_event(
            "engine_error",
            tool_name,
            0,
            0,
            start_ms,
            extra={
                **_diag(route),
                **build_error_fields(str(e), "AE_ON_PRE_TOOL_FAILED"),
            },
        )
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
    start_ms = time.time() * 1000.0
    resolved_trace_id = trace_id

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

        # Outcome predictor (world-model-lite): record outcome for cheap risk scoring.
        try:
            from .outcome_predictor import record_outcome
            record_outcome(
                tool_name=tool_name,
                intent_family=state.intent_family or "emergent_other",
                phase=state.task_phase or "implementation",
                success=bool(success),
            )
        except Exception:
            pass

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
        _log_engine_event(
            "post_tool_error",
            tool_name,
            0,
            0,
            start_ms,
            extra={
                **_diagnostics_envelope(
                    session_id=session_id,
                    trace_id=resolved_trace_id,
                    route="post_tool",
                    scope="session",
                ),
                **build_error_fields(str(e), "AE_ON_POST_TOOL_FAILED"),
            },
        )


def on_user_prompt(
    session_id: str,
    prompt_text: str,
) -> None:
    if not ENGINE_ENABLED:
        return
    start_ms = time.time() * 1000.0

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

        baseline_text = _baseline_text(intent_family)
        baseline_action = _ensure_actionability(baseline_text, "*", task_plane)
        baseline_text = str(baseline_action.get("text") or baseline_text)
        baseline_proof = {
            "advice_id": f"baseline_{intent_family}",
            "insight_key": f"intent:{intent_family}",
            "source": "baseline",
        }
        baseline_packet = build_packet(
            project_key=project_key,
            session_context_key=session_context_key,
            tool_name="*",
            intent_family=intent_family,
            task_plane=task_plane,
            advisory_text=baseline_text,
            source_mode="baseline_deterministic",
            advice_items=[
                {
                    "advice_id": f"baseline_{intent_family}",
                    "insight_key": f"intent:{intent_family}",
                    "text": baseline_text,
                    "confidence": max(0.75, float(intent_info.get("confidence", 0.75) or 0.75)),
                    "source": "baseline",
                    "context_match": 0.8,
                    "reason": "session_baseline",
                    "proof_refs": baseline_proof,
                    "evidence_hash": _evidence_hash_for_row(
                        advice_text=baseline_text,
                        proof_refs=baseline_proof,
                    ),
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

        _log_engine_event(
            "user_prompt_prefetch",
            "*",
            1,
            0,
            start_ms,
            extra={
                **_diagnostics_envelope(
                    session_id=session_id,
                    trace_id=None,
                    route="user_prompt",
                    session_context_key=session_context_key,
                    scope="session",
                ),
                "intent_family": intent_family,
                "task_plane": task_plane,
                "packet_id": baseline_packet.get("packet_id"),
                "prefetch_queue_enabled": bool(ENABLE_PREFETCH_QUEUE),
            },
        )
    except Exception as e:
        log_debug("advisory_engine", "on_user_prompt failed", e)
        _log_engine_event(
            "user_prompt_error",
            "*",
            0,
            0,
            start_ms,
            extra={
                **_diagnostics_envelope(
                    session_id=session_id,
                    trace_id=None,
                    route="user_prompt",
                    scope="session",
                ),
                **build_error_fields(str(e), "AE_ON_USER_PROMPT_FAILED"),
            },
        )


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
            parsed_tail: List[Dict[str, Any]] = []
            for line in lines[-100:]:
                try:
                    row = json.loads(line)
                    if isinstance(row, dict):
                        parsed_tail.append(row)
                except Exception:
                    continue
            recent = parsed_tail[-10:]
            status["recent_events"] = recent
            status["total_events"] = len(lines)
            emitted = sum(1 for row in parsed_tail if row.get("event") == "emitted")
            total = len(parsed_tail)
            status["emission_rate"] = round(emitted / max(total, 1), 3)
            status["delivery_badge"] = _derive_delivery_badge(parsed_tail)
        else:
            status["recent_events"] = []
            status["total_events"] = 0
            status["emission_rate"] = 0.0
            status["delivery_badge"] = _derive_delivery_badge([])
    except Exception:
        status["delivery_badge"] = _derive_delivery_badge([])

    return status
