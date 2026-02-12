#!/usr/bin/env python3
"""Run multi-style chip experiments for advisory realism benchmarks.

Supports:
- A/B global chip off/on
- C/D segmented domain-targeted chip strategies
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
import random
import re
import sys
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Dict, List, Tuple

ROOT = Path(__file__).resolve().parents[1]
BENCH_DIR = ROOT / "benchmarks"
if str(BENCH_DIR) not in sys.path:
    sys.path.insert(0, str(BENCH_DIR))

import advisory_quality_ab as aq
import advisory_realism_bench as arb


DEFAULT_PLAN = BENCH_DIR / "data" / "advisory_chip_experiment_plan_v1.json"


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except Exception:
        return float(default)


def _load_json(path: Path) -> Dict[str, Any]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError(f"expected object JSON: {path}")
    return raw


def _norm_domain(value: Any) -> str:
    text = str(value or "").strip().lower()
    if not text:
        return "general"
    text = re.sub(r"[^a-z0-9_]+", "_", text)
    text = re.sub(r"_+", "_", text).strip("_")
    return text or "general"


def _slug(value: str) -> str:
    return _norm_domain(value)[:64] or "x"


def _load_cases(path: Path) -> Dict[str, Any]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(raw, dict):
        rows = [r for r in (raw.get("cases") or []) if isinstance(r, dict)]
        return {"version": str(raw.get("version") or "cases"), "notes": str(raw.get("notes") or ""), "cases": rows}
    if isinstance(raw, list):
        return {"version": "cases", "notes": "", "cases": [r for r in raw if isinstance(r, dict)]}
    raise ValueError(f"invalid cases payload: {path}")


def _group_cases_by_domain(rows: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
    grouped: Dict[str, List[Dict[str, Any]]] = {}
    for row in rows:
        domain = _norm_domain(row.get("domain"))
        grouped.setdefault(domain, []).append(row)
    return grouped


def _parse_domains(spec: str, available: List[str]) -> List[str]:
    text = str(spec or "").strip()
    if not text or text == "*":
        return sorted(set(available))
    wanted = []
    for raw in text.split(","):
        dom = _norm_domain(raw)
        if dom:
            wanted.append(dom)
    return sorted(set(wanted))


def _merge_profiles(profile_file: str) -> Dict[str, Dict[str, Any]]:
    profiles = dict(aq.DEFAULT_PROFILE_PRESETS)
    if not profile_file:
        return profiles
    pf = Path(profile_file)
    loaded = json.loads(pf.read_text(encoding="utf-8"))
    if not isinstance(loaded, dict):
        return profiles
    for key, val in loaded.items():
        if not isinstance(val, dict):
            continue
        cur = dict(profiles.get(key) or {})
        for section in ("advisory_engine", "advisory_gate", "advisor"):
            if isinstance(val.get(section), dict):
                merged = dict(cur.get(section) or {})
                merged.update(val.get(section) or {})
                cur[section] = merged
        profiles[key] = cur
    return profiles


def _stable_int_seed(*parts: Any) -> int:
    joined = "|".join(str(p) for p in parts)
    digest = hashlib.sha256(joined.encode("utf-8")).hexdigest()
    return int(digest[:8], 16)


def _maybe_shuffle_and_sample(
    rows: List[Dict[str, Any]],
    *,
    shuffle_seed: int,
    sample_ratio: float,
) -> List[Dict[str, Any]]:
    items = list(rows or [])
    if not items:
        return items
    if shuffle_seed >= 0:
        rng = random.Random(shuffle_seed)
        rng.shuffle(items)
    ratio = max(0.05, min(1.0, float(sample_ratio)))
    if ratio >= 1.0:
        return items
    keep = max(1, int(round(len(items) * ratio)))
    return items[:keep]


def _chip_ablation_profiles(profiles: Dict[str, Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    out = copy.deepcopy(profiles)
    for _, cfg in out.items():
        advisor_cfg = dict(cfg.get("advisor") or {})
        advisor_cfg.update(
            {
                "chip_advice_limit": 1,
                "chip_advice_min_score": 0.99,
                "chip_advice_max_files": 1,
                "chip_advice_file_tail": 8,
                "chip_source_boost": 0.6,
            }
        )
        cfg["advisor"] = advisor_cfg
    return out


def _run_realism_with_chip_mode(
    *,
    cases_path: Path,
    profiles: Dict[str, Dict[str, Any]],
    profile_names: List[str],
    repeats: int,
    force_live: bool,
    disable_chips: bool,
) -> Dict[str, Any]:
    env_key = "SPARK_ADVISORY_DISABLE_CHIPS"
    previous = os.environ.get(env_key)
    try:
        if disable_chips:
            os.environ[env_key] = "1"
        else:
            os.environ.pop(env_key, None)
        return arb.run_realism_benchmark(
            cases_path=cases_path,
            profiles=profiles,
            profile_names=profile_names,
            repeats=max(1, int(repeats)),
            force_live=bool(force_live),
            gates=arb.REALISM_GATES,
        )
    finally:
        if previous is None:
            os.environ.pop(env_key, None)
        else:
            os.environ[env_key] = previous


def _winner_source_hit_rates(winner: Dict[str, Any]) -> Dict[str, float]:
    cases = list(winner.get("cases") or [])
    if not cases:
        return {
            "chip_hit_case_rate": 0.0,
            "mind_hit_case_rate": 0.0,
            "semantic_hit_case_rate": 0.0,
            "chip_evidence_case_rate": 0.0,
            "mind_evidence_case_rate": 0.0,
            "semantic_evidence_case_rate": 0.0,
        }

    chip = 0
    mind = 0
    semantic = 0
    chip_evidence = 0
    mind_evidence = 0
    semantic_evidence = 0
    for row in cases:
        src = dict(row.get("source_counts") or {})
        adv = dict(row.get("advice_source_counts") or {})
        chip_advice_count = int(adv.get("chips", 0) or 0) + int(adv.get("chip", 0) or 0)
        mind_advice_count = int(adv.get("mind", 0) or 0)
        semantic_advice_count = int(adv.get("semantic", 0) or 0)
        chip_evidence_count = int(src.get("chips", 0) or 0)
        mind_evidence_count = int(src.get("mind", 0) or 0)
        semantic_evidence_count = int(src.get("semantic", 0) or 0)
        if chip_advice_count > 0:
            chip += 1
        if mind_advice_count > 0:
            mind += 1
        if semantic_advice_count > 0:
            semantic += 1
        if chip_evidence_count > 0:
            chip_evidence += 1
        if mind_evidence_count > 0:
            mind_evidence += 1
        if semantic_evidence_count > 0:
            semantic_evidence += 1
    denom = max(1, len(cases))
    return {
        "chip_hit_case_rate": round(chip / denom, 4),
        "mind_hit_case_rate": round(mind / denom, 4),
        "semantic_hit_case_rate": round(semantic / denom, 4),
        "chip_evidence_case_rate": round(chip_evidence / denom, 4),
        "mind_evidence_case_rate": round(mind_evidence / denom, 4),
        "semantic_evidence_case_rate": round(semantic_evidence / denom, 4),
    }


def _weighted(runs: List[Dict[str, Any]], key: str) -> float:
    numer = 0.0
    denom = 0
    for row in runs:
        weight = max(1, int(row.get("case_count", 0) or 0))
        numer += _safe_float(row.get(key), 0.0) * weight
        denom += weight
    if denom <= 0:
        return 0.0
    return round(numer / denom, 4)


def _report_markdown(report: Dict[str, Any]) -> str:
    lines: List[str] = []
    lines.append(f"# Advisory Chip Experiments ({report.get('generated_at', '')})")
    lines.append("")
    lines.append(f"- Plan: `{report.get('plan_path', '')}`")
    lines.append(f"- Cases: `{report.get('cases_path', '')}`")
    lines.append(f"- Profiles: `{', '.join(report.get('profiles') or [])}`")
    lines.append(f"- Repeats: `{report.get('repeats', 1)}`")
    lines.append(f"- Force live: `{bool(report.get('force_live', True))}`")
    lines.append(f"- Random seed: `{report.get('random_seed', -1)}`")
    lines.append(f"- Sample ratio: `{float(report.get('sample_ratio', 1.0)):.2f}`")
    lines.append(f"- Chip ablation: `{bool(report.get('chip_ablation', True))}`")
    lines.append("")
    lines.append("| Rank | Experiment | Cases | Objective | Ablation Obj | Chip Lift Obj | High-Value | Harmful | Unsolicited | Chip Advice Hit | Delta Obj |")
    lines.append("|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|")
    for idx, row in enumerate(report.get("ranked_experiments") or [], start=1):
        lines.append(
            f"| {idx} | `{row.get('id','')}` | {int(row.get('case_count',0))} | "
            f"{float(row.get('objective',0.0)):.4f} | {float(row.get('ablation_objective',0.0)):.4f} | "
            f"{float(row.get('chip_lift_objective',0.0)):+.4f} | {float(row.get('high_value_rate',0.0)):.2%} | "
            f"{float(row.get('harmful_emit_rate',0.0)):.2%} | {float(row.get('unsolicited_emit_rate',0.0)):.2%} | "
            f"{float(row.get('chip_hit_case_rate',0.0)):.2%} | {float(row.get('delta_objective_vs_control',0.0)):+.4f} |"
        )
    lines.append("")
    lines.append("## Experiment Notes")
    lines.append("")
    for row in report.get("ranked_experiments") or []:
        lines.append(f"### `{row.get('id','')}`")
        lines.append(f"- Description: {row.get('description','')}")
        lines.append(f"- Domains: `{', '.join(row.get('domains') or [])}`")
        lines.append(f"- Objective: `{float(row.get('objective',0.0)):.4f}`")
        lines.append(f"- Ablation objective (chips disabled): `{float(row.get('ablation_objective',0.0)):.4f}`")
        lines.append(f"- Chip lift objective: `{float(row.get('chip_lift_objective',0.0)):+.4f}`")
        lines.append(f"- High-value: `{float(row.get('high_value_rate',0.0)):.2%}`")
        lines.append(f"- Ablation high-value: `{float(row.get('ablation_high_value_rate',0.0)):.2%}`")
        lines.append(f"- Chip lift high-value: `{float(row.get('chip_lift_high_value_rate',0.0)):+.2%}`")
        lines.append(f"- Harmful: `{float(row.get('harmful_emit_rate',0.0)):.2%}`")
        lines.append(f"- Ablation harmful: `{float(row.get('ablation_harmful_emit_rate',0.0)):.2%}`")
        lines.append(f"- Chip lift harmful (positive is safer): `{float(row.get('chip_lift_harmful_emit_rate',0.0)):+.2%}`")
        lines.append(f"- Unsolicited: `{float(row.get('unsolicited_emit_rate',0.0)):.2%}`")
        lines.append(f"- Chip advice hit: `{float(row.get('chip_hit_case_rate',0.0)):.2%}`")
        lines.append(f"- Chip evidence hit: `{float(row.get('chip_evidence_case_rate',0.0)):.2%}`")
        lines.append(f"- Mind advice hit: `{float(row.get('mind_hit_case_rate',0.0)):.2%}`")
        lines.append(f"- Mind evidence hit: `{float(row.get('mind_evidence_case_rate',0.0)):.2%}`")
        lines.append(f"- Semantic advice hit: `{float(row.get('semantic_hit_case_rate',0.0)):.2%}`")
        lines.append(f"- Semantic evidence hit: `{float(row.get('semantic_evidence_case_rate',0.0)):.2%}`")
        lines.append(f"- Delta objective vs control: `{float(row.get('delta_objective_vs_control',0.0)):+.4f}`")
        lines.append("")
    return "\n".join(lines).strip() + "\n"


def main() -> int:
    ap = argparse.ArgumentParser(description="Run advisory chip experiment plan")
    ap.add_argument("--plan", default=str(DEFAULT_PLAN), help="Path to chip experiment plan JSON")
    ap.add_argument("--cases", default="", help="Override cases path")
    ap.add_argument("--profiles", default="", help="Override profile names (comma-separated)")
    ap.add_argument("--experiments", default="", help="Run only these experiment ids (comma-separated)")
    ap.add_argument("--repeats", type=int, default=1, help="Repeats per case")
    ap.add_argument("--force-live", action=argparse.BooleanOptionalAction, default=True, help="Force live retrieval path")
    ap.add_argument("--random-seed", type=int, default=-1, help="Shuffle seed for case order per segment (-1 disables shuffle)")
    ap.add_argument("--sample-ratio", type=float, default=1.0, help="Random sample ratio per segment (0.05..1.0)")
    ap.add_argument(
        "--chip-ablation",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Run chips-disabled ablation pass for each segment and report chip lift",
    )
    ap.add_argument(
        "--save-segment-reports",
        action=argparse.BooleanOptionalAction,
        default=False,
        help="Save per-segment realism report artifacts",
    )
    ap.add_argument("--out-prefix", default="advisory_chip_experiments_v1", help="Output file prefix under benchmarks/out")
    args = ap.parse_args()

    plan_path = Path(args.plan)
    plan = _load_json(plan_path)
    selected_ids = {x.strip() for x in str(args.experiments or "").split(",") if x.strip()}

    cases_path = Path(args.cases or plan.get("cases") or "")
    if not str(cases_path):
        raise ValueError("missing cases path")
    cases_payload = _load_cases(cases_path)
    all_cases = list(cases_payload.get("cases") or [])
    grouped = _group_cases_by_domain(all_cases)
    available_domains = sorted(grouped.keys())

    profiles_text = str(args.profiles or plan.get("profiles") or "baseline").strip()
    profile_names = [x.strip() for x in profiles_text.split(",") if x.strip()]
    if not profile_names:
        profile_names = ["baseline"]

    out_dir = ROOT / "benchmarks" / "out"
    out_dir.mkdir(parents=True, exist_ok=True)
    segment_out_dir = out_dir / f"{args.out_prefix}_segments"
    if bool(args.save_segment_reports):
        segment_out_dir.mkdir(parents=True, exist_ok=True)

    experiments = [e for e in (plan.get("experiments") or []) if isinstance(e, dict)]
    if selected_ids:
        experiments = [e for e in experiments if str(e.get("id") or "") in selected_ids]
    if not experiments:
        print("No experiments selected", file=sys.stderr)
        return 2

    results: List[Dict[str, Any]] = []
    with tempfile.TemporaryDirectory(prefix="advisory_chip_exp_", dir=str(ROOT)) as tmp:
        tmp_dir = Path(tmp)
        for exp in experiments:
            exp_id = str(exp.get("id") or f"exp_{len(results)+1}")
            description = str(exp.get("description") or "")
            segments = [s for s in (exp.get("segments") or []) if isinstance(s, dict)]
            if not segments:
                continue
            seen_case_ids: set[str] = set()
            seg_rows: List[Dict[str, Any]] = []
            used_domains: set[str] = set()

            for idx, seg in enumerate(segments, start=1):
                domains = _parse_domains(str(seg.get("domains") or "*"), available_domains)
                segment_cases: List[Dict[str, Any]] = []
                for dom in domains:
                    for row in grouped.get(dom, []):
                        cid = str(row.get("id") or "")
                        if cid and cid in seen_case_ids:
                            continue
                        if cid:
                            seen_case_ids.add(cid)
                        segment_cases.append(row)
                        used_domains.add(dom)
                segment_cases = _maybe_shuffle_and_sample(
                    segment_cases,
                    shuffle_seed=(
                        _stable_int_seed(args.random_seed, exp_id, idx)
                        if int(args.random_seed) >= 0
                        else -1
                    ),
                    sample_ratio=float(args.sample_ratio),
                )
                if not segment_cases:
                    continue

                profile_file = str(seg.get("profile_file") or "")
                profiles = _merge_profiles(profile_file)
                seg_profile_names = profile_names
                if str(seg.get("profiles") or "").strip():
                    seg_profile_names = [x.strip() for x in str(seg.get("profiles") or "").split(",") if x.strip()] or seg_profile_names

                subset_path = tmp_dir / f"{_slug(exp_id)}_{idx}.json"
                subset_path.write_text(
                    json.dumps({"version": str(cases_payload.get("version") or "cases"), "notes": f"{exp_id}-segment-{idx}", "cases": segment_cases}, indent=2),
                    encoding="utf-8",
                )
                report = _run_realism_with_chip_mode(
                    cases_path=subset_path,
                    profiles=profiles,
                    profile_names=seg_profile_names,
                    repeats=max(1, int(args.repeats)),
                    force_live=bool(args.force_live),
                    disable_chips=False,
                )
                ablation_report: Dict[str, Any] = {}
                if bool(args.chip_ablation):
                    ablation_report = _run_realism_with_chip_mode(
                        cases_path=subset_path,
                        profiles=_chip_ablation_profiles(profiles),
                        profile_names=seg_profile_names,
                        repeats=max(1, int(args.repeats)),
                        force_live=bool(args.force_live),
                        disable_chips=True,
                    )
                if bool(args.save_segment_reports):
                    exp_dir = segment_out_dir / _slug(exp_id)
                    exp_dir.mkdir(parents=True, exist_ok=True)
                    (exp_dir / f"segment_{idx}_report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
                    (exp_dir / f"segment_{idx}_report.md").write_text(arb._report_markdown(report), encoding="utf-8")
                    if ablation_report:
                        (exp_dir / f"segment_{idx}_ablation_report.json").write_text(
                            json.dumps(ablation_report, indent=2),
                            encoding="utf-8",
                        )
                        (exp_dir / f"segment_{idx}_ablation_report.md").write_text(
                            arb._report_markdown(ablation_report),
                            encoding="utf-8",
                        )

                winner = dict(report.get("winner") or {})
                realism = dict(winner.get("realism") or {})
                source_hits = _winner_source_hit_rates(winner)
                ablation_winner = dict((ablation_report or {}).get("winner") or {})
                ablation_realism = dict(ablation_winner.get("realism") or {})
                seg_rows.append(
                    {
                        "segment_index": idx,
                        "domains": domains,
                        "profile_file": profile_file,
                        "winner_profile": str(winner.get("profile") or "n/a"),
                        "case_count": len(segment_cases),
                        "objective": _safe_float(winner.get("objective"), 0.0),
                        "score": _safe_float((winner.get("summary") or {}).get("score"), 0.0),
                        "high_value_rate": _safe_float(realism.get("high_value_rate"), 0.0),
                        "harmful_emit_rate": _safe_float(realism.get("harmful_emit_rate"), 1.0),
                        "unsolicited_emit_rate": _safe_float(realism.get("unsolicited_emit_rate"), 0.0),
                        "critical_miss_rate": _safe_float(realism.get("critical_miss_rate"), 1.0),
                        "source_alignment_rate": _safe_float(realism.get("source_alignment_rate"), 0.0),
                        "theory_discrimination_rate": _safe_float(realism.get("theory_discrimination_rate"), 0.0),
                        "trace_bound_rate": _safe_float(realism.get("trace_bound_rate"), 0.0),
                        "ablation_objective": _safe_float(ablation_winner.get("objective"), 0.0),
                        "ablation_high_value_rate": _safe_float(ablation_realism.get("high_value_rate"), 0.0),
                        "ablation_harmful_emit_rate": _safe_float(ablation_realism.get("harmful_emit_rate"), 0.0),
                        **source_hits,
                    }
                )

            if not seg_rows:
                continue

            aggregated = {
                "id": exp_id,
                "description": description,
                "domains": sorted(used_domains),
                "segment_count": len(seg_rows),
                "segments": seg_rows,
                "case_count": int(sum(int(r.get("case_count", 0) or 0) for r in seg_rows)),
                "objective": _weighted(seg_rows, "objective"),
                "score": _weighted(seg_rows, "score"),
                "high_value_rate": _weighted(seg_rows, "high_value_rate"),
                "harmful_emit_rate": _weighted(seg_rows, "harmful_emit_rate"),
                "unsolicited_emit_rate": _weighted(seg_rows, "unsolicited_emit_rate"),
                "critical_miss_rate": _weighted(seg_rows, "critical_miss_rate"),
                "source_alignment_rate": _weighted(seg_rows, "source_alignment_rate"),
                "theory_discrimination_rate": _weighted(seg_rows, "theory_discrimination_rate"),
                "trace_bound_rate": _weighted(seg_rows, "trace_bound_rate"),
                "ablation_objective": _weighted(seg_rows, "ablation_objective"),
                "ablation_high_value_rate": _weighted(seg_rows, "ablation_high_value_rate"),
                "ablation_harmful_emit_rate": _weighted(seg_rows, "ablation_harmful_emit_rate"),
                "chip_hit_case_rate": _weighted(seg_rows, "chip_hit_case_rate"),
                "mind_hit_case_rate": _weighted(seg_rows, "mind_hit_case_rate"),
                "semantic_hit_case_rate": _weighted(seg_rows, "semantic_hit_case_rate"),
                "chip_evidence_case_rate": _weighted(seg_rows, "chip_evidence_case_rate"),
                "mind_evidence_case_rate": _weighted(seg_rows, "mind_evidence_case_rate"),
                "semantic_evidence_case_rate": _weighted(seg_rows, "semantic_evidence_case_rate"),
            }
            aggregated["chip_lift_objective"] = round(
                _safe_float(aggregated.get("objective"), 0.0)
                - _safe_float(aggregated.get("ablation_objective"), 0.0),
                4,
            )
            aggregated["chip_lift_high_value_rate"] = round(
                _safe_float(aggregated.get("high_value_rate"), 0.0)
                - _safe_float(aggregated.get("ablation_high_value_rate"), 0.0),
                4,
            )
            # Positive means chips reduced harmful emission.
            aggregated["chip_lift_harmful_emit_rate"] = round(
                _safe_float(aggregated.get("ablation_harmful_emit_rate"), 0.0)
                - _safe_float(aggregated.get("harmful_emit_rate"), 0.0),
                4,
            )
            results.append(aggregated)

    if not results:
        print("No experiment results produced", file=sys.stderr)
        return 2

    control_id = str(plan.get("control_experiment_id") or results[0]["id"])
    control = next((r for r in results if str(r.get("id")) == control_id), results[0])
    control_obj = _safe_float(control.get("objective"), 0.0)
    control_hv = _safe_float(control.get("high_value_rate"), 0.0)
    control_harm = _safe_float(control.get("harmful_emit_rate"), 0.0)
    control_chip = _safe_float(control.get("chip_hit_case_rate"), 0.0)

    for row in results:
        row["delta_objective_vs_control"] = round(_safe_float(row.get("objective"), 0.0) - control_obj, 4)
        row["delta_high_value_vs_control"] = round(_safe_float(row.get("high_value_rate"), 0.0) - control_hv, 4)
        row["delta_harmful_vs_control"] = round(_safe_float(row.get("harmful_emit_rate"), 0.0) - control_harm, 4)
        row["delta_chip_hit_vs_control"] = round(_safe_float(row.get("chip_hit_case_rate"), 0.0) - control_chip, 4)

    ranked = sorted(results, key=lambda r: (_safe_float(r.get("objective"), 0.0), _safe_float(r.get("high_value_rate"), 0.0)), reverse=True)

    report = {
        "generated_at": datetime.now(UTC).isoformat(),
        "plan_path": str(plan_path),
        "cases_path": str(cases_path),
        "profiles": profile_names,
        "repeats": int(args.repeats),
        "force_live": bool(args.force_live),
        "random_seed": int(args.random_seed),
        "sample_ratio": float(args.sample_ratio),
        "chip_ablation": bool(args.chip_ablation),
        "control_experiment_id": str(control.get("id")),
        "experiments": results,
        "ranked_experiments": ranked,
        "winner": ranked[0] if ranked else {},
    }

    json_path = out_dir / f"{args.out_prefix}_report.json"
    md_path = out_dir / f"{args.out_prefix}_report.md"
    json_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    md_path.write_text(_report_markdown(report), encoding="utf-8")

    winner = report.get("winner") or {}
    print(f"Wrote: {json_path}")
    print(f"Wrote: {md_path}")
    print(
        "Winner="
        f"{winner.get('id','n/a')} "
        f"objective={_safe_float(winner.get('objective'), 0.0):.4f} "
        f"ablation={_safe_float(winner.get('ablation_objective'), 0.0):.4f} "
        f"chip_lift={_safe_float(winner.get('chip_lift_objective'), 0.0):+.4f} "
        f"high_value={_safe_float(winner.get('high_value_rate'), 0.0):.2%} "
        f"chip_hit={_safe_float(winner.get('chip_hit_case_rate'), 0.0):.2%}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
