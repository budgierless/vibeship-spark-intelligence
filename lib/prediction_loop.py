"""Prediction -> outcome validation loop (semantic + lightweight).

Uses:
- Exposures (what was surfaced)
- Outcomes (user approvals/corrections, tool failures)
- Embeddings (optional) for semantic matching
"""

from __future__ import annotations

import hashlib
import json
import os
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from lib.queue import read_events, count_events, EventType, _tail_lines
from lib.cognitive_learner import get_cognitive_learner, _boost_confidence
from lib.aha_tracker import get_aha_tracker, SurpriseType
from lib.diagnostics import log_debug
from lib.exposure_tracker import read_recent_exposures
from lib.embeddings import embed_texts
from lib.outcome_log import OUTCOMES_FILE, append_outcomes, make_outcome_id
from lib.project_profile import list_profiles
from lib.primitive_filter import is_primitive_text


PREDICTIONS_FILE = Path.home() / ".spark" / "predictions.jsonl"
STATE_FILE = Path.home() / ".spark" / "prediction_state.json"

DEFAULT_SOURCE_BUDGETS = {
    "chip_merge": 80,
    "spark_inject": 60,
    "sync_context": 40,
}
DEFAULT_SOURCE_BUDGET = 30
DEFAULT_TOTAL_PREDICTION_BUDGET = 180


POSITIVE_OUTCOME = {
    "looks good", "ship it", "ship", "perfect", "great", "awesome", "thanks",
    "approved", "good", "works", "nice", "love it", "exactly",
}
NEGATIVE_OUTCOME = {
    "no", "wrong", "redo", "change", "fix", "not", "doesnt", "doesn't", "broken",
    "still", "bad", "failed", "issue", "bug",
}


def _load_state() -> Dict:
    if not STATE_FILE.exists():
        return {"offset": 0, "matched_ids": []}
    try:
        return json.loads(STATE_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {"offset": 0, "matched_ids": []}


def _save_state(state: Dict) -> None:
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(state, indent=2), encoding="utf-8")


def _hash_id(*parts: str) -> str:
    raw = "|".join(p or "" for p in parts).encode("utf-8")
    return hashlib.sha1(raw).hexdigest()[:12]


def _normalize(text: str) -> str:
    return (text or "").lower().strip()


def _expected_polarity(insight_text: str) -> str:
    t = _normalize(insight_text)
    if any(w in t for w in ("struggle", "fails", "error", "timeout", "broken")):
        return "neg"
    return "pos"


def _prediction_type(category: str, insight_text: str) -> str:
    t = _normalize(insight_text)
    if any(w in t for w in ("struggle", "fails", "error", "timeout")):
        return "failure_pattern"
    if "sequence" in t or "pattern" in t:
        return "workflow"
    if category in ("communication", "user_understanding"):
        return "preference"
    if category in ("wisdom", "reasoning", "meta_learning"):
        return "principle"
    return "general"


def _load_prediction_budget_config() -> Tuple[int, int, Dict[str, int]]:
    total_budget = DEFAULT_TOTAL_PREDICTION_BUDGET
    default_source_budget = DEFAULT_SOURCE_BUDGET
    source_budgets = dict(DEFAULT_SOURCE_BUDGETS)

    raw_total = os.environ.get("SPARK_PREDICTION_TOTAL_BUDGET")
    if raw_total:
        try:
            total_budget = max(20, min(2000, int(raw_total)))
        except Exception:
            pass

    raw_default = os.environ.get("SPARK_PREDICTION_DEFAULT_SOURCE_BUDGET")
    if raw_default:
        try:
            default_source_budget = max(1, min(2000, int(raw_default)))
        except Exception:
            pass

    raw = os.environ.get("SPARK_PREDICTION_SOURCE_BUDGETS", "").strip()
    if not raw:
        return total_budget, default_source_budget, source_budgets

    for part in raw.split(","):
        token = part.strip()
        if not token or "=" not in token:
            continue
        source, raw_value = token.split("=", 1)
        source = source.strip()
        if not source:
            continue
        try:
            value = int(raw_value.strip())
            if value <= 0:
                continue
            source_budgets[source] = min(value, 2000)
        except Exception:
            continue
    return total_budget, default_source_budget, source_budgets


def _load_jsonl(path: Path, limit: int = 300) -> List[Dict]:
    """Load last N lines from JSONL file using memory-efficient tail read."""
    if not path.exists():
        return []

    # Use tail read to avoid loading entire file into memory
    lines = _tail_lines(path, limit)
    if not lines:
        return []

    out: List[Dict] = []
    for line in reversed(lines):
        try:
            out.append(json.loads(line))
        except Exception:
            continue
    return out


