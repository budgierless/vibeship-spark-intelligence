#!/usr/bin/env python3
"""
Tracer Dashboard - Vibeship Style
=================================

Standalone decision trace observability dashboard.
Real-time visibility into Spark's intelligence loops.

Run: python tracer_dashboard.py
Open: http://localhost:8777

Vibeship Design:
- Deep navy background (#0e1016)
- Green (#00C49A) primary accent
- Orange (#D97757) for emphasis/punchlines
- Gold (#c8a84e) for premium insights
- No rounded corners
- JetBrains Mono + Instrument Serif typography
"""

import json
import time
import asyncio
import threading
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
import webbrowser

# Add project root to path
import sys
sys.path.insert(0, str(Path(__file__).parent))

from trace_hud import TraceCollector, TraceState, TraceStore
from lib.diagnostics import setup_component_logging

PORT = 8777
SPARK_DIR = Path.home() / ".spark"
TRACER_STORE_DIR = SPARK_DIR / "tracer"
AUTO_SCORER_LATEST = TRACER_STORE_DIR / "advisory_auto_score_latest.json"
_AUTO_SCORER_LOCK = threading.Lock()

# Global state
_tracer_state: Optional[TraceState] = None
_tracer_collector: Optional[TraceCollector] = None
_tracer_store: Optional[TraceStore] = None
_poll_thread: Optional[threading.Thread] = None
_running = False


def get_tracer_components():
    """Get or initialize tracer components."""
    global _tracer_state, _tracer_collector, _tracer_store
    
    if _tracer_collector is None:
        _tracer_collector = TraceCollector(spark_dir=SPARK_DIR)
    if _tracer_state is None:
        _tracer_state = TraceState()
    if _tracer_store is None:
        _tracer_store = TraceStore(store_dir=TRACER_STORE_DIR)
    
    return _tracer_collector, _tracer_state, _tracer_store


def poll_once():
    """Single poll cycle."""
    collector, state, store = get_tracer_components()
    
    try:
        events = collector.poll_all_sources()
        if events:
            state.ingest_events(events)
            store.append_many(events)
        state.cleanup_stale(timeout_seconds=300)
    except Exception as e:
        print(f"[Tracer] Poll error: {e}")


def poll_loop():
    """Background polling loop."""
    global _running
    while _running:
        poll_once()
        time.sleep(1.0)


def start_polling():
    """Start background polling."""
    global _poll_thread, _running
    if _poll_thread is None or not _poll_thread.is_alive():
        _running = True
        _poll_thread = threading.Thread(target=poll_loop, daemon=True)
        _poll_thread.start()


def stop_polling():
    """Stop background polling."""
    global _running
    _running = False


