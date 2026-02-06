"""Project profile and questioning helpers.

Lightweight, local-only storage for project-level goals, decisions, and domain insights.
"""

from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from lib.diagnostics import log_debug
from lib.memory_banks import infer_project_key
from lib.project_context import get_project_context


PROJECT_DIR = Path.home() / ".spark" / "projects"


def _get_chip_questions(phase: Optional[str] = None) -> List[Dict[str, Any]]:
    """Get questions from active chips."""
    try:
        from lib.chips.registry import get_registry
        registry = get_registry()
        return registry.get_active_questions(phase=phase)
    except Exception:
        return []

DOMAIN_QUESTIONS: Dict[str, List[Dict[str, str]]] = {
    "game_dev": [
        {"id": "game_core_loop", "category": "done", "question": "What makes the core loop satisfying?"},
        {"id": "game_feedback", "category": "quality", "question": "What immediate feedback must the player feel?"},
        {"id": "game_physics", "category": "insight", "question": "Any critical physics balance or tuning rules?"},
        {"id": "game_pacing", "category": "quality", "question": "What pace feels right for this experience?"},
        {"id": "game_definition_done", "category": "done", "question": "How will we know the game feels complete?"},
        {"id": "game_reference", "category": "reference", "question": "What real-world system or game should we reference?"},
        {"id": "game_transfer", "category": "transfer", "question": "What transferable heuristic should we capture for future projects?"},
    ],
    "product": [
        {"id": "product_activation", "category": "metric", "question": "What is the activation metric for this product?"},
        {"id": "product_value", "category": "done", "question": "What does 'done' mean for users?"},
        {"id": "product_onboarding", "category": "quality", "question": "Where do users struggle in onboarding?"},
        {"id": "product_kpi", "category": "metric", "question": "Which KPI matters most right now?"},
        {"id": "product_risk", "category": "risk", "question": "What could make this fail after launch?"},
    ],
    "marketing": [
        {"id": "mkt_audience", "category": "goal", "question": "Who is the primary audience?"},
        {"id": "mkt_kpi", "category": "metric", "question": "What is the primary KPI (CTR, CAC, MQL)?"},
        {"id": "mkt_message", "category": "insight", "question": "What message or hook should resonate most?"},
        {"id": "mkt_channel", "category": "strategy", "question": "Which channel is most important?"},
        {"id": "mkt_done", "category": "done", "question": "What does success look like for this campaign?"},
    ],
    "org": [
        {"id": "org_goal", "category": "goal", "question": "What operational outcome matters most?"},
        {"id": "org_bottleneck", "category": "risk", "question": "Where is the main bottleneck or handoff risk?"},
        {"id": "org_metric", "category": "metric", "question": "Which metric tells us we're improving?"},
        {"id": "org_decision", "category": "decision", "question": "What hard decision are we making now?"},
        {"id": "org_done", "category": "done", "question": "What does 'done' mean operationally?"},
    ],
    "engineering": [
        {"id": "eng_arch", "category": "decision", "question": "What architecture decision matters most?"},
        {"id": "eng_risk", "category": "risk", "question": "What will cause problems later if ignored?"},
        {"id": "eng_done", "category": "done", "question": "What signals completion beyond tests passing?"},
        {"id": "eng_perf", "category": "quality", "question": "What performance or reliability target matters?"},
        {"id": "eng_constraint", "category": "goal", "question": "What constraints must we respect?"},
    ],
    "general": [
        {"id": "gen_goal", "category": "goal", "question": "What is the project goal in one sentence?"},
        {"id": "gen_done", "category": "done", "question": "How will we know it's complete?"},
        {"id": "gen_risk", "category": "risk", "question": "What could make this fail later?"},
        {"id": "gen_quality", "category": "quality", "question": "What quality signal matters most?"},
        {"id": "gen_feedback", "category": "feedback", "question": "Who gives feedback and how often?"},
        {"id": "gen_reference", "category": "reference", "question": "What existing system or example are we referencing?"},
        {"id": "gen_transfer", "category": "transfer", "question": "What principle should carry into other projects?"},
    ],
}

PHASE_QUESTIONS: Dict[str, List[Dict[str, str]]] = {
    "discovery": [
        {"id": "phase_problem", "category": "goal", "question": "What problem are we solving and for whom?"},
        {"id": "phase_constraints", "category": "risk", "question": "What constraints must we respect?"},
    ],
    "prototype": [
        {"id": "phase_loop", "category": "done", "question": "What must feel good in the prototype?"},
        {"id": "phase_risk", "category": "risk", "question": "What risk should we validate next?"},
    ],
    "polish": [
        {"id": "phase_quality", "category": "quality", "question": "What quality bar must be met (feel, UX, stability)?"},
        {"id": "phase_cohesion", "category": "quality", "question": "Where is cohesion or consistency still weak?"},
    ],
    "launch": [
        {"id": "phase_success", "category": "metric", "question": "Which metric defines launch success?"},
        {"id": "phase_post", "category": "risk", "question": "What could fail after launch?"},
    ],
}

