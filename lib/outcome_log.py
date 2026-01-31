"""
Outcome log helpers for prediction validation.

Phase 3: Outcome-Driven Learning
- Link outcomes to specific insights for validation
- Support chip-scoped outcomes (per domain)
- Track outcome -> insight attribution for learning
"""

from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

OUTCOMES_FILE = Path.home() / ".spark" / "outcomes.jsonl"
OUTCOME_LINKS_FILE = Path.home() / ".spark" / "outcome_links.jsonl"


def _hash_id(*parts: str) -> str:
    raw = "|".join(p or "" for p in parts).encode("utf-8")
    return hashlib.sha1(raw).hexdigest()[:12]


def make_outcome_id(*parts: str) -> str:
    return _hash_id(*parts)


def append_outcomes(rows: Iterable[Dict[str, Any]]) -> int:
    """Append outcome rows to the shared outcomes log. Returns count written."""
    if not rows:
        return 0
    OUTCOMES_FILE.parent.mkdir(parents=True, exist_ok=True)
    written = 0
    with OUTCOMES_FILE.open("a", encoding="utf-8") as f:
        for row in rows:
            if not row:
                continue
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
            written += 1
    return written


def append_outcome(row: Dict[str, Any]) -> int:
    return append_outcomes([row] if row else [])


def build_explicit_outcome(
    result: str,
    text: str = "",
    *,
    tool: Optional[str] = None,
    created_at: Optional[float] = None,
) -> Tuple[Dict[str, Any], str]:
    """Build an explicit outcome row from a user check-in."""
    res = (result or "").strip().lower()
    if res in {"yes", "y", "success", "ok", "good", "worked"}:
        polarity = "pos"
    elif res in {"partial", "mixed", "some", "meh", "unclear"}:
        polarity = "neutral"
    else:
        polarity = "neg"
    now = float(created_at or time.time())
    clean_text = (text or "").strip()
    if not clean_text:
        clean_text = f"explicit check-in: {res or 'unknown'}"
    row = {
        "outcome_id": make_outcome_id(str(now), res, clean_text[:120]),
        "event_type": "explicit_checkin",
        "tool": tool,
        "text": clean_text,
        "polarity": polarity,
        "result": res or "unknown",
        "created_at": now,
    }
    return row, polarity


# =============================================================================
# Phase 3: Outcome-Insight Linking
# =============================================================================

def link_outcome_to_insight(
    outcome_id: str,
    insight_key: str,
    *,
    chip_id: Optional[str] = None,
    confidence: float = 1.0,
    notes: str = "",
) -> Dict[str, Any]:
    """
    Link an outcome to a specific insight for validation.

    This creates an explicit attribution between:
    - An outcome (something that happened - success/failure)
    - An insight (something Spark learned)

    The validation loop uses these links to validate/contradict insights.
    """
    link = {
        "link_id": _hash_id(outcome_id, insight_key, str(time.time())),
        "outcome_id": outcome_id,
        "insight_key": insight_key,
        "chip_id": chip_id,
        "confidence": confidence,
        "notes": notes,
        "created_at": time.time(),
        "validated": False,
    }

    OUTCOME_LINKS_FILE.parent.mkdir(parents=True, exist_ok=True)
    with OUTCOME_LINKS_FILE.open("a", encoding="utf-8") as f:
        f.write(json.dumps(link, ensure_ascii=False) + "\n")

    return link


def get_outcome_links(
    insight_key: Optional[str] = None,
    outcome_id: Optional[str] = None,
    chip_id: Optional[str] = None,
    limit: int = 100,
) -> List[Dict[str, Any]]:
    """Get outcome-insight links, optionally filtered."""
    if not OUTCOME_LINKS_FILE.exists():
        return []

    links = []
    with OUTCOME_LINKS_FILE.open("r", encoding="utf-8") as f:
        for line in f:
            try:
                link = json.loads(line.strip())
                if insight_key and link.get("insight_key") != insight_key:
                    continue
                if outcome_id and link.get("outcome_id") != outcome_id:
                    continue
                if chip_id and link.get("chip_id") != chip_id:
                    continue
                links.append(link)
            except Exception:
                pass

    return links[-limit:]


def read_outcomes(
    limit: int = 100,
    polarity: Optional[str] = None,
    chip_id: Optional[str] = None,
    since: Optional[float] = None,
) -> List[Dict[str, Any]]:
    """Read outcomes from the log, optionally filtered."""
    if not OUTCOMES_FILE.exists():
        return []

    outcomes = []
    with OUTCOMES_FILE.open("r", encoding="utf-8") as f:
        for line in f:
            try:
                outcome = json.loads(line.strip())
                if polarity and outcome.get("polarity") != polarity:
                    continue
                if chip_id and outcome.get("chip_id") != chip_id:
                    continue
                if since and (outcome.get("created_at", 0) < since):
                    continue
                outcomes.append(outcome)
            except Exception:
                pass

    return outcomes[-limit:]


def get_unlinked_outcomes(limit: int = 50) -> List[Dict[str, Any]]:
    """Get outcomes that haven't been linked to any insight yet."""
    outcomes = read_outcomes(limit=limit * 2)
    links = get_outcome_links(limit=1000)

    linked_ids = {link.get("outcome_id") for link in links}
    unlinked = [o for o in outcomes if o.get("outcome_id") not in linked_ids]

    return unlinked[-limit:]


def build_chip_outcome(
    chip_id: str,
    outcome_type: str,
    result: str,
    *,
    insight: str = "",
    data: Optional[Dict] = None,
    session_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Build an outcome row for a chip-specific event.

    Args:
        chip_id: Which chip this outcome belongs to
        outcome_type: "positive", "negative", or "neutral"
        result: Description of what happened
        insight: The insight this validates/contradicts
        data: Additional outcome data (metrics, etc.)
    """
    polarity_map = {"positive": "pos", "negative": "neg", "neutral": "neutral"}
    polarity = polarity_map.get(outcome_type, "neutral")

    now = time.time()
    row = {
        "outcome_id": make_outcome_id(chip_id, str(now), result[:100]),
        "event_type": f"chip_{outcome_type}",
        "chip_id": chip_id,
        "text": result,
        "insight": insight,
        "polarity": polarity,
        "data": data or {},
        "created_at": now,
    }

    if session_id:
        row["session_id"] = session_id

    return row


def get_outcome_stats(chip_id: Optional[str] = None) -> Dict[str, Any]:
    """Get outcome statistics, optionally filtered by chip."""
    outcomes = read_outcomes(limit=1000, chip_id=chip_id)
    links = get_outcome_links(chip_id=chip_id, limit=1000)

    by_polarity = {"pos": 0, "neg": 0, "neutral": 0}
    for o in outcomes:
        pol = o.get("polarity", "neutral")
        by_polarity[pol] = by_polarity.get(pol, 0) + 1

    validated_links = sum(1 for l in links if l.get("validated"))

    return {
        "total_outcomes": len(outcomes),
        "by_polarity": by_polarity,
        "total_links": len(links),
        "validated_links": validated_links,
        "unlinked": len(outcomes) - len(links),
    }
