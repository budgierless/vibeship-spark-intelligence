#!/usr/bin/env python3
"""A/B benchmark for advisory quality and utilization.

Evaluates advisory behavior across scenario cases and profile presets.

Primary metrics:
- emit correctness (should_emit vs actual emit)
- expected-content hit rate
- forbidden-content violation rate
- actionability rate
- trace-bound rate
- memory-source utilization rate
- repetition rate (cross-case text duplication)
"""

from __future__ import annotations

import argparse
import json
import statistics
import sys
import time
import uuid
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))


@dataclass
class AdvisoryCase:
    case_id: str
    tool: str
    prompt: str
    tool_input: Dict[str, Any] = field(default_factory=dict)
    should_emit: bool = True
    expected_contains: List[str] = field(default_factory=list)
    forbidden_contains: List[str] = field(default_factory=list)
    notes: str = ""


@dataclass
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
    advice_source_counts: Dict[str, int] = field(default_factory=dict)


@dataclass
class ProfileSummary:
    profile: str
    case_count: int
    score: float
    emit_accuracy: float
    emit_rate: float
    no_emit_rate: float
    expected_hit_rate: float
    forbidden_clean_rate: float
    actionability_rate: float
    trace_bound_rate: float
    memory_utilization_rate: float
    repetition_penalty_rate: float
    fallback_share_pct: float
    p50_latency_ms: float
    p95_latency_ms: float
    top_error_codes: List[Tuple[str, int]]
    no_emit_error_codes: List[Tuple[str, int]]
    route_counts: Dict[str, int]


DEFAULT_PROFILE_PRESETS: Dict[str, Dict[str, Any]] = {
    "baseline": {
        "advisory_engine": {"advisory_text_repeat_cooldown_s": 1800},
        "advisory_gate": {
            "max_emit_per_call": 1,
            "tool_cooldown_s": 90,
            "advice_repeat_cooldown_s": 1800,
        },
        "advisor": {"max_items": 5, "max_advice_items": 5, "min_rank_score": 0.45},
    },
    "balanced": {
        "advisory_engine": {"advisory_text_repeat_cooldown_s": 7200},
        "advisory_gate": {
            "max_emit_per_call": 1,
            "tool_cooldown_s": 120,
            "advice_repeat_cooldown_s": 3600,
        },
        "advisor": {"max_items": 4, "max_advice_items": 4, "min_rank_score": 0.50},
    },
    "strict": {
        "advisory_engine": {"advisory_text_repeat_cooldown_s": 10800},
        "advisory_gate": {
            "max_emit_per_call": 1,
            "tool_cooldown_s": 180,
            "advice_repeat_cooldown_s": 7200,
        },
        "advisor": {"max_items": 4, "max_advice_items": 4, "min_rank_score": 0.55},
    },
}


