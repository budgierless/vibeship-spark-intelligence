#!/usr/bin/env python3
"""Tuneable sweeper for advisory-quality benchmark profiles."""

from __future__ import annotations

import argparse
import itertools
import json
import statistics
import sys
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List, Sequence

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))
BENCH_DIR = Path(__file__).resolve().parent
if str(BENCH_DIR) not in sys.path:
    sys.path.insert(0, str(BENCH_DIR))

import advisory_quality_ab as aq


@dataclass
class SweepWeights:
    score_weight: float = 1.0
    no_emit_penalty: float = 0.25
    repeat_penalty: float = 0.15
    actionability_bonus: float = 0.10
    trace_bonus: float = 0.05


def parse_int_grid(text: str) -> List[int]:
    return [int(x.strip()) for x in str(text or "").split(",") if x.strip()]


def parse_float_grid(text: str) -> List[float]:
    return [float(x.strip()) for x in str(text or "").split(",") if x.strip()]


def build_candidate_profiles(
    *,
    advisory_text_repeat_grid: Sequence[int],
    tool_cooldown_grid: Sequence[int],
    advice_repeat_grid: Sequence[int],
    min_rank_score_grid: Sequence[float],
    max_items_grid: Sequence[int],
    max_emit_per_call: int = 1,
) -> List[Dict[str, Any]]:
    candidates: List[Dict[str, Any]] = []
    idx = 0
    for repeat_s, tool_s, advice_s, min_rank, max_items in itertools.product(
        advisory_text_repeat_grid,
        tool_cooldown_grid,
        advice_repeat_grid,
        min_rank_score_grid,
        max_items_grid,
    ):
        if advice_s < tool_s:
            continue
        idx += 1
        candidates.append(
            {
                "name": f"sweep_{idx:04d}",
                "advisory_engine": {"advisory_text_repeat_cooldown_s": int(repeat_s)},
                "advisory_gate": {
                    "max_emit_per_call": int(max_emit_per_call),
                    "tool_cooldown_s": int(tool_s),
                    "advice_repeat_cooldown_s": int(advice_s),
                },
                "advisor": {
                    "max_items": int(max_items),
                    "max_advice_items": int(max_items),
                    "min_rank_score": float(min_rank),
                },
            }
        )
    return candidates


def _strictness_key(profile: Dict[str, Any]) -> float:
    eng = profile.get("advisory_engine") or {}
    gate = profile.get("advisory_gate") or {}
    adv = profile.get("advisor") or {}
    return (
        float(eng.get("advisory_text_repeat_cooldown_s", 0.0))
        + float(gate.get("tool_cooldown_s", 0.0) * 12.0)
        + float(gate.get("advice_repeat_cooldown_s", 0.0))
        + float(adv.get("min_rank_score", 0.0) * 10000.0)
        - float(adv.get("max_items", 0.0) * 100.0)
    )


def select_candidate_subset(
    candidates: Sequence[Dict[str, Any]],
    max_candidates: int,
) -> List[Dict[str, Any]]:
    if max_candidates <= 0 or len(candidates) <= max_candidates:
        return list(candidates)
    ordered = sorted(candidates, key=_strictness_key)
    out: List[Dict[str, Any]] = []
    # Evenly sample across strictness spectrum.
    step = (len(ordered) - 1) / max(1, max_candidates - 1)
    seen = set()
    for i in range(max_candidates):
        idx = int(round(i * step))
        idx = max(0, min(len(ordered) - 1, idx))
        name = ordered[idx].get("name")
        if name in seen:
            continue
        seen.add(name)
        out.append(ordered[idx])
    return out


def objective_score(summary: Dict[str, Any], weights: SweepWeights) -> float:
    score = float(summary.get("score", 0.0))
    no_emit = float(summary.get("no_emit_rate", 0.0))
    repeat_penalty = float(summary.get("repetition_penalty_rate", 0.0))
    actionability = float(summary.get("actionability_rate", 0.0))
    trace = float(summary.get("trace_bound_rate", 0.0))
    out = (
        (weights.score_weight * score)
        - (weights.no_emit_penalty * no_emit)
        - (weights.repeat_penalty * repeat_penalty)
        + (weights.actionability_bonus * actionability)
        + (weights.trace_bonus * trace)
    )
    return round(float(out), 6)


