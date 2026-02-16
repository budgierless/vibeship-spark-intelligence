#!/usr/bin/env python3
"""
Spark Dashboard - True Vibeship Style

Run with: python3 dashboard.py
Open: http://localhost:<dashboard-port>
"""

import json
import time
import sqlite3
import os
from datetime import datetime
from pathlib import Path
from typing import Optional
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
import threading
import webbrowser
from typing import Dict, List, Any, Callable
from urllib import request
from urllib.parse import urlparse, parse_qs

import sys
sys.path.insert(0, str(Path(__file__).parent))

from lib.cognitive_learner import CognitiveLearner, CognitiveCategory
from lib.mind_bridge import MindBridge
from lib.sync_tracker import get_sync_tracker
from lib.promoter import Promoter
from lib.queue import get_queue_stats, read_recent_events, count_events
from lib.aha_tracker import AhaTracker
from lib.spark_voice import SparkVoice
from lib.growth_tracker import GrowthTracker
from lib.resonance import get_resonance_display
from lib.dashboard_project import get_active_project, get_project_memory_preview
from lib.taste_api import add_from_dashboard
from lib.diagnostics import setup_component_logging, log_exception
from lib.ports import DASHBOARD_PORT, PULSE_PORT, META_RALPH_PORT, MIND_HEALTH_URL
from lib.run_log import get_recent_runs, get_run_detail, get_run_kpis
from lib.advisory_preferences import (
    setup_questions as advisory_setup_questions,
    get_current_preferences as advisory_get_current_preferences,
    apply_preferences as advisory_apply_preferences,
)

# Service control
from lib.service_control import service_status

# EIDOS integration
try:
    from lib.eidos import (
        get_store, get_elevated_control_plane,
        get_truth_ledger, get_policy_patch_engine,
        get_minimal_mode_controller,
        get_acceptance_compiler,
        get_deferred_tracker,
        get_evidence_store,
        WatcherEngine,
        WatcherSeverity,
        WatcherType,
        Phase,
        Outcome,
        DistillationType,
        Evaluation,
        EscalationType,
        build_escalation,
        MinimalModeReason,
    )
    HAS_EIDOS = True
except ImportError:
    HAS_EIDOS = False

PORT = DASHBOARD_PORT
SPARK_DIR = Path.home() / ".spark"
QUEUE_FILE = SPARK_DIR / "queue" / "events.jsonl"
QUEUE_LOCK_FILE = SPARK_DIR / "queue" / ".queue.lock"
INVALID_EVENTS_FILE = SPARK_DIR / "invalid_events.jsonl"
OUTCOMES_FILE = SPARK_DIR / "outcomes.jsonl"
BRIDGE_HEARTBEAT_FILE = SPARK_DIR / "bridge_worker_heartbeat.json"
WATCHDOG_STATE_FILE = SPARK_DIR / "watchdog_state.json"
EIDOS_ACTIVE_EPISODES_FILE = SPARK_DIR / "eidos_active_episodes.json"
EIDOS_ACTIVE_STEPS_FILE = SPARK_DIR / "eidos_active_steps.json"
EIDOS_ESCALATIONS_FILE = SPARK_DIR / "eidos_escalations.jsonl"
MINIMAL_MODE_HISTORY_FILE = SPARK_DIR / "minimal_mode_history.jsonl"
OPPORTUNITY_DIR = SPARK_DIR / "opportunity_scanner"
OPPORTUNITY_SELF_FILE = OPPORTUNITY_DIR / "self_opportunities.jsonl"
OPPORTUNITY_OUTCOMES_FILE = OPPORTUNITY_DIR / "outcomes.jsonl"


def get_eidos_status():
    """Get EIDOS system status for dashboard footer."""
    if not HAS_EIDOS:
        return {"available": False, "reason": "not installed"}

    try:
        store = get_store()
        ecp = get_elevated_control_plane()
        ledger = get_truth_ledger()
        patches = get_policy_patch_engine()
        minimal = get_minimal_mode_controller()

        stats = store.get_stats()
        mm_stats = minimal.get_stats()
        patch_stats = patches.get_stats()
        tl_stats = ledger.get_stats()

        return {
            "available": True,
            "episodes": stats["episodes"],
            "steps": stats["steps"],
            "success_rate": stats["success_rate"],
            "alerts": len(ecp.watcher_engine.alert_history),
            "minimal_mode": mm_stats["currently_active"],
            "active_patches": patch_stats["enabled"],
            "truths": tl_stats["total"],
            "facts": tl_stats["facts"],
        }
    except Exception as e:
        return {"available": False, "reason": str(e)}
SKILLS_INDEX_FILE = SPARK_DIR / "skills_index.json"
SKILLS_EFFECTIVENESS_FILE = SPARK_DIR / "skills_effectiveness.json"
ORCH_DIR = SPARK_DIR / "orchestration"
ORCH_AGENTS_FILE = ORCH_DIR / "agents.json"
ORCH_HANDOFFS_FILE = ORCH_DIR / "handoffs.jsonl"
LOGO_FILE = Path(__file__).parent / "logo.png"


def _to_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except Exception:
        return default


def _to_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except Exception:
        return default


def _get_advisory_setup_payload() -> Dict[str, Any]:
    current = advisory_get_current_preferences()
    setup = advisory_setup_questions(current=current)
    return {
        "ok": True,
        "preferences": current,
        "setup": setup,
    }


def _apply_advisory_preferences_payload(payload: Dict[str, Any]) -> Dict[str, Any]:
    body = payload if isinstance(payload, dict) else {}
    memory_mode = body.get("memory_mode")
    guidance_style = body.get("guidance_style")
    source = str(body.get("source") or "dashboard")
    return advisory_apply_preferences(
        memory_mode=memory_mode,
        guidance_style=guidance_style,
        source=source,
    )


def _build_advisory_status_block(engine_status: Dict[str, Any], now_ts: Optional[float] = None) -> Dict[str, Any]:
    """Compact advisory-engine status for dashboard/operator surfaces."""
    status = engine_status if isinstance(engine_status, dict) else {}
    now = _to_float(now_ts, time.time()) if now_ts is not None else time.time()

    badge_raw = status.get("delivery_badge") if isinstance(status.get("delivery_badge"), dict) else {}
    state = str(badge_raw.get("state") or "blocked").strip().lower()
    if state not in {"live", "fallback", "blocked", "stale"}:
        state = "blocked"
    delivery_badge = {
        "state": state,
        "reason": str(badge_raw.get("reason") or ""),
        "age_s": _to_float(badge_raw.get("age_s"), 0.0) if badge_raw.get("age_s") is not None else None,
        "event": str(badge_raw.get("event") or ""),
        "delivery_mode": str(badge_raw.get("delivery_mode") or ""),
    }

    recent_events = status.get("recent_events")
    latest_event = None
    if isinstance(recent_events, list) and recent_events:
        last = recent_events[-1] if isinstance(recent_events[-1], dict) else {}
        ts = _to_float(last.get("ts"), 0.0)
        latest_event = {
            "event": str(last.get("event") or ""),
            "route": str(last.get("route") or ""),
            "tool": str(last.get("tool") or ""),
            "age_s": round(max(0.0, now - ts), 1) if ts > 0 else None,
        }

    packet = status.get("packet_store") if isinstance(status.get("packet_store"), dict) else {}
    worker = status.get("prefetch_worker") if isinstance(status.get("prefetch_worker"), dict) else {}
    synth = status.get("synthesizer") if isinstance(status.get("synthesizer"), dict) else {}

    return {
        "available": True,
        "enabled": bool(status.get("enabled")),
        "delivery_badge": delivery_badge,
        "emission_rate": _to_float(status.get("emission_rate"), 0.0),
        "total_events": _to_int(status.get("total_events"), 0),
        "latest_event": latest_event,
        "packet_store": {
            "queue_depth": _to_int(packet.get("queue_depth"), 0),
            "hit_rate": _to_float(packet.get("hit_rate"), 0.0),
            "active_packets": _to_int(packet.get("active_packets"), 0),
            "fresh_packets": _to_int(packet.get("fresh_packets"), 0),
        },
        "prefetch_worker": {
            "pending_jobs": _to_int(worker.get("pending_jobs"), 0),
            "paused": bool(worker.get("paused")),
        },
        "synthesizer": {
            "tier_label": str(synth.get("tier_label") or ""),
            "provider": str(synth.get("preferred_provider") or ""),
        },
    }


def _advisory_status_unavailable(error: str = "") -> Dict[str, Any]:
    return {
        "available": False,
        "enabled": False,
        "delivery_badge": {
            "state": "blocked",
            "reason": "status_unavailable",
            "age_s": None,
            "event": "",
            "delivery_mode": "",
        },
        "emission_rate": 0.0,
        "total_events": 0,
        "latest_event": None,
        "packet_store": {
            "queue_depth": 0,
            "hit_rate": 0.0,
            "active_packets": 0,
            "fresh_packets": 0,
        },
        "prefetch_worker": {
            "pending_jobs": 0,
            "paused": False,
        },
        "synthesizer": {
            "tier_label": "",
            "provider": "",
        },
        "error": error,
    }


def _get_advisory_status_block(fetch_status: Optional[Callable[[], Dict[str, Any]]] = None) -> Dict[str, Any]:
    try:
        if fetch_status is None:
            from lib.advisory_engine import get_engine_status as fetch_status
        return _build_advisory_status_block(fetch_status())
    except Exception as e:
        return _advisory_status_unavailable(str(e))


def _get_process_memory_mb() -> Optional[float]:
    try:
        import psutil  # type: ignore
        rss = psutil.Process(os.getpid()).memory_info().rss
        return round(rss / (1024 * 1024), 2)
    except Exception:
        return None

def get_dashboard_data():
    """Gather all status data - fresh from disk each time for real-time updates."""
    cognitive = CognitiveLearner()  # Fresh instance, reads from disk
    cognitive_stats = cognitive.get_stats()
    insights_list = []
    for key, insight in sorted(cognitive.insights.items(), 
                                key=lambda x: x[1].created_at, reverse=True)[:8]:
        insights_list.append({
            "category": insight.category.value,
            "insight": insight.insight[:70],
            "reliability": insight.reliability,
            "validations": insight.times_validated,
            "promoted": insight.promoted,
        })
    
    bridge = MindBridge()  # Fresh instance
    mind_stats = bridge.get_stats()
    
    sync_tracker = get_sync_tracker()  # Fresh instance
    sync_stats = sync_tracker.get_stats()
    
    promoter = Promoter()  # Fresh instance
    promo_stats = promoter.get_promotion_status()
    
    queue_stats = get_queue_stats()
    recent_events = read_recent_events(5)
    events_list = []
    for event in reversed(recent_events):
        events_list.append({
            "type": event.event_type.value,
            "tool": event.tool_name or "—",
            "success": not event.error,
            "time": datetime.fromtimestamp(event.timestamp).strftime("%H:%M:%S")
        })
    
    # Aha tracker data - fresh from disk
    aha = AhaTracker()
    aha_stats = aha.get_stats()
    surprises = aha.get_recent_surprises(25)
    surprises_list = []
    for s in surprises:
        # Support both dicts (current storage) and dataclass-like objects (legacy)
        if isinstance(s, dict):
            surprise_type = s.get("surprise_type", "unknown")
            predicted_outcome = s.get("predicted_outcome", "") or ""
            actual_outcome = s.get("actual_outcome", "") or ""
            confidence_gap = s.get("confidence_gap", 0)
            lesson_extracted = s.get("lesson_extracted")
        else:
            surprise_type = getattr(s, "surprise_type", "unknown")
            predicted_outcome = getattr(s, "predicted_outcome", "") or ""
            actual_outcome = getattr(s, "actual_outcome", "") or ""
            confidence_gap = getattr(s, "confidence_gap", 0)
            lesson_extracted = getattr(s, "lesson_extracted", None)
        surprises_list.append({
            "type": str(surprise_type).replace("_", " ").title(),
            "predicted": predicted_outcome[:50],
            "actual": actual_outcome[:50],
            "gap": confidence_gap,
            "lesson": lesson_extracted[:60] if lesson_extracted else None
        })
    
    # Voice data - fresh from disk
    voice = SparkVoice()
    voice_stats = voice.get_stats()
    # Show most relevant opinions (not only "strong"), so the dashboard visibly evolves.
    opinions_all = voice.get_opinions()
    # Display the most recent opinions so changes show up immediately (and allow scrolling).
    opinions_all.sort(key=lambda o: o.formed_at, reverse=True)
    opinions = opinions_all[:25]
    opinions_list = [{"topic": o.topic, "preference": o.preference, "strength": o.strength} for o in opinions]

    growth = voice.get_recent_growth(10)
    growth_list = [{"before": g.before, "after": g.after} for g in growth]
    
    # Growth tracker - fresh from disk
    growth_tracker = GrowthTracker()
    growth_narrative = growth_tracker.get_growth_narrative()
    
    # Resonance - connection depth
    resonance = get_resonance_display()

    # Project inference + bank preview (MVP)
    project_key = get_active_project()
    project_mem = get_project_memory_preview(project_key, limit=5)
    
    return {
        "timestamp": datetime.now().strftime("%H:%M:%S"),
        "cognitive": {
            "total": cognitive_stats["total_insights"],
            "avg_reliability": cognitive_stats["avg_reliability"],
            "promoted": cognitive_stats["promoted_count"],
            "by_category": cognitive_stats["by_category"],
            "insights": insights_list
        },
        "mind": {
            "available": mind_stats["mind_available"],
            "synced": mind_stats["synced_count"],
            "queue": mind_stats["offline_queue_size"],
        },
        "outputs": {
            "last_sync": sync_stats["last_sync"],
            "total_syncs": sync_stats["total_syncs"],
            "adapters_ok": sync_stats["adapters_ok"],
            "adapters_error": sync_stats["adapters_error"],
            "adapters": sync_stats["adapters"],
        },
        "promotions": {
            "ready": promo_stats["ready_for_promotion"],
            "promoted": promo_stats["promoted_count"],
            "by_target": promo_stats["by_target"]
        },
        "queue": {
            "events": queue_stats["event_count"],
            "recent": events_list
        },
        "surprises": {
            "total": aha_stats["total_captured"],
            "successes": aha_stats["unexpected_successes"],
            "failures": aha_stats["unexpected_failures"],
            "lessons": aha_stats["lessons_extracted"],
            "recent": surprises_list
        },
        "voice": {
            "age_days": voice_stats["age_days"],
            "interactions": voice_stats["interactions"],
            "opinions_count": voice_stats["opinions_formed"],
            "growth_count": voice_stats["growth_moments"],
            "opinions": opinions_list,
            "growth": growth_list,
            "status": voice.get_status_voice()
        },
        "narrative": growth_narrative,
        "resonance": resonance,
        "project": {
            "active": project_key,
            "memories": project_mem,
        },
        "taste": {
            "stats": __import__("lib.tastebank", fromlist=["stats"]).stats(),
            "recent": __import__("lib.tastebank", fromlist=["recent"]).recent(limit=5),
        },
        "advisory": _get_advisory_status_block(),
        "opportunity_scanner": _get_opportunity_scanner_snapshot(),
        "eidos": get_eidos_status(),
        "systems": {
            "mind": {"ok": mind_stats["mind_available"], "label": "Mind API"},
            "cognitive": {"ok": cognitive_stats["total_insights"] > 0, "label": "Cognitive Learner"},
            "eidos": {"ok": HAS_EIDOS and get_eidos_status().get("available", False), "label": "EIDOS Control"},
            "queue": {"ok": True, "label": "Event Queue"},
            "voice": {"ok": voice_stats["age_days"] >= 0, "label": "Spark Voice"},
        }
    }


def _load_json(path: Path) -> Dict:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _http_ok(url: str, timeout: float = 3.0) -> bool:
    """Check if URL returns 2xx. Timeout increased from 1.5s to reduce false negatives."""
    try:
        req = request.Request(url, method="GET")
        with request.urlopen(req, timeout=timeout) as resp:
            return 200 <= resp.status < 300
    except Exception:
        return False


def _read_jsonl(path: Path, limit: Optional[int] = None) -> List[Dict[str, Any]]:
    if not path.exists():
        return []
    items: List[Dict[str, Any]] = []
    try:
        with path.open("r", encoding="utf-8") as f:
            for line in f:
                raw = line.strip()
                if not raw:
                    continue
                try:
                    items.append(json.loads(raw))
                except Exception:
                    continue
    except Exception:
        return []

    if limit and limit > 0:
        return items[-limit:]
    return items


def _get_opportunity_scanner_snapshot(limit: int = 5, max_age_s: float = 172800.0) -> Dict[str, Any]:
    status = {"enabled": False, "user_scan_enabled": False, "self_recent": 0}
    try:
        from lib.opportunity_scanner import get_scanner_status

        status = get_scanner_status()
    except Exception:
        pass

    now = time.time()
    rows = _read_jsonl(OPPORTUNITY_SELF_FILE, limit=400)
    outcomes = _read_jsonl(OPPORTUNITY_OUTCOMES_FILE, limit=400)

    recent_rows: List[Dict[str, Any]] = []
    seen_questions: set[str] = set()
    scanned_recent = 0
    for row in reversed(rows):
        ts = _to_float(row.get("ts"), 0.0)
        if ts <= 0:
            continue
        if max_age_s > 0 and (now - ts) > max_age_s:
            continue
        scanned_recent += 1
        question = str(row.get("question") or "").strip()
        if not question:
            continue
        key = question.lower()
        if key in seen_questions:
            continue
        seen_questions.add(key)
        recent_rows.append(
            {
                "ts": ts,
                "category": str(row.get("category") or "general"),
                "priority": str(row.get("priority") or "medium"),
                "question": question[:140],
                "next_step": str(row.get("next_step") or "")[:160],
            }
        )
        if len(recent_rows) >= max(1, int(limit or 1)):
            break

    adopted_recent = 0
    acted_total = 0
    for row in reversed(outcomes):
        ts = _to_float(row.get("ts"), 0.0)
        if ts <= 0:
            continue
        if max_age_s > 0 and (now - ts) > max_age_s:
            continue
        acted = bool(row.get("acted_on"))
        if not acted:
            continue
        acted_total += 1
        if bool(row.get("improved")):
            adopted_recent += 1

    if acted_total > 0:
        adoption_rate = round(adopted_recent / max(acted_total, 1), 4)
    else:
        fallback_adopted = len([r for r in rows if isinstance(r, dict) and bool(r.get("adopted"))])
        fallback_total = len([r for r in rows if isinstance(r, dict)])
        adoption_rate = round(fallback_adopted / max(fallback_total, 1), 4) if fallback_total > 0 else 0.0

    return {
        "enabled": bool(status.get("enabled")),
        "user_scan_enabled": bool(status.get("user_scan_enabled")),
        "self_recent": int(status.get("self_recent") or 0),
        "scanned_recent": int(scanned_recent),
        "acted_total": int(acted_total),
        "adopted_recent": int(adopted_recent),
        "adoption_rate": float(adoption_rate),
        "latest": recent_rows,
    }


def _count_jsonl(path: Path, max_lines: Optional[int] = None) -> int:
    if not path.exists():
        return 0
    count = 0
    try:
        with path.open("r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    count += 1
                    if max_lines and count >= max_lines:
                        break
    except Exception:
        return 0
    return count


def _append_jsonl(path: Path, payload: Dict[str, Any]) -> None:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(payload) + "\n")
    except Exception:
        return


def get_trace_timeline_data(trace_id: str) -> Dict[str, Any]:
    if not trace_id:
        return {"trace_id": trace_id, "steps": [], "evidence": [], "outcomes": [], "episodes": []}
    if not HAS_EIDOS:
        return {"trace_id": trace_id, "steps": [], "evidence": [], "outcomes": [], "episodes": [], "available": False}

    store = _get_eidos_store_safe()
    if not store:
        return {"trace_id": trace_id, "steps": [], "evidence": [], "outcomes": [], "episodes": [], "available": False}

    steps: List[Dict[str, Any]] = []
    episodes: List[Dict[str, Any]] = []
    evidence_rows: List[Dict[str, Any]] = []
    outcomes: List[Dict[str, Any]] = []

    try:
        with sqlite3.connect(store.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                "SELECT * FROM steps WHERE trace_id = ? ORDER BY created_at",
                (trace_id,),
            ).fetchall()
        step_objs = [store._row_to_step(r) for r in rows]
    except Exception:
        step_objs = []

    if step_objs:
        for step in step_objs:
            tool = ""
            try:
                tool = step.action_details.get("tool") or ""
            except Exception:
                tool = ""
            steps.append({
                "step_id": step.step_id,
                "episode_id": step.episode_id,
                "intent": (step.intent or "")[:80],
                "decision": (step.decision or "")[:80],
                "tool": tool,
                "evaluation": step.evaluation.value if hasattr(step.evaluation, "value") else str(step.evaluation),
                "validated": bool(step.validated),
                "created_at": step.created_at,
                "result": (step.result or "")[:160],
            })

        episode_ids = sorted({s.episode_id for s in step_objs if s.episode_id})
        for ep_id in episode_ids:
            ep = store.get_episode(ep_id)
            if not ep:
                continue
            episodes.append({
                "episode_id": ep.episode_id,
                "goal": ep.goal,
                "phase": ep.phase.value,
                "outcome": ep.outcome.value,
                "step_count": ep.step_count,
                "start_ts": ep.start_ts,
                "end_ts": ep.end_ts,
            })

        try:
            ev_store = get_evidence_store()
            for step in step_objs:
                for ev in ev_store.get_for_step(step.step_id):
                    evidence_rows.append({
                        "evidence_id": ev.evidence_id,
                        "step_id": ev.step_id,
                        "trace_id": ev.trace_id,
                        "type": ev.type.value if hasattr(ev.type, "value") else str(ev.type),
                        "tool": ev.tool_name,
                        "created_at": ev.created_at,
                        "expires_at": ev.expires_at,
                        "bytes": ev.byte_size,
                    })
        except Exception as e:
            log_exception("dashboard", "evidence load failed", e)

    if OUTCOMES_FILE.exists():
        for row in _read_jsonl(OUTCOMES_FILE, limit=400):
            if row.get("trace_id") != trace_id:
                continue
            outcomes.append({
                "outcome_id": row.get("outcome_id"),
                "event_type": row.get("event_type"),
                "tool": row.get("tool"),
                "polarity": row.get("polarity"),
                "text": (row.get("text") or "")[:160],
                "created_at": row.get("created_at"),
            })

    return {
        "trace_id": trace_id,
        "steps": steps,
        "episodes": episodes,
        "evidence": evidence_rows,
        "outcomes": outcomes,
        "available": True,
    }