def get_tracer_data() -> Dict[str, Any]:
    """Get current tracer data for dashboard."""
    _, state, store = get_tracer_components()
    
    kpis = state.get_kpis()
    stats = state.get_detailed_stats()
    active_traces = state.get_active_traces()
    blocked_traces = state.get_blocked_traces()
    recent_completed = state.get_recent_completed(10)
    
    # Filter out advisory/telemetry noise (same as terminal)
    SKIP_CATEGORIES = {'research_decision', 'build_delivery', 'unknown', 'advisory'}
    SKIP_INTENT_PREFIXES = [
        'research_decision_support', 'emergent_other', 'knowledge_alignment',
        'team_coordination', 'deployment_ops', 'orchestration_execution',
    ]
    SKIP_TRACE_PREFIXES = ['advisory-', 'bridge_', 'bridge-', 'pattern_']
    SKIP_GENERIC_INTENTS = ['learning: learning', 'run exec command', 'execute process']
    SKIP_FILE_PATTERNS = ['SPARK_', 'spark_reports/', '.openclaw/workspace/SPARK_']
    
    def is_real_work(trace) -> bool:
        """Check if trace represents real work, not advisory noise."""
        # Skip advisory categories
        if trace.intent_category in SKIP_CATEGORIES:
            return False
        
        intent_lower = (trace.intent or "").lower()
        intent = trace.intent or ""
        
        # Skip advisory intent prefixes
        if any(intent_lower.startswith(prefix) for prefix in SKIP_INTENT_PREFIXES):
            return False
        
        # Skip generic/low-value intents
        if any(intent_lower == gi for gi in SKIP_GENERIC_INTENTS):
            return False
        
        # Skip very short intents (like "Yes", "Ok", "Hi")
        if len(intent.strip()) < 10:
            return False
        
        # Skip meta trace IDs
        if any(trace.trace_id.startswith(prefix) for prefix in SKIP_TRACE_PREFIXES):
            return False
        
        # Skip reads of internal Spark files
        if trace.intent_category == 'read' and intent:
            for pattern in SKIP_FILE_PATTERNS:
                if pattern in intent:
                    return False
        
        return True
    
    # Filter traces
    active_traces = [t for t in active_traces if is_real_work(t)]
    blocked_traces = [t for t in blocked_traces if is_real_work(t)]
    recent_completed = [t for t in recent_completed if is_real_work(t)]
    
    # Format active traces
    active_list = []
    for t in active_traces[:20]:
        active_list.append({
            "trace_id": t.trace_id[:16],
            "phase": t.phase.value,
            "status": t.status.value,
            "intent": t.intent[:80],
            "action": t.action[:60] if t.action else None,
            "outcome": t.outcome[:60] if t.outcome else None,
            "lesson": t.lesson[:80] if t.lesson else None,
            "lesson_confidence": round(t.lesson_confidence, 2),
            "blockers": len(t.blockers),
            "duration_ms": t.metrics.duration_ms,
            "files": t.file_paths[:5],
            "category": t.intent_category,
            "advisory_actioned": t.advisory_actioned,
        })
    
    # Format blocked traces
    blocked_list = []
    for t in blocked_traces[:10]:
        blocked_list.append({
            "trace_id": t.trace_id[:16],
            "intent": t.intent[:60],
            "blockers": t.blockers[-3:] if t.blockers else [],
            "duration_blocked_ms": int((time.time() - t.last_activity) * 1000),
        })
    
    # Format recent completed
    completed_list = []
    for t in recent_completed:
        completed_list.append({
            "trace_id": t.trace_id[:16],
            "intent": t.intent[:60],
            "status": t.status.value,
            "lesson": t.lesson[:80] if t.lesson else None,
            "duration_ms": t.metrics.duration_ms,
            "ended_ago_ms": int((time.time() - t.last_activity) * 1000),
        })
    
    # Phase distribution for chart
    phase_dist = kpis.get('phase_distribution', {})
    phase_chart = [
        {"phase": phase, "count": count}
        for phase, count in sorted(phase_dist.items(), key=lambda x: -x[1])
    ]
    
    return {
        "timestamp": datetime.now().isoformat(),
        "kpis": {
            "active_tasks": kpis.get('active_tasks', 0),
            "recent_active": kpis.get('recent_active', 0),
            "blocked_tasks": kpis.get('blocked_tasks', 0),
            "success_rate": kpis.get('success_rate_100', 0),
            "advisory_rate": kpis.get('advisory_action_rate_100', 0),
            "lessons_learned": kpis.get('lessons_learned', 0),
            "total_actions": kpis.get('total_actions', 0),
        },
        "stats": {
            "active_traces": stats.get('active_traces', 0),
            "historical_traces": stats.get('historical_traces', 0),
            "avg_duration_ms": stats.get('avg_duration_ms', 0),
            "total_blockers": stats.get('total_blockers', 0),
        },
        "active": active_list,
        "blocked": blocked_list,
        "completed": completed_list,
        "phase_chart": phase_chart,
        "store_stats": store.get_stats(),
    }