DOMAIN_PHASE_QUESTIONS: Dict[str, List[Dict[str, str]]] = {
    "game_dev:prototype": [
        {"id": "game_proto_feedback", "category": "feedback", "question": "What immediate player feedback is critical?"},
        {"id": "game_proto_balance", "category": "insight", "question": "Any tuning or balance rule that must hold?"},
    ],
    "marketing:launch": [
        {"id": "mkt_launch_kpi", "category": "metric", "question": "What KPI tells us this launch worked?"},
    ],
    "org:polish": [
        {"id": "org_polish_bottleneck", "category": "risk", "question": "Which bottleneck still slows execution?"},
    ],
}


def _now() -> float:
    return time.time()


def _hash_id(*parts: str) -> str:
    raw = "|".join(str(p or "") for p in parts).encode("utf-8")
    return hashlib.sha1(raw).hexdigest()[:12]


def _default_profile(project_key: str, domain: str) -> Dict[str, Any]:
    return {
        "project_key": project_key,
        "domain": domain,
        "created_at": _now(),
        "updated_at": _now(),
        "phase": "discovery",
        "questions": [],
        "answers": [],
        "goals": [],
        "done": "",
        "done_history": [],
        "milestones": [],
        "decisions": [],
        "insights": [],
        "feedback": [],
        "risks": [],
        "references": [],
        "transfers": [],
    }


def _profile_path(project_key: str) -> Path:
    PROJECT_DIR.mkdir(parents=True, exist_ok=True)
    return PROJECT_DIR / f"{project_key}.json"


def infer_domain(project_dir: Optional[Path] = None, hint: Optional[str] = None) -> str:
    if hint:
        return hint

    root = Path(project_dir or Path.cwd()).resolve()
    name = root.name.lower()
    try:
        ctx = get_project_context(root)
    except Exception:
        ctx = {}

    tokens = " ".join([name] + (ctx.get("languages") or []) + (ctx.get("frameworks") or []) + (ctx.get("tools") or []))
    tokens = tokens.lower()

    if any(t in tokens for t in ("unity", "godot", "unreal", "pygame", "phaser", "game")):
        return "game_dev"
    if any(t in tokens for t in ("marketing", "campaign", "seo", "growth")):
        return "marketing"
    if any(t in tokens for t in ("org", "ops", "operations", "process")):
        return "org"
    if any(t in tokens for t in ("product", "saas", "onboarding")):
        return "product"
    if any(t in tokens for t in ("backend", "api", "service", "infra")):
        return "engineering"

    return "general"


def get_project_key(project_dir: Optional[Path] = None) -> str:
    key = infer_project_key()
    if key:
        return key
    root = Path(project_dir or Path.cwd()).resolve()
    return root.name or "default"


def load_profile(project_dir: Optional[Path] = None) -> Dict[str, Any]:
    project_key = get_project_key(project_dir)
    path = _profile_path(project_key)
    if not path.exists():
        domain = infer_domain(project_dir)
        return _default_profile(project_key, domain)
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            raise ValueError("invalid_profile")
        if not data.get("phase"):
            data["phase"] = "discovery"
            save_profile(data)
        return data
    except Exception as e:
        log_debug("project_profile", "load_profile failed", e)
        domain = infer_domain(project_dir)
        return _default_profile(project_key, domain)


def save_profile(profile: Dict[str, Any]) -> None:
    project_key = profile.get("project_key") or "default"
    profile["updated_at"] = _now()
    path = _profile_path(project_key)
    path.write_text(json.dumps(profile, indent=2), encoding="utf-8")


def list_profiles() -> List[Dict[str, Any]]:
    PROJECT_DIR.mkdir(parents=True, exist_ok=True)
    profiles: List[Dict[str, Any]] = []
    for path in PROJECT_DIR.glob("*.json"):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                profiles.append(data)
        except Exception:
            continue
    return profiles


def ensure_questions(profile: Dict[str, Any]) -> int:
    domain = profile.get("domain") or "general"
    phase = profile.get("phase") or "discovery"
    pool = []
    pool.extend(DOMAIN_QUESTIONS.get(domain, DOMAIN_QUESTIONS["general"]))
    pool.extend(PHASE_QUESTIONS.get(phase, []))
    pool.extend(DOMAIN_PHASE_QUESTIONS.get(f"{domain}:{phase}", []))
    existing = {q.get("id") for q in profile.get("questions", []) if isinstance(q, dict)}
    added = 0
    for q in pool:
        if q["id"] in existing:
            continue
        profile.setdefault("questions", []).append({
            "id": q["id"],
            "category": q["category"],
            "question": q["question"],
            "asked_at": None,
            "answered_at": None,
        })
        added += 1
    if added:
        save_profile(profile)
    return added