def _queue_oldest_event_age_s() -> Optional[float]:
    if not QUEUE_FILE.exists():
        return None
    try:
        with QUEUE_FILE.open("r", encoding="utf-8") as f:
            for line in f:
                raw = line.strip()
                if not raw:
                    continue
                try:
                    data = json.loads(raw)
                    ts = data.get("timestamp")
                    if isinstance(ts, (int, float)):
                        return max(0.0, time.time() - ts)
                except Exception:
                    continue
    except Exception as e:
        log_exception("dashboard", "queue age check failed", e)
        return None
    return None


def _format_age(seconds: Optional[float]) -> str:
    if seconds is None:
        return "â€”"
    if seconds < 60:
        return f"{int(seconds)}s"
    minutes = int(seconds // 60)
    rem = int(seconds % 60)
    if minutes < 60:
        return f"{minutes}m {rem}s"
    hours = minutes // 60
    minutes = minutes % 60
    return f"{hours}h {minutes}m"


def generate_system_badges(data: Dict) -> str:
    """Generate HTML for system status badges in footer."""
    badges = []
    systems = data.get("systems", {})
    eidos = data.get("eidos", {})
    advisory = data.get("advisory", {})

    # Core systems
    for key, info in systems.items():
        status_class = "ok" if info.get("ok") else "error"
        label = info.get("label", key)
        badges.append(
            f'<span class="system-badge {status_class}">'
            f'<span class="system-dot"></span>{label}</span>'
        )

    # EIDOS details if available
    if eidos.get("available"):
        sr = eidos.get("success_rate", 0)
        sr_class = "ok" if sr >= 0.5 else "error"
        badges.append(
            f'<span class="system-badge {sr_class}">'
            f'<span class="system-dot"></span>EIDOS {sr:.0%}</span>'
        )
        if eidos.get("minimal_mode"):
            badges.append(
                '<span class="system-badge error">'
                '<span class="system-dot"></span>MINIMAL MODE</span>'
            )
        if eidos.get("alerts", 0) > 0:
            badges.append(
                f'<span class="system-badge error">'
                f'<span class="system-dot"></span>{eidos["alerts"]} Alerts</span>'
            )

    # Advisory delivery badge
    if isinstance(advisory, dict):
        delivery = advisory.get("delivery_badge") if isinstance(advisory.get("delivery_badge"), dict) else {}
        state = str(delivery.get("state") or "").strip().lower()
        if state:
            status_class = "ok" if state in {"live", "fallback"} else "error"
            badges.append(
                f'<span class="system-badge {status_class}">'
                f'<span class="system-dot"></span>Advisory {state}</span>'
            )

    return " ".join(badges)


def get_ops_data() -> Dict:
    # Auto-refresh skills index from H70 YAML files if SPARK_SKILLS_DIR is set.
    # load_skills_index() uses mtime caching so this is lightweight (no re-parse
    # unless files changed on disk).
    if os.environ.get("SPARK_SKILLS_DIR"):
        try:
            from lib.skills_registry import load_skills_index
            load_skills_index()  # refreshes ~/.spark/skills_index.json if stale
        except Exception:
            pass

    index_data = _load_json(SKILLS_INDEX_FILE)
    skills = index_data.get("skills") if isinstance(index_data.get("skills"), list) else []
    categories: Dict[str, int] = {}
    for s in skills:
        cat = str(s.get("category") or "uncategorized")
        categories[cat] = categories.get(cat, 0) + 1

    effectiveness = _load_json(SKILLS_EFFECTIVENESS_FILE)
    needs_attention = []
    top_performers = []
    usage_stats = []
    no_signal = []
    for s in skills:
        sid = s.get("skill_id") or s.get("name")
        if not sid:
            continue
        stats = effectiveness.get(sid, {})
        success = int(stats.get("success", 0))
        fail = int(stats.get("fail", 0))
        total = success + fail
        if total == 0:
            no_signal.append(sid)
            continue
        rate = success / max(total, 1)
        entry = {
            "skill": sid,
            "rate": rate,
            "total": total,
            "success": success,
            "fail": fail,
        }
        usage_stats.append(entry)
        if fail >= 1 and rate < 0.55:
            needs_attention.append(entry)
        if total >= 2 and rate >= 0.7:
            top_performers.append(entry)

    needs_attention.sort(key=lambda x: (x["rate"], -x["fail"]))
    top_performers.sort(key=lambda x: (-x["rate"], -x["total"]))
    usage_stats.sort(key=lambda x: (-x["total"], -x["rate"]))
    no_signal_sorted = sorted(no_signal)

    agents_raw = _load_json(ORCH_AGENTS_FILE)
    if isinstance(agents_raw, dict):
        agents = list(agents_raw.values())
    elif isinstance(agents_raw, list):
        agents = agents_raw
    else:
        agents = []

    handoffs = _read_jsonl(ORCH_HANDOFFS_FILE)

    def _handoff_ts(h: Dict[str, Any]) -> float:
        raw = h.get("timestamp", 0)
        try:
            return float(raw or 0)
        except Exception:
            return 0.0

    handoffs_sorted = sorted(handoffs, key=_handoff_ts, reverse=True)
    recent_handoffs = handoffs_sorted[:8]

    pair_stats: Dict[str, Dict] = {}
    for h in handoffs:
        from_agent = h.get("from_agent") or "unknown"
        to_agent = h.get("to_agent") or "unknown"
        key = f"{from_agent} -> {to_agent}"
        stats = pair_stats.setdefault(
            key,
            {"pair": key, "from_agent": from_agent, "to_agent": to_agent, "success": 0, "fail": 0, "known": 0, "total": 0},
        )
        stats["total"] += 1
        if h.get("success") is True:
            stats["success"] += 1
            stats["known"] += 1
        elif h.get("success") is False:
            stats["fail"] += 1
            stats["known"] += 1

    best_pairs = []
    risky_pairs = []
    for stats in pair_stats.values():
        if stats["known"] < 2:
            continue
        rate = stats["success"] / max(stats["known"], 1)
        stats["rate"] = rate
        if rate >= 0.7:
            best_pairs.append(stats)
        elif rate < 0.4:
            risky_pairs.append(stats)

    best_pairs.sort(key=lambda x: (-x["rate"], -x["known"]))
    risky_pairs.sort(key=lambda x: (x["rate"], -x["known"]))

    return {
        "skills_total": len(skills),
        "categories": categories,
        "needs_attention": needs_attention[:8],
        "top_performers": top_performers[:8],
        "most_used": usage_stats[:8],
        "no_signal_skills": no_signal_sorted[:10],
        "no_signal_count": len(no_signal_sorted),
        "index_generated_at": index_data.get("generated_at") or "",
        "agents": agents,
        "recent_handoffs": recent_handoffs,
        "best_pairs": best_pairs[:6],
        "risky_pairs": risky_pairs[:6],
        "advisory": _get_advisory_status_block(),
    }


def _get_eidos_store_safe():
    if not HAS_EIDOS:
        return None
    try:
        return get_store()
    except Exception:
        return None


def _get_active_episodes(store) -> List:
    mapping = _load_json(EIDOS_ACTIVE_EPISODES_FILE)
    ids = list(mapping.values()) if isinstance(mapping, dict) else []
    episodes = []
    for eid in ids:
        try:
            ep = store.get_episode(eid)
        except Exception:
            ep = None
        if not ep:
            continue
        if getattr(ep, "outcome", None) == Outcome.IN_PROGRESS:
            episodes.append(ep)
    episodes.sort(key=lambda e: getattr(e, "start_ts", 0), reverse=True)
    return episodes


def _count_steps_since(store, seconds: float) -> int:
    try:
        cutoff = time.time() - seconds
        with sqlite3.connect(store.db_path) as conn:
            row = conn.execute(
                "SELECT COUNT(*) FROM steps WHERE created_at >= ?",
                (cutoff,)
            ).fetchone()
            return int(row[0] or 0)
    except Exception:
        return 0


def _distillation_sums(store) -> Dict[str, int]:
    try:
        with sqlite3.connect(store.db_path) as conn:
            row = conn.execute(
                "SELECT COALESCE(SUM(times_retrieved),0), COALESCE(SUM(times_used),0), COALESCE(SUM(times_helped),0) FROM distillations"
            ).fetchone()
            return {
                "retrieved": int(row[0] or 0),
                "used": int(row[1] or 0),
                "helped": int(row[2] or 0),
            }
    except Exception:
        return {"retrieved": 0, "used": 0, "helped": 0}


def get_funnel_kpis() -> Dict[str, int]:
    if not HAS_EIDOS:
        return {"retrieved": 0, "cited": 0, "used": 0, "helped": 0, "promoted": 0}

    store = _get_eidos_store_safe()
    if not store:
        return {"retrieved": 0, "cited": 0, "used": 0, "helped": 0, "promoted": 0}

    sums = _distillation_sums(store)
    cited = 0
    try:
        with sqlite3.connect(store.db_path) as conn:
            row = conn.execute(
                "SELECT COUNT(*) FROM steps WHERE memory_cited = 1"
            ).fetchone()
            cited = int(row[0] or 0)
    except Exception:
        cited = 0

    promoter = Promoter()
    promo_stats = promoter.get_promotion_status()

    return {
        "retrieved": sums.get("retrieved", 0),
        "cited": cited,
        "used": sums.get("used", 0),
        "helped": sums.get("helped", 0),
        "promoted": int(promo_stats.get("promoted_count", 0)),
    }


def _derive_watcher_alerts(store, episodes: List) -> List[Dict[str, Any]]:
    if not episodes:
        return []
    engine = WatcherEngine()
    alerts: List[Dict[str, Any]] = []
    for ep in episodes:
        steps = store.get_episode_steps(ep.episode_id)
        if not steps:
            continue
        recent = steps[-10:]
        last_step = steps[-1]
        try:
            episode_alerts = engine.check_all(ep, last_step, recent, memories_exist=False)
            for alert in episode_alerts:
                payload = alert.to_dict()
                if getattr(last_step, "trace_id", None):
                    payload["trace_id"] = last_step.trace_id
                alerts.append(payload)
        except Exception as e:
            log_exception("dashboard", "watcher alert check failed", e)
            continue
    try:
        alerts.extend(_extract_trace_gaps(store))
    except Exception as e:
        log_exception("dashboard", "trace gap extract failed", e)
    alerts.sort(key=lambda a: a.get("timestamp", 0), reverse=True)
    return alerts


def _extract_trace_gaps(store, limit: int = 12) -> List[Dict[str, Any]]:
    alerts: List[Dict[str, Any]] = []
    now = time.time()

    def _alert(message: str, ts: Optional[float] = None, **extra) -> Dict[str, Any]:
        strict = os.environ.get("SPARK_TRACE_STRICT", "").strip().lower() in {"1", "true", "yes", "on"}
        payload = {
            "watcher": WatcherType.TRACE_GAP.value,
            "severity": (WatcherSeverity.BLOCK.value if strict else WatcherSeverity.WARNING.value),
            "message": message,
            "timestamp": ts or now,
        }
        payload.update(extra)
        return payload

    # Steps missing trace_id
    try:
        with sqlite3.connect(store.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                "SELECT step_id, episode_id, created_at FROM steps WHERE trace_id IS NULL OR trace_id = '' ORDER BY created_at DESC LIMIT ?",
                (limit,),
            ).fetchall()
        for row in rows:
            alerts.append(_alert(
                "Step missing trace_id",
                ts=row["created_at"] if row["created_at"] else now,
                step_id=row["step_id"],
                episode_id=row["episode_id"],
            ))
    except Exception as e:
        log_exception("dashboard", "trace gap step scan failed", e)

    # Evidence missing trace_id
    try:
        ev_store = get_evidence_store()
        with sqlite3.connect(ev_store.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cols = conn.execute("PRAGMA table_info(evidence)").fetchall()
            has_trace = any(c[1] == "trace_id" for c in cols)
            if has_trace:
                rows = conn.execute(
                    "SELECT evidence_id, step_id, created_at FROM evidence WHERE trace_id IS NULL OR trace_id = '' ORDER BY created_at DESC LIMIT ?",
                    (limit,),
                ).fetchall()
                for row in rows:
                    alerts.append(_alert(
                        "Evidence missing trace_id",
                        ts=row["created_at"] if row["created_at"] else now,
                        evidence_id=row["evidence_id"],
                        step_id=row["step_id"],
                    ))
    except Exception as e:
        log_exception("dashboard", "trace gap evidence scan failed", e)

    # Outcomes missing trace_id
    try:
        missing = 0
        for row in _read_jsonl(OUTCOMES_FILE, limit=200):
            if row.get("trace_id"):
                continue
            missing += 1
            alerts.append(_alert(
                "Outcome missing trace_id",
                ts=row.get("created_at") or now,
                outcome_id=row.get("outcome_id"),
                event_type=row.get("event_type"),
            ))
            if missing >= limit:
                break
    except Exception as e:
        log_exception("dashboard", "trace gap outcome scan failed", e)

    return alerts[:limit]


def _extract_repeat_failures(store, limit: int = 10) -> List[Dict[str, Any]]:
    counts: Dict[str, int] = {}
    trace_by_sig: Dict[str, Optional[str]] = {}
    steps = store.get_recent_steps(limit=300)
    for step in steps:
        try:
            if step.evaluation != Evaluation.FAIL:
                continue
        except Exception:
            if str(step.evaluation).lower() != "evaluation.fail":
                continue
        sig = (step.result or step.lesson or "failure").strip()
        if not sig:
            sig = "failure"
        sig = sig[:80]
        counts[sig] = counts.get(sig, 0) + 1
        if sig not in trace_by_sig and getattr(step, "trace_id", None):
            trace_by_sig[sig] = step.trace_id
    ranked = sorted(counts.items(), key=lambda x: -x[1])
    return [{"signature": k, "count": v, "trace_id": trace_by_sig.get(k)} for k, v in ranked[:limit]]


def _extract_diff_thrash(store, limit: int = 10) -> List[Dict[str, Any]]:
    counts: Dict[str, int] = {}
    trace_by_file: Dict[str, Optional[str]] = {}
    steps = store.get_recent_steps(limit=500)
    for step in steps:
        tool = str(step.action_details.get("tool") or "").lower()
        if tool not in ("edit", "write"):
            continue
        file_path = step.action_details.get("file_path") or step.action_details.get("path") or ""
        file_path = str(file_path)
        if not file_path:
            continue
        counts[file_path] = counts.get(file_path, 0) + 1
        if file_path not in trace_by_file and getattr(step, "trace_id", None):
            trace_by_file[file_path] = step.trace_id
    ranked = sorted(counts.items(), key=lambda x: -x[1])
    return [{"file": k, "count": v, "trace_id": trace_by_file.get(k)} for k, v in ranked[:limit]]


def _extract_validation_gaps(store, limit: int = 10) -> List[Dict[str, Any]]:
    gaps: List[Dict[str, Any]] = []
    episodes = store.get_recent_episodes(limit=50)
    for ep in episodes:
        steps = store.get_episode_steps(ep.episode_id)
        if len(steps) < 2:
            continue
        recent = steps[-3:]
        if all((not s.validated and not s.validation_method) for s in recent):
            trace_id = None
            for s in reversed(recent):
                if getattr(s, "trace_id", None):
                    trace_id = s.trace_id
                    break
            gaps.append({
                "episode_id": ep.episode_id,
                "goal": ep.goal[:60],
                "missing_count": len(recent),
                "phase": ep.phase.value,
                "trace_id": trace_id,
            })
    return gaps[:limit]


def _extract_no_evidence_streaks(store, limit: int = 10) -> List[Dict[str, Any]]:
    streaks: List[Dict[str, Any]] = []
    episodes = store.get_recent_episodes(limit=50)
    for ep in episodes:
        steps = store.get_episode_steps(ep.episode_id)
        if not steps:
            continue
        streak = 0
        trace_id = None
        for step in reversed(steps):
            if step.validated or step.validation_method:
                break
            streak += 1
            if trace_id is None and getattr(step, "trace_id", None):
                trace_id = step.trace_id
        if streak > 0:
            streaks.append({
                "episode_id": ep.episode_id,
                "goal": ep.goal[:60],
                "streak": streak,
                "phase": ep.phase.value,
                "trace_id": trace_id,
            })
    streaks.sort(key=lambda x: -x["streak"])
    return streaks[:limit]


def get_mission_control_data(include_pulse_probe: bool = True) -> Dict[str, Any]:
    funnel = get_funnel_kpis()
    services = service_status(include_pulse_probe=include_pulse_probe)
    mind_ok = _http_ok(MIND_HEALTH_URL)
    services["mind_server"] = {
        "running": mind_ok,
        "healthy": mind_ok,
        "pid": None,
    }
    mem_mb = _get_process_memory_mb()

    queue_stats = get_queue_stats()
    oldest_age = _queue_oldest_event_age_s()
    invalid_count = _count_jsonl(INVALID_EVENTS_FILE)
    queue_health = {
        **queue_stats,
        "oldest_age_s": oldest_age,
        "oldest_age": _format_age(oldest_age),
        "invalid_events": invalid_count,
        "lock_present": QUEUE_LOCK_FILE.exists(),
    }

    bridge = _load_json(BRIDGE_HEARTBEAT_FILE)
    bridge_stats = bridge.get("stats", {}) if isinstance(bridge, dict) else {}
    bridge_last = bridge.get("ts") if isinstance(bridge, dict) else None
    bridge_health = {
        "last_run_ts": bridge_last,
        "last_run": datetime.fromtimestamp(bridge_last).strftime("%H:%M:%S") if bridge_last else "â€”",
        "pattern_processed": bridge_stats.get("pattern_processed", 0),
        "content_learned": bridge_stats.get("content_learned", 0),
        "events_processed": bridge_stats.get("events_processed", 0),
        "errors": bridge_stats.get("errors") or [],
    }

    eidos_block = {
        "available": HAS_EIDOS,
        "active_episodes": 0,
        "steps_per_min": 0,
        "watchers_per_min": 0,
    }
    active_episode = None
    watcher_feed: List[Dict[str, Any]] = []
    minimal_mode = {"currently_active": False}
    acceptance_status = {}

    if HAS_EIDOS:
        store = _get_eidos_store_safe()
        if store:
            active_eps = _get_active_episodes(store)
            eidos_block["active_episodes"] = len(active_eps)
            eidos_block["steps_per_min"] = _count_steps_since(store, 60)
            watcher_feed = _derive_watcher_alerts(store, active_eps)
            eidos_block["watchers_per_min"] = len([w for w in watcher_feed if w.get("timestamp", 0) > time.time() - 60])

            if active_eps:
                ep = active_eps[0]
                steps = store.get_episode_steps(ep.episode_id)
                elapsed = time.time() - ep.start_ts
                time_remaining = max(0, ep.budget.max_time_seconds - elapsed)
                recent_steps_detail = []
                for s in steps[-5:]:
                    recent_steps_detail.append({
                        "step_id": s.step_id,
                        "intent": (s.intent or "")[:60],
                        "evaluation": s.evaluation.value if hasattr(s.evaluation, "value") else str(s.evaluation),
                        "trace_id": getattr(s, "trace_id", None),
                    })
                active_episode = {
                    "episode_id": ep.episode_id,
                    "goal": ep.goal,
                    "phase": ep.phase.value,
                    "step_count": ep.step_count,
                    "budget_remaining": max(0, ep.budget.max_steps - ep.step_count),
                    "time_remaining": _format_age(time_remaining),
                    "recent_steps": len(steps),
                    "recent_steps_detail": recent_steps_detail,
                }

                compiler = get_acceptance_compiler()
                plan = None
                for p in compiler.plans.values():
                    if p.episode_id == ep.episode_id:
                        plan = p
                        break
                if plan:
                    acceptance_status = {
                        "plan_id": plan.plan_id,
                        "is_approved": plan.is_approved,
                        "critical_tests": len(plan.critical_tests),
                        "progress": round(plan.progress * 100, 1),
                    }

            minimal = get_minimal_mode_controller()
            minimal_mode = minimal.get_stats()
            minimal_mode.update(minimal.state.to_dict())

    escalations = _read_jsonl(EIDOS_ESCALATIONS_FILE, limit=10)

    return {
        "timestamp": datetime.now().strftime("%H:%M:%S"),
        "funnel": funnel,
        "services": services,
        "process_memory_mb": mem_mb,
        "advisory": _get_advisory_status_block(),
        "queue": queue_health,
        "bridge": bridge_health,
        "opportunity_scanner": _get_opportunity_scanner_snapshot(),
        "eidos": eidos_block,
        "active_episode": active_episode,
        "acceptance_status": acceptance_status,
        "minimal_mode": minimal_mode,
        "watchers": watcher_feed[:20],
        "escalations": escalations[-10:],
        "runs": get_recent_runs(limit=6),
        "run_kpis": get_run_kpis(limit=50),
    }


def get_learning_factory_data() -> Dict[str, Any]:
    funnel = get_funnel_kpis()
    if not HAS_EIDOS:
        return {"funnel": funnel, "available": False}

    store = _get_eidos_store_safe()
    if not store:
        return {"funnel": funnel, "available": False}

    now = time.time()
    start_day = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0).timestamp()
    last_7d = now - 7 * 86400

    with sqlite3.connect(store.db_path) as conn:
        conn.row_factory = sqlite3.Row
        total_distillations = conn.execute("SELECT COUNT(*) FROM distillations").fetchone()[0]
        today_distillations = conn.execute(
            "SELECT COUNT(*) FROM distillations WHERE created_at >= ?",
            (start_day,)
        ).fetchone()[0]
        week_distillations = conn.execute(
            "SELECT COUNT(*) FROM distillations WHERE created_at >= ?",
            (last_7d,)
        ).fetchone()[0]
        by_type_rows = conn.execute(
            "SELECT type, COUNT(*) as cnt FROM distillations GROUP BY type"
        ).fetchall()
        by_type = {r["type"]: r["cnt"] for r in by_type_rows}

        dist_rows = conn.execute(
            "SELECT * FROM distillations ORDER BY created_at DESC LIMIT 200"
        ).fetchall()

    distillations = [store._row_to_distillation(r) for r in dist_rows]
    top_helped = sorted(distillations, key=lambda d: -d.times_helped)[:5]
    top_ignored = sorted(
        [d for d in distillations if d.times_retrieved > 0 and d.times_used == 0],
        key=lambda d: -d.times_retrieved
    )[:5]

    def _trace_for_distillation(dist) -> Optional[str]:
        for sid in dist.source_steps or []:
            try:
                step = store.get_step(sid)
            except Exception:
                step = None
            if step and getattr(step, "trace_id", None):
                return step.trace_id
        return None

    ledger = get_truth_ledger()
    ledger_stats = ledger.get_stats()
    evidence_levels = {"none": 0, "weak": 0, "strong": 0}
    contradicted = 0
    for entry in ledger.entries.values():
        evidence_levels[entry.evidence_level.value] = evidence_levels.get(entry.evidence_level.value, 0) + 1
        if entry.status.value == "contradicted":
            contradicted += 1

    promoter = Promoter()
    promo_stats = promoter.get_promotion_status()
    cognitive = CognitiveLearner()
    promoted_items = [
        {
            "insight": i.insight[:80],
            "target": i.promoted_to or "unknown",
            "reliability": i.reliability,
        }
        for i in cognitive.insights.values()
        if i.promoted
    ]
    promoted_items.sort(key=lambda x: -x["reliability"])

    revalidation = store.get_distillations_for_revalidation()
    source_attribution: Dict[str, Any] = {
        "total_sources": 0,
        "rows": [],
        "totals": {},
        "attribution_mode": {},
    }
    try:
        from lib.meta_ralph import get_meta_ralph

        source_attribution = get_meta_ralph().get_source_attribution(limit=8)
    except Exception:
        pass

    return {
        "funnel": funnel,
        "available": True,
        "distillations": {
            "total": total_distillations,
            "today": today_distillations,
            "last_7d": week_distillations,
            "by_type": by_type,
        },
        "truth_ledger": {
            **ledger_stats,
            "contradicted": contradicted,
            "evidence_levels": evidence_levels,
        },
        "utilization": {
            "top_helped": [
                {
                    "id": d.distillation_id,
                    "statement": d.statement[:80],
                    "helped": d.times_helped,
                    "trace_id": _trace_for_distillation(d),
                }
                for d in top_helped
            ],
            "top_ignored": [
                {
                    "id": d.distillation_id,
                    "statement": d.statement[:80],
                    "retrieved": d.times_retrieved,
                    "trace_id": _trace_for_distillation(d),
                }
                for d in top_ignored
            ],
        },
        "source_attribution": source_attribution,
        "promotion": {
            **promo_stats,
            "recent_promoted": promoted_items[:6],
        },
        "revalidation": {
            "due": len(revalidation),
            "items": [
                {
                    "id": d.distillation_id,
                    "statement": d.statement[:80],
                    "due": d.revalidate_by,
                    "trace_id": _trace_for_distillation(d),
                }
                for d in revalidation[:6]
            ],
        },
    }


def get_rabbit_recovery_data() -> Dict[str, Any]:
    funnel = get_funnel_kpis()
    if not HAS_EIDOS:
        return {"funnel": funnel, "available": False}

    store = _get_eidos_store_safe()
    if not store:
        return {"funnel": funnel, "available": False}

    repeat_failures = _extract_repeat_failures(store)
    diff_thrash = _extract_diff_thrash(store)
    no_evidence = _extract_no_evidence_streaks(store)

    escape_distillations = store.get_distillations_by_domain("escape_protocol", limit=50)
    escape_count = len(escape_distillations)

    episodes = store.get_recent_episodes(limit=50)
    escape_episodes = [e for e in episodes if e.escape_protocol_triggered]
    recovered = len([e for e in escape_episodes if e.outcome == Outcome.SUCCESS])
    avg_steps_to_escape = 0
    if escape_episodes:
        avg_steps_to_escape = sum(e.step_count for e in escape_episodes) / len(escape_episodes)

    minimal = get_minimal_mode_controller()
    minimal_stats = minimal.get_stats()
    history = _read_jsonl(MINIMAL_MODE_HISTORY_FILE, limit=20)

    escalations = _read_jsonl(EIDOS_ESCALATIONS_FILE, limit=10)

    return {
        "funnel": funnel,
        "available": True,
        "scoreboard": {
            "repeat_failures": repeat_failures,
            "no_evidence": no_evidence,
            "diff_thrash": diff_thrash,
        },
        "escapes": {
            "triggered": escape_count,
            "avg_steps_to_escape": round(avg_steps_to_escape, 1) if escape_episodes else 0,
            "recovered": recovered,
            "artifacts": escape_count,
            "recent": [
                {"id": d.distillation_id, "statement": d.statement[:80], "created_at": d.created_at}
                for d in escape_distillations[:6]
            ],
        },
        "minimal_mode": {
            **minimal_stats,
            "history": history,
        },
        "escalations": escalations,
    }


def get_acceptance_data() -> Dict[str, Any]:
    funnel = get_funnel_kpis()
    if not HAS_EIDOS:
        return {"funnel": funnel, "available": False}

    store = _get_eidos_store_safe()
    if not store:
        return {"funnel": funnel, "available": False}

    compiler = get_acceptance_compiler()
    plans = []
    for plan in compiler.plans.values():
        status_counts = {
            "pending": len([t for t in plan.tests if t.status.value == "pending"]),
            "passed": len([t for t in plan.tests if t.status.value == "passed"]),
            "failed": len([t for t in plan.tests if t.status.value == "failed"]),
            "skipped": len([t for t in plan.tests if t.status.value == "skipped"]),
            "blocked": len([t for t in plan.tests if t.status.value == "blocked"]),
        }
        plans.append({
            "plan_id": plan.plan_id,
            "episode_id": plan.episode_id,
            "goal": plan.goal[:80],
            "is_approved": plan.is_approved,
            "progress": round(plan.progress * 100, 1),
            "critical_tests": len(plan.critical_tests),
            "status_counts": status_counts,
            "tests": [
                {
                    "description": t.description[:80],
                    "status": t.status.value,
                    "priority": t.priority,
                    "evidence_ref": t.evidence_ref or "",
                }
                for t in plan.tests[:6]
            ],
        })

    tracker = get_deferred_tracker()
    pending = tracker.get_pending()
    overdue = tracker.get_overdue()

    validation_gaps = _extract_validation_gaps(store)

    evidence = get_evidence_store()
    evidence_stats = evidence.get_stats()

    def _trace_for_step(step_id: Optional[str]) -> Optional[str]:
        if not step_id:
            return None
        try:
            step = store.get_step(step_id)
        except Exception:
            step = None
        return step.trace_id if step and getattr(step, "trace_id", None) else None

    return {
        "funnel": funnel,
        "available": True,
        "plans": plans,
        "deferrals": {
            "pending": len(pending),
            "overdue": len(overdue),
            "items": [
                {
                    "step_id": d.step_id,
                    "reason": d.reason,
                    "age_s": time.time() - d.deferred_at,
                    "max_wait_s": d.max_wait_seconds,
                    "trace_id": _trace_for_step(d.step_id),
                }
                for d in pending[:6]
            ],
        },
        "validation_gaps": validation_gaps,
        "evidence": evidence_stats,
    }


def _handle_eidos_action(path: str, payload: Dict[str, Any]) -> tuple[str, str]:
    if not HAS_EIDOS:
        return "error", "EIDOS not available"

    store = _get_eidos_store_safe()
    if not store:
        return "error", "EIDOS store unavailable"

    episodes = _get_active_episodes(store)
    if not episodes:
        return "error", "No active episodes"

    episode = episodes[0]
    steps = store.get_episode_steps(episode.episode_id)
    reason = str(payload.get("reason") or "manual").strip()

    if path == "/api/eidos/escape":
        ecp = get_elevated_control_plane()
        result = ecp.initiate_escape(episode, steps, reason=reason)
        _append_jsonl(EIDOS_ESCALATIONS_FILE, {
            "type": "escape_protocol",
            "episode_id": episode.episode_id,
            "reason": result.reason or reason,
            "summary": result.summary,
            "timestamp": time.time(),
        })
        return "ok", result.reason or "escape triggered"

    if path == "/api/eidos/minimal/enter":
        minimal = get_minimal_mode_controller()
        mm_reason = MinimalModeReason.MANUAL_TRIGGER
        try:
            if reason:
                mm_reason = MinimalModeReason(reason)
        except Exception:
            mm_reason = MinimalModeReason.MANUAL_TRIGGER
        minimal.enter(episode, mm_reason)
        return "ok", f"entered minimal mode ({mm_reason.value})"

    if path == "/api/eidos/minimal/exit":
        minimal = get_minimal_mode_controller()
        minimal.exit(episode, reason=reason)
        return "ok", "exited minimal mode"

    if path == "/api/eidos/escalate":
        blocker = payload.get("reason") or "manual escalation"
        esc = build_escalation(episode, steps, EscalationType.BLOCKED, str(blocker))
        _append_jsonl(EIDOS_ESCALATIONS_FILE, {
            "type": esc.escalation_type.value,
            "episode_id": episode.episode_id,
            "reason": blocker,
            "summary": esc.summary[:200],
            "timestamp": time.time(),
        })
        return "ok", "escalation recorded"

    return "error", "unknown action"


def generate_html():
    """Generate true Vibeship-style dashboard HTML."""
    data = get_dashboard_data()
    
    # Category items - abbreviated for cleaner display
    cat_abbrev = {
        "self_awareness": "self",
        "reasoning": "reason",
        "wisdom": "wisdom",
        "user_understanding": "user",
        "communication": "comm",
        "meta_learning": "meta",
        "creativity": "create",
    }
    cats = data["cognitive"]["by_category"]
    cat_html = "".join([f'<span class="cat-pill">{cat_abbrev.get(c, c)} <span class="cat-count">{n}</span></span>' for c, n in cats.items()])
    
    # Surprises HTML
    surprises_html = ""
    for s in data["surprises"]["recent"]:
        icon = "△" if "Success" in s["type"] else "▽" if "Failure" in s["type"] else "◇"
        icon_class = "success" if "Success" in s["type"] else "failure" if "Failure" in s["type"] else ""
        lesson_html = f'<div class="surprise-lesson">→ {s["lesson"]}</div>' if s["lesson"] else ""
        surprises_html += f'''
        <div class="surprise-row">
            <div class="surprise-header">
                <span class="surprise-icon {icon_class}">{icon}</span>
                <span class="surprise-type">{s["type"]}</span>
                <span class="surprise-gap">{int(s["gap"]*100)}% gap</span>
            </div>
            <div class="surprise-detail">
                <span class="surprise-label">Expected</span>
                <span class="surprise-text">{s["predicted"]}…</span>
            </div>
            <div class="surprise-detail">
                <span class="surprise-label">Got</span>
                <span class="surprise-text">{s["actual"]}…</span>
            </div>
            {lesson_html}
        </div>'''

    # Project memory HTML (MVP)
    project_key = (data.get("project") or {}).get("active")
    project_memories = (data.get("project") or {}).get("memories") or []
    project_rows = ""
    for m in project_memories:
        try:
            t = datetime.fromtimestamp(float(m.get("created_at") or time.time())).strftime("%H:%M:%S")
        except Exception:
            t = "—"
        cat = str(m.get("category") or "—")
        txt = str(m.get("text") or "—")
        project_rows += f'''<div class="event-row">
            <span class="event-time">{t}</span>
            <span class="event-type">{cat}</span>
            <span class="event-tool">{txt[:60]}</span>
            <span class="event-status success">✓</span>
        </div>'''

    project_card = ""
    if project_key:
        project_card = f'''
        <div class="card">
            <div class="card-header">
                <span class="card-title">Project Memory</span>
                <span class="muted" style="font-size: 0.7rem;">{project_key}</span>
            </div>
            <div class="card-body">
                {project_rows if project_rows else '<div class="empty">No project memories yet.</div>'}
            </div>
        </div>'''

    # TasteBank (visual input)
    taste_stats = (data.get("taste") or {}).get("stats") or {}
    taste_recent = (data.get("taste") or {}).get("recent") or []

    taste_rows = ""
    for it in taste_recent:
        try:
            t = datetime.fromtimestamp(float(it.get("created_at") or time.time())).strftime("%H:%M:%S")
        except Exception:
            t = "—"
        dom = str(it.get("domain") or "—")
        label = str(it.get("label") or "")
        src = str(it.get("source") or "")
        notes = str(it.get("notes") or "")
        show = (label or src)[:120]
        badge = dom.replace("_", " ")
        taste_rows += f'''<div class="taste-item">
            <div class="taste-top">
                <span class="taste-domain">{badge}</span>
                <span class="muted" style="font-size:0.7rem;">{t}</span>
            </div>
            <div class="taste-main">{show}</div>
            {f'<div class="taste-notes">{notes[:140]}</div>' if notes else ''}
        </div>'''

    taste_card = f'''
        <div class="card">
            <div class="card-header">
                <span class="card-title">TasteBank</span>
                <span class="muted" style="font-size: 0.7rem;">posts {taste_stats.get("social_posts",0)} · ui {taste_stats.get("ui_design",0)} · art {taste_stats.get("art",0)}</span>
            </div>
            <div class="card-body">
                <div class="taste-drop" id="taste-drop">
                    <div class="taste-drop-title">Drop a link or paste content</div>
                    <div class="taste-drop-sub">Pick domain → paste URL/text → add notes (optional)</div>

                    <div class="taste-form">
                        <select id="taste-domain">
                            <option value="social_posts">Social posts</option>
                            <option value="ui_design">UI designs</option>
                            <option value="art">Art / graphics</option>
                        </select>
                        <input id="taste-label" placeholder="Label (optional)" />
                        <textarea id="taste-source" placeholder="Paste URL or content…"></textarea>
                        <textarea id="taste-notes" placeholder="Why you like it / what to copy (optional)…"></textarea>
                        <button id="taste-add">Add to TasteBank</button>
                        <div class="muted" id="taste-status" style="font-size:0.75rem; margin-top:0.5rem;"></div>
                    </div>
                </div>

                <div style="margin-top: 1rem;">
                    <div class="section-header-row">
                        <div class="section-kicker">Recent</div>
                        <div class="section-meta">latest {min(5, len(taste_recent))}</div>
                    </div>
                    <div class="taste-grid" id="taste-recent">
                        {taste_rows if taste_rows else '<div class="empty">No taste references yet.</div>'}
                    </div>
                </div>
            </div>
        </div>'''
    
    # Opinions HTML
    opinions_html = ""
    for o in data["voice"]["opinions"]:
        opinions_html += f'''
        <div class="opinion-item">
            <span class="opinion-topic">{o["topic"]}</span>
            <span class="opinion-pref">{o["preference"]}</span>
            <span class="opinion-strength">{int(o["strength"]*100)}%</span>
        </div>'''
    
    # Growth HTML
    growth_html = ""
    for g in data["voice"]["growth"]:
        growth_html += f'''
        <div class="growth-item">
            <span class="growth-before">Was: {g["before"]}</span>
            <span class="growth-arrow">→</span>
            <span class="growth-after">Now: {g["after"]}</span>
        </div>'''
    
    # Insights rows
    insights_html = ""
    for ins in data["cognitive"]["insights"]:
        rel_pct = int(ins["reliability"] * 100)
        if ins["promoted"]:
            status_class = "promoted"
            status_text = "PROMOTED"
        elif rel_pct >= 70 and ins["validations"] >= 3:
            status_class = "ready"
            status_text = "READY"
        else:
            status_class = "learning"
            status_text = "LEARNING"
        insights_html += f'''
        <div class="insight-row">
            <span class="insight-cat">{ins["category"].replace("_", " ")}</span>
            <span class="insight-text">{ins["insight"]}...</span>
            <span class="insight-rel">{rel_pct}%</span>
            <span class="insight-status {status_class}">{status_text}</span>
        </div>'''
    
    # Events rows
    events_html = ""
    for evt in data["queue"]["recent"]:
        icon = "✓" if evt["success"] else "✗"
        status_class = "success" if evt["success"] else "error"
        events_html += f'''
        <div class="event-row">
            <span class="event-time">{evt["time"]}</span>
            <span class="event-type">{evt["type"]}</span>
            <span class="event-tool">{evt["tool"]}</span>
            <span class="event-status {status_class}">{icon}</span>
        </div>'''
    
    # Output Adapters - build tooltip for hover
    adapters = data["outputs"]["adapters"]
    total_adapters = len(adapters)
    ok_adapters = data["outputs"]["adapters_ok"]
    error_adapters = data["outputs"]["adapters_error"]

    # Build tooltip content
    ok_names = [a["name"] for a in adapters if a["status"] == "success"]
    error_names = [a["name"] for a in adapters if a["status"] == "error"]
    never_names = [a["name"] for a in adapters if a["status"] == "never"]

    tooltip_parts = []
    if ok_names:
        tooltip_parts.append("Synced: " + ", ".join(ok_names))
    if error_names:
        tooltip_parts.append("Errors: " + ", ".join(error_names))
    if never_names:
        tooltip_parts.append("Never: " + ", ".join(never_names))
    adapters_tooltip = " | ".join(tooltip_parts) if tooltip_parts else "No adapters"

    # Display "All" if all adapters synced, otherwise show count
    synced_display = "All" if ok_adapters == total_adapters and ok_adapters > 0 else str(ok_adapters)
    
    mind_status = "live" if data["mind"]["available"] else "offline"
    mind_text = "Connected" if data["mind"]["available"] else "Offline"
    opp = data.get("opportunity_scanner") or {}
    opp_enabled = bool(opp.get("enabled"))
    opp_state_class = "live" if opp_enabled else "offline"
    opp_state_text = "Active" if opp_enabled else "Disabled"
    opp_rate = int(round(_to_float(opp.get("adoption_rate"), 0.0) * 100))
    opp_recent_total = int(opp.get("scanned_recent", 0) or 0)
    opp_latest = opp.get("latest") or []
    opp_rows = ""
    for row in opp_latest:
        cat = str(row.get("category") or "general").replace("_", " ")
        pr = str(row.get("priority") or "medium")
        q = str(row.get("question") or "")
        ns = str(row.get("next_step") or "")
        opp_rows += f'''
        <div class="event-row">
            <span class="event-time">{cat}</span>
            <span class="event-type">{pr}</span>
            <span class="event-tool">{q[:96]}</span>
            <span class="event-status success">{'+' if ns else '|'}</span>
        </div>'''
    
    html = f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <!-- live updates via JS (no full-page refresh) -->
    <title>Spark Lab — Vibeship</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Instrument+Serif:ital@0;1&family=JetBrains+Mono:wght@400;500;600&display=swap" rel="stylesheet">
    <style>
        :root {{
            --bg-primary: #0e1016;
            --bg-secondary: #151820;
            --bg-tertiary: #1c202a;
            --text-primary: #e2e4e9;
            --text-secondary: #9aa3b5;
            --text-tertiary: #6b7489;
            --border: #2a3042;
            --green-dim: #00C49A;
            --orange: #D97757;
            --red: #FF4D4D;
            --font-mono: "JetBrains Mono", monospace;
            --font-serif: "Instrument Serif", Georgia, serif;
        }}
        
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        
        body {{
            font-family: var(--font-mono);
            background: var(--bg-primary);
            color: var(--text-primary);
            line-height: 1.6;
            font-size: 14px;
        }}
        
        /* Nav */
        .navbar {{
            height: 52px;
            border-bottom: 1px solid var(--border);
            display: flex;
            align-items: center;
            padding: 0 1.5rem;
        }}
        
        .navbar-logo {{
            display: flex;
            align-items: center;
            gap: 0.4rem;
        }}

        .navbar-icon {{
            width: 22px;
            height: 22px;
            object-fit: contain;
            display: block;
        }}
        
        .navbar-text {{
            font-family: var(--font-serif);
            font-size: 1.25rem;
            color: var(--text-primary);
        }}
        
        .navbar-product {{
            font-family: var(--font-serif);
            font-size: 1.25rem;
            color: var(--green-dim);
        }}

        .navbar-links {{
            margin-left: auto;
            display: flex;
            gap: 1rem;
        }}

        .nav-link {{
            color: var(--text-secondary);
            text-decoration: none;
            font-size: 0.7rem;
            letter-spacing: 0.1em;
            text-transform: uppercase;
            border-bottom: 1px solid transparent;
            padding-bottom: 2px;
        }}

        .nav-link:hover {{
            color: var(--text-primary);
        }}

        .nav-link.active {{
            color: var(--text-primary);
            border-color: var(--green-dim);
        }}
        
        /* Main */
        main {{
            max-width: 1000px;
            margin: 0 auto;
            padding: 2rem 1.5rem;
        }}
        
        /* Hero */
        .hero {{
            text-align: center;
            margin-bottom: 3rem;
        }}
        
        .hero h1 {{
            font-family: var(--font-serif);
            font-size: 2.5rem;
            font-weight: 400;
            margin-bottom: 0.5rem;
        }}
        
        .hero h1 span {{
            color: var(--green-dim);
        }}
        
        .hero-sub {{
            color: var(--text-secondary);
            font-size: 0.9rem;
        }}
        
        /* Stats Grid */
        .stats-grid {{
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 1rem;
            margin-bottom: 2rem;
        }}
        
        .stat-card {{
            background: var(--bg-secondary);
            border: 1px solid var(--border);
            padding: 1.25rem;
            text-align: center;
        }}
        
        .stat-value {{
            font-family: var(--font-serif);
            font-size: 2.5rem;
            color: var(--green-dim);
            line-height: 1;
        }}
        
        .stat-label {{
            font-size: 0.7rem;
            text-transform: uppercase;
            letter-spacing: 0.1em;
            color: var(--text-tertiary);
            margin-top: 0.5rem;
        }}
        
        /* Cards */
        .card {{
            background: var(--bg-secondary);
            border: 1px solid var(--border);
            margin-bottom: 1.5rem;
        }}
        
        .card-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 1rem 1.25rem;
            border-bottom: 1px solid var(--border);
            background: var(--bg-tertiary);
        }}
        
        .card-title {{
            font-size: 0.8rem;
            text-transform: uppercase;
            letter-spacing: 0.1em;
            color: var(--text-secondary);
        }}
        
        .card-status {{
            font-size: 0.65rem;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            padding: 0.25rem 0.5rem;
            border: 1px solid;
            display: flex;
            align-items: center;
            gap: 0.4rem;
        }}
        
        .card-status.live {{
            border-color: var(--green-dim);
            color: var(--green-dim);
        }}
        
        .card-status.offline {{
            border-color: var(--orange);
            color: var(--orange);
        }}
        
        .status-dot {{
            width: 6px;
            height: 6px;
            border-radius: 50%;
            background: currentColor;
        }}
        
        .card-status.live .status-dot {{
            animation: pulse 2s infinite;
        }}
        
        @keyframes pulse {{
            0%, 100% {{ opacity: 1; }}
            50% {{ opacity: 0.5; }}
        }}
        
        .card-body {{
            padding: 1rem 1.25rem;
        }}

        /* TasteBank */
        .taste-drop {{
            border: 1px dashed rgba(255,255,255,0.18);
            background: rgba(255,255,255,0.015);
            padding: 1rem;
        }}
        .taste-drop-title {{
            font-size: 0.85rem;
            color: var(--text-primary);
        }}
        .taste-drop-sub {{
            font-size: 0.75rem;
            color: var(--text-tertiary);
            margin-top: 0.25rem;
        }}
        .taste-form {{
            display: grid;
            grid-template-columns: 1fr;
            gap: 0.5rem;
            margin-top: 0.75rem;
        }}
        .taste-form input, .taste-form textarea, .taste-form select {{
            width: 100%;
            background: rgba(255,255,255,0.02);
            border: 1px solid rgba(255,255,255,0.10);
            color: var(--text-primary);
            padding: 0.6rem 0.7rem;
            font-family: var(--font-mono);
            font-size: 0.85rem;
        }}
        .taste-form textarea {{
            min-height: 80px;
            resize: vertical;
        }}
        .taste-form button {{
            background: rgba(0,196,154,0.12);
            border: 1px solid rgba(0,196,154,0.28);
            color: var(--green-dim);
            padding: 0.6rem 0.8rem;
            font-family: var(--font-mono);
            font-size: 0.85rem;
            cursor: pointer;
        }}
        .taste-form button:disabled {{
            opacity: 0.6;
            cursor: not-allowed;
        }}
        .taste-grid {{
            display: grid;
            grid-template-columns: 1fr;
            gap: 0.75rem;
        }}
        .taste-item {{
            border: 1px solid rgba(255,255,255,0.08);
            background: rgba(255,255,255,0.015);
            padding: 0.75rem;
        }}
        .taste-top {{
            display: flex;
            justify-content: space-between;
            align-items: baseline;
            gap: 0.75rem;
            margin-bottom: 0.35rem;
        }}
        .taste-domain {{
            font-size: 0.65rem;
            text-transform: uppercase;
            letter-spacing: 0.1em;
            color: var(--text-tertiary);
        }}
        .taste-main {{
            font-size: 0.85rem;
            color: var(--text-secondary);
            line-height: 1.35;
            word-break: break-word;
        }}
        .taste-notes {{
            margin-top: 0.35rem;
            font-size: 0.75rem;
            color: var(--text-tertiary);
        }}

        
        /* Two columns */
        .grid-2 {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 1.5rem;
            align-items: stretch; /* match column card heights */
        }}

        .grid-2 .card {{
            display: flex;
            flex-direction: column;
        }}

        .grid-2 .card-body {{
            flex: 1;
        }}
        
        /* Mini stats */
        .mini-stats {{
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 0.75rem;
        }}
        
        .mini-stat {{
            background: var(--bg-tertiary);
            padding: 0.75rem;
            text-align: center;
        }}
        
        .mini-stat-value {{
            font-size: 1.5rem;
            font-weight: 600;
            color: var(--text-primary);
        }}
        
        .mini-stat-label {{
            font-size: 0.6rem;
            text-transform: uppercase;
            letter-spacing: 0.1em;
            color: var(--text-tertiary);
            margin-top: 0.25rem;
        }}
        
        /* Category pills */
        .cat-pills {{
            display: flex;
            flex-wrap: nowrap;
            gap: 0.35rem;
            overflow-x: auto;
            max-width: 70%;
            justify-content: flex-end;
        }}
        
        .cat-pill {{
            font-size: 0.6rem;
            padding: 0.15rem 0.4rem;
            background: transparent;
            border: 1px solid var(--border);
            color: var(--text-tertiary);
            white-space: nowrap;
        }}
        
        .cat-count {{
            color: var(--green-dim);
            margin-left: 0.2rem;
            font-weight: 600;
        }}
        
        /* Target pills */
        .target-pill {{
            font-size: 0.65rem;
            padding: 0.2rem 0.5rem;
            border: 1px solid var(--green-dim);
            color: var(--green-dim);
        }}

        /* Tooltip */
        .has-tooltip {{
            position: relative;
            cursor: help;
        }}
        .has-tooltip .tooltip {{
            visibility: hidden;
            opacity: 0;
            position: absolute;
            bottom: 100%;
            left: 50%;
            transform: translateX(-50%);
            background: var(--bg-tertiary);
            border: 1px solid var(--border);
            padding: 0.5rem 0.75rem;
            font-size: 0.7rem;
            white-space: nowrap;
            z-index: 100;
            transition: opacity 0.15s;
            margin-bottom: 0.25rem;
        }}
        .has-tooltip:hover .tooltip {{
            visibility: visible;
            opacity: 1;
        }}

        /* Insight rows */
        .insight-row {{
            display: grid;
            grid-template-columns: 100px 1fr 50px 80px;
            gap: 1rem;
            padding: 0.75rem 0;
            border-bottom: 1px solid var(--border);
            font-size: 0.8rem;
            align-items: center;
        }}
        
        .insight-row:last-child {{ border-bottom: none; }}
        
        .insight-cat {{
            font-size: 0.6rem;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            color: var(--green-dim);
        }}
        
        .insight-text {{
            color: var(--text-secondary);
        }}
        
        .insight-rel {{
            text-align: right;
            color: var(--text-tertiary);
        }}
        
        .insight-status {{
            font-size: 0.55rem;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            padding: 0.2rem 0.4rem;
            text-align: center;
        }}
        
        .insight-status.promoted {{
            background: rgba(0, 196, 154, 0.15);
            color: var(--green-dim);
        }}
        
        .insight-status.ready {{
            background: rgba(217, 119, 87, 0.15);
            color: var(--orange);
        }}
        
        .insight-status.learning {{
            background: var(--bg-tertiary);
            color: var(--text-tertiary);
        }}
        
        /* Event rows */
        .event-row {{
            display: grid;
            grid-template-columns: 60px 100px 1fr 30px;
            gap: 1rem;
            padding: 0.5rem 0;
            border-bottom: 1px solid var(--border);
            font-size: 0.75rem;
        }}
        
        .event-row:last-child {{ border-bottom: none; }}
        
        .event-time {{
            color: var(--text-tertiary);
            font-variant-numeric: tabular-nums;
        }}
        
        .event-type {{
            color: var(--text-secondary);
        }}
        
        .event-tool {{
            color: var(--text-primary);
        }}
        
        .event-status {{
            text-align: right;
        }}
        
        .event-status.success {{ color: var(--green-dim); }}
        .event-status.error {{ color: var(--red); }}
        
        /* Footer */
        .footer {{
            text-align: center;
            padding: 1.5rem;
            border-top: 1px solid var(--border);
            margin-top: 2rem;
        }}

        .footer-systems {{
            display: flex;
            justify-content: center;
            gap: 1rem;
            flex-wrap: wrap;
            margin-bottom: 0.75rem;
        }}

        .system-badge {{
            display: inline-flex;
            align-items: center;
            gap: 0.3rem;
            font-size: 0.65rem;
            padding: 0.2rem 0.5rem;
            border-radius: 3px;
            background: var(--bg-tertiary);
        }}

        .system-badge.ok {{
            color: var(--green-dim);
            border: 1px solid rgba(0, 196, 154, 0.3);
        }}

        .system-badge.error {{
            color: var(--red);
            border: 1px solid rgba(255, 82, 82, 0.3);
        }}

        .system-dot {{
            width: 6px;
            height: 6px;
            border-radius: 50%;
            background: currentColor;
        }}

        .system-badge.ok .system-dot {{
            animation: pulse 2s infinite;
        }}

        .footer-text {{
            font-size: 0.7rem;
            color: var(--text-tertiary);
        }}

        .footer-text span {{
            color: var(--green-dim);
        }}
        
        .muted {{ color: var(--text-tertiary); }}
        
        .empty {{
            text-align: center;
            padding: 1.5rem;
            color: var(--text-tertiary);
            font-style: italic;
        }}
        
        /* Resonance Fill (shared) */
        .resonance-fill {{
            height: 100%;
            transition: width 0.5s ease;
            border-radius: 2px;
        }}
        
        /* Surprise rows */
        #surprises-body {{
            display: flex;
            flex-direction: column;
        }}

        .surprise-list {{
            padding-right: 6px;
        }}

        /* Pagination controls */
        .pagination {{
            display: flex;
            align-items: center;
            gap: 0.5rem;
            font-size: 0.7rem;
        }}
        .pagination button {{
            background: var(--bg-tertiary);
            border: 1px solid var(--border);
            color: var(--text-secondary);
            padding: 0.2rem 0.5rem;
            cursor: pointer;
            font-family: var(--font-mono);
            font-size: 0.65rem;
        }}
        .pagination button:hover:not(:disabled) {{
            background: var(--bg-secondary);
            color: var(--text-primary);
        }}
        .pagination button:disabled {{
            opacity: 0.4;
            cursor: not-allowed;
        }}
        .pagination .page-info {{
            color: var(--text-tertiary);
            min-width: 3rem;
            text-align: center;
        }}

        .surprise-row {{
            padding: 1rem;
            border-bottom: 1px solid var(--border);
            background: rgba(255,255,255,0.018);
        }}

        .surprise-row:nth-child(even) {{
            background: rgba(255,255,255,0.03);
        }}
        
        .surprise-row:last-child {{ border-bottom: none; }}
        
        .surprise-header {{
            display: flex;
            align-items: center;
            gap: 0.75rem;
            margin-bottom: 0.5rem;
        }}
        
        .surprise-icon {{
            font-size: 1rem;
            font-weight: 600;
            width: 20px;
            height: 20px;
            display: flex;
            align-items: center;
            justify-content: center;
            color: var(--text-tertiary);
        }}
        
        .surprise-icon.success {{
            color: var(--green-dim);
        }}
        
        .surprise-icon.failure {{
            color: var(--orange);
        }}
        
        .surprise-type {{
            font-size: 0.8rem;
            font-weight: 600;
            color: var(--text-primary);
        }}
        
        .surprise-gap {{
            font-size: 0.65rem;
            padding: 0.2rem 0.55rem;
            background: rgba(255,255,255,0.05);
            border: 1px solid rgba(255,255,255,0.08);
            color: var(--orange);
        }}
        
        .surprise-detail {{
            font-size: 0.78rem;
            color: var(--text-secondary);
            margin-left: 2rem;
            margin-top: 0.35rem;
            line-height: 1.35;
        }}
        
        .surprise-label {{
            color: var(--text-tertiary);
            font-size: 0.62rem;
            text-transform: uppercase;
            letter-spacing: 0.08em;
            margin-right: 0.5rem;
        }}

        .surprise-text {{
            color: var(--text-secondary);
            font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace;
            font-size: 0.73rem;
            opacity: 0.95;
        }}
        
        .surprise-lesson {{
            margin-left: 2rem;
            margin-top: 0.5rem;
            font-size: 0.75rem;
            color: var(--green-dim);
            font-style: italic;
        }}
        
        /* Scroll areas (Personality) */
        .scroll-area {{
            max-height: 300px;
            overflow-y: auto;
            padding-right: 6px; /* room for scrollbar */
        }}

        /* Growth is usually shorter; keep a smaller cap */
        .scroll-area.growth {{
            max-height: 210px;
        }}
        
        .scroll-area::-webkit-scrollbar {{
            width: 6px;
        }}
        .scroll-area::-webkit-scrollbar-track {{
            background: transparent;
        }}
        .scroll-area::-webkit-scrollbar-thumb {{
            background: rgba(255,255,255,0.14);
            border-radius: 0px;
        }}
        .scroll-area::-webkit-scrollbar-thumb:hover {{
            background: rgba(255,255,255,0.22);
        }}
        
        /* Opinion items */
        .opinion-item {{
            display: flex;
            align-items: center;
            gap: 1rem;
            padding: 0.75rem 0;
            border-bottom: 1px solid var(--border);
        }}
        
        .opinion-item:last-child {{ border-bottom: none; }}
        
        .opinion-topic {{
            font-size: 0.7rem;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            color: var(--green-dim);
            min-width: 100px;
        }}
        
        .opinion-pref {{
            flex: 1;
            font-size: 0.8rem;
            color: var(--text-secondary);
        }}
        
        .opinion-strength {{
            font-size: 0.7rem;
            color: var(--text-tertiary);
        }}
        
        /* Growth items */
        .growth-item {{
            display: flex;
            align-items: center;
            gap: 0.75rem;
            padding: 0.75rem 0;
            border-bottom: 1px solid var(--border);
            font-size: 0.8rem;
        }}
        
        .growth-item:last-child {{ border-bottom: none; }}
        
        .growth-before {{
            color: var(--text-tertiary);
            text-decoration: line-through;
        }}
        
        .growth-arrow {{
            color: var(--green-dim);
            font-weight: bold;
        }}
        
        .growth-after {{
            color: var(--text-primary);
        }}
        
        /* Personality Resonance - Integrated */
        .personality-resonance {{
            padding: 0.9rem;
            border: 1px solid rgba(255,255,255,0.10);
            background: rgba(255,255,255,0.02);
        }}

        .subpanel {{
            padding: 0.9rem;
            border: 1px solid rgba(255,255,255,0.08);
            background: rgba(255,255,255,0.015);
        }}

        .section-divider {{
            height: 1px;
            background: linear-gradient(90deg, transparent, rgba(255,255,255,0.16), transparent);
            margin: 1rem 0;
        }}

        .section-header-row {{
            display: flex;
            align-items: baseline;
            justify-content: space-between;
            gap: 0.75rem;
            margin-bottom: 0.5rem;
        }}

        .section-kicker {{
            font-size: 0.7rem;
            text-transform: uppercase;
            letter-spacing: 0.1em;
            color: var(--text-tertiary);
        }}

        .section-meta {{
            font-size: 0.65rem;
            color: var(--text-tertiary);
        }}
        
        .resonance-compact {{
            display: flex;
            align-items: center;
            gap: 0.75rem;
        }}
        
        .resonance-icon-sm {{
            font-size: 1.75rem;
            line-height: 1;
        }}
        
        .resonance-details {{
            flex: 1;
        }}
        
        .resonance-score-sm {{
            font-family: var(--font-mono);
            font-size: 0.85rem;
            font-weight: 600;
            letter-spacing: 0.02em;
        }}
        
        .resonance-desc-sm {{
            font-size: 0.7rem;
            color: var(--text-tertiary);
            margin-top: 0.15rem;
        }}
        
        .resonance-bar-sm {{
            height: 3px;
            background: var(--bg-tertiary);
            margin-top: 0.75rem;
            border-radius: 2px;
        }}
        
        @media (max-width: 768px) {{
            .stats-grid {{ grid-template-columns: repeat(2, 1fr); }}
            .grid-2 {{ grid-template-columns: 1fr; }}
            .insight-row {{ grid-template-columns: 1fr; gap: 0.5rem; }}
        }}
    </style>
