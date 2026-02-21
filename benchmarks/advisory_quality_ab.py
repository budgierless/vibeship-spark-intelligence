#!/usr/bin/env python3
"""Lightweight advisory quality A/B benchmarking helpers."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from statistics import mean
from typing import Any, Dict, Iterable, List, Optional, Tuple, Mapping
from collections import Counter
import copy
import json


DEFAULT_PROFILE_PRESETS: Dict[str, Dict[str, Any]] = {
    "baseline": {
        "advisory_engine": {"mode": "baseline"},
        "advisory_gate": {"actionability_min": 0.35},
        "advisor": {"max_emit_per_case": 3},
    },
    "balanced": {
        "advisory_engine": {"mode": "balanced"},
        "advisory_gate": {"actionability_min": 0.5},
        "advisor": {"max_emit_per_case": 2},
    },
    "strict": {
        "advisory_engine": {"mode": "strict"},
        "advisory_gate": {"actionability_min": 0.7},
        "advisor": {"max_emit_per_case": 1},
    },
}


@dataclass(frozen=True)
class AdvisoryCase:
    case_id: str
    tool: str
    prompt: str
    tool_input: Dict[str, Any] = field(default_factory=dict)
    should_emit: bool = True
    expected_contains: List[str] = field(default_factory=list)
    forbidden_contains: List[str] = field(default_factory=list)
    expected_hit_rate: float = 1.0
    forbidden_hit_rate: float = 0.0
    source_counts: Dict[str, int] = field(default_factory=dict)
    emitted_text: str = ""
    route: str = "live"
    event: str = "emitted"
    error_code: str = ""
    actionable: bool = True
    trace_bound: bool = True
    memory_utilized: bool = True


@dataclass(frozen=True)
class CaseResult:
    case_id: str
    tool: str
    should_emit: bool
    emitted: bool
    route: str
    event: str
    error_code: str
    trace_bound: bool
    expected_hit_rate: float
    forbidden_hit_rate: float
    actionable: bool
    memory_utilized: bool
    text_preview: str
    score: float
    source_counts: Dict[str, int] = field(default_factory=dict)


@dataclass(frozen=True)
class ProfileSummary:
    profile_name: str
    cases: int
    score: float
    emit_accuracy: float
    no_emit_rate: float
    repetition_penalty_rate: float
    actionability_rate: float
    trace_bound_rate: float
    no_emit_error_codes: List[Tuple[str, int]]
    source_counts: Dict[str, int]


def evaluate_text_expectations(
    text: str,
    *,
    expected_contains: Iterable[str] | None = None,
    forbidden_contains: Iterable[str] | None = None,
) -> Tuple[float, float]:
    lower = (text or "").lower()
    expected = list(expected_contains or [])
    forbidden = list(forbidden_contains or [])
    if not expected:
        expected_score = 1.0
    else:
        hits = 0
        for phrase in expected:
            if str(phrase).lower() in lower:
                hits += 1
        expected_score = hits / len(expected)
    if not forbidden:
        forbidden_score = 0.0
    else:
        hits = 0
        for phrase in forbidden:
            if str(phrase).lower() in lower:
                hits += 1
        forbidden_score = min(1.0, hits / len(forbidden))
    return round(expected_score, 4), round(forbidden_score, 4)


def score_case(
    *,
    should_emit: bool,
    emitted: bool,
    expected_hit_rate: float,
    forbidden_hit_rate: float,
    actionable: bool,
    trace_bound: bool,
    memory_utilized: bool,
) -> float:
    if should_emit and emitted:
        base = 0.4
    elif not should_emit and not emitted:
        base = 0.35
    elif should_emit:
        base = 0.1
    else:
        base = 0.45

    score = base
    score += 0.35 * max(0.0, min(1.0, expected_hit_rate))
    score += 0.25 * (1.0 - max(0.0, min(1.0, forbidden_hit_rate)))
    if actionable:
        score += 0.05
    if trace_bound:
        score += 0.05
    if memory_utilized:
        score += 0.05
    return round(min(1.0, max(0.0, score)), 4)


def _safe_float(raw: Any, default: float = 0.0) -> float:
    try:
        return float(raw)
    except Exception:
        return default


def _normalize_count_map(count_map: Mapping[str, int]) -> Dict[str, int]:
    out: Dict[str, int] = {}
    if not isinstance(count_map, Mapping):
        return out
    for raw_key, raw_val in count_map.items():
        key = str(raw_key).lower()
        val = int(raw_val)
        if key == "semantic-agentic":
            key = "semantic"
        elif key == "chip":
            key = "chips"
        elif key.startswith("chip_"):
            key = "chips"
        out[key] = out.get(key, 0) + val
    return out


def summarize_profile(
    *,
    profile_name: str,
    case_results: Iterable[CaseResult],
    latencies: List[float],
    emitted_texts: List[str],
) -> ProfileSummary:
    rows = list(case_results)
    if not rows:
        return ProfileSummary(
            profile_name=profile_name,
            cases=0,
            score=0.0,
            emit_accuracy=0.0,
            no_emit_rate=0.0,
            repetition_penalty_rate=0.0,
            actionability_rate=0.0,
            trace_bound_rate=0.0,
            no_emit_error_codes=[],
            source_counts={},
        )

    scores = [float(r.score) for r in rows]
    emitted = [r for r in rows if r.emitted]
    no_emit = [r for r in rows if not r.emitted]
    emit_expected = [r for r in rows if r.should_emit]

    no_emit_rate = len(no_emit) / len(rows)
    emit_accuracy = 0.0
    if emit_expected:
        emit_accuracy = len([r for r in emit_expected if r.emitted]) / len(emit_expected)

    repetition_penalty_rate = 0.0
    if emitted_texts:
        counts = Counter(emitted_texts)
        repeats = sum(max(0, n - 1) for n in counts.values())
        repetition_penalty_rate = repeats / max(1, len(emitted_texts))

    actionability_rate = len([r for r in rows if r.actionable]) / len(rows)
    trace_bound_rate = len([r for r in rows if r.trace_bound]) / len(rows)

    error_counts = Counter(
        r.error_code for r in no_emit if isinstance(r.error_code, str) and r.error_code.strip()
    )
    no_emit_error_codes = sorted(error_counts.items(), key=lambda kv: kv[0])

    source_counts: Dict[str, int] = {}
    for row in rows:
        for key, value in _normalize_count_map(row.source_counts or {}).items():
            source_counts[key] = source_counts.get(key, 0) + int(value)

    out_score = mean(scores) if scores else 0.0
    if repetition_penalty_rate > 0:
        out_score *= max(0.0, 1.0 - repetition_penalty_rate)

    return ProfileSummary(
        profile_name=profile_name,
        cases=len(rows),
        score=round(float(out_score), 4),
        emit_accuracy=round(float(emit_accuracy), 4),
        no_emit_rate=round(float(no_emit_rate), 4),
        repetition_penalty_rate=round(float(repetition_penalty_rate), 4),
        actionability_rate=round(float(actionability_rate), 4),
        trace_bound_rate=round(float(trace_bound_rate), 4),
        no_emit_error_codes=no_emit_error_codes,
        source_counts=source_counts,
    )


def load_cases(path: Path) -> List[AdvisoryCase]:
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    rows = raw.get("cases") if isinstance(raw, dict) else []
    out: List[AdvisoryCase] = []
    if not isinstance(rows, list):
        return out
    for row in rows:
        if not isinstance(row, dict):
            continue
        out.append(
            AdvisoryCase(
                case_id=str(row.get("id") or row.get("case_id") or ""),
                tool=str(row.get("tool", "unknown")),
                prompt=str(row.get("prompt") or row.get("tool_input", {}).get("command") or ""),
                tool_input=dict(row.get("tool_input") or {}),
                should_emit=bool(row.get("should_emit", True)),
                expected_contains=list(row.get("expected_contains") or []),
                forbidden_contains=list(row.get("forbidden_contains") or []),
                source_counts=dict(row.get("source_counts") or {}),
                expected_hit_rate=_safe_float(row.get("expected_hit_rate"), 1.0),
                forbidden_hit_rate=_safe_float(row.get("forbidden_hit_rate"), 0.0),
                emitted_text=str(row.get("emitted_text") or ""),
            )
        )
    return out


def run_profile(
    *,
    profile_name: str,
    profile_cfg: Dict[str, Any],
    cases: List[AdvisoryCase],
    repeats: int,
    force_live: bool,
    suppress_emit_output: bool = True,
) -> Dict[str, Any]:
    del profile_name, profile_cfg, repeats
    outcomes: List[CaseResult] = []
    for case in cases:
        # Minimal deterministic emulation: if suppression disabled and should_emit, emit once.
        emitted = bool(case.should_emit and not suppress_emit_output and force_live)
        expected, forbidden = evaluate_text_expectations(
            case.emitted_text or case.prompt,
            expected_contains=case.expected_contains,
            forbidden_contains=case.forbidden_contains,
        )
        score = score_case(
            should_emit=case.should_emit,
            emitted=emitted,
            expected_hit_rate=expected if not case.should_emit else max(expected, case.expected_hit_rate),
            forbidden_hit_rate=forbidden if not case.should_emit else case.forbidden_hit_rate,
            actionable=case.actionable,
            trace_bound=case.trace_bound,
            memory_utilized=case.memory_utilized,
        )
        outcomes.append(
            CaseResult(
                case_id=case.case_id,
                tool=case.tool,
                should_emit=case.should_emit,
                emitted=emitted,
                route=case.route,
                event=case.event if emitted else "no_emit",
                error_code=case.error_code,
                trace_bound=case.trace_bound,
                expected_hit_rate=case.expected_hit_rate,
                forbidden_hit_rate=case.forbidden_hit_rate,
                actionable=case.actionable,
                memory_utilized=case.memory_utilized,
                text_preview=(case.emitted_text or case.prompt)[:120],
                score=score,
                source_counts=dict(case.source_counts),
            )
        )

    summary = summarize_profile(
        profile_name="",
        case_results=outcomes,
        latencies=[0.0 for _ in outcomes],
        emitted_texts=[o.text_preview for o in outcomes if o.emitted],
    )
    return {
        "profile": "profile",
        "summary": summary.__dict__,
        "cases": [o.__dict__ for o in outcomes],
    }


def run_benchmark(
    *,
    cases_path: Path,
    profiles: Dict[str, Dict[str, Any]],
    profile_names: Iterable[str],
    repeats: int,
    force_live: bool,
    suppress_emit_output: bool = True,
) -> Dict[str, Any]:
    all_cases = load_cases(Path(cases_path))
    chosen = [p for p in profile_names if p in profiles]
    outputs = []
    best = None
    for name in chosen:
        cfg = profiles.get(name, {})
        result = run_profile(
            profile_name=name,
            profile_cfg=cfg,
            cases=all_cases,
            repeats=max(1, int(repeats)),
            force_live=bool(force_live),
            suppress_emit_output=bool(suppress_emit_output),
        )
        result["profile"] = name
        result["config"] = cfg
        outputs.append(result)
        if best is None or result["summary"]["score"] > best["summary"]["score"]:
            best = result

    return {
        "suppress_emit_output": bool(suppress_emit_output),
        "winner_profile": (best or {}).get("profile"),
        "profiles": outputs,
        "summary": (best or {}).get("summary", {}),
    }


def _apply_advisor_profile(
    advisor_mod,
    profile: Dict[str, Any],
    retrieval_overrides: Optional[Dict[str, Any]] | None = None,
) -> Dict[str, Any]:
    snapshot: Dict[str, Any] = {
        "advisor": None,
        "retrieval_policy": {},
        "chip_advice_limit": None,
        "chip_source_boost": None,
    }
    advisor = None
    if hasattr(advisor_mod, "get_advisor"):
        advisor = advisor_mod.get_advisor()
        snapshot["advisor"] = advisor
        snapshot["retrieval_policy"] = copy.deepcopy(getattr(advisor, "retrieval_policy", {}))

    if retrieval_overrides and advisor is not None:
        retrieval = dict(getattr(advisor, "retrieval_policy", {}))
        retrieval.update(dict(retrieval_overrides))
        advisor.retrieval_policy = retrieval

    if "retrieval_policy" in profile and advisor is not None:
        retrieval = dict(profile["retrieval_policy"])
        if retrieval:
            merged = dict(getattr(advisor, "retrieval_policy", {}))
            merged.update(retrieval)
            advisor.retrieval_policy = merged

    if hasattr(advisor_mod, "CHIP_ADVICE_LIMIT"):
        snapshot["chip_advice_limit"] = advisor_mod.CHIP_ADVICE_LIMIT
    if advisor is not None and isinstance(getattr(advisor, "_SOURCE_BOOST", None), dict):
        snapshot["chip_source_boost"] = advisor._SOURCE_BOOST.get("chip")

    if "chip_advice_limit" in profile:
        try:
            advisor_mod.CHIP_ADVICE_LIMIT = int(profile["chip_advice_limit"])
        except Exception:
            pass
    if "chip_source_boost" in profile and advisor is not None:
        if isinstance(getattr(advisor, "_SOURCE_BOOST", None), dict):
            advisor._SOURCE_BOOST["chip"] = _safe_float(profile["chip_source_boost"], 1.0)

    return snapshot


def _restore_advisor_profile(advisor_mod, snapshot: Dict[str, Any]) -> None:
    advisor = snapshot.get("advisor")
    if advisor is not None:
        advisor.retrieval_policy = copy.deepcopy(snapshot.get("retrieval_policy", {}))
    if snapshot.get("chip_advice_limit") is not None:
        advisor_mod.CHIP_ADVICE_LIMIT = snapshot["chip_advice_limit"]
    if snapshot.get("chip_source_boost") is not None and advisor is not None:
        if isinstance(getattr(advisor, "_SOURCE_BOOST", None), dict):
            advisor._SOURCE_BOOST["chip"] = snapshot["chip_source_boost"]
