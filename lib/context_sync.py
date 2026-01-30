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
from .project_context import get_project_context, filter_insights_for_context
from .project_profile import load_profile, get_suggested_questions
from .exposure_tracker import record_exposures, infer_latest_session_id
from .sync_tracker import get_sync_tracker
from .outcome_checkin import list_checkins


DEFAULT_MIN_RELIABILITY = 0.7
DEFAULT_MIN_VALIDATIONS = 3
DEFAULT_MAX_ITEMS = 12
DEFAULT_MAX_PROMOTED = 6
DEFAULT_HIGH_VALIDATION_OVERRIDE = 50


@dataclass
class SyncStats:
    targets: Dict[str, str]
    selected: int
    promoted_selected: int
    diagnostics: Optional[Dict] = None


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


def _actionability_score(text: str) -> int:
    t = (text or "").lower()
    score = 0
    if "fix:" in t:
        score += 3
    if "avoid" in t or "never" in t:
        score += 2
    if "do " in t or "don't" in t or "should" in t or "must" in t:
        score += 1
    if "use " in t or "prefer" in t or "verify" in t or "check" in t:
        score += 1
    if "->" in t:
        score += 1
    return score


def _category_weight(category) -> int:
    order = {
        "wisdom": 7,
        "reasoning": 6,
        "meta_learning": 5,
        "communication": 4,
        "user_understanding": 4,
        "self_awareness": 5,
        "context": 2,
        "creativity": 1,
    }
    return int(order.get(getattr(category, "value", str(category)), 1))


def _select_insights(
    *,
    min_reliability: float = DEFAULT_MIN_RELIABILITY,
    min_validations: int = DEFAULT_MIN_VALIDATIONS,
    limit: int = DEFAULT_MAX_ITEMS,
    high_validation_override: int = DEFAULT_HIGH_VALIDATION_OVERRIDE,
    diagnostics: Optional[Dict] = None,
    cognitive: Optional[CognitiveLearner] = None,
    project_context: Optional[Dict] = None,
) -> List[CognitiveInsight]:
    cognitive = cognitive or CognitiveLearner()

    # Pull a larger ranked set to allow filtering without starving the output.
    raw = cognitive.get_ranked_insights(
        min_reliability=min_reliability,
        min_validations=min_validations,
        limit=max(int(limit or 0) * 3, int(limit or 0)),
        resolve_conflicts=True,
    )
    if diagnostics is not None:
        diagnostics.update({
            "min_reliability": min_reliability,
            "min_validations": min_validations,
            "limit": limit,
            "high_validation_override": high_validation_override,
            "raw_ranked": len(raw),
        })

    picked = [i for i in raw if not _is_low_value(i.insight)]
    if diagnostics is not None:
        diagnostics["filtered_low_value"] = max(0, len(raw) - len(picked))

    if high_validation_override and high_validation_override > 0:
        override_candidates = 0
        for ins in cognitive.insights.values():
            if ins.times_validated < high_validation_override:
                continue
            if _is_low_value(ins.insight):
                continue
            picked.append(ins)
            override_candidates += 1
        if diagnostics is not None:
            diagnostics["override_candidates"] = override_candidates

    if project_context is not None:
        before = len(picked)
        picked = filter_insights_for_context(picked, project_context)
        if diagnostics is not None:
            diagnostics["filtered_context"] = max(0, before - len(picked))

    picked.sort(
        key=lambda i: (
            _actionability_score(i.insight),
            _category_weight(i.category),
            cognitive.effective_reliability(i),
            i.times_validated,
            i.confidence,
        ),
        reverse=True,
    )

    # De-dupe by normalized insight text
    seen = set()
    deduped: List[CognitiveInsight] = []
    duplicates = 0
    for ins in picked:
        key = _normalize_text(ins.insight)
        if not key or key in seen:
            duplicates += 1
            continue
        seen.add(key)
        deduped.append(ins)
        if len(deduped) >= max(0, int(limit or 0)):
            break

    if diagnostics is not None:
        diagnostics.update({
            "deduped_unique": len(deduped),
            "duplicates_dropped": duplicates,
            "selected": [
                {
                    "category": i.category.value,
                    "insight": i.insight,
                    "reliability": round(cognitive.effective_reliability(i), 3),
                    "validations": i.times_validated,
                    "actionability": _actionability_score(i.insight),
                }
                for i in deduped[: min(5, len(deduped))]
            ],
        })

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
            entry = s[2:].strip()
            if entry and not _is_low_value(entry):
                lines.append(entry)
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
    project_profile: Optional[Dict[str, Any]] = None,
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

    if project_profile:
        done = project_profile.get("done") or ""
        goals = project_profile.get("goals") or []
        milestones = project_profile.get("milestones") or []
        phase = project_profile.get("phase") or ""
        references = project_profile.get("references") or []
        transfers = project_profile.get("transfers") or []
        lines.append("")
        lines.append("## Project Focus")
        if phase:
            lines.append(f"- Phase: {phase}")
        if done:
            lines.append(f"- Done means: {done}")
        if goals:
            for g in goals[:3]:
                lines.append(f"- Goal: {g.get('text') or g}")
        if milestones:
            for m in milestones[:3]:
                status = (m.get("meta") or {}).get("status") or ""
                tag = f" [{status}]" if status else ""
                lines.append(f"- Milestone: {m.get('text')}{tag}")
        if references:
            for r in references[:2]:
                lines.append(f"- Reference: {r.get('text') or r}")
        if transfers:
            for t in transfers[:2]:
                lines.append(f"- Transfer: {t.get('text') or t}")

        questions = get_suggested_questions(project_profile, limit=3)
        if questions:
            lines.append("")
            lines.append("## Project Questions")
            for q in questions:
                lines.append(f"- {q.get('question')}")

        checkins = list_checkins(limit=2)
        if checkins:
            lines.append("")
            lines.append("## Outcome Check-in")
            for item in checkins:
                reason = item.get("reason") or item.get("event") or "check-in"
                lines.append(f"- {reason}")

    if promoted:
        lines.append("")
        lines.append("## Promoted Learnings (Docs)")
        for s in promoted[:DEFAULT_MAX_PROMOTED]:
            lines.append(f"- {s}")

    return "\n".join(lines).strip()


