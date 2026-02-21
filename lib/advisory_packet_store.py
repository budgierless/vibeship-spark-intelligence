"""
Advisory packet store for predictive/direct-path reuse.

Phase 1 scope:
- Deterministic packet CRUD
- Exact and relaxed lookup
- Invalidation helpers
- Background prefetch queue append
"""

from __future__ import annotations

from collections import Counter
import hashlib
import json
import os
import re
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

try:
    import httpx as _HTTPX
except Exception:
    _HTTPX = None

PACKET_DIR = Path.home() / ".spark" / "advice_packets"
INDEX_FILE = PACKET_DIR / "index.json"
PREFETCH_QUEUE_FILE = PACKET_DIR / "prefetch_queue.jsonl"
OBSIDIAN_EXPORT_DIR = PACKET_DIR / "obsidian"
OBSIDIAN_PACKETS_DIR = OBSIDIAN_EXPORT_DIR / "packets"
OBSIDIAN_INDEX_FILE = OBSIDIAN_PACKETS_DIR / "index.md"

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
DEFAULT_PACKET_RELAXED_MAX_CANDIDATES = 6
DEFAULT_PACKET_RELAXED_PREVIEW_CHARS = 360
DEFAULT_PACKET_LOOKUP_CANDIDATES = 6
DEFAULT_PACKET_LOOKUP_LLM_ENABLED = False
DEFAULT_PACKET_LOOKUP_LLM_PROVIDER = "minimax"
DEFAULT_PACKET_LOOKUP_LLM_TIMEOUT_S = 1.2
DEFAULT_PACKET_LOOKUP_LLM_TOP_K = 3
DEFAULT_PACKET_LOOKUP_LLM_MIN_CANDIDATES = 2
DEFAULT_PACKET_LOOKUP_LLM_CONTEXT_CHARS = 220
DEFAULT_PACKET_LOOKUP_LLM_PROVIDER_URL = "https://api.minimax.io/v1"
DEFAULT_PACKET_LOOKUP_LLM_MODEL = "MiniMax-M2.5"
DEFAULT_OBSIDIAN_EXPORT_MAX_PACKETS = 300
DEFAULT_OBSIDIAN_EXPORT_ENABLED = False
DEFAULT_OBSIDIAN_AUTO_EXPORT = False
DEFAULT_OBSIDIAN_EXPORT_DIR = str(OBSIDIAN_EXPORT_DIR)
INDEX_SCHEMA_VERSION_KEY = "_schema_version"
INDEX_SCHEMA_VERSION = 2

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
    "deliver_count",
    "helpful_count",
    "unhelpful_count",
    "noisy_count",
    "feedback_count",
    "acted_count",
    "blocked_count",
    "harmful_count",
    "ignored_count",
    "read_count",
    "effectiveness_score",
}
REQUIRED_LINEAGE_FIELDS = {"sources", "memory_absent_declared"}

_INDEX_CACHE: Optional[Dict[str, Any]] = None
_INDEX_CACHE_MTIME_NS: Optional[int] = None
_ALIASED_EXACT_KEYS: set[str] = set()

_OBSIDIAN_CONFIG_DIR_OVERRIDE: Optional[str] = None
PACKET_RELAXED_MAX_CANDIDATES = int(DEFAULT_PACKET_RELAXED_MAX_CANDIDATES)
PACKET_LOOKUP_CANDIDATES = int(DEFAULT_PACKET_LOOKUP_CANDIDATES)
PACKET_LOOKUP_LLM_ENABLED = bool(DEFAULT_PACKET_LOOKUP_LLM_ENABLED)
PACKET_LOOKUP_LLM_PROVIDER = str(DEFAULT_PACKET_LOOKUP_LLM_PROVIDER).strip().lower() or "minimax"
PACKET_LOOKUP_LLM_TIMEOUT_S = float(DEFAULT_PACKET_LOOKUP_LLM_TIMEOUT_S)
PACKET_LOOKUP_LLM_TOP_K = int(DEFAULT_PACKET_LOOKUP_LLM_TOP_K)
PACKET_LOOKUP_LLM_MIN_CANDIDATES = int(DEFAULT_PACKET_LOOKUP_LLM_MIN_CANDIDATES)
PACKET_LOOKUP_LLM_CONTEXT_CHARS = int(DEFAULT_PACKET_LOOKUP_LLM_CONTEXT_CHARS)
PACKET_LOOKUP_LLM_URL = str(DEFAULT_PACKET_LOOKUP_LLM_PROVIDER_URL).strip() or "https://api.minimax.io/v1"
PACKET_LOOKUP_LLM_MODEL = str(DEFAULT_PACKET_LOOKUP_LLM_MODEL).strip() or "MiniMax-M2.5"
PACKET_LOOKUP_LLM_FALLBACK_TO_SCORING = True
OBSIDIAN_EXPORT_ENABLED = bool(DEFAULT_OBSIDIAN_EXPORT_ENABLED)
OBSIDIAN_AUTO_EXPORT = bool(DEFAULT_OBSIDIAN_AUTO_EXPORT)
OBSIDIAN_EXPORT_MAX_PACKETS = int(DEFAULT_OBSIDIAN_EXPORT_MAX_PACKETS)


def _obsidian_export_dir() -> Path:
    base = str(_OBSIDIAN_CONFIG_DIR_OVERRIDE or DEFAULT_OBSIDIAN_EXPORT_DIR).strip()
    if base:
        return Path(base).expanduser()
    return OBSIDIAN_EXPORT_DIR


def _obsidian_packets_dir() -> Path:
    return _obsidian_export_dir() / "packets"


def _obsidian_enabled() -> bool:
    return bool(OBSIDIAN_EXPORT_ENABLED)


def _load_packet_store_config(path: Optional[Path] = None) -> Dict[str, Any]:
    """Load advisory packet store tuneables."""
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
    section = data.get("advisory_packet_store") if isinstance(data, dict) else {}
    return section if isinstance(section, dict) else {}


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


def _safe_list(value: Any, *, max_items: int = 20) -> List[str]:
    out: List[str] = []
    if isinstance(value, (list, tuple, set)):
        for item in value:
            text = str(item or "").strip()
            if not text:
                continue
            out.append(text)
            if len(out) >= max_items:
                break
    elif isinstance(value, str):
        text = value.strip()
        if text:
            out.append(text)
    return out


def _meta_count(row: Dict[str, Any], key: str, *, fallback_key: Optional[str] = None) -> int:
    if not isinstance(row, dict):
        return 0
    value = row.get(key)
    if key in row or fallback_key is None:
        return max(0, _to_int(value, 0))
    if fallback_key in row:
        return max(0, _to_int(row.get(fallback_key), 0))
    return 0


def _sanitize_lookup_provider(raw: Any) -> str:
    provider = str(raw or "").strip().lower()
    if not provider:
        return PACKET_LOOKUP_LLM_PROVIDER
    if provider in {"minimax", "openai", "ollama", "anthropic", "gemini"}:
        return provider
    return PACKET_LOOKUP_LLM_PROVIDER


def _build_lookup_payload(
    packet_candidates: List[Dict[str, Any]],
    context_text: str,
    top_k: int,
) -> str:
    prompt_lines = [
        "You are a strict ranker for advisory packet retrieval.",
        "Return exactly one JSON array of packet_id strings in descending relevance order.",
        "Only include packet_ids from the provided candidate list.",
        f"Select at most {top_k} packet_ids.",
        "Prefer packets with higher expected usefulness for the immediate user intent.",
    ]
    context = str(context_text or "").strip().replace("\n", " ")
    if context:
        prompt_lines.append(f'Context: "{context}"')
    prompt_lines.append("Candidates (packet_id, score, tool_name, intent_family, task_plane, advisory_preview):")
    for row in packet_candidates[:top_k]:
        prompt_lines.append(json.dumps({
            "packet_id": str(row.get("packet_id") or ""),
            "score": float(row.get("score", 0.0) or 0.0),
            "tool_name": str(row.get("tool_name") or ""),
            "intent_family": str(row.get("intent_family") or ""),
            "task_plane": str(row.get("task_plane") or ""),
            "effectiveness_score": float(row.get("effectiveness_score", 0.0) or 0.0),
            "advisory_text_preview": str(row.get("advisory_text_preview") or ""),
        }, ensure_ascii=False, separators=(",", ":")))
    prompt_lines.append("Return only JSON. No markdown. Example: [\"pkt_abc\", \"pkt_def\"]")
    return "\n".join(prompt_lines)


def _extract_json_like_array(raw: str) -> List[str]:
    if not raw:
        return []
    text = str(raw).strip()
    try:
        parsed = json.loads(text)
    except Exception:
        # Try extracting first JSON-like list from markdown-wrapped output.
        match = re.search(r"\[[^\r\n]*\]", text, re.DOTALL)
        if not match:
            return []
        try:
            parsed = json.loads(match.group(0))
        except Exception:
            return []
    if isinstance(parsed, dict):
        parsed_list: Optional[List[Any]] = None
        for k in ("packet_ids", "reranked_ids", "result", "ids"):
            candidate = parsed.get(k)
            if isinstance(candidate, list):
                parsed_list = candidate
                break
        parsed = parsed_list if parsed_list is not None else []
    if not isinstance(parsed, list):
        return []
    out: List[str] = []
    for value in parsed:
        packet_id = str(value or "").strip()
        if packet_id:
            out.append(packet_id)
    return out


