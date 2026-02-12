#!/usr/bin/env python3
"""Realism benchmark for advisory quality across depth and cross-system scenarios.

Builds on advisory_quality_ab by adding:
- depth-tier performance splits (D1/D2/D3)
- domain and cross-system splits
- theory discrimination (good advice promoted, bad advice suppressed)
- source-alignment checks (expected memory source actually used)
- readiness gates for production fine-tuning
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List, Sequence

BENCH_DIR = Path(__file__).resolve().parent
if str(BENCH_DIR) not in sys.path:
    sys.path.insert(0, str(BENCH_DIR))

import advisory_quality_ab as aq


@dataclass
class CaseMeta:
    case_id: str
    depth_tier: str
    domain: str
    systems: List[str]
    importance: str
    theory_quality: str
    expected_sources: List[str]
    forbidden_sources: List[str]


REALISM_GATES: Dict[str, float] = {
    "high_value_rate_min": 0.55,
    "harmful_emit_rate_max": 0.10,
    "critical_miss_rate_max": 0.10,
    "source_alignment_rate_min": 0.55,
    "theory_discrimination_rate_min": 0.70,
    "trace_bound_rate_min": 0.85,
}


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except Exception:
        return float(default)


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except Exception:
        return int(default)


def _clamp01(value: float) -> float:
    return max(0.0, min(1.0, float(value)))


def _as_list(value: Any) -> List[str]:
    if not isinstance(value, list):
        return []
    out: List[str] = []
    for item in value:
        text = str(item or "").strip().lower()
        if text:
            out.append(text)
    return out


def _normalize_depth(value: Any) -> str:
    text = str(value or "").strip().upper()
    if text in {"D1", "D2", "D3"}:
        return text
    if text in {"1", "2", "3"}:
        return f"D{text}"
    return "D1"


def _normalize_importance(value: Any) -> str:
    text = str(value or "").strip().lower()
    if text in {"low", "medium", "high", "critical"}:
        return text
    return "medium"


def _normalize_theory_quality(value: Any) -> str:
    text = str(value or "").strip().lower()
    if text in {"good", "bad", "neutral"}:
        return text
    return "neutral"


def load_case_meta(path: Path) -> Dict[str, CaseMeta]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    rows = raw.get("cases", []) if isinstance(raw, dict) else raw
    if not isinstance(rows, list):
        raise ValueError("cases file must contain a list or object with 'cases' list")

    meta: Dict[str, CaseMeta] = {}
    for idx, row in enumerate(rows):
        if not isinstance(row, dict):
            continue
        case_id = str(row.get("id") or row.get("case_id") or f"case_{idx + 1}")
        domain = str(row.get("domain") or "general").strip().lower() or "general"
        systems = _as_list(row.get("systems"))
        if not systems:
            systems = ["advisory"]
        meta[case_id] = CaseMeta(
            case_id=case_id,
            depth_tier=_normalize_depth(row.get("depth_tier") or row.get("depth") or "D1"),
            domain=domain,
            systems=systems,
            importance=_normalize_importance(row.get("importance")),
            theory_quality=_normalize_theory_quality(row.get("theory_quality")),
            expected_sources=_as_list(row.get("expected_sources")),
            forbidden_sources=_as_list(row.get("forbidden_sources")),
        )
    return meta


def _source_alignment(meta: CaseMeta, source_counts: Dict[str, Any]) -> float:
    counts: Dict[str, int] = {}
    for key, value in dict(source_counts or {}).items():
        counts[str(key or "").strip().lower()] = max(0, _safe_int(value, 0))

    expected = list(meta.expected_sources)
    forbidden = list(meta.forbidden_sources)

    if not expected and not forbidden:
        return 1.0

    expected_hits = 0
    for src in expected:
        if counts.get(src, 0) > 0:
            expected_hits += 1

    forbidden_hits = 0
    for src in forbidden:
        if counts.get(src, 0) > 0:
            forbidden_hits += 1

    expected_rate = expected_hits / max(1, len(expected)) if expected else 1.0
    forbidden_rate = forbidden_hits / max(1, len(forbidden)) if forbidden else 0.0
    return _clamp01(expected_rate - (0.5 * forbidden_rate))


def _avg(values: Iterable[float]) -> float:
    vals = [float(v) for v in values]
    if not vals:
        return 0.0
    return float(sum(vals) / max(1, len(vals)))


def _objective_from_metrics(base_score: float, realism: Dict[str, Any]) -> float:
    high_value = _safe_float(realism.get("high_value_rate"), 0.0)
    harmful = _safe_float(realism.get("harmful_emit_rate"), 1.0)
    critical_miss = _safe_float(realism.get("critical_miss_rate"), 1.0)
    source_align = _safe_float(realism.get("source_alignment_rate"), 0.0)
    theory_disc = _safe_float(realism.get("theory_discrimination_rate"), 0.0)
    trace_rate = _safe_float(realism.get("trace_bound_rate"), 0.0)

    objective = (
        0.32 * _clamp01(base_score)
        + 0.22 * _clamp01(high_value)
        + 0.16 * _clamp01(source_align)
        + 0.15 * _clamp01(theory_disc)
        + 0.07 * _clamp01(1.0 - harmful)
        + 0.04 * _clamp01(1.0 - critical_miss)
        + 0.04 * _clamp01(trace_rate)
    )
    return round(_clamp01(objective), 4)


def summarize_realism(profile_run: Dict[str, Any], meta_by_case: Dict[str, CaseMeta]) -> Dict[str, Any]:
    rows = profile_run.get("cases") or []
    base_summary = profile_run.get("summary") or {}

    depth_scores: Dict[str, List[float]] = {"D1": [], "D2": [], "D3": []}
    domain_scores: Dict[str, List[float]] = {}
    source_alignment_scores: List[float] = []

    cross_system_total = 0
    cross_system_good = 0
    high_value = 0
    harmful_emit = 0
    critical_total = 0
    critical_miss = 0

    theory_good_total = 0
    theory_good_ok = 0
    theory_bad_total = 0
    theory_bad_ok = 0

    source_expect_total: Dict[str, int] = {}
    source_expect_hit: Dict[str, int] = {}

    for row in rows:
        case_id = str(row.get("case_id") or "")
        meta = meta_by_case.get(case_id)
        if not meta:
            meta = CaseMeta(
                case_id=case_id,
                depth_tier="D1",
                domain="general",
                systems=["advisory"],
                importance="medium",
                theory_quality="neutral",
                expected_sources=[],
                forbidden_sources=[],
            )

        should_emit = bool(row.get("should_emit"))
        emitted = bool(row.get("emitted"))
        actionable = bool(row.get("actionable"))
        trace_bound = bool(row.get("trace_bound"))
        memory_utilized = bool(row.get("memory_utilized"))
        expected_hit_rate = _safe_float(row.get("expected_hit_rate"), 0.0)
        forbidden_hit_rate = _safe_float(row.get("forbidden_hit_rate"), 0.0)
        score = _safe_float(row.get("score"), 0.0)
        source_counts = row.get("source_counts") if isinstance(row.get("source_counts"), dict) else {}

        align = _source_alignment(meta, source_counts)
        source_alignment_scores.append(align)

        if meta.expected_sources:
            for src in meta.expected_sources:
                source_expect_total[src] = source_expect_total.get(src, 0) + 1
                if _safe_int(source_counts.get(src), 0) > 0:
                    source_expect_hit[src] = source_expect_hit.get(src, 0) + 1

        depth_scores.setdefault(meta.depth_tier, []).append(score)
        domain_scores.setdefault(meta.domain, []).append(score)

        if len(meta.systems) >= 2:
            cross_system_total += 1
            if emitted and trace_bound and align >= 0.5:
                cross_system_good += 1

        if should_emit and emitted and actionable and trace_bound and memory_utilized and expected_hit_rate >= 0.5 and forbidden_hit_rate <= 0.0 and align >= 0.5:
            high_value += 1

        if (not should_emit) and emitted:
            harmful_emit += 1

        if meta.importance in {"high", "critical"} and should_emit:
            critical_total += 1
            if not emitted:
                critical_miss += 1

        if meta.theory_quality == "good":
            theory_good_total += 1
            if should_emit and emitted and expected_hit_rate >= 0.5 and forbidden_hit_rate <= 0.0:
                theory_good_ok += 1
        elif meta.theory_quality == "bad":
            theory_bad_total += 1
            if should_emit:
                # Bad-theory prompts should emit corrective guidance (not silent pass-through).
                if emitted and expected_hit_rate >= 0.5 and forbidden_hit_rate <= 0.0:
                    theory_bad_ok += 1
            else:
                # Suppression-mode bad theories should stay suppressed.
                if (not emitted) and forbidden_hit_rate <= 0.0:
                    theory_bad_ok += 1

    total = max(1, len(rows))
    theory_total = theory_good_total + theory_bad_total
    theory_correct = theory_good_ok + theory_bad_ok

    depth_score_avg = {k: round(_avg(v), 4) for k, v in depth_scores.items() if v}
    domain_score_avg = {k: round(_avg(v), 4) for k, v in sorted(domain_scores.items())}

    source_recall = {}
    for src in sorted(source_expect_total):
        source_recall[src] = round(source_expect_hit.get(src, 0) / max(1, source_expect_total.get(src, 0)), 4)

    realism = {
        "high_value_rate": round(high_value / total, 4),
        "harmful_emit_rate": round(harmful_emit / total, 4),
        "critical_miss_rate": round(critical_miss / max(1, critical_total), 4),
        "cross_system_success_rate": round(cross_system_good / max(1, cross_system_total), 4),
        "source_alignment_rate": round(_avg(source_alignment_scores), 4),
        "theory_discrimination_rate": round(theory_correct / max(1, theory_total), 4),
        "trace_bound_rate": round(_safe_float(base_summary.get("trace_bound_rate"), 0.0), 4),
        "depth_score_avg": depth_score_avg,
        "domain_score_avg": domain_score_avg,
        "source_recall": source_recall,
        "counts": {
            "cases": len(rows),
            "high_value": high_value,
            "harmful_emit": harmful_emit,
            "critical_total": critical_total,
            "critical_miss": critical_miss,
            "cross_system_total": cross_system_total,
            "cross_system_good": cross_system_good,
            "theory_good_total": theory_good_total,
            "theory_bad_total": theory_bad_total,
        },
    }
    return realism


def evaluate_gates(realism: Dict[str, Any], gates: Dict[str, float]) -> Dict[str, Dict[str, Any]]:
    checks: Dict[str, Dict[str, Any]] = {}
    checks["high_value_rate"] = {
        "value": _safe_float(realism.get("high_value_rate"), 0.0),
        "target": _safe_float(gates.get("high_value_rate_min"), 0.0),
    }
    checks["high_value_rate"]["ok"] = checks["high_value_rate"]["value"] >= checks["high_value_rate"]["target"]

    checks["harmful_emit_rate"] = {
        "value": _safe_float(realism.get("harmful_emit_rate"), 1.0),
        "target": _safe_float(gates.get("harmful_emit_rate_max"), 1.0),
    }
    checks["harmful_emit_rate"]["ok"] = checks["harmful_emit_rate"]["value"] <= checks["harmful_emit_rate"]["target"]

    checks["critical_miss_rate"] = {
        "value": _safe_float(realism.get("critical_miss_rate"), 1.0),
        "target": _safe_float(gates.get("critical_miss_rate_max"), 1.0),
    }
    checks["critical_miss_rate"]["ok"] = checks["critical_miss_rate"]["value"] <= checks["critical_miss_rate"]["target"]

    checks["source_alignment_rate"] = {
        "value": _safe_float(realism.get("source_alignment_rate"), 0.0),
        "target": _safe_float(gates.get("source_alignment_rate_min"), 0.0),
    }
    checks["source_alignment_rate"]["ok"] = checks["source_alignment_rate"]["value"] >= checks["source_alignment_rate"]["target"]

    checks["theory_discrimination_rate"] = {
        "value": _safe_float(realism.get("theory_discrimination_rate"), 0.0),
        "target": _safe_float(gates.get("theory_discrimination_rate_min"), 0.0),
    }
    checks["theory_discrimination_rate"]["ok"] = checks["theory_discrimination_rate"]["value"] >= checks["theory_discrimination_rate"]["target"]

    checks["trace_bound_rate"] = {
        "value": _safe_float(realism.get("trace_bound_rate"), 0.0),
        "target": _safe_float(gates.get("trace_bound_rate_min"), 0.0),
    }
    checks["trace_bound_rate"]["ok"] = checks["trace_bound_rate"]["value"] >= checks["trace_bound_rate"]["target"]

    return checks


def _report_markdown(report: Dict[str, Any]) -> str:
    lines: List[str] = []
    lines.append(f"# Advisory Realism Benchmark Report ({report.get('generated_at', '')})")
    lines.append("")
    lines.append(f"- Cases: `{report.get('case_count', 0)}`")
    lines.append(f"- Repeats: `{report.get('repeats', 1)}`")
    lines.append(f"- Force live path: `{report.get('force_live', True)}`")
    lines.append("")
    lines.append("## Ranking")
    lines.append("")
    lines.append("| Rank | Profile | Objective | Base Score | High-Value | Harmful Emit | Source Align | Theory Disc |")
    lines.append("|---|---|---:|---:|---:|---:|---:|---:|")

    for idx, run in enumerate(report.get("ranked_profiles", []), start=1):
        summary = run.get("summary") or {}
        realism = run.get("realism") or {}
        lines.append(
            f"| {idx} | `{run.get('profile','')}` | {float(run.get('objective', 0.0)):.4f} | "
            f"{float(summary.get('score', 0.0)):.4f} | "
            f"{float(realism.get('high_value_rate', 0.0)):.2%} | "
            f"{float(realism.get('harmful_emit_rate', 0.0)):.2%} | "
            f"{float(realism.get('source_alignment_rate', 0.0)):.2%} | "
            f"{float(realism.get('theory_discrimination_rate', 0.0)):.2%} |"
        )

    lines.append("")
    winner = report.get("winner") or {}
    lines.append(f"## Winner: `{winner.get('profile', 'n/a')}`")
    lines.append("")
    w_realism = winner.get("realism") or {}
    w_checks = winner.get("gates") or {}
    lines.append(f"- Objective: `{float(winner.get('objective', 0.0)):.4f}`")
    lines.append(f"- High-value advice rate: `{float(w_realism.get('high_value_rate', 0.0)):.2%}`")
    lines.append(f"- Harmful emit rate: `{float(w_realism.get('harmful_emit_rate', 0.0)):.2%}`")
    lines.append(f"- Critical miss rate: `{float(w_realism.get('critical_miss_rate', 0.0)):.2%}`")
    lines.append(f"- Source alignment rate: `{float(w_realism.get('source_alignment_rate', 0.0)):.2%}`")
    lines.append(f"- Theory discrimination: `{float(w_realism.get('theory_discrimination_rate', 0.0)):.2%}`")
    lines.append("")
    lines.append("### Winner Gates")
    lines.append("")
    for name, check in sorted(dict(w_checks).items()):
        state = "PASS" if bool(check.get("ok")) else "FAIL"
        lines.append(
            f"- `{name}`: `{state}` (value={float(check.get('value', 0.0)):.4f}, target={float(check.get('target', 0.0)):.4f})"
        )

    lines.append("")
    lines.append("### Winner Source Recall")
    lines.append("")
    recall = w_realism.get("source_recall") or {}
    if recall:
        for src, rate in sorted(recall.items()):
            lines.append(f"- `{src}`: `{float(rate):.2%}`")
    else:
        lines.append("- none")

    lines.append("")
    lines.append("### Winner Depth Scores")
    lines.append("")
    depth = w_realism.get("depth_score_avg") or {}
    if depth:
        for key in sorted(depth):
            lines.append(f"- `{key}`: `{float(depth[key]):.4f}`")
    else:
        lines.append("- none")

    lines.append("")
    return "\n".join(lines).strip() + "\n"


def run_realism_benchmark(
    *,
    cases_path: Path,
    profiles: Dict[str, Dict[str, Any]],
    profile_names: Sequence[str],
    repeats: int,
    force_live: bool,
    gates: Dict[str, float],
) -> Dict[str, Any]:
    base_report = aq.run_benchmark(
        cases_path=cases_path,
        profiles=profiles,
        profile_names=profile_names,
        repeats=repeats,
        force_live=force_live,
    )
    meta = load_case_meta(cases_path)

    enriched_runs: List[Dict[str, Any]] = []
    for run in base_report.get("profile_runs", []):
        enriched = dict(run)
        summary = enriched.get("summary") or {}
        realism = summarize_realism(enriched, meta)
        objective = _objective_from_metrics(_safe_float(summary.get("score"), 0.0), realism)
        gate_checks = evaluate_gates(realism, gates)
        enriched["realism"] = realism
        enriched["objective"] = objective
        enriched["gates"] = gate_checks
        enriched_runs.append(enriched)

    ranked = sorted(
        enriched_runs,
        key=lambda r: (
            _safe_float(r.get("objective"), 0.0),
            _safe_float((r.get("summary") or {}).get("score"), 0.0),
        ),
        reverse=True,
    )

    return {
        "generated_at": datetime.now(UTC).isoformat(),
        "cases_path": str(cases_path),
        "case_count": int(base_report.get("case_count") or 0),
        "repeats": int(repeats),
        "force_live": bool(force_live),
        "profiles": base_report.get("profiles") or {},
        "gates": dict(gates),
        "profile_runs": enriched_runs,
        "ranked_profiles": ranked,
        "winner": ranked[0] if ranked else {},
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="Realism benchmark for advisory quality")
    ap.add_argument(
        "--cases",
        default=str(Path("benchmarks") / "data" / "advisory_realism_eval_v1.json"),
        help="JSON cases file path",
    )
    ap.add_argument(
        "--profiles",
        default="baseline,balanced,strict",
        help="Comma-separated profile names to evaluate",
    )
    ap.add_argument(
        "--profile-file",
        default="",
        help="Optional JSON file with profile config object (merged over defaults)",
    )
    ap.add_argument("--repeats", type=int, default=1, help="How many times to run each case")
    ap.add_argument("--force-live", action="store_true", help="Bypass packet lookup and force live advisory retrieval")
    ap.add_argument("--out-prefix", default="advisory_realism_bench", help="Output file prefix under benchmarks/out")
    args = ap.parse_args()

    profiles = dict(aq.DEFAULT_PROFILE_PRESETS)
    if args.profile_file:
        pf = Path(args.profile_file)
        loaded = json.loads(pf.read_text(encoding="utf-8"))
        if isinstance(loaded, dict):
            for key, val in loaded.items():
                if isinstance(val, dict):
                    cur = dict(profiles.get(key) or {})
                    for section in ("advisory_engine", "advisory_gate", "advisor"):
                        if isinstance(val.get(section), dict):
                            merged = dict(cur.get(section) or {})
                            merged.update(val.get(section) or {})
                            cur[section] = merged
                    profiles[key] = cur

    names = [n.strip() for n in str(args.profiles or "").split(",") if n.strip()]
    report = run_realism_benchmark(
        cases_path=Path(args.cases),
        profiles=profiles,
        profile_names=names,
        repeats=max(1, int(args.repeats)),
        force_live=bool(args.force_live),
        gates=REALISM_GATES,
    )

    out_dir = Path("benchmarks") / "out"
    out_dir.mkdir(parents=True, exist_ok=True)
    json_path = out_dir / f"{args.out_prefix}_report.json"
    md_path = out_dir / f"{args.out_prefix}_report.md"
    json_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    md_path.write_text(_report_markdown(report), encoding="utf-8")

    winner = report.get("winner") or {}
    print(f"Wrote: {json_path}")
    print(f"Wrote: {md_path}")
    print(
        "Winner="
        f"{winner.get('profile', 'n/a')} "
        f"objective={float(winner.get('objective', 0.0)):.4f} "
        f"base={float((winner.get('summary') or {}).get('score', 0.0)):.4f} "
        f"high_value={float((winner.get('realism') or {}).get('high_value_rate', 0.0)):.2%}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
