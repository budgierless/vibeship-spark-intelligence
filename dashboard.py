#!/usr/bin/env python3
"""
Spark Dashboard - True Vibeship Style

Run with: python3 dashboard.py
Open: http://localhost:8585
"""

import json
import time
from datetime import datetime
from pathlib import Path
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
import threading
import webbrowser
from typing import Dict

import sys
sys.path.insert(0, str(Path(__file__).parent))

from lib.cognitive_learner import CognitiveLearner, CognitiveCategory
from lib.mind_bridge import MindBridge
from lib.markdown_writer import MarkdownWriter
from lib.promoter import Promoter
from lib.queue import get_queue_stats, read_recent_events, count_events
from lib.aha_tracker import AhaTracker
from lib.spark_voice import SparkVoice
from lib.growth_tracker import GrowthTracker
from lib.resonance import get_resonance_display
from lib.dashboard_project import get_active_project, get_project_memory_preview
from lib.taste_api import add_from_dashboard

PORT = 8585
SPARK_DIR = Path.home() / ".spark"
SKILLS_INDEX_FILE = SPARK_DIR / "skills_index.json"
SKILLS_EFFECTIVENESS_FILE = SPARK_DIR / "skills_effectiveness.json"
ORCH_DIR = SPARK_DIR / "orchestration"
ORCH_AGENTS_FILE = ORCH_DIR / "agents.json"
ORCH_HANDOFFS_FILE = ORCH_DIR / "handoffs.jsonl"
LOGO_FILE = Path(__file__).parent / "logo.png"

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
    
    writer = MarkdownWriter()  # Fresh instance
    writer_stats = writer.get_stats()
    
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
    surprises = aha.get_recent_surprises(5)
    surprises_list = []
    for s in surprises:
        surprises_list.append({
            "type": s.surprise_type.replace("_", " ").title(),
            "predicted": s.predicted_outcome[:50],
            "actual": s.actual_outcome[:50],
            "gap": s.confidence_gap,
            "lesson": s.lesson_extracted[:60] if s.lesson_extracted else None
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
        "markdown": {
            "learnings": writer_stats["learnings_count"],
            "errors": writer_stats["errors_count"]
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
        }
    }


def _load_json(path: Path) -> Dict:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _read_jsonl(path: Path, limit: int | None = None) -> list:
    if not path.exists():
        return []
    items = []
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


def get_ops_data() -> Dict:
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
    handoffs_sorted = sorted(handoffs, key=lambda h: h.get("timestamp", 0), reverse=True)
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
    }


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
    
    # Targets
    targets = data["promotions"]["by_target"]
    targets_html = " ".join([f'<span class="target-pill">{t}</span>' for t in targets.keys()]) if targets else '<span class="muted">—</span>'
    
    mind_status = "live" if data["mind"]["available"] else "offline"
    mind_text = "Connected" if data["mind"]["available"] else "Offline"
    
    html = f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <!-- live updates via JS (no full-page refresh) -->
    <title>Spark — Vibeship</title>
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
            flex: 1;
            overflow-y: auto;
            padding-right: 6px;
        }}

        .surprise-list::-webkit-scrollbar {{
            width: 6px;
        }}
        .surprise-list::-webkit-scrollbar-track {{
            background: transparent;
        }}
        .surprise-list::-webkit-scrollbar-thumb {{
            background: rgba(255,255,255,0.14);
            border-radius: 0px;
        }}
        .surprise-list::-webkit-scrollbar-thumb:hover {{
            background: rgba(255,255,255,0.22);
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
            <span class="navbar-product">spark</span>
        </div>
        <div class="navbar-links">
            <a class="nav-link active" href="/">Overview</a>
            <a class="nav-link" href="/ops">Orchestration</a>
        </div>
    </nav>
    
    <main>
        <div class="hero">
            <h1>Self-Evolving <span>Intelligence</span></h1>
            <p class="hero-sub">Learn. Remember. Improve.</p>
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
                </div>
                <div class="card-body">
                    <div class="mini-stats">
                        <div class="mini-stat">
                            <div class="mini-stat-value">{data["markdown"]["learnings"]}</div>
                            <div class="mini-stat-label">Learnings</div>
                        </div>
                        <div class="mini-stat">
                            <div class="mini-stat-value">{data["markdown"]["errors"]}</div>
                            <div class="mini-stat-label">Errors</div>
                        </div>
                        <div class="mini-stat">
                            <div class="mini-stat-value">{data["promotions"]["ready"]}</div>
                            <div class="mini-stat-label">Ready</div>
                        </div>
                    </div>
                    <div style="margin-top: 0.75rem;">{targets_html}</div>
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
                    <span class="muted" style="font-size: 0.7rem;" id="surprises-total">{data["surprises"]["total"]} total</span>
                </div>
                <div class="card-body" id="surprises-body">
                    {('' if surprises_html else '<div class="empty" id="surprises-empty">No surprises yet. They happen when predictions do not match outcomes.</div>')}
                    {('' if not surprises_html else f'<div class="surprise-list" id="surprises-list">{surprises_html}</div>')}
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
        <p class="footer-text">Updated <span id="updated-at">{data["timestamp"]}</span> · Live · Project: <span id="active-project">{data.get("project", {}).get("active") or "—"}</span> · <span>vibeship</span> ecosystem</p>
    </div>

    <script>
      // Live updates (no full page refresh)
      const $ = (id) => document.getElementById(id);

      function esc(s) {{
        // NOTE: braces are doubled because this HTML is generated from a Python f-string.
        return String(s ?? '').replace(/[&<>"']/g, (c) => ({{'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;','\'':'&#39;'}}[c]));
      }}

      function renderSurprises(recent) {{
        if (!Array.isArray(recent) || recent.length === 0) return '';
        return recent.map((s) => {{
          const type = esc(s.type);
          const gap = Math.round((s.gap || 0) * 100);
          const predicted = esc(s.predicted || '');
          const actual = esc(s.actual || '');
          const lesson = s.lesson ? `<div class="surprise-lesson">→ ${{esc(s.lesson)}}</div>` : '';
          const icon = type.includes('Success') ? '△' : type.includes('Failure') ? '▽' : '◇';
          const iconClass = type.includes('Success') ? 'success' : type.includes('Failure') ? 'failure' : '';
          return `
            <div class="surprise-row">
              <div class="surprise-header">
                <span class="surprise-icon ${{iconClass}}">${{icon}}</span>
                <span class="surprise-type">${{type}}</span>
                <span class="surprise-gap">${{gap}}% gap</span>
              </div>
              <div class="surprise-detail"><span class="surprise-label">Expected</span><span class="surprise-text">${{predicted}}…</span></div>
              <div class="surprise-detail"><span class="surprise-label">Got</span><span class="surprise-text">${{actual}}…</span></div>
              ${{lesson}}
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
        if ($('surprises-total')) $('surprises-total').textContent = `${{data.surprises?.total ?? 0}} total`;

        const recent = data.surprises?.recent || [];
        const list = $('surprises-list');
        const empty = $('surprises-empty');

        if (recent.length === 0) {{
          if (list) list.remove();
          if (empty) empty.style.display = '';
        }} else {{
          if (empty) empty.style.display = 'none';
          if (!list) {{
            // create list container if it doesn't exist yet
            const wrap = document.createElement('div');
            wrap.id = 'surprises-list';
            wrap.className = 'surprise-list';
            const body = $('surprises-body') || document.querySelector('.card-body');
            body.appendChild(wrap);
          }}
          const l = $('surprises-list');
          if (l) {{
            l.innerHTML = renderSurprises(recent);
          }}
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
            <span class="navbar-product">spark</span>
        </div>
        <div class="navbar-links">
            <a class="nav-link" href="/">Overview</a>
            <a class="nav-link active" href="/ops">Orchestration</a>
        </div>
    </nav>

    <main>
        <div class="hero">
            <h1>Orchestration <span>& Skills</span></h1>
            <p class="hero-sub">Utility-first signals for team coordination and skill health.</p>
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
        if self.path == '/' or self.path == '/index.html':
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            self.wfile.write(generate_html().encode())
        elif self.path == '/ops' or self.path == '/ops.html':
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            self.wfile.write(generate_ops_html().encode())
        elif self.path == '/api/status':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(get_dashboard_data(), indent=2).encode())
        elif self.path == '/api/ops':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(get_ops_data(), indent=2).encode())
        elif self.path == '/api/status/stream':
            self._serve_sse(get_dashboard_data)
        elif self.path == '/api/ops/stream':
            self._serve_sse(get_ops_data)
        elif self.path == '/logo.png':
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
        if self.path == '/api/taste/add':
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

        self.send_response(404)
        self.end_headers()
    
    def log_message(self, format, *args):
        pass


def main():
    print()
    print("  vibeship spark")
    print("  ─────────────────────────────")
    print(f"  Dashboard: http://localhost:{PORT}")
    print("  Press Ctrl+C to stop")
    print()
    
    server = ThreadingHTTPServer(('localhost', PORT), DashboardHandler)
    
    def open_browser():
        time.sleep(1)
        webbrowser.open(f'http://localhost:{PORT}')
    
    threading.Thread(target=open_browser, daemon=True).start()
    
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n  Shutting down...")
        server.shutdown()


if __name__ == "__main__":
    main()