def _lookup_llm_api_key(provider: str) -> Optional[str]:
    p = str(provider or "").strip().lower()
    if p == "minimax":
        return (
            os.getenv("SPARK_MINIMAX_API_KEY")
            or os.getenv("MINIMAX_API_KEY")
            or os.getenv("SPARK_MINIMAX_TOKEN")
        )
    if p == "openai":
        return os.getenv("OPENAI_API_KEY") or os.getenv("SPARK_OPENAI_API_KEY")
    if p == "anthropic":
        return (
            os.getenv("ANTHROPIC_API_KEY")
            or os.getenv("SPARK_ANTHROPIC_API_KEY")
            or os.getenv("CLAUDE_API_KEY")
        )
    if p == "gemini":
        return os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    return None


def _lookup_llm_url(provider: str) -> str:
    p = str(provider or "").strip().lower()
    if p == "ollama":
        return str(os.getenv("SPARK_OLLAMA_API", "http://localhost:11434")).rstrip("/")
    if p == "minimax":
        return str(os.getenv("SPARK_MINIMAX_BASE_URL", PACKET_LOOKUP_LLM_URL)).rstrip("/")
    if p == "openai":
        return str(os.getenv("SPARK_OPENAI_BASE_URL", "https://api.openai.com")).rstrip("/")
    if p == "anthropic":
        return str(os.getenv("SPARK_ANTHROPIC_BASE_URL", "https://api.anthropic.com")).rstrip("/")
    if p == "gemini":
        return str(os.getenv("SPARK_GEMINI_BASE_URL", "https://generativelanguage.googleapis.com")).rstrip("/")
    return str(PACKET_LOOKUP_LLM_URL).rstrip("/")


def _call_lookup_llm(
    prompt: str,
    *,
    provider: str,
    timeout_s: float,
) -> Optional[str]:
    if _HTTPX is None:
        return None
    provider = str(provider or "").strip().lower()
    base_url = _lookup_llm_url(provider)
    if provider == "ollama":
        request_url = f"{base_url}/api/chat"
        payload = {
            "model": PACKET_LOOKUP_LLM_MODEL,
            "messages": [{"role": "user", "content": prompt}],
            "stream": False,
            "options": {"temperature": 0.0},
        }
        headers: Dict[str, str] = {"Content-Type": "application/json"}
    else:
        if provider == "minimax":
            request_url = f"{base_url}/chat/completions"
        else:
            request_url = f"{base_url}/v1/chat/completions"
        api_key = _lookup_llm_api_key(provider)
        if not api_key:
            return None
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": PACKET_LOOKUP_LLM_MODEL,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": 220,
            "temperature": 0.0,
            "response_format": {"type": "json_object"},
        }
    try:
        with _HTTPX.Client(timeout=timeout_s) as client:
            resp = client.post(request_url, headers=headers, json=payload)
        if not (200 <= int(resp.status_code) < 300):
            return None
        data = resp.json()
        if isinstance(data, dict):
            choices = data.get("choices") or []
            if choices:
                msg = choices[0].get("message") if isinstance(choices[0], dict) else {}
                content = msg.get("content", "") if isinstance(msg, dict) else ""
                if isinstance(content, str) and content.strip():
                    return content.strip()
            raw = data.get("response")
            if isinstance(raw, str) and raw.strip():
                return raw.strip()
    except Exception:
        return None
    return None


def _rerank_candidates_with_lookup_llm(
    candidates: List[Dict[str, Any]],
    *,
    context_text: str,
) -> List[Dict[str, Any]]:
    if not PACKET_LOOKUP_LLM_ENABLED or not candidates:
        return candidates
    provider = _sanitize_lookup_provider(PACKET_LOOKUP_LLM_PROVIDER)
    if provider not in {"minimax", "openai", "ollama", "anthropic", "gemini"}:
        return candidates
    min_candidates = max(1, int(PACKET_LOOKUP_LLM_MIN_CANDIDATES))
    if len(candidates) < min_candidates:
        return candidates

    top_k = max(1, min(len(candidates), int(PACKET_LOOKUP_LLM_TOP_K)))
    context = str(context_text or "").strip().replace("\n", " ")
    if context:
        context = context[: max(1, int(PACKET_LOOKUP_LLM_CONTEXT_CHARS))]
    prompt = _build_lookup_payload(candidates, context, top_k)
    response = _call_lookup_llm(prompt, provider=provider, timeout_s=PACKET_LOOKUP_LLM_TIMEOUT_S)
    if not response:
        return candidates
    ranked_ids = _extract_json_like_array(response)
    if not ranked_ids:
        return candidates

    ranked = list(ranked_ids)
    lookup = {str(row.get("packet_id") or ""): row for row in candidates}
    reranked: List[Dict[str, Any]] = []
    seen: set[str] = set()
    for packet_id in ranked:
        packet_id = str(packet_id or "").strip()
        if not packet_id or packet_id in seen:
            continue
        row = lookup.get(packet_id)
        if row is not None:
            row = dict(row)
            row["llm_rank"] = len(reranked)
            row["llm_reranked"] = True
            reranked.append(row)
            seen.add(packet_id)

    for row in candidates:
        packet_id = str(row.get("packet_id") or "")
        if packet_id in seen:
            continue
        row = dict(row)
        row["llm_rank"] = len(reranked)
        row["llm_reranked"] = False
        reranked.append(row)
    return reranked


def _coerce_bool(value: Any, default: bool = False) -> bool:
    if isinstance(value, bool):
        return value
    text = str(value or "").strip().lower()
    if text in {"1", "true", "yes", "on"}:
        return True
    if text in {"0", "false", "no", "off"}:
        return False
    return bool(default)


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
    out["read_count"] = max(0, _to_int(out.get("read_count", 0), 0))
    out["last_read_ts"] = float(_to_float(out.get("last_read_ts", 0.0), 0.0))
    out["last_read_route"] = str(out.get("last_read_route", "") or "")
    # Backwards compatibility with older packets where usage_count/deliver_count were
    # not tracked independently yet.
    out["usage_count"] = max(0, _to_int(out.get("usage_count", out.get("read_count", 0)), 0))
    out["emit_count"] = max(0, _to_int(out.get("emit_count", 0), 0))
    out["deliver_count"] = max(0, _to_int(out.get("deliver_count", out.get("emit_count", 0)), 0))
    out["helpful_count"] = max(0, _to_int(out.get("helpful_count", 0), 0))
    out["unhelpful_count"] = max(0, _to_int(out.get("unhelpful_count", 0), 0))
    out["noisy_count"] = max(0, _to_int(out.get("noisy_count", 0), 0))
    out["feedback_count"] = max(0, _to_int(out.get("feedback_count", 0), 0))
    out["acted_count"] = max(0, _to_int(out.get("acted_count", 0), 0))
    out["blocked_count"] = max(0, _to_int(out.get("blocked_count", 0), 0))
    out["harmful_count"] = max(0, _to_int(out.get("harmful_count", 0), 0))
    out["ignored_count"] = max(0, _to_int(out.get("ignored_count", 0), 0))
    out["effectiveness_score"] = _compute_effectiveness_score(
        helpful_count=out["helpful_count"],
        unhelpful_count=out["unhelpful_count"],
        noisy_count=out["noisy_count"],
    )
    out["category_summary"] = _safe_list(out.get("category_summary"), max_items=20)
    out["source_summary"] = _safe_list(out.get("source_summary"), max_items=40)
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


def _packet_lookup_context(row: Dict[str, Any]) -> Dict[str, Any]:
    if not isinstance(row, dict):
        return {}
    return {
        "packet_id": str(row.get("packet_id") or ""),
        "tool_name": str(row.get("tool_name") or ""),
        "intent_family": str(row.get("intent_family") or ""),
        "task_plane": str(row.get("task_plane") or ""),
        "project_key": str(row.get("project_key") or ""),
        "updated_ts": float(row.get("updated_ts") or 0.0),
        "fresh_until_ts": float(row.get("fresh_until_ts") or 0.0),
    }


