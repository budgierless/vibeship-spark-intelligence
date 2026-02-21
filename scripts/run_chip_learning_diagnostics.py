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
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List

from lib import chip_merger as cm

ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "benchmarks" / "out"
DEFAULT_PROJECT_PATH = "<USER_HOME>\\Desktop\\vibeship-spark-intelligence"


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except Exception:
        return float(default)


def _apply_limit_overrides(base: Dict[str, Any], args: argparse.Namespace) -> Dict[str, Any]:
    out = dict(base or {})

    if args.min_cognitive_value is not None:
        out["min_cognitive_value"] = max(0.0, min(1.0, float(args.min_cognitive_value)))
    if args.min_actionability is not None:
        out["min_actionability"] = max(0.0, min(1.0, float(args.min_actionability)))
    if args.min_transferability is not None:
        out["min_transferability"] = max(0.0, min(1.0, float(args.min_transferability)))
    if args.min_statement_len is not None:
        out["min_statement_len"] = max(12, min(240, int(args.min_statement_len)))
    if args.duplicate_churn_ratio is not None:
        out["duplicate_churn_ratio"] = max(0.5, min(1.0, float(args.duplicate_churn_ratio)))
    if args.duplicate_churn_min_processed is not None:
        out["duplicate_churn_min_processed"] = max(5, min(1000, int(args.duplicate_churn_min_processed)))
    if args.duplicate_churn_cooldown_s is not None:
        out["duplicate_churn_cooldown_s"] = max(60, min(24 * 3600, int(args.duplicate_churn_cooldown_s)))
    return out


def _parse_timestamp(value: Any) -> datetime | None:
    text = str(value or "").strip()
    if not text:
        return None
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        ts = datetime.fromisoformat(text)
    except Exception:
        return None
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=UTC)
    return ts


def _load_registry_active(project_path: str) -> List[str]:
    registry = Path.home() / ".spark" / "chip_registry.json"
    if not registry.exists():
        return []
    try:
        raw = json.loads(registry.read_text(encoding="utf-8"))
    except Exception:
        return []
    if not isinstance(raw, dict):
        return []
    active = raw.get("active") or {}
    if not isinstance(active, dict):
        return []
    rows = active.get(project_path) or []
    if not isinstance(rows, list):
        return []
    return sorted({str(r).strip() for r in rows if str(r).strip()})


