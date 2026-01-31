import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, Iterable, List, Tuple

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from benchmarks.methodologies import get_methodologies
from lib.chips.loader import ChipLoader, ChipSpec
from lib.chips.runner import ChipRunner
from lib.chips import store as chip_store
from lib.promoter import is_operational_insight, is_unsafe_insight


def _normalize_event(raw: Dict) -> Dict:
    payload = raw.get("data") or {}
    if isinstance(payload, dict) and "payload" in payload and isinstance(payload["payload"], dict):
        payload = payload["payload"]

    event = {
        "kind": raw.get("event_type"),
        "session_id": raw.get("session_id", "unknown"),
        "payload": payload,
        "tool_name": raw.get("tool_name"),
        "tool_input": raw.get("tool_input") or {},
        "error": raw.get("error"),
    }

    # Merge tool_input into payload for field extraction
    tool_input = event.get("tool_input") or {}
    if isinstance(tool_input, dict):
        merged = dict(payload) if isinstance(payload, dict) else {}
        for key, value in tool_input.items():
            merged.setdefault(key, value)
        event["payload"] = merged
        payload = merged

    # Help text extraction for routers/filters.
    if isinstance(payload, dict):
        for k in ("text", "content", "message", "prompt"):
            if k in payload and payload[k]:
                event[k] = payload[k]

    # Include tool input as searchable content
    if tool_input:
        event["content"] = (event.get("content") or "") + " " + str(tool_input)

    return event


def _enrich_event(event: Dict) -> Dict:
    """Heuristic enrichment to enable domain chip matching in benchmarks."""
    text = _get_event_text(event).lower()
    payload = event.get("payload", {})
    if not isinstance(payload, dict):
        payload = {}

    # Vibecoding: ensure repo/commit/test fields exist when keywords appear
    if "refactor" in text or "commit" in text or "pr" in text:
        payload.setdefault("repo", "bench-repo")
        payload.setdefault("commit_id", "bench-commit")
    if "test failed" in text or "ci failed" in text:
        payload.setdefault("test_name", "bench_test")
        payload.setdefault("error_code", "AssertionError")
    if "deploy" in text or "release" in text:
        payload.setdefault("env", "prod")
        payload.setdefault("status", "success" if "success" in text else "failure")

    # Game dev: playtest feedback and retention fields
    if "playtest" in text:
        payload.setdefault("playtest_id", "bench-playtest")
        payload.setdefault("rating", 4)
    if "retention" in text:
        payload.setdefault("metric_name", "D1")
        payload.setdefault("metric_value", 0.3)
    if "balance" in text or "difficulty" in text:
        payload.setdefault("system", "combat")
        payload.setdefault("change", "bench change")

    event["payload"] = payload
    return event


def _load_events(path: Path, limit: int) -> Iterable[Dict]:
    if not path.exists():
        return []
    events: List[Dict] = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            if limit and len(events) >= limit:
                break
            try:
                raw = json.loads(line.strip())
                events.append(_normalize_event(raw))
            except Exception:
                continue
    return events


def _matches(spec: ChipSpec, event: Dict) -> bool:
    event_type = event.get("type") or event.get("hook_event") or event.get("kind", "")
    if event_type and event_type in spec.triggers.events:
        return True

    tool_name = event.get("tool_name") or event.get("tool", "")
    if tool_name:
        for tool_trigger in spec.triggers.tools:
            if tool_trigger.get("name", "").lower() == tool_name.lower():
                context_patterns = tool_trigger.get("context_contains", [])
                if not context_patterns or context_patterns == ["*"]:
                    return True
                content = _get_event_text(event)
                for pattern in context_patterns:
                    if pattern.lower() in content.lower():
                        return True

    content = _get_event_text(event)
    if content and spec.triggers.matches(content):
        return True

    return False


def _get_event_text(event: Dict) -> str:
    parts = []
    for key in ("content", "text", "message", "prompt", "user_prompt", "description"):
        if key in event and event[key]:
            parts.append(str(event[key]))
    payload = event.get("payload", {})
    if isinstance(payload, dict):
        for key in ("text", "content", "message", "prompt"):
            if key in payload and payload[key]:
                parts.append(str(payload[key]))
    # Tool input/output
    for key in ("tool_input", "tool_output", "result"):
        if key in event and event[key]:
            parts.append(str(event[key]))
    return " ".join(parts)


def _load_chips(chips_dir: Path, chip_ids: List[str]) -> List[ChipSpec]:
    loader = ChipLoader()
    specs = []
    for path in chips_dir.glob("*.chip.yaml"):
        try:
            spec = loader.load(path)
        except Exception:
            continue
        if chip_ids and spec.id not in chip_ids:
            continue
        specs.append(spec)
    return specs


def _init_chip_store(base_dir: Path) -> None:
    chip_store.CHIP_INSIGHTS_DIR = base_dir
    chip_store._stores.clear()


