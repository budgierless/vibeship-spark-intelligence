#!/usr/bin/env python3
"""Run a 3-pass selective-AI tune loop on non-benchmark probe traffic."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Dict, List, Tuple


@dataclass
class Candidate:
    name: str
    selective_ai_min_authority: str
    selective_ai_min_remaining_ms: int
    note_threshold: float
    whisper_threshold: float
    ai_timeout_s: float
    force_programmatic_synth: bool = True
    selective_ai_synth_enabled: bool = True


def _utc_stamp() -> str:
    return datetime.now(UTC).strftime("%Y%m%d_%H%M%S")


def _read_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _write_json(path: Path, data: Dict[str, Any]) -> None:
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")


def _score(summary: Dict[str, Any]) -> Tuple[float, Dict[str, Any]]:
    engine = summary.get("engine") or {}
    latency = engine.get("latency") or {}
    events = engine.get("events") or {}
    emitted_synth = engine.get("emitted_synth_policy_counts") or {}
    error_codes = engine.get("error_codes") or {}

    emitted = int(events.get("emitted", 0))
    no_emit = int(events.get("no_emit", 0))
    synth_empty = int(events.get("synth_empty", 0))
    global_dedupe_suppressed = int(events.get("global_dedupe_suppressed", 0))
    no_advice = int(events.get("no_advice", 0))
    p50 = float(latency.get("p50_ms", 0.0))
    p95 = float(latency.get("p95_ms", 0.0))
    selective_hits = int(emitted_synth.get("selective_ai_auto", 0))
    forced_hits = int(emitted_synth.get("programmatic_forced", 0))
    gate_supp = int(error_codes.get("AE_GATE_SUPPRESSED", 0))

    score = 0.0
    score += emitted * 10.0
    score += selective_hits * 14.0
    score += forced_hits * 1.5
    score -= no_emit * 2.0
    score -= synth_empty * 1.5
    score -= global_dedupe_suppressed * 2.0
    score -= no_advice * 2.0
    score -= gate_supp * 1.0

    # Prevent all-suppressed profiles from "winning" by being idle.
    if emitted <= 0:
        score -= 250.0
    elif emitted < 3:
        score -= 30.0

    # Latency guard: strongly penalize long tails on AI-enabled paths.
    if p95 > 1500.0:
        score -= (p95 - 1500.0) / 20.0
    if p95 > 3500.0:
        score -= 300.0
    if p50 > 1000.0:
        score -= (p50 - 1000.0) / 20.0

    metrics = {
        "emitted": emitted,
        "no_emit": no_emit,
        "synth_empty": synth_empty,
        "global_dedupe_suppressed": global_dedupe_suppressed,
        "no_advice": no_advice,
        "p50_ms": round(p50, 2),
        "p95_ms": round(p95, 2),
        "selective_hits": selective_hits,
        "programmatic_forced_hits": forced_hits,
        "gate_suppressed": gate_supp,
        "viable_live_profile": bool(emitted > 0 and p95 > 0 and p95 <= 1500.0),
        "score": round(score, 3),
    }
    return score, metrics


def _reset_dedupe_logs() -> None:
    spark_dir = Path.home() / ".spark"
    for name in ("advisory_global_dedupe.jsonl", "advisory_low_auth_dedupe.jsonl"):
        path = spark_dir / name
        try:
            if path.exists():
                path.unlink()
        except Exception:
            pass


def _apply_candidate(tuneables: Dict[str, Any], candidate: Candidate) -> Dict[str, Any]:
    out = dict(tuneables)
    advisory_engine = dict(out.get("advisory_engine") or {})
    advisory_engine["force_programmatic_synth"] = bool(candidate.force_programmatic_synth)
    advisory_engine["selective_ai_synth_enabled"] = bool(candidate.selective_ai_synth_enabled)
    advisory_engine["selective_ai_min_authority"] = str(candidate.selective_ai_min_authority)
    advisory_engine["selective_ai_min_remaining_ms"] = int(candidate.selective_ai_min_remaining_ms)
    out["advisory_engine"] = advisory_engine
    advisory_gate = dict(out.get("advisory_gate") or {})
    advisory_gate["note_threshold"] = float(candidate.note_threshold)
    advisory_gate["whisper_threshold"] = float(candidate.whisper_threshold)
    out["advisory_gate"] = advisory_gate
    synthesizer = dict(out.get("synthesizer") or {})
    synthesizer["ai_timeout_s"] = max(0.2, float(candidate.ai_timeout_s))
    out["synthesizer"] = synthesizer
    out["updated_at"] = datetime.now(UTC).isoformat()
    return out


def _run_candidate(
    candidate: Candidate,
    rounds: int,
    out_dir: Path,
    py_exec: str,
) -> Dict[str, Any]:
    stamp = _utc_stamp()
    out_json = out_dir / f"{stamp}_{candidate.name}_live_probe_loop.json"
    session_prefix = f"advisory-liveprobe-{candidate.name}"
    trace_prefix = f"liveprobe-{candidate.name}-{stamp}"
    cmd = [
        py_exec,
        "scripts/advisory_controlled_delta.py",
        "--rounds",
        str(rounds),
        "--label",
        f"live_probe_{candidate.name}",
        "--session-prefix",
        session_prefix,
        "--trace-prefix",
        trace_prefix,
        "--force-live",
        "--prompt-mode",
        "vary",
        "--tool-input-mode",
        "repo",
        "--out",
        str(out_json),
    ]
    env = dict(os.environ)
    env["SPARK_SYNTH_TIMEOUT"] = str(max(0.2, float(candidate.ai_timeout_s)))
    subprocess.run(cmd, check=True, env=env)
    summary = _read_json(out_json)
    return {
        "artifact": str(out_json),
        "summary": summary,
        "session_prefix": session_prefix,
        "trace_prefix": trace_prefix,
    }


def _render_report(result: Dict[str, Any]) -> str:
    lines: List[str] = []
    lines.append("# Selective-AI Live Probe Tune Loop Report")
    lines.append("")
    lines.append(f"- Generated (UTC): `{result['generated_at_utc']}`")
    lines.append(f"- Rounds per pass: `{result['rounds']}`")
    lines.append(
        f"- Dedupe history preserved between passes: `{result.get('dedupe_history_preserved', False)}`"
    )
    lines.append(f"- Tuneables backup: `{result['tuneables_backup']}`")
    lines.append(f"- Winner: `{result['winner']['candidate']['name']}`")
    lines.append(f"- Winner reason: `{result.get('winner_reason', 'best_score')}`")
    lines.append("")
    lines.append("## Pass Results")
    lines.append("")
    for row in result["passes"]:
        cfg = row["candidate"]
        m = row["metrics"]
        lines.append(f"### {cfg['name']}")
        lines.append(f"- artifact: `{row['artifact']}`")
        lines.append(
            f"- probe ids: session_prefix=`{row['session_prefix']}`, trace_prefix=`{row['trace_prefix']}`"
        )
        lines.append(
            f"- config: authority=`{cfg['selective_ai_min_authority']}`, "
            f"min_remaining_ms=`{cfg['selective_ai_min_remaining_ms']}`, "
            f"note_threshold=`{cfg['note_threshold']}`, whisper_threshold=`{cfg['whisper_threshold']}`, "
            f"ai_timeout_s=`{cfg['ai_timeout_s']}`"
        )
        lines.append(
            f"- metrics: emitted={m['emitted']}, selective_hits={m['selective_hits']}, "
            f"programmatic_forced={m['programmatic_forced_hits']}, "
            f"p50={m['p50_ms']}ms, p95={m['p95_ms']}ms, no_emit={m['no_emit']}, "
            f"viable_live_profile={m.get('viable_live_profile', False)}, score={m['score']}"
        )
        lines.append("")
    lines.append("## Applied Runtime Config")
    lines.append("")
    winner_cfg = result["winner"]["candidate"]
    lines.append(f"- `force_programmatic_synth={winner_cfg['force_programmatic_synth']}`")
    lines.append(f"- `selective_ai_synth_enabled={winner_cfg['selective_ai_synth_enabled']}`")
    lines.append(f"- `selective_ai_min_authority={winner_cfg['selective_ai_min_authority']}`")
    lines.append(f"- `selective_ai_min_remaining_ms={winner_cfg['selective_ai_min_remaining_ms']}`")
    lines.append(f"- `advisory_gate.note_threshold={winner_cfg['note_threshold']}`")
    lines.append(f"- `advisory_gate.whisper_threshold={winner_cfg['whisper_threshold']}`")
    lines.append(f"- `synthesizer.ai_timeout_s={winner_cfg['ai_timeout_s']}`")
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--rounds", type=int, default=80)
    parser.add_argument("--out-dir", type=Path, default=Path("docs/reports"))
    parser.add_argument(
        "--preserve-dedupe-history",
        action="store_true",
        help="Do not clear global/low-auth dedupe logs between candidate passes.",
    )
    args = parser.parse_args()

    rounds = max(20, int(args.rounds))
    out_dir = args.out_dir
    out_dir.mkdir(parents=True, exist_ok=True)

    tuneables_path = Path.home() / ".spark" / "tuneables.json"
    if not tuneables_path.exists():
        raise FileNotFoundError(f"Tuneables not found: {tuneables_path}")
    tuneables_original = _read_json(tuneables_path)

    backup_dir = Path.home() / ".spark" / "backups"
    backup_dir.mkdir(parents=True, exist_ok=True)
    backup_path = backup_dir / f"tuneables.json.live_probe_loop_{_utc_stamp()}.bak"
    shutil.copy2(tuneables_path, backup_path)

    candidates = [
        Candidate("probe_pass1_note_1400_gate050_t12", "note", 1400, 0.50, 0.35, 1.2),
        Candidate("probe_pass2_note_1400_gate035_t09", "note", 1400, 0.35, 0.25, 0.9),
        Candidate("probe_pass3_warning_1800_gate035_t09", "warning", 1800, 0.35, 0.25, 0.9),
    ]

    py_exec = sys.executable
    pass_rows: List[Dict[str, Any]] = []
    for candidate in candidates:
        if not bool(args.preserve_dedupe_history):
            _reset_dedupe_logs()
        tuned = _apply_candidate(tuneables_original, candidate)
        _write_json(tuneables_path, tuned)
        run = _run_candidate(
            candidate,
            rounds=rounds,
            out_dir=out_dir,
            py_exec=py_exec,
        )
        score, metrics = _score(run["summary"])
        pass_rows.append(
            {
                "candidate": candidate.__dict__,
                "artifact": run["artifact"],
                "session_prefix": run["session_prefix"],
                "trace_prefix": run["trace_prefix"],
                "score": score,
                "metrics": metrics,
            }
        )

    viable = [
        row
        for row in pass_rows
        if bool((row.get("metrics") or {}).get("viable_live_profile"))
    ]
    if viable:
        winner = sorted(viable, key=lambda r: r["score"], reverse=True)[0]
        winner_reason = "best_viable_profile"
    else:
        winner = next(
            (
                row
                for row in pass_rows
                if str((row.get("candidate") or {}).get("selective_ai_min_authority", "")).lower()
                == "warning"
            ),
            sorted(pass_rows, key=lambda r: r["score"], reverse=True)[0],
        )
        winner_reason = "no_viable_profile_fallback_to_conservative"
    winner_candidate = Candidate(**winner["candidate"])
    winner_tuneables = _apply_candidate(tuneables_original, winner_candidate)
    _write_json(tuneables_path, winner_tuneables)

    result = {
        "generated_at_utc": datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S"),
        "rounds": rounds,
        "dedupe_history_preserved": bool(args.preserve_dedupe_history),
        "tuneables_backup": str(backup_path),
        "passes": pass_rows,
        "winner": winner,
        "winner_reason": winner_reason,
    }

    stamp = _utc_stamp()
    out_json = out_dir / f"{stamp}_selective_ai_live_probe_loop_result.json"
    out_md = out_dir / f"{stamp}_selective_ai_live_probe_loop_report.md"
    _write_json(out_json, result)
    out_md.write_text(_render_report(result), encoding="utf-8")

    print(f"Wrote {out_json}")
    print(f"Wrote {out_md}")
    print(f"Winner: {winner_candidate.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