def _load_rows(path: Path, limit: int, max_age_days: int = 0) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    cutoff = None
    if max_age_days and max_age_days > 0:
        cutoff = datetime.now(UTC) - timedelta(days=max_age_days)
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
            if cutoff is not None:
                ts = _parse_timestamp(row.get("timestamp"))
                if ts is None or ts < cutoff:
                    continue
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
    lines.append(f"- Telemetry observer rate: `{float(report.get('telemetry_observer_rate', 0.0)):.2%}`")
    lines.append(f"- Statement yield: `{float(report.get('statement_yield_rate', 0.0)):.2%}`")
    lines.append(f"- Learning-quality pass rate: `{float(report.get('learning_quality_pass_rate', 0.0)):.2%}`")
    lines.append(f"- Missing confidence rate: `{float(report.get('missing_confidence_rate', 0.0)):.2%}`")
    lines.append(f"- Missing quality-score rate: `{float(report.get('missing_quality_rate', 0.0)):.2%}`")
    lines.append(f"- Schema payload rate: `{float(report.get('schema_payload_rate', 0.0)):.2%}`")
    lines.append(f"- Schema statement yield: `{float(report.get('schema_statement_rate', 0.0)):.2%}`")
    lines.append(f"- Min total quality score: `{float(report.get('min_total_score', 0.55)):.2f}`")
    lines.append(f"- Active-only filter: `{bool(report.get('active_only', False))}`")
    lines.append(f"- Max age days: `{int(report.get('max_age_days', 0))}`")
    lines.append("")
    lines.append("| Chip | Rows | Telemetry | Telemetry Obs | Missing Conf | Missing Quality | Schema Payload | Schema Statement | Statements | Quality Pass | Merge Eligible |")
    lines.append("|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|")
    for row in report.get("chips", []):
        lines.append(
            f"| `{row.get('chip_id','')}` | {int(row.get('rows',0))} | "
            f"{float(row.get('telemetry_rate',0.0)):.2%} | {float(row.get('telemetry_observer_rate',0.0)):.2%} | "
            f"{float(row.get('missing_confidence_rate',0.0)):.2%} | {float(row.get('missing_quality_rate',0.0)):.2%} | "
            f"{float(row.get('schema_payload_rate',0.0)):.2%} | {float(row.get('schema_statement_rate',0.0)):.2%} | "
            f"{float(row.get('statement_yield_rate',0.0)):.2%} | {float(row.get('learning_quality_pass_rate',0.0)):.2%} | "
            f"{int(row.get('merge_eligible',0))} |"
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

    observers = report.get("observers") or []
    if observers:
        lines.append("## Observer KPIs")
        lines.append("")
        lines.append("| Observer | Rows | Schema Payload | Schema Statement | Statements | Merge Eligible | Non-Telemetry |")
        lines.append("|---|---:|---:|---:|---:|---:|---:|")
        for row in observers[: int(report.get("observer_limit", 12))]:
            lines.append(
                f"| `{row.get('observer','')}` | {int(row.get('rows',0))} | "
                f"{float(row.get('schema_payload_rate',0.0)):.2%} | {float(row.get('schema_statement_rate',0.0)):.2%} | "
                f"{float(row.get('statement_yield_rate',0.0)):.2%} | {int(row.get('merge_eligible',0))} | "
                f"{(1.0 - float(row.get('telemetry_rate',1.0))):.2%} |"
            )
        lines.append("")
    return "\n".join(lines).strip() + "\n"


def main() -> int:
    ap = argparse.ArgumentParser(description="Run chip learning diagnostics")
    ap.add_argument("--limit-per-chip", type=int, default=400, help="Rows to inspect per chip file")
    ap.add_argument("--min-total-score", type=float, default=0.55, help="Minimum quality_score.total for merge-eligible counting")
    ap.add_argument("--min-cognitive-value", type=float, default=None, help="Override chip_merge.min_cognitive_value")
    ap.add_argument("--min-actionability", type=float, default=None, help="Override chip_merge.min_actionability")
    ap.add_argument("--min-transferability", type=float, default=None, help="Override chip_merge.min_transferability")
    ap.add_argument("--min-statement-len", type=int, default=None, help="Override chip_merge.min_statement_len")
    ap.add_argument("--duplicate-churn-ratio", type=float, default=None, help="Override chip_merge.duplicate_churn_ratio for diagnostics context")
    ap.add_argument("--duplicate-churn-min-processed", type=int, default=None, help="Override chip_merge.duplicate_churn_min_processed for diagnostics context")
    ap.add_argument("--duplicate-churn-cooldown-s", type=int, default=None, help="Override chip_merge.duplicate_churn_cooldown_s for diagnostics context")
    ap.add_argument("--active-only", action="store_true", help="Analyze only chip files active for a project in ~/.spark/chip_registry.json")
    ap.add_argument("--project-path", default=DEFAULT_PROJECT_PATH, help="Project registry key for --active-only filtering")
    ap.add_argument("--max-age-days", type=int, default=0, help="Analyze only rows newer than N days (0 disables)")
    ap.add_argument("--observer-limit", type=int, default=12, help="Max observer rows to include in markdown report")
    ap.add_argument("--out-prefix", default="chip_learning_diagnostics_v1", help="Output file prefix under benchmarks/out")
    args = ap.parse_args()

    chip_dir = cm.CHIP_INSIGHTS_DIR
    files = sorted(chip_dir.glob("*.jsonl")) if chip_dir.exists() else []
    active_ids = _load_registry_active(str(args.project_path)) if bool(args.active_only) else []
    if active_ids:
        wanted = {f"{cid}.jsonl" for cid in active_ids}
        files = [f for f in files if f.name in wanted]
    limits = _apply_limit_overrides(cm._load_merge_tuneables(), args)
    min_total_score = max(0.0, min(1.0, float(args.min_total_score)))

    rows_analyzed = 0
    total_telemetry = 0
    total_statement = 0
    total_quality_pass = 0
    total_merge_eligible = 0
    total_missing_confidence = 0
    total_missing_quality = 0
    total_telemetry_observer = 0
    total_schema_payload = 0
    total_schema_statement = 0
    chips: List[Dict[str, Any]] = []
    observers_map: Dict[str, Dict[str, Any]] = {}

    for fp in files:
        rows = _load_rows(fp, args.limit_per_chip, max_age_days=int(args.max_age_days))
        if not rows:
            continue
        c_rows = len(rows)
        rows_analyzed += c_rows
        telemetry = 0
        statements = 0
        quality_pass = 0
        merge_eligible = 0
        missing_confidence = 0
        missing_quality = 0
        telemetry_observer = 0
        schema_payload = 0
        schema_statement = 0
        sample_statements: List[str] = []
        seen = set()

        for row in rows:
            chip_id = str(row.get("chip_id") or fp.stem)
            content = str(row.get("content") or "")
            captured = row.get("captured_data") or {}
            quality = (captured.get("quality_score") or {}) if isinstance(captured, dict) else {}
            total = _safe_float(quality.get("total"), _safe_float(row.get("confidence"), 0.0))
            observer_name = str(row.get("observer_name") or "")
            observer_key = f"{chip_id}/{observer_name or 'unknown'}"
            if observer_key not in observers_map:
                observers_map[observer_key] = {
                    "observer": observer_key,
                    "rows": 0,
                    "telemetry_count": 0,
                    "statement_count": 0,
                    "schema_payload_count": 0,
                    "schema_statement_count": 0,
                    "quality_pass_count": 0,
                    "merge_eligible": 0,
                    "_seen": set(),
                }
            obs = observers_map[observer_key]
            obs["rows"] += 1

            if row.get("confidence") is None:
                missing_confidence += 1
            if not isinstance(quality, dict) or not quality:
                missing_quality += 1
            if cm._is_telemetry_observer(observer_name):
                telemetry_observer += 1

            if cm._looks_like_telemetry(chip_id, content):
                telemetry += 1
                obs["telemetry_count"] += 1

            if isinstance(captured.get("learning_payload"), dict):
                schema_payload += 1
                obs["schema_payload_count"] += 1
                payload_statement = cm._payload_based_learning_statement(
                    captured_data=captured,
                    min_len=int(limits.get("min_statement_len", 28)),
                )
                if payload_statement:
                    schema_statement += 1
                    obs["schema_statement_count"] += 1

            statement = cm._distill_learning_statement(
                chip_id=chip_id,
                content=content,
                captured_data=captured,
                min_len=int(limits.get("min_statement_len", 28)),
                observer_name=observer_name,
            )
            if statement:
                statements += 1
                obs["statement_count"] += 1
                if len(sample_statements) < 3:
                    sample_statements.append(statement)

            learning_ok = cm._is_learning_quality_ok(quality, limits)
            if learning_ok:
                quality_pass += 1
                obs["quality_pass_count"] += 1

            if total >= min_total_score and statement and learning_ok:
                h = cm._hash_insight(chip_id, statement)
                if h not in seen:
                    seen.add(h)
                    merge_eligible += 1
                if h not in obs["_seen"]:
                    obs["_seen"].add(h)
                    obs["merge_eligible"] += 1

        total_telemetry += telemetry
        total_statement += statements
        total_quality_pass += quality_pass
        total_merge_eligible += merge_eligible
        total_missing_confidence += missing_confidence
        total_missing_quality += missing_quality
        total_telemetry_observer += telemetry_observer
        total_schema_payload += schema_payload
        total_schema_statement += schema_statement
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
                "missing_confidence_count": missing_confidence,
                "missing_confidence_rate": round(missing_confidence / max(1, c_rows), 4),
                "missing_quality_count": missing_quality,
                "missing_quality_rate": round(missing_quality / max(1, c_rows), 4),
                "telemetry_observer_count": telemetry_observer,
                "telemetry_observer_rate": round(telemetry_observer / max(1, c_rows), 4),
                "schema_payload_count": schema_payload,
                "schema_payload_rate": round(schema_payload / max(1, c_rows), 4),
                "schema_statement_count": schema_statement,
                "schema_statement_rate": round(schema_statement / max(1, c_rows), 4),
                "sample_statements": sample_statements,
            }
        )

    chips.sort(key=lambda r: (int(r.get("merge_eligible", 0)), float(r.get("statement_yield_rate", 0.0))), reverse=True)
    observers: List[Dict[str, Any]] = []
    for _, row in observers_map.items():
        c_rows = max(1, int(row.get("rows", 0)))
        observers.append(
            {
                "observer": row.get("observer"),
                "rows": int(row.get("rows", 0)),
                "telemetry_rate": round(int(row.get("telemetry_count", 0)) / c_rows, 4),
                "statement_yield_rate": round(int(row.get("statement_count", 0)) / c_rows, 4),
                "schema_payload_rate": round(int(row.get("schema_payload_count", 0)) / c_rows, 4),
                "schema_statement_rate": round(int(row.get("schema_statement_count", 0)) / c_rows, 4),
                "learning_quality_pass_rate": round(int(row.get("quality_pass_count", 0)) / c_rows, 4),
                "merge_eligible": int(row.get("merge_eligible", 0)),
            }
        )
    observers.sort(
        key=lambda r: (
            float(r.get("schema_statement_rate", 0.0)),
            int(r.get("merge_eligible", 0)),
            int(r.get("rows", 0)),
        ),
        reverse=True,
    )

    report = {
        "generated_at": datetime.now(UTC).isoformat(),
        "limits": limits,
        "active_only": bool(args.active_only),
        "project_path": str(args.project_path),
        "max_age_days": int(args.max_age_days),
        "observer_limit": int(args.observer_limit),
        "active_chip_ids": active_ids,
        "rows_analyzed": rows_analyzed,
        "merge_eligible": total_merge_eligible,
        "telemetry_rate": round(total_telemetry / max(1, rows_analyzed), 4),
        "telemetry_observer_rate": round(total_telemetry_observer / max(1, rows_analyzed), 4),
        "statement_yield_rate": round(total_statement / max(1, rows_analyzed), 4),
        "learning_quality_pass_rate": round(total_quality_pass / max(1, rows_analyzed), 4),
        "missing_confidence_rate": round(total_missing_confidence / max(1, rows_analyzed), 4),
        "missing_quality_rate": round(total_missing_quality / max(1, rows_analyzed), 4),
        "schema_payload_rate": round(total_schema_payload / max(1, rows_analyzed), 4),
        "schema_statement_rate": round(total_schema_statement / max(1, rows_analyzed), 4),
        "min_total_score": min_total_score,
        "chips": chips,
        "observers": observers,
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
        f"statement_yield={float(report['statement_yield_rate']):.2%} "
        f"min_total_score={min_total_score:.2f}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

