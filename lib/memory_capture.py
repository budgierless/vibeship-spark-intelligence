"""Memory capture engine (portable, lightweight)

Goal
----
Turn high-signal conversational statements into durable Spark learnings *without*
platform coupling.

Design constraints
------------------
- Works from normalized SparkEventV1 payloads stored in the existing queue.
- No LLM required (fast, deterministic).
- Adapters can optionally send explicit intent events:
    kind=command, payload.intent="remember"
- Otherwise we use heuristic detection (keywords + emphasis signals).

This module is intentionally pure + testable:
- input: Spark queue events (SparkEvent)
- output: either committed learnings or pending suggestions

"""

from __future__ import annotations

import json
import re
import time
import hashlib
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from lib.cognitive_learner import CognitiveCategory, get_cognitive_learner
from lib.queue import read_recent_events, EventType
from lib.memory_banks import store_memory
from lib.outcome_log import append_outcome, make_outcome_id


PENDING_DIR = Path.home() / ".spark"
PENDING_FILE = PENDING_DIR / "pending_memory.json"
STATE_FILE = PENDING_DIR / "memory_capture_state.json"
MAX_CAPTURE_CHARS = 2000


# -----------------------------
# Scoring / Heuristics
# -----------------------------

HARD_TRIGGERS = {
    "remember this": 1.0,
    "don\u2019t forget": 0.95,
    "dont forget": 0.95,
    "note this": 0.9,
    "save this": 0.9,
    "lock this in": 0.95,
    "non-negotiable": 0.95,
    "hard rule": 0.95,
    "hard boundary": 0.95,
    "from now on": 0.85,
    "always": 0.65,
    "never": 0.65,
}

SOFT_TRIGGERS = {
    "i prefer": 0.55,
    "i hate": 0.75,
    "i don\u2019t like": 0.65,
    "i dont like": 0.65,
    "i need": 0.5,
    "i want": 0.5,
    "we should": 0.45,
    "design constraint": 0.65,
    "default": 0.4,
    "compatibility": 0.35,
    "adaptability": 0.35,
    "should": 0.25,
    "must": 0.4,
    "non-negotiable": 0.55,
    "for this project": 0.65,
}

DECISION_MARKERS = {
    "let's do it": 0.25,
    "lets do it": 0.25,
    "ship it": 0.25,
    "do it": 0.15,
}
_DECISION_EXTRA = {
    "launch",
    "greenlight",
    "approved",
    "go with",
    "move forward",
}


def _norm(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "").strip().lower())


def _is_decision_text(text: str) -> bool:
    t = _norm(text)
    for k in DECISION_MARKERS:
        if k in t:
            return True
    for k in _DECISION_EXTRA:
        if k in t:
            return True
    return False


def infer_category(text: str) -> CognitiveCategory:
    t = _norm(text)
    if any(k in t for k in ["security", "boundary", "non-negotiable", "hard rule"]):
        return CognitiveCategory.META_LEARNING
    if any(k in t for k in ["prefer", "hate", "don't like", "dont like", "love"]):
        return CognitiveCategory.USER_UNDERSTANDING
    if any(k in t for k in ["tone", "be direct", "no sugarcoating", "explain"]):
        return CognitiveCategory.COMMUNICATION
    if any(k in t for k in ["principle", "philosophy", "rule", "design constraint", "architecture", "compatibility", "adaptability"]):
        return CognitiveCategory.WISDOM
    return CognitiveCategory.META_LEARNING


def importance_score(text: str) -> Tuple[float, Dict[str, float]]:
    """Return (score 0..1, breakdown)."""
    t = _norm(text)
    breakdown: Dict[str, float] = {}

    def apply(phrases: Dict[str, float], bucket: str):
        s = 0.0
        for p, w in phrases.items():
            if p in t:
                s = max(s, w)  # strongest match wins
        if s:
            breakdown[bucket] = s
        return s

    score = 0.0
    score = max(score, apply(HARD_TRIGGERS, "hard_trigger"))
    score = max(score, apply(SOFT_TRIGGERS, "soft_trigger"))
    score = max(score, apply(DECISION_MARKERS, "decision_marker"))

    # Emphasis signals (cheap but useful)
    if re.search(r"\b(must|nonnegotiable|non-negotiable|critical|important)\b", t):
        breakdown["emphasis"] = max(breakdown.get("emphasis", 0.0), 0.2)
        score = min(1.0, score + 0.2)

    # ALL CAPS word emphasis
    if re.search(r"\b[A-Z]{4,}\b", (text or "")):
        breakdown["caps"] = max(breakdown.get("caps", 0.0), 0.1)
        score = min(1.0, score + 0.1)

    # Length heuristic: longer statements more likely to be principles
    if len((text or "").strip()) > 180:
        breakdown["length"] = max(breakdown.get("length", 0.0), 0.05)
        score = min(1.0, score + 0.05)

    return float(min(1.0, score)), breakdown