def _append_jsonl(path: Path, rows: List[Dict]) -> None:
    if not rows:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def build_predictions(max_age_s: float = 6 * 3600) -> int:
    """Generate predictions for recently surfaced insights."""
    total_budget, default_source_budget, source_budgets = _load_prediction_budget_config()
    scan_limit = max(200, min(2000, total_budget * 4))
    exposures = read_recent_exposures(limit=scan_limit, max_age_s=max_age_s)
    if not exposures:
        return 0

    existing = {p.get("prediction_id") for p in _load_jsonl(PREDICTIONS_FILE, limit=500)}
    cog = get_cognitive_learner()
    preds: List[Dict] = []
    source_counts: Dict[str, int] = {}
    now = time.time()

    for ex in exposures:
        if len(preds) >= total_budget:
            break
        key = ex.get("insight_key")
        text = ex.get("text") or ""
        category = ex.get("category") or ""
        source = ex.get("source") or "exposure"
        session_id = ex.get("session_id")
        if not text:
            continue
        if is_primitive_text(text):
            continue
        pred_id = _hash_id(key or "", text, source)
        if pred_id in existing:
            continue
        source_cap = int(source_budgets.get(source, default_source_budget))
        if source_counts.get(source, 0) >= source_cap:
            continue

        pred = {
            "prediction_id": pred_id,
            "insight_key": key,
            "category": category,
            "type": _prediction_type(category, text),
            "text": text,
            "expected_polarity": _expected_polarity(text),
            "created_at": now,
            "expires_at": now + max_age_s,
            "source": source,
            "session_id": session_id,
        }
        trace_id = ex.get("trace_id")
        if trace_id:
            pred["trace_id"] = trace_id
        preds.append(pred)
        source_counts[source] = source_counts.get(source, 0) + 1

    _append_jsonl(PREDICTIONS_FILE, preds)
    return len(preds)


def build_project_predictions(max_age_s: float = 14 * 24 * 3600) -> int:
    """Generate predictions from project profiles (done + milestones)."""
    profiles = list_profiles()
    if not profiles:
        return 0
    existing = {p.get("prediction_id") for p in _load_jsonl(PREDICTIONS_FILE, limit=800)}
    now = time.time()
    preds: List[Dict] = []

    for profile in profiles:
        project_key = profile.get("project_key") or "project"
        domain = profile.get("domain") or "general"
        done_text = profile.get("done") or ""
        if done_text:
            pred_id = _hash_id("project_done", project_key, done_text[:120])
            if pred_id not in existing:
                preds.append({
                    "prediction_id": pred_id,
                    "insight_key": f"project:done:{project_key}",
                    "category": "project_done",
                    "type": "project_done",
                    "text": f"Project done: {done_text}",
                    "expected_polarity": "pos",
                    "created_at": now,
                    "expires_at": now + max_age_s,
                    "source": "project_profile",
                    "project_key": project_key,
                    "domain": domain,
                    "entity_id": _hash_id(project_key, "done"),
                })

        for m in profile.get("milestones") or []:
            text = (m.get("text") or "").strip()
            if not text:
                continue
            status = (m.get("meta") or {}).get("status") or ""
            if str(status).lower() in ("done", "complete", "completed"):
                continue
            entity_id = m.get("entry_id") or _hash_id(project_key, "milestone", text[:120])
            pred_id = _hash_id("project_milestone", project_key, entity_id)
            if pred_id in existing:
                continue
            preds.append({
                "prediction_id": pred_id,
                "insight_key": f"project:milestone:{project_key}:{entity_id}",
                "category": "project_milestone",
                "type": "project_milestone",
                "text": f"Milestone pending: {text}",
                "expected_polarity": "pos",
                "created_at": now,
                "expires_at": now + max_age_s,
                "source": "project_profile",
                "project_key": project_key,
                "domain": domain,
                "entity_id": entity_id,
            })

    _append_jsonl(PREDICTIONS_FILE, preds)
    return len(preds)


def _outcome_polarity(text: str) -> Optional[str]:
    t = _normalize(text)
    if any(w in t for w in POSITIVE_OUTCOME):
        return "pos"
    if any(w in t for w in NEGATIVE_OUTCOME):
        return "neg"
    return None


