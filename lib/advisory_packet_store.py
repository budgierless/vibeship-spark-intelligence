"""
Advisory packet store for predictive/direct-path reuse.

Phase 1 scope:
- Deterministic packet CRUD
- Exact and relaxed lookup
- Invalidation helpers
- Background prefetch queue append
"""

from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

PACKET_DIR = Path.home() / ".spark" / "advice_packets"
INDEX_FILE = PACKET_DIR / "index.json"
PREFETCH_QUEUE_FILE = PACKET_DIR / "prefetch_queue.jsonl"

DEFAULT_PACKET_TTL_S = 900.0
MAX_INDEX_PACKETS = 2000
RELAXED_MATCH_WEIGHT_TOOL = 4.0
RELAXED_MATCH_WEIGHT_INTENT = 3.0
RELAXED_MATCH_WEIGHT_PLANE = 2.0
RELAXED_WILDCARD_TOOL_BONUS = 0.5
RELAXED_EFFECTIVENESS_WEIGHT = 2.0
RELAXED_LOW_EFFECTIVENESS_THRESHOLD = 0.3
RELAXED_LOW_EFFECTIVENESS_PENALTY = 0.5
RELAXED_MIN_MATCH_DIMENSIONS = 1
RELAXED_MIN_MATCH_SCORE = 3.0

REQUIRED_PACKET_FIELDS = {
    "packet_id",
    "project_key",
    "session_context_key",
    "tool_name",
    "intent_family",
    "task_plane",
    "advisory_text",
    "source_mode",
    "created_ts",
    "updated_ts",
    "fresh_until_ts",
    "lineage",
    "usage_count",
    "emit_count",
    "helpful_count",
    "unhelpful_count",
    "noisy_count",
    "feedback_count",
    "effectiveness_score",
}
REQUIRED_LINEAGE_FIELDS = {"sources", "memory_absent_declared"}

_INDEX_CACHE: Optional[Dict[str, Any]] = None
_INDEX_CACHE_MTIME_NS: Optional[int] = None


def _to_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except Exception:
        return int(default)


def _to_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except Exception:
        return float(default)


def _compute_effectiveness_score(
    *,
    helpful_count: int,
    unhelpful_count: int,
    noisy_count: int,
) -> float:
    # Simple Bayesian estimate with neutral prior + noise penalty.
    prior_good = 1.0
    prior_bad = 1.0
    effective_good = max(0.0, float(helpful_count)) + prior_good
    effective_bad = max(0.0, float(unhelpful_count)) + prior_bad
    score = effective_good / max(1.0, effective_good + effective_bad)
    score -= min(0.35, max(0, int(noisy_count)) * 0.05)
    return max(0.05, min(0.99, float(score)))


def _normalize_packet(packet: Dict[str, Any]) -> Dict[str, Any]:
    out = dict(packet or {})
    out["usage_count"] = max(0, _to_int(out.get("usage_count", 0), 0))
    out["emit_count"] = max(0, _to_int(out.get("emit_count", 0), 0))
    out["helpful_count"] = max(0, _to_int(out.get("helpful_count", 0), 0))
    out["unhelpful_count"] = max(0, _to_int(out.get("unhelpful_count", 0), 0))
    out["noisy_count"] = max(0, _to_int(out.get("noisy_count", 0), 0))
    out["feedback_count"] = max(0, _to_int(out.get("feedback_count", 0), 0))
    out["effectiveness_score"] = _compute_effectiveness_score(
        helpful_count=out["helpful_count"],
        unhelpful_count=out["unhelpful_count"],
        noisy_count=out["noisy_count"],
    )
    return out


def _now() -> float:
    return time.time()


def _ensure_dirs() -> None:
    PACKET_DIR.mkdir(parents=True, exist_ok=True)


def _atomic_write_json(path: Path, payload: Dict[str, Any]) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    # os.replace is atomic even on Windows (no unlink+rename race)
    import os
    os.replace(str(tmp), str(path))