</head>
<body>
    <nav class="navbar">
        <div class="navbar-logo">
            <img src="/logo.png" alt="vibeship" class="navbar-icon" />
            <span class="navbar-text">vibeship</span>
            <span class="navbar-product">spark lab</span>
        </div>
        <div class="navbar-links">
            <a class="nav-link active" href="/">Overview</a>
            <a class="nav-link" href="/ops">Orchestration</a>
            <a class="nav-link" href="/dashboards">Dashboards</a>
            <a class="nav-link" href="http://localhost:{PULSE_PORT}">Pulse</a>
            <a class="nav-link" href="http://localhost:{META_RALPH_PORT}">Meta-Ralph</a>
        </div>
    </nav>
    
    <main>
        <div class="hero">
            <h1>Spark <span>Lab</span></h1>
            <p class="hero-sub">Data. Diagnostics. Deep Dive.</p>
        </div>
        
        <div class="stats-grid">
            <div class="stat-card">
                <div class="stat-value">{data["cognitive"]["total"]}</div>
                <div class="stat-label">Insights</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">{int(data["cognitive"]["avg_reliability"]*100)}%</div>
                <div class="stat-label">Reliability</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">{data["surprises"]["total"]}</div>
                <div class="stat-label">Surprises</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">{data["mind"]["synced"]}</div>
                <div class="stat-label">Synced</div>
            </div>
        </div>
        
        <div class="grid-2">
            <div class="card">
                <div class="card-header">
                    <span class="card-title">Mind Bridge</span>
                    <span class="card-status {mind_status}"><span class="status-dot"></span> {mind_text}</span>
                </div>
                <div class="card-body">
                    <div class="mini-stats">
                        <div class="mini-stat">
                            <div class="mini-stat-value">{data["mind"]["synced"]}</div>
                            <div class="mini-stat-label">Synced</div>
                        </div>
                        <div class="mini-stat">
                            <div class="mini-stat-value">{data["mind"]["queue"]}</div>
                            <div class="mini-stat-label">Queued</div>
                        </div>
                        <div class="mini-stat">
                            <div class="mini-stat-value">{data["queue"]["events"]}</div>
                            <div class="mini-stat-label">Events</div>
                        </div>
                    </div>
                </div>
            </div>
            
            <div class="card">
                <div class="card-header">
                    <span class="card-title">Output</span>
                    <span class="muted" style="font-size: 0.7rem;">{data["outputs"]["total_syncs"]} syncs</span>
                </div>
                <div class="card-body">
                    <div class="mini-stats">
                        <div class="mini-stat has-tooltip">
                            <span class="tooltip">{adapters_tooltip}</span>
                            <div class="mini-stat-value" style="color: var(--green);">{synced_display}</div>
                            <div class="mini-stat-label">Synced</div>
                        </div>
                        <div class="mini-stat">
                            <div class="mini-stat-value" style="color: {'var(--red)' if error_adapters > 0 else 'var(--text-muted)'};">{error_adapters}</div>
                            <div class="mini-stat-label">Errors</div>
                        </div>
                        <div class="mini-stat">
                            <div class="mini-stat-value">{data["promotions"]["ready"]}</div>
                            <div class="mini-stat-label">Ready</div>
                        </div>
                    </div>
                </div>
            </div>
        </div>

        <div class="card" id="opportunity-card">
            <div class="card-header">
                <span class="card-title">Opportunity Scanner</span>
                <span class="card-status {opp_state_class}" id="opp-enabled"><span class="status-dot"></span> {opp_state_text}</span>
            </div>
            <div class="card-body">
                <div class="mini-stats">
                    <div class="mini-stat">
                        <div class="mini-stat-value" id="opp-adoption">{opp_rate}%</div>
                        <div class="mini-stat-label">Adoption</div>
                    </div>
                    <div class="mini-stat">
                        <div class="mini-stat-value" id="opp-scanned">{opp_recent_total}</div>
                        <div class="mini-stat-label">Last 48h</div>
                    </div>
                    <div class="mini-stat">
                        <div class="mini-stat-value" id="opp-acted">{int(opp.get("acted_total", 0) or 0)}</div>
                        <div class="mini-stat-label">Acted</div>
                    </div>
                </div>
                <div id="opp-list">
                    {opp_rows if opp_rows else '<div class="empty">No recent self-opportunities captured yet.</div>'}
                </div>
            </div>
        </div>
        
        <div class="card">
            <div class="card-header">
                <span class="card-title">Cognitive Insights</span>
                <div class="cat-pills">{cat_html}</div>
            </div>
            <div class="card-body">
                {insights_html if insights_html else '<div class="empty">No insights yet. Start using tools to learn.</div>'}
            </div>
        </div>
        
        <div class="card">
            <div class="card-header">
                <span class="card-title">Recent Events</span>
                <span class="muted" style="font-size: 0.7rem;">{data["queue"]["events"]} total</span>
            </div>
            <div class="card-body">
                {events_html if events_html else '<div class="empty">No events captured yet.</div>'}
            </div>
        </div>
        
        <div class="grid-2">
            <div class="card">
                <div class="card-header">
                    <span class="card-title">Surprises</span>
                    <div class="pagination" id="surprises-pagination">
                        <button id="surprises-prev" onclick="surprisePage(-1)">&lt;</button>
                        <span class="page-info" id="surprises-page-info">1/1</span>
                        <button id="surprises-next" onclick="surprisePage(1)">&gt;</button>
                    </div>
                </div>
                <div class="card-body" id="surprises-body">
                    <div class="empty" id="surprises-empty" style="display:none;">No surprises yet. They happen when predictions do not match outcomes.</div>
                    <div class="surprise-list" id="surprises-list"></div>
                </div>
            </div>
            
            <div class="card">
                <div class="card-header">
                    <span class="card-title">🎭 Personality</span>
                    <span class="card-status live"><span class="status-dot" style="background: {data["resonance"]["color"]}"></span> <span style="color: {data["resonance"]["color"]}">{data["resonance"]["name"]}</span></span>
                </div>
                <div class="card-body">
                    <div class="subpanel personality-resonance">
                        <div class="resonance-compact">
                            <span class="resonance-icon-sm" style="color: {data["resonance"]["color"]}">{data["resonance"]["icon"]}</span>
                            <div class="resonance-details">
                                <div class="resonance-score-sm" style="color: {data["resonance"]["color"]}">{data["resonance"]["score"]:.0f}% Resonance</div>
                                <div class="resonance-desc-sm">{data["resonance"]["description"]}</div>
                            </div>
                        </div>
                        <div class="resonance-bar-sm">
                            <div class="resonance-fill" style="width: {data["resonance"]["score"]}%; background: {data["resonance"]["color"]}"></div>
                        </div>
                    </div>

                    <div class="section-divider"></div>

                    <div class="subpanel">
                        <div class="section-header-row">
                            <div class="section-kicker">Opinions</div>
                            <div class="section-meta">scroll for more</div>
                        </div>
                        <div class="scroll-area">
                            {opinions_html if opinions_html else '<div class="muted" style="font-size: 0.8rem;">No opinions yet.</div>'}
                        </div>
                    </div>

                    <div class="section-divider"></div>

                    <div class="subpanel">
                        <div class="section-header-row">
                            <div class="section-kicker">Growth</div>
                            <div class="section-meta">scroll for more</div>
                        </div>
                        <div class="scroll-area growth">
                            {growth_html if growth_html else '<div class="muted" style="font-size: 0.8rem;">No growth moments yet.</div>'}
                        </div>
                    </div>
                </div>
            </div>
        </div>

        {project_card}
        {taste_card}

    </main>
    
    <div class="footer">
        <div class="footer-systems" id="footer-systems">
            {generate_system_badges(data)}
        </div>
        <p class="footer-text">Updated <span id="updated-at">{data["timestamp"]}</span> · Project: <span id="active-project">{data.get("project", {}).get("active") or "—"}</span> · <span>vibeship</span> ecosystem</p>
    </div>

    <script>
      // Live updates (no full page refresh)
      const $ = (id) => document.getElementById(id);

      function esc(s) {{
        // NOTE: braces are doubled because this HTML is generated from a Python f-string.
        return String(s ?? '').replace(/[&<>"']/g, (c) => ({{'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":"&#39;"}}[c]));
      }}

      // Surprises pagination state
      const SURPRISES_PER_PAGE = 6;
      let surprisesData = [];
      let surprisesPage = 0;

      function renderSurprisesPage() {{
        const total = surprisesData.length;
        const totalPages = Math.max(1, Math.ceil(total / SURPRISES_PER_PAGE));
        surprisesPage = Math.max(0, Math.min(surprisesPage, totalPages - 1));

        const start = surprisesPage * SURPRISES_PER_PAGE;
        const pageItems = surprisesData.slice(start, start + SURPRISES_PER_PAGE);
        console.log('Rendering page', surprisesPage + 1, 'of', totalPages, 'items:', pageItems.length);

        // Update pagination UI
        const pageInfo = $('surprises-page-info');
        const prevBtn = $('surprises-prev');
        const nextBtn = $('surprises-next');
        if (pageInfo) pageInfo.textContent = `${{surprisesPage + 1}}/${{totalPages}}`;
        if (prevBtn) prevBtn.disabled = surprisesPage === 0;
        if (nextBtn) nextBtn.disabled = surprisesPage >= totalPages - 1;

        // Render items
        const list = $('surprises-list');
        const empty = $('surprises-empty');
        console.log('List element:', list, 'Empty element:', empty);
        if (total === 0) {{
          if (list) list.innerHTML = '';
          if (empty) empty.style.display = '';
        }} else {{
          if (empty) empty.style.display = 'none';
          const html = renderSurpriseItems(pageItems);
          console.log('Generated HTML length:', html.length);
          if (list) {{
            list.innerHTML = html;
          }} else {{
            console.error('surprises-list element not found!');
          }}
        }}
      }}

      function surprisePage(delta) {{
        surprisesPage += delta;
        renderSurprisesPage();
      }}

      function renderSurpriseItems(items) {{
        if (!Array.isArray(items) || items.length === 0) return '';
        return items.map((s) => {{
          const type = esc(s.type);
          const gap = Math.round((s.gap || 0) * 100);
          const predicted = esc(s.predicted || '');
          const actual = esc(s.actual || '');
          const lesson = s.lesson ? `<div class="surprise-lesson">-> ${{esc(s.lesson)}}</div>` : '';
          const icon = type.includes('Success') ? '+' : type.includes('Failure') ? '-' : '*';
          const iconClass = type.includes('Success') ? 'success' : type.includes('Failure') ? 'failure' : '';
          return `
            <div class="surprise-row">
              <div class="surprise-header">
                <span class="surprise-icon ${{iconClass}}">${{icon}}</span>
                <span class="surprise-type">${{type}}</span>
                <span class="surprise-gap">${{gap}}% gap</span>
              </div>
              <div class="surprise-detail"><span class="surprise-label">Expected</span><span class="surprise-text">${{predicted}}...</span></div>
              <div class="surprise-detail"><span class="surprise-label">Got</span><span class="surprise-text">${{actual}}...</span></div>
              ${{lesson}}
            </div>`;
        }}).join('');
      }}

      function renderOpportunityItems(items) {{
        if (!Array.isArray(items) || items.length === 0) {{
          return '<div class="empty">No recent self-opportunities captured yet.</div>';
        }}
        return items.map((o) => {{
          const category = esc(String(o.category || 'general').replaceAll('_', ' '));
          const priority = esc(o.priority || 'medium');
          const question = esc(o.question || '');
          return `
            <div class="event-row">
              <span class="event-time">${{category}}</span>
              <span class="event-type">${{priority}}</span>
              <span class="event-tool">${{question}}</span>
              <span class="event-status success">+</span>
            </div>`;
        }}).join('');
      }}

      async function postJSON(url, body) {{
        const res = await fetch(url, {{
          method: 'POST',
          headers: {{ 'Content-Type': 'application/json' }},
          body: JSON.stringify(body)
        }});
        return res.json();
      }}

      function applyStatus(data) {{
        if ($('updated-at')) $('updated-at').textContent = data.timestamp || '';

        // Update surprises with pagination
        surprisesData = data.surprises?.recent || [];
        renderSurprisesPage();

        // Opportunity Scanner panel
        const opp = data.opportunity_scanner || {{}};
        const oppEnabled = !!opp.enabled;
        const oppEl = $('opp-enabled');
        if (oppEl) {{
          oppEl.className = `card-status ${{oppEnabled ? 'live' : 'offline'}}`;
          oppEl.innerHTML = `<span class="status-dot"></span> ${{oppEnabled ? 'Active' : 'Disabled'}}`;
        }}
        if ($('opp-adoption')) $('opp-adoption').textContent = `${{Math.round((Number(opp.adoption_rate) || 0) * 100)}}%`;
        if ($('opp-scanned')) $('opp-scanned').textContent = `${{Number(opp.scanned_recent || 0)}}`;
        if ($('opp-acted')) $('opp-acted').textContent = `${{Number(opp.acted_total || 0)}}`;
        if ($('opp-list')) $('opp-list').innerHTML = renderOpportunityItems(opp.latest || []);

        // Update footer systems status
        const footerSys = $('footer-systems');
        if (footerSys && data.systems) {{
          let badges = '';
          for (const [key, info] of Object.entries(data.systems)) {{
            const cls = info.ok ? 'ok' : 'error';
            badges += `<span class="system-badge ${{cls}}"><span class="system-dot"></span>${{esc(info.label || key)}}</span> `;
          }}
          // EIDOS details
          if (data.eidos?.available) {{
            const sr = data.eidos.success_rate || 0;
            const srCls = sr >= 0.5 ? 'ok' : 'error';
            badges += `<span class="system-badge ${{srCls}}"><span class="system-dot"></span>EIDOS ${{Math.round(sr * 100)}}%</span> `;
            if (data.eidos.minimal_mode) {{
              badges += `<span class="system-badge error"><span class="system-dot"></span>MINIMAL MODE</span> `;
            }}
            if (data.eidos.alerts > 0) {{
              badges += `<span class="system-badge error"><span class="system-dot"></span>${{data.eidos.alerts}} Alerts</span> `;
            }}
          }}
          const advState = String(data.advisory?.delivery_badge?.state || '').toLowerCase();
          if (advState) {{
            const advCls = advState === 'live' || advState === 'fallback' ? 'ok' : 'error';
            badges += `<span class="system-badge ${{advCls}}"><span class="system-dot"></span>Advisory ${{advState}}</span> `;
          }}
          footerSys.innerHTML = badges;
        }}
      }}

      async function tick() {{
        try {{
          const res = await fetch('/api/status', {{ cache: 'no-store' }});
          if (!res.ok) return;
          const data = await res.json();
          applyStatus(data);
        }} catch (e) {{
          // best-effort; keep UI stable
        }}
      }}

      // TasteBank add
      async function wireTaste() {{
        const btn = $('taste-add');
        if (!btn) return;
        btn.addEventListener('click', async () => {{
          const domain = $('taste-domain')?.value;
          const label = $('taste-label')?.value || '';
          const source = $('taste-source')?.value || '';
          const notes = $('taste-notes')?.value || '';
          const status = $('taste-status');

          if (!domain || !source.trim()) {{
            if (status) status.textContent = 'Paste a URL or some content first.';
            return;
          }}

          btn.disabled = true;
          if (status) status.textContent = 'Saving…';
          try {{
            const resp = await postJSON('/api/taste/add', {{ domain, label, source, notes }});
            if (resp.ok) {{
              if (status) status.textContent = 'Saved.';
              $('taste-label').value = '';
              $('taste-source').value = '';
              $('taste-notes').value = '';
              // refresh view
              tick();
            }} else {{
              if (status) status.textContent = `Could not save (${{resp.error || 'error'}})`;
            }}
          }} catch (e) {{
            if (status) status.textContent = 'Error saving.';
          }} finally {{
            btn.disabled = false;
          }}
        }});
      }}

      function startStream() {{
        if (!window.EventSource) {{
          tick();
          setInterval(tick, 2000);
          return;
        }}
        const es = new EventSource('/api/status/stream');
        es.onmessage = (event) => {{
          try {{
            const data = JSON.parse(event.data || '{{}}');
            applyStatus(data);
          }} catch (e) {{
            // ignore bad payloads
          }}
        }};
        es.onerror = () => {{
          es.close();
          setTimeout(startStream, 3000);
        }};
      }}

      // Initialize pagination on page load
      async function initPage() {{
        try {{
          const res = await fetch('/api/status', {{ cache: 'no-store' }});
          if (res.ok) {{
            const data = await res.json();
            surprisesData = data.surprises?.recent || [];
            console.log('Surprises loaded:', surprisesData.length);
            renderSurprisesPage();
          }} else {{
            console.error('API fetch failed:', res.status);
          }}
        }} catch (e) {{
          console.error('initPage error:', e);
        }}
      }}

      initPage();
      startStream();
      wireTaste();
    </script>
