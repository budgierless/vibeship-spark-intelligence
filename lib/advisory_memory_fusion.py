"""
Memory fusion adapter for advisory.

Phase 1 scope:
- Build an evidence bundle across available Spark memory sources
- Degrade gracefully when sources are missing
- Expose `memory_absent_declared` for deterministic fallback behavior
"""

from __future__ import annotations

import json
import re
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from .outcome_log import read_outcomes
from .primitive_filter import is_primitive_text

COGNITIVE_FILE = Path.home() / ".spark" / "cognitive_insights.json"
CHIP_INSIGHTS_DIR = Path.home() / ".spark" / "chip_insights"
ORCHESTRATION_DIR = Path.home() / ".spark" / "orchestration"
_NOISE_PATTERNS = (
    re.compile(r"\btool[_\s-]*\d+[_\s-]*error\b", re.I),
    re.compile(r"\bi struggle with tool_", re.I),
    re.compile(r"\berror_pattern:", re.I),
    re.compile(r"\brequest failed with status code\s+404\b", re.I),
)
_TOKEN_STOPWORDS = {
    "the",
    "and",
    "for",
    "with",
    "that",
    "this",
    "from",
    "into",
    "your",
    "have",
    "when",
    "what",
    "should",
    "would",
    "could",
    "about",
    "there",
    "here",
    "were",
    "been",
    "will",
    "just",
    "they",
    "them",
    "then",
    "than",
    "also",
    "only",
    "much",
    "more",
    "very",
    "some",
    "like",
    "into",
    "across",
    "using",
    "use",
    "used",
    "run",
    "runs",
}


def _is_noise_evidence(text: str) -> bool:
    sample = str(text or "").strip()
    if not sample:
        return True
    if is_primitive_text(sample):
        return True
    return any(rx.search(sample) for rx in _NOISE_PATTERNS)


def _tail_jsonl(path: Path, limit: int) -> List[Dict[str, Any]]:
    if limit <= 0 or not path.exists():
        return []
    out: List[Dict[str, Any]] = []
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
        for line in lines[-limit:]:
            line = (line or "").strip()
            if not line:
                continue
            try:
                row = json.loads(line)
                if isinstance(row, dict):
                    out.append(row)
            except Exception:
                continue
    except Exception:
        return []
    return out


def _coerce_ts(value: Any, default: float = 0.0) -> float:
    try:
        if isinstance(value, (int, float)):
            return float(value)
        text = str(value or "").strip()
        if not text:
            return float(default)
        if text.endswith("Z"):
            text = text[:-1] + "+00:00"
        return float(datetime.fromisoformat(text).timestamp())
    except Exception:
        try:
            return float(value)
        except Exception:
            return float(default)


def _tokenize_text(text: str) -> List[str]:
    parts = re.split(r"[^a-z0-9_]+", str(text or "").lower())
    out: List[str] = []
    for token in parts:
        token = token.strip()
        if len(token) < 3:
            continue
        if token in _TOKEN_STOPWORDS:
            continue
        out.append(token)
    return out


def _intent_relevance_score(intent_tokens: set[str], text: str) -> float:
    if not intent_tokens:
        return 0.0
    tokens = set(_tokenize_text(text))
    if not tokens:
        return 0.0
    overlap = len(intent_tokens & tokens)
    if overlap > 0:
        return float(overlap)

    weak = 0
    for needle in intent_tokens:
        for token in tokens:
            if needle in token or token in needle:
                weak += 1
                break
    if weak > 0:
        return 0.2 + min(0.6, weak * 0.1)
    return 0.0


def _collect_cognitive(limit: int = 6) -> List[Dict[str, Any]]:
    if not COGNITIVE_FILE.exists():
        return []
    try:
        data = json.loads(COGNITIVE_FILE.read_text(encoding="utf-8"))
    except Exception:
        return []

    rows: List[Dict[str, Any]] = []
    if isinstance(data, list):
        rows = [r for r in data if isinstance(r, dict)]
    elif isinstance(data, dict):
        if isinstance(data.get("insights"), dict):
            rows = [r for r in data.get("insights", {}).values() if isinstance(r, dict)]
        elif isinstance(data.get("insights"), list):
            rows = [r for r in data.get("insights", []) if isinstance(r, dict)]

    rows = rows[-max(0, limit):]
    evidence: List[Dict[str, Any]] = []
    for row in rows:
        text = str(row.get("insight") or row.get("text") or "").strip()
        if not text:
            continue
        if _is_noise_evidence(text):
            continue
        evidence.append(
            {
                "source": "cognitive",
                "id": str(row.get("key") or row.get("insight_key") or text[:48]),
                "text": text,
                "confidence": float(row.get("reliability") or row.get("confidence") or 0.5),
                "created_at": float(row.get("timestamp") or row.get("created_at") or 0.0),
            }
        )
    return evidence


