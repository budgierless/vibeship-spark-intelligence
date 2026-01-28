"""Session bootstrap sync: write high-confidence learnings to platform targets."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import re

from .cognitive_learner import CognitiveLearner, CognitiveInsight
from .output_adapters import (
    write_claude_code,
    write_cursor,
    write_windsurf,
    write_clawdbot,
    write_exports,
)
from .sync_tracker import get_sync_tracker


DEFAULT_MIN_RELIABILITY = 0.7
DEFAULT_MIN_VALIDATIONS = 3
DEFAULT_MAX_ITEMS = 12
DEFAULT_MAX_PROMOTED = 6


@dataclass
class SyncStats:
    targets: Dict[str, str]
    selected: int
    promoted_selected: int


def _normalize_text(text: str) -> str:
    t = (text or "").strip().lower()
    t = re.sub(r"\s*\(\d+\s*calls?\)", "", t)
    t = re.sub(r"\s*\(\d+\)", "", t)
    t = re.sub(r"\(\s*recovered\s*\d+%?\s*\)", "", t)
    t = re.sub(r"\brecovered\s*\d+%?\b", "recovered", t)
    t = re.sub(r"\s+\d+$", "", t)
    t = re.sub(r"\s+", " ", t)
    return t.strip()


def _is_low_value(insight_text: str) -> bool:
    t = (insight_text or "").lower()
    if "indicates task type" in t:
        return True
    if "heavy " in t and " usage" in t:
        return True
    return False


def _category_weight(category) -> int:
    order = {
        "wisdom": 7,
        "reasoning": 6,
        "meta_learning": 5,
        "communication": 4,
        "user_understanding": 4,
        "self_awareness": 3,
        "context": 2,
        "creativity": 1,
    }
    return int(order.get(getattr(category, "value", str(category)), 1))


def _select_insights(
    *,
    min_reliability: float = DEFAULT_MIN_RELIABILITY,
    min_validations: int = DEFAULT_MIN_VALIDATIONS,
    limit: int = DEFAULT_MAX_ITEMS,
    cognitive: Optional[CognitiveLearner] = None,
) -> List[CognitiveInsight]:
    cognitive = cognitive or CognitiveLearner()

    # Pull a larger ranked set to allow filtering without starving the output.
    raw = cognitive.get_ranked_insights(
        min_reliability=min_reliability,
        min_validations=min_validations,
        limit=max(int(limit or 0) * 3, int(limit or 0)),
        resolve_conflicts=True,
    )

    picked = [i for i in raw if not _is_low_value(i.insight)]

    picked.sort(
        key=lambda i: (_category_weight(i.category), cognitive.effective_reliability(i), i.times_validated, i.confidence),
        reverse=True,
    )

    # De-dupe by normalized insight text
    seen = set()
    deduped: List[CognitiveInsight] = []
    for ins in picked:
        key = _normalize_text(ins.insight)
        if not key or key in seen:
            continue
        seen.add(key)
        deduped.append(ins)
        if len(deduped) >= max(0, int(limit or 0)):
            break
    return deduped


def _load_promoted_lines(project_dir: Path) -> List[str]:
    lines: List[str] = []
    for name in ("CLAUDE.md", "AGENTS.md", "TOOLS.md", "SOUL.md"):
        path = project_dir / name
        if not path.exists():
            continue
        try:
            content = path.read_text(encoding="utf-8")
        except Exception:
            continue
        idx = content.find("## Spark Learnings")
        if idx == -1:
            continue
        tail = content[idx + len("## Spark Learnings") :]
        # Stop at next section header
        next_idx = tail.find("\n## ")
        block = tail if next_idx == -1 else tail[:next_idx]
        for raw in block.splitlines():
            s = raw.strip()
            if s.startswith("- "):
                lines.append(s[2:].strip())
    # De-dupe
    seen = set()
    out: List[str] = []
    for s in lines:
        key = _normalize_text(s)
        if not key or key in seen:
            continue
        seen.add(key)
        out.append(s)
    return out


def _format_context(
    insights: List[CognitiveInsight],
    promoted: List[str],
) -> str:
    lines = [
        "## Spark Bootstrap",
        "Auto-loaded high-confidence learnings from ~/.spark/cognitive_insights.json",
        f"Last updated: {datetime.now().isoformat(timespec='seconds')}",
        "",
    ]

    if not insights and not promoted:
        lines.append("No validated insights yet.")
        return "\n".join(lines).strip()

    for ins in insights:
        rel = f"{ins.reliability:.0%}"
        lines.append(
            f"- [{ins.category.value}] {ins.insight} ({rel} reliable, {ins.times_validated} validations)"
        )

    if promoted:
        lines.append("")
        lines.append("## Promoted Learnings (Docs)")
        for s in promoted[:DEFAULT_MAX_PROMOTED]:
            lines.append(f"- {s}")

    return "\n".join(lines).strip()


def sync_context(
    *,
    project_dir: Optional[Path] = None,
    min_reliability: float = DEFAULT_MIN_RELIABILITY,
    min_validations: int = DEFAULT_MIN_VALIDATIONS,
    limit: int = DEFAULT_MAX_ITEMS,
    include_promoted: bool = True,
) -> SyncStats:
    cognitive = CognitiveLearner()
    # Prune stale insights (conservative defaults)
    cognitive.prune_stale(max_age_days=180.0, min_effective=0.2)

    insights = _select_insights(
        min_reliability=min_reliability,
        min_validations=min_validations,
        limit=limit,
        cognitive=cognitive,
    )

    root = project_dir or Path.cwd()
    promoted = _load_promoted_lines(root) if include_promoted else []
    # De-dupe promoted vs selected insights
    seen = {_normalize_text(i.insight) for i in insights}
    promoted = [p for p in promoted if _normalize_text(p) not in seen]

    context = _format_context(insights, promoted)
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

    # Record sync stats for dashboard tracking
    try:
        tracker = get_sync_tracker()
        tracker.record_full_sync(targets, items_per_adapter=len(insights))
    except Exception:
        pass

    return SyncStats(
        targets=targets,
        selected=len(insights),
        promoted_selected=len(promoted),
    )


def main(argv: Optional[List[str]] = None) -> int:
    import argparse
    import json

    ap = argparse.ArgumentParser(description="Sync Spark bootstrap context to platforms")
    ap.add_argument("--project", "-p", default=None, help="Project root for file-based outputs")
    ap.add_argument("--min-reliability", type=float, default=DEFAULT_MIN_RELIABILITY)
    ap.add_argument("--min-validations", type=int, default=DEFAULT_MIN_VALIDATIONS)
    ap.add_argument("--limit", type=int, default=DEFAULT_MAX_ITEMS)
    ap.add_argument("--no-promoted", action="store_true", help="Skip promoted learnings from docs")
    args = ap.parse_args(argv)

    project_dir = Path(args.project).expanduser() if args.project else None
    stats = sync_context(
        project_dir=project_dir,
        min_reliability=args.min_reliability,
        min_validations=args.min_validations,
        limit=args.limit,
        include_promoted=(not args.no_promoted),
    )
    print(json.dumps({
        "selected": stats.selected,
        "promoted_selected": stats.promoted_selected,
        "targets": stats.targets,
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
