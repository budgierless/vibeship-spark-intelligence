#!/usr/bin/env python3
"""Standalone memory retrieval A/B helpers used by unit tests."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Optional


def _safe_float(raw: Any, default: float = 0.0) -> float:
    try:
        return float(raw)
    except Exception:
        return float(default)


def classify_error_kind(text: str) -> str:
    lower = (text or "").lower()
    if "401" in lower or "403" in lower or "token" in lower or "auth" in lower:
        return "auth"
    if "timeout" in lower or "timed out" in lower:
        return "timeout"
    if "policy" in lower or "guardrail" in lower or "forbidden" in lower:
        return "policy"
    if "refused" in lower or "connection" in lower or "transport" in lower:
        return "transport"
    if "error" in lower or "exception" in lower:
        return "unknown"
    return "unknown"


@dataclass(frozen=True)
class EvalCase:
    case_id: str
    query: str
    relevant_insight_keys: List[str] = field(default_factory=list)
    relevant_contains: List[str] = field(default_factory=list)
    notes: str = ""
    domain: str | None = None


@dataclass(frozen=True)
class RetrievedItem:
    insight_key: str
    text: str
    source: str
    semantic_score: float
    fusion_score: float
    score: float
    why: str
    support_score: float = 0.0
    lexical_score: float = 0.0
    reliability_score: float = 0.0
    emotion_score: float = 0.0


@dataclass(frozen=True)
class CaseMetrics:
    hits: int
    label_count: int
    precision_at_k: Optional[float]
    recall_at_k: Optional[float]
    mrr: Optional[float]
    top1_hit: Optional[bool]


def compute_case_metrics(
    case: EvalCase,
    items: Iterable[Any],
    top_k: int,
) -> CaseMetrics:
    labels = list(case.relevant_insight_keys or [])
    label_count = len(labels)
    items_list = list(items)
    if not items_list or not labels or top_k <= 0:
        return CaseMetrics(
            hits=0,
            label_count=label_count,
            precision_at_k=None if not labels else 0.0,
            recall_at_k=None if not labels else 0.0,
            mrr=None if not labels else None,
            top1_hit=None if not labels else False,
        )

    ranked = list(items_list[:top_k])
    ranked_keys = [getattr(r, "insight_key", "") for r in ranked]
    hits = 0
    first_hit = False
    mrr = None

    for idx, key in enumerate(ranked_keys, start=1):
        if key in labels:
            hits += 1
            if mrr is None:
                mrr = 1.0 / idx
            if idx == 1:
                first_hit = True

    precision = hits / max(1, min(top_k, len(ranked)))
    recall = hits / max(1, label_count)
    return CaseMetrics(
        hits=hits,
        label_count=label_count,
        precision_at_k=precision,
        recall_at_k=recall,
        mrr=mrr,
        top1_hit=first_hit,
    )


def _tokenize(value: str) -> List[str]:
    return [p for p in (value or "").lower().replace("-", " ").split() if p]


def hybrid_lexical_scores(query: str, corpus: Iterable[str], bm25_mix: float = 0.8) -> List[float]:
    query_tokens = _tokenize(query)
    query_counts: Dict[str, int] = {}
    for token in query_tokens:
        query_counts[token] = query_counts.get(token, 0) + 1
    output: List[float] = []
    for text in corpus:
        tokens = _tokenize(text)
        score = 0.0
        for token in tokens:
            if token in query_counts:
                score += query_counts[token]
        # tiny normalization keeps scores bounded
        norm = max(1, len(set(query_tokens)))
        output.append(round((score / norm) * float(bm25_mix), 6))
    return output


def _read_signal(item: Any, field: str, default: float = 0.0) -> float:
    return _safe_float(getattr(item, field, default), default=default)


def _resolve_insight_meta(insights: Dict[str, Any], key: str) -> Dict[str, Any]:
    raw = insights.get(key) if isinstance(insights, dict) else None
    if raw is None:
        return {}
    if isinstance(raw, dict):
        return raw
    if hasattr(raw, "__dict__"):
        return dict(raw.__dict__)
    return {}


def runtime_policy_overrides_for_case(case: EvalCase, tool_name: str = "Bash") -> Dict[str, Any]:
    return {
        "candidate_k": 8,
        "lexical_weight": 0.3,
        "intent_coverage_weight": 0.2,
        "support_boost_weight": 0.1,
        "reliability_weight": 0.1,
        "semantic_intent_min": 0.0,
        "runtime_active_domain": "general",
        "runtime_profile_domain": "general",
    }


def resolve_case_knobs(
    *,
    case: EvalCase,
    use_runtime_policy: bool,
    tool_name: str,
    candidate_k: Optional[int],
    lexical_weight: Optional[float],
    intent_coverage_weight: Optional[float],
    support_boost_weight: Optional[float],
    reliability_weight: Optional[float],
    emotion_state_weight: Optional[float] = None,
    semantic_intent_min: Optional[float],
    **extra: Any,
) -> Dict[str, Any]:
    knobs: Dict[str, Any] = {
        "candidate_k": 8,
        "lexical_weight": 0.25,
        "intent_coverage_weight": 0.1,
        "support_boost_weight": 0.2,
        "reliability_weight": 0.1,
        "emotion_state_weight": emotion_state_weight if emotion_state_weight is not None else 0.0,
        "semantic_intent_min": semantic_intent_min if semantic_intent_min is not None else 0.0,
        "runtime_active_domain": "",
        "runtime_profile_domain": "",
    }
    if use_runtime_policy:
        runtime = runtime_policy_overrides_for_case(case=case, tool_name=tool_name)
        for key, value in dict(runtime).items():
            knobs[key] = value

    if candidate_k is not None:
        knobs["candidate_k"] = int(candidate_k)
    if lexical_weight is not None:
        knobs["lexical_weight"] = float(lexical_weight)
    if intent_coverage_weight is not None:
        knobs["intent_coverage_weight"] = float(intent_coverage_weight)
    if support_boost_weight is not None:
        knobs["support_boost_weight"] = float(support_boost_weight)
    if reliability_weight is not None:
        knobs["reliability_weight"] = float(reliability_weight)
    if semantic_intent_min is not None:
        knobs["semantic_intent_min"] = float(semantic_intent_min)
    if emotion_state_weight is not None:
        knobs["emotion_state_weight"] = float(emotion_state_weight)
    for key in ("runtime_active_domain", "runtime_profile_domain"):
        if key in extra:
            knobs[key] = extra[key]
        elif knobs.get(key) is None:
            knobs[key] = ""
    return knobs


def _contains_noise(text: str) -> bool:
    t = (text or "").lower()
    return "webfetch_error" in t or "traceback" in t or "stack overflow" in t


def _emotion_similarity(meta: Dict[str, Any], state: Dict[str, Any]) -> float:
    if not meta or not state:
        return 0.0
    source_emotion = (meta.get("emotion") or {})
    if not isinstance(source_emotion, dict):
        return 0.0
    score = 0.0
    primary = str(source_emotion.get("primary_emotion") or "").lower()
    if primary and state.get("primary_emotion"):
        score += 0.2 if primary == str(state.get("primary_emotion")).lower() else 0.0
    for key in ("strain", "calm"):
        s_val = _safe_float(state.get(key), 0.0)
        i_val = _safe_float(source_emotion.get(key), 0.0)
        if s_val or i_val:
            score += max(0.0, 1.0 - abs(s_val - i_val))
    return score


def retrieve_hybrid(
    *,
    retriever: Any,
    insights: Dict[str, Any],
    query: str,
    top_k: int,
    candidate_k: int,
    lexical_weight: float,
    intent_coverage_weight: float,
    support_boost_weight: float,
    reliability_weight: float,
    semantic_intent_min: float,
    strict_filter: bool,
    agentic: bool,
    emotion_state_weight: float = 0.0,
    emotion_state: Optional[Dict[str, Any]] = None,
    **_extra: Any,
) -> List[RetrievedItem]:
    query = query or ""
    raw = list(retriever.retrieve(query, insights=insights, limit=candidate_k))
    lex_scores = hybrid_lexical_scores(query, [getattr(r, "insight_text", "") for r in raw], bm25_mix=1.0)

    scored: List[RetrievedItem] = []
    for idx, row in enumerate(raw):
        item_key = getattr(row, "insight_key", "")
        text = str(getattr(row, "insight_text", ""))
        raw_row = _resolve_insight_meta(insights, item_key)
        reliability = _safe_float(raw_row.get("reliability", 0.6), 0.6)

        if strict_filter and _contains_noise(text) and reliability < 0.55:
            continue

        semantic = _safe_float(getattr(row, "semantic_sim", getattr(row, "semantic_score", 0.0)))
        if semantic < semantic_intent_min:
            continue
        fusion = _safe_float(getattr(row, "fusion_score", semantic))
        lexical = lex_scores[idx] if idx < len(lex_scores) else 0.0
        intent_cov = 1.0 if any(t in text.lower() for t in _tokenize(query)) else 0.0
        support = _safe_float(getattr(row, "support_score", 0.0))
        emotion = _emotion_similarity(raw_row.get("meta", {}), emotion_state or {})
        score = (
            semantic * 0.35
            + fusion * 0.35
            + lexical * lexical_weight
            + intent_cov * intent_coverage_weight
            + support * support_boost_weight
            + reliability * reliability_weight
            + emotion * emotion_state_weight
        )
        scored.append(
            RetrievedItem(
                insight_key=item_key,
                text=text,
                source=str(getattr(row, "source_type", getattr(row, "source", ""))),
                semantic_score=semantic,
                fusion_score=fusion,
                score=score,
                why=str(getattr(row, "why", "")),
                lexical_score=lexical,
                reliability_score=reliability,
                support_score=support,
                emotion_score=emotion,
            )
        )

    scored.sort(key=lambda row: (row.score, row.semantic_score), reverse=True)
    return scored[:top_k]


def main() -> int:
    raise SystemExit(0)

