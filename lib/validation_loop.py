"""Lightweight validation loop for user preference + communication insights."""

from __future__ import annotations

import json
import time
import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from lib.queue import read_events, count_events, EventType
from lib.cognitive_learner import get_cognitive_learner, CognitiveCategory, _boost_confidence
from lib.aha_tracker import get_aha_tracker, SurpriseType
from lib.diagnostics import log_debug


STATE_FILE = Path.home() / ".spark" / "validation_state.json"

# Words that do not carry preference meaning for matching.
STOPWORDS = {
    "user", "prefers", "prefer", "likes", "like", "love", "loves", "hates", "hate",
    "dislike", "dislikes", "dont", "don't", "do", "not", "no", "never", "avoid",
    "please", "use", "using", "for", "to", "and", "the", "a", "an", "of", "in", "on",
    "with", "this", "that", "these", "those", "is", "are", "be", "as", "it", "its",
    "when", "about", "need", "want", "should", "must",
}

POS_TRIGGERS = {
    "prefer", "like", "love", "want", "need", "please", "use", "using", "require",
    "should", "must", "explain", "examples", "example", "brief", "short", "detailed",
    "step", "steps", "walk", "show",
}

NEG_TRIGGERS = {
    "no", "not", "never", "avoid", "dont", "stop", "without", "hate", "dislike",
}

NEG_PREF_WORDS = {"hate", "dislike", "don't like", "dont like", "avoid", "never"}
POS_PREF_WORDS = {"prefer", "like", "love", "want", "need"}


def _load_state() -> Dict:
    if not STATE_FILE.exists():
        return {"offset": 0}
    try:
        return json.loads(STATE_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {"offset": 0}


def _save_state(state: Dict) -> None:
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(state, indent=2), encoding="utf-8")


def _normalize_text(text: str) -> str:
    t = (text or "").lower()
    t = t.replace("don't", "dont").replace("do not", "dont")
    t = re.sub(r"[^a-z0-9]+", " ", t)
    return re.sub(r"\s+", " ", t).strip()


def _tokenize(text: str) -> List[str]:
    return _normalize_text(text).split()


def _extract_keywords(text: str, max_terms: int = 3) -> List[str]:
    tokens = _tokenize(text)
    out: List[str] = []
    for tok in tokens:
        if tok in STOPWORDS:
            continue
        if tok not in out:
            out.append(tok)
        if len(out) >= max_terms:
            break
    return out


def _insight_polarity(insight_text: str) -> Optional[str]:
    t = _normalize_text(insight_text)
    if any(p in t for p in POS_PREF_WORDS):
        return "pos"
    if any(p in t for p in NEG_PREF_WORDS):
        return "neg"
    return None


def _prompt_polarity(tokens: List[str], keyword_positions: List[int]) -> Optional[str]:
    if not keyword_positions:
        return None
    has_pos = False
    has_neg = False
    for idx in keyword_positions:
        start = max(0, idx - 3)
        end = min(len(tokens), idx + 4)
        window = tokens[start:end]
        if any(w in NEG_TRIGGERS for w in window):
            has_neg = True
        if any(w in POS_TRIGGERS for w in window):
            has_pos = True

    if has_neg and not has_pos:
        return "neg"
    if has_pos and not has_neg:
        return "pos"
    if has_neg and has_pos:
        return "neg"
    return None


def _match_insight(prompt_tokens: List[str], insight_text: str) -> Tuple[bool, Optional[str]]:
    """Return (matched, polarity) where polarity is 'pos'/'neg'/None."""
    keywords = _extract_keywords(insight_text, max_terms=3)
    if not keywords:
        return False, None

    positions = []
    token_set = set(prompt_tokens)
    for kw in keywords:
        if kw not in token_set:
            continue
        # record the first occurrence position for polarity window checks
        try:
            positions.append(prompt_tokens.index(kw))
        except Exception:
            continue

    if not positions:
        return False, None

    polarity = _prompt_polarity(prompt_tokens, positions)
    return True, polarity