</body>
</html>'''
    return html


def generate_ops_html():
    """Generate orchestration + skills ops page."""
    data = get_ops_data()
    skills_total = data.get("skills_total", 0)
    needs_attention = data.get("needs_attention", [])
    top_performers = data.get("top_performers", [])
    categories = data.get("categories", {})
    agents = data.get("agents", [])
    recent_handoffs = data.get("recent_handoffs", [])
    best_pairs = data.get("best_pairs", [])
    risky_pairs = data.get("risky_pairs", [])
    most_used = data.get("most_used", [])
    no_signal_skills = data.get("no_signal_skills", [])
    no_signal_count = data.get("no_signal_count", 0)
    advisory = data.get("advisory", {}) if isinstance(data.get("advisory"), dict) else {}
    advisory_badge = advisory.get("delivery_badge", {}) if isinstance(advisory.get("delivery_badge"), dict) else {}
    advisory_state = str(advisory_badge.get("state") or "blocked").lower()
    advisory_class = "good" if advisory_state in {"live", "fallback"} else "bad"
    advisory_reason = str(advisory_badge.get("reason") or "--")
    advisory_event = str(advisory_badge.get("event") or "--")
    advisory_age = "--"
    if advisory_badge.get("age_s") is not None:
        advisory_age = f'{round(_to_float(advisory_badge.get("age_s"), 0.0))}s'

    idx_raw = (data.get("index_generated_at") or "").strip()
    idx_label = "unknown"
    if idx_raw:
        try:
            idx_label = datetime.fromisoformat(idx_raw).strftime("%Y-%m-%d %H:%M")
        except Exception:
            idx_label = idx_raw

    def fmt_ts(ts):
        try:
            return datetime.fromtimestamp(float(ts)).strftime("%H:%M:%S")
        except Exception:
            return "--:--:--"

    needs_html = ""
    for item in needs_attention:
        rate = int(item.get("rate", 0) * 100)
        success = item.get("success", 0)
        total = item.get("total", 0)
        needs_html += f'''
        <div class="ops-row">
            <span class="ops-name">{item.get("skill", "unknown")}</span>
            <span class="ops-meta">{rate}% ({success}/{total})</span>
            <span class="pill bad">Needs attention</span>
        </div>'''
    if not needs_html:
        needs_html = '<div class="empty">No skills need attention yet.</div>'

    top_html = ""
    for item in top_performers:
        rate = int(item.get("rate", 0) * 100)
        success = item.get("success", 0)
        total = item.get("total", 0)
        top_html += f'''
        <div class="ops-row">
            <span class="ops-name">{item.get("skill", "unknown")}</span>
            <span class="ops-meta">{rate}% ({success}/{total})</span>
            <span class="pill good">Strong</span>
        </div>'''
    if not top_html:
        top_html = '<div class="empty">No strong performers yet.</div>'

    most_html = ""
    for item in most_used:
        total = item.get("total", 0)
        rate = int(item.get("rate", 0) * 100)
        most_html += f'''
        <div class="ops-row">
            <span class="ops-name">{item.get("skill", "unknown")}</span>
            <span class="ops-meta">{total} uses</span>
            <span class="pill">{rate}%</span>
        </div>'''
    if not most_html:
        most_html = '<div class="empty">No usage data yet.</div>'

    cat_html = ""
    for cat, count in sorted(categories.items(), key=lambda x: (-x[1], x[0])):
        cat_html += f'<span class="pill">{cat} <span class="pill-count">{count}</span></span>'
    if not cat_html:
        cat_html = '<span class="muted">No skill index found.</span>'

    no_signal_html = ""
    for name in no_signal_skills:
        no_signal_html += f'<span class="pill">{name}</span>'
    if not no_signal_html:
        no_signal_html = '<span class="muted">All skills have signals.</span>'

    agents_sorted = sorted(
        agents,
        key=lambda a: (a.get("success_rate", 0), a.get("total_tasks", 0)),
        reverse=True,
    )[:6]
    agents_html = ""
    for a in agents_sorted:
        name = a.get("name") or a.get("agent_id") or "agent"
        spec = a.get("specialization") or "general"
        rate = int(a.get("success_rate", 0) * 100)
        total = a.get("total_tasks", 0)
        agents_html += f'''
        <div class="ops-row">
            <span class="ops-name">{name}</span>
            <span class="ops-meta">{spec}</span>
            <span class="pill">{rate}% / {total}</span>
        </div>'''
    if not agents_html:
        agents_html = '<div class="empty">No agents registered yet.</div>'

    best_html = ""
    for p in best_pairs:
        rate = int(p.get("rate", 0) * 100)
        known = p.get("known", 0)
        best_html += f'''
        <div class="ops-row">
            <span class="ops-name">{p.get("pair", "unknown")}</span>
            <span class="ops-meta">{rate}% ({known} known)</span>
            <span class="pill good">Stable</span>
        </div>'''
    if not best_html:
        best_html = '<div class="empty">No stable pairings yet.</div>'

    risky_html = ""
    for p in risky_pairs:
        rate = int(p.get("rate", 0) * 100)
        known = p.get("known", 0)
        risky_html += f'''
        <div class="ops-row">
            <span class="ops-name">{p.get("pair", "unknown")}</span>
            <span class="ops-meta">{rate}% ({known} known)</span>
            <span class="pill bad">Risky</span>
        </div>'''
    if not risky_html:
        risky_html = '<div class="empty">No risky pairings yet.</div>'

    recent_html = ""
    for h in recent_handoffs:
        status = h.get("success")
        status_label = "ok" if status is True else "fail" if status is False else "unknown"
        status_class = "good" if status is True else "bad" if status is False else ""
        recent_html += f'''
        <div class="ops-row">
            <span class="ops-name">{h.get("from_agent", "unknown")} -> {h.get("to_agent", "unknown")}</span>
            <span class="ops-meta">{fmt_ts(h.get("timestamp"))}</span>
            <span class="pill {status_class}">{status_label}</span>
        </div>'''
    if not recent_html:
        recent_html = '<div class="empty">No handoffs captured yet.</div>'

    css = """
        :root {
            --bg-primary: #0e1016;
            --bg-secondary: #151820;
            --bg-tertiary: #1c202a;
            --text-primary: #e2e4e9;
            --text-secondary: #9aa3b5;
            --text-tertiary: #6b7489;
            --border: #2a3042;
            --green-dim: #00C49A;
            --orange: #D97757;
            --red: #FF4D4D;
            --font-mono: "JetBrains Mono", monospace;
            --font-serif: "Instrument Serif", Georgia, serif;
        }

        * { margin: 0; padding: 0; box-sizing: border-box; }

        body {
            font-family: var(--font-mono);
            background: var(--bg-primary);
            color: var(--text-primary);
            line-height: 1.6;
            font-size: 14px;
        }

        .navbar {
            height: 52px;
            border-bottom: 1px solid var(--border);
            display: flex;
            align-items: center;
            padding: 0 1.5rem;
        }

        .navbar-logo {
            display: flex;
            align-items: center;
            gap: 0.4rem;
        }

        .navbar-icon {
            width: 22px;
            height: 22px;
            object-fit: contain;
            display: block;
        }

        .navbar-text {
            font-family: var(--font-serif);
            font-size: 1.25rem;
            color: var(--text-primary);
        }

        .navbar-product {
            font-family: var(--font-serif);
            font-size: 1.25rem;
            color: var(--green-dim);
        }

        .navbar-links {
            margin-left: auto;
            display: flex;
            gap: 1rem;
        }

        .nav-link {
            color: var(--text-secondary);
            text-decoration: none;
            font-size: 0.7rem;
            letter-spacing: 0.1em;
            text-transform: uppercase;
            border-bottom: 1px solid transparent;
            padding-bottom: 2px;
        }

        .nav-link:hover {
            color: var(--text-primary);
        }

        .nav-link.active {
            color: var(--text-primary);
            border-color: var(--green-dim);
        }

        main {
            max-width: 1100px;
            margin: 0 auto;
            padding: 2rem 1.5rem;
        }

        .hero {
            text-align: center;
            margin-bottom: 2.5rem;
        }

        .hero h1 {
            font-family: var(--font-serif);
            font-size: 2.2rem;
            font-weight: 400;
            margin-bottom: 0.5rem;
        }

        .hero h1 span {
            color: var(--green-dim);
        }

        .hero-sub {
            color: var(--text-secondary);
            font-size: 0.9rem;
        }

        .stats-grid {
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 1rem;
            margin-bottom: 2rem;
        }

        .stat-card {
            background: var(--bg-secondary);
            border: 1px solid var(--border);
            padding: 1.25rem;
            text-align: center;
        }

        .stat-value {
            font-family: var(--font-serif);
            font-size: 2.2rem;
            color: var(--green-dim);
            line-height: 1;
        }

        .stat-label {
            font-size: 0.7rem;
            text-transform: uppercase;
            letter-spacing: 0.1em;
            color: var(--text-tertiary);
            margin-top: 0.5rem;
        }

        .grid-2 {
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 1.25rem;
            margin-bottom: 1.5rem;
        }

        .card {
            background: var(--bg-secondary);
            border: 1px solid var(--border);
        }

        .card-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 1rem 1.25rem;
            border-bottom: 1px solid var(--border);
            background: var(--bg-tertiary);
        }

        .card-title {
            font-size: 0.8rem;
            text-transform: uppercase;
            letter-spacing: 0.1em;
            color: var(--text-secondary);
        }

        .card-body {
            padding: 1rem 1.25rem;
        }

        .pill {
            display: inline-flex;
            align-items: center;
            gap: 0.4rem;
            border: 1px solid var(--border);
            padding: 0.2rem 0.5rem;
            font-size: 0.65rem;
            text-transform: uppercase;
            letter-spacing: 0.08em;
            color: var(--text-secondary);
        }

        .pill.good {
            border-color: rgba(0, 196, 154, 0.6);
            color: var(--green-dim);
        }

        .pill.bad {
            border-color: rgba(255, 77, 77, 0.6);
            color: var(--red);
        }

        .pill-count {
            color: var(--text-primary);
        }

        .ops-row {
            display: grid;
            grid-template-columns: 2fr 1fr auto;
            gap: 0.75rem;
            align-items: center;
            padding: 0.7rem 0;
            border-bottom: 1px solid var(--border);
        }

        .ops-row:last-child {
            border-bottom: none;
        }

        .ops-name {
            color: var(--text-primary);
            font-size: 0.85rem;
        }

        .ops-meta {
            color: var(--text-tertiary);
            font-size: 0.75rem;
        }

        .pill-row {
            display: flex;
            flex-wrap: wrap;
            gap: 0.5rem;
        }

        .muted {
            color: var(--text-tertiary);
            font-size: 0.75rem;
        }

        .empty {
            color: var(--text-tertiary);
            font-size: 0.8rem;
            padding: 0.5rem 0;
        }

        .footer {
            border-top: 1px solid var(--border);
            padding: 1rem 1.5rem;
            text-align: center;
            color: var(--text-tertiary);
            font-size: 0.7rem;
        }

        @media (max-width: 860px) {
            .stats-grid { grid-template-columns: repeat(2, 1fr); }
            .grid-2 { grid-template-columns: 1fr; }
            .ops-row { grid-template-columns: 1fr; }
        }
    """

    ops_js = """
      const $ = (id) => document.getElementById(id);

      function esc(s) {
        return String(s ?? '').replace(/[&<>"']/g, (c) => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
      }

      function setHTML(id, html) {
        const el = $(id);
        if (el) el.innerHTML = html;
      }

      function fmtTime(ts) {
        try {
          const d = new Date((Number(ts) || 0) * 1000);
          return d.toLocaleTimeString('en-US', { hour12: false });
        } catch (e) {
          return '--:--:--';
        }
      }

      function renderNeeds(list) {
        if (!Array.isArray(list) || list.length === 0) return '<div class="empty">No skills need attention yet.</div>';
        return list.map((item) => {
          const rate = Math.round((item.rate || 0) * 100);
          const success = item.success || 0;
          const total = item.total || 0;
          return `
            <div class="ops-row">
              <span class="ops-name">${esc(item.skill || 'unknown')}</span>
              <span class="ops-meta">${rate}% (${success}/${total})</span>
              <span class="pill bad">Needs attention</span>
            </div>`;
        }).join('');
      }

      function renderStrong(list) {
        if (!Array.isArray(list) || list.length === 0) return '<div class="empty">No strong performers yet.</div>';
        return list.map((item) => {
          const rate = Math.round((item.rate || 0) * 100);
          const success = item.success || 0;
          const total = item.total || 0;
          return `
            <div class="ops-row">
              <span class="ops-name">${esc(item.skill || 'unknown')}</span>
              <span class="ops-meta">${rate}% (${success}/${total})</span>
              <span class="pill good">Strong</span>
            </div>`;
        }).join('');
      }

      function renderMost(list) {
        if (!Array.isArray(list) || list.length === 0) return '<div class="empty">No usage data yet.</div>';
        return list.map((item) => {
          const rate = Math.round((item.rate || 0) * 100);
          const total = item.total || 0;
          return `
            <div class="ops-row">
              <span class="ops-name">${esc(item.skill || 'unknown')}</span>
              <span class="ops-meta">${total} uses</span>
              <span class="pill">${rate}%</span>
            </div>`;
        }).join('');
      }

      function renderCategories(obj) {
        if (!obj || Object.keys(obj).length === 0) return '<span class="muted">No skill index found.</span>';
        return Object.entries(obj)
          .sort((a, b) => b[1] - a[1])
          .map(([cat, count]) => `<span class="pill">${esc(cat)} <span class="pill-count">${count}</span></span>`)
          .join('');
      }

      function renderNoSignal(list) {
        if (!Array.isArray(list) || list.length === 0) return '<span class="muted">All skills have signals.</span>';
        return list.map((name) => `<span class="pill">${esc(name)}</span>`).join('');
      }

      function renderPairs(list, tone) {
        if (!Array.isArray(list) || list.length === 0) {
          return `<div class="empty">No ${tone === 'good' ? 'stable' : 'risky'} pairings yet.</div>`;
        }
        return list.map((item) => {
          const rate = Math.round((item.rate || 0) * 100);
          const known = item.known || 0;
          const klass = tone === 'good' ? 'good' : 'bad';
          const label = tone === 'good' ? 'Stable' : 'Risky';
          return `
            <div class="ops-row">
              <span class="ops-name">${esc(item.pair || 'unknown')}</span>
              <span class="ops-meta">${rate}% (${known} known)</span>
              <span class="pill ${klass}">${label}</span>
            </div>`;
        }).join('');
      }

      function renderAgents(list) {
        if (!Array.isArray(list) || list.length === 0) return '<div class="empty">No agents registered yet.</div>';
        return list.map((item) => {
          const name = item.name || item.agent_id || 'agent';
          const spec = item.specialization || 'general';
          const rate = Math.round((item.success_rate || 0) * 100);
          const total = item.total_tasks || 0;
          return `
            <div class="ops-row">
              <span class="ops-name">${esc(name)}</span>
              <span class="ops-meta">${esc(spec)}</span>
              <span class="pill">${rate}% / ${total}</span>
            </div>`;
        }).join('');
      }

      function renderRecent(list) {
        if (!Array.isArray(list) || list.length === 0) return '<div class="empty">No handoffs captured yet.</div>';
        return list.map((item) => {
          const status = item.success;
          const statusLabel = status === true ? 'ok' : status === false ? 'fail' : 'unknown';
          const statusClass = status === true ? 'good' : status === false ? 'bad' : '';
          return `
            <div class="ops-row">
              <span class="ops-name">${esc(item.from_agent || 'unknown')} -> ${esc(item.to_agent || 'unknown')}</span>
              <span class="ops-meta">${fmtTime(item.timestamp)}</span>
              <span class="pill ${statusClass}">${statusLabel}</span>
            </div>`;
        }).join('');
      }

      function renderAdvisory(advisory) {
        const adv = advisory || {};
        const badge = adv.delivery_badge || {};
        const packet = adv.packet_store || {};
        const worker = adv.prefetch_worker || {};
        const age = badge.age_s == null ? '--' : `${Math.round(Number(badge.age_s) || 0)}s`;
        const emission = `${Math.round((Number(adv.emission_rate) || 0) * 100)}%`;
        return [
          `<div class="ops-row"><span class="ops-name">Reason</span><span class="ops-meta">${esc(badge.reason || '--')}</span><span class="pill">${esc(badge.event || '--')}</span></div>`,
          `<div class="ops-row"><span class="ops-name">Age</span><span class="ops-meta">${age}</span><span class="pill">${emission}</span></div>`,
          `<div class="ops-row"><span class="ops-name">Packet Queue</span><span class="ops-meta">${packet.queue_depth ?? 0}</span><span class="pill">${worker.pending_jobs ?? 0} pending</span></div>`,
        ].join('');
      }

      function formatIndexLabel(raw) {
        if (!raw) return 'unknown';
        try {
          const d = new Date(raw);
          if (Number.isNaN(d.getTime())) return raw;
          return d.toLocaleString('en-US', { hour12: false });
        } catch (e) {
          return raw;
        }
      }

      function applyOps(data) {
        if ($('ops-skills-total')) $('ops-skills-total').textContent = data.skills_total ?? 0;
        if ($('ops-needs-count')) $('ops-needs-count').textContent = (data.needs_attention || []).length;
        if ($('ops-agents-count')) $('ops-agents-count').textContent = (data.agents || []).length;
        if ($('ops-handoffs-count')) $('ops-handoffs-count').textContent = (data.recent_handoffs || []).length;
        if ($('ops-index-label')) $('ops-index-label').textContent = `Index ${formatIndexLabel(data.index_generated_at || '')}`;
        if ($('ops-categories-count')) $('ops-categories-count').textContent = `${Object.keys(data.categories || {}).length} categories`;
        if ($('ops-no-signal-label')) $('ops-no-signal-label').textContent = `No-signal skills (${data.no_signal_count ?? 0})`;
        if ($('ops-recent-count')) $('ops-recent-count').textContent = `${(data.recent_handoffs || []).length} shown`;

        setHTML('ops-needs', renderNeeds(data.needs_attention));
        setHTML('ops-strong', renderStrong(data.top_performers));
        setHTML('ops-most', renderMost(data.most_used));
        setHTML('ops-categories', renderCategories(data.categories));
        setHTML('ops-no-signal', renderNoSignal(data.no_signal_skills));
        setHTML('ops-best', renderPairs(data.best_pairs, 'good'));
        setHTML('ops-risky', renderPairs(data.risky_pairs, 'bad'));
        setHTML('ops-agents', renderAgents(data.agents));
        setHTML('ops-recent', renderRecent(data.recent_handoffs));
        setHTML('ops-advisory', renderAdvisory(data.advisory));

        const advPill = $('ops-advisory-state');
        if (advPill) {
          const state = String(data.advisory?.delivery_badge?.state || 'blocked').toLowerCase();
          const klass = state === 'live' || state === 'fallback' ? 'good' : 'bad';
          advPill.className = `pill ${klass}`;
          advPill.textContent = state;
        }
      }

      async function tickOps() {
        try {
          const res = await fetch('/api/ops', { cache: 'no-store' });
          if (!res.ok) return;
          const data = await res.json();
          applyOps(data);
        } catch (e) {
          // ignore
        }
      }

      function startOpsStream() {
        if (!window.EventSource) {
          tickOps();
          setInterval(tickOps, 2000);
          return;
        }
        const es = new EventSource('/api/ops/stream');
        es.onmessage = (event) => {
          try {
            const data = JSON.parse(event.data || '{}');
            applyOps(data);
          } catch (e) {
            // ignore bad payloads
          }
        };
        es.onerror = () => {
          es.close();
          setTimeout(startOpsStream, 3000);
        };
      }

      startOpsStream();
    """

    html = f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Spark Ops</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Instrument+Serif:ital@0;1&family=JetBrains+Mono:wght@400;500;600&display=swap" rel="stylesheet">
    <style>{css}</style>
</head>
<body>
    <nav class="navbar">
        <div class="navbar-logo">
            <img src="/logo.png" alt="vibeship" class="navbar-icon" />
            <span class="navbar-text">vibeship</span>
            <span class="navbar-product">spark lab</span>
        </div>
        <div class="navbar-links">
            <a class="nav-link" href="/">Overview</a>
            <a class="nav-link active" href="/ops">Orchestration</a>
            <a class="nav-link" href="/dashboards">Dashboards</a>
            <a class="nav-link" href="http://localhost:{PULSE_PORT}">Pulse</a>
            <a class="nav-link" href="http://localhost:{META_RALPH_PORT}">Meta-Ralph</a>
        </div>
    </nav>

    <main>
        <div class="hero">
            <h1>Orchestration <span>& Skills</span></h1>
            <p class="hero-sub">Skills effectiveness. Agent coordination. Operational signals.</p>
        </div>

        <div class="stats-grid">
            <div class="stat-card">
                <div class="stat-value" id="ops-skills-total">{skills_total}</div>
                <div class="stat-label">Skills Indexed</div>
            </div>
            <div class="stat-card">
                <div class="stat-value" id="ops-needs-count">{len(needs_attention)}</div>
                <div class="stat-label">Needs Attention</div>
            </div>
            <div class="stat-card">
                <div class="stat-value" id="ops-agents-count">{len(agents)}</div>
                <div class="stat-label">Agents</div>
            </div>
            <div class="stat-card">
                <div class="stat-value" id="ops-handoffs-count">{len(recent_handoffs)}</div>
                <div class="stat-label">Recent Handoffs</div>
            </div>
        </div>

        <div class="grid-2">
            <div class="card">
                <div class="card-header">
                    <span class="card-title">Skill Health</span>
                    <span class="muted" id="ops-index-label">Index {idx_label}</span>
                </div>
                <div class="card-body">
                    <div class="muted" style="margin-bottom:0.6rem;">Needs attention</div>
                    <div id="ops-needs">
                        {needs_html}
                    </div>
                    <div style="height: 1px; background: var(--border); margin: 0.75rem 0;"></div>
                    <div class="muted" style="margin-bottom:0.6rem;">Strong performers</div>
                    <div id="ops-strong">
                        {top_html}
                    </div>
                    <div style="height: 1px; background: var(--border); margin: 0.75rem 0;"></div>
                    <div class="muted" style="margin-bottom:0.6rem;">Most used</div>
                    <div id="ops-most">
                        {most_html}
                    </div>
                </div>
            </div>

            <div class="card">
                <div class="card-header">
                    <span class="card-title">Skill Coverage</span>
                    <span class="muted" id="ops-categories-count">{len(categories)} categories</span>
                </div>
                <div class="card-body">
                    <div class="pill-row" id="ops-categories">
                        {cat_html}
                    </div>
                    <div style="height: 1px; background: var(--border); margin: 0.75rem 0;"></div>
                    <div class="muted" style="margin-bottom:0.6rem;" id="ops-no-signal-label">No-signal skills ({no_signal_count})</div>
                    <div class="pill-row" id="ops-no-signal">
                        {no_signal_html}
                    </div>
                </div>
            </div>
        </div>

        <div class="grid-2">
            <div class="card">
                <div class="card-header">
                    <span class="card-title">Team Coordination</span>
                    <span class="muted">Pair stability</span>
                </div>
                <div class="card-body">
                    <div class="muted" style="margin-bottom:0.6rem;">Stable pairs</div>
                    <div id="ops-best">
                        {best_html}
                    </div>
                    <div style="height: 1px; background: var(--border); margin: 0.75rem 0;"></div>
                    <div class="muted" style="margin-bottom:0.6rem;">Risky pairs</div>
                    <div id="ops-risky">
                        {risky_html}
                    </div>
                </div>
            </div>

            <div class="card">
                <div class="card-header">
                    <span class="card-title">Agent Reliability</span>
                    <span class="muted">Top agents</span>
                </div>
                <div class="card-body" id="ops-agents">
                    {agents_html}
                </div>
            </div>

            <div class="card">
                <div class="card-header">
                    <span class="card-title">Advisory Delivery</span>
                    <span class="pill {advisory_class}" id="ops-advisory-state">{advisory_state}</span>
                </div>
                <div class="card-body" id="ops-advisory">
                    <div class="ops-row">
                        <span class="ops-name">Reason</span>
                        <span class="ops-meta">{advisory_reason}</span>
                        <span class="pill">{advisory_event}</span>
                    </div>
                    <div class="ops-row">
                        <span class="ops-name">Age</span>
                        <span class="ops-meta">{advisory_age}</span>
                        <span class="pill">{int(_to_float(advisory.get("emission_rate"), 0.0) * 100)}%</span>
                    </div>
                    <div class="ops-row">
                        <span class="ops-name">Packet Queue</span>
                        <span class="ops-meta">{_to_int((advisory.get("packet_store") or {}).get("queue_depth"), 0)}</span>
                        <span class="pill">{_to_int((advisory.get("prefetch_worker") or {}).get("pending_jobs"), 0)} pending</span>
                    </div>
                </div>
            </div>
        </div>

        <div class="card" style="margin-bottom: 1.5rem;">
            <div class="card-header">
                <span class="card-title">Recent Handoffs</span>
                <span class="muted" id="ops-recent-count">{len(recent_handoffs)} shown</span>
            </div>
            <div class="card-body" id="ops-recent">
                {recent_html}
            </div>
        </div>
    </main>

    <div class="footer">
        <p>Updated {datetime.now().strftime("%H:%M:%S")} · Spark Ops</p>
    </div>
    <script>{ops_js}</script>
</body>
</html>'''
    return html