def _collect_eidos(intent_text: str, limit: int = 5) -> List[Dict[str, Any]]:
    if not intent_text.strip():
        return []
    try:
        from .eidos import get_retriever

        retriever = get_retriever()
        items = retriever.retrieve_for_intent(intent_text)[:limit]
    except Exception:
        return []

    evidence: List[Dict[str, Any]] = []
    for item in items:
        statement = str(getattr(item, "statement", "") or "").strip()
        if not statement:
            continue
        if _is_noise_evidence(statement):
            continue
        evidence.append(
            {
                "source": "eidos",
                "id": str(getattr(item, "distillation_id", "") or statement[:48]),
                "text": statement,
                "confidence": float(getattr(item, "confidence", 0.6) or 0.6),
                "created_at": float(getattr(item, "created_at", 0.0) or 0.0),
            }
        )
    return evidence


def _collect_chips(limit: int = 6) -> List[Dict[str, Any]]:
    if not CHIP_INSIGHTS_DIR.exists():
        return []
    files = sorted(CHIP_INSIGHTS_DIR.glob("*.jsonl"), key=lambda p: p.stat().st_mtime, reverse=True)[:4]
    evidence: List[Dict[str, Any]] = []
    min_quality = 0.30
    min_confidence = 0.45
    for fp in files:
        for row in _tail_jsonl(fp, limit=max(24, limit * 8)):
            captured = row.get("captured_data") or {}
            quality = (captured.get("quality_score") or {}) if isinstance(captured, dict) else {}
            quality_total = float(quality.get("total", 0.0) or 0.0)
            conf = float(row.get("confidence") or row.get("score") or quality_total or 0.0)
            if quality_total < min_quality and conf < min_confidence:
                continue
            text = str(
                row.get("insight")
                or row.get("text")
                or row.get("summary")
                or row.get("content")
                or (captured.get("summary") if isinstance(captured, dict) else "")
                or ""
            ).strip()
            if (not text) and isinstance(captured, dict):
                for key in ("signal", "trend", "pattern", "topic"):
                    if captured.get(key):
                        text = f"{key}: {captured.get(key)}"
                        break
            if not text:
                continue
            if _is_noise_evidence(text):
                continue
            evidence.append(
                {
                    "source": "chips",
                    "id": str(
                        row.get("insight_key")
                        or row.get("id")
                        or row.get("chip_id")
                        or f"{fp.stem}:{len(evidence)}"
                    ),
                    "text": text,
                    "confidence": max(conf, quality_total),
                    "created_at": _coerce_ts(row.get("ts") or row.get("timestamp") or row.get("created_at") or 0.0),
                    "meta": {
                        "file": fp.name,
                        "chip_id": row.get("chip_id") or fp.stem,
                        "observer": row.get("observer") or row.get("observer_name"),
                        "quality_total": quality_total,
                    },
                }
            )
            if len(evidence) >= limit:
                return evidence
    return evidence


def _collect_outcomes(intent_text: str, limit: int = 6) -> List[Dict[str, Any]]:
    cutoff = time.time() - (14 * 24 * 3600.0)
    rows = read_outcomes(limit=max(12, limit * 10), since=cutoff)
    intent_tokens = set(_tokenize_text(intent_text))
    scored_rows: List[tuple[float, float, Dict[str, Any]]] = []
    fallback_rows: List[tuple[float, Dict[str, Any]]] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        text = str(row.get("text") or row.get("result") or "").strip()
        if not text:
            continue
        if _is_noise_evidence(text):
            continue
        created_at = float(row.get("created_at") or 0.0)
        if not intent_tokens:
            fallback_rows.append((created_at, row))
            continue
        tokens = set(_tokenize_text(text))
        overlap = len(intent_tokens & tokens)
        if overlap > 0:
            scored_rows.append((float(overlap), created_at, row))
        else:
            # Keep lexical-near rows as weak fallback only when no direct match exists.
            weak_overlap = 0
            for token in intent_tokens:
                if any(token in t or t in token for t in tokens):
                    weak_overlap += 1
            if weak_overlap > 0:
                scored_rows.append((0.5 + min(0.4, weak_overlap * 0.1), created_at, row))
            else:
                fallback_rows.append((created_at, row))

    selected_rows: List[Dict[str, Any]]
    if scored_rows:
        scored_rows.sort(key=lambda t: (t[0], t[1]), reverse=True)
        selected_rows = [row for _, _, row in scored_rows[: max(1, limit)]]
    else:
        fallback_rows.sort(key=lambda t: t[0], reverse=True)
        selected_rows = [row for _, row in fallback_rows[: max(1, min(limit, 2))]]

    evidence: List[Dict[str, Any]] = []
    for row in selected_rows:
        text = str(row.get("text") or row.get("result") or "").strip()
        if not text:
            continue
        if _is_noise_evidence(text):
            continue
        polarity = str(row.get("polarity") or "neutral")
        confidence = 0.7 if polarity == "pos" else (0.45 if polarity == "neutral" else 0.8)
        evidence.append(
            {
                "source": "outcomes",
                "id": str(row.get("outcome_id") or f"outcome:{len(evidence)}"),
                "text": text,
                "confidence": confidence,
                "created_at": float(row.get("created_at") or 0.0),
                "meta": {"polarity": polarity, "event_type": row.get("event_type")},
            }
        )
    return evidence


