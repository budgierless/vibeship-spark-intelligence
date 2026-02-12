#!/usr/bin/env python3
"""Run A/B/C/D schema-capture experiments for chip learning quality.

This benchmark is intentionally isolated from live runtime files:
- each experiment runs in a temporary chip-insights directory
- runtime/env overrides are applied per experiment arm
- outputs are comparable across arms (same synthetic event stream)
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import random
import re
import sys
import tempfile
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Dict, Iterator, List

ROOT = Path(__file__).resolve().parents[1]
BENCH_DIR = ROOT / "benchmarks"
DEFAULT_PLAN = BENCH_DIR / "data" / "chip_schema_experiment_plan_v1.json"

from lib import chip_merger as cm
from lib.chips import runtime as runtime_mod


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except Exception:
        return float(default)


def _slug(value: str) -> str:
    text = re.sub(r"[^a-z0-9_]+", "_", str(value or "").strip().lower())
    text = re.sub(r"_+", "_", text).strip("_")
    return text or "exp"


def _load_plan(path: Path) -> Dict[str, Any]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError(f"expected object JSON: {path}")
    exps = [e for e in (raw.get("experiments") or []) if isinstance(e, dict)]
    if not exps:
        raise ValueError(f"plan has no experiments: {path}")
    return raw


def _stable_int_seed(*parts: Any) -> int:
    text = "|".join(str(p) for p in parts)
    digest = hashlib.sha1(text.encode("utf-8", errors="ignore")).hexdigest()[:8]
    return int(digest, 16)


def _build_event(chip_id: str, i: int, rng: random.Random) -> Dict[str, Any]:
    suffix = f"{chip_id.replace('_', '-')}-{i}"
    if chip_id == "social-convo":
        outcome = "positive" if i % 4 != 0 else "neutral"
        likes = int(10 + i + rng.randint(0, 15))
        replies_received = int(1 + (i % 5))
        base = {
            "event_type": "post_tool",
            "tool_name": "mcp__x-twitter__get_tweet_details",
            "content": "reply performance reply engagement reply metrics conversation dynamics",
            "tweet_id": f"tw-{suffix}",
            "outcome_type": outcome,
            "likes": likes,
            "replies_received": replies_received,
            "author_responded": bool(i % 2 == 0),
            "status": "success",
        }
        base["payload"] = {
            "text": base["content"],
            "tweet_id": base["tweet_id"],
            "outcome_type": base["outcome_type"],
            "likes": likes,
            "replies_received": replies_received,
        }
        return base
    if chip_id == "engagement-pulse":
        age = "1" if i % 3 == 0 else ("6" if i % 3 == 1 else "24")
        likes = int(20 + i + rng.randint(0, 30))
        replies = int(2 + (i % 6))
        retweets = int(1 + (i % 4))
        base = {
            "event_type": "engagement_snapshot",
            "tool_name": "mcp__x-twitter__get_tweet_details",
            "content": "engagement snapshot engagement update tweet metrics performance",
            "tweet_id": f"tw-{suffix}",
            "snapshot_age": age,
            "likes": likes,
            "replies": replies,
            "retweets": retweets,
            "velocity": f"{8 + (i % 7)}",
            "status": "success",
        }
        base["payload"] = {
            "text": base["content"],
            "tweet_id": base["tweet_id"],
            "snapshot_age": age,
            "likes": likes,
            "replies": replies,
            "retweets": retweets,
            "velocity": base["velocity"],
        }
        return base
    # x_social default path
    quality = "low" if i % 5 == 0 else "high"
    confidence = 0.85 if quality == "high" else 0.65
    base = {
        "event_type": "x_session_complete",
        "tool_name": "mcp__x-twitter__search_twitter",
        "content": "social insight learned that works better than generic posting",
        "insight": f"Conversation hooks with reciprocity outperform generic broadcasts ({quality}).",
        "confidence": confidence,
        "evidence": f"observed_in_{3 + (i % 5)}_threads",
        "category": "engagement",
        "status": "success",
    }
    base["payload"] = {
        "text": base["content"],
        "insight": base["insight"],
        "confidence": confidence,
        "evidence": base["evidence"],
        "category": base["category"],
    }
    return base


@contextmanager
def _scoped_overrides(
    *,
    chip_dir: Path,
    merge_state_file: Path,
    distill_file: Path,
    tuneables_file: Path,
    env_overrides: Dict[str, str],
) -> Iterator[None]:
    old_runtime_dir = runtime_mod.CHIP_INSIGHTS_DIR
    old_chip_dir = cm.CHIP_INSIGHTS_DIR
    old_merge_state = cm.MERGE_STATE_FILE
    old_distill_file = cm.LEARNING_DISTILLATIONS_FILE
    old_tuneables_file = cm.TUNEABLES_FILE
    old_env: Dict[str, str | None] = {}
    try:
        runtime_mod.CHIP_INSIGHTS_DIR = chip_dir
        cm.CHIP_INSIGHTS_DIR = chip_dir
        cm.MERGE_STATE_FILE = merge_state_file
        cm.LEARNING_DISTILLATIONS_FILE = distill_file
        cm.TUNEABLES_FILE = tuneables_file
        for k, v in env_overrides.items():
            old_env[k] = os.environ.get(k)
            os.environ[k] = str(v)
        yield
    finally:
        runtime_mod.CHIP_INSIGHTS_DIR = old_runtime_dir
        cm.CHIP_INSIGHTS_DIR = old_chip_dir
        cm.MERGE_STATE_FILE = old_merge_state
        cm.LEARNING_DISTILLATIONS_FILE = old_distill_file
        cm.TUNEABLES_FILE = old_tuneables_file
        for k, prev in old_env.items():
            if prev is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = prev


def _objective_score(metrics: Dict[str, Any], weights: Dict[str, float]) -> float:
    row = {
        "capture_coverage": _safe_float(metrics.get("capture_coverage"), 0.0),
        "schema_payload_rate": _safe_float(metrics.get("schema_payload_rate"), 0.0),
        "schema_statement_rate": _safe_float(metrics.get("schema_statement_rate"), 0.0),
        "merge_eligible_rate": _safe_float(metrics.get("merge_eligible_rate"), 0.0),
        "learning_quality_pass_rate": _safe_float(metrics.get("learning_quality_pass_rate"), 0.0),
        "non_telemetry_rate": 1.0 - _safe_float(metrics.get("telemetry_rate"), 1.0),
        "payload_valid_emission_rate": _safe_float(metrics.get("payload_valid_emission_rate"), 0.0),
    }
    total = 0.0
    for key, weight in weights.items():
        total += _safe_float(weight, 0.0) * _safe_float(row.get(key), 0.0)
    return round(total, 4)


def _infer_quality_fallback(*, row: Dict[str, Any], statement: str, captured: Dict[str, Any]) -> Dict[str, float]:
    text = str(statement or "").strip().lower()
    payload = (captured.get("learning_payload") or {}) if isinstance(captured, dict) else {}
    evidence_items = 0
    if isinstance(payload, dict):
        evidence = payload.get("evidence")
        if isinstance(evidence, list):
            evidence_items = len([x for x in evidence if str(x or "").strip()])

    confidence = _safe_float(row.get("confidence"), 0.0)
    words = max(1, len(text.split()))
    cognitive = min(1.0, 0.2 + min(0.35, words / 40.0) + min(0.2, evidence_items * 0.08))
    actionability = min(1.0, 0.2 + (0.25 if any(k in text for k in ("prefer ", "avoid ", "when ", "if ")) else 0.05))
    transferability = min(1.0, 0.2 + (0.2 if any(k in text for k in ("across ", "for ", "pattern", "works better")) else 0.05))
    total = max(confidence, (cognitive + actionability + transferability) / 3.0)
    return {
        "total": round(total, 4),
        "cognitive_value": round(cognitive, 4),
        "actionability": round(actionability, 4),
        "transferability": round(transferability, 4),
    }


def _quality_effectively_empty(quality: Dict[str, Any]) -> bool:
    if not isinstance(quality, dict) or not quality:
        return True
    keys = ("total", "cognitive_value", "actionability", "transferability")
    values = [_safe_float(quality.get(k), 0.0) for k in keys]
    return max(values) <= 0.0


def _evaluate_promotion_gate(
    experiments: List[Dict[str, Any]],
    *,
    baseline_id: str,
    candidate_id: str,
    min_objective_delta: float = 0.0,
    min_coverage_delta: float = 0.0,
    min_candidate_non_telemetry: float = 0.0,
    min_candidate_schema_statement: float = 0.0,
    min_candidate_merge_eligible: float = 0.0,
) -> Dict[str, Any]:
    baseline = next((r for r in experiments if str(r.get("id")) == str(baseline_id)), {})
    candidate = next((r for r in experiments if str(r.get("id")) == str(candidate_id)), {})
    base_obj = _safe_float(baseline.get("objective"), 0.0)
    cand_obj = _safe_float(candidate.get("objective"), 0.0)
    base_cov = _safe_float(baseline.get("capture_coverage"), 0.0)
    cand_cov = _safe_float(candidate.get("capture_coverage"), 0.0)
    cand_non_tel = 1.0 - _safe_float(candidate.get("telemetry_rate"), 1.0)
    cand_schema = _safe_float(candidate.get("schema_statement_rate"), 0.0)
    cand_merge = _safe_float(candidate.get("merge_eligible_rate"), 0.0)
    obj_delta = round(cand_obj - base_obj, 4)
    cov_delta = round(cand_cov - base_cov, 4)
    floor_ok = (
        cand_non_tel >= float(min_candidate_non_telemetry)
        and cand_schema >= float(min_candidate_schema_statement)
        and cand_merge >= float(min_candidate_merge_eligible)
    )
    passed = obj_delta > float(min_objective_delta) and cov_delta > float(min_coverage_delta) and floor_ok
    reasons: List[str] = []
    if not (obj_delta > float(min_objective_delta) and cov_delta > float(min_coverage_delta)):
        reasons.append("candidate_did_not_beat_baseline_on_both_objective_and_coverage")
    if cand_non_tel < float(min_candidate_non_telemetry):
        reasons.append("candidate_non_telemetry_below_floor")
    if cand_schema < float(min_candidate_schema_statement):
        reasons.append("candidate_schema_statement_below_floor")
    if cand_merge < float(min_candidate_merge_eligible):
        reasons.append("candidate_merge_eligible_below_floor")
    if not reasons:
        reasons.append("candidate_beats_baseline_and_meets_quality_floors")
    return {
        "baseline_id": str(baseline_id),
        "candidate_id": str(candidate_id),
        "baseline_objective": round(base_obj, 4),
        "candidate_objective": round(cand_obj, 4),
        "baseline_coverage": round(base_cov, 4),
        "candidate_coverage": round(cand_cov, 4),
        "objective_delta": obj_delta,
        "coverage_delta": cov_delta,
        "min_objective_delta": float(min_objective_delta),
        "min_coverage_delta": float(min_coverage_delta),
        "candidate_non_telemetry": round(cand_non_tel, 4),
        "candidate_schema_statement": round(cand_schema, 4),
        "candidate_merge_eligible": round(cand_merge, 4),
        "min_candidate_non_telemetry": float(min_candidate_non_telemetry),
        "min_candidate_schema_statement": float(min_candidate_schema_statement),
        "min_candidate_merge_eligible": float(min_candidate_merge_eligible),
        "passed": bool(passed),
        "reasons": reasons,
    }


def _analyze_rows(*, rows: List[Dict[str, Any]], min_total_score: float, limits: Dict[str, Any]) -> Dict[str, Any]:
    rows_analyzed = len(rows)
    telemetry = 0
    statements = 0
    schema_payload = 0
    schema_statement = 0
    quality_pass = 0
    merge_eligible = 0
    fallback_quality_used = 0
    seen = set()

    for row in rows:
        chip_id = str(row.get("chip_id") or "unknown")
        content = str(row.get("content") or "")
        observer_name = str(row.get("observer_name") or "")
        captured = row.get("captured_data") or {}
        statement = cm._distill_learning_statement(
            chip_id=chip_id,
            content=content,
            captured_data=captured,
            min_len=int(limits.get("min_statement_len", 28)),
            observer_name=observer_name,
        )
        quality = (captured.get("quality_score") or {}) if isinstance(captured, dict) else {}
        if _quality_effectively_empty(quality) and statement:
            quality = _infer_quality_fallback(row=row, statement=statement, captured=captured)
            fallback_quality_used += 1
        total = _safe_float(quality.get("total"), _safe_float(row.get("confidence"), 0.0))

        if cm._looks_like_telemetry(chip_id, content):
            telemetry += 1
        if isinstance(captured.get("learning_payload"), dict):
            schema_payload += 1
            payload_statement = cm._payload_based_learning_statement(
                captured_data=captured,
                min_len=int(limits.get("min_statement_len", 28)),
            )
            if payload_statement:
                schema_statement += 1
        if statement:
            statements += 1
        learning_ok = cm._is_learning_quality_ok(quality, limits)
        if learning_ok:
            quality_pass += 1
        if total >= min_total_score and statement and learning_ok:
            sig = cm._hash_insight(chip_id, statement)
            if sig not in seen:
                seen.add(sig)
                merge_eligible += 1

    denom = max(1, rows_analyzed)
    return {
        "rows_analyzed": rows_analyzed,
        "telemetry_rate": round(telemetry / denom, 4),
        "statement_yield_rate": round(statements / denom, 4),
        "schema_payload_rate": round(schema_payload / denom, 4),
        "schema_statement_rate": round(schema_statement / denom, 4),
        "learning_quality_pass_rate": round(quality_pass / denom, 4),
        "merge_eligible_count": int(merge_eligible),
        "merge_eligible_rate": round(merge_eligible / denom, 4),
        "quality_fallback_rate": round(fallback_quality_used / denom, 4),
    }


def _run_experiment(
    *,
    exp: Dict[str, Any],
    weights: Dict[str, float],
    chips: List[str],
    events_per_chip: int,
    min_total_score: float,
    base_seed: int,
    tmp_dir: Path,
) -> Dict[str, Any]:
    exp_id = str(exp.get("id") or "exp")
    runtime_cfg = dict(exp.get("runtime") or {})
    merge_cfg = dict(exp.get("merge_limits") or {})
    arm_dir = tmp_dir / _slug(exp_id)
    arm_dir.mkdir(parents=True, exist_ok=True)
    chip_dir = arm_dir / "chip_insights"
    chip_dir.mkdir(parents=True, exist_ok=True)
    tuneables_file = arm_dir / "tuneables.json"
    tuneables_file.write_text(json.dumps({"chip_merge": merge_cfg}, indent=2), encoding="utf-8")

    env_overrides = {
        "SPARK_CHIP_REQUIRE_LEARNING_SCHEMA": str(runtime_cfg.get("require_learning_schema", "1")),
        "SPARK_CHIP_MIN_LEARNING_EVIDENCE": str(runtime_cfg.get("min_learning_evidence", 1)),
        "SPARK_CHIP_MIN_CONFIDENCE": str(runtime_cfg.get("min_confidence", 0.7)),
        "SPARK_CHIP_MIN_SCORE": str(runtime_cfg.get("min_score", 0.35)),
        "SPARK_CHIP_OBSERVER_ONLY": str(runtime_cfg.get("observer_only", "1")),
    }

    insights_emitted = 0
    payload_valid = 0
    emitted_by_chip: Dict[str, int] = {}
    rows: List[Dict[str, Any]] = []

    with _scoped_overrides(
        chip_dir=chip_dir,
        merge_state_file=arm_dir / "chip_merge_state.json",
        distill_file=arm_dir / "chip_learning_distillations.jsonl",
        tuneables_file=tuneables_file,
        env_overrides=env_overrides,
    ):
        runtime = runtime_mod.ChipRuntime()
        for chip_id in chips:
            chip = runtime.registry.get_chip(chip_id)
            if not chip:
                continue
            rng = random.Random(_stable_int_seed(base_seed, exp_id, chip_id))
            for i in range(max(1, int(events_per_chip))):
                event = _build_event(chip_id, i, rng)
                out = runtime.process_event_for_chips(event, [chip])
                for ins in out:
                    insights_emitted += 1
                    emitted_by_chip[chip_id] = emitted_by_chip.get(chip_id, 0) + 1
                    if runtime._is_learning_payload_valid((ins.captured_data or {}).get("learning_payload")):
                        payload_valid += 1

        rows = cm.load_chip_insights(limit=max(100, len(chips) * events_per_chip * 4))
        limits = cm._load_merge_tuneables()
        analyzed = _analyze_rows(rows=rows, min_total_score=min_total_score, limits=limits)

        merge_stats = cm.merge_chip_insights(
            min_confidence=_safe_float(runtime_cfg.get("merge_min_confidence"), 0.7),
            min_quality_score=_safe_float(runtime_cfg.get("merge_min_quality"), 0.7),
            limit=max(20, len(rows)),
            dry_run=True,
        )

    analyzed["id"] = exp_id
    analyzed["mode"] = str(exp.get("mode") or exp_id)
    analyzed["hypothesis"] = str(exp.get("hypothesis") or "")
    analyzed["description"] = str(exp.get("description") or "")
    analyzed["events_requested"] = int(max(1, int(events_per_chip)) * max(1, len(chips)))
    analyzed["insights_emitted"] = int(insights_emitted)
    analyzed["capture_coverage"] = round(insights_emitted / max(1, analyzed["events_requested"]), 4)
    analyzed["payload_valid_count"] = int(payload_valid)
    analyzed["payload_valid_emission_rate"] = round(payload_valid / max(1, insights_emitted), 4)
    analyzed["emitted_by_chip"] = emitted_by_chip
    analyzed["merge_dry_run"] = {
        "processed": int(merge_stats.get("processed", 0) or 0),
        "merged_distilled": int(merge_stats.get("merged_distilled", 0) or 0),
        "skipped_non_learning": int(merge_stats.get("skipped_non_learning", 0) or 0),
    }
    analyzed["objective"] = _objective_score(analyzed, weights)
    analyzed["runtime"] = runtime_cfg
    analyzed["merge_limits"] = merge_cfg
    return analyzed


def _report_markdown(report: Dict[str, Any]) -> str:
    lines: List[str] = []
    lines.append(f"# Chip Schema Experiments ({report.get('generated_at', '')})")
    lines.append("")
    lines.append(f"- Plan: `{report.get('plan_path','')}`")
    lines.append(f"- Chips: `{', '.join(report.get('chips') or [])}`")
    lines.append(f"- Events per chip: `{int(report.get('events_per_chip', 0))}`")
    lines.append(f"- Min total quality score: `{_safe_float(report.get('min_total_score'), 0.55):.2f}`")
    lines.append(f"- Weights: `{report.get('objective_weights')}`")
    gate = dict(report.get("promotion_gate") or {})
    if gate:
        lines.append(
            f"- Promotion gate (`{gate.get('candidate_id','')}` vs `{gate.get('baseline_id','')}`): "
            f"`{'PASS' if bool(gate.get('passed')) else 'FAIL'}` "
            f"(objective_delta={float(gate.get('objective_delta',0.0)):+.4f}, "
            f"coverage_delta={float(gate.get('coverage_delta',0.0)):+.4f})"
        )
    lines.append("")
    lines.append("| Rank | Experiment | Objective | Coverage | Schema Payload | Schema Statement | Merge Eligible | Non-Telemetry | Payload Valid Emission |")
    lines.append("|---|---|---:|---:|---:|---:|---:|---:|---:|")
    for idx, row in enumerate(report.get("ranked_experiments") or [], start=1):
        lines.append(
            f"| {idx} | `{row.get('id','')}` ({row.get('mode','')}) | {float(row.get('objective',0.0)):.4f} | "
            f"{float(row.get('capture_coverage',0.0)):.2%} | "
            f"{float(row.get('schema_payload_rate',0.0)):.2%} | {float(row.get('schema_statement_rate',0.0)):.2%} | "
            f"{float(row.get('merge_eligible_rate',0.0)):.2%} | {1.0 - float(row.get('telemetry_rate',1.0)):.2%} | "
            f"{float(row.get('payload_valid_emission_rate',0.0)):.2%} |"
        )
    lines.append("")
    lines.append("## Experiment Details")
    lines.append("")
    for row in report.get("ranked_experiments") or []:
        lines.append(f"### `{row.get('id','')}`")
        lines.append(f"- Mode: `{row.get('mode','')}`")
        if str(row.get("hypothesis") or "").strip():
            lines.append(f"- Hypothesis: {row.get('hypothesis','')}")
        lines.append(f"- Description: {row.get('description','')}")
        lines.append(f"- Objective: `{float(row.get('objective',0.0)):.4f}`")
        lines.append(f"- Rows analyzed: `{int(row.get('rows_analyzed',0))}`")
        lines.append(f"- Capture coverage: `{float(row.get('capture_coverage',0.0)):.2%}`")
        lines.append(f"- Schema payload rate: `{float(row.get('schema_payload_rate',0.0)):.2%}`")
        lines.append(f"- Schema statement rate: `{float(row.get('schema_statement_rate',0.0)):.2%}`")
        lines.append(f"- Merge-eligible rate: `{float(row.get('merge_eligible_rate',0.0)):.2%}`")
        lines.append(f"- Telemetry rate: `{float(row.get('telemetry_rate',0.0)):.2%}`")
        lines.append(f"- Payload valid emission rate: `{float(row.get('payload_valid_emission_rate',0.0)):.2%}`")
        lines.append(f"- Emitted by chip: `{row.get('emitted_by_chip',{})}`")
        lines.append("")
    return "\n".join(lines).strip() + "\n"


def main() -> int:
    ap = argparse.ArgumentParser(description="Run chip schema A/B/C/D experiments")
    ap.add_argument("--plan", default=str(DEFAULT_PLAN), help="Path to schema experiment plan JSON")
    ap.add_argument("--chips", default="social-convo,engagement-pulse,x_social", help="Comma-separated chip ids")
    ap.add_argument("--events-per-chip", type=int, default=20, help="Synthetic events generated per chip per experiment")
    ap.add_argument("--min-total-score", type=float, default=None, help="Threshold for merge-eligible counting (default: plan value, else 0.55)")
    ap.add_argument("--random-seed", type=int, default=7, help="Random seed for synthetic event variation")
    ap.add_argument("--promotion-baseline-id", default="A_schema_baseline", help="Baseline arm ID for promotion gate")
    ap.add_argument("--promotion-candidate-id", default="B_schema_evidence2", help="Candidate arm ID for promotion gate")
    ap.add_argument("--min-objective-delta", type=float, default=0.0, help="Promotion requires candidate objective delta > this")
    ap.add_argument("--min-coverage-delta", type=float, default=0.0, help="Promotion requires candidate coverage delta > this")
    ap.add_argument("--min-candidate-non-telemetry", type=float, default=0.0, help="Promotion requires candidate non-telemetry rate >= this")
    ap.add_argument("--min-candidate-schema-statement", type=float, default=0.0, help="Promotion requires candidate schema statement rate >= this")
    ap.add_argument("--min-candidate-merge-eligible", type=float, default=0.0, help="Promotion requires candidate merge-eligible rate >= this")
    ap.add_argument("--out-prefix", default="chip_schema_experiments_v1", help="Output file prefix under benchmarks/out")
    args = ap.parse_args()

    plan_path = Path(args.plan)
    plan = _load_plan(plan_path)
    experiments = [e for e in (plan.get("experiments") or []) if isinstance(e, dict)]
    weights = dict(plan.get("objective_weights") or {})
    chips = [c.strip() for c in str(args.chips or "").split(",") if c.strip()]
    if not chips:
        raise ValueError("no chips specified")

    chosen_min_total_score = (
        float(args.min_total_score)
        if args.min_total_score is not None
        else float(plan.get("min_total_score", 0.55))
    )

    out_dir = ROOT / "benchmarks" / "out"
    out_dir.mkdir(parents=True, exist_ok=True)

    rows: List[Dict[str, Any]] = []
    with tempfile.TemporaryDirectory(prefix="chip_schema_exp_", dir=str(ROOT)) as tmp:
        tmp_dir = Path(tmp)
        for exp in experiments:
            row = _run_experiment(
                exp=exp,
                weights=weights,
                chips=chips,
                events_per_chip=max(1, int(args.events_per_chip)),
                min_total_score=max(0.0, min(1.0, float(chosen_min_total_score))),
                base_seed=int(args.random_seed),
                tmp_dir=tmp_dir,
            )
            rows.append(row)

    control_id = str(plan.get("control_experiment_id") or (rows[0].get("id") if rows else ""))
    control = next((r for r in rows if str(r.get("id")) == control_id), rows[0] if rows else {})
    control_obj = _safe_float(control.get("objective"), 0.0)
    for row in rows:
        row["delta_objective_vs_control"] = round(_safe_float(row.get("objective"), 0.0) - control_obj, 4)

    ranked = sorted(rows, key=lambda r: _safe_float(r.get("objective"), 0.0), reverse=True)
    promotion_gate = _evaluate_promotion_gate(
        rows,
        baseline_id=str(args.promotion_baseline_id),
        candidate_id=str(args.promotion_candidate_id),
        min_objective_delta=float(args.min_objective_delta),
        min_coverage_delta=float(args.min_coverage_delta),
        min_candidate_non_telemetry=float(args.min_candidate_non_telemetry),
        min_candidate_schema_statement=float(args.min_candidate_schema_statement),
        min_candidate_merge_eligible=float(args.min_candidate_merge_eligible),
    )
    report = {
        "generated_at": datetime.now(UTC).isoformat(),
        "plan_path": str(plan_path),
        "chips": chips,
        "events_per_chip": int(args.events_per_chip),
        "min_total_score": float(chosen_min_total_score),
        "objective_weights": weights,
        "control_experiment_id": control_id,
        "experiments": rows,
        "ranked_experiments": ranked,
        "winner": ranked[0] if ranked else {},
        "promotion_gate": promotion_gate,
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
        f"schema_statement={_safe_float(winner.get('schema_statement_rate'), 0.0):.2%} "
        f"merge_eligible={_safe_float(winner.get('merge_eligible_rate'), 0.0):.2%}"
    )
    print(
        "PromotionGate="
        f"{'PASS' if bool(promotion_gate.get('passed')) else 'FAIL'} "
        f"candidate={promotion_gate.get('candidate_id','')} "
        f"baseline={promotion_gate.get('baseline_id','')} "
        f"objective_delta={_safe_float(promotion_gate.get('objective_delta'),0.0):+.4f} "
        f"coverage_delta={_safe_float(promotion_gate.get('coverage_delta'),0.0):+.4f}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
