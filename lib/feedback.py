"""Lightweight feedback loop to improve skills + self-awareness reliability."""

from __future__ import annotations

import json
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional

from .cognitive_learner import get_cognitive_learner
from .skills_router import recommend_skills
from .outcome_log import append_outcomes, make_outcome_id


SKILLS_EFFECTIVENESS_FILE = Path.home() / ".spark" / "skills_effectiveness.json"


def _load_json(path: Path) -> Dict:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _save_json(path: Path, data: Dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")


def update_skill_effectiveness(query: str, success: bool, limit: int = 2) -> None:
    """Update skill effectiveness counters for top-matched skills."""
    q = (query or "").strip()
    if not q:
        return

    skills = recommend_skills(q, limit=limit)
    if not skills:
        return

    outcomes = []
    now = time.time()
    data = _load_json(SKILLS_EFFECTIVENESS_FILE)
    for s in skills:
        sid = s.get("skill_id") or s.get("name")
        if not sid:
            continue
        stats = data.get(sid, {"success": 0, "fail": 0})
        if success:
            stats["success"] = int(stats.get("success", 0)) + 1
        else:
            stats["fail"] = int(stats.get("fail", 0)) + 1
        data[sid] = stats
        outcomes.append({
            "outcome_id": make_outcome_id(str(now), "skill", sid, q[:120]),
            "event_type": "skill_result",
            "tool": None,
            "text": f"skill {sid} {'succeeded' if success else 'failed'} for {q[:120]}",
            "polarity": "pos" if success else "neg",
            "created_at": now,
            "domain": "skills",
            "skill_id": sid,
            "query": q[:200],
        })

    _save_json(SKILLS_EFFECTIVENESS_FILE, data)
    append_outcomes(outcomes)


def update_self_awareness_reliability(tool_name: str, success: bool) -> None:
    """Increment reliability counters for self-awareness insights about a tool."""
    t = (tool_name or "").lower().strip()
    if not t:
        return

    cog = get_cognitive_learner()
    updated = False
    for insight in cog.get_self_awareness_insights():
        if t in (insight.insight or "").lower():
            if success:
                insight.times_contradicted += 1
            else:
                insight.times_validated += 1
            insight.last_validated_at = datetime.now().isoformat()
            updated = True

    if updated:
        cog._save_insights()