def sweep_profiles(
    *,
    cases_path: Path,
    repeats: int,
    force_live: bool,
    candidates: Sequence[Dict[str, Any]],
    weights: SweepWeights,
) -> Dict[str, Any]:
    cases = aq.load_cases(cases_path)
    runs: List[Dict[str, Any]] = []

    for candidate in candidates:
        name = str(candidate.get("name") or f"sweep_{len(runs)+1:04d}")
        cfg = {
            "advisory_engine": dict(candidate.get("advisory_engine") or {}),
            "advisory_gate": dict(candidate.get("advisory_gate") or {}),
            "advisor": dict(candidate.get("advisor") or {}),
        }
        run = aq.run_profile(
            profile_name=name,
            profile_cfg=cfg,
            cases=cases,
            repeats=repeats,
            force_live=force_live,
        )
        summary = dict(run.get("summary") or {})
        summary["objective_score"] = objective_score(summary, weights)
        run["summary"] = summary
        runs.append(run)

    ranked = sorted(runs, key=lambda r: float((r.get("summary") or {}).get("objective_score", 0.0)), reverse=True)
    winner = ranked[0] if ranked else {}
    if winner:
        winner_cfg = {
            winner.get("profile", "winner"): {
                "advisory_engine": (winner.get("config") or {}).get("advisory_engine") or {},
                "advisory_gate": (winner.get("config") or {}).get("advisory_gate") or {},
                "advisor": (winner.get("config") or {}).get("advisor") or {},
            }
        }
    else:
        winner_cfg = {}

    objective_values = [float((r.get("summary") or {}).get("objective_score", 0.0)) for r in ranked]
    return {
        "generated_at": datetime.now(UTC).isoformat(),
        "cases_path": str(cases_path),
        "case_count": len(cases),
        "repeats": int(repeats),
        "force_live": bool(force_live),
        "weights": {
            "score_weight": weights.score_weight,
            "no_emit_penalty": weights.no_emit_penalty,
            "repeat_penalty": weights.repeat_penalty,
            "actionability_bonus": weights.actionability_bonus,
            "trace_bonus": weights.trace_bonus,
        },
        "candidate_count": len(candidates),
        "objective_stats": {
            "min": min(objective_values) if objective_values else 0.0,
            "max": max(objective_values) if objective_values else 0.0,
            "mean": statistics.fmean(objective_values) if objective_values else 0.0,
        },
        "ranked_profiles": ranked,
        "winner": winner,
        "winner_profile_file": winner_cfg,
    }


def render_markdown(report: Dict[str, Any]) -> str:
    lines: List[str] = []
    lines.append(f"# Advisory Profile Sweeper Report ({report.get('generated_at','')})")
    lines.append("")
    lines.append(f"- Cases: `{report.get('case_count', 0)}`")
    lines.append(f"- Candidates: `{report.get('candidate_count', 0)}`")
    lines.append(f"- Repeats: `{report.get('repeats', 1)}`")
    lines.append(f"- Force live path: `{report.get('force_live', True)}`")
    lines.append("")
    lines.append("| Rank | Profile | Objective | Score | No-Emit | Repeat Penalty | Actionability | Trace |")
    lines.append("|---|---|---:|---:|---:|---:|---:|---:|")
    for idx, run in enumerate(report.get("ranked_profiles", []), start=1):
        s = run.get("summary") or {}
        lines.append(
            f"| {idx} | `{run.get('profile','')}` | {float(s.get('objective_score',0.0)):.4f} | "
            f"{float(s.get('score',0.0)):.4f} | {float(s.get('no_emit_rate',0.0)):.2%} | "
            f"{float(s.get('repetition_penalty_rate',0.0)):.2%} | {float(s.get('actionability_rate',0.0)):.2%} | "
            f"{float(s.get('trace_bound_rate',0.0)):.2%} |"
        )
    lines.append("")
    winner = report.get("winner") or {}
    if winner:
        lines.append(f"## Winner: `{winner.get('profile','n/a')}`")
        lines.append("")
        summary = winner.get("summary") or {}
        lines.append(f"- Objective: `{float(summary.get('objective_score', 0.0)):.4f}`")
        lines.append(f"- Score: `{float(summary.get('score', 0.0)):.4f}`")
        lines.append(f"- No-emit: `{float(summary.get('no_emit_rate', 0.0)):.2%}`")
        no_emit_codes = summary.get("no_emit_error_codes") or []
        if no_emit_codes:
            lines.append(f"- Top no-emit reasons: `{', '.join([f'{c}:{n}' for c, n in no_emit_codes])}`")
    return "\n".join(lines).strip() + "\n"