def _obsidian_payload(packet: Dict[str, Any]) -> str:
    packet_id = str(packet.get("packet_id") or "")
    if not packet_id:
        return ""
    project = str(packet.get("project_key") or "unknown_project")
    session_ctx = str(packet.get("session_context_key") or "")
    tool = str(packet.get("tool_name") or "*")
    intent = str(packet.get("intent_family") or "emergent_other")
    plane = str(packet.get("task_plane") or "build_delivery")
    source_mode = str(packet.get("source_mode") or "")
    advisory_text = str(packet.get("advisory_text") or "").strip()
    created_ts = float(packet.get("created_ts") or 0.0)
    updated_ts = float(packet.get("updated_ts") or 0.0)
    fresh_until_ts = float(packet.get("fresh_until_ts") or 0.0)
    sources = _safe_list(packet.get("source_summary"), max_items=30)
    categories = _safe_list(packet.get("category_summary"), max_items=20)
    source_line = ", ".join(sources) if sources else "unset"
    category_line = ", ".join(categories) if categories else "unset"
    flags = _readiness_flags(packet, now_ts=_now())
    freshness_remaining = float(packet.get("fresh_until_ts", 0.0) or 0.0) - _now()
    if freshness_remaining < 0.0:
        freshness_remaining = 0.0
    last_read_ts = float(packet.get("last_read_ts", 0.0) or 0.0)
    last_read_at = (
        time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(last_read_ts))
        if last_read_ts > 0.0
        else "never"
    )

    lines = [
        f"# Packet {packet_id}",
        "",
        "## Packet Metadata",
        f"- Project: `{project}`",
        f"- Session key: `{session_ctx}`",
        f"- Tool context: `{tool}`",
        f"- Intent family: `{intent}`",
        f"- Task plane: `{plane}`",
        f"- Source mode: `{source_mode}`",
        f"- Created: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(created_ts)) if created_ts else 'unknown'}",
        f"- Updated: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(updated_ts)) if updated_ts else 'unknown'}",
        f"- Fresh until: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(fresh_until_ts)) if fresh_until_ts else 'unknown'}",
        f"- Sources: {source_line}",
        f"- Categories: {category_line}",
        f"- Invalidated: {bool(packet.get('invalidated', False))}",
        f"- Invalidation reason: `{str(packet.get('invalidate_reason', '') or 'none')}`",
        f"- Readiness: {float(flags.get('readiness_score', 0.0) or 0.0):.3f}",
        f"- Fresh now: {'yes' if bool(flags.get('is_fresh')) else 'no'}",
        f"- Ready for use: {bool(flags.get('ready_for_use'))}",
        f"- Freshness remaining (s): {int(freshness_remaining)}",
        f"- Last read at: {last_read_at}",
        f"- Last read route: `{str(packet.get('last_read_route', '') or 'none')}`",
        f"- Effectiveness: {float(packet.get('effectiveness_score', 0.5) or 0.5):.3f}",
        f"- Usage: {int(packet.get('usage_count', 0) or 0)}",
        f"- Deliveries: {int(packet.get('deliver_count', 0) or 0)}",
        f"- Emitted: {int(packet.get('emit_count', 0) or 0)}",
        f"- Feedback: {int(packet.get('feedback_count', 0) or 0)}",
        f"- Helpful: {int(packet.get('helpful_count', 0) or 0)}",
        f"- Unhelpful: {int(packet.get('unhelpful_count', 0) or 0)}",
        f"- Noisy: {int(packet.get('noisy_count', 0) or 0)}",
        "",
        "## Advisory Text",
    ]

    if advisory_text:
        lines.append(advisory_text)

    lines.extend(["", "## Advice Items", ""])
    for idx, row in enumerate(packet.get("advice_items") or [], start=1):
        if not isinstance(row, dict):
            continue
        text = str(row.get("text") or "").strip()
        if not text:
            continue
        src = str(row.get("source") or "unknown")
        conf = row.get("confidence")
        aid = str(row.get("advice_id") or f"item_{idx}")
        cat = str(row.get("category") or row.get("source") or "general")
        try:
            conf_display = f"{float(conf):.2f}"
        except Exception:
            conf_display = "n/a"
        lines.append(f"### {idx}. {aid}")
        lines.append(f"- source: {src}")
        lines.append(f"- category: {cat}")
        lines.append(f"- confidence: {conf_display}")
        lines.append(text)
        lines.append("")

    return "\n".join(lines).strip() + "\n"


def _packet_readiness_score(packet: Dict[str, Any], now_ts: Optional[float] = None) -> float:
    if not isinstance(packet, dict):
        return 0.0
    if bool(packet.get("invalidated")):
        return 0.0
    now_value = float(now_ts if now_ts is not None else _now())
    freshness_until = float(packet.get("fresh_until_ts", 0.0) or 0.0)
    if freshness_until <= now_value:
        return 0.0

    updated_ts = float(packet.get("updated_ts", 0.0) or 0.0)
    ttl = float(max(30.0, float(packet.get("ttl_s", 0.0) or (freshness_until - updated_ts) or DEFAULT_PACKET_TTL_S)))
    remaining = min(ttl, max(0.0, freshness_until - now_value))
    freshness_ratio = remaining / ttl if ttl > 0 else 0.0
    effectiveness = float(packet.get("effectiveness_score", 0.5) or 0.5)
    effectiveness = max(0.0, min(1.0, effectiveness))
    score = (0.35 * max(0.0, min(1.0, freshness_ratio))) + (0.65 * effectiveness)
    return max(0.0, min(1.0, score))


def _readiness_flags(packet: Dict[str, Any], now_ts: Optional[float] = None) -> Dict[str, Any]:
    now_value = float(now_ts if now_ts is not None else _now())
    freshness_until = float(packet.get("fresh_until_ts", 0.0) or 0.0)
    is_fresh = (not bool(packet.get("invalidated"))) and (freshness_until >= now_value)
    score = _packet_readiness_score(packet, now_value)
    return {
        "is_fresh": bool(is_fresh),
        "ready_for_use": bool(is_fresh and score >= 0.35),
        "readiness_score": float(score),
        "ready_age_s": max(0.0, now_value - float(packet.get("updated_ts", 0.0) or 0.0)),
    }


def _obsidian_catalog_entry(packet: Dict[str, Any], now_ts: Optional[float] = None) -> Dict[str, Any]:
    now_value = float(now_ts if now_ts is not None else _now())
    flags = _readiness_flags(packet, now_ts=now_value)
    fresh_remaining = float(packet.get("fresh_until_ts", 0.0) or 0.0) - now_value
    if fresh_remaining < 0.0:
        fresh_remaining = 0.0
    return {
        "packet_id": str(packet.get("packet_id") or ""),
        "project_key": str(packet.get("project_key") or ""),
        "session_context_key": str(packet.get("session_context_key") or ""),
        "tool_name": str(packet.get("tool_name") or ""),
        "intent_family": str(packet.get("intent_family") or ""),
        "task_plane": str(packet.get("task_plane") or ""),
        "updated_ts": float(packet.get("updated_ts", 0.0) or 0.0),
        "fresh_until_ts": float(packet.get("fresh_until_ts", 0.0) or 0.0),
        "ready_for_use": bool(flags.get("ready_for_use")),
        "is_fresh": bool(flags.get("is_fresh")),
        "invalidated": bool(packet.get("invalidated", False)),
        "invalidate_reason": str(packet.get("invalidate_reason", "") or ""),
        "freshness_remaining_s": float(fresh_remaining),
        "readiness_score": float(flags.get("readiness_score", 0.0)),
        "effectiveness_score": float(packet.get("effectiveness_score", 0.5) or 0.5),
        "read_count": int(packet.get("read_count", 0) or 0),
        "last_read_ts": float(packet.get("last_read_ts", 0.0) or 0.0),
        "last_read_route": str(packet.get("last_read_route", "") or ""),
        "usage_count": int(packet.get("usage_count", 0) or 0),
        "emit_count": int(packet.get("emit_count", 0) or 0),
        "deliver_count": int(packet.get("deliver_count", packet.get("emit_count", 0)) or 0),
        "source_summary": _safe_list(packet.get("source_summary"), max_items=10),
        "category_summary": _safe_list(packet.get("category_summary"), max_items=8),
    }


def _build_obsidian_catalog(
    *,
    now_ts: Optional[float] = None,
    only_ready: bool = False,
    include_stale: bool = False,
    include_invalid: bool = False,
    limit: int = 0,
) -> List[Dict[str, Any]]:
    index = _load_index()
    meta = index.get("packet_meta") or {}
    out: List[Dict[str, Any]] = []
    now_value = float(now_ts if now_ts is not None else _now())
    limit_count = max(0, int(limit or 0))
    for packet_id, row in meta.items():
        pid = str(packet_id or "").strip()
        if not pid:
            continue
        row_packet = get_packet(pid)
        if not row_packet:
            continue
        flags = _readiness_flags(row_packet, now_value)
        if not include_invalid and bool(row_packet.get("invalidated")):
            continue
        if not include_stale and not bool(flags.get("is_fresh", False)):
            continue
        if only_ready and not bool(flags.get("ready_for_use", False)):
            continue
        entry = _obsidian_catalog_entry(row_packet, now_ts=now_value)
        if not entry.get("packet_id"):
            continue
        out.append(entry)

    out.sort(key=lambda row: (float(row.get("readiness_score", 0.0) or 0.0), float(row.get("updated_ts", 0.0) or 0.0), str(row.get("packet_id") or "")), reverse=True)
    if limit_count > 0:
        return out[:limit_count]
    return out