def _nav_html(active: str) -> str:
    links = [
        ("mission", "/", "Mission Control"),
        ("learning", "/learning", "Learning Factory"),
        ("rabbit", "/rabbit", "Rabbit Hole Recovery"),
        ("acceptance", "/acceptance", "Acceptance Board"),
        ("ops", "/ops", "Ops"),
        ("dashboards", "/dashboards", "Dashboards"),
        ("pulse", f"http://localhost:{PULSE_PORT}", "Pulse"),
        ("meta_ralph", f"http://localhost:{META_RALPH_PORT}", "Meta-Ralph"),
    ]
    items = []
    for key, href, label in links:
        cls = "nav-link active" if key == active else "nav-link"
        items.append(f'<a class="{cls}" href="{href}">{label}</a>')
    return "".join(items)


def _funnel_html(funnel: Dict[str, Any]) -> str:
    return f"""
    <div class="funnel-grid">
      <div class="funnel-item"><span class="f-label">retrieved</span><span id="f-retrieved" class="f-value">{funnel.get("retrieved", 0)}</span></div>
      <div class="funnel-item"><span class="f-label">cited</span><span id="f-cited" class="f-value">{funnel.get("cited", 0)}</span></div>
      <div class="funnel-item"><span class="f-label">used</span><span id="f-used" class="f-value">{funnel.get("used", 0)}</span></div>
      <div class="funnel-item"><span class="f-label">helped</span><span id="f-helped" class="f-value">{funnel.get("helped", 0)}</span></div>
      <div class="funnel-item accent"><span class="f-label">promoted</span><span id="f-promoted" class="f-value">{funnel.get("promoted", 0)}</span></div>
    </div>
    """


