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
}
REQUIRED_LINEAGE_FIELDS = {"sources", "memory_absent_declared"}


def _now() -> float:
    return time.time()


def _ensure_dirs() -> None:
    PACKET_DIR.mkdir(parents=True, exist_ok=True)


def _atomic_write_json(path: Path, payload: Dict[str, Any]) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    if path.exists():
        path.unlink()
    tmp.rename(path)


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
    data = _read_json(INDEX_FILE, default)
    data.setdefault("by_exact", {})
    data.setdefault("packet_meta", {})
    return data


def _save_index(index: Dict[str, Any]) -> None:
    _ensure_dirs()
    _atomic_write_json(INDEX_FILE, index)


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
    ttl_s: float = DEFAULT_PACKET_TTL_S,
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
        "fresh_until_ts": created + max(30.0, float(ttl_s or DEFAULT_PACKET_TTL_S)),
        "invalidated": False,
        "invalidate_reason": "",
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
            return data
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
        if tool_name and row.get("tool_name") == tool_name:
            score += 4.0
        if intent_family and row.get("intent_family") == intent_family:
            score += 3.0
        if task_plane and row.get("task_plane") == task_plane:
            score += 2.0
        if not tool_name and row.get("tool_name") == "*":
            score += 0.5
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
) -> int:
    index = _load_index()
    meta = index.get("packet_meta") or {}
    to_invalidate: List[str] = []
    for packet_id, row in meta.items():
        item = row or {}
        if project_key and item.get("project_key") != project_key:
            continue
        if tool_name and item.get("tool_name") != tool_name:
            continue
        if intent_family and item.get("intent_family") != intent_family:
            continue
        to_invalidate.append(packet_id)
    count = 0
    for packet_id in to_invalidate:
        if invalidate_packet(packet_id, reason=reason):
            count += 1
    return count


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
    return {
        "total_packets": total,
        "active_packets": active,
        "fresh_packets": fresh,
        "queue_depth": queue_depth,
        "index_file": str(INDEX_FILE),
    }