def _render_obsidian_index(lines: List[str], catalog: List[Dict[str, Any]]) -> None:
    def _render_tags(values: List[str]) -> str:
        if not values:
            return ""
        return " ".join(f"`{v}`" for v in values[:8])

    category_counter: Counter[str] = Counter()
    source_counter: Counter[str] = Counter()
    for row in catalog:
        for category in _safe_list(row.get("category_summary"), max_items=20):
            if category:
                category_counter[str(category)] += 1
        for source in _safe_list(row.get("source_summary"), max_items=20):
            if source:
                source_counter[str(source)] += 1
    ready = [r for r in catalog if bool(r.get("ready_for_use"))]
    invalid = [r for r in catalog if bool(r.get("invalidated"))]
    stale = [r for r in catalog if not bool(r.get("is_fresh")) and not bool(r.get("invalidated"))]

    lines.append("# SPARK Advisory Packet Catalog")
    lines.append("")
    lines.append(f"- entries: {len(catalog)}")
    lines.append(f"- ready: {len(ready)}")
    lines.append(f"- stale: {len(stale)}")
    if invalid:
        lines.append(f"- invalidated: {len(invalid)}")
    lines.append(f"- updated: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(_now()))}")
    if source_counter:
        lines.append("- top sources: " + ", ".join(f"{k}({v})" for k, v in source_counter.most_common(8)))
    if category_counter:
        lines.append("- top categories: " + ", ".join(f"{k}({v})" for k, v in category_counter.most_common(8)))
    lines.append("")
    if invalid:
        lines.append("## Invalid Packets")
        for idx, row in enumerate(invalid[:80], start=1):
            packet_id = str(row.get("packet_id") or "")
            updated_ts = float(row.get("updated_ts", 0.0) or 0.0)
            updated_text = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(updated_ts)) if updated_ts else "unknown"
            lines.append(
                f"{idx}. [[{packet_id}]] "
                f"| {str(row.get('tool_name') or '*')} "
                f"| {str(row.get('intent_family') or 'emergent_other')} "
                f"| reason: {str(row.get('invalidate_reason') or 'none')} "
                f"| updated={updated_text}"
            )
        lines.append("")

    lines.append("## Ready Packets")
    for idx, row in enumerate(ready[:100], start=1):
        packet_id = str(row.get("packet_id") or "")
        updated_ts = float(row.get("updated_ts", 0.0) or 0.0)
        updated_text = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(updated_ts)) if updated_ts else "unknown"
        lines.append(
            f"{idx}. [[{packet_id}]] "
            f"| {str(row.get('tool_name') or '*')} "
            f"| {str(row.get('intent_family') or 'emergent_other')} "
            f"| readiness={float(row.get('readiness_score') or 0.0):.2f} "
            f"| eff={float(row.get('effectiveness_score') or 0.0):.2f} "
            f"| reads={int(row.get('read_count', 0) or 0)} "
            f"| usages={int(row.get('usage_count', 0) or 0)} "
            f"| deliveries={int(row.get('deliver_count', row.get('emit_count', 0)) or 0)} "
            f"| updated={updated_text}"
        )
        lines.append(f"   - sources: {_render_tags(_safe_list(row.get('source_summary'), max_items=10))}")
        lines.append(f"   - categories: {_render_tags(_safe_list(row.get('category_summary'), max_items=10))}")

    lines.append("")
    lines.append("## Full Packet Index")
    for idx, row in enumerate(catalog[:200], start=1):
        packet_id = str(row.get("packet_id") or "")
        updated_ts = float(row.get("updated_ts", 0.0) or 0.0)
        updated_text = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(updated_ts)) if updated_ts else "unknown"
        lines.append(
            f"{idx}. [[{packet_id}]] "
            f"| {str(row.get('project_key') or 'unknown_project')} "
            f"| {str(row.get('task_plane') or 'build_delivery')} "
            f"| freshness={'fresh' if bool(row.get('is_fresh')) else 'stale'} "
            f"| updated={updated_text}"
        )


def _sync_obsidian_catalog() -> Optional[str]:
    if not _obsidian_enabled():
        return None
    if not OBSIDIAN_AUTO_EXPORT:
        return None

    packets_dir = _obsidian_packets_dir()
    if not packets_dir.exists():
        return None

    catalog = _build_obsidian_catalog(
        now_ts=_now(),
        only_ready=False,
        include_stale=True,
        include_invalid=True,
        limit=max(1, OBSIDIAN_EXPORT_MAX_PACKETS),
    )
    if not catalog:
        return None

    lines: List[str] = []
    _render_obsidian_index(lines, catalog)
    target = _obsidian_packets_dir() / "index.md"
    target.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return str(target)


def _export_packet_to_obsidian(packet: Dict[str, Any], *, force: bool = False) -> Optional[str]:
    if not _obsidian_enabled() or not isinstance(packet, dict):
        return None
    packet_id = str(packet.get("packet_id") or "").strip()
    if not packet_id:
        return None
    if not OBSIDIAN_AUTO_EXPORT and not force:
        return None

    packets_dir = _obsidian_packets_dir()
    packets_dir.mkdir(parents=True, exist_ok=True)
    payload = _obsidian_payload(packet)
    if not payload:
        return None

    target = packets_dir / f"{packet_id}.md"
    target.write_text(payload, encoding="utf-8")

    try:
        all_exports = list(packets_dir.glob("*.md"))
        all_exports.sort(key=lambda p: p.stat().st_mtime)
        keep = max(1, OBSIDIAN_EXPORT_MAX_PACKETS)
        # Keep the catalog file if it exists.
        catalog_name = OBSIDIAN_INDEX_FILE.name.lower()
        if len(all_exports) > keep:
            for stale in all_exports[: len(all_exports) - keep]:
                if stale.name.lower() == catalog_name:
                    continue
                try:
                    stale.unlink()
                except Exception:
                    pass

        _sync_obsidian_catalog()
    except Exception:
        pass

    return str(target)


def export_packet_packet(packet_id: str) -> Optional[str]:
    """Export an advisory packet into Obsidian manually (outside auto flow)."""
    packet = get_packet(packet_id)
    if not packet:
        return None
    original_auto = OBSIDIAN_AUTO_EXPORT
    try:
        return _export_packet_to_obsidian(packet, force=True)
    except Exception:
        return None
    finally:
        # restore original auto export preference if any caller mutates at runtime
        if original_auto != OBSIDIAN_AUTO_EXPORT:
            pass


def _packet_path(packet_id: str) -> Path:
    return PACKET_DIR / f"{packet_id}.json"


def _obsidian_dir_override(raw: Any) -> None:
    global _OBSIDIAN_CONFIG_DIR_OVERRIDE
    if raw is None:
        _OBSIDIAN_CONFIG_DIR_OVERRIDE = None
        return
    value = str(raw).strip()
    if value:
        _OBSIDIAN_CONFIG_DIR_OVERRIDE = value
    else:
        _OBSIDIAN_CONFIG_DIR_OVERRIDE = None


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


def _derive_packet_metadata(
    advice_items: Optional[List[Dict[str, Any]]] = None,
) -> Tuple[List[str], List[str]]:
    """Derive compact source and category summaries from packet advice rows."""
    sources: List[str] = []
    categories: List[str] = []
    for row in (advice_items or []):
        if not isinstance(row, dict):
            continue
        source = str(row.get("source") or "").strip()
        category = str(row.get("category") or "").strip()
        if source:
            sources.append(source)
        if category:
            categories.append(category)

    # Deduplicate preserving order.
    def _uniq(values: List[str]) -> List[str]:
        seen = set()
        out: List[str] = []
        for value in values:
            normalized = value.strip()
            if not normalized or normalized in seen:
                continue
            seen.add(normalized)
            out.append(normalized)
        return out

    return _uniq(sources), _uniq(categories)


def _normalize_packet_meta_row(row: Any) -> Optional[Dict[str, Any]]:
    if not isinstance(row, dict):
        return None
    out = dict(row)
    out["read_count"] = max(0, _to_int(out.get("read_count", 0), 0))
    out["usage_count"] = max(0, _to_int(out.get("usage_count", out.get("read_count", 0)), 0))
    out["emit_count"] = max(0, _to_int(out.get("emit_count", 0), 0))
    out["deliver_count"] = max(0, _to_int(out.get("deliver_count", out.get("emit_count", 0)), 0))
    out["feedback_count"] = max(0, _to_int(out.get("feedback_count", 0), 0))
    out["helpful_count"] = max(0, _to_int(out.get("helpful_count", 0), 0))
    out["unhelpful_count"] = max(0, _to_int(out.get("unhelpful_count", 0), 0))
    out["noisy_count"] = max(0, _to_int(out.get("noisy_count", 0), 0))
    out["acted_count"] = max(0, _to_int(out.get("acted_count", 0), 0))
    out["blocked_count"] = max(0, _to_int(out.get("blocked_count", 0), 0))
    out["harmful_count"] = max(0, _to_int(out.get("harmful_count", 0), 0))
    out["ignored_count"] = max(0, _to_int(out.get("ignored_count", 0), 0))
    out["source_summary"] = _safe_list(out.get("source_summary"), max_items=40)
    out["category_summary"] = _safe_list(out.get("category_summary"), max_items=20)
    out["readiness_score"] = float(out.get("readiness_score") or 0.0)
    out["effectiveness_score"] = float(out.get("effectiveness_score", 0.5) or 0.5)
    out["fresh_until_ts"] = float(out.get("fresh_until_ts", 0.0) or 0.0)
    out["updated_ts"] = float(out.get("updated_ts", 0.0) or 0.0)
    out["last_read_ts"] = float(out.get("last_read_ts", 0.0) or 0.0)
    out["last_read_route"] = str(out.get("last_read_route", "") or "")
    out["invalidated"] = bool(out.get("invalidated", False))
    out["project_key"] = str(out.get("project_key") or "")
    out["session_context_key"] = str(out.get("session_context_key") or "")
    out["tool_name"] = str(out.get("tool_name") or "")
    out["intent_family"] = str(out.get("intent_family") or "")
    out["task_plane"] = str(out.get("task_plane") or "")
    out["source_mode"] = str(out.get("source_mode") or "")
    return out