def main() -> int:
    ap = argparse.ArgumentParser(description="Advisory tuneable profile sweeper")
    ap.add_argument(
        "--cases",
        default=str(Path("benchmarks") / "data" / "advisory_quality_eval_seed.json"),
        help="Benchmark cases JSON",
    )
    ap.add_argument("--repeats", type=int, default=1, help="Repetitions per case")
    ap.add_argument("--force-live", action="store_true", help="Force live advisory path")
    ap.add_argument("--max-candidates", type=int, default=12, help="Max candidate profiles to evaluate")
    ap.add_argument("--cooldown-grid", default="1800,3600,7200,10800", help="advisory_text_repeat_cooldown_s grid")
    ap.add_argument("--tool-cooldown-grid", default="90,120,180", help="tool_cooldown_s grid")
    ap.add_argument("--advice-repeat-grid", default="1800,3600,7200", help="advice_repeat_cooldown_s grid")
    ap.add_argument("--min-rank-grid", default="0.45,0.5,0.55", help="advisor.min_rank_score grid")
    ap.add_argument("--max-items-grid", default="3,4,5", help="advisor.max_items grid")
    ap.add_argument("--out-prefix", default="advisory_profile_sweeper", help="Output file prefix in benchmarks/out")
    args = ap.parse_args()

    candidates = build_candidate_profiles(
        advisory_text_repeat_grid=parse_int_grid(args.cooldown_grid),
        tool_cooldown_grid=parse_int_grid(args.tool_cooldown_grid),
        advice_repeat_grid=parse_int_grid(args.advice_repeat_grid),
        min_rank_score_grid=parse_float_grid(args.min_rank_grid),
        max_items_grid=parse_int_grid(args.max_items_grid),
        max_emit_per_call=1,
    )
    selected = select_candidate_subset(candidates, max(1, int(args.max_candidates)))
    report = sweep_profiles(
        cases_path=Path(args.cases),
        repeats=max(1, int(args.repeats)),
        force_live=bool(args.force_live),
        candidates=selected,
        weights=SweepWeights(),
    )

    out_dir = Path("benchmarks") / "out"
    out_dir.mkdir(parents=True, exist_ok=True)
    json_path = out_dir / f"{args.out_prefix}_report.json"
    md_path = out_dir / f"{args.out_prefix}_report.md"
    winner_profile_path = out_dir / f"{args.out_prefix}_winner_profile.json"

    json_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    md_path.write_text(render_markdown(report), encoding="utf-8")
    winner_profile_path.write_text(json.dumps(report.get("winner_profile_file") or {}, indent=2), encoding="utf-8")

    winner = report.get("winner") or {}
    summary = winner.get("summary") or {}
    print(f"Wrote: {json_path}")
    print(f"Wrote: {md_path}")
    print(f"Wrote: {winner_profile_path}")
    print(
        f"Winner={winner.get('profile','n/a')} "
        f"objective={float(summary.get('objective_score',0.0)):.4f} "
        f"score={float(summary.get('score',0.0)):.4f} "
        f"no_emit={float(summary.get('no_emit_rate',0.0)):.2%}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
