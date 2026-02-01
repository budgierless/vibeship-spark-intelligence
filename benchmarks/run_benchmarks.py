import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple

import yaml

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from benchmarks.methodologies import get_methodologies
from lib.chips.loader import ChipLoader, Chip
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


def _load_scenario(path: Optional[Path]) -> Optional[Dict]:
    if not path:
        return None
    if not path.exists():
        return None
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    scenario = data.get("scenario") if isinstance(data, dict) else None
    return scenario or data


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


def _normalize_weighted_signals(signals: List) -> List[Dict]:
    normalized = []
    for item in signals:
        if isinstance(item, dict):
            signal = item.get("signal") or item.get("text") or item.get("pattern")
            weight = float(item.get("weight", 1.0))
        else:
            signal = str(item)
            weight = 1.0
        if signal:
            normalized.append({"signal": signal, "weight": weight})
    return normalized


def _normalize_weighted_artifacts(artifacts: List) -> List[Dict]:
    normalized = []
    for item in artifacts:
        if isinstance(item, dict):
            path = item.get("path")
            weight = float(item.get("weight", 1.0))
        else:
            path = str(item)
            weight = 1.0
        if path:
            normalized.append({"path": path, "weight": weight})
    return normalized


def _score_scenario(events: List[Dict], scenario: Dict, root_dir: Path) -> Dict:
    scoring = scenario.get("scoring", {}) if isinstance(scenario, dict) else {}
    outcome_weight = float(scoring.get("outcome_weight", 1.0))
    artifact_weight = float(scoring.get("artifact_weight", 1.0))

    tasks = scenario.get("tasks", []) if isinstance(scenario, dict) else []
    task_summaries = []

    outcomes_hit_weight = 0.0
    outcomes_total_weight = 0.0
    artifacts_found_weight = 0.0
    artifacts_total_weight = 0.0

    for task in tasks:
        task_id = task.get("id")
        signals = _normalize_weighted_signals(task.get("outcome_signals", []))
        expected_artifacts = _normalize_weighted_artifacts(task.get("expected_artifacts", []))

        task_events = [
            e for e in events
            if isinstance(e.get("payload"), dict)
            and e["payload"].get("task_id") == task_id
        ]
        if not task_events:
            task_events = events

        event_text = " ".join(_get_event_text(e) for e in task_events).lower()
        outcome_hits = []
        for signal in signals:
            text = signal["signal"].lower()
            hit = text in event_text if text else False
            outcome_hits.append({"signal": signal["signal"], "weight": signal["weight"], "hit": hit})
            outcomes_total_weight += signal["weight"]
            if hit:
                outcomes_hit_weight += signal["weight"]

        artifacts = []
        for item in expected_artifacts:
            path = item["path"]
            weight = item["weight"]
            artifact_path = root_dir / path
            exists = artifact_path.exists()
            artifacts.append({"path": path, "weight": weight, "exists": exists})
            artifacts_total_weight += weight
            if exists:
                artifacts_found_weight += weight

        outcome_total_for_task = sum(s["weight"] for s in signals)
        outcome_hit_for_task = sum(s["weight"] for s in outcome_hits if s["hit"])
        artifact_total_for_task = sum(a["weight"] for a in artifacts)
        artifact_hit_for_task = sum(a["weight"] for a in artifacts if a["exists"])

        task_summaries.append({
            "id": task_id,
            "goal": task.get("goal"),
            "outcome_hit": outcome_hit_for_task,
            "outcome_total": outcome_total_for_task,
            "outcome_signals": outcome_hits,
            "artifacts": artifacts,
            "artifact_hit": artifact_hit_for_task,
            "artifact_total": artifact_total_for_task,
        })

    score = outcomes_hit_weight * outcome_weight + artifacts_found_weight * artifact_weight
    max_score = outcomes_total_weight * outcome_weight + artifacts_total_weight * artifact_weight
    score_rate = score / max_score if max_score > 0 else 0.0

    return {
        "id": scenario.get("id"),
        "name": scenario.get("name"),
        "domain": scenario.get("domain"),
        "outcomes_hit": outcomes_hit_weight,
        "outcomes_total": outcomes_total_weight,
        "artifacts_found": artifacts_found_weight,
        "artifacts_total": artifacts_total_weight,
        "score": score,
        "max_score": max_score,
        "score_rate": score_rate,
        "tasks": task_summaries,
    }