def _apply_validation(
    insight_key: str,
    insight,
    polarity: str,
    prompt_text: str,
    *,
    stats: Dict[str, int],
) -> None:
    cog = get_cognitive_learner()
    insight_polarity = _insight_polarity(insight.insight)

    validated = False
    contradicted = False

    if polarity == "pos":
        if insight_polarity == "neg":
            contradicted = True
        else:
            validated = True
    elif polarity == "neg":
        if insight_polarity == "pos":
            contradicted = True
        else:
            validated = True

    if validated:
        cog._touch_validation(insight, validated_delta=1)
        insight.confidence = _boost_confidence(insight.confidence, 1)
        insight.evidence.append(prompt_text[:200])
        insight.evidence = insight.evidence[-10:]
        stats["validated"] += 1
    elif contradicted:
        cog._touch_validation(insight, contradicted_delta=1)
        insight.counter_examples.append(prompt_text[:200])
        insight.counter_examples = insight.counter_examples[-10:]
        stats["contradicted"] += 1

        # Capture surprise if a previously reliable insight gets contradicted
        if insight.reliability >= 0.7 and insight.times_validated >= 2:
            try:
                tracker = get_aha_tracker()
                tracker.capture_surprise(
                    surprise_type=SurpriseType.UNEXPECTED_FAILURE,
                    predicted=f"Expected: {insight.insight}",
                    actual=f"User said: {prompt_text[:120]}",
                    confidence_gap=min(1.0, insight.reliability),
                    context={"tool": "validation", "insight": insight.insight},
                    lesson=f"Preference may have changed: {insight.insight[:60]}",
                )
                stats["surprises"] += 1
            except Exception as e:
                log_debug("validation", "surprise capture failed", e)

    if validated or contradicted:
        cog.insights[insight_key] = insight


def process_validation_events(limit: int = 200) -> Dict[str, int]:
    """Process queued user prompts and validate preference/communication insights."""
    state = _load_state()
    offset = int(state.get("offset", 0))

    total = count_events()
    if total < offset:
        offset = max(0, total - limit)

    events = read_events(limit=limit, offset=offset)
    if not events:
        return {"processed": 0, "validated": 0, "contradicted": 0, "surprises": 0}

    cog = get_cognitive_learner()
    candidates = {
        k: v
        for k, v in cog.insights.items()
        if v.category in (CognitiveCategory.USER_UNDERSTANDING, CognitiveCategory.COMMUNICATION)
    }

    stats = {"processed": 0, "validated": 0, "contradicted": 0, "surprises": 0}

    for ev in events:
        stats["processed"] += 1
        if ev.event_type != EventType.USER_PROMPT:
            continue

        payload = (ev.data or {}).get("payload") or {}
        role = payload.get("role") or "user"
        if role != "user":
            continue

        text = str(payload.get("text") or "").strip()
        if not text:
            continue

        tokens = _tokenize(text)
        if not tokens:
            continue

        # Only scan when there's a hint of preference language.
        token_set = set(tokens)
        if not (token_set & POS_TRIGGERS or token_set & NEG_TRIGGERS):
            continue

        for key, insight in candidates.items():
            matched, polarity = _match_insight(tokens, insight.insight)
            if not matched or not polarity:
                continue
            _apply_validation(key, insight, polarity, text, stats=stats)

    if stats["validated"] or stats["contradicted"]:
        cog._save_insights()

    state["offset"] = offset + len(events)
    state["last_run_ts"] = time.time()
    state["last_stats"] = stats
    _save_state(state)

    return stats


def get_validation_backlog() -> int:
    """Return the count of queued events not yet processed by validation."""
    state = _load_state()
    try:
        offset = int(state.get("offset", 0))
    except Exception:
        offset = 0
    total = count_events()
    if total < offset:
        offset = total
    return max(0, total - offset)


def get_validation_state() -> Dict:
    """Return last validation run stats and timestamp."""
    state = _load_state()
    return {
        "last_run_ts": state.get("last_run_ts"),
        "last_stats": state.get("last_stats") or {},
        "offset": state.get("offset", 0),
    }
