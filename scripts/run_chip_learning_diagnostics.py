#!/usr/bin/env python3
"""Diagnose chip-to-learning yield and blockers.

Outputs per-chip and global metrics for:
- telemetry/noise prevalence
- distilled learning statement yield
- quality gate pass rates
- final merge-eligible learning candidates
"""

from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Dict, List

from lib import chip_merger as cm

ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "benchmarks" / "out"


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except Exception:
        return float(default)


def _load_rows(path: Path, limit: int) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    try:
        lines = path.read_text(encoding="utf-8", errors="ignore").splitlines()
    except Exception:
        return rows
    for line in lines[-max(1, int(limit)) :]:
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except Exception:
            continue
        if isinstance(row, dict):
            rows.append(row)
    return rows


def _md(report: Dict[str, Any]) -> str:
    lines: List[str] = []
    lines.append(f"# Chip Learning Diagnostics ({report.get('generated_at','')})")
    lines.append("")
    lines.append(f"- Limits: `{report.get('limits')}`")
    lines.append(f"- Rows analyzed: `{int(report.get('rows_analyzed', 0))}`")
    lines.append(f"- Merge-eligible candidates: `{int(report.get('merge_eligible', 0))}`")
    lines.append(f"- Telemetry rate: `{float(report.get('telemetry_rate', 0.0)):.2%}`")
    lines.append(f"- Statement yield: `{float(report.get('statement_yield_rate', 0.0)):.2%}`")
    lines.append(f"- Learning-quality pass rate: `{float(report.get('learning_quality_pass_rate', 0.0)):.2%}`")
    lines.append("")
    lines.append("| Chip | Rows | Telemetry | Statements | Quality Pass | Merge Eligible |")
    lines.append("|---|---:|---:|---:|---:|---:|")
    for row in report.get("chips", []):
        lines.append(
            f"| `{row.get('chip_id','')}` | {int(row.get('rows',0))} | "
            f"{float(row.get('telemetry_rate',0.0)):.2%} | {float(row.get('statement_yield_rate',0.0)):.2%} | "
            f"{float(row.get('learning_quality_pass_rate',0.0)):.2%} | {int(row.get('merge_eligible',0))} |"
        )
    lines.append("")
    lines.append("## Top Examples")
    lines.append("")
    for row in report.get("chips", []):
        examples = row.get("sample_statements") or []
        if not examples:
            continue
        lines.append(f"### `{row.get('chip_id','')}`")
        for item in examples[:3]:
            lines.append(f"- {str(item)[:220]}")
        lines.append("")
    return "\n".join(lines).strip() + "\n"


def main() -> int:
    ap = argparse.ArgumentParser(description="Run chip learning diagnostics")
    ap.add_argument("--limit-per-chip", type=int, default=400, help="Rows to inspect per chip file")
    ap.add_argument("--out-prefix", default="chip_learning_diagnostics_v1", help="Output file prefix under benchmarks/out")
    args = ap.parse_args()

    chip_dir = cm.CHIP_INSIGHTS_DIR
    files = sorted(chip_dir.glob("*.jsonl")) if chip_dir.exists() else []
    limits = cm._load_merge_tuneables()

    rows_analyzed = 0
    total_telemetry = 0
    total_statement = 0
    total_quality_pass = 0
    total_merge_eligible = 0
    chips: List[Dict[str, Any]] = []

    for fp in files:
        rows = _load_rows(fp, args.limit_per_chip)
        if not rows:
            continue
        c_rows = len(rows)
        rows_analyzed += c_rows
        telemetry = 0
        statements = 0
        quality_pass = 0
        merge_eligible = 0
        sample_statements: List[str] = []
        seen = set()

        for row in rows:
            chip_id = str(row.get("chip_id") or fp.stem)
            content = str(row.get("content") or "")
            captured = row.get("captured_data") or {}
            quality = (captured.get("quality_score") or {}) if isinstance(captured, dict) else {}
            total = _safe_float(quality.get("total"), _safe_float(row.get("confidence"), 0.0))

            if cm._looks_like_telemetry(chip_id, content):
                telemetry += 1

            statement = cm._distill_learning_statement(
                chip_id=chip_id,
                content=content,
                captured_data=captured,
                min_len=int(limits.get("min_statement_len", 28)),
            )
            if statement:
                statements += 1
                if len(sample_statements) < 3:
                    sample_statements.append(statement)

            learning_ok = cm._is_learning_quality_ok(quality, limits)
            if learning_ok:
                quality_pass += 1

            if total >= 0.55 and statement and learning_ok:
                h = cm._hash_insight(chip_id, statement)
                if h not in seen:
                    seen.add(h)
                    merge_eligible += 1

        total_telemetry += telemetry
        total_statement += statements
        total_quality_pass += quality_pass
        total_merge_eligible += merge_eligible
        chips.append(
            {
                "chip_id": fp.stem,
                "rows": c_rows,
                "telemetry_count": telemetry,
                "telemetry_rate": round(telemetry / max(1, c_rows), 4),
                "statement_count": statements,
                "statement_yield_rate": round(statements / max(1, c_rows), 4),
                "learning_quality_pass_count": quality_pass,
                "learning_quality_pass_rate": round(quality_pass / max(1, c_rows), 4),
                "merge_eligible": merge_eligible,
                "sample_statements": sample_statements,
            }
        )

    chips.sort(key=lambda r: (int(r.get("merge_eligible", 0)), float(r.get("statement_yield_rate", 0.0))), reverse=True)

    report = {
        "generated_at": datetime.now(UTC).isoformat(),
        "limits": limits,
        "rows_analyzed": rows_analyzed,
        "merge_eligible": total_merge_eligible,
        "telemetry_rate": round(total_telemetry / max(1, rows_analyzed), 4),
        "statement_yield_rate": round(total_statement / max(1, rows_analyzed), 4),
        "learning_quality_pass_rate": round(total_quality_pass / max(1, rows_analyzed), 4),
        "chips": chips,
    }

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    json_path = OUT_DIR / f"{args.out_prefix}_report.json"
    md_path = OUT_DIR / f"{args.out_prefix}_report.md"
    json_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    md_path.write_text(_md(report), encoding="utf-8")

    print(f"Wrote: {json_path}")
    print(f"Wrote: {md_path}")
    print(
        f"rows={rows_analyzed} merge_eligible={total_merge_eligible} "
        f"telemetry_rate={float(report['telemetry_rate']):.2%} "
        f"statement_yield={float(report['statement_yield_rate']):.2%}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
