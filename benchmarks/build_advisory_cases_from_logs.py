#!/usr/bin/env python3
"""Build draft advisory benchmark cases from recent runtime logs."""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path
from typing import Any, Dict, List


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except Exception:
        return float(default)


def _read_jsonl(path: Path) -> List[Dict[str, Any]]:
    if not path.exists():
        return []
    out: List[Dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            row = json.loads(line)
        except Exception:
            continue
        if isinstance(row, dict):
            out.append(row)
    return out


def build_cases(engine_log: Path, lookback_hours: int, limit: int) -> List[Dict[str, Any]]:
    now = time.time()
    window_s = max(1, int(lookback_hours)) * 3600
    rows = [r for r in _read_jsonl(engine_log) if (_safe_float(r.get("ts"), 0.0) >= (now - window_s))]

    by_key: Dict[str, Dict[str, Any]] = {}
    for row in rows:
        event = str(row.get("event") or "")
        if event not in {"no_emit", "duplicate_suppressed", "engine_error", "emitted"}:
            continue
        tool = str(row.get("tool") or "Read").strip() or "Read"
        error_code = str(row.get("error_code") or "").strip()
        key = f"{tool}|{event}|{error_code}"
        bucket = by_key.setdefault(
            key,
            {
                "tool": tool,
                "event": event,
                "error_code": error_code,
                "count": 0,
                "routes": {},
            },
        )
        bucket["count"] += 1
        route = str(row.get("route") or "unknown")
        bucket["routes"][route] = int(bucket["routes"].get(route, 0)) + 1

    ranked = sorted(by_key.values(), key=lambda x: int(x.get("count", 0)), reverse=True)[: max(1, int(limit))]
    cases: List[Dict[str, Any]] = []
    for idx, row in enumerate(ranked, start=1):
        tool = str(row.get("tool") or "Read")
        event = str(row.get("event") or "")
        error_code = str(row.get("error_code") or "")
        should_emit = event != "no_emit"
        expected = ["next check"] if should_emit else []
        forbidden = []
        if error_code:
            forbidden.append(error_code.lower())
        if tool.lower() == "webfetch":
            forbidden.append("multiplier granted")
        cases.append(
            {
                "id": f"log_{idx:03d}_{tool.lower()}_{event}",
                "tool": tool,
                "prompt": (
                    f"Derived from runtime: event={event}, error_code={error_code or 'none'}, "
                    f"route-skew={max((row.get('routes') or {}).items(), key=lambda t: t[1])[0] if row.get('routes') else 'unknown'}."
                ),
                "tool_input": {"file_path": f"derived/{tool.lower()}_{idx}.txt"},
                "should_emit": should_emit,
                "expected_contains": expected,
                "forbidden_contains": forbidden,
                "notes": f"generated_from_logs count={row.get('count', 0)}",
            }
        )
    return cases


def main() -> int:
    ap = argparse.ArgumentParser(description="Generate draft advisory benchmark cases from runtime logs")
    ap.add_argument(
        "--engine-log",
        default=str(Path.home() / ".spark" / "advisory_engine.jsonl"),
        help="Path to advisory_engine.jsonl",
    )
    ap.add_argument("--lookback-hours", type=int, default=24, help="Lookback window for events")
    ap.add_argument("--limit", type=int, default=20, help="Max cases to generate")
    ap.add_argument(
        "--out",
        default=str(Path("benchmarks") / "data" / "advisory_quality_eval_from_logs.json"),
        help="Output JSON file",
    )
    args = ap.parse_args()

    cases = build_cases(Path(args.engine_log), lookback_hours=int(args.lookback_hours), limit=int(args.limit))
    payload = {"generated_at": time.time(), "source": str(args.engine_log), "cases": cases}
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"Wrote: {out_path}")
    print(f"Cases: {len(cases)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
