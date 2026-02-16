#!/usr/bin/env python3
"""Apply tuned advisory retrieval config, run canary benchmarks, rollback on gate failure."""

from __future__ import annotations

import argparse
import importlib.util
import json
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Tuple


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MEMORY_CASES = ROOT / "benchmarks" / "data" / "memory_retrieval_eval_multidomain_real_user_2026_02_16.json"
DEFAULT_MEMORY_GATES = ROOT / "benchmarks" / "data" / "memory_retrieval_domain_gates_multidomain_v1.json"
DEFAULT_ADVISORY_CASES = ROOT / "benchmarks" / "data" / "advisory_quality_eval_seed.json"
DEFAULT_TUNEABLES = Path.home() / ".spark" / "tuneables.json"


def _load_json(path: Path) -> Dict[str, Any]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError(f"expected JSON object: {path}")
    return raw


def _load_apply_module():
    path = ROOT / "scripts" / "apply_advisory_wow_tuneables.py"
    spec = importlib.util.spec_from_file_location("apply_advisory_wow_tuneables", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("failed to load apply_advisory_wow_tuneables")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _run(cmd: list[str], *, timeout_s: int) -> Tuple[int, str]:
    proc = subprocess.run(
        cmd,
        cwd=str(ROOT),
        text=True,
        capture_output=True,
        timeout=max(30, int(timeout_s)),
        check=False,
    )
    output = (proc.stdout or "") + ("\n" + proc.stderr if proc.stderr else "")
    return int(proc.returncode), output.strip()


def _evaluate(
    *,
    memory_report: Dict[str, Any],
    advisory_report: Dict[str, Any],
    mrr_min: float,
    gate_pass_rate_min: float,
    advisory_score_min: float,
) -> Dict[str, Any]:
    weighted = memory_report.get("weighted") or {}
    mem_mrr = float(weighted.get("mrr", 0.0) or 0.0)
    mem_gate_pass = float(weighted.get("domain_gate_pass_rate", 0.0) or 0.0)
    winner = advisory_report.get("winner") or {}
    adv_summary = winner.get("summary") or {}
    adv_score = float(adv_summary.get("score", 0.0) or 0.0)
    checks = {
        "memory_mrr_min": mem_mrr >= float(mrr_min),
        "memory_gate_pass_rate_min": mem_gate_pass >= float(gate_pass_rate_min),
        "advisory_score_min": adv_score >= float(advisory_score_min),
    }
    return {
        "checks": checks,
        "all_pass": all(checks.values()),
        "metrics": {
            "memory_weighted_mrr": mem_mrr,
            "memory_domain_gate_pass_rate": mem_gate_pass,
            "advisory_winner_score": adv_score,
            "advisory_winner_profile": str(winner.get("profile") or "n/a"),
        },
    }


def _render_md(report: Dict[str, Any]) -> str:
    e = report.get("evaluation") or {}
    m = e.get("metrics") or {}
    checks = e.get("checks") or {}
    lines = []
    lines.append("# Advisory Retrieval Canary Report")
    lines.append("")
    lines.append(f"- Timestamp: `{report.get('generated_at', '')}`")
    lines.append(f"- Status: `{report.get('status', '')}`")
    lines.append(f"- Tuneables path: `{report.get('tuneables_path', '')}`")
    lines.append(f"- Backup path: `{report.get('backup_path', '')}`")
    lines.append("")
    lines.append("## Metrics")
    lines.append("")
    lines.append(f"- Memory weighted MRR: `{float(m.get('memory_weighted_mrr', 0.0)):.4f}`")
    lines.append(f"- Memory domain gate pass rate: `{float(m.get('memory_domain_gate_pass_rate', 0.0)):.2%}`")
    lines.append(f"- Advisory winner score: `{float(m.get('advisory_winner_score', 0.0)):.4f}`")
    lines.append(f"- Advisory winner profile: `{m.get('advisory_winner_profile', 'n/a')}`")
    lines.append("")
    lines.append("## Checks")
    lines.append("")
    for key, ok in checks.items():
        lines.append(f"- `{key}`: `{'PASS' if ok else 'FAIL'}`")
    lines.append("")
    return "\n".join(lines).strip() + "\n"


def main() -> int:
    ap = argparse.ArgumentParser(description="Run advisory/retrieval canary and rollback on gate failure")
    ap.add_argument("--tuneables", default=str(DEFAULT_TUNEABLES))
    ap.add_argument("--retrieval-level", default="2")
    ap.add_argument("--memory-cases", default=str(DEFAULT_MEMORY_CASES))
    ap.add_argument("--memory-gates", default=str(DEFAULT_MEMORY_GATES))
    ap.add_argument("--advisory-cases", default=str(DEFAULT_ADVISORY_CASES))
    ap.add_argument("--memory-mrr-min", type=float, default=0.35)
    ap.add_argument("--memory-gate-pass-rate-min", type=float, default=0.60)
    ap.add_argument("--advisory-score-min", type=float, default=0.70)
    ap.add_argument("--timeout-s", type=int, default=1200)
    ap.add_argument("--no-rollback", action="store_true", help="Do not rollback tuneables on failure")
    ap.add_argument(
        "--build-multidomain-if-missing",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Build multidomain retrieval cases if the configured memory case file is missing",
    )
    args = ap.parse_args()

    memory_cases = Path(args.memory_cases)
    memory_gates = Path(args.memory_gates)
    advisory_cases = Path(args.advisory_cases)
    tuneables_path = Path(args.tuneables)
    tuneables_path.parent.mkdir(parents=True, exist_ok=True)

    if not memory_cases.exists() and bool(args.build_multidomain_if_missing):
        rc, out = _run(
            [sys.executable, str(ROOT / "scripts" / "build_multidomain_memory_retrieval_cases.py"), "--out", str(memory_cases)],
            timeout_s=max(60, int(args.timeout_s)),
        )
        if rc != 0:
            print(out, file=sys.stderr)
            return rc
    if not memory_cases.exists():
        raise FileNotFoundError(f"missing memory cases: {memory_cases}")
    if not memory_gates.exists():
        raise FileNotFoundError(f"missing memory gates: {memory_gates}")
    if not advisory_cases.exists():
        raise FileNotFoundError(f"missing advisory cases: {advisory_cases}")

    apply_mod = _load_apply_module()
    patch = apply_mod.build_recommended_patch(str(args.retrieval_level))
    merge_fn = apply_mod._deep_merge

    now = datetime.now(timezone.utc)
    stamp = now.strftime("%Y%m%d_%H%M%S")
    backup_path = tuneables_path.with_name(f"tuneables.canary_backup_{stamp}.json")
    existing = {}
    if tuneables_path.exists():
        existing = _load_json(tuneables_path)
        shutil.copyfile(tuneables_path, backup_path)
    else:
        backup_path.write_text("{}", encoding="utf-8")
    merged = merge_fn(existing, patch)
    tuneables_path.write_text(json.dumps(merged, indent=2), encoding="utf-8")

    mem_prefix = f"memory_retrieval_domain_matrix_canary_{stamp}"
    adv_prefix = f"advisory_quality_canary_{stamp}"
    mem_cmd = [
        sys.executable,
        str(ROOT / "benchmarks" / "memory_retrieval_domain_matrix.py"),
        "--cases",
        str(memory_cases),
        "--gate-file",
        str(memory_gates),
        "--out-prefix",
        mem_prefix,
    ]
    adv_cmd = [
        sys.executable,
        str(ROOT / "benchmarks" / "advisory_quality_ab.py"),
        "--cases",
        str(advisory_cases),
        "--profiles",
        "baseline,balanced,strict",
        "--repeats",
        "1",
        "--force-live",
        "--suppress-emit-output",
        "--out-prefix",
        adv_prefix,
    ]

    mem_rc, mem_out = _run(mem_cmd, timeout_s=int(args.timeout_s))
    if mem_rc != 0:
        print(mem_out, file=sys.stderr)
        if not bool(args.no_rollback):
            shutil.copyfile(backup_path, tuneables_path)
        return mem_rc
    adv_rc, adv_out = _run(adv_cmd, timeout_s=int(args.timeout_s))
    if adv_rc != 0:
        print(adv_out, file=sys.stderr)
        if not bool(args.no_rollback):
            shutil.copyfile(backup_path, tuneables_path)
        return adv_rc

    memory_report = _load_json(ROOT / "benchmarks" / "out" / f"{mem_prefix}_report.json")
    advisory_report = _load_json(ROOT / "benchmarks" / "out" / f"{adv_prefix}_report.json")
    evaluation = _evaluate(
        memory_report=memory_report,
        advisory_report=advisory_report,
        mrr_min=float(args.memory_mrr_min),
        gate_pass_rate_min=float(args.memory_gate_pass_rate_min),
        advisory_score_min=float(args.advisory_score_min),
    )

    rolled_back = False
    status = "promoted"
    if not bool(evaluation.get("all_pass")) and not bool(args.no_rollback):
        shutil.copyfile(backup_path, tuneables_path)
        rolled_back = True
        status = "rolled_back"
    elif not bool(evaluation.get("all_pass")):
        status = "failed_no_rollback"

    report = {
        "generated_at": now.isoformat(),
        "status": status,
        "rolled_back": rolled_back,
        "tuneables_path": str(tuneables_path),
        "backup_path": str(backup_path),
        "patch_applied": patch,
        "memory_cases": str(memory_cases),
        "memory_gates": str(memory_gates),
        "advisory_cases": str(advisory_cases),
        "memory_report_path": str(ROOT / "benchmarks" / "out" / f"{mem_prefix}_report.json"),
        "advisory_report_path": str(ROOT / "benchmarks" / "out" / f"{adv_prefix}_report.json"),
        "evaluation": evaluation,
    }
    docs_dir = ROOT / "docs" / "reports"
    docs_dir.mkdir(parents=True, exist_ok=True)
    report_json = docs_dir / f"{now.strftime('%Y-%m-%d')}_advisory_retrieval_canary_{stamp}.json"
    report_md = docs_dir / f"{now.strftime('%Y-%m-%d')}_advisory_retrieval_canary_{stamp}.md"
    report_json.write_text(json.dumps(report, indent=2), encoding="utf-8")
    report_md.write_text(_render_md(report), encoding="utf-8")

    print(f"Canary status: {status}")
    print(f"Memory: {memory_report.get('weighted')}")
    winner = (advisory_report.get("winner") or {}).get("profile")
    score = ((advisory_report.get("winner") or {}).get("summary") or {}).get("score")
    print(f"Advisory winner: {winner} score={score}")
    print(f"Wrote: {report_json}")
    print(f"Wrote: {report_md}")

    return 0 if status == "promoted" else 2


if __name__ == "__main__":
    raise SystemExit(main())
