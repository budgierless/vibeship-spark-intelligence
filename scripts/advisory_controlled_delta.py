from __future__ import annotations

import argparse
import json
import time
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Dict, List


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


def _row_ts(row: Dict[str, Any]) -> float:
    # Different Spark logs use different timestamp keys.
    # - advisory_engine.jsonl: typically "ts"
    # - advice_feedback_requests.jsonl: typically "created_at"
    for key in ("ts", "created_at", "timestamp"):
        if key in row:
            ts = _safe_float(row.get(key), 0.0)
            if ts:
                return ts
    return 0.0


def _collect_rows_since(path: Path, start_ts: float) -> List[Dict[str, Any]]:
    out = []
    for row in _read_jsonl(path):
        ts = _row_ts(row)
        if ts >= start_ts:
            out.append(row)
    return out


def _summarize_repeats(advice_rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    texts: List[str] = []
    trace_rows = 0
    for row in advice_rows:
        if row.get("trace_id"):
            trace_rows += 1
        for t in (row.get("advice_texts") or []):
            text = str(t or "").strip()
            if text:
                texts.append(text)
    total_items = len(texts)
    if total_items <= 0:
        return {
            "rows": len(advice_rows),
            "trace_rows": trace_rows,
            "trace_coverage_pct": 0.0,
            "item_total": 0,
            "top_repeats": [],
            "top_repeat_share_pct": 0.0,
            "unique_ratio_pct": 0.0,
        }
    counter = Counter(texts)
    top = [
        {"text": text[:180], "count": int(count)}
        for text, count in counter.most_common(5)
    ]
    top_share = (top[0]["count"] / total_items * 100.0) if top else 0.0
    unique_ratio = len(counter) / total_items * 100.0
    return {
        "rows": len(advice_rows),
        "trace_rows": trace_rows,
        "trace_coverage_pct": round((trace_rows / max(1, len(advice_rows))) * 100.0, 2),
        "item_total": total_items,
        "top_repeats": top,
        "top_repeat_share_pct": round(top_share, 2),
        "unique_ratio_pct": round(unique_ratio, 2),
    }


def _summarize_engine(engine_rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    events = Counter()
    routes = Counter()
    trace_rows = 0
    fallback_events = 0
    delivered = 0
    for row in engine_rows:
        ev = str(row.get("event") or "")
        rt = str(row.get("route") or "")
        if ev:
            events[ev] += 1
        if rt:
            routes[rt] += 1
        if row.get("trace_id"):
            trace_rows += 1
        if ev == "fallback_emit" or str(row.get("delivery_mode") or "") == "fallback":
            fallback_events += 1
        if ev in {"emitted", "fallback_emit"}:
            delivered += 1
    return {
        "rows": len(engine_rows),
        "trace_rows": trace_rows,
        "trace_coverage_pct": round((trace_rows / max(1, len(engine_rows))) * 100.0, 2),
        "events": dict(events),
        "routes": dict(routes),
        "fallback_share_pct": round((fallback_events / max(1, delivered)) * 100.0, 2),
    }


def run_workload(
    rounds: int,
    session_prefix: str,
    trace_prefix: str,
    *,
    force_live: bool = False,
    reset_feedback_state: bool = True,
) -> Dict[str, Any]:
    from lib import advisory_engine
    from lib import advisory_gate
    from lib import advisor as advisor_mod
    from lib import advisory_packet_store as packet_store

    spark_dir = Path.home() / ".spark"
    engine_log = spark_dir / "advisory_engine.jsonl"
    feedback_requests = spark_dir / "advice_feedback_requests.jsonl"
    feedback_state = spark_dir / "advice_feedback_state.json"

    if reset_feedback_state and feedback_state.exists():
        try:
            feedback_state.unlink()
        except Exception:
            pass

    start_ts = time.time()
    emitted_count = 0
    tools = ["Read", "Edit", "Task", "WebFetch", "Read", "Task", "Edit", "WebFetch"]
    orig_lookup_exact = packet_store.lookup_exact
    orig_lookup_relaxed = packet_store.lookup_relaxed
    if force_live:
        packet_store.lookup_exact = lambda **_kwargs: None  # type: ignore[assignment]
        packet_store.lookup_relaxed = lambda **_kwargs: None  # type: ignore[assignment]

    try:
        for i in range(max(1, rounds)):
            tool_name = tools[i % len(tools)]
            session_id = f"{session_prefix}-{i % 6}"
            trace_id = f"{trace_prefix}-{i:04d}"
            prompt = (
                "Evaluate advisory quality under repeated tool execution. "
                "Focus on precise, non-repetitive, actionable guidance with trace binding."
            )
            advisory_engine.on_user_prompt(session_id, prompt)
            tool_input = {"file_path": f"synthetic/{tool_name.lower()}_{i}.txt", "attempt": i}
            text = advisory_engine.on_pre_tool(
                session_id=session_id,
                tool_name=tool_name,
                tool_input=tool_input,
                trace_id=trace_id,
            )
            if text:
                emitted_count += 1
            success = not (tool_name in {"Task", "WebFetch"} and (i % 3 == 0))
            advisory_engine.on_post_tool(
                session_id=session_id,
                tool_name=tool_name,
                success=success,
                tool_input=tool_input,
                trace_id=trace_id,
                error=(None if success else "synthetic_failure"),
            )
    finally:
        if force_live:
            packet_store.lookup_exact = orig_lookup_exact  # type: ignore[assignment]
            packet_store.lookup_relaxed = orig_lookup_relaxed  # type: ignore[assignment]

    # Small flush window for file writes.
    time.sleep(0.25)

    engine_rows = _collect_rows_since(engine_log, start_ts)
    advice_rows = _collect_rows_since(feedback_requests, start_ts)

    return {
        "generated_at": datetime.now(UTC).isoformat(),
        "start_ts": start_ts,
        "rounds": rounds,
        "emitted_returns": emitted_count,
        "engine": _summarize_engine(engine_rows),
        "feedback_requests": _summarize_repeats(advice_rows),
        "config": {
            "advisory_engine": advisory_engine.get_engine_config(),
            "advisory_gate": advisory_gate.get_gate_config(),
            "advisor": {
                "max_items": int(getattr(advisor_mod, "MAX_ADVICE_ITEMS", 0)),
                "min_rank_score": float(getattr(advisor_mod, "MIN_RANK_SCORE", 0.0)),
            },
        },
        "force_live": bool(force_live),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="Run controlled advisory workload and summarize KPIs")
    ap.add_argument("--rounds", type=int, default=40, help="Number of synthetic pre/post tool rounds")
    ap.add_argument("--label", default="run", help="Label used in output metadata")
    ap.add_argument("--out", default="", help="Optional output JSON path")
    ap.add_argument("--force-live", action="store_true", help="Bypass packet lookup to exercise live advisory path")
    ap.add_argument(
        "--no-reset-feedback-state",
        action="store_true",
        help="Keep existing advice feedback state (default resets for clean comparisons)",
    )
    args = ap.parse_args()

    ts = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
    trace_prefix = f"delta-{args.label}-{ts}"
    session_prefix = f"delta-{args.label}"
    summary = run_workload(
        rounds=max(1, int(args.rounds)),
        session_prefix=session_prefix,
        trace_prefix=trace_prefix,
        force_live=bool(args.force_live),
        reset_feedback_state=not bool(args.no_reset_feedback_state),
    )
    summary["label"] = str(args.label)
    summary["trace_prefix"] = trace_prefix
    summary["session_prefix"] = session_prefix

    out_path = Path(args.out) if args.out else None
    if out_path:
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
        print(f"Wrote: {out_path}")
    else:
        print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