def _read_json(path: Path, default: Dict[str, Any]) -> Dict[str, Any]:
    try:
        if path.exists():
            data = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                return data
    except Exception:
        pass
    return dict(default)


def _packet_path(packet_id: str) -> Path:
    return PACKET_DIR / f"{packet_id}.json"


def _make_exact_key(
    project_key: str,
    session_context_key: str,
    tool_name: str,
    intent_family: str,
) -> str:
    parts = [project_key or "", session_context_key or "", tool_name or "", intent_family or ""]
    return "|".join(parts)


def _sanitize_token(value: Any, default: str) -> str:
    text = str(value or "").strip()
    if not text:
        return default
    return text[:120]


def _make_packet_id(
    project_key: str,
    session_context_key: str,
    tool_name: str,
    intent_family: str,
    created_ts: float,
) -> str:
    raw = _make_exact_key(project_key, session_context_key, tool_name, intent_family)
    digest = hashlib.sha1(f"{raw}|{created_ts:.6f}".encode("utf-8", errors="replace")).hexdigest()[:12]
    return f"pkt_{digest}"


def _load_index() -> Dict[str, Any]:
    _ensure_dirs()
    default = {"by_exact": {}, "packet_meta": {}}
    global _INDEX_CACHE, _INDEX_CACHE_MTIME_NS

    try:
        mtime_ns = int(INDEX_FILE.stat().st_mtime_ns) if INDEX_FILE.exists() else None
    except Exception:
        mtime_ns = None

    # Hot-path optimization: lookups happen on pre-tool advisory. Avoid re-parsing
    # the index JSON unless the file changed.
    if _INDEX_CACHE is not None and mtime_ns is not None and _INDEX_CACHE_MTIME_NS == mtime_ns:
        return _INDEX_CACHE

    data = _read_json(INDEX_FILE, default)
    data.setdefault("by_exact", {})
    data.setdefault("packet_meta", {})
    _INDEX_CACHE = data
    _INDEX_CACHE_MTIME_NS = mtime_ns
    return data


def _save_index(index: Dict[str, Any]) -> None:
    _ensure_dirs()
    _atomic_write_json(INDEX_FILE, index)
    # Keep cache coherent for subsequent reads in this process.
    global _INDEX_CACHE, _INDEX_CACHE_MTIME_NS
    _INDEX_CACHE = index
    try:
        _INDEX_CACHE_MTIME_NS = int(INDEX_FILE.stat().st_mtime_ns) if INDEX_FILE.exists() else None
    except Exception:
        _INDEX_CACHE_MTIME_NS = None


def build_packet(
    *,
    project_key: str,
    session_context_key: str,
    tool_name: str,
    intent_family: str,
    task_plane: str,
    advisory_text: str,
    source_mode: str,
    advice_items: Optional[List[Dict[str, Any]]] = None,
    lineage: Optional[Dict[str, Any]] = None,
    trace_id: Optional[str] = None,
    ttl_s: Optional[float] = None,
) -> Dict[str, Any]:
    created = _now()
    project = _sanitize_token(project_key, "unknown_project")
    session_ctx = _sanitize_token(session_context_key, "default")
    tool = _sanitize_token(tool_name, "*")
    intent = _sanitize_token(intent_family, "emergent_other")
    plane = _sanitize_token(task_plane, "build_delivery")
    mode = _sanitize_token(source_mode, "deterministic")
    packet_id = _make_packet_id(project, session_ctx, tool, intent, created)
    safe_lineage = dict(lineage or {})
    safe_lineage.setdefault("sources", [])
    safe_lineage.setdefault("memory_absent_declared", False)
    if trace_id:
        safe_lineage.setdefault("trace_id", trace_id)

    ttl_value = DEFAULT_PACKET_TTL_S if ttl_s is None else float(ttl_s or DEFAULT_PACKET_TTL_S)
    return {
        "packet_id": packet_id,
        "project_key": project,
        "session_context_key": session_ctx,
        "tool_name": tool,
        "intent_family": intent,
        "task_plane": plane,
        "advisory_text": (advisory_text or "").strip(),
        "source_mode": mode,
        "advice_items": list(advice_items or []),
        "lineage": safe_lineage,
        "created_ts": created,
        "updated_ts": created,
        "fresh_until_ts": created + max(30.0, float(ttl_value)),
        "invalidated": False,
        "invalidate_reason": "",
        "usage_count": 0,
        "emit_count": 0,
        "helpful_count": 0,
        "unhelpful_count": 0,
        "noisy_count": 0,
        "feedback_count": 0,
        "effectiveness_score": 0.5,
    }