def _normalize_packet_meta(index: Dict[str, Any]) -> bool:
    meta = index.get("packet_meta")
    if not isinstance(meta, dict):
        index["packet_meta"] = {}
        return True

    changed = False
    normalized_meta: Dict[str, Any] = {}
    for packet_id, row in meta.items():
        normalized = _normalize_packet_meta_row(row)
        if normalized is None:
            changed = True
            continue
        if not isinstance(row, dict) or row != normalized:
            changed = True
        normalized_meta[str(packet_id or "")] = normalized

    if not isinstance(index.get("packet_meta"), dict):
        changed = True
    index["packet_meta"] = normalized_meta
    return changed


def _migrate_packet_index_schema(index: Dict[str, Any]) -> bool:
    try:
        if not isinstance(index, dict):
            return False
        current = int(index.get(INDEX_SCHEMA_VERSION_KEY, 1))
    except Exception:
        current = 1
    if current >= INDEX_SCHEMA_VERSION:
        return False
    index[INDEX_SCHEMA_VERSION_KEY] = INDEX_SCHEMA_VERSION
    return True


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

    migrated = _migrate_packet_index_schema(data)
    meta_changed = _normalize_packet_meta(data)
    if migrated or meta_changed:
        try:
            _save_index(data)
            mtime_ns = int(INDEX_FILE.stat().st_mtime_ns) if INDEX_FILE.exists() else mtime_ns
        except Exception:
            pass

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