# -----------------------------
# Pending suggestions storage
# -----------------------------

@dataclass
class MemorySuggestion:
    suggestion_id: str
    created_at: float
    session_id: str
    text: str
    category: str
    score: float
    breakdown: Dict[str, float]
    status: str = "pending"  # pending|accepted|rejected|auto_saved

    def to_dict(self) -> Dict[str, Any]:
        return {
            "suggestion_id": self.suggestion_id,
            "created_at": self.created_at,
            "session_id": self.session_id,
            "text": self.text,
            "category": self.category,
            "score": self.score,
            "breakdown": self.breakdown,
            "status": self.status,
        }


def _load_pending() -> Dict[str, Any]:
    if not PENDING_FILE.exists():
        return {"items": []}
    try:
        return json.loads(PENDING_FILE.read_text())
    except Exception:
        return {"items": []}


def _save_pending(d: Dict[str, Any]) -> None:
    PENDING_DIR.mkdir(parents=True, exist_ok=True)
    PENDING_FILE.write_text(json.dumps(d, indent=2, sort_keys=True))


def _state() -> Dict[str, Any]:
    if not STATE_FILE.exists():
        return {}
    try:
        return json.loads(STATE_FILE.read_text())
    except Exception:
        return {}


def _save_state(d: Dict[str, Any]) -> None:
    PENDING_DIR.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(d, indent=2, sort_keys=True))


def _make_id(session_id: str, text: str) -> str:
    raw = f"{session_id}|{_norm(normalize_memory_text(text))}".encode("utf-8")
    return hashlib.sha1(raw).hexdigest()[:10]


# -----------------------------
# Core processing
# -----------------------------

AUTO_SAVE_THRESHOLD = 0.82
SUGGEST_THRESHOLD = 0.55


_REMEMBER_PREFIX_RE = re.compile(r"^\s*(remember this|note this|save this)\s*:\s*", re.IGNORECASE)
_MESSAGE_ID_LINE_RE = re.compile(r"\n?\[message_id:.*?\]\s*$", re.IGNORECASE | re.DOTALL)
# Clawdbot transcript prefix, e.g. "[Telegram Meta ...] "
_CHANNEL_PREFIX_RE = re.compile(r"^\s*\[[^\]]+\]\s*", re.IGNORECASE)


def normalize_memory_text(text: str) -> str:
    t = (text or "").strip()
    t = _CHANNEL_PREFIX_RE.sub("", t)
    t = _REMEMBER_PREFIX_RE.sub("", t)
    t = _MESSAGE_ID_LINE_RE.sub("", t).strip()
    if len(t) > MAX_CAPTURE_CHARS:
        t = t[:MAX_CAPTURE_CHARS].rstrip()
    return t


def commit_learning(text: str, category: CognitiveCategory, context: str = "", session_id: str = "") -> bool:
    try:
        cog = get_cognitive_learner()
        clean = normalize_memory_text(text)
        if not clean:
            return False
        if len(clean) > MAX_CAPTURE_CHARS:
            clean = clean[:MAX_CAPTURE_CHARS].rstrip()
        # Use a short context snippet so retrieval has something relevant.
        ctx = (context or clean)[:100]
        cog.add_insight(category=category, insight=clean, context=ctx, confidence=0.7)

        # Also store into layered memory banks for fast retrieval + future project scoping.
        try:
            store_memory(text=clean, category=category.value, session_id=session_id or None, source="capture")
        except Exception:
            pass
        try:
            if _is_decision_text(clean):
                append_outcome({
                    "outcome_id": make_outcome_id(str(time.time()), "project_decision", clean[:120]),
                    "event_type": "project_decision",
                    "tool": None,
                    "text": f"project decision: {clean[:200]}",
                    "polarity": "pos",
                    "created_at": time.time(),
                    "domain": "project",
                    "session_id": session_id or None,
                })
        except Exception:
            pass

        return True
    except Exception:
        return False