def validate_packet(packet: Dict[str, Any]) -> Tuple[bool, str]:
    if not isinstance(packet, dict):
        return False, "packet must be a dict"
    missing = REQUIRED_PACKET_FIELDS - set(packet.keys())
    if missing:
        return False, f"missing_fields:{','.join(sorted(missing))}"
    lineage = packet.get("lineage")
    if not isinstance(lineage, dict):
        return False, "lineage must be a dict"
    lineage_missing = REQUIRED_LINEAGE_FIELDS - set(lineage.keys())
    if lineage_missing:
        return False, f"missing_lineage_fields:{','.join(sorted(lineage_missing))}"
    if not packet.get("packet_id"):
        return False, "packet_id missing"
    if not isinstance(packet.get("advisory_text"), str):
        return False, "advisory_text must be string"
    return True, ""


def save_packet(packet: Dict[str, Any]) -> str:
    packet = _normalize_packet(packet)
    ok, reason = validate_packet(packet)
    if not ok:
        raise ValueError(f"invalid packet: {reason}")

    _ensure_dirs()
    packet_id = str(packet.get("packet_id"))
    packet["updated_ts"] = _now()

    _packet_path(packet_id).write_text(
        json.dumps(packet, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    index = _load_index()
    exact_key = _make_exact_key(
        str(packet.get("project_key", "")),
        str(packet.get("session_context_key", "")),
        str(packet.get("tool_name", "")),
        str(packet.get("intent_family", "")),
    )
    index["by_exact"][exact_key] = packet_id
    index["packet_meta"][packet_id] = {
        "project_key": packet.get("project_key"),
        "session_context_key": packet.get("session_context_key"),
        "tool_name": packet.get("tool_name"),
        "intent_family": packet.get("intent_family"),
        "task_plane": packet.get("task_plane"),
        "updated_ts": packet.get("updated_ts"),
        "fresh_until_ts": packet.get("fresh_until_ts"),
        "invalidated": bool(packet.get("invalidated", False)),
        "usage_count": int(packet.get("usage_count", 0) or 0),
        "emit_count": int(packet.get("emit_count", 0) or 0),
        "helpful_count": int(packet.get("helpful_count", 0) or 0),
        "unhelpful_count": int(packet.get("unhelpful_count", 0) or 0),
        "noisy_count": int(packet.get("noisy_count", 0) or 0),
        "feedback_count": int(packet.get("feedback_count", 0) or 0),
        "effectiveness_score": float(packet.get("effectiveness_score", 0.5) or 0.5),
    }
    _prune_index(index)
    _save_index(index)
    return packet_id


def _prune_index(index: Dict[str, Any]) -> None:
    meta = index.get("packet_meta") or {}
    if len(meta) <= MAX_INDEX_PACKETS:
        return
    ordered = sorted(
        meta.items(),
        key=lambda kv: float((kv[1] or {}).get("updated_ts", 0.0)),
    )
    remove_count = len(meta) - MAX_INDEX_PACKETS
    remove_ids = {packet_id for packet_id, _ in ordered[:remove_count]}
    for packet_id in remove_ids:
        meta.pop(packet_id, None)
    by_exact = index.get("by_exact") or {}
    dead_keys = [k for k, v in by_exact.items() if v in remove_ids]
    for k in dead_keys:
        by_exact.pop(k, None)


def get_packet(packet_id: str) -> Optional[Dict[str, Any]]:
    if not packet_id:
        return None
    try:
        path = _packet_path(packet_id)
        if not path.exists():
            return None
        data = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(data, dict):
            return _normalize_packet(data)
    except Exception:
        return None
    return None


def _is_fresh(packet: Dict[str, Any], now_ts: Optional[float] = None) -> bool:
    now_value = float(now_ts if now_ts is not None else _now())
    if bool(packet.get("invalidated")):
        return False
    return float(packet.get("fresh_until_ts", 0.0)) >= now_value


def lookup_exact(
    *,
    project_key: str,
    session_context_key: str,
    tool_name: str,
    intent_family: str,
    now_ts: Optional[float] = None,
) -> Optional[Dict[str, Any]]:
    index = _load_index()
    exact_key = _make_exact_key(project_key, session_context_key, tool_name, intent_family)
    packet_id = (index.get("by_exact") or {}).get(exact_key)
    packet = get_packet(str(packet_id or ""))
    if not packet:
        return None
    if not _is_fresh(packet, now_ts=now_ts):
        return None
    return packet


def lookup_relaxed(
    *,
    project_key: str,
    tool_name: str = "",
    intent_family: str = "",
    task_plane: str = "",
    now_ts: Optional[float] = None,
) -> Optional[Dict[str, Any]]:
    index = _load_index()
    meta = index.get("packet_meta") or {}
    now_value = float(now_ts if now_ts is not None else _now())
    candidates: List[Tuple[float, float, str]] = []

    for packet_id, item in meta.items():
        row = item or {}
        if row.get("project_key") != project_key:
            continue
        if bool(row.get("invalidated")):
            continue
        if float(row.get("fresh_until_ts", 0.0)) < now_value:
            continue
        score = 0.0
        match_score = 0.0
        match_dimensions = 0
        if tool_name and row.get("tool_name") == tool_name:
            score += RELAXED_MATCH_WEIGHT_TOOL
            match_score += RELAXED_MATCH_WEIGHT_TOOL
            match_dimensions += 1
        if intent_family and row.get("intent_family") == intent_family:
            score += RELAXED_MATCH_WEIGHT_INTENT
            match_score += RELAXED_MATCH_WEIGHT_INTENT
            match_dimensions += 1
        if task_plane and row.get("task_plane") == task_plane:
            score += RELAXED_MATCH_WEIGHT_PLANE
            match_score += RELAXED_MATCH_WEIGHT_PLANE
            match_dimensions += 1
        if not tool_name and row.get("tool_name") == "*":
            score += RELAXED_WILDCARD_TOOL_BONUS
            match_score += RELAXED_WILDCARD_TOOL_BONUS
            match_dimensions += 1
        if match_dimensions < RELAXED_MIN_MATCH_DIMENSIONS:
            continue
        if match_score < RELAXED_MIN_MATCH_SCORE:
            continue
        effectiveness = max(0.0, min(1.0, float(row.get("effectiveness_score", 0.5) or 0.5)))
        score += effectiveness * RELAXED_EFFECTIVENESS_WEIGHT
        if effectiveness < RELAXED_LOW_EFFECTIVENESS_THRESHOLD:
            score -= RELAXED_LOW_EFFECTIVENESS_PENALTY
        score += min(1.0, max(0.0, (float(row.get("updated_ts", 0.0)) / 1e10)))
        candidates.append((score, float(row.get("updated_ts", 0.0)), packet_id))

    if not candidates:
        return None

    candidates.sort(key=lambda x: (x[0], x[1]), reverse=True)
    for _, __, packet_id in candidates:
        packet = get_packet(packet_id)
        if packet and _is_fresh(packet, now_ts=now_value):
            return packet
    return None


def invalidate_packet(packet_id: str, reason: str = "manual") -> bool:
    packet = get_packet(packet_id)
    if not packet:
        return False
    packet["invalidated"] = True
    packet["invalidate_reason"] = reason[:200]
    packet["updated_ts"] = _now()
    _packet_path(packet_id).write_text(
        json.dumps(packet, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    index = _load_index()
    if packet_id in (index.get("packet_meta") or {}):
        index["packet_meta"][packet_id]["invalidated"] = True
        index["packet_meta"][packet_id]["updated_ts"] = packet["updated_ts"]
    _save_index(index)
    return True


def invalidate_packets(
    *,
    project_key: Optional[str] = None,
    tool_name: Optional[str] = None,
    intent_family: Optional[str] = None,
    reason: str = "filtered_invalidation",
    file_hint: Optional[str] = None,
) -> int:
    """Invalidate matching packets.

    When *file_hint* is provided (e.g. an edited file path), only
    packets whose advisory text or advice items reference that file
    are invalidated, rather than blanket project-wide invalidation.
    """
    index = _load_index()
    meta = index.get("packet_meta") or {}
    to_invalidate: List[str] = []

    # Normalise file_hint for substring matching
    file_hint_lower = ""
    if file_hint:
        file_hint_lower = file_hint.replace("\\", "/").rsplit("/", 1)[-1].lower()

    for packet_id, row in meta.items():
        item = row or {}
        if project_key and item.get("project_key") != project_key:
            continue
        if tool_name and item.get("tool_name") != tool_name:
            continue
        if intent_family and item.get("intent_family") != intent_family:
            continue

        # If file_hint given, only invalidate packets that reference
        # the same file (by filename match in advisory text or advice items).
        # NOTE: packet_meta intentionally does not store advisory_text/advice_items,
        # so we must read full packet for reliable matching.
        if file_hint_lower:
            pkt_tool = str(item.get("tool_name") or "").lower()
            packet = get_packet(packet_id)
            pkt_text = str((packet or {}).get("advisory_text") or "").lower()
            items_blob = (packet or {}).get("advice_items") or []
            items_text = json.dumps(items_blob, ensure_ascii=False).lower()

            if file_hint_lower not in pkt_text and file_hint_lower not in items_text:
                # Also skip wildcard baseline packets — those aren't file-specific.
                if pkt_tool == "*":
                    continue
                continue

        to_invalidate.append(packet_id)
    count = 0
    for packet_id in to_invalidate:
        if invalidate_packet(packet_id, reason=reason):
            count += 1
    return count


def record_packet_usage(
    packet_id: str,
    *,
    emitted: bool = False,
    route: Optional[str] = None,
) -> Dict[str, Any]:
    packet = get_packet(packet_id)
    if not packet:
        return {"ok": False, "reason": "packet_not_found", "packet_id": packet_id}

    packet["usage_count"] = int(packet.get("usage_count", 0) or 0) + 1
    if emitted:
        packet["emit_count"] = int(packet.get("emit_count", 0) or 0) + 1
    packet["last_route"] = str(route or packet.get("last_route") or "")
    packet["last_used_ts"] = _now()
    packet = _normalize_packet(packet)
    save_packet(packet)
    return {
        "ok": True,
        "packet_id": packet_id,
        "usage_count": int(packet.get("usage_count", 0) or 0),
        "emit_count": int(packet.get("emit_count", 0) or 0),
    }


def record_packet_feedback(
    packet_id: str,
    *,
    helpful: Optional[bool],
    noisy: bool = False,
    followed: bool = True,
    source: str = "explicit",
) -> Dict[str, Any]:
    packet = get_packet(packet_id)
    if not packet:
        return {"ok": False, "reason": "packet_not_found", "packet_id": packet_id}

    packet["feedback_count"] = int(packet.get("feedback_count", 0) or 0) + 1
    # Count effectiveness outcomes for both explicit and implicit feedback.
    # `followed` remains valuable metadata for analysis, but should not block
    # score updates when a post-tool outcome clearly indicates helpful/unhelpful.
    if helpful is True:
        packet["helpful_count"] = int(packet.get("helpful_count", 0) or 0) + 1
    elif helpful is False:
        packet["unhelpful_count"] = int(packet.get("unhelpful_count", 0) or 0) + 1
    if noisy:
        packet["noisy_count"] = int(packet.get("noisy_count", 0) or 0) + 1

    packet["last_feedback"] = {
        "helpful": helpful,
        "noisy": bool(noisy),
        "followed": bool(followed),
        "source": str(source or "")[:80],
        "ts": _now(),
    }
    packet = _normalize_packet(packet)
    save_packet(packet)
    return {
        "ok": True,
        "packet_id": packet_id,
        "effectiveness_score": float(packet.get("effectiveness_score", 0.5) or 0.5),
        "feedback_count": int(packet.get("feedback_count", 0) or 0),
    }


def record_packet_feedback_for_advice(
    advice_id: str,
    *,
    helpful: Optional[bool],
    noisy: bool = False,
    followed: bool = True,
    source: str = "explicit",
) -> Dict[str, Any]:
    advice = str(advice_id or "").strip()
    if not advice:
        return {"ok": False, "reason": "missing_advice_id"}

    index = _load_index()
    meta = index.get("packet_meta") or {}
    ordered_ids = sorted(
        meta.keys(),
        key=lambda pid: float((meta.get(pid) or {}).get("updated_ts", 0.0)),
        reverse=True,
    )
    for packet_id in ordered_ids:
        packet = get_packet(packet_id)
        if not packet:
            continue
        advice_rows = packet.get("advice_items") or []
        for row in advice_rows:
            if str((row or {}).get("advice_id") or "").strip() == advice:
                result = record_packet_feedback(
                    packet_id,
                    helpful=helpful,
                    noisy=noisy,
                    followed=followed,
                    source=source,
                )
                result["matched_advice_id"] = advice
                return result
    return {"ok": False, "reason": "packet_not_found_for_advice", "advice_id": advice}


def enqueue_prefetch_job(job: Dict[str, Any]) -> str:
    _ensure_dirs()
    ts = _now()
    payload = dict(job or {})
    if not payload.get("job_id"):
        digest = hashlib.sha1(f"{ts:.6f}|{json.dumps(payload, sort_keys=True)}".encode("utf-8")).hexdigest()[:10]
        payload["job_id"] = f"pf_{digest}"
    payload.setdefault("created_ts", ts)
    payload.setdefault("status", "queued")
    with PREFETCH_QUEUE_FILE.open("a", encoding="utf-8") as f:
        f.write(json.dumps(payload, ensure_ascii=False) + "\n")
    return str(payload["job_id"])


def apply_packet_store_config(cfg: Dict[str, Any]) -> Dict[str, List[str]]:
    """Apply packet store tuneables used by packet creation and relaxed ranking."""
    global DEFAULT_PACKET_TTL_S
    global MAX_INDEX_PACKETS
    global RELAXED_EFFECTIVENESS_WEIGHT
    global RELAXED_LOW_EFFECTIVENESS_THRESHOLD
    global RELAXED_LOW_EFFECTIVENESS_PENALTY
    global RELAXED_MIN_MATCH_DIMENSIONS
    global RELAXED_MIN_MATCH_SCORE

    applied: List[str] = []
    warnings: List[str] = []
    if not isinstance(cfg, dict):
        return {"applied": applied, "warnings": warnings}

    if "packet_ttl_s" in cfg:
        try:
            DEFAULT_PACKET_TTL_S = max(30.0, min(86400.0, float(cfg.get("packet_ttl_s") or 30.0)))
            applied.append("packet_ttl_s")
        except Exception:
            warnings.append("invalid_packet_ttl_s")

    if "max_index_packets" in cfg:
        try:
            MAX_INDEX_PACKETS = max(100, min(50000, int(cfg.get("max_index_packets") or 100)))
            applied.append("max_index_packets")
        except Exception:
            warnings.append("invalid_max_index_packets")

    if "relaxed_effectiveness_weight" in cfg:
        try:
            RELAXED_EFFECTIVENESS_WEIGHT = max(
                0.0,
                min(10.0, float(cfg.get("relaxed_effectiveness_weight") or 0.0)),
            )
            applied.append("relaxed_effectiveness_weight")
        except Exception:
            warnings.append("invalid_relaxed_effectiveness_weight")

    if "relaxed_low_effectiveness_threshold" in cfg:
        try:
            RELAXED_LOW_EFFECTIVENESS_THRESHOLD = max(
                0.0,
                min(1.0, float(cfg.get("relaxed_low_effectiveness_threshold") or 0.0)),
            )
            applied.append("relaxed_low_effectiveness_threshold")
        except Exception:
            warnings.append("invalid_relaxed_low_effectiveness_threshold")

    if "relaxed_low_effectiveness_penalty" in cfg:
        try:
            RELAXED_LOW_EFFECTIVENESS_PENALTY = max(
                0.0,
                min(5.0, float(cfg.get("relaxed_low_effectiveness_penalty") or 0.0)),
            )
            applied.append("relaxed_low_effectiveness_penalty")
        except Exception:
            warnings.append("invalid_relaxed_low_effectiveness_penalty")

    if "relaxed_min_match_dimensions" in cfg:
        try:
            RELAXED_MIN_MATCH_DIMENSIONS = max(
                0,
                min(3, int(cfg.get("relaxed_min_match_dimensions") or 0)),
            )
            applied.append("relaxed_min_match_dimensions")
        except Exception:
            warnings.append("invalid_relaxed_min_match_dimensions")

    if "relaxed_min_match_score" in cfg:
        try:
            RELAXED_MIN_MATCH_SCORE = max(
                0.0,
                min(10.0, float(cfg.get("relaxed_min_match_score") or 0.0)),
            )
            applied.append("relaxed_min_match_score")
        except Exception:
            warnings.append("invalid_relaxed_min_match_score")

    return {"applied": applied, "warnings": warnings}


def get_packet_store_config() -> Dict[str, Any]:
    return {
        "packet_ttl_s": float(DEFAULT_PACKET_TTL_S),
        "max_index_packets": int(MAX_INDEX_PACKETS),
        "relaxed_effectiveness_weight": float(RELAXED_EFFECTIVENESS_WEIGHT),
        "relaxed_low_effectiveness_threshold": float(RELAXED_LOW_EFFECTIVENESS_THRESHOLD),
        "relaxed_low_effectiveness_penalty": float(RELAXED_LOW_EFFECTIVENESS_PENALTY),
        "relaxed_min_match_dimensions": int(RELAXED_MIN_MATCH_DIMENSIONS),
        "relaxed_min_match_score": float(RELAXED_MIN_MATCH_SCORE),
    }


def get_store_status() -> Dict[str, Any]:
    index = _load_index()
    meta = index.get("packet_meta") or {}
    total = len(meta)
    active = sum(1 for row in meta.values() if not bool((row or {}).get("invalidated")))
    now_value = _now()
    fresh = sum(
        1
        for row in meta.values()
        if (not bool((row or {}).get("invalidated")))
        and float((row or {}).get("fresh_until_ts", 0.0)) >= now_value
    )
    queue_depth = 0
    try:
        if PREFETCH_QUEUE_FILE.exists():
            queue_depth = len([ln for ln in PREFETCH_QUEUE_FILE.read_text(encoding="utf-8").splitlines() if ln.strip()])
    except Exception:
        queue_depth = 0
    usage_total = sum(int((row or {}).get("usage_count", 0) or 0) for row in meta.values())
    emit_total = sum(int((row or {}).get("emit_count", 0) or 0) for row in meta.values())
    feedback_total = sum(int((row or {}).get("feedback_count", 0) or 0) for row in meta.values())
    avg_effectiveness = 0.0
    if meta:
        avg_effectiveness = sum(
            float((row or {}).get("effectiveness_score", 0.5) or 0.5)
            for row in meta.values()
        ) / max(1, len(meta))
    return {
        "total_packets": total,
        "active_packets": active,
        "fresh_packets": fresh,
        "queue_depth": queue_depth,
        "usage_total": usage_total,
        "emit_total": emit_total,
        "feedback_total": feedback_total,
        "hit_rate": (emit_total / max(usage_total, 1)) if usage_total > 0 else None,
        "avg_effectiveness_score": round(float(avg_effectiveness), 3),
        "config": get_packet_store_config(),
        "index_file": str(INDEX_FILE),
    }