def _base_page(title: str, active: str, body: str, data: Dict[str, Any], endpoint: str, page_js: str) -> str:
    boot = json.dumps(data)
    nav = _nav_html(active)
    funnel = _funnel_html(data.get("funnel", {}))
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1.0"/>
  <title>{title}</title>
  <style>
    @import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap');
    :root {{
      --bg-0: #0b0f14;
      --bg-1: #101724;
      --panel: #141d2b;
      --panel-2: #0f1621;
      --text: #e6edf7;
      --muted: #9aa8bb;
      --accent: #f5b547;
      --accent-2: #48d1a6;
      --danger: #ff6b6b;
      --warn: #f6c26b;
      --ok: #6ee7b7;
      --border: rgba(148, 163, 184, 0.18);
      --shadow: 0 18px 40px rgba(0,0,0,0.35);
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      font-family: "Space Grotesk", system-ui, -apple-system, sans-serif;
      color: var(--text);
      background: radial-gradient(1200px 600px at 10% -10%, rgba(72,209,166,0.15), transparent),
                  radial-gradient(1000px 500px at 110% 0%, rgba(245,181,71,0.12), transparent),
                  linear-gradient(180deg, var(--bg-1), var(--bg-0));
      min-height: 100vh;
    }}
    .bg-grid {{
      position: fixed;
      inset: 0;
      background-image: linear-gradient(rgba(255,255,255,0.03) 1px, transparent 1px),
                        linear-gradient(90deg, rgba(255,255,255,0.03) 1px, transparent 1px);
      background-size: 120px 120px;
      pointer-events: none;
      opacity: 0.25;
    }}
    header {{
      display: flex;
      align-items: center;
      justify-content: space-between;
      padding: 24px 6vw 12px;
    }}
    .title {{
      font-size: 1.5rem;
      font-weight: 700;
      letter-spacing: 0.02em;
    }}
    nav {{
      display: flex;
      gap: 12px;
      flex-wrap: wrap;
    }}
    .nav-link {{
      text-decoration: none;
      color: var(--muted);
      border: 1px solid var(--border);
      padding: 6px 12px;
      border-radius: 999px;
      transition: 0.2s ease;
      font-size: 0.85rem;
    }}
    .nav-link:hover {{
      color: var(--text);
      border-color: rgba(245,181,71,0.6);
    }}
    .nav-link.active {{
      color: var(--text);
      background: rgba(245,181,71,0.12);
      border-color: rgba(245,181,71,0.6);
    }}
    .funnel {{
      padding: 0 6vw 18px;
    }}
    .funnel-grid {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
      gap: 12px;
    }}
    .funnel-item {{
      background: var(--panel);
      border: 1px solid var(--border);
      border-radius: 14px;
      padding: 10px 14px;
      box-shadow: var(--shadow);
      display: flex;
      flex-direction: column;
      gap: 6px;
    }}
    .funnel-item.accent {{
      border-color: rgba(72,209,166,0.6);
      background: linear-gradient(135deg, rgba(72,209,166,0.16), rgba(20,29,43,0.9));
    }}
    .f-label {{
      text-transform: uppercase;
      font-size: 0.65rem;
      letter-spacing: 0.2em;
      color: var(--muted);
    }}
    .f-value {{
      font-family: "JetBrains Mono", ui-monospace, monospace;
      font-size: 1.2rem;
      font-weight: 600;
    }}
    main {{
      padding: 0 6vw 40px;
      display: flex;
      flex-direction: column;
      gap: 24px;
    }}
    .grid {{
      display: grid;
      gap: 18px;
      grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
    }}
    .card {{
      background: var(--panel);
      border: 1px solid var(--border);
      border-radius: 16px;
      padding: 16px;
      box-shadow: var(--shadow);
    }}
    .card-header {{
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 12px;
    }}
    .card-title {{
      font-weight: 600;
      font-size: 1rem;
    }}
    .muted {{
      color: var(--muted);
      font-size: 0.8rem;
    }}
    .pill {{
      padding: 4px 10px;
      border-radius: 999px;
      font-size: 0.7rem;
      border: 1px solid var(--border);
      color: var(--muted);
    }}
    .pill.ok {{ color: var(--ok); border-color: rgba(110,231,183,0.5); }}
    .pill.warn {{ color: var(--warn); border-color: rgba(246,194,107,0.5); }}
    .pill.danger {{ color: var(--danger); border-color: rgba(255,107,107,0.5); }}
    .list {{
      display: flex;
      flex-direction: column;
      gap: 10px;
    }}
    .row {{
      display: flex;
      justify-content: space-between;
      align-items: center;
      gap: 10px;
      font-size: 0.85rem;
      padding: 8px 10px;
      border-radius: 12px;
      background: var(--panel-2);
      border: 1px solid rgba(148,163,184,0.12);
    }}
    .mono {{
      font-family: "JetBrains Mono", ui-monospace, monospace;
    }}
    .actions {{
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
    }}
    .input {{
      border: 1px solid var(--border);
      background: rgba(15,22,33,0.9);
      color: var(--text);
      padding: 8px 10px;
      border-radius: 10px;
      font-size: 0.8rem;
      min-width: 180px;
    }}
    .input:focus {{
      outline: none;
      border-color: rgba(245,181,71,0.7);
    }}
    .btn {{
      border: 1px solid var(--border);
      padding: 8px 12px;
      border-radius: 10px;
      background: rgba(15,22,33,0.8);
      color: var(--text);
      font-size: 0.8rem;
      cursor: pointer;
    }}
    .btn.primary {{
      background: rgba(245,181,71,0.16);
      border-color: rgba(245,181,71,0.6);
    }}
    .btn.danger {{
      background: rgba(255,107,107,0.16);
      border-color: rgba(255,107,107,0.6);
    }}
    footer {{
      padding: 0 6vw 24px;
      color: var(--muted);
      font-size: 0.75rem;
    }}
    @keyframes pulse {{
      0% {{ box-shadow: 0 0 0 rgba(245,181,71,0.0); }}
      50% {{ box-shadow: 0 0 18px rgba(245,181,71,0.25); }}
      100% {{ box-shadow: 0 0 0 rgba(245,181,71,0.0); }}
    }}
    .pulse {{ animation: pulse 3s ease-in-out infinite; }}
  </style>