def _matches(chip: Chip, event: Dict) -> bool:
    event_type = event.get("type") or event.get("hook_event") or event.get("kind", "")
    if event_type and event_type in (chip.trigger_events or []):
        return True

    tool_name = event.get("tool_name") or event.get("tool", "")
    if tool_name:
        for tool_trigger in chip.trigger_tools or []:
            if isinstance(tool_trigger, dict):
                name = tool_trigger.get("name", "")
                context_patterns = tool_trigger.get("context_contains", [])
            else:
                name = str(tool_trigger)
                context_patterns = []
            if name.lower() == tool_name.lower():
                if not context_patterns or context_patterns == ["*"]:
                    return True
                content = _get_event_text(event)
                for pattern in context_patterns:
                    if pattern.lower() in content.lower():
                        return True

    content = _get_event_text(event)
    if content and chip.matches_content(content):
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


def _load_chips(chips_dir: Path, chip_ids: List[str]) -> List[Chip]:
    loader = ChipLoader(chips_dir=chips_dir)
    specs: List[Chip] = []
    for path in chips_dir.glob("*.chip.yaml"):
        try:
            spec = loader.load_chip(path)
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
                   chip_ids: List[str], limit: int, enrich: bool = False,
                   scenario: Optional[Dict] = None) -> Dict:
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

    if scenario:
        stats["meta"]["scenario_id"] = scenario.get("id")

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

    if scenario:
        stats["scenario"] = _score_scenario(list(events), scenario, ROOT_DIR)

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

    scenario = stats.get("scenario")
    if scenario:
        lines.append("")
        lines.append("## Scenario Summary")
        lines.append(f"Scenario: {scenario.get('id')} ({scenario.get('name')})")
        lines.append(
            f"Score: {scenario.get('score'):.2f} / "
            f"{scenario.get('max_score', 0.0):.2f} "
            f"({scenario.get('score_rate', 0.0):.2%})"
        )
        lines.append("")
        lines.append("| Task | Outcome Score | Artifacts Score |")
        lines.append("|------|---------------|-----------------|")
        for task in scenario.get("tasks", []):
            outcome_hit = task.get("outcome_hit", 0.0)
            outcome_total = task.get("outcome_total", 0.0)
            artifact_hit = task.get("artifact_hit", 0.0)
            artifact_total = task.get("artifact_total", 0.0)
            lines.append(
                f"| {task.get('id')} | {outcome_hit:.2f}/{outcome_total:.2f} | "
                f"{artifact_hit:.2f}/{artifact_total:.2f} |"
            )

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
    parser.add_argument("--scenario", default="", help="Scenario YAML for extra scoring")
    parser.add_argument("--answers", action="store_true", help="Generate question answers")
    parser.add_argument("--questions", default=str(Path("benchmarks") / "question_bank.json"))
    parser.add_argument("--answers-out", default="", help="Override answers output path")
    args = parser.parse_args()

    chip_ids = [c.strip() for c in args.chips.split(",") if c.strip()]
    scenario = _load_scenario(Path(args.scenario)) if args.scenario else None
    stats = run_benchmarks(
        event_log=Path(args.log),
        chips_dir=Path(args.chips_dir),
        out_dir=Path(args.out_dir),
        chip_ids=chip_ids,
        limit=args.limit,
        enrich=args.enrich,
        scenario=scenario,
    )
    out_json, out_md = _write_report(stats, Path(args.out_dir))
    print(f"[bench] wrote {out_json}")
    print(f"[bench] wrote {out_md}")

    if args.answers:
        from benchmarks.answer_questions import generate_answers

        answers_out = args.answers_out or str(Path(args.out_dir) / "answers.md")
        generate_answers(Path(out_json), Path(args.questions), Path(answers_out))
        print(f"[answers] wrote {answers_out}")


if __name__ == "__main__":
    main()
