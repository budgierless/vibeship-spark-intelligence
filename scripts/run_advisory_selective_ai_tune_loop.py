#!/usr/bin/env python3
"""Run a 3-pass selective-AI tune loop and apply the best candidate."""

from __future__ import annotations

import argparse
import json
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
    no_advice = int(events.get("no_advice", 0))
    p95 = float(latency.get("p95_ms", 0.0))
    p50 = float(latency.get("p50_ms", 0.0))
    selective_hits = int(emitted_synth.get("selective_ai_auto", 0))
    forced_hits = int(emitted_synth.get("programmatic_forced", 0))
    gate_supp = int(error_codes.get("AE_GATE_SUPPRESSED", 0))

    # Reward emissions and selective-hit coverage; penalize latency and suppression.
    score = 0.0
    score += emitted * 12.0
    score += selective_hits * 8.0
    score += forced_hits * 2.0
    score -= no_emit * 1.5
    score -= no_advice * 2.0
    score -= gate_supp * 1.0

    if p95 > 1500.0:
        score -= (p95 - 1500.0) / 25.0
    if p95 > 3500.0:
        score -= 250.0
    if p50 > 900.0:
        score -= (p50 - 900.0) / 20.0

    metrics = {
        "emitted": emitted,
        "no_emit": no_emit,
        "no_advice": no_advice,
        "p50_ms": round(p50, 2),
        "p95_ms": round(p95, 2),
        "selective_hits": selective_hits,
        "programmatic_forced_hits": forced_hits,
        "gate_suppressed": gate_supp,
        "score": round(score, 3),
    }
    return score, metrics


def _apply_candidate(tuneables: Dict[str, Any], candidate: Candidate) -> Dict[str, Any]:
    out = dict(tuneables)
    advisory_engine = dict(out.get("advisory_engine") or {})
    advisory_engine["force_programmatic_synth"] = bool(candidate.force_programmatic_synth)
    advisory_engine["selective_ai_synth_enabled"] = bool(candidate.selective_ai_synth_enabled)
    advisory_engine["selective_ai_min_authority"] = str(candidate.selective_ai_min_authority)
    advisory_engine["selective_ai_min_remaining_ms"] = int(candidate.selective_ai_min_remaining_ms)
    out["advisory_engine"] = advisory_engine
    out["updated_at"] = datetime.now(UTC).isoformat()
    return out


def _run_candidate(
    candidate: Candidate,
    rounds: int,
    out_dir: Path,
    py_exec: str,
) -> Dict[str, Any]:
    stamp = _utc_stamp()
    out_json = out_dir / f"{stamp}_{candidate.name}_selective_loop.json"
    cmd = [
        py_exec,
        "scripts/advisory_controlled_delta.py",
        "--rounds",
        str(rounds),
        "--label",
        f"selective_loop_{candidate.name}",
        "--force-live",
        "--prompt-mode",
        "vary",
        "--tool-input-mode",
        "repo",
        "--out",
        str(out_json),
    ]
    subprocess.run(cmd, check=True)
    summary = _read_json(out_json)
    return {"artifact": str(out_json), "summary": summary}


def _render_report(result: Dict[str, Any]) -> str:
    lines: List[str] = []
    lines.append("# Selective-AI Tune Loop Report")
    lines.append("")
    lines.append(f"- Generated (UTC): `{result['generated_at_utc']}`")
    lines.append(f"- Rounds per pass: `{result['rounds']}`")
    lines.append(f"- Tuneables backup: `{result['tuneables_backup']}`")
    lines.append(f"- Winner: `{result['winner']['candidate']['name']}`")
    lines.append("")
    lines.append("## Pass Results")
    lines.append("")
    for row in result["passes"]:
        m = row["metrics"]
        cfg = row["candidate"]
        lines.append(f"### {row['candidate']['name']}")
        lines.append(f"- artifact: `{row['artifact']}`")
        lines.append(
            f"- config: authority=`{cfg['selective_ai_min_authority']}`, "
            f"min_remaining_ms=`{cfg['selective_ai_min_remaining_ms']}`, "
            f"force_programmatic=`{cfg['force_programmatic_synth']}`"
        )
        lines.append(
            f"- metrics: emitted={m['emitted']}, selective_hits={m['selective_hits']}, "
            f"p50={m['p50_ms']}ms, p95={m['p95_ms']}ms, no_emit={m['no_emit']}, score={m['score']}"
        )
        lines.append("")
    lines.append("## Applied Runtime Config")
    lines.append("")
    winner_cfg = result["winner"]["candidate"]
    lines.append(f"- `force_programmatic_synth={winner_cfg['force_programmatic_synth']}`")
    lines.append(f"- `selective_ai_synth_enabled={winner_cfg['selective_ai_synth_enabled']}`")
    lines.append(f"- `selective_ai_min_authority={winner_cfg['selective_ai_min_authority']}`")
    lines.append(f"- `selective_ai_min_remaining_ms={winner_cfg['selective_ai_min_remaining_ms']}`")
    lines.append("")
    return "\n".join(lines).strip() + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--rounds", type=int, default=120)
    parser.add_argument("--out-dir", type=Path, default=Path("docs/reports"))
    args = parser.parse_args()

    py_exec = sys.executable
    rounds = max(20, int(args.rounds))
    out_dir = args.out_dir
    out_dir.mkdir(parents=True, exist_ok=True)

    tuneables_path = Path.home() / ".spark" / "tuneables.json"
    if not tuneables_path.exists():
        raise FileNotFoundError(f"Tuneables not found: {tuneables_path}")

    tuneables_original = _read_json(tuneables_path)
    backup_dir = Path.home() / ".spark" / "backups"
    backup_dir.mkdir(parents=True, exist_ok=True)
    backup_path = backup_dir / f"tuneables.json.selective_loop_{_utc_stamp()}.bak"
    shutil.copy2(tuneables_path, backup_path)

    candidates = [
        Candidate(name="pass1_warning_1800", selective_ai_min_authority="warning", selective_ai_min_remaining_ms=1800),
        Candidate(name="pass2_note_1800", selective_ai_min_authority="note", selective_ai_min_remaining_ms=1800),
        Candidate(name="pass3_note_2400", selective_ai_min_authority="note", selective_ai_min_remaining_ms=2400),
    ]

    pass_rows: List[Dict[str, Any]] = []
    for candidate in candidates:
        tuned = _apply_candidate(tuneables_original, candidate)
        _write_json(tuneables_path, tuned)
        run = _run_candidate(candidate, rounds=rounds, out_dir=out_dir, py_exec=py_exec)
        score, metrics = _score(run["summary"])
        pass_rows.append(
            {
                "candidate": candidate.__dict__,
                "artifact": run["artifact"],
                "score": score,
                "metrics": metrics,
            }
        )

    winner = sorted(pass_rows, key=lambda r: r["score"], reverse=True)[0]
    winner_candidate = Candidate(**winner["candidate"])
    tuned_winner = _apply_candidate(tuneables_original, winner_candidate)
    _write_json(tuneables_path, tuned_winner)

    result = {
        "generated_at_utc": datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S"),
        "rounds": rounds,
        "tuneables_backup": str(backup_path),
        "passes": pass_rows,
        "winner": winner,
    }

    out_json = out_dir / f"{_utc_stamp()}_selective_ai_tune_loop_result.json"
    out_md = out_dir / f"{_utc_stamp()}_selective_ai_tune_loop_report.md"
    _write_json(out_json, result)
    out_md.write_text(_render_report(result), encoding="utf-8")

    print(f"Wrote {out_json}")
    print(f"Wrote {out_md}")
    print(f"Winner: {winner_candidate.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