</head>
<body>
  <div class="bg-grid"></div>
  <header>
    <div class="title">{title}</div>
    <nav>{nav}</nav>
  </header>
  <section class="funnel">{funnel}</section>
  <main>{body}</main>
  <footer>Updated <span id="last-updated">{datetime.now().strftime("%H:%M:%S")}</span></footer>
  <script>
    const ENDPOINT = "{endpoint}";
    const BOOT = {boot};
    const $ = (id) => document.getElementById(id);
    const setText = (id, value) => {{ const el = $(id); if (el) el.textContent = value ?? "â€”"; }};
    const renderList = (id, items, render) => {{
      const el = $(id);
      if (!el) return;
      if (!items || !items.length) {{
        el.innerHTML = '<div class="muted">No activity yet.</div>';
        return;
      }}
      el.innerHTML = items.map(render).join('');
    }};
    const updateFunnel = (f) => {{
      if (!f) return;
      setText("f-retrieved", f.retrieved ?? 0);
      setText("f-cited", f.cited ?? 0);
      setText("f-used", f.used ?? 0);
      setText("f-helped", f.helped ?? 0);
      setText("f-promoted", f.promoted ?? 0);
    }};
    const updatePage = (data) => {{
      if (!data) return;
      updateFunnel(data.funnel);
      setText("last-updated", data.timestamp || new Date().toLocaleTimeString());
      {page_js}
    }};
    updatePage(BOOT);
    setInterval(async () => {{
      try {{
        const res = await fetch(ENDPOINT, {{ cache: "no-store" }});
        const data = await res.json();
        updatePage(data);
      }} catch (e) {{}}
    }}, 4000);
  </script>