def generate_html() -> str:
    """Generate the vibeship-styled dashboard HTML."""
    return '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Tracer | Spark Intelligence</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Instrument+Serif:ital@0;1&family=JetBrains+Mono:wght@400;500;600;700&display=swap" rel="stylesheet">
    <style>
        :root {
            --bg-deep: #0e1016;
            --bg-card: #1a1e28;
            --border: #2a3042;
            --green: #00C49A;
            --green-glow: rgba(0, 196, 154, 0.3);
            --orange: #D97757;
            --orange-glow: rgba(217, 119, 87, 0.3);
            --gold: #c8a84e;
            --text-primary: #ffffff;
            --text-secondary: #9ca3af;
            --text-tertiary: #6b7280;
            --success: #00C49A;
            --warning: #D97757;
            --error: #ef4444;
        }
        
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: 'JetBrains Mono', monospace;
            background: var(--bg-deep);
            color: var(--text-primary);
            min-height: 100vh;
            line-height: 1.5;
        }
        
        /* Background atmosphere */
        .bg-atmosphere {
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            pointer-events: none;
            background: 
                radial-gradient(ellipse at 50% 50%, rgba(0, 196, 154, 0.03) 0%, transparent 70%),
                radial-gradient(ellipse at 80% 20%, rgba(200, 168, 78, 0.02) 0%, transparent 50%);
            z-index: 0;
        }
        
        .particles {
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            pointer-events: none;
            z-index: 1;
            overflow: hidden;
        }
        
        .particle {
            position: absolute;
            width: 2px;
            height: 2px;
            background: var(--gold);
            border-radius: 50%;
            opacity: 0.1;
            animation: float 20s infinite ease-in-out;
        }
        
        @keyframes float {
            0%, 100% { transform: translateY(100vh) rotate(0deg); opacity: 0; }
            10% { opacity: 0.1; }
            90% { opacity: 0.1; }
            100% { transform: translateY(-100px) rotate(360deg); opacity: 0; }
        }
        
        /* Layout */
        .container {
            position: relative;
            z-index: 10;
            max-width: 1920px;
            margin: 0 auto;
            padding: 40px 60px;
        }
        
        /* Header */
        .header {
            display: flex;
            justify-content: space-between;
            align-items: flex-start;
            margin-bottom: 48px;
            padding-bottom: 24px;
            border-bottom: 1px solid var(--border);
        }

        .header-left {
            display: flex;
            flex-direction: column;
            gap: 14px;
        }

        .nav {
            display: flex;
            gap: 10px;
            flex-wrap: wrap;
        }

        .nav a {
            display: inline-flex;
            align-items: center;
            font-size: 11px;
            text-transform: uppercase;
            letter-spacing: 2px;
            color: var(--text-secondary);
            text-decoration: none;
            border: 1px solid var(--border);
            padding: 8px 12px;
            background: var(--bg-deep);
        }

        .nav a.active {
            color: var(--text-primary);
            border-color: rgba(0, 196, 154, 0.8);
            box-shadow: 0 0 0 1px rgba(0, 196, 154, 0.25);
        }
        
        .brand {
            display: flex;
            align-items: center;
            gap: 16px;
        }
        
        .logo {
            width: 48px;
            height: 48px;
            background: var(--green);
            display: flex;
            align-items: center;
            justify-content: center;
            font-weight: 700;
            font-size: 24px;
            color: var(--bg-deep);
        }
        
        .brand-text h1 {
            font-family: 'Instrument Serif', serif;
            font-size: 42px;
            font-weight: 400;
            letter-spacing: -0.5px;
        }
        
        .brand-text p {
            color: var(--text-tertiary);
            font-size: 14px;
            margin-top: 4px;
            letter-spacing: 2px;
            text-transform: uppercase;
        }
        
        .live-indicator {
            display: flex;
            align-items: center;
            gap: 8px;
            font-size: 12px;
            text-transform: uppercase;
            letter-spacing: 3px;
            color: var(--green);
        }
        
        .live-dot {
            width: 8px;
            height: 8px;
            background: var(--green);
            border-radius: 50%;
            box-shadow: 0 0 10px var(--green);
            animation: pulse 2s infinite;
        }
        
        @keyframes pulse {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.5; }
        }
        
        /* KPI Grid */
        .kpi-grid {
            display: grid;
            grid-template-columns: repeat(6, 1fr);
            gap: 20px;
            margin-bottom: 48px;
        }
        
        .kpi-card {
            background: var(--bg-card);
            border: 1px solid var(--border);
            padding: 24px;
            position: relative;
            overflow: hidden;
        }
        
        .kpi-card::before {
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            height: 3px;
            background: var(--green);
        }
        
        .kpi-card.warning::before {
            background: var(--orange);
        }
        
        .kpi-card.error::before {
            background: var(--error);
        }
        
        .kpi-label {
            font-size: 11px;
            text-transform: uppercase;
            letter-spacing: 2px;
            color: var(--text-tertiary);
            margin-bottom: 8px;
        }
        
        .kpi-value {
            font-size: 36px;
            font-weight: 700;
            color: var(--green);
            line-height: 1;
        }
        
        .kpi-card.warning .kpi-value {
            color: var(--orange);
        }
        
        .kpi-card.error .kpi-value {
            color: var(--error);
        }
        
        .kpi-sub {
            font-size: 12px;
            color: var(--text-secondary);
            margin-top: 8px;
        }
        
        /* Main Content Grid */
        .main-grid {
            display: grid;
            grid-template-columns: 2fr 1fr;
            gap: 24px;
        }
        
        /* Cards */
        .card {
            background: var(--bg-card);
            border: 1px solid var(--border);
            margin-bottom: 24px;
        }
        
        .card-header {
            padding: 20px 24px;
            border-bottom: 1px solid var(--border);
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        
        .card-title {
            display: flex;
            align-items: center;
            gap: 12px;
            font-size: 13px;
            text-transform: uppercase;
            letter-spacing: 2px;
            font-weight: 600;
        }
        
        .card-title::before {
            content: '';
            width: 8px;
            height: 8px;
            background: var(--green);
            border-radius: 50%;
        }
        
        .card-title.orange::before {
            background: var(--orange);
        }
        
        .card-title.red::before {
            background: var(--error);
        }
        
        .card-count {
            font-size: 12px;
            color: var(--text-tertiary);
            background: var(--bg-deep);
            padding: 4px 12px;
            border: 1px solid var(--border);
        }
        
        .card-body {
            padding: 0;
            max-height: 600px;
            overflow-y: auto;
        }
        
        /* Trace Items */
        .trace-list {
            list-style: none;
        }
        
        .trace-item {
            padding: 16px 24px;
            border-bottom: 1px solid var(--border);
            transition: background 0.2s;
        }
        
        .trace-item:hover {
            background: rgba(0, 196, 154, 0.03);
        }
        
        .trace-item:last-child {
            border-bottom: none;
        }
        
        .trace-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 8px;
        }
        
        .trace-id {
            font-size: 11px;
            color: var(--text-tertiary);
            font-family: 'JetBrains Mono', monospace;
        }
        
        .trace-phase {
            font-size: 10px;
            text-transform: uppercase;
            letter-spacing: 1px;
            padding: 2px 8px;
            background: var(--bg-deep);
            border: 1px solid var(--border);
            color: var(--green);
        }
        
        .trace-phase.action { color: var(--green); border-color: var(--green); }
        .trace-phase.executing { color: var(--gold); border-color: var(--gold); }
        .trace-phase.outcome { color: var(--orange); border-color: var(--orange); }
        .trace-phase.lesson { color: var(--success); border-color: var(--success); }
        .trace-phase.blocked { color: var(--error); border-color: var(--error); }
        
        .trace-intent {
            font-size: 14px;
            color: var(--text-primary);
            margin-bottom: 8px;
            line-height: 1.4;
        }
        
        .trace-meta {
            display: flex;
            gap: 16px;
            font-size: 11px;
            color: var(--text-tertiary);
        }
        
        .trace-action {
            color: var(--text-secondary);
        }
        
        .trace-lesson {
            margin-top: 8px;
            padding: 8px 12px;
            background: rgba(0, 196, 154, 0.08);
            border-left: 3px solid var(--green);
            font-size: 12px;
            color: var(--green);
        }
        
        .trace-blocker {
            margin-top: 8px;
            padding: 8px 12px;
            background: rgba(239, 68, 68, 0.08);
            border-left: 3px solid var(--error);
            font-size: 12px;
            color: var(--error);
        }
        
        /* Blocked Section */
        .blocked-section {
            background: rgba(239, 68, 68, 0.05);
            border-color: var(--error);
        }
        
        .blocked-section .card-title::before {
            background: var(--error);
        }
        
        /* Phase Chart */
        .phase-chart {
            padding: 24px;
        }
        
        .phase-bar {
            display: flex;
            align-items: center;
            margin-bottom: 12px;
        }
        
        .phase-label {
            width: 100px;
            font-size: 11px;
            text-transform: uppercase;
            letter-spacing: 1px;
            color: var(--text-tertiary);
        }
        
        .phase-track {
            flex: 1;
            height: 8px;
            background: var(--bg-deep);
            margin: 0 12px;
            position: relative;
        }
        
        .phase-fill {
            height: 100%;
            background: var(--green);
            transition: width 0.5s ease;
        }
        
        .phase-count {
            width: 40px;
            text-align: right;
            font-size: 12px;
            font-weight: 600;
            color: var(--text-secondary);
        }
        
        /* Empty State */
        .empty-state {
            padding: 48px;
            text-align: center;
            color: var(--text-tertiary);
        }
        
        .empty-state-icon {
            font-size: 48px;
            margin-bottom: 16px;
            opacity: 0.3;
        }
        
        /* Scrollbar */
        ::-webkit-scrollbar {
            width: 6px;
        }
        
        ::-webkit-scrollbar-track {
            background: var(--bg-deep);
        }
        
        ::-webkit-scrollbar-thumb {
            background: var(--border);
        }
        
        ::-webkit-scrollbar-thumb:hover {
            background: var(--green);
        }
        
        /* Status badges */
        .badge {
            display: inline-block;
            padding: 2px 8px;
            font-size: 10px;
            text-transform: uppercase;
            letter-spacing: 1px;
            border: 1px solid var(--border);
        }
        
        .badge.success {
            border-color: var(--success);
            color: var(--success);
        }
        
        .badge.fail {
            border-color: var(--error);
            color: var(--error);
        }
        
        .badge.pending {
            border-color: var(--gold);
            color: var(--gold);
        }
        
        /* Footer */
        .footer {
            margin-top: 48px;
            padding-top: 24px;
            border-top: 1px solid var(--border);
            display: flex;
            justify-content: space-between;
            align-items: center;
            font-size: 12px;
            color: var(--text-tertiary);
        }
        
        .footer-brand {
            display: flex;
            align-items: center;
            gap: 8px;
        }
        
        .footer-dot {
            width: 6px;
            height: 6px;
            background: var(--green);
            border-radius: 50%;
            box-shadow: 0 0 8px var(--green);
        }
        
        /* Responsive */
        @media (max-width: 1200px) {
            .kpi-grid {
                grid-template-columns: repeat(3, 1fr);
            }
            .main-grid {
                grid-template-columns: 1fr;
            }
        }
        
        @media (max-width: 768px) {
            .container {
                padding: 20px;
            }
            .kpi-grid {
                grid-template-columns: repeat(2, 1fr);
            }
            .brand-text h1 {
                font-size: 28px;
            }
        }
    </style>
