#!/usr/bin/env python3
"""Compatibility wrapper for benchmark CI workflows.

Historically the benchmark entrypoint existed with this filename. The current
pipeline and docs still invoke it, so keep this thin shim to preserve that
contract while forwarding to the available comprehensive benchmark implementation.
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from benchmarks.comprehensive_pipeline_benchmark import run_benchmark


def _prepare_out_dir(out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)


def _write_report(out_dir: Path, report: dict) -> None:
    ts = report["generated_at"]
    json_path = out_dir / f"report_{ts}.json"
    md_path = out_dir / f"report_{ts}.md"
    latest_json = out_dir / "report.json"
    latest_md = out_dir / "report.md"

    payload = json.dumps(report, indent=2)
    json_path.write_text(payload, encoding="utf-8")
    latest_json.write_text(payload, encoding="utf-8")

    md = [
        "# Spark benchmark report",
        "",
        f"Generated: {report['generated_at']}",
        f"Status: {report['status']}",
        "",
        "## Inputs",
        f"- Chips: {', '.join(report['chips']) if report['chips'] else 'all'}",
        f"- Limit: {report['limit']}",
        f"- Enrich: {report['enrich']}",
        "",
        "## Notes",
        "- Compatibility mode run; detailed results are emitted by the",
        "  comprehensive benchmark in `benchmarks/comprehensive_pipeline_benchmark.py`.",
    ]
    md_text = "\n".join(md).strip() + "\n"
    md_path.write_text(md_text, encoding="utf-8")
    latest_md.write_text(md_text, encoding="utf-8")


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run benchmark compatibility entrypoint")
    parser.add_argument("--chips", default="", help="Comma separated chip names (compat only)")
    parser.add_argument("--limit", type=int, default=300, help="Compatibility limit argument")
    parser.add_argument("--out-dir", default="benchmarks/out/ci", help="Where to write compatibility report")
    parser.add_argument("--enrich", action="store_true", help="Compatibility enrich flag")
    parser.add_argument("--seed", type=int, default=42, help="Deterministic random seed")
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    out_dir = Path(args.out_dir)
    _prepare_out_dir(out_dir)

    report = {
        "generated_at": datetime.now().strftime("%Y%m%d_%H%M%S"),
        "status": "ok",
        "chips": [s for s in args.chips.split(",") if s],
        "limit": args.limit,
        "out_dir": str(out_dir),
        "enrich": bool(args.enrich),
    }

    try:
        run_benchmark(seed=args.seed)
        report["run_benchmark"] = "completed"
    except Exception as e:  # pragma: no cover
        report["status"] = "error"
        report["run_benchmark"] = "failed"
        report["error"] = str(e)
        _write_report(out_dir, report)
        return 1

    _write_report(out_dir, report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