</body>
</html>"""


def generate_mission_html() -> str:
    data = get_mission_control_data()
    body = """
    <section class="grid">
      <div class="card">
        <div class="card-header"><span class="card-title">Services Health</span><span class="pill" id="services-summary"></span></div>
        <div class="list" id="services-list"></div>
      </div>
      <div class="card">
        <div class="card-header"><span class="card-title">Queue Health</span><span class="pill" id="queue-status"></span></div>
        <div class="list" id="queue-list"></div>
      </div>
      <div class="card">
        <div class="card-header"><span class="card-title">Bridge Cycle</span><span class="pill" id="bridge-status"></span></div>
        <div class="list" id="bridge-list"></div>
      </div>
      <div class="card">
        <div class="card-header"><span class="card-title">EIDOS Activity</span><span class="pill" id="eidos-status"></span></div>
        <div class="list" id="eidos-list"></div>
      </div>
    </section>
    <section class="grid">
      <div class="card">
        <div class="card-header"><span class="card-title">Active Episode</span><span class="pill" id="episode-phase"></span></div>
        <div class="list" id="episode-details"></div>
      </div>
      <div class="card">
        <div class="card-header"><span class="card-title">System Mode</span><span class="pill" id="mode-status"></span></div>
        <div class="list" id="mode-details"></div>
      </div>
      <div class="card">
        <div class="card-header"><span class="card-title">Advisory Delivery</span><span class="pill" id="advisory-state"></span></div>
        <div class="list" id="advisory-details"></div>
      </div>
    </section>
    <section class="grid">
      <div class="card">
        <div class="card-header"><span class="card-title">Watchers Feed</span><span class="muted">last 20</span></div>
        <div class="list" id="watchers-feed"></div>
      </div>
      <div class="card">
        <div class="card-header"><span class="card-title">Escalations</span><span class="muted">last 10</span></div>
        <div class="list" id="escalations-feed"></div>
      </div>
    </section>
    <section class="grid">
      <div class="card">
        <div class="card-header"><span class="card-title">Recent Runs</span><span class="muted">facade</span></div>
        <div class="list" id="runs-list"></div>
      </div>
      <div class="card">
        <div class="card-header"><span class="card-title">Run KPIs</span><span class="muted">last 50</span></div>
        <div class="list" id="run-kpis"></div>
      </div>
    </section>
    <section class="grid">
      <div class="card">
        <div class="card-header"><span class="card-title">Run Timeline</span><span class="muted">episode_id</span></div>
        <div class="actions">
          <input id="run-input" class="input" placeholder="episode_id" />
          <button class="btn primary" id="run-load">Load</button>
        </div>
        <div class="list" id="run-summary"></div>
        <div class="list" id="run-steps"></div>
        <div class="list" id="run-evidence"></div>
        <div class="list" id="run-outcomes"></div>
      </div>
    </section>
    <section class="grid">
      <div class="card">
        <div class="card-header"><span class="card-title">Trace Drilldown</span><span class="muted">trace_id</span></div>
        <div class="actions">
          <input id="trace-input" class="input" placeholder="trace_id" />
          <button class="btn primary" id="trace-load">Load</button>
        </div>
        <div class="list" id="trace-summary"></div>
        <div class="list" id="trace-steps"></div>
        <div class="list" id="trace-evidence"></div>
        <div class="list" id="trace-outcomes"></div>
      </div>
    </section>
    """
    page_js = """
      const renderTrace = (trace) => {
        if (!trace) return;
        const summary = [
          `<div class="row"><span>trace</span><span class="mono">${trace.trace_id || "—"}</span></div>`,
          `<div class="row"><span>steps</span><span class="mono">${(trace.steps || []).length}</span></div>`,
          `<div class="row"><span>evidence</span><span class="mono">${(trace.evidence || []).length}</span></div>`,
          `<div class="row"><span>outcomes</span><span class="mono">${(trace.outcomes || []).length}</span></div>`
        ];
        renderList("trace-summary", summary, (x) => x);
        renderList("trace-steps", trace.steps || [], (s) => `
          <div class="row">
            <span>${s.intent || "step"}</span>
            <span class="pill ${s.evaluation === "pass" ? "ok" : s.evaluation === "fail" ? "danger" : "warn"}">${s.evaluation || "unknown"}</span>
            <span class="mono">${s.step_id || ""}</span>
          </div>
        `);
        renderList("trace-evidence", trace.evidence || [], (e) => `
          <div class="row">
            <span>${e.type || "evidence"}</span>
            <span class="mono">${e.step_id || ""}</span>
            <span class="muted">${e.tool || ""}</span>
          </div>
        `);
        renderList("trace-outcomes", trace.outcomes || [], (o) => `
          <div class="row">
            <span>${o.polarity || "outcome"}</span>
            <span class="muted">${o.text || ""}</span>
          </div>
        `);
      };
      const loadTrace = async (traceId) => {
        const tid = (traceId || "").trim();
        if (!tid) return;
        try {
          const res = await fetch(`/api/trace?trace_id=${encodeURIComponent(tid)}`, { cache: "no-store" });
          const data = await res.json();
          renderTrace(data);
        } catch (e) {}
      };
      const renderRun = (run) => {
        if (!run) return;
        const ep = run.episode || {};
        const summary = [
          `<div class="row"><span>episode</span><span class="mono">${ep.episode_id || "—"}</span></div>`,
          `<div class="row"><span>goal</span><span class="muted">${ep.goal || ""}</span></div>`,
          `<div class="row"><span>phase</span><span class="mono">${ep.phase || ""}</span></div>`,
          `<div class="row"><span>outcome</span><span class="mono">${ep.outcome || ""}</span></div>`,
          `<div class="row"><span>steps</span><span class="mono">${ep.step_count ?? 0}</span></div>`
        ];
        renderList("run-summary", summary, (x) => x);
        renderList("run-steps", run.steps || [], (s) => `
          <div class="row">
            <span>${s.intent || "step"}</span>
            <span class="pill ${s.evaluation === "pass" ? "ok" : s.evaluation === "fail" ? "danger" : "warn"}">${s.evaluation || "unknown"}</span>
            <span class="mono">${s.step_id || ""}</span>
          </div>
        `);
        renderList("run-evidence", run.evidence || [], (e) => `
          <div class="row">
            <span>${e.type || "evidence"}</span>
            <span class="mono">${e.step_id || ""}</span>
            <span class="muted">${e.tool || ""}</span>
          </div>
        `);
        renderList("run-outcomes", run.outcomes || [], (o) => `
          <div class="row">
            <span>${o.polarity || "outcome"}</span>
            <span class="muted">${(o.text || "").slice(0, 120)}</span>
          </div>
        `);
      };
      const traceButton = (tid) => {
        if (!tid) return "";
        return `<button class="btn" onclick="loadTrace('${tid}')">trace</button>`;
      };
      const runButton = (episodeId) => {
        if (!episodeId) return "";
        return `<button class="btn" onclick="loadRun('${episodeId}')">run</button>`;
      };
      const loadRun = async (episodeId) => {
        const eid = (episodeId || "").trim();
        if (!eid) return;
        try {
          const res = await fetch(`/api/run?episode_id=${encodeURIComponent(eid)}`, { cache: "no-store" });
          const data = await res.json();
          renderRun(data);
        } catch (e) {}
      };

      const services = data.services || {};
      const serviceItems = Object.entries(services).map(([name, info]) => {
        const ok = info.healthy || info.running;
        const pill = ok ? "ok" : "danger";
        const details = [];
        if (info.pid) details.push(`pid ${info.pid}`);
        if (info.heartbeat_age_s !== undefined && info.heartbeat_age_s !== null) {
          details.push(`heartbeat ${Math.round(info.heartbeat_age_s)}s`);
        }
        return `<div class="row"><span>${name.replace(/_/g,' ')}</span><span class="pill ${pill}">${ok ? "ok" : "down"}</span><span class="muted mono">${details.join(" Â· ")}</span></div>`;
      });
      renderList("services-list", serviceItems, (x) => x);
      setText("services-summary", Object.keys(services).length + " services");

      const queue = data.queue || {};
      const queueItems = [
        `<div class="row"><span>events</span><span class="mono">${queue.event_count ?? 0}</span></div>`,
        `<div class="row"><span>oldest event</span><span class="mono">${queue.oldest_age ?? "â€”"}</span></div>`,
        `<div class="row"><span>invalid events</span><span class="mono">${queue.invalid_events ?? 0}</span></div>`,
        `<div class="row"><span>lock present</span><span class="mono">${queue.lock_present ? "yes" : "no"}</span></div>`
      ];
      renderList("queue-list", queueItems, (x) => x);
      setText("queue-status", queue.needs_rotation ? "rotate" : "ok");

      const bridge = data.bridge || {};
      const bridgeItems = [
        `<div class="row"><span>last run</span><span class="mono">${bridge.last_run || "â€”"}</span></div>`,
        `<div class="row"><span>patterns</span><span class="mono">${bridge.pattern_processed ?? 0}</span></div>`,
        `<div class="row"><span>content learned</span><span class="mono">${bridge.content_learned ?? 0}</span></div>`,
        `<div class="row"><span>errors</span><span class="mono">${(bridge.errors || []).length}</span></div>`
      ];
      renderList("bridge-list", bridgeItems, (x) => x);
      setText("bridge-status", (bridge.errors || []).length ? "errors" : "ok");

      const eidos = data.eidos || {};
      const eidosItems = [
        `<div class="row"><span>active episodes</span><span class="mono">${eidos.active_episodes ?? 0}</span></div>`,
        `<div class="row"><span>steps/min</span><span class="mono">${eidos.steps_per_min ?? 0}</span></div>`,
        `<div class="row"><span>watchers/min</span><span class="mono">${eidos.watchers_per_min ?? 0}</span></div>`
      ];
      renderList("eidos-list", eidosItems, (x) => x);
      setText("eidos-status", eidos.active_episodes ? "active" : "idle");

      const ep = data.active_episode;
      if (ep) {
        setText("episode-phase", ep.phase);
        const details = [
          `<div class="row"><span>goal</span><span class="muted">${ep.goal}</span></div>`,
          `<div class="row"><span>steps</span><span class="mono">${ep.step_count}</span></div>`,
          `<div class="row"><span>budget left</span><span class="mono">${ep.budget_remaining}</span></div>`,
          `<div class="row"><span>time remaining</span><span class="mono">${ep.time_remaining}</span></div>`
        ];
        const acc = data.acceptance_status || {};
        if (acc.plan_id) {
          details.push(`<div class="row"><span>acceptance</span><span class="mono">${acc.is_approved ? "approved" : "pending"} (${acc.critical_tests} critical)</span></div>`);
        }
        const recent = ep.recent_steps_detail || [];
        for (const s of recent) {
          details.push(`<div class="row"><span>${s.intent || "step"}</span><span class="mono">${s.trace_id || "—"}</span>${traceButton(s.trace_id)}</div>`);
        }
        renderList("episode-details", details, (x) => x);
      } else {
        setText("episode-phase", "none");
        renderList("episode-details", [], (x) => x);
      }

      const mode = data.minimal_mode || {};
      const modeActive = mode.currently_active;
      setText("mode-status", modeActive ? "minimal" : "normal");
      const modeItems = [
        `<div class="row"><span>state</span><span class="mono">${modeActive ? "active" : "normal"}</span></div>`,
        `<div class="row"><span>reason</span><span class="mono">${mode.reason || "â€”"}</span></div>`,
        `<div class="row"><span>edits allowed</span><span class="mono">${mode.edits_allowed ? "yes" : "no"}</span></div>`
      ];
      renderList("mode-details", modeItems, (x) => x);

      const advisory = data.advisory || {};
      const delivery = advisory.delivery_badge || {};
      const advisoryState = String(delivery.state || "blocked").toLowerCase();
      const advisoryClass = advisoryState === "live" ? "ok" : advisoryState === "fallback" ? "warn" : "danger";
      const advisoryPill = document.getElementById("advisory-state");
      if (advisoryPill) {
        advisoryPill.className = `pill ${advisoryClass}`;
        advisoryPill.textContent = advisoryState;
      }
      const advisoryItems = [
        `<div class="row"><span>reason</span><span class="mono">${delivery.reason || "--"}</span></div>`,
        `<div class="row"><span>event</span><span class="mono">${delivery.event || "--"}</span></div>`,
        `<div class="row"><span>age</span><span class="mono">${delivery.age_s == null ? "--" : Math.round(Number(delivery.age_s) || 0) + "s"}</span></div>`,
        `<div class="row"><span>emission rate</span><span class="mono">${Math.round((Number(advisory.emission_rate) || 0) * 100)}%</span></div>`,
        `<div class="row"><span>packet queue</span><span class="mono">${advisory.packet_store?.queue_depth ?? 0}</span></div>`,
        `<div class="row"><span>prefetch pending</span><span class="mono">${advisory.prefetch_worker?.pending_jobs ?? 0}</span></div>`
      ];
      renderList("advisory-details", advisoryItems, (x) => x);

      renderList("watchers-feed", data.watchers || [], (w) => `
        <div class="row">
          <span>${w.watcher}</span>
          <span class="pill ${w.severity === "force" ? "danger" : w.severity === "block" ? "warn" : "warn"}">${w.severity}</span>
          <span class="muted">${w.message}</span>
          ${traceButton(w.trace_id)}
        </div>
      `);

      renderList("escalations-feed", data.escalations || [], (e) => `
        <div class="row">
          <span>${e.type || "escalation"}</span>
          <span class="muted">${e.summary || e.reason || ""}</span>
          <span class="mono">${new Date((e.timestamp || 0) * 1000).toLocaleTimeString()}</span>
        </div>
      `);

      renderList("runs-list", data.runs || [], (r) => `
        <div class="row">
          <span>${r.goal}</span>
          <span class="mono">${r.step_count}</span>
          <span class="muted">${r.outcome}</span>
          ${runButton(r.episode_id)}
        </div>
      `);

      const kpis = data.run_kpis || {};
      renderList("run-kpis", [
        `<div class="row"><span>avg steps</span><span class="mono">${kpis.avg_steps ?? 0}</span></div>`,
        `<div class="row"><span>escape rate</span><span class="mono">${(kpis.escape_rate ?? 0) * 100}%</span></div>`,
        `<div class="row"><span>evidence ratio</span><span class="mono">${kpis.evidence_ratio ?? 0}</span></div>`
      ], (x) => x);

      const traceBtn = document.getElementById("trace-load");
      if (traceBtn && !traceBtn.dataset.bound) {
        traceBtn.dataset.bound = "1";
        traceBtn.onclick = () => {
          const input = document.getElementById("trace-input");
          loadTrace(input ? input.value : "");
        };
      }
      const runBtn = document.getElementById("run-load");
      if (runBtn && !runBtn.dataset.bound) {
        runBtn.dataset.bound = "1";
        runBtn.onclick = () => {
          const input = document.getElementById("run-input");
          loadRun(input ? input.value : "");
        };
      }
      const qp = new URLSearchParams(window.location.search);
      const qpTrace = qp.get("trace_id");
      if (qpTrace) {
        const input = document.getElementById("trace-input");
        if (input) input.value = qpTrace;
        loadTrace(qpTrace);
      }
      const qpRun = qp.get("episode_id");
      if (qpRun) {
        const input = document.getElementById("run-input");
        if (input) input.value = qpRun;
        loadRun(qpRun);
      }
    """
    return _base_page("Mission Control", "mission", body, data, "/api/mission", page_js)


def generate_learning_html() -> str:
    data = get_learning_factory_data()
    body = """
    <section class="grid">
      <div class="card">
        <div class="card-header"><span class="card-title">Distillation Pipeline</span><span class="pill" id="distill-total"></span></div>
        <div class="list" id="distillations-list"></div>
      </div>
      <div class="card">
        <div class="card-header"><span class="card-title">Truth Ledger</span><span class="pill" id="truth-total"></span></div>
        <div class="list" id="truth-list"></div>
      </div>
      <div class="card">
        <div class="card-header"><span class="card-title">Utilization</span><span class="pill" id="util-status"></span></div>
        <div class="list" id="util-list"></div>
      </div>
    </section>
    <section class="grid">
      <div class="card">
        <div class="card-header"><span class="card-title">Top Helped Distillations</span></div>
        <div class="list" id="top-helped"></div>
      </div>
      <div class="card">
        <div class="card-header"><span class="card-title">Top Retrieved / Ignored</span></div>
        <div class="list" id="top-ignored"></div>
      </div>
      <div class="card">
        <div class="card-header"><span class="card-title">Promotion</span><span class="pill" id="promo-ready"></span></div>
        <div class="list" id="promo-list"></div>
      </div>
    </section>
    """
    page_js = """
      const traceLink = (tid) => {
        if (!tid) return "";
        return `<a class="btn" href="/mission?trace_id=${encodeURIComponent(tid)}">trace</a>`;
      };
      const dist = data.distillations || {};
      setText("distill-total", dist.total ?? 0);
      const distList = [
        `<div class="row"><span>today</span><span class="mono">${dist.today ?? 0}</span></div>`,
        `<div class="row"><span>7d</span><span class="mono">${dist.last_7d ?? 0}</span></div>`
      ];
      Object.entries(dist.by_type || {}).forEach(([k,v]) => {
        distList.push(`<div class="row"><span>${k}</span><span class="mono">${v}</span></div>`);
      });
      renderList("distillations-list", distList, (x) => x);

      const truth = data.truth_ledger || {};
      setText("truth-total", truth.total ?? 0);
      const truthList = [
        `<div class="row"><span>claims</span><span class="mono">${truth.claims ?? 0}</span></div>`,
        `<div class="row"><span>facts</span><span class="mono">${truth.facts ?? 0}</span></div>`,
        `<div class="row"><span>rules</span><span class="mono">${truth.rules ?? 0}</span></div>`,
        `<div class="row"><span>stale</span><span class="mono">${truth.stale ?? 0}</span></div>`,
        `<div class="row"><span>contradicted</span><span class="mono">${truth.contradicted ?? 0}</span></div>`
      ];
      const levels = truth.evidence_levels || {};
      truthList.push(`<div class="row"><span>evidence strong</span><span class="mono">${levels.strong ?? 0}</span></div>`);
      truthList.push(`<div class="row"><span>evidence weak</span><span class="mono">${levels.weak ?? 0}</span></div>`);
      truthList.push(`<div class="row"><span>evidence none</span><span class="mono">${levels.none ?? 0}</span></div>`);
      renderList("truth-list", truthList, (x) => x);

      const util = data.utilization || {};
      setText("util-status", (data.funnel?.helped ?? 0) + " helped");
      renderList("util-list", [
        `<div class="row"><span>retrieved</span><span class="mono">${data.funnel?.retrieved ?? 0}</span></div>`,
        `<div class="row"><span>used</span><span class="mono">${data.funnel?.used ?? 0}</span></div>`,
        `<div class="row"><span>helped</span><span class="mono">${data.funnel?.helped ?? 0}</span></div>`
      ], (x) => x);

      renderList("top-helped", util.top_helped || [], (d) => `
        <div class="row"><span>${d.statement}</span><span class="mono">${d.helped}</span>${traceLink(d.trace_id)}</div>
      `);
      renderList("top-ignored", util.top_ignored || [], (d) => `
        <div class="row"><span>${d.statement}</span><span class="mono">${d.retrieved}</span>${traceLink(d.trace_id)}</div>
      `);

      const promo = data.promotion || {};
      setText("promo-ready", `${promo.ready_for_promotion ?? 0} ready`);
      renderList("promo-list", promo.recent_promoted || [], (p) => `
        <div class="row"><span>${p.insight}</span><span class="mono">${p.target}</span></div>
      `);
    """
    return _base_page("Learning Factory", "learning", body, data, "/api/learning", page_js)


def generate_rabbit_html() -> str:
    data = get_rabbit_recovery_data()
    body = """
    <section class="grid">
      <div class="card">
        <div class="card-header"><span class="card-title">Rabbit Hole Scoreboard</span></div>
        <div class="list" id="scoreboard-repeat"></div>
      </div>
      <div class="card">
        <div class="card-header"><span class="card-title">No-Evidence Streaks</span></div>
        <div class="list" id="scoreboard-evidence"></div>
      </div>
      <div class="card">
        <div class="card-header"><span class="card-title">Diff Thrash Files</span></div>
        <div class="list" id="scoreboard-diff"></div>
      </div>
    </section>
    <section class="grid">
      <div class="card">
        <div class="card-header"><span class="card-title">Escape Protocol Outcomes</span></div>
        <div class="list" id="escape-list"></div>
      </div>
      <div class="card">
        <div class="card-header"><span class="card-title">Minimal Mode Timeline</span></div>
        <div class="list" id="minimal-list"></div>
      </div>
      <div class="card">
        <div class="card-header"><span class="card-title">Manual Actions</span></div>
        <div class="actions">
          <button class="btn danger" onclick="triggerEscape()">Trigger ESCAPE_PROTOCOL</button>
          <button class="btn primary" onclick="enterMinimal()">Enter Minimal Mode</button>
          <button class="btn" onclick="freezeEdits()">Freeze Edits</button>
          <button class="btn" onclick="createEscalation()">Create Escalation</button>
        </div>
        <div class="list" id="action-status"></div>
      </div>
    </section>
    """
    page_js = """
      const traceLink = (tid) => {
        if (!tid) return "";
        return `<a class="btn" href="/mission?trace_id=${encodeURIComponent(tid)}">trace</a>`;
      };
      const sb = data.scoreboard || {};
      renderList("scoreboard-repeat", sb.repeat_failures || [], (r) => `
        <div class="row"><span>${r.signature}</span><span class="mono">${r.count}</span>${traceLink(r.trace_id)}</div>
      `);
      renderList("scoreboard-evidence", sb.no_evidence || [], (r) => `
        <div class="row"><span>${r.goal}</span><span class="mono">${r.streak}</span>${traceLink(r.trace_id)}</div>
      `);
      renderList("scoreboard-diff", sb.diff_thrash || [], (r) => `
        <div class="row"><span>${r.file}</span><span class="mono">${r.count}</span>${traceLink(r.trace_id)}</div>
      `);

      const esc = data.escapes || {};
      renderList("escape-list", [
        `<div class="row"><span>triggered</span><span class="mono">${esc.triggered ?? 0}</span></div>`,
        `<div class="row"><span>avg steps to escape</span><span class="mono">${esc.avg_steps_to_escape ?? 0}</span></div>`,
        `<div class="row"><span>recovered</span><span class="mono">${esc.recovered ?? 0}</span></div>`,
        `<div class="row"><span>learning artifacts</span><span class="mono">${esc.artifacts ?? 0}</span></div>`
      ], (x) => x);

      const minimal = data.minimal_mode || {};
      renderList("minimal-list", minimal.history || [], (h) => `
        <div class="row"><span>${h.event}</span><span class="muted">${h.reason || ""}</span><span class="mono">${new Date((h.timestamp || 0) * 1000).toLocaleTimeString()}</span></div>
      `);

      window.triggerEscape = async () => {{
        await postAction('/api/eidos/escape', {{ reason: 'manual' }});
      }};
      window.enterMinimal = async () => {{
        await postAction('/api/eidos/minimal/enter', {{ reason: 'manual_trigger' }});
      }};
      window.freezeEdits = async () => {{
        await postAction('/api/eidos/minimal/enter', {{ reason: 'manual_trigger' }});
      }};
      window.createEscalation = async () => {{
        const reason = prompt("Escalation summary?");
        if (!reason) return;
        await postAction('/api/eidos/escalate', {{ reason }});
      }};
      async function postAction(url, payload) {{
        try {{
          const res = await fetch(url, {{ method: 'POST', headers: {{ 'Content-Type': 'application/json' }}, body: JSON.stringify(payload || {{}}) }});
          const data = await res.json();
          renderList("action-status", [data], (d) => `<div class="row"><span>${d.status}</span><span class="muted">${d.message || ""}</span></div>`);
        }} catch (e) {{
          renderList("action-status", [{{status: 'error', message: e.message}}], (d) => `<div class="row"><span>${d.status}</span><span class="muted">${d.message}</span></div>`);
        }}
      }}
    """
    return _base_page("Rabbit Hole Recovery", "rabbit", body, data, "/api/rabbit", page_js)


def generate_acceptance_html() -> str:
    data = get_acceptance_data()
    body = """
    <section class="grid">
      <div class="card">
        <div class="card-header"><span class="card-title">Acceptance Plans</span></div>
        <div class="list" id="plans-list"></div>
      </div>
      <div class="card">
        <div class="card-header"><span class="card-title">Deferrals</span><span class="pill" id="deferral-count"></span></div>
        <div class="list" id="deferral-list"></div>
      </div>
      <div class="card">
        <div class="card-header"><span class="card-title">Validation Gap Alerts</span></div>
        <div class="list" id="gap-list"></div>
      </div>
    </section>
    <section class="grid">
      <div class="card">
        <div class="card-header"><span class="card-title">Evidence Store</span></div>
        <div class="list" id="evidence-list"></div>
      </div>
    </section>
    """
    page_js = """
      const traceLink = (tid) => {
        if (!tid) return "";
        return `<a class="btn" href="/mission?trace_id=${encodeURIComponent(tid)}">trace</a>`;
      };
      renderList("plans-list", data.plans || [], (p) => `
        <div class="row">
          <span>${p.goal}</span>
          <span class="pill ${p.is_approved ? "ok" : "warn"}">${p.is_approved ? "approved" : "pending"}</span>
          <span class="mono">${p.progress}%</span>
        </div>
      `);
      const def = data.deferrals || {};
      setText("deferral-count", `${def.pending ?? 0} pending / ${def.overdue ?? 0} overdue`);
      renderList("deferral-list", def.items || [], (d) => `
        <div class="row"><span>${d.reason}</span><span class="mono">${Math.round(d.age_s/60)}m</span>${traceLink(d.trace_id)}</div>
      `);
      renderList("gap-list", data.validation_gaps || [], (g) => `
        <div class="row"><span>${g.goal}</span><span class="mono">${g.missing_count} steps</span>${traceLink(g.trace_id)}</div>
      `);
      const ev = data.evidence || {};
      renderList("evidence-list", [
        `<div class="row"><span>total evidence</span><span class="mono">${ev.total_items ?? 0}</span></div>`,
        `<div class="row"><span>expiring 24h</span><span class="mono">${ev.expiring_in_24h ?? 0}</span></div>`,
        `<div class="row"><span>permanent</span><span class="mono">${ev.permanent ?? 0}</span></div>`
      ], (x) => x);
    """
    return _base_page("Acceptance & Validation Board", "acceptance", body, data, "/api/acceptance", page_js)


def generate_dashboards_html() -> str:
    data = get_mission_control_data()
    body = """
    <section class="grid">
      <div class="card">
        <div class="card-header"><span class="card-title">Web Dashboards</span></div>
        <div class="list">
          <div class="row"><span>Spark Lab (Mission/learning/rabbit/acceptance/ops)</span><span class="mono"><a href="http://localhost:{PORT}">:{PORT}</a></span></div>
          <div class="row"><span>Meta-Ralph Quality Analyzer</span><span class="mono"><a href="http://localhost:{META_RALPH_PORT}">:{META_RALPH_PORT}</a></span></div>
          <div class="row"><span>Spark Pulse (chips + tuneables)</span><span class="mono"><a href="http://localhost:{PULSE_PORT}">:{PULSE_PORT}</a></span></div>
        </div>
      </div>
      <div class="card">
        <div class="card-header"><span class="card-title">CLI Dashboards</span></div>
        <div class="list">
          <div class="row"><span>EIDOS quick health</span><span class="mono">python scripts/eidos_dashboard.py</span></div>
          <div class="row"><span>Spark Intelligence CLI</span><span class="mono">python scripts/spark_dashboard.py</span></div>
        </div>
      </div>
      <div class="card">
        <div class="card-header"><span class="card-title">Start/Stop</span></div>
        <div class="list">
          <div class="row"><span>All services</span><span class="mono">spark up</span></div>
          <div class="row"><span>Stop services</span><span class="mono">spark down</span></div>
          <div class="row"><span>Status</span><span class="mono">spark services</span></div>
        </div>
      </div>
    </section>
    <section class="grid">
      <div class="card">
        <div class="card-header"><span class="card-title">Data Sources (No Hallucinations)</span></div>
        <div class="list">
          <div class="row"><span>Spark Lab</span><span class="mono">~/.spark/queue, eidos.db, truth_ledger.json, acceptance_plans.json, evidence.db</span></div>
          <div class="row"><span>Meta-Ralph</span><span class="mono">~/.spark/meta_ralph/*.json, ~/.spark/advisor/*.jsonl</span></div>
          <div class="row"><span>Pulse</span><span class="mono">~/.spark/chip_*, chip_registry.json</span></div>
        </div>
      </div>
    </section>
    """
    return _base_page("Dashboards", "dashboards", body, data, "/api/status", "")


class DashboardHandler(SimpleHTTPRequestHandler):
    def _serve_sse(self, data_fn, interval: float = 2.0) -> None:
        self.send_response(200)
        self.send_header('Content-type', 'text/event-stream')
        self.send_header('Cache-Control', 'no-cache')
        self.send_header('Connection', 'keep-alive')
        self.end_headers()
        try:
            self.wfile.write(b"retry: 2000\n\n")
            self.wfile.flush()
        except Exception:
            return

        try:
            while True:
                payload = data_fn()
                data = json.dumps(payload)
                msg = f"data: {data}\n\n".encode("utf-8")
                self.wfile.write(msg)
                self.wfile.flush()
                time.sleep(interval)
        except (BrokenPipeError, ConnectionResetError):
            return
        except Exception:
            return

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path
        query = parse_qs(parsed.query)

        if path in ('/', '/index.html', '/mission'):
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            self.wfile.write(generate_mission_html().encode())
        elif path in ('/learning', '/learning.html'):
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            self.wfile.write(generate_learning_html().encode())
        elif path in ('/rabbit', '/rabbit.html'):
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            self.wfile.write(generate_rabbit_html().encode())
        elif path in ('/acceptance', '/acceptance.html'):
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            self.wfile.write(generate_acceptance_html().encode())
        elif path == '/ops' or path == '/ops.html':
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            self.wfile.write(generate_ops_html().encode())
        elif path == '/dashboards' or path == '/dashboards.html':
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            self.wfile.write(generate_dashboards_html().encode())
        elif path == '/api/status':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(get_mission_control_data(), indent=2).encode())
        elif path == '/health':
            self.send_response(200)
            self.send_header('Content-type', 'text/plain; charset=utf-8')
            self.end_headers()
            self.wfile.write(b"ok")
        elif path == '/api/mission':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(get_mission_control_data(), indent=2).encode())
        elif path == '/api/learning':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(get_learning_factory_data(), indent=2).encode())
        elif path == '/api/rabbit':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(get_rabbit_recovery_data(), indent=2).encode())
        elif path == '/api/acceptance':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(get_acceptance_data(), indent=2).encode())
        elif path == '/api/ops':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(get_ops_data(), indent=2).encode())
        elif path == '/api/advisory/setup':
            payload = _get_advisory_setup_payload()
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(payload, indent=2).encode())
        elif path == '/api/advisory/preferences':
            payload = {
                "ok": True,
                "preferences": advisory_get_current_preferences(),
            }
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(payload, indent=2).encode())
        elif path == '/api/trace':
            trace_id = ""
            if "trace_id" in query and query["trace_id"]:
                trace_id = query["trace_id"][0]
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(get_trace_timeline_data(trace_id), indent=2).encode())
        elif path == '/api/run':
            episode_id = ""
            if "episode_id" in query and query["episode_id"]:
                episode_id = query["episode_id"][0]
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(get_run_detail(episode_id), indent=2).encode())
        elif path == '/api/status/stream':
            self._serve_sse(get_mission_control_data)
        elif path == '/api/ops/stream':
            self._serve_sse(get_ops_data)
        elif path == '/logo.png':
            if not LOGO_FILE.exists():
                self.send_response(404)
                self.end_headers()
                return
            logo_bytes = LOGO_FILE.read_bytes()
            self.send_response(200)
            self.send_header('Content-type', 'image/png')
            self.send_header('Content-Length', str(len(logo_bytes)))
            self.end_headers()
            self.wfile.write(logo_bytes)
        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self):
        parsed = urlparse(self.path)
        path = parsed.path

        # Safety: only accept POSTs from localhost by default.
        remote = str(self.client_address[0]) if getattr(self, 'client_address', None) else ''
        allow_remote = str(os.environ.get('SPARK_DASHBOARD_ALLOW_REMOTE_POST') or '').strip().lower() in {'1','true','yes','on'}
        if not allow_remote and remote not in {'127.0.0.1', '::1'}:
            self.send_response(403)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({'ok': False, 'error': 'remote POST forbidden'}).encode())
            return

        if path == '/api/taste/add':
            length = int(self.headers.get('Content-Length', '0') or 0)
            raw = self.rfile.read(length) if length else b'{}'
            try:
                payload = json.loads(raw.decode('utf-8') or '{}')
            except Exception:
                payload = {}

            resp = add_from_dashboard(payload)
            body = json.dumps(resp).encode('utf-8')
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Content-Length', str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        if path in ('/api/eidos/escape', '/api/eidos/minimal/enter', '/api/eidos/minimal/exit', '/api/eidos/escalate'):
            length = int(self.headers.get('Content-Length', '0') or 0)
            raw = self.rfile.read(length) if length else b'{}'
            try:
                payload = json.loads(raw.decode('utf-8') or '{}')
            except Exception:
                payload = {}

            status, message = _handle_eidos_action(path, payload)
            body = json.dumps({"status": status, "message": message}).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        if path in ('/api/advisory/setup', '/api/advisory/preferences'):
            length = int(self.headers.get('Content-Length', '0') or 0)
            raw = self.rfile.read(length) if length else b'{}'
            try:
                payload = json.loads(raw.decode('utf-8') or '{}')
            except Exception:
                payload = {}

            try:
                result = _apply_advisory_preferences_payload(payload)
                body = json.dumps(result).encode('utf-8')
                self.send_response(200)
            except Exception as exc:
                body = json.dumps({
                    "ok": False,
                    "error": f"advisory preferences update failed: {exc}",
                }).encode('utf-8')
                self.send_response(500)
            self.send_header('Content-type', 'application/json')
            self.send_header('Content-Length', str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return

        self.send_response(404)
        self.end_headers()
    
    def log_message(self, format, *args):
        pass


def main():
    setup_component_logging("dashboard")
    print()
    print("  vibeship spark")
    print("  -----------------------------")
    print(f"  Dashboard: http://localhost:{PORT}")
    print("  Press Ctrl+C to stop")
    print()
    
    server = ThreadingHTTPServer(("localhost", PORT), DashboardHandler)
    stop_event = threading.Event()

    def _shutdown(signum=None, frame=None):
        if stop_event.is_set():
            return
        stop_event.set()
        print("\n  Shutting down...")
        threading.Thread(target=server.shutdown, daemon=True).start()

    try:
        import signal
        signal.signal(signal.SIGINT, _shutdown)
        signal.signal(signal.SIGTERM, _shutdown)
    except Exception:
        pass
    
    def _parse_bool(v: object) -> bool:
        return str(v or "").strip().lower() in {"1", "true", "yes", "on"}

    def _should_open_browser() -> bool:
        if _parse_bool(os.environ.get("SPARK_SERVICE_MODE")):
            return False
        if _parse_bool(os.environ.get("SPARK_NO_BROWSER")):
            return False
        if _parse_bool(os.environ.get("SPARK_OPEN_BROWSER")):
            return True
        return True

    if _should_open_browser():
        def open_browser():
            time.sleep(1)
            webbrowser.open(f'http://localhost:{PORT}')
        
        threading.Thread(target=open_browser, daemon=True).start()
    
    try:
        server.serve_forever()
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