</head>
<body>
    <div class="bg-atmosphere"></div>
    <div class="particles" id="particles"></div>
    
    <div class="container">
        <header class="header">
            <div class="header-left">
                <div class="brand">
                    <div class="logo">T</div>
                    <div class="brand-text">
                        <h1>Tracer</h1>
                        <p>Decision Trace Observability</p>
                    </div>
                </div>
                <nav class="nav" aria-label="Dashboard pages">
                    <a class="active" href="/">Tracer</a>
                    <a href="/scorer">Scorer</a>
                </nav>
            </div>
            <div class="live-indicator">
                <div class="live-dot"></div>
                <span>Live</span>
            </div>
        </header>
        
        <div class="kpi-grid" id="kpi-grid">
            <div class="kpi-card">
                <div class="kpi-label">Active Tasks</div>
                <div class="kpi-value" id="kpi-active">—</div>
                <div class="kpi-sub" id="kpi-active-sub">recent: —</div>
            </div>
            <div class="kpi-card">
                <div class="kpi-label">Success Rate</div>
                <div class="kpi-value" id="kpi-success">—%</div>
                <div class="kpi-sub">last 100 actions</div>
            </div>
            <div class="kpi-card" id="kpi-blocked-card">
                <div class="kpi-label">Blocked</div>
                <div class="kpi-value" id="kpi-blocked">—</div>
                <div class="kpi-sub">unresolved blockers</div>
            </div>
            <div class="kpi-card">
                <div class="kpi-label">Advice Acted</div>
                <div class="kpi-value" id="kpi-advice">—%</div>
                <div class="kpi-sub">advisory effectiveness</div>
            </div>
            <div class="kpi-card">
                <div class="kpi-label">Lessons Learned</div>
                <div class="kpi-value" id="kpi-lessons">—</div>
                <div class="kpi-sub">total distillations</div>
            </div>
            <div class="kpi-card">
                <div class="kpi-label">Avg Duration</div>
                <div class="kpi-value" id="kpi-duration">—</div>
                <div class="kpi-sub" id="kpi-duration-sub">per trace</div>
            </div>
        </div>
        
        <div class="main-grid">
            <div class="main-col">
                <div class="card">
                    <div class="card-header">
                        <div class="card-title">Active Traces</div>
                        <div class="card-count" id="active-count">0</div>
                    </div>
                    <div class="card-body">
                        <ul class="trace-list" id="active-traces">
                            <li class="empty-state">
                                <div class="empty-state-icon">◌</div>
                                <p>No active traces</p>
                            </li>
                        </ul>
                    </div>
                </div>
                
                <div class="card blocked-section" id="blocked-card" style="display: none;">
                    <div class="card-header">
                        <div class="card-title red">Blocked Traces</div>
                        <div class="card-count" id="blocked-count">0</div>
                    </div>
                    <div class="card-body">
                        <ul class="trace-list" id="blocked-traces"></ul>
                    </div>
                </div>
            </div>
            
            <div class="side-col">
                <div class="card">
                    <div class="card-header">
                        <div class="card-title orange">Phase Distribution</div>
                    </div>
                    <div class="card-body">
                        <div class="phase-chart" id="phase-chart">
                            <div class="empty-state">
                                <p>No data</p>
                            </div>
                        </div>
                    </div>
                </div>
                
                <div class="card">
                    <div class="card-header">
                        <div class="card-title">Recent Completed</div>
                        <div class="card-count" id="completed-count">0</div>
                    </div>
                    <div class="card-body">
                        <ul class="trace-list" id="completed-traces">
                            <li class="empty-state">
                                <p>No completed traces</p>
                            </li>
                        </ul>
                    </div>
                </div>
            </div>
        </div>
        
        <footer class="footer">
            <div class="footer-brand">
                <div class="footer-dot"></div>
                <span>@Spark_coded</span>
            </div>
            <div id="last-update">Updated: —</div>
        </footer>
    </div>
    
    <script>
        // Create floating particles
        function createParticles() {
            const container = document.getElementById('particles');
            for (let i = 0; i < 20; i++) {
                const p = document.createElement('div');
                p.className = 'particle';
                p.style.left = Math.random() * 100 + '%';
                p.style.animationDelay = Math.random() * 20 + 's';
                p.style.animationDuration = (15 + Math.random() * 10) + 's';
                container.appendChild(p);
            }
        }
        createParticles();
        
        // Format duration
        function formatDuration(ms) {
            if (!ms) return '—';
            if (ms < 1000) return ms + 'ms';
            return (ms / 1000).toFixed(1) + 's';
        }
        
        // Format time ago
        function timeAgo(ms) {
            if (ms < 60000) return Math.floor(ms / 1000) + 's ago';
            if (ms < 3600000) return Math.floor(ms / 60000) + 'm ago';
            return Math.floor(ms / 3600000) + 'h ago';
        }
        
        // Render active trace
        function renderActiveTrace(trace) {
            const lessonHtml = trace.lesson 
                ? `<div class="trace-lesson">${escapeHtml(trace.lesson)}</div>` 
                : '';
            
            const actionHtml = trace.action 
                ? `<span class="trace-action">→ ${escapeHtml(trace.action)}</span>` 
                : '';
            
            const blockerHtml = trace.blockers > 0
                ? `<span style="color: var(--error)">⚠ ${trace.blockers} blocker${trace.blockers > 1 ? 's' : ''}</span>`
                : '';
            
            return `
                <li class="trace-item">
                    <div class="trace-header">
                        <span class="trace-id">${trace.trace_id}</span>
                        <span class="trace-phase ${trace.phase}">${trace.phase}</span>
                    </div>
                    <div class="trace-intent">${escapeHtml(trace.intent)}</div>
                    <div class="trace-meta">
                        ${actionHtml}
                        ${blockerHtml}
                        <span>${formatDuration(trace.duration_ms)}</span>
                        ${trace.files && trace.files.length ? `<span>${trace.files.length} files</span>` : ''}
                    </div>
                    ${lessonHtml}
                </li>
            `;
        }
        
        // Render blocked trace
        function renderBlockedTrace(trace) {
            const blockersHtml = trace.blockers.map(b => 
                `<div class="trace-blocker">${escapeHtml(b)}</div>`
            ).join('');
            
            return `
                <li class="trace-item">
                    <div class="trace-header">
                        <span class="trace-id">${trace.trace_id}</span>
                        <span class="badge fail">Blocked</span>
                    </div>
                    <div class="trace-intent">${escapeHtml(trace.intent)}</div>
                    <div class="trace-meta">
                        <span>Blocked for ${formatDuration(trace.duration_blocked_ms)}</span>
                    </div>
                    ${blockersHtml}
                </li>
            `;
        }
        
        // Render completed trace
        function renderCompletedTrace(trace) {
            const lessonHtml = trace.lesson 
                ? `<div class="trace-lesson">${escapeHtml(trace.lesson)}</div>` 
                : '';
            
            const statusClass = trace.status === 'success' ? 'success' : 'fail';
            const statusText = trace.status === 'success' ? '✓ Success' : '✗ Fail';
            
            return `
                <li class="trace-item">
                    <div class="trace-header">
                        <span class="trace-id">${trace.trace_id}</span>
                        <span class="badge ${statusClass}">${statusText}</span>
                    </div>
                    <div class="trace-intent">${escapeHtml(trace.intent)}</div>
                    <div class="trace-meta">
                        <span>${formatDuration(trace.duration_ms)}</span>
                        <span>${timeAgo(trace.ended_ago_ms)}</span>
                    </div>
                    ${lessonHtml}
                </li>
            `;
        }
        
        // Render phase chart
        function renderPhaseChart(phases) {
            if (!phases || phases.length === 0) {
                return '<div class="empty-state"><p>No data</p></div>';
            }
            
            const maxCount = Math.max(...phases.map(p => p.count));
            
            return phases.map(phase => {
                const pct = maxCount > 0 ? (phase.count / maxCount * 100) : 0;
                return `
                    <div class="phase-bar">
                        <div class="phase-label">${phase.phase}</div>
                        <div class="phase-track">
                            <div class="phase-fill" style="width: ${pct}%"></div>
                        </div>
                        <div class="phase-count">${phase.count}</div>
                    </div>
                `;
            }).join('');
        }
        
        // Escape HTML
        function escapeHtml(text) {
            if (!text) return '';
            const div = document.createElement('div');
            div.textContent = text;
            return div.innerHTML;
        }
        
        // Update dashboard
        async function updateDashboard() {
            try {
                const response = await fetch('/api/data');
                const data = await response.json();
                
                // Update KPIs
                document.getElementById('kpi-active').textContent = data.kpis.active_tasks;
                document.getElementById('kpi-active-sub').textContent = `recent: ${data.kpis.recent_active}`;
                document.getElementById('kpi-success').textContent = data.kpis.success_rate + '%';
                document.getElementById('kpi-blocked').textContent = data.kpis.blocked_tasks;
                document.getElementById('kpi-advice').textContent = data.kpis.advisory_rate + '%';
                document.getElementById('kpi-lessons').textContent = data.kpis.lessons_learned;
                document.getElementById('kpi-duration').textContent = formatDuration(data.stats.avg_duration_ms);
                
                // Update blocked card styling
                const blockedCard = document.getElementById('kpi-blocked-card');
                if (data.kpis.blocked_tasks > 0) {
                    blockedCard.classList.add('error');
                } else {
                    blockedCard.classList.remove('error');
                }
                
                // Update active traces
                const activeList = document.getElementById('active-traces');
                document.getElementById('active-count').textContent = data.active.length;
                if (data.active.length > 0) {
                    activeList.innerHTML = data.active.map(renderActiveTrace).join('');
                } else {
                    activeList.innerHTML = `
                        <li class="empty-state">
                            <div class="empty-state-icon">◌</div>
                            <p>No active traces</p>
                        </li>
                    `;
                }
                
                // Update blocked traces
                const blockedSection = document.getElementById('blocked-card');
                const blockedList = document.getElementById('blocked-traces');
                document.getElementById('blocked-count').textContent = data.blocked.length;
                if (data.blocked.length > 0) {
                    blockedSection.style.display = 'block';
                    blockedList.innerHTML = data.blocked.map(renderBlockedTrace).join('');
                } else {
                    blockedSection.style.display = 'none';
                }
                
                // Update completed traces
                const completedList = document.getElementById('completed-traces');
                document.getElementById('completed-count').textContent = data.completed.length;
                if (data.completed.length > 0) {
                    completedList.innerHTML = data.completed.map(renderCompletedTrace).join('');
                } else {
                    completedList.innerHTML = `
                        <li class="empty-state">
                            <p>No completed traces</p>
                        </li>
                    `;
                }
                
                // Update phase chart
                document.getElementById('phase-chart').innerHTML = renderPhaseChart(data.phase_chart);
                
                // Update footer
                document.getElementById('last-update').textContent = 'Updated: ' + new Date().toLocaleTimeString();
                
            } catch (err) {
                console.error('Failed to update:', err);
            }
        }
        
        // Initial update and polling
        updateDashboard();
        setInterval(updateDashboard, 1000);
    </script>