def collect_outcomes(limit: int = 200) -> Dict[str, int]:
    """Collect outcomes from recent events."""
    state = _load_state()
    offset = int(state.get("offset", 0))

    total = count_events()
    if total < offset:
        offset = max(0, total - limit)

    events = read_events(limit=limit, offset=offset)
    if not events:
        return {"processed": 0, "outcomes": 0}

    rows: List[Dict] = []
    processed = 0
    for ev in events:
        processed += 1
        trace_id = (ev.data or {}).get("trace_id")
        if ev.event_type == EventType.USER_PROMPT:
            payload = (ev.data or {}).get("payload") or {}
            role = payload.get("role") or "user"
            if role != "user":
                continue
            text = str(payload.get("text") or "").strip()
            if not text:
                continue
            polarity = _outcome_polarity(text)
            if not polarity:
                continue
            row = {
                "outcome_id": make_outcome_id(str(ev.timestamp), text[:100]),
                "event_type": "user_prompt",
                "tool": None,
                "text": text,
                "polarity": polarity,
                "created_at": ev.timestamp,
                "session_id": ev.session_id,
            }
            if trace_id:
                row["trace_id"] = trace_id
            rows.append(row)
        elif ev.event_type in (EventType.POST_TOOL_FAILURE,):
            tool = ev.tool_name or ""
            error = ev.error or ""
            if not error:
                payload = (ev.data or {}).get("payload") or {}
                error = payload.get("error") or payload.get("stderr") or payload.get("message") or ""
            if not error:
                continue
            text = f"{tool} error: {str(error)[:200]}"
            row = {
                "outcome_id": make_outcome_id(str(ev.timestamp), tool, "error"),
                "event_type": "tool_error",
                "tool": tool,
                "text": text,
                "polarity": "neg",
                "created_at": ev.timestamp,
                "session_id": ev.session_id,
            }
            if trace_id:
                row["trace_id"] = trace_id
            rows.append(row)

    append_outcomes(rows)
    state["offset"] = offset + len(events)
    _save_state(state)
    return {"processed": processed, "outcomes": len(rows)}


def _token_overlap(a: str, b: str) -> float:
    a_t = set(_normalize(a).split())
    b_t = set(_normalize(b).split())
    if not a_t or not b_t:
        return 0.0
    return len(a_t & b_t) / max(1, len(a_t | b_t))


def _cosine(a: List[float], b: List[float]) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = 0.0
    na = 0.0
    nb = 0.0
    for x, y in zip(a, b):
        dot += x * y
        na += x * x
        nb += y * y
    if na <= 0.0 or nb <= 0.0:
        return 0.0
    return max(0.0, min(1.0, dot / ((na ** 0.5) * (nb ** 0.5))))


