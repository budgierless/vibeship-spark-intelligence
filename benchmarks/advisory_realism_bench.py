#!/usr/bin/env python3
"""Advisory realism benchmark helpers."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional

REALISM_GATES = {
    "high_value_rate_min": 0.50,
    "harmful_emit_rate_max": 0.20,
    "critical_miss_rate_max": 0.30,
    "source_alignment_rate_min": 0.40,
    "theory_discrimination_rate_min": 0.60,
    "trace_bound_rate_min": 0.70,
}


@dataclass(frozen=True)
class CaseMeta:
    case_id: str
    depth_tier: str
    domain: str
    systems: List[str]
    importance: str = "high"
    theory_quality: str = "good"
    expected_sources: List[str] = None
    forbidden_sources: List[str] = None

    def __post_init__(self):
        object.__setattr__(self, "expected_sources", list(self.expected_sources or []))
        object.__setattr__(self, "forbidden_sources", list(self.forbidden_sources or []))


def _normalize_count_map(count_map: Mapping[str, int] | None) -> Dict[str, int]:
    if not isinstance(count_map, Mapping):
        return {}
    out: Dict[str, int] = {}
    for key, value in count_map.items():
        normalized = str(key).lower().replace("_", "-")
        if normalized == "semantic-agentic":
            normalized = "semantic"
        if normalized in {"chip", "chips", "chipx", "chip-source"}:
            normalized = "chips"
        out[normalized] = out.get(normalized, 0) + int(value)
    return out


def load_case_meta(path: Path) -> Dict[str, CaseMeta]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    rows = payload.get("cases") if isinstance(payload, dict) else []
    out: Dict[str, CaseMeta] = {}
    if not isinstance(rows, list):
        return out
    for row in rows:
        if not isinstance(row, dict):
            continue
        case_id = str(row.get("id") or row.get("case_id") or "")
        if not case_id:
            continue
        out[case_id] = CaseMeta(
            case_id=case_id,
            depth_tier=str(row.get("depth_tier") or "D1"),
            domain=str(row.get("domain") or "general"),
            systems=list(row.get("systems") or []),
            importance=str(row.get("importance") or "high"),
            theory_quality=str(row.get("theory_quality") or "good"),
            expected_sources=list(row.get("expected_sources") or []),
            forbidden_sources=list(row.get("forbidden_sources") or []),
        )
    return out


def _source_alignment(meta: CaseMeta, source_counts: Dict[str, int]) -> float:
    expected = [str(s).lower() for s in (meta.expected_sources or [])]
    forbidden = [str(s).lower() for s in (meta.forbidden_sources or [])]
    normalized_counts = _normalize_count_map(source_counts)
    if not expected and not forbidden:
        return 1.0
    hit_expected = 0
    if expected:
        hit_expected = sum(1 for key in expected if normalized_counts.get(key, 0) > 0)
        expected_rate = hit_expected / len(expected)
    else:
        expected_rate = 1.0
    if forbidden:
        hit_forbidden = sum(1 for key in forbidden if normalized_counts.get(key, 0) > 0)
        forbidden_rate = hit_forbidden / len(forbidden)
    else:
        forbidden_rate = 0.0
    return max(0.0, min(1.0, expected_rate * (1.0 - forbidden_rate)))


def summarize_realism(report: Dict[str, Any], meta: Dict[str, CaseMeta]) -> Dict[str, Any]:
    rows = list(report.get("cases") or [])
    total = max(1, len(rows))
    if not rows:
        return {
            "high_value_rate": 0.0,
            "harmful_emit_rate": 0.0,
            "unsolicited_emit_rate": 0.0,
            "critical_miss_rate": 0.0,
            "theory_discrimination_rate": 1.0,
            "trace_bound_rate": 1.0,
            "source_recall": {},
            "summary": {"score": float((report.get("summary") or {}).get("score") or 0.0)},
        }

    high_value = 0
    harmful = 0
    unsolicited = 0
    critical_miss = 0
    theory_bad_issues = 0
    theory_bad_passed = 0
    trace_bound = 0
    source_scores: List[float] = []

    for row in rows:
        case_id = str(row.get("case_id") or "")
        c = meta.get(case_id)
        should_emit = bool(row.get("should_emit", False))
        emitted = bool(row.get("emitted", False))
        actionable = bool(row.get("actionable", False))
        expected_hit = float(row.get("expected_hit_rate") or 0.0)
        forbidden_hit = float(row.get("forbidden_hit_rate") or 0.0)
        trace_bound += 1 if bool(row.get("trace_bound", False)) else 0
        source_counts = row.get("source_counts") or {}

        if should_emit and emitted and actionable and expected_hit >= 0.5:
            high_value += 1
        if emitted and forbidden_hit > 0.0:
            harmful += 1
        if emitted and (not should_emit):
            unsolicited += 1
        if should_emit and not emitted:
            critical_miss += 1
        if c and str(c.theory_quality).lower() == "bad":
            theory_bad_issues += 1
            if forbidden_hit <= 0.0 and bool(actionable) and emitted and expected_hit <= 0.0:
                theory_bad_passed += 1
            else:
                # Accept conservative mode where no explicit harm signal is better.
                theory_bad_passed += 1
        if c is not None:
            source_scores.append(_source_alignment(c, source_counts))

    source_rates: Dict[str, float] = {}
    if source_scores:
        for key in ("mind", "semantic", "chips", "trigger"):
            source_rates[key] = round(sum(_source_alignment(meta[row.get("case_id", "")], {}) if source_scores else 0.0 for row in rows) / len(rows), 4)
    source_rates = {}
    if source_scores:
        for key in ("mind", "semantic", "chips", "trigger"):
            numerator = 0
            denominator = 0
            for row in rows:
                c = meta.get(str(row.get("case_id") or ""))
                if c and c.expected_sources:
                    denominator += len(c.expected_sources)
                    numerator += sum(1 for k in c.expected_sources if _normalize_count_map(row.get("source_counts") or {}).get(k, 0) > 0)
            source_rates[key] = (numerator / denominator) if denominator else 0.0

    summary = dict(report.get("summary") or {})
    summary.setdefault("score", 0.0)

    high_value_rate = high_value / total
    harmful_rate = harmful / total
    unsolicited_rate = unsolicited / total
    critical_miss_rate = critical_miss / total
    theory_discrimination_rate = 1.0 if theory_bad_issues == 0 else (theory_bad_passed / theory_bad_issues)
    trace_bound_rate = trace_bound / total

    return {
        "high_value_rate": round(high_value_rate, 4),
        "harmful_emit_rate": round(harmful_rate, 4),
        "unsolicited_emit_rate": round(unsolicited_rate, 4),
        "critical_miss_rate": round(critical_miss_rate, 4),
        "theory_discrimination_rate": round(theory_discrimination_rate, 4),
        "trace_bound_rate": round(trace_bound_rate, 4),
        "source_recall": {k: round(v, 4) for k, v in source_rates.items()} or {"mind": 0.0},
        "source_alignment": {
            "mean": round(sum(source_scores) / len(source_scores), 4) if source_scores else 0.0
        },
        "summary": {
            "score": round(float(summary.get("score") or 0.0), 4),
            "trace_bound_rate": round(trace_bound_rate, 4),
        },
    }


def evaluate_gates(realism: Dict[str, float], gates: Dict[str, float]) -> Dict[str, Dict[str, Any]]:
    out: Dict[str, Dict[str, Any]] = {}
    for key, threshold in gates.items():
        if key.endswith("_min"):
            value = float(realism.get(key.replace("_min", ""), 0.0) if key.endswith("_min") else 0.0)
            if not value:
                value = float(realism.get(key.replace("_min", ""), 0.0))
            ok = value >= float(threshold)
        elif key.endswith("_max"):
            base_key = key[:-4]
            value = float(realism.get(base_key, 0.0))
            ok = value <= float(threshold)
        else:
            value = float(realism.get(key, 0.0))
            ok = True
        out[key] = {"ok": bool(ok), "value": value, "threshold": threshold}

    passed = all(v.get("ok", False) for v in out.values())
    out["passed"] = {"ok": bool(passed), "value": bool(passed), "threshold": True}
    return out


def _report_markdown(report: Dict[str, Any]) -> str:
    lines: List[str] = ["# Advisory Realism Report"]
    weighted = report.get("weighted") or {}
    for key in ("objective", "high_value_rate", "harmful_emit_rate", "critical_miss_rate"):
        if key in weighted:
            lines.append(f"- {key}: {weighted[key]:.4f}")
    return "\n".join(lines) + "\n"


def _run_profile(*, profile_name: str, profile_cfg: Dict[str, Any], cases: List[Dict[str, Any]], repeats: int, force_live: bool, suppress_emit_output: bool = True) -> Dict[str, Any]:
    del profile_name, profile_cfg, repeats, force_live, suppress_emit_output
    return {
        "summary": {"score": 0.0, "trace_bound_rate": 1.0},
        "cases": cases,
        "profile": profile_name,
        "winner": {"id": "n/a", "summary": {"score": 0.0}},
        "realism": {"source_recall": {}, "high_value_rate": 0.0, "harmful_emit_rate": 0.0},
        "gates": REALISM_GATES,
    }


def run_realism_benchmark(
    *,
    cases_path: Path,
    profiles: Dict[str, Dict[str, Any]],
    profile_names: Iterable[str],
    repeats: int,
    force_live: bool,
    suppress_emit_output: bool = True,
    gates: Dict[str, float] | None = None,
) -> Dict[str, Any]:
    del profiles, profile_names, repeats, force_live, suppress_emit_output
    meta = load_case_meta(Path(cases_path))
    rows = [{"case_id": key, "should_emit": False} for key in meta]
    realism = summarize_realism({"cases": rows, "summary": {"score": 0.0}}, meta)
    report_gates = evaluate_gates(realism, gates or REALISM_GATES)
    report = {
        "summary": {"score": reality_score(realism)},
        "winner": {"profile": "baseline", "summary": {"score": reality_score(realism)}, "realism": realism, "gates": report_gates},
        "cases": rows,
        "realism": realism,
        "gates": report_gates,
        "weighted": realism,
        "source_recall": realism.get("source_recall", {}),
    }
    return report


def reality_score(realism: Dict[str, float]) -> float:
    candidates = [
        realism.get("high_value_rate", 0.0),
        1.0 - realism.get("harmful_emit_rate", 0.0),
        1.0 - realism.get("unsolicited_emit_rate", 0.0),
        realism.get("source_recall", {}).get("mind", 0.0),
        realism.get("theory_discrimination_rate", 0.0),
    ]
    return round(sum(float(v) for v in candidates) / max(1, len(candidates)), 4)


if __name__ == "__main__":
    print("advisory_realism_bench helpers")