def _collect_orchestration(limit: int = 5) -> List[Dict[str, Any]]:
    handoffs = ORCHESTRATION_DIR / "handoffs.jsonl"
    if not handoffs.exists():
        return []
    evidence: List[Dict[str, Any]] = []
    for row in _tail_jsonl(handoffs, limit=limit):
        ctx = row.get("context") or {}
        prompt = str(ctx.get("prompt") or ctx.get("task") or ctx.get("summary") or "").strip()
        if not prompt:
            continue
        if _is_noise_evidence(prompt):
            continue
        evidence.append(
            {
                "source": "orchestration",
                "id": str(row.get("handoff_id") or f"handoff:{len(evidence)}"),
                "text": prompt,
                "confidence": 0.55,
                "created_at": float(row.get("timestamp") or 0.0),
                "meta": {"to_agent": row.get("to_agent"), "success": row.get("success")},
            }
        )
    return evidence


def _collect_mind(intent_text: str, limit: int = 4) -> List[Dict[str, Any]]:
    if not intent_text.strip():
        return []
    try:
        from .mind_bridge import get_mind_bridge

        bridge = get_mind_bridge()
        memories = bridge.retrieve_relevant(intent_text, limit=limit)
    except Exception:
        return []
    evidence: List[Dict[str, Any]] = []
    for mem in memories:
        if not isinstance(mem, dict):
            continue
        text = str(mem.get("content") or mem.get("text") or "").strip()
        if not text:
            continue
        if _is_noise_evidence(text):
            continue
        evidence.append(
            {
                "source": "mind",
                "id": str(mem.get("memory_id") or mem.get("id") or f"mind:{len(evidence)}"),
                "text": text,
                "confidence": float(mem.get("score") or 0.6),
                "created_at": float(mem.get("created_at") or 0.0),
            }
        )
    return evidence


def _collect_with_status(fetcher: Callable[[], List[Dict[str, Any]]]) -> Dict[str, Any]:
    try:
        rows = fetcher()
        return {"available": True, "rows": list(rows or [])}
    except Exception as exc:
        return {"available": False, "rows": [], "error": str(exc)}


def build_memory_bundle(
    *,
    session_id: str,
    intent_text: str,
    intent_family: str,
    tool_name: str,
    include_mind: bool = False,
) -> Dict[str, Any]:
    """
    Build a single memory evidence bundle for advisory decisions.
    """
    source_results = {
        "cognitive": _collect_with_status(lambda: _collect_cognitive(limit=6)),
        "eidos": _collect_with_status(lambda: _collect_eidos(intent_text, limit=5)),
        "chips": _collect_with_status(lambda: _collect_chips(limit=6)),
        "outcomes": _collect_with_status(lambda: _collect_outcomes(intent_text, limit=6)),
        "orchestration": _collect_with_status(lambda: _collect_orchestration(limit=5)),
    }
    if include_mind:
        source_results["mind"] = _collect_with_status(lambda: _collect_mind(intent_text, limit=4))

    evidence: List[Dict[str, Any]] = []
    missing_sources: List[str] = []
    source_summary: Dict[str, Dict[str, Any]] = {}

    for source_name, result in source_results.items():
        rows = result.get("rows") or []
        available = bool(result.get("available", True))
        if not available:
            missing_sources.append(source_name)
        source_summary[source_name] = {
            "available": available,
            "count": len(rows),
            "error": result.get("error"),
        }
        evidence.extend(rows)

    intent_tokens = set(_tokenize_text(intent_text))
    scored: List[tuple[float, float, float, Dict[str, Any]]] = []
    for row in evidence:
        text = str((row or {}).get("text") or "").strip()
        if not text:
            continue
        relevance = _intent_relevance_score(intent_tokens, text)
        scored.append(
            (
                relevance,
                float(row.get("confidence") or 0.0),
                float(row.get("created_at") or 0.0),
                row,
            )
        )

    if scored and intent_tokens:
        relevant = [entry for entry in scored if entry[0] > 0.0]
        if relevant:
            scored = relevant

    scored.sort(key=lambda t: (t[0], t[1], t[2]), reverse=True)
    evidence = [row for _, _, _, row in scored]

    deduped: List[Dict[str, Any]] = []
    seen_text = set()
    for row in evidence:
        text = str((row or {}).get("text") or "").strip()
        if not text or _is_noise_evidence(text):
            continue
        key = " ".join(text.lower().split())[:180]
        if key in seen_text:
            continue
        seen_text.add(key)
        deduped.append(row)
        if len(deduped) >= 24:
            break
    evidence = deduped

    memory_absent = len(evidence) == 0

    return {
        "session_id": session_id,
        "intent_family": intent_family or "emergent_other",
        "tool_name": tool_name,
        "intent_text": intent_text,
        "generated_ts": time.time(),
        "sources": source_summary,
        "missing_sources": missing_sources,
        "evidence": evidence,
        "evidence_count": len(evidence),
        "memory_absent_declared": memory_absent,
    }