def run_benchmarks(event_log: Path, chips_dir: Path, out_dir: Path,
                   chip_ids: List[str], limit: int, enrich: bool = False) -> Dict:
    out_dir.mkdir(parents=True, exist_ok=True)
    _init_chip_store(out_dir / "chip_insights")

    specs = _load_chips(chips_dir, chip_ids)
    runners = {spec.id: ChipRunner(spec) for spec in specs}
    methods = get_methodologies()

    stats = {
        "meta": {
            "event_log": str(event_log),
            "chips": [s.id for s in specs],
            "limit": limit,
            "created_at": datetime.utcnow().isoformat(),
        },
        "methods": {},
    }

    for m in methods:
        stats["methods"][m["id"]] = {
            "description": m["description"],
            "total_candidates": 0,
            "accepted": 0,
            "accept_rate": 0.0,
            "avg_confidence": 0.0,
            "outcome_hits": 0,
            "operational_rejected": 0,
            "unsafe_rejected": 0,
        }

    events = _load_events(event_log, limit)
    if enrich:
        events = [_enrich_event(e) for e in events]

    for event in events:
        event_text = _get_event_text(event)
        for spec in specs:
            if not _matches(spec, event):
                continue
            runner = runners[spec.id]

            content = runner._get_event_content(event)
            observers = runner._find_matching_observers(content)
            for obs in observers:
                captured = runner._extract_fields(obs, event, content)
                if not captured.fields or captured.confidence < 0.5:
                    continue

                field_summary = ", ".join(
                    f"{k}={v}" for k, v in list(captured.fields.items())[:5]
                )
                insight_text = f"{obs.description}: {field_summary}"
                outcome = runner.check_outcomes(captured.fields)

                record = {
                    "chip_id": spec.id,
                    "observer": obs.name,
                    "insight": insight_text,
                    "confidence": captured.confidence,
                    "fields": captured.fields,
                    "fields_count": len(captured.fields),
                    "outcome": outcome,
                    "event_text": event_text,
                }

                for m in methods:
                    mstats = stats["methods"][m["id"]]
                    mstats["total_candidates"] += 1
                    if is_operational_insight(insight_text):
                        mstats["operational_rejected"] += 1
                    if is_unsafe_insight(insight_text):
                        mstats["unsafe_rejected"] += 1

                    if m["accept"](record):
                        mstats["accepted"] += 1
                        mstats["avg_confidence"] += captured.confidence
                        if outcome:
                            mstats["outcome_hits"] += 1

    for m in methods:
        mstats = stats["methods"][m["id"]]
        if mstats["accepted"] > 0:
            mstats["avg_confidence"] = mstats["avg_confidence"] / mstats["accepted"]
            mstats["accept_rate"] = mstats["accepted"] / max(1, mstats["total_candidates"])
        else:
            mstats["avg_confidence"] = 0.0
            mstats["accept_rate"] = 0.0

    return stats


def _write_report(stats: Dict, out_dir: Path) -> Tuple[Path, Path]:
    out_json = out_dir / "report.json"
    out_md = out_dir / "report.md"

    with open(out_json, "w", encoding="utf-8") as f:
        json.dump(stats, f, indent=2)

    lines = []
    lines.append("# Chip Methodology Benchmark Report")
    lines.append("")
    meta = stats.get("meta", {})
    lines.append(f"Event log: {meta.get('event_log')}")
    lines.append(f"Chips: {', '.join(meta.get('chips', []))}")
    lines.append(f"Limit: {meta.get('limit')}")
    lines.append("")
    lines.append("| Method | Accepted | Accept Rate | Avg Conf | Outcome Hits |")
    lines.append("|--------|----------|------------|----------|--------------|")

    for method_id, mstats in stats["methods"].items():
        lines.append(
            f"| {method_id} | {mstats['accepted']} | {mstats['accept_rate']:.2%} | {mstats['avg_confidence']:.2f} | {mstats['outcome_hits']} |"  # noqa: E501
        )

    lines.append("")
    lines.append("## Notes")
    for method_id, mstats in stats["methods"].items():
        desc = mstats.get("description", "")
        lines.append(f"- {method_id}: {desc}")

    out_md.write_text("\n".join(lines), encoding="utf-8")
    return out_json, out_md


def main() -> None:
    parser = argparse.ArgumentParser(description="Benchmark chip methodologies on an event log.")
    parser.add_argument("--log", default=str(Path.home() / ".spark" / "queue" / "events.jsonl"))
    parser.add_argument("--chips-dir", default=str(Path("chips")))
    parser.add_argument("--chips", default="", help="Comma-separated chip ids to include")
    parser.add_argument("--limit", type=int, default=500)
    parser.add_argument("--out-dir", default=str(Path("benchmarks") / "out"))
    parser.add_argument("--enrich", action="store_true", help="Enable heuristic enrichment")
    args = parser.parse_args()

    chip_ids = [c.strip() for c in args.chips.split(",") if c.strip()]
    stats = run_benchmarks(
        event_log=Path(args.log),
        chips_dir=Path(args.chips_dir),
        out_dir=Path(args.out_dir),
        chip_ids=chip_ids,
        limit=args.limit,
        enrich=args.enrich,
    )
    out_json, out_md = _write_report(stats, Path(args.out_dir))
    print(f"[bench] wrote {out_json}")
    print(f"[bench] wrote {out_md}")


if __name__ == "__main__":
    main()
