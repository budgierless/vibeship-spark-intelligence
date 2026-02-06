"""
Memory fusion adapter for advisory.

Phase 1 scope:
- Build an evidence bundle across available Spark memory sources
- Degrade gracefully when sources are missing
- Expose `memory_absent_declared` for deterministic fallback behavior
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from .outcome_log import read_outcomes

COGNITIVE_FILE = Path.home() / ".spark" / "cognitive_insights.json"
CHIP_INSIGHTS_DIR = Path.home() / ".spark" / "chip_insights"
ORCHESTRATION_DIR = Path.home() / ".spark" / "orchestration"


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
    files = sorted(CHIP_INSIGHTS_DIR.glob("*.jsonl"), key=lambda p: p.stat().st_mtime, reverse=True)[:3]
    evidence: List[Dict[str, Any]] = []
    for fp in files:
        for row in _tail_jsonl(fp, limit=3):
            text = str(row.get("insight") or row.get("text") or row.get("summary") or "").strip()
            if not text:
                continue
            evidence.append(
                {
                    "source": "chips",
                    "id": str(row.get("insight_key") or row.get("id") or f"{fp.stem}:{len(evidence)}"),
                    "text": text,
                    "confidence": float(row.get("score") or row.get("confidence") or 0.55),
                    "created_at": float(row.get("ts") or row.get("created_at") or 0.0),
                    "meta": {"file": fp.name},
                }
            )
            if len(evidence) >= limit:
                return evidence
    return evidence


def _collect_outcomes(limit: int = 6) -> List[Dict[str, Any]]:
    cutoff = time.time() - (14 * 24 * 3600.0)
    rows = read_outcomes(limit=limit * 4, since=cutoff)
    evidence: List[Dict[str, Any]] = []
    for row in rows[-limit:]:
        text = str(row.get("text") or row.get("result") or "").strip()
        if not text:
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
        "outcomes": _collect_with_status(lambda: _collect_outcomes(limit=6)),
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

    evidence.sort(key=lambda row: (float(row.get("confidence") or 0.0), float(row.get("created_at") or 0.0)), reverse=True)
    evidence = evidence[:24]

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