def process_recent_memory_events(limit: int = 50) -> Dict[str, Any]:
    """Scan recent queue events and generate suggestions / auto-saves.

    Portable rule: we only use data in Spark queue.

    Returns stats for observability.
    """

    st = _state()
    last_ts = float(st.get("last_ts", 0.0))

    events = read_recent_events(limit)

    pending = _load_pending()
    items: List[Dict[str, Any]] = list(pending.get("items", []))
    existing_ids = {i.get("suggestion_id") for i in items}

    auto_saved = 0
    suggested = 0
    explicit_saved = 0

    max_seen_ts = last_ts

    for e in events:
        max_seen_ts = max(max_seen_ts, float(e.timestamp or 0.0))
        if float(e.timestamp or 0.0) <= last_ts:
            continue

        # We only understand SparkEventV1 shaped payloads via sparkd ingest
        payload = (e.data or {}).get("payload") or {}

        # 1) Explicit intent events (best compatibility)
        if e.event_type == EventType.LEARNING and payload.get("intent") == "remember":
            txt = str(payload.get("text") or "").strip()
            if not txt:
                continue
            cat = payload.get("category")
            try:
                category = CognitiveCategory(str(cat)) if cat else infer_category(txt)
            except Exception:
                category = infer_category(txt)

            ok = commit_learning(txt, category, context="explicit remember intent", session_id=e.session_id)
            if ok:
                explicit_saved += 1
            continue

        # 2) Keyword/heuristic from user messages
        if e.event_type != EventType.USER_PROMPT:
            continue

        role = str(payload.get("role") or "user")
        if role != "user":
            continue

        txt = str(payload.get("text") or "").strip()
        if not txt:
            continue
        if len(txt) > MAX_CAPTURE_CHARS:
            txt = txt[:MAX_CAPTURE_CHARS].rstrip()

        score, breakdown = importance_score(txt)
        if score < SUGGEST_THRESHOLD:
            continue

        # Dedupe: avoid storing the same preference repeatedly (even across sessions)
        norm_txt = normalize_memory_text(txt)
        if not norm_txt:
            continue

        suggestion_id = _make_id(e.session_id, norm_txt)
        if suggestion_id in existing_ids:
            continue

        category = infer_category(norm_txt)

        sug = MemorySuggestion(
            suggestion_id=suggestion_id,
            created_at=time.time(),
            session_id=e.session_id,
            text=norm_txt,
            category=category.value,
            score=score,
            breakdown=breakdown,
        )

        if score >= AUTO_SAVE_THRESHOLD:
            if commit_learning(norm_txt, category, context="auto-captured from conversation", session_id=e.session_id):
                sug.status = "auto_saved"
                auto_saved += 1
            else:
                sug.status = "pending"
                suggested += 1
        else:
            suggested += 1

        items.append(sug.to_dict())
        existing_ids.add(suggestion_id)

    # keep file small
    items = sorted(items, key=lambda x: x.get("created_at", 0), reverse=True)[:200]
    pending["items"] = items
    _save_pending(pending)

    st["last_ts"] = max_seen_ts
    _save_state(st)

    return {
        "auto_saved": auto_saved,
        "explicit_saved": explicit_saved,
        "suggested": suggested,
        "pending_total": sum(1 for i in items if i.get("status") == "pending"),
    }


def list_pending(limit: int = 20) -> List[Dict[str, Any]]:
    d = _load_pending()
    items = [i for i in d.get("items", []) if i.get("status") == "pending"]
    items.sort(key=lambda x: x.get("created_at", 0), reverse=True)
    return items[:limit]


def accept_suggestion(suggestion_id: str) -> bool:
    d = _load_pending()
    items = d.get("items", [])
    changed = False
    for it in items:
        if it.get("suggestion_id") == suggestion_id and it.get("status") == "pending":
            txt = it.get("text") or ""
            cat = it.get("category") or "meta_learning"
            try:
                category = CognitiveCategory(str(cat))
            except Exception:
                category = infer_category(txt)
            if commit_learning(str(txt), category, context="accepted memory suggestion"):
                it["status"] = "accepted"
                changed = True
    if changed:
        _save_pending(d)
    return changed


def reject_suggestion(suggestion_id: str) -> bool:
    d = _load_pending()
    items = d.get("items", [])
    changed = False
    for it in items:
        if it.get("suggestion_id") == suggestion_id and it.get("status") == "pending":
            it["status"] = "rejected"
            changed = True
    if changed:
        _save_pending(d)
    return changed
