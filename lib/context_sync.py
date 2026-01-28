"""Session bootstrap sync: write high-confidence learnings to platform targets."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from .cognitive_learner import CognitiveLearner, CognitiveInsight
from .output_adapters import (
    write_claude_code,
    write_cursor,
    write_windsurf,
    write_clawdbot,
    write_exports,
)


DEFAULT_MIN_RELIABILITY = 0.7
DEFAULT_MIN_VALIDATIONS = 3
DEFAULT_MAX_ITEMS = 12


@dataclass
class SyncStats:
    targets: Dict[str, str]
    selected: int


def _select_insights(
    *,
    min_reliability: float = DEFAULT_MIN_RELIABILITY,
    min_validations: int = DEFAULT_MIN_VALIDATIONS,
    limit: int = DEFAULT_MAX_ITEMS,
) -> List[CognitiveInsight]:
    cognitive = CognitiveLearner()
    picked: List[CognitiveInsight] = []
    for insight in cognitive.insights.values():
        if insight.reliability < min_reliability:
            continue
        if insight.times_validated < min_validations:
            continue
        picked.append(insight)

    picked.sort(
        key=lambda i: (i.reliability, i.times_validated, i.confidence),
        reverse=True,
    )
    return picked[: max(0, int(limit or 0))]


def _format_context(insights: List[CognitiveInsight]) -> str:
    lines = [
        "## Spark Bootstrap",
        "Auto-loaded high-confidence learnings from ~/.spark/cognitive_insights.json",
        f"Last updated: {datetime.now().isoformat(timespec='seconds')}",
        "",
    ]

    if not insights:
        lines.append("No validated insights yet.")
        return "\n".join(lines).strip()

    for ins in insights:
        rel = f"{ins.reliability:.0%}"
        lines.append(
            f"- [{ins.category.value}] {ins.insight} ({rel} reliable, {ins.times_validated} validations)"
        )

    return "\n".join(lines).strip()


def sync_context(
    *,
    project_dir: Optional[Path] = None,
    min_reliability: float = DEFAULT_MIN_RELIABILITY,
    min_validations: int = DEFAULT_MIN_VALIDATIONS,
    limit: int = DEFAULT_MAX_ITEMS,
) -> SyncStats:
    insights = _select_insights(
        min_reliability=min_reliability,
        min_validations=min_validations,
        limit=limit,
    )
    context = _format_context(insights)

    root = project_dir or Path.cwd()
    targets: Dict[str, str] = {}

    try:
        write_claude_code(context, project_dir=root)
        targets["claude_code"] = "written"
    except Exception:
        targets["claude_code"] = "error"

    try:
        write_cursor(context, project_dir=root)
        targets["cursor"] = "written"
    except Exception:
        targets["cursor"] = "error"

    try:
        write_windsurf(context, project_dir=root)
        targets["windsurf"] = "written"
    except Exception:
        targets["windsurf"] = "error"

    try:
        ok = write_clawdbot(context)
        targets["clawdbot"] = "written" if ok else "skipped"
    except Exception:
        targets["clawdbot"] = "error"

    try:
        write_exports(context)
        targets["exports"] = "written"
    except Exception:
        targets["exports"] = "error"

    return SyncStats(targets=targets, selected=len(insights))


def main(argv: Optional[List[str]] = None) -> int:
    import argparse
    import json

    ap = argparse.ArgumentParser(description="Sync Spark bootstrap context to platforms")
    ap.add_argument("--project", "-p", default=None, help="Project root for file-based outputs")
    ap.add_argument("--min-reliability", type=float, default=DEFAULT_MIN_RELIABILITY)
    ap.add_argument("--min-validations", type=int, default=DEFAULT_MIN_VALIDATIONS)
    ap.add_argument("--limit", type=int, default=DEFAULT_MAX_ITEMS)
    args = ap.parse_args(argv)

    project_dir = Path(args.project).expanduser() if args.project else None
    stats = sync_context(
        project_dir=project_dir,
        min_reliability=args.min_reliability,
        min_validations=args.min_validations,
        limit=args.limit,
    )
    print(json.dumps({"selected": stats.selected, "targets": stats.targets}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