def get_suggested_questions(profile: Dict[str, Any], limit: int = 3, include_chips: bool = True) -> List[Dict[str, Any]]:
    ensure_questions(profile)
    questions = profile.get("questions") or []
    unanswered = [q for q in questions if not q.get("answered_at")]
    extra = []
    if not profile.get("done"):
        extra.append({"category": "done", "id": "proj_done", "question": "How will you know this is complete?"})
    if not profile.get("goals"):
        extra.append({"category": "goal", "id": "proj_goal", "question": "What is the primary goal for this project?"})
    if not profile.get("milestones"):
        extra.append({"category": "milestone", "id": "proj_milestone", "question": "What is the next milestone?"})
    references = profile.get("references") or []
    transfers = profile.get("transfers") or []
    if references and len(transfers) < len(references):
        ref_text = (references[-1].get("text") or "").strip()
        ref_snip = ref_text[:80] + ("..." if len(ref_text) > 80 else "")
        prompt = "What principle should transfer from the latest reference?"
        if ref_snip:
            prompt = f"{prompt} ({ref_snip})"
        extra.append({"category": "transfer", "id": "proj_transfer", "question": prompt})

    # Include chip questions (Phase 5)
    chip_questions = []
    if include_chips:
        phase = profile.get("phase")
        answered_ids = {a.get("question_id") for a in profile.get("answers", [])}
        for cq in _get_chip_questions(phase=phase):
            if cq.get("id") not in answered_ids:
                chip_questions.append({
                    "id": cq["id"],
                    "category": cq.get("category", "goal"),
                    "question": cq["question"],
                    "chip_id": cq.get("chip_id"),
                    "affects_learning": cq.get("affects_learning", []),
                })

    return (unanswered + extra + chip_questions)[: max(1, int(limit or 3))]


def record_answer(profile: Dict[str, Any], question_id: str, answer: str) -> Optional[Dict[str, Any]]:
    if not question_id or not answer:
        return None
    now = _now()
    questions = profile.get("questions") or []
    found = None
    for q in questions:
        if q.get("id") == question_id:
            q["answered_at"] = now
            found = q
            break
    entry = {
        "question_id": question_id,
        "answer": answer.strip(),
        "category": (found.get("category") if found else "general"),
        "answered_at": now,
    }
    profile.setdefault("answers", []).append(entry)
    save_profile(profile)
    return entry


def record_entry(profile: Dict[str, Any], entry_type: str, text: str, meta: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    now = _now()
    entry = {
        "entry_id": _hash_id(profile.get("project_key") or "", entry_type, (text or "").strip()[:160]),
        "text": (text or "").strip(),
        "created_at": now,
        "meta": meta or {},
    }
    target = entry_type
    if entry_type == "done":
        target = "done_history"
    if entry_type == "reference":
        target = "references"
    if entry_type == "transfer":
        target = "transfers"
    bucket = profile.setdefault(target, [])
    if isinstance(bucket, list):
        bucket.append(entry)
    else:
        profile[target] = [entry]
    save_profile(profile)
    return entry


def set_phase(profile: Dict[str, Any], phase: str) -> None:
    phase_val = (phase or "").strip().lower()
    if not phase_val:
        return
    profile["phase"] = phase_val
    record_entry(profile, "phase_history", f"phase -> {phase_val}", meta={})


def completion_score(profile: Dict[str, Any]) -> Dict[str, Any]:
    done = bool(profile.get("done"))
    goals = profile.get("goals") or []
    milestones = profile.get("milestones") or []
    questions = profile.get("questions") or []
    answered = len([q for q in questions if q.get("answered_at")])
    insights = profile.get("insights") or []
    decisions = profile.get("decisions") or []
    feedback = profile.get("feedback") or []
    risks = profile.get("risks") or []
    references = profile.get("references") or []
    transfers = profile.get("transfers") or []

    done_score = 20 if done else 0
    goals_score = 10 if goals else 0
    q_score = int((answered / max(1, len(questions))) * 20) if questions else 0

    if milestones:
        done_count = 0
        for m in milestones:
            status = (m.get("meta") or {}).get("status") or ""
            if str(status).lower() in ("done", "complete", "completed"):
                done_count += 1
        milestone_score = int((done_count / max(1, len(milestones))) * 25)
    else:
        milestone_score = 0

    phase = (profile.get("phase") or "discovery").lower()
    phase_score = {"discovery": 2, "prototype": 5, "polish": 8, "launch": 10}.get(phase, 2)

    craft_count = len(insights) + len(decisions) + len(feedback) + len(risks) + len(references) + len(transfers)
    craft_score = min(15, craft_count * 3)

    total = min(100, done_score + goals_score + q_score + milestone_score + phase_score + craft_score)
    return {
        "score": total,
        "done": done_score,
        "goals": goals_score,
        "questions": q_score,
        "milestones": milestone_score,
        "phase": phase_score,
        "craft": craft_score,
    }