</body>
</html>'''


class TracerHandler(SimpleHTTPRequestHandler):
    """HTTP handler for tracer dashboard."""
    
    def log_message(self, format, *args):
        # Suppress default logging
        pass
    
    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path
        
        if path == '/' or path == '/index.html':
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            self.wfile.write(generate_html().encode('utf-8'))
        
        elif path == '/api/data':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Cache-Control', 'no-cache')
            self.end_headers()
            data = get_tracer_data()
            self.wfile.write(json.dumps(data).encode('utf-8'))
        
        else:
            self.send_response(404)
            self.end_headers()


def open_browser(port: int):
    """Open browser after short delay."""
    def _open():
        time.sleep(1.5)
        webbrowser.open(f'http://localhost:{port}')
    threading.Thread(target=_open, daemon=True).start()


def main():
    """Run the tracer dashboard."""
    setup_component_logging("tracer_dashboard")
    
    # Start polling
    start_polling()
    
    # Create server
    server = ThreadingHTTPServer(('0.0.0.0', PORT), TracerHandler)
    
    print(f"""
╔══════════════════════════════════════════════════════════════╗
║                    TRACER DASHBOARD                          ║
║                  Vibeship Style / Port {PORT}                    ║
╠══════════════════════════════════════════════════════════════╣
║  Open: http://localhost:{PORT}                                ║
║                                                              ║
║  Features:                                                   ║
║  • Real-time decision trace observability                    ║
║  • Intent → Action → Evidence → Outcome → Lesson flow        ║
║  • KPIs: Active, Success Rate, Blocked, Advice %             ║
║  • Phase distribution visualization                          ║
║  • Blocker detection & alerts                                ║
╚══════════════════════════════════════════════════════════════╝
""")
    
    # Open browser
    open_browser(PORT)
    
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n[Tracer] Shutting down...")
        stop_polling()
        server.shutdown()


if __name__ == "__main__":
    main()