def build_compact_context(
    *,
    project_dir: Optional[Path] = None,
    min_reliability: float = DEFAULT_MIN_RELIABILITY,
    min_validations: int = DEFAULT_MIN_VALIDATIONS,
    limit: int = 3,
    high_validation_override: int = DEFAULT_HIGH_VALIDATION_OVERRIDE,
) -> Tuple[str, int]:
    """Build a compact context block for agent prompt injection."""
    cognitive = CognitiveLearner()
    root = project_dir or Path.cwd()
    project_context = None
    try:
        project_context = get_project_context(root)
    except Exception:
        project_context = None

    insights = _select_insights(
        min_reliability=min_reliability,
        min_validations=min_validations,
        limit=limit,
        high_validation_override=high_validation_override,
        cognitive=cognitive,
        project_context=project_context,
    )
    return cognitive.format_for_injection(insights), len(insights)


def sync_context(
    *,
    project_dir: Optional[Path] = None,
    min_reliability: float = DEFAULT_MIN_RELIABILITY,
    min_validations: int = DEFAULT_MIN_VALIDATIONS,
    limit: int = DEFAULT_MAX_ITEMS,
    high_validation_override: int = DEFAULT_HIGH_VALIDATION_OVERRIDE,
    include_promoted: bool = True,
    diagnose: bool = False,
) -> SyncStats:
    cognitive = CognitiveLearner()
    # Prune stale insights (conservative defaults)
    cognitive.prune_stale(max_age_days=180.0, min_effective=0.2)

    root = project_dir or Path.cwd()
    project_context = None
    try:
        project_context = get_project_context(root)
    except Exception:
        project_context = None

    diagnostics: Optional[Dict] = {} if diagnose else None
    insights = _select_insights(
        min_reliability=min_reliability,
        min_validations=min_validations,
        limit=limit,
        high_validation_override=high_validation_override,
        diagnostics=diagnostics,
        cognitive=cognitive,
        project_context=project_context,
    )

    try:
        key_by_id = {id(v): k for k, v in cognitive.insights.items()}
        exposures = []
        for ins in insights:
            exposures.append({
                "insight_key": key_by_id.get(id(ins)),
                "category": ins.category.value,
                "text": ins.insight,
            })
        record_exposures("sync_context", exposures, session_id=infer_latest_session_id())
    except Exception:
        pass

    try:
        profile = load_profile(root)
        p_exposures = []
        if profile.get("done"):
            p_exposures.append({
                "insight_key": f"project:done:{profile.get('project_key')}",
                "category": "project_done",
                "text": profile.get("done"),
            })
        for m in profile.get("milestones") or []:
            p_exposures.append({
                "insight_key": f"project:milestone:{profile.get('project_key')}:{m.get('entry_id')}",
                "category": "project_milestone",
                "text": m.get("text"),
            })
        if p_exposures:
            record_exposures("sync_context:project", p_exposures, session_id=infer_latest_session_id())
    except Exception:
        pass

    promoted = _load_promoted_lines(root) if include_promoted else []
    # De-dupe promoted vs selected insights
    seen = {_normalize_text(i.insight) for i in insights}
    promoted = [p for p in promoted if _normalize_text(p) not in seen]

    profile = None
    try:
        profile = load_profile(root)
    except Exception:
        profile = None

    context = _format_context(insights, promoted, project_profile=profile)
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
        diagnostics=diagnostics,
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