def match_predictions(
    *,
    max_age_s: float = 6 * 3600,
    sim_threshold: float = 0.72,
) -> Dict[str, int]:
    """Match predictions to outcomes and update insight reliability."""
    preds = _load_jsonl(PREDICTIONS_FILE, limit=400)
    outcomes = _load_jsonl(OUTCOMES_FILE, limit=400)
    if not preds or not outcomes:
        return {"matched": 0, "validated": 0, "contradicted": 0, "surprises": 0}

    state = _load_state()
    matched_ids = set(state.get("matched_ids") or [])
    now = time.time()

    # Filter to recent predictions/outcomes
    preds = [p for p in preds if (now - float(p.get("created_at") or 0.0)) <= max_age_s]
    outcomes = [o for o in outcomes if (now - float(o.get("created_at") or 0.0)) <= max_age_s]

    pred_texts = [p.get("text") or "" for p in preds]
    outcome_texts = [o.get("text") or "" for o in outcomes]
    pred_vecs = embed_texts(pred_texts) or []
    out_vecs = embed_texts(outcome_texts) or []

    def similarity(i: int, j: int) -> float:
        if pred_vecs and out_vecs:
            return _cosine(pred_vecs[i], out_vecs[j])
        return _token_overlap(pred_texts[i], outcome_texts[j])

    cog = get_cognitive_learner()
    stats = {"matched": 0, "validated": 0, "contradicted": 0, "surprises": 0}

    for i, pred in enumerate(preds):
        pred_id = pred.get("prediction_id")
        if not pred_id or pred_id in matched_ids:
            continue
        expires = float(pred.get("expires_at") or 0.0)
        if expires and now > expires:
            continue
        pred_pol = pred.get("expected_polarity")
        pred_type = pred.get("type") or "general"
        insight_key = pred.get("insight_key")
        insight = cog.insights.get(insight_key) if insight_key else None

        best = None
        best_sim = 0.0
        linked_hits = []
        if insight_key:
            for outcome in outcomes:
                links = outcome.get("linked_insights") or []
                if isinstance(links, list) and insight_key in links:
                    linked_hits.append(outcome)
        # Hard link by entity_id (project milestones/done)
        entity_id = pred.get("entity_id")
        if entity_id:
            for outcome in outcomes:
                if outcome.get("entity_id") == entity_id:
                    linked_hits.append(outcome)
        if linked_hits:
            linked_hits.sort(key=lambda o: float(o.get("created_at") or 0.0), reverse=True)
            best = linked_hits[0]
            best_sim = 1.0

        pred_sid = pred.get("session_id")
        cand_indices = list(range(len(outcomes)))
        if pred_sid:
            same = [idx for idx, o in enumerate(outcomes) if o.get("session_id") == pred_sid]
            if same:
                cand_indices = same

        for j in cand_indices:
            outcome = outcomes[j]
            if best is not None:
                break
            if outcome.get("created_at") and pred.get("created_at"):
                if float(outcome["created_at"]) < float(pred["created_at"]):
                    continue
            sim = similarity(i, j)
            if sim > best_sim:
                best_sim = sim
                best = outcome

        if not best or best_sim < sim_threshold:
            continue

        stats["matched"] += 1
        matched_ids.add(pred_id)

        out_pol = best.get("polarity")
        if out_pol not in ("pos", "neg"):
            continue
        if pred_type == "failure_pattern":
            validated = True
        else:
            validated = (pred_pol == out_pol)

        if validated:
            stats["validated"] += 1
        else:
            stats["contradicted"] += 1

        if not insight:
            continue

        if validated:
            cog._touch_validation(insight, validated_delta=1)
            insight.confidence = _boost_confidence(insight.confidence, 1)
            insight.evidence.append(best.get("text", "")[:200])
            insight.evidence = insight.evidence[-10:]
        else:
            cog._touch_validation(insight, contradicted_delta=1)
            insight.counter_examples.append(best.get("text", "")[:200])
            insight.counter_examples = insight.counter_examples[-10:]

            if insight.reliability >= 0.7 and insight.times_validated >= 2:
                try:
                    tracker = get_aha_tracker()
                    tracker.capture_surprise(
                        surprise_type=SurpriseType.UNEXPECTED_FAILURE,
                        predicted=f"Expected: {insight.insight}",
                        actual=f"Outcome: {best.get('text', '')[:120]}",
                        confidence_gap=min(1.0, insight.reliability),
                        context={"tool": "prediction", "insight": insight.insight},
                        lesson=f"Prediction contradicted: {insight.insight[:60]}",
                    )
                    stats["surprises"] += 1
                except Exception as e:
                    log_debug("prediction", "surprise capture failed", e)

    if stats["validated"] or stats["contradicted"]:
        cog._save_insights()

    state["matched_ids"] = list(matched_ids)[-500:]
    state["last_run_ts"] = time.time()
    state["last_stats"] = stats
    _save_state(state)
    return stats


def process_prediction_cycle(limit: int = 200) -> Dict[str, int]:
    """Full prediction cycle: build -> outcomes -> match."""
    stats = {"predictions": 0, "outcomes": 0, "matched": 0, "validated": 0, "contradicted": 0, "surprises": 0}
    try:
        stats["predictions"] = build_predictions()
    except Exception as e:
        log_debug("prediction", "build_predictions failed", e)
    try:
        stats["predictions"] += build_project_predictions()
    except Exception as e:
        log_debug("prediction", "build_project_predictions failed", e)
    try:
        outcome_stats = collect_outcomes(limit=limit)
        stats["outcomes"] = outcome_stats.get("outcomes", 0)
    except Exception as e:
        log_debug("prediction", "collect_outcomes failed", e)
    try:
        match_stats = match_predictions()
        stats.update({k: match_stats.get(k, 0) for k in ("matched", "validated", "contradicted", "surprises")})
    except Exception as e:
        log_debug("prediction", "match_predictions failed", e)
    return stats


def get_prediction_state() -> Dict:
    state = _load_state()
    return {
        "last_run_ts": state.get("last_run_ts"),
        "last_stats": state.get("last_stats") or {},
        "offset": state.get("offset", 0),
        "matched_count": len(state.get("matched_ids") or []),
    }