def _read_jsonl(path: Path) -> List[Dict[str, Any]]:
    if not path.exists():
        return []
    rows: List[Dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            row = json.loads(line)
        except Exception:
            continue
        if isinstance(row, dict):
            rows.append(row)
    return rows


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except Exception:
        return float(default)


def _normalize_source_name(name: str) -> str:
    src = str(name or "").strip().lower()
    if not src:
        return ""
    if src.startswith("semantic") or src in {"trigger", "bank"}:
        return "semantic"
    if src in {
        "cognitive",
        "self_awareness",
        "reasoning",
        "context",
        "wisdom",
        "meta_learning",
        "communication",
        "creativity",
    }:
        return "cognitive"
    if src in {"mind"}:
        return "mind"
    if src in {"chip", "chips"}:
        return "chips"
    if src in {"outcome", "outcomes"}:
        return "outcomes"
    if src in {"eidos"}:
        return "eidos"
    if src in {"orchestration"}:
        return "orchestration"
    return src


def _normalize_count_map(raw: Any) -> Dict[str, int]:
    out: Dict[str, int] = {}
    if not isinstance(raw, dict):
        return out
    for key, value in raw.items():
        name = _normalize_source_name(str(key or ""))
        if not name:
            continue
        try:
            count = max(0, int(value or 0))
        except Exception:
            count = 0
        out[name] = out.get(name, 0) + count
    return out


def _collect_engine_rows_since(path: Path, start_ts: float) -> List[Dict[str, Any]]:
    rows = []
    for row in _read_jsonl(path):
        ts = _safe_float(row.get("ts"), 0.0)
        if ts >= start_ts:
            rows.append(row)
    return rows


def normalize_text(text: str) -> str:
    out = " ".join(str(text or "").strip().lower().split())
    return out[:280]


def evaluate_text_expectations(
    text: str,
    expected_contains: Sequence[str],
    forbidden_contains: Sequence[str],
) -> Tuple[float, float]:
    lower = str(text or "").lower()
    expected = [str(x).strip().lower() for x in expected_contains if str(x).strip()]
    forbidden = [str(x).strip().lower() for x in forbidden_contains if str(x).strip()]

    expected_hits = sum(1 for frag in expected if frag in lower)
    forbidden_hits = sum(1 for frag in forbidden if frag in lower)

    expected_rate = expected_hits / max(1, len(expected)) if expected else 1.0
    forbidden_rate = forbidden_hits / max(1, len(forbidden)) if forbidden else 0.0
    return float(expected_rate), float(forbidden_rate)


def is_actionable(text: str) -> bool:
    lower = str(text or "").lower()
    if not lower.strip():
        return False
    hints = [
        "next check:",
        "`python ",
        "`rg ",
        "run ",
        "check ",
        "verify ",
        "ensure ",
    ]
    return any(h in lower for h in hints)


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
    emit_correct = 1.0 if bool(should_emit) == bool(emitted) else 0.0
    forbidden_clean = 1.0 - max(0.0, min(1.0, float(forbidden_hit_rate)))
    score = (
        (0.35 * emit_correct)
        + (0.20 * max(0.0, min(1.0, float(expected_hit_rate))))
        + (0.15 * forbidden_clean)
        + (0.10 * (1.0 if actionable else 0.0))
        + (0.10 * (1.0 if trace_bound else 0.0))
        + (0.10 * (1.0 if memory_utilized else 0.0))
    )
    return round(max(0.0, min(1.0, score)), 4)


def _extract_decision_event(rows: List[Dict[str, Any]], trace_id: str) -> Dict[str, Any]:
    candidates = []
    for row in rows:
        if str(row.get("trace_id") or "") != str(trace_id):
            continue
        event = str(row.get("event") or "")
        if event in {"emitted", "no_emit", "fallback_emit", "duplicate_suppressed", "synth_empty", "engine_error"}:
            candidates.append(row)
    if not candidates:
        return {}
    candidates.sort(key=lambda r: _safe_float(r.get("ts"), 0.0))
    return candidates[-1]


def _apply_advisor_profile(advisor_mod: Any, cfg: Dict[str, Any]) -> Dict[str, Any]:
    snap = {
        "MAX_ADVICE_ITEMS": int(getattr(advisor_mod, "MAX_ADVICE_ITEMS", 8)),
        "MIN_RANK_SCORE": float(getattr(advisor_mod, "MIN_RANK_SCORE", 0.35)),
    }
    if "max_items" in cfg:
        advisor_mod.MAX_ADVICE_ITEMS = max(1, int(cfg.get("max_items") or snap["MAX_ADVICE_ITEMS"]))
    if "max_advice_items" in cfg:
        advisor_mod.MAX_ADVICE_ITEMS = max(1, int(cfg.get("max_advice_items") or advisor_mod.MAX_ADVICE_ITEMS))
    if "min_rank_score" in cfg:
        advisor_mod.MIN_RANK_SCORE = max(0.0, min(1.0, float(cfg.get("min_rank_score") or snap["MIN_RANK_SCORE"])))
    return snap


def _restore_advisor_profile(advisor_mod: Any, snap: Dict[str, Any]) -> None:
    advisor_mod.MAX_ADVICE_ITEMS = int(snap.get("MAX_ADVICE_ITEMS", advisor_mod.MAX_ADVICE_ITEMS))
    advisor_mod.MIN_RANK_SCORE = float(snap.get("MIN_RANK_SCORE", advisor_mod.MIN_RANK_SCORE))


def load_cases(path: Path) -> List[AdvisoryCase]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    data = raw.get("cases", []) if isinstance(raw, dict) else raw
    if not isinstance(data, list):
        raise ValueError("cases file must contain a list or object with 'cases' list")

    cases: List[AdvisoryCase] = []
    for idx, row in enumerate(data):
        if not isinstance(row, dict):
            continue
        case_id = str(row.get("id") or row.get("case_id") or f"case_{idx + 1}")
        tool = str(row.get("tool") or "Read").strip() or "Read"
        prompt = str(row.get("prompt") or "").strip()
        if not prompt:
            continue
        tool_input = row.get("tool_input") if isinstance(row.get("tool_input"), dict) else {}
        should_emit = bool(row.get("should_emit", True))
        expected = [str(x) for x in (row.get("expected_contains") or []) if str(x).strip()]
        forbidden = [str(x) for x in (row.get("forbidden_contains") or []) if str(x).strip()]
        notes = str(row.get("notes") or "")
        cases.append(
            AdvisoryCase(
                case_id=case_id,
                tool=tool,
                prompt=prompt,
                tool_input=tool_input,
                should_emit=should_emit,
                expected_contains=expected,
                forbidden_contains=forbidden,
                notes=notes,
            )
        )
    return cases


def run_profile(
    *,
    profile_name: str,
    profile_cfg: Dict[str, Any],
    cases: List[AdvisoryCase],
    repeats: int,
    force_live: bool,
) -> Dict[str, Any]:
    from lib import advisory_engine
    from lib import advisory_gate
    from lib import advisory_packet_store
    from lib import advisor as advisor_mod

    spark_dir = Path.home() / ".spark"
    engine_log = spark_dir / "advisory_engine.jsonl"

    engine_snapshot = advisory_engine.get_engine_config()
    gate_snapshot = advisory_gate.get_gate_config()
    advisor_snapshot = _apply_advisor_profile(advisor_mod, {})
    lookup_exact = advisory_packet_store.lookup_exact
    lookup_relaxed = advisory_packet_store.lookup_relaxed

    try:
        advisory_engine.apply_engine_config(profile_cfg.get("advisory_engine") or {})
        advisory_gate.apply_gate_config(profile_cfg.get("advisory_gate") or {})
        advisor_snapshot = _apply_advisor_profile(advisor_mod, profile_cfg.get("advisor") or {})

        if force_live:
            advisory_packet_store.lookup_exact = lambda **_kwargs: None  # type: ignore[assignment]
            advisory_packet_store.lookup_relaxed = lambda **_kwargs: None  # type: ignore[assignment]

        results: List[CaseResult] = []
        latencies: List[float] = []
        emitted_texts: List[str] = []

        run_token = datetime.now(UTC).strftime("%Y%m%d%H%M%S") + "-" + uuid.uuid4().hex[:6]
        idx = 0
        for rep in range(max(1, repeats)):
            for case in cases:
                idx += 1
                session_id = f"advisory-bench-{profile_name}-{run_token}-{case.case_id}-{rep}"
                trace_id = f"advisory-bench-{profile_name}-{run_token}-{idx:04d}"
                start_ts = time.time()

                advisory_engine.on_user_prompt(session_id, case.prompt)
                text = advisory_engine.on_pre_tool(
                    session_id=session_id,
                    tool_name=case.tool,
                    tool_input=dict(case.tool_input or {}),
                    trace_id=trace_id,
                )
                advisory_engine.on_post_tool(
                    session_id=session_id,
                    tool_name=case.tool,
                    success=True,
                    tool_input=dict(case.tool_input or {}),
                    trace_id=trace_id,
                    error=None,
                )

                rows = _collect_engine_rows_since(engine_log, start_ts)
                event_row = _extract_decision_event(rows, trace_id)
                emitted = bool(text) or str(event_row.get("event") or "") in {"emitted", "fallback_emit"}
                route = str(event_row.get("route") or "unknown")
                event = str(event_row.get("event") or "unknown")
                error_code = str(event_row.get("error_code") or "")
                trace_bound = str(event_row.get("trace_id") or "") == trace_id
                emitted_text = str(text or event_row.get("emitted_text_preview") or "")

                expected_rate, forbidden_rate = evaluate_text_expectations(
                    emitted_text,
                    case.expected_contains,
                    case.forbidden_contains,
                )
                actionable = is_actionable(emitted_text)
                memory_source_counts = _normalize_count_map(event_row.get("source_counts"))
                advice_source_counts = _normalize_count_map(event_row.get("advice_source_counts"))
                source_counts: Dict[str, int] = {}
                for key, value in memory_source_counts.items():
                    source_counts[key] = source_counts.get(key, 0) + int(value)
                for key, value in advice_source_counts.items():
                    source_counts[key] = source_counts.get(key, 0) + int(value)
                memory_utilized = any(int(source_counts.get(k, 0) or 0) > 0 for k in ("cognitive", "semantic", "mind", "outcomes", "chips", "eidos"))
                score = score_case(
                    should_emit=case.should_emit,
                    emitted=emitted,
                    expected_hit_rate=expected_rate,
                    forbidden_hit_rate=forbidden_rate,
                    actionable=actionable,
                    trace_bound=trace_bound,
                    memory_utilized=memory_utilized,
                )
                if emitted_text:
                    emitted_texts.append(normalize_text(emitted_text))
                latencies.append(_safe_float(event_row.get("elapsed_ms"), 0.0))
                results.append(
                    CaseResult(
                        case_id=case.case_id,
                        tool=case.tool,
                        should_emit=case.should_emit,
                        emitted=emitted,
                        route=route,
                        event=event,
                        error_code=error_code,
                        trace_bound=trace_bound,
                        expected_hit_rate=round(expected_rate, 4),
                        forbidden_hit_rate=round(forbidden_rate, 4),
                        actionable=actionable,
                        memory_utilized=memory_utilized,
                        text_preview=(emitted_text.strip()[:220]),
                        score=score,
                        source_counts=source_counts,
                        advice_source_counts=advice_source_counts,
                    )
                )

        profile_summary = summarize_profile(profile_name=profile_name, case_results=results, latencies=latencies, emitted_texts=emitted_texts)
        return {
            "profile": profile_name,
            "config": {
                "advisory_engine": advisory_engine.get_engine_config(),
                "advisory_gate": advisory_gate.get_gate_config(),
                "advisor": {
                    "max_items": int(getattr(advisor_mod, "MAX_ADVICE_ITEMS", 0)),
                    "min_rank_score": float(getattr(advisor_mod, "MIN_RANK_SCORE", 0.0)),
                },
            },
            "summary": asdict(profile_summary),
            "cases": [asdict(r) for r in results],
        }
    finally:
        advisory_engine.apply_engine_config(engine_snapshot)
        advisory_gate.apply_gate_config(gate_snapshot)
        _restore_advisor_profile(advisor_mod, advisor_snapshot)
        advisory_packet_store.lookup_exact = lookup_exact  # type: ignore[assignment]
        advisory_packet_store.lookup_relaxed = lookup_relaxed  # type: ignore[assignment]


def summarize_profile(
    *,
    profile_name: str,
    case_results: Sequence[CaseResult],
    latencies: Sequence[float],
    emitted_texts: Sequence[str],
) -> ProfileSummary:
    if not case_results:
        return ProfileSummary(
            profile=profile_name,
            case_count=0,
            score=0.0,
            emit_accuracy=0.0,
            emit_rate=0.0,
            no_emit_rate=0.0,
            expected_hit_rate=0.0,
            forbidden_clean_rate=0.0,
            actionability_rate=0.0,
            trace_bound_rate=0.0,
            memory_utilization_rate=0.0,
            repetition_penalty_rate=0.0,
            fallback_share_pct=0.0,
            p50_latency_ms=0.0,
            p95_latency_ms=0.0,
            top_error_codes=[],
            no_emit_error_codes=[],
            route_counts={},
        )

    total = float(len(case_results))
    emit_correct = sum(1 for r in case_results if bool(r.emitted) == bool(r.should_emit))
    emitted = sum(1 for r in case_results if r.emitted)
    no_emit = sum(1 for r in case_results if not r.emitted)
    expected_avg = statistics.fmean([r.expected_hit_rate for r in case_results])
    forbidden_avg = statistics.fmean([r.forbidden_hit_rate for r in case_results])
    actionability = sum(1 for r in case_results if r.actionable)
    trace_bound = sum(1 for r in case_results if r.trace_bound)
    memory_used = sum(1 for r in case_results if r.memory_utilized)

    route_counts: Dict[str, int] = {}
    error_counts: Dict[str, int] = {}
    no_emit_error_counts: Dict[str, int] = {}
    fallback_count = 0
    for r in case_results:
        route_counts[r.route] = route_counts.get(r.route, 0) + 1
        if r.error_code:
            error_counts[r.error_code] = error_counts.get(r.error_code, 0) + 1
            if not r.emitted:
                no_emit_error_counts[r.error_code] = no_emit_error_counts.get(r.error_code, 0) + 1
        if r.event == "fallback_emit":
            fallback_count += 1

    # Repetition penalty: repeated emitted advisories reduce final score.
    repeat_penalty = 0.0
    if emitted_texts:
        counts: Dict[str, int] = {}
        for text in emitted_texts:
            counts[text] = counts.get(text, 0) + 1
        repeats = sum(max(0, c - 1) for c in counts.values())
        repeat_penalty = repeats / max(1, len(emitted_texts))

    score = statistics.fmean([r.score for r in case_results])
    score *= (1.0 - (0.20 * min(1.0, repeat_penalty)))
    score = round(max(0.0, min(1.0, score)), 4)

    ls = sorted(float(v) for v in latencies if v is not None)
    p50 = ls[len(ls) // 2] if ls else 0.0
    p95 = ls[min(len(ls) - 1, int(len(ls) * 0.95))] if ls else 0.0

    top_error_codes = sorted(error_counts.items(), key=lambda x: x[1], reverse=True)[:5]
    no_emit_error_codes = sorted(no_emit_error_counts.items(), key=lambda x: x[1], reverse=True)[:5]
    return ProfileSummary(
        profile=profile_name,
        case_count=int(total),
        score=score,
        emit_accuracy=round(emit_correct / total, 4),
        emit_rate=round(emitted / total, 4),
        no_emit_rate=round(no_emit / total, 4),
        expected_hit_rate=round(expected_avg, 4),
        forbidden_clean_rate=round(1.0 - forbidden_avg, 4),
        actionability_rate=round(actionability / total, 4),
        trace_bound_rate=round(trace_bound / total, 4),
        memory_utilization_rate=round(memory_used / total, 4),
        repetition_penalty_rate=round(repeat_penalty, 4),
        fallback_share_pct=round((fallback_count / max(1, emitted)) * 100.0, 2),
        p50_latency_ms=round(p50, 2),
        p95_latency_ms=round(p95, 2),
        top_error_codes=top_error_codes,
        no_emit_error_codes=no_emit_error_codes,
        route_counts=route_counts,
    )


def _rank_profiles(profile_runs: Sequence[Dict[str, Any]]) -> List[Dict[str, Any]]:
    ordered = sorted(profile_runs, key=lambda r: float((r.get("summary") or {}).get("score", 0.0)), reverse=True)
    return ordered


def _report_markdown(report: Dict[str, Any]) -> str:
    lines: List[str] = []
    lines.append(f"# Advisory Quality A/B Report ({report.get('generated_at', '')})")
    lines.append("")
    lines.append(f"- Cases: `{report.get('case_count', 0)}`")
    lines.append(f"- Repeats per case: `{report.get('repeats', 1)}`")
    lines.append(f"- Force live path: `{report.get('force_live', True)}`")
    lines.append("")
    lines.append("## Ranking")
    lines.append("")
    lines.append("| Rank | Profile | Score | Emit Acc | Emit Rate | No-Emit | Actionability | Trace | Memory | Repeat Penalty |")
    lines.append("|---|---|---:|---:|---:|---:|---:|---:|---:|---:|")
    for idx, run in enumerate(report.get("ranked_profiles", []), start=1):
        s = run.get("summary") or {}
        lines.append(
            f"| {idx} | `{run.get('profile','')}` | {float(s.get('score', 0.0)):.4f} | "
            f"{float(s.get('emit_accuracy', 0.0)):.2%} | {float(s.get('emit_rate', 0.0)):.2%} | "
            f"{float(s.get('no_emit_rate', 0.0)):.2%} | {float(s.get('actionability_rate', 0.0)):.2%} | "
            f"{float(s.get('trace_bound_rate', 0.0)):.2%} | {float(s.get('memory_utilization_rate', 0.0)):.2%} | "
            f"{float(s.get('repetition_penalty_rate', 0.0)):.2%} |"
        )
    lines.append("")
    lines.append("## No-Emit Reasons")
    lines.append("")
    for run in report.get("ranked_profiles", []):
        s = run.get("summary") or {}
        reasons = s.get("no_emit_error_codes") or []
        reason_text = ", ".join([f"{code}:{count}" for code, count in reasons]) if reasons else "none"
        lines.append(f"- `{run.get('profile','')}`: {reason_text}")
    lines.append("")
    winner = report.get("winner") or {}
    lines.append(f"## Winner: `{winner.get('profile', 'n/a')}`")
    lines.append("")
    s = winner.get("summary") or {}
    lines.append(f"- Score: `{float(s.get('score', 0.0)):.4f}`")
    lines.append(f"- Emit accuracy: `{float(s.get('emit_accuracy', 0.0)):.2%}`")
    lines.append(f"- No-emit rate: `{float(s.get('no_emit_rate', 0.0)):.2%}`")
    lines.append(f"- Actionability: `{float(s.get('actionability_rate', 0.0)):.2%}`")
    lines.append(f"- Trace-bound rate: `{float(s.get('trace_bound_rate', 0.0)):.2%}`")
    lines.append(f"- Memory utilization: `{float(s.get('memory_utilization_rate', 0.0)):.2%}`")
    lines.append("")
    return "\n".join(lines).strip() + "\n"


def run_benchmark(
    *,
    cases_path: Path,
    profiles: Dict[str, Dict[str, Any]],
    profile_names: Sequence[str],
    repeats: int,
    force_live: bool,
) -> Dict[str, Any]:
    cases = load_cases(cases_path)
    selected = [name for name in profile_names if name in profiles]
    if not selected:
        raise ValueError("no valid profiles selected")

    profile_runs: List[Dict[str, Any]] = []
    for name in selected:
        profile_runs.append(
            run_profile(
                profile_name=name,
                profile_cfg=profiles.get(name) or {},
                cases=cases,
                repeats=repeats,
                force_live=force_live,
            )
        )

    ranked = _rank_profiles(profile_runs)
    return {
        "generated_at": datetime.now(UTC).isoformat(),
        "cases_path": str(cases_path),
        "case_count": len(cases),
        "repeats": int(repeats),
        "force_live": bool(force_live),
        "profiles": {name: profiles.get(name) for name in selected},
        "profile_runs": profile_runs,
        "ranked_profiles": ranked,
        "winner": ranked[0] if ranked else {},
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="A/B benchmark for advisory quality")
    ap.add_argument(
        "--cases",
        default=str(Path("benchmarks") / "data" / "advisory_quality_eval_seed.json"),
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
    ap.add_argument(
        "--force-live",
        action="store_true",
        help="Bypass packet lookup and force live advisory retrieval path",
    )
    ap.add_argument(
        "--out-prefix",
        default="advisory_quality_ab",
        help="Output file prefix under benchmarks/out",
    )
    args = ap.parse_args()

    profiles = dict(DEFAULT_PROFILE_PRESETS)
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
    report = run_benchmark(
        cases_path=Path(args.cases),
        profiles=profiles,
        profile_names=names,
        repeats=max(1, int(args.repeats)),
        force_live=bool(args.force_live),
    )

    out_dir = Path("benchmarks") / "out"
    out_dir.mkdir(parents=True, exist_ok=True)
    json_path = out_dir / f"{args.out_prefix}_report.json"
    md_path = out_dir / f"{args.out_prefix}_report.md"
    json_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    md_path.write_text(_report_markdown(report), encoding="utf-8")

    print(f"Wrote: {json_path}")
    print(f"Wrote: {md_path}")
    winner = report.get("winner") or {}
    summary = winner.get("summary") or {}
    print(
        f"Winner={winner.get('profile', 'n/a')} "
        f"score={float(summary.get('score', 0.0)):.4f} "
        f"emit_acc={float(summary.get('emit_accuracy', 0.0)):.2%} "
        f"no_emit={float(summary.get('no_emit_rate', 0.0)):.2%}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