def alias_exact_key(
    *,
    project_key: str,
    session_context_key: str,
    tool_name: str,
    intent_family: str,
    packet_id: str,
) -> bool:
    """
    Promote a packet found via relaxed lookup into the exact index by creating an alias from the
    current exact key to the existing packet_id. This increases future exact-hit rate without
    duplicating packet files.
    """
    if not packet_id:
        return False
    project = _sanitize_token(project_key, "unknown_project")
    session_ctx = _sanitize_token(session_context_key, "default")
    tool = _sanitize_token(tool_name, "*")
    intent = _sanitize_token(intent_family, "emergent_other")
    exact_key = _make_exact_key(project, session_ctx, tool, intent)
    if exact_key in _ALIASED_EXACT_KEYS:
        return False
    index = _load_index()
    by_exact = index.get("by_exact") or {}
    if by_exact.get(exact_key) == packet_id:
        _ALIASED_EXACT_KEYS.add(exact_key)
        return False
    by_exact[exact_key] = packet_id
    index["by_exact"] = by_exact
    _save_index(index)
    _ALIASED_EXACT_KEYS.add(exact_key)
    return True


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
    rows = list(advice_items or [])
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
    source_summary, category_summary = _derive_packet_metadata(rows)
    return {
        "packet_id": packet_id,
        "project_key": project,
        "session_context_key": session_ctx,
        "tool_name": tool,
        "intent_family": intent,
        "task_plane": plane,
        "advisory_text": (advisory_text or "").strip(),
        "source_mode": mode,
        "advice_items": rows,
        "source_summary": source_summary,
        "category_summary": category_summary,
        "lineage": safe_lineage,
        "created_ts": created,
        "updated_ts": created,
        "fresh_until_ts": created + max(30.0, float(ttl_value)),
        "invalidated": False,
        "invalidate_reason": "",
        "read_count": 0,
        "last_read_ts": 0.0,
        "last_read_route": "",
        "usage_count": 0,
        "emit_count": 0,
        "deliver_count": 0,
        "helpful_count": 0,
        "unhelpful_count": 0,
        "noisy_count": 0,
        "feedback_count": 0,
        "acted_count": 0,
        "blocked_count": 0,
        "harmful_count": 0,
        "ignored_count": 0,
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
    flags = _readiness_flags(packet, now_ts=packet.get("updated_ts"))
    index["packet_meta"][packet_id] = {
        "project_key": packet.get("project_key"),
        "session_context_key": packet.get("session_context_key"),
        "tool_name": packet.get("tool_name"),
        "intent_family": packet.get("intent_family"),
        "task_plane": packet.get("task_plane"),
        "source_summary": _safe_list(packet.get("source_summary"), max_items=40),
        "category_summary": _safe_list(packet.get("category_summary"), max_items=20),
        "updated_ts": packet.get("updated_ts"),
        "fresh_until_ts": packet.get("fresh_until_ts"),
        "invalidated": bool(packet.get("invalidated", False)),
        "read_count": int(packet.get("read_count", 0) or 0),
        "last_read_ts": float(packet.get("last_read_ts", 0.0) or 0.0),
        "last_read_route": str(packet.get("last_read_route") or ""),
        "usage_count": int(packet.get("usage_count", 0) or 0),
        "emit_count": int(packet.get("emit_count", 0) or 0),
        "deliver_count": int(packet.get("deliver_count", 0) or 0),
        "feedback_count": int(packet.get("feedback_count", 0) or 0),
        "helpful_count": int(packet.get("helpful_count", 0) or 0),
        "unhelpful_count": int(packet.get("unhelpful_count", 0) or 0),
        "noisy_count": int(packet.get("noisy_count", 0) or 0),
        "effectiveness_score": float(packet.get("effectiveness_score", 0.5) or 0.5),
        "source_mode": str(packet.get("source_mode") or ""),
        "age_s": max(0.0, _now() - float(packet.get("updated_ts", 0.0) or 0.0)),
        "is_ready": bool(flags.get("ready_for_use", False)),
        "readiness_score": float(flags.get("readiness_score", 0.0)),
    }
    _prune_index(index)
    _save_index(index)
    try:
        _export_packet_to_obsidian(packet)
    except Exception:
        pass
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


def _candidate_match_score(
    row: Dict[str, Any],
    *,
    project: str,
    tool_name: str,
    intent_family: str,
    task_plane: str,
    now_value: float,
) -> Optional[Tuple[float, float]]:
    if row.get("project_key") != project:
        return None
    if bool(row.get("invalidated")):
        return None
    if float(row.get("fresh_until_ts", 0.0)) < now_value:
        return None

    score = 0.0
    match_score = 0.0
    match_dimensions = 0
    row_tool = str(row.get("tool_name") or "")
    row_intent = str(row.get("intent_family") or "")
    row_plane = str(row.get("task_plane") or "")

    if tool_name and row_tool == tool_name:
        score += RELAXED_MATCH_WEIGHT_TOOL
        match_score += RELAXED_MATCH_WEIGHT_TOOL
        match_dimensions += 1
    elif row_tool == "*":
        score += RELAXED_WILDCARD_TOOL_BONUS
        match_score += RELAXED_WILDCARD_TOOL_BONUS
        match_dimensions += 1
    if intent_family and row_intent == intent_family:
        score += RELAXED_MATCH_WEIGHT_INTENT
        match_score += RELAXED_MATCH_WEIGHT_INTENT
        match_dimensions += 1
    if task_plane and row_plane == task_plane:
        score += RELAXED_MATCH_WEIGHT_PLANE
        match_score += RELAXED_MATCH_WEIGHT_PLANE
        match_dimensions += 1

    if match_dimensions < RELAXED_MIN_MATCH_DIMENSIONS:
        return None
    if match_score < RELAXED_MIN_MATCH_SCORE:
        return None

    effectiveness = max(0.0, min(1.0, float(row.get("effectiveness_score", 0.5) or 0.5)))
    score += effectiveness * RELAXED_EFFECTIVENESS_WEIGHT
    if effectiveness < RELAXED_LOW_EFFECTIVENESS_THRESHOLD:
        score -= RELAXED_LOW_EFFECTIVENESS_PENALTY
    score += min(1.0, max(0.0, (float(row.get("updated_ts", 0.0)) / 1e10)))
    return score, float(row.get("updated_ts", 0.0))


def lookup_exact(
    *,
    project_key: str,
    session_context_key: str,
    tool_name: str,
    intent_family: str,
    now_ts: Optional[float] = None,
) -> Optional[Dict[str, Any]]:
    index = _load_index()
    # Mirror build_packet/save_packet sanitization so exact hits work even if caller passes raw values.
    project = _sanitize_token(project_key, "unknown_project")
    session_ctx = _sanitize_token(session_context_key, "default")
    tool = _sanitize_token(tool_name, "*")
    intent = _sanitize_token(intent_family, "emergent_other")
    exact_key = _make_exact_key(project, session_ctx, tool, intent)
    packet_id = (index.get("by_exact") or {}).get(exact_key)
    packet = get_packet(str(packet_id or ""))
    if not packet:
        return None
    if not _is_fresh(packet, now_ts=now_ts):
        return None
    return packet


def resolve_advisory_packet_for_context(
    *,
    project_key: str,
    session_context_key: str,
    tool_name: str = "",
    intent_family: str = "",
    task_plane: str = "",
    context_text: str = "",
    now_ts: Optional[float] = None,
    do_alias_relaxed_to_exact: bool = True,
) -> Tuple[Optional[Dict[str, Any]], str]:
    """
    Resolve an advisory packet with exact-first fallback semantics.

    Returns:
        (packet, route): packet may be None; route is one of
        "packet_exact", "packet_relaxed", or "packet_miss".
    """
    packet = lookup_exact(
        project_key=project_key,
        session_context_key=session_context_key,
        tool_name=tool_name,
        intent_family=intent_family,
        now_ts=now_ts,
    )
    if packet:
        return packet, "packet_exact"

    packet = lookup_relaxed(
        project_key=project_key,
        tool_name=tool_name,
        intent_family=intent_family,
        task_plane=task_plane,
        now_ts=now_ts,
        context_text=context_text,
    )
    if not packet:
        return None, "packet_miss"

    if do_alias_relaxed_to_exact:
        try:
            if (
                str(packet.get("project_key") or "").strip() == str(project_key or "").strip()
                and str(packet.get("tool_name") or "").strip() == str(tool_name or "").strip()
                and str(packet.get("intent_family") or "").strip() == str(intent_family or "").strip()
            ):
                alias_exact_key(
                    project_key=project_key,
                    session_context_key=session_context_key,
                    tool_name=tool_name,
                    intent_family=intent_family,
                    packet_id=str(packet.get("packet_id") or ""),
                )
        except Exception:
            pass

    return packet, "packet_relaxed"


def lookup_relaxed(
    *,
    project_key: str,
    tool_name: str = "",
    intent_family: str = "",
    task_plane: str = "",
    now_ts: Optional[float] = None,
    context_text: str = "",
) -> Optional[Dict[str, Any]]:
    candidates = lookup_relaxed_candidates(
        project_key=project_key,
        tool_name=tool_name,
        intent_family=intent_family,
        task_plane=task_plane,
        now_ts=now_ts,
        max_candidates=PACKET_LOOKUP_CANDIDATES,
        context_text=context_text,
    )
    if not candidates:
        return None
    packet_id = str(candidates[0].get("packet_id") or "")
    if not packet_id:
        return None
    return get_packet(packet_id)


def lookup_relaxed_candidates(
    *,
    project_key: str,
    tool_name: str = "",
    intent_family: str = "",
    task_plane: str = "",
    now_ts: Optional[float] = None,
    max_candidates: int = 10,
    context_text: str = "",
) -> List[Dict[str, Any]]:
    index = _load_index()
    meta = index.get("packet_meta") or {}
    now_value = float(now_ts if now_ts is not None else _now())
    limit = max(1, min(30, int(max_candidates or PACKET_RELAXED_MAX_CANDIDATES or 1)))
    candidates: List[Tuple[float, float, str, Dict[str, Any]]] = []
    project = _sanitize_token(project_key, "unknown_project")
    tool_name = _sanitize_token(tool_name, "") if tool_name else ""
    intent_family = _sanitize_token(intent_family, "") if intent_family else ""
    task_plane = _sanitize_token(task_plane, "") if task_plane else ""

    for packet_id, item in meta.items():
        row = item or {}
        scored = _candidate_match_score(
            row,
            project=project,
            tool_name=tool_name,
            intent_family=intent_family,
            task_plane=task_plane,
            now_value=now_value,
        )
        if not scored:
            continue
        score, updated_ts = scored
        candidates.append((score, updated_ts, str(packet_id or ""), row))

    if not candidates:
        return None
    candidates.sort(key=lambda x: (x[0], x[1]), reverse=True)
    out: List[Dict[str, Any]] = []
    for score, updated_ts, packet_id, row in candidates[:limit]:
        preview = ""
        try:
            packet = get_packet(packet_id)
            if packet:
                text = str(packet.get("advisory_text") or "")
                preview = text[:DEFAULT_PACKET_RELAXED_PREVIEW_CHARS].replace("\n", " ").strip()
        except Exception:
            preview = ""

        item = {
            "packet_id": str(packet_id),
            "score": float(score),
            "updated_ts": float(updated_ts),
            "tool_name": str(row.get("tool_name") or ""),
            "intent_family": str(row.get("intent_family") or ""),
            "task_plane": str(row.get("task_plane") or ""),
            "source_summary": _safe_list(row.get("source_summary"), max_items=20),
            "category_summary": _safe_list(row.get("category_summary"), max_items=20),
            "effectiveness_score": float(row.get("effectiveness_score", 0.5) or 0.5),
            "read_count": _meta_count(row, "read_count"),
            "usage_count": _meta_count(row, "usage_count", fallback_key="read_count"),
            "emit_count": _meta_count(row, "emit_count"),
            "deliver_count": _meta_count(row, "deliver_count", fallback_key="emit_count"),
            "fresh_until_ts": float(row.get("fresh_until_ts", 0.0) or 0.0),
            "advisory_text_preview": preview,
            "invalidated": bool(row.get("invalidated", False)),
        }
        out.append(item)

    if context_text and len(out) > 1:
        out = _rerank_candidates_with_lookup_llm(out, context_text=context_text)
    return out


def get_advisory_catalog(
    *,
    project_key: str = "",
    tool_name: str = "",
    intent_family: str = "",
    task_plane: str = "",
    only_ready: bool = True,
    include_stale: bool = False,
    min_effectiveness: Optional[float] = None,
    limit: int = 60,
) -> List[Dict[str, Any]]:
    """Read a curated advisory catalog directly from packet meta + packet payload."""
    index = _load_index()
    meta = index.get("packet_meta") or {}
    normalized_project = str(project_key or "").strip().lower()
    normalized_tool = str(tool_name or "").strip().lower()
    normalized_intent = str(intent_family or "").strip().lower()
    normalized_plane = str(task_plane or "").strip().lower()
    limit_rows = max(1, min(500, int(limit or 60)))

    out: List[Dict[str, Any]] = []
    for packet_id, row in meta.items():
        if not isinstance(row, dict):
            continue
        row_project = str(row.get("project_key") or "").strip().lower()
        if normalized_project and row_project and row_project != normalized_project:
            continue
        row_tool = str(row.get("tool_name") or "").strip().lower()
        if normalized_tool and row_tool and row_tool != normalized_tool:
            continue
        row_intent = str(row.get("intent_family") or "").strip().lower()
        if normalized_intent and row_intent and row_intent != normalized_intent:
            continue
        row_plane = str(row.get("task_plane") or "").strip().lower()
        if normalized_plane and row_plane and row_plane != normalized_plane:
            continue

        try:
            packet = get_packet(str(packet_id or ""))
            if not packet:
                continue
            flags = _readiness_flags(packet)
            if not include_stale and not bool(flags.get("is_fresh", False)):
                continue
            if only_ready and not bool(flags.get("ready_for_use", False)):
                continue
            min_effective = min_effectiveness
            if min_effective is not None and float(packet.get("effectiveness_score", 0.5) or 0.0) < float(min_effective):
                continue
            item = _obsidian_catalog_entry(packet, now_ts=_now())
            item["packet_meta_only"] = False
            out.append(item)
        except Exception:
            # Fall back to meta-only row if packet body cannot be read.
            flags = _readiness_flags(row)
            if not include_stale and not bool(flags.get("is_fresh", False)):
                continue
            if only_ready and not bool(flags.get("ready_for_use", False)):
                continue
            score = float(row.get("effectiveness_score", 0.5) or 0.5)
            if min_effectiveness is not None and score < float(min_effectiveness):
                continue
            out.append({
                "packet_id": str(packet_id or ""),
                "project_key": str(row.get("project_key") or ""),
                "session_context_key": str(row.get("session_context_key") or ""),
                "tool_name": str(row.get("tool_name") or ""),
                "intent_family": str(row.get("intent_family") or ""),
                "task_plane": str(row.get("task_plane") or ""),
                "invalidated": bool(row.get("invalidated", False)),
                "invalidate_reason": str(row.get("invalidate_reason", "") or ""),
                "updated_ts": float(row.get("updated_ts", 0.0) or 0.0),
                "fresh_until_ts": float(row.get("fresh_until_ts", 0.0) or 0.0),
                "ready_for_use": bool(flags.get("ready_for_use", False)),
                "is_fresh": bool(flags.get("is_fresh", False)),
                "readiness_score": float(flags.get("readiness_score", 0.0)),
                "effectiveness_score": score,
                "read_count": _meta_count(row, "read_count"),
                "usage_count": _meta_count(row, "usage_count", fallback_key="read_count"),
                "emit_count": _meta_count(row, "emit_count"),
                "deliver_count": _meta_count(row, "deliver_count", fallback_key="emit_count"),
                "source_summary": _safe_list(row.get("source_summary"), max_items=10),
                "category_summary": _safe_list(row.get("category_summary"), max_items=8),
                "packet_meta_only": True,
            })

    out.sort(
        key=lambda r: (
            float(r.get("readiness_score", 0.0) or 0.0),
            float(r.get("updated_ts", 0.0) or 0.0),
            str(r.get("packet_id") or ""),
        ),
        reverse=True,
    )
    return out[:limit_rows]


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
        index["packet_meta"][packet_id]["invalidate_reason"] = reason[:200]
    _save_index(index)
    try:
        if _obsidian_enabled():
            _export_packet_to_obsidian(packet, force=True)
    except Exception:
        pass
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

    packet["read_count"] = int(packet.get("read_count", 0) or 0) + 1
    packet["last_read_ts"] = _now()
    packet["last_read_route"] = str(route or packet.get("last_read_route") or "")
    packet["usage_count"] = int(packet.get("usage_count", 0) or 0) + 1
    if emitted:
        packet["emit_count"] = int(packet.get("emit_count", 0) or 0) + 1
        packet["deliver_count"] = int(packet.get("deliver_count", 0) or 0) + 1
    packet["last_route"] = str(route or packet.get("last_route") or "")
    packet["last_used_ts"] = _now()
    packet = _normalize_packet(packet)
    save_packet(packet)
    return {
        "ok": True,
        "packet_id": packet_id,
        "read_count": int(packet.get("read_count", 0) or 0),
        "usage_count": int(packet.get("usage_count", 0) or 0),
        "emit_count": int(packet.get("emit_count", 0) or 0),
        "deliver_count": int(packet.get("deliver_count", 0) or 0),
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


def record_packet_outcome(
    packet_id: str,
    *,
    status: str,
    source: str = "implicit",
    tool_name: Optional[str] = None,
    trace_id: Optional[str] = None,
    notes: str = "",
    # Optional: also update helpful/unhelpful counters using this outcome as a weak signal.
    count_effectiveness: bool = True,
) -> Dict[str, Any]:
    """
    Record an outcome tag for a packet.

    Status is a small, operator-meaningful taxonomy:
    - acted: advice was acted on and the step succeeded
    - blocked: advice was acted on but the step failed/blocked
    - harmful: advice was followed and led to a bad outcome (explicit tag)
    - ignored: advice was shown but not acted on (explicit tag)
    """
    packet = get_packet(packet_id)
    if not packet:
        return {"ok": False, "reason": "packet_not_found", "packet_id": packet_id}

    st = str(status or "").strip().lower()
    if st not in {"acted", "blocked", "harmful", "ignored"}:
        return {"ok": False, "reason": "invalid_status", "status": st, "packet_id": packet_id}

    # Outcome counts are separate from explicit helpfulness feedback.
    if st == "acted":
        packet["acted_count"] = int(packet.get("acted_count", 0) or 0) + 1
    elif st == "blocked":
        packet["blocked_count"] = int(packet.get("blocked_count", 0) or 0) + 1
    elif st == "harmful":
        packet["harmful_count"] = int(packet.get("harmful_count", 0) or 0) + 1
    elif st == "ignored":
        packet["ignored_count"] = int(packet.get("ignored_count", 0) or 0) + 1

    if count_effectiveness:
        # Conservative mapping: treat acted as weak-positive, blocked/harmful as negative.
        if st == "acted":
            packet["helpful_count"] = int(packet.get("helpful_count", 0) or 0) + 1
        elif st in {"blocked", "harmful"}:
            packet["unhelpful_count"] = int(packet.get("unhelpful_count", 0) or 0) + 1

    packet["last_outcome"] = {
        "status": st,
        "source": str(source or "")[:80],
        "tool": str(tool_name or "")[:40] if tool_name else "",
        "trace_id": str(trace_id or "")[:120] if trace_id else "",
        "notes": str(notes or "")[:200] if notes else "",
        "ts": _now(),
    }
    packet = _normalize_packet(packet)
    save_packet(packet)
    return {
        "ok": True,
        "packet_id": packet_id,
        "status": st,
        "effectiveness_score": float(packet.get("effectiveness_score", 0.5) or 0.5),
        "acted_count": int(packet.get("acted_count", 0) or 0),
        "blocked_count": int(packet.get("blocked_count", 0) or 0),
        "harmful_count": int(packet.get("harmful_count", 0) or 0),
        "ignored_count": int(packet.get("ignored_count", 0) or 0),
    }


def record_packet_outcome_for_advice(
    advice_id: str,
    *,
    status: str,
    source: str = "explicit",
    tool_name: Optional[str] = None,
    trace_id: Optional[str] = None,
    notes: str = "",
    count_effectiveness: bool = True,
) -> Dict[str, Any]:
    """Find the newest packet that contains advice_id and record an outcome tag on it."""
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
                result = record_packet_outcome(
                    packet_id,
                    status=status,
                    source=source,
                    tool_name=tool_name,
                    trace_id=trace_id,
                    notes=notes,
                    count_effectiveness=count_effectiveness,
                )
                result["matched_advice_id"] = advice
                return result
    return {"ok": False, "reason": "packet_not_found_for_advice", "advice_id": advice}


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
    global PACKET_RELAXED_MAX_CANDIDATES
    global PACKET_LOOKUP_CANDIDATES
    global PACKET_LOOKUP_LLM_ENABLED
    global PACKET_LOOKUP_LLM_PROVIDER
    global PACKET_LOOKUP_LLM_TIMEOUT_S
    global PACKET_LOOKUP_LLM_TOP_K
    global PACKET_LOOKUP_LLM_MIN_CANDIDATES
    global PACKET_LOOKUP_LLM_CONTEXT_CHARS
    global PACKET_LOOKUP_LLM_URL
    global PACKET_LOOKUP_LLM_MODEL
    global OBSIDIAN_EXPORT_ENABLED
    global OBSIDIAN_AUTO_EXPORT
    global OBSIDIAN_EXPORT_MAX_PACKETS
    global DEFAULT_OBSIDIAN_EXPORT_DIR

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

    if "relaxed_max_candidates" in cfg:
        try:
            PACKET_RELAXED_MAX_CANDIDATES = max(
                1,
                min(30, int(cfg.get("relaxed_max_candidates") or 1)),
            )
            applied.append("relaxed_max_candidates")
        except Exception:
            warnings.append("invalid_relaxed_max_candidates")

    if "packet_lookup_candidates" in cfg:
        try:
            PACKET_LOOKUP_CANDIDATES = max(
                1,
                min(30, int(cfg.get("packet_lookup_candidates") or 1)),
            )
            applied.append("packet_lookup_candidates")
        except Exception:
            warnings.append("invalid_packet_lookup_candidates")

    if "packet_lookup_llm_enabled" in cfg:
        PACKET_LOOKUP_LLM_ENABLED = _coerce_bool(
            cfg.get("packet_lookup_llm_enabled"),
            PACKET_LOOKUP_LLM_ENABLED,
        )
        applied.append("packet_lookup_llm_enabled")

    if "packet_lookup_llm_provider" in cfg:
        PACKET_LOOKUP_LLM_PROVIDER = _sanitize_lookup_provider(cfg.get("packet_lookup_llm_provider"))
        applied.append("packet_lookup_llm_provider")

    if "packet_lookup_llm_timeout_s" in cfg:
        try:
            PACKET_LOOKUP_LLM_TIMEOUT_S = max(0.2, float(cfg.get("packet_lookup_llm_timeout_s")))
            applied.append("packet_lookup_llm_timeout_s")
        except Exception:
            warnings.append("invalid_packet_lookup_llm_timeout_s")

    if "packet_lookup_llm_top_k" in cfg:
        try:
            PACKET_LOOKUP_LLM_TOP_K = max(1, min(20, int(cfg.get("packet_lookup_llm_top_k") or 1)))
            applied.append("packet_lookup_llm_top_k")
        except Exception:
            warnings.append("invalid_packet_lookup_llm_top_k")

    if "packet_lookup_llm_min_candidates" in cfg:
        try:
            PACKET_LOOKUP_LLM_MIN_CANDIDATES = max(
                1, min(20, int(cfg.get("packet_lookup_llm_min_candidates") or 1))
            )
            applied.append("packet_lookup_llm_min_candidates")
        except Exception:
            warnings.append("invalid_packet_lookup_llm_min_candidates")

    if "packet_lookup_llm_context_chars" in cfg:
        try:
            PACKET_LOOKUP_LLM_CONTEXT_CHARS = max(
                40, min(5000, int(cfg.get("packet_lookup_llm_context_chars") or 40))
            )
            applied.append("packet_lookup_llm_context_chars")
        except Exception:
            warnings.append("invalid_packet_lookup_llm_context_chars")

    if "packet_lookup_llm_provider_url" in cfg:
        url = str(cfg.get("packet_lookup_llm_provider_url") or PACKET_LOOKUP_LLM_URL).strip()
        if url:
            PACKET_LOOKUP_LLM_URL = url.rstrip("/")
            applied.append("packet_lookup_llm_provider_url")

    if "packet_lookup_llm_model" in cfg:
        model = str(cfg.get("packet_lookup_llm_model") or PACKET_LOOKUP_LLM_MODEL).strip()
        if model:
            PACKET_LOOKUP_LLM_MODEL = model
            applied.append("packet_lookup_llm_model")

    if "obsidian_enabled" in cfg:
        OBSIDIAN_EXPORT_ENABLED = _coerce_bool(
            cfg.get("obsidian_enabled"),
            OBSIDIAN_EXPORT_ENABLED,
        )
        applied.append("obsidian_enabled")

    if "obsidian_auto_export" in cfg:
        OBSIDIAN_AUTO_EXPORT = _coerce_bool(
            cfg.get("obsidian_auto_export"),
            OBSIDIAN_AUTO_EXPORT,
        )
        applied.append("obsidian_auto_export")

    if "obsidian_export_max_packets" in cfg:
        try:
            OBSIDIAN_EXPORT_MAX_PACKETS = max(1, min(5000, int(cfg.get("obsidian_export_max_packets") or 1)))
            applied.append("obsidian_export_max_packets")
        except Exception:
            warnings.append("invalid_obsidian_export_max_packets")

    if "obsidian_export_dir" in cfg:
        try:
            raw_dir = str(cfg.get("obsidian_export_dir") or DEFAULT_OBSIDIAN_EXPORT_DIR).strip()
            if raw_dir:
                _obsidian_dir_override(raw_dir)
            applied.append("obsidian_export_dir")
        except Exception:
            warnings.append("invalid_obsidian_export_dir")

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
        "relaxed_max_candidates": int(PACKET_RELAXED_MAX_CANDIDATES),
        "packet_lookup_candidates": int(PACKET_LOOKUP_CANDIDATES),
        "packet_lookup_llm_enabled": bool(PACKET_LOOKUP_LLM_ENABLED),
        "packet_lookup_llm_provider": str(PACKET_LOOKUP_LLM_PROVIDER),
        "packet_lookup_llm_timeout_s": float(PACKET_LOOKUP_LLM_TIMEOUT_S),
        "packet_lookup_llm_top_k": int(PACKET_LOOKUP_LLM_TOP_K),
        "packet_lookup_llm_min_candidates": int(PACKET_LOOKUP_LLM_MIN_CANDIDATES),
        "packet_lookup_llm_context_chars": int(PACKET_LOOKUP_LLM_CONTEXT_CHARS),
        "packet_lookup_llm_provider_url": str(PACKET_LOOKUP_LLM_URL),
        "packet_lookup_llm_model": str(PACKET_LOOKUP_LLM_MODEL),
        "obsidian_enabled": bool(OBSIDIAN_EXPORT_ENABLED),
        "obsidian_auto_export": bool(OBSIDIAN_AUTO_EXPORT),
        "obsidian_export_max_packets": int(OBSIDIAN_EXPORT_MAX_PACKETS),
        "obsidian_export_dir": str(_obsidian_export_dir()),
    }


def get_store_status() -> Dict[str, Any]:
    index = _load_index()
    meta = index.get("packet_meta") or {}
    total = len(meta)
    active = sum(1 for row in meta.values() if not bool((row or {}).get("invalidated")))
    now_value = _now()
    source_counter: Counter[str] = Counter()
    category_counter: Counter[str] = Counter()
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
    usage_total = sum(_meta_count(row, "usage_count", fallback_key="read_count") for row in meta.values())
    emit_total = sum(_meta_count(row, "emit_count") for row in meta.values())
    deliver_total = sum(_meta_count(row, "deliver_count", fallback_key="emit_count") for row in meta.values())
    read_total = sum(_meta_count(row, "read_count") for row in meta.values())
    feedback_total = sum(_meta_count(row, "feedback_count") for row in meta.values())
    noisy_total = sum(_meta_count(row, "noisy_count") for row in meta.values())
    avg_effectiveness = 0.0
    freshness_age_sum = 0.0
    freshness_age_count = 0
    age_sum = 0.0
    age_count = 0
    stale = 0
    ready_meta = 0
    inactive = total - active
    if meta:
        avg_effectiveness = sum(
            float((row or {}).get("effectiveness_score", 0.5) or 0.5)
            for row in meta.values()
        ) / max(1, len(meta))
        for row in meta.values():
            if bool((row or {}).get("invalidated")):
                continue
            flags = _readiness_flags(_normalize_packet(dict(row)))
            if bool(flags.get("ready_for_use")):
                ready_meta += 1
            for source in _safe_list(row.get("source_summary"), max_items=1):
                source_counter[source] += 1
            for category in _safe_list(row.get("category_summary"), max_items=1):
                category_counter[category] += 1
        for row in meta.values():
            if bool((row or {}).get("invalidated")):
                continue
            updated_ts = float((row or {}).get("updated_ts", 0.0) or 0.0)
            age_sum += max(0.0, now_value - updated_ts)
            age_count += 1
            freshness_age = float((row or {}).get("fresh_until_ts", 0.0) or 0.0) - now_value
            if freshness_age > 0.0:
                freshness_age_sum += freshness_age
                freshness_age_count += 1
    stale = sum(
        1
        for row in meta.values()
        if not bool((row or {}).get("invalidated"))
        and float((row or {}).get("fresh_until_ts", 0.0)) < now_value
    )
    active_rows = max(1, int(active))
    top_sources = [
        {"name": str(name), "count": int(count)}
        for name, count in source_counter.most_common(5)
    ]
    top_categories = [
        {"name": str(name), "count": int(count)}
        for name, count in category_counter.most_common(5)
    ]
    top_concentration = 0.0
    if top_categories:
        top_concentration = top_categories[0]["count"] / float(max(active_rows, 1))
    return {
        "schema_version": int(index.get(INDEX_SCHEMA_VERSION_KEY, 1) or 1),
        "total_packets": total,
        "active_packets": active,
        "fresh_packets": fresh,
        "stale_packets": stale,
        "inactive_packets": inactive,
        "freshness_ratio": round(float(fresh) / max(total, 1), 3),
        "ready_packets": int(ready_meta),
        "stale_ratio": round(float(stale) / max(total, 1), 3),
        "inactive_ratio": round(float(inactive) / max(total, 1), 3),
        "readiness_ratio": round(float(fresh) / max(active_rows, 1), 3),
        "catalog_size": int(total),
        "catalog_ready_packets": int(ready_meta),
        "top_sources": top_sources,
        "top_categories": top_categories,
        "top_category_concentration": round(float(top_concentration), 3),
        "lookup_candidate_budget": int(PACKET_LOOKUP_CANDIDATES),
        "packet_age_avg_s": round(float(age_sum / max(age_count, 1)), 2),
        "packet_freshness_age_avg_s": round(
            float(freshness_age_sum / max(freshness_age_count, 1)),
            2,
        ),
        "queue_depth": queue_depth,
        "usage_total": usage_total,
        "read_total": read_total,
        "emit_total": emit_total,
        "deliver_total": deliver_total,
        "category_inventory": [
            {"category": str(name), "count": int(count)}
            for name, count in category_counter.most_common(20)
        ],
        "source_inventory": [
            {"source": str(name), "count": int(count)}
            for name, count in source_counter.most_common(20)
        ],
        "feedback_total": feedback_total,
        "noisy_total": noisy_total,
        "emit_hit_rate": (emit_total / max(usage_total, 1)) if usage_total > 0 else None,
        "deliver_hit_rate": (deliver_total / max(usage_total, 1)) if usage_total > 0 else None,
        "hit_rate": (deliver_total / max(usage_total, 1)) if usage_total > 0 else None,
        "avg_effectiveness_score": round(float(avg_effectiveness), 3),
        "lookup_rerank_enabled": bool(PACKET_LOOKUP_LLM_ENABLED),
        "config": get_packet_store_config(),
        "lookup_rerank_provider": str(PACKET_LOOKUP_LLM_PROVIDER),
        "obsidian_enabled": bool(OBSIDIAN_EXPORT_ENABLED),
        "obsidian_auto_export": bool(OBSIDIAN_AUTO_EXPORT),
        "obsidian_export_dir": str(_obsidian_export_dir()),
        "obsidian_export_dir_exists": bool(_obsidian_export_dir().exists()),
        "obsidian_index_file": str(OBSIDIAN_INDEX_FILE),
        "index_file": str(INDEX_FILE),
    }


try:
    _BOOT_PACKET_CFG = _load_packet_store_config()
    if _BOOT_PACKET_CFG:
        apply_packet_store_config(_BOOT_PACKET_CFG)
    try:
        from .tuneables_reload import register_reload as _register_packet_store_reload

        _register_packet_store_reload(
            "advisory_packet_store",
            apply_packet_store_config,
            label="advisory_packet_store.apply_config",
        )
    except Exception:
        pass
except Exception:
    pass
