#!/usr/bin/env python3
"""
Meta Ralph Quality Analyzer Dashboard
=====================================

A dedicated dashboard for understanding and improving Spark's advice quality.
Ralph Wiggum style: "Me fail English? That's unpossible!"

Features:
- Real-time advice quality metrics from storage (Rule 1: Data from Storage)
- Verdict distribution (QUALITY vs PRIMITIVE vs NEEDS_WORK)
- Score dimension breakdown (actionability, novelty, reasoning, specificity, outcome_linked)
- Outcome tracking (did following advice actually help?)
- Source effectiveness (which sources produce best advice?)
- Recent roasts browser

Run with: python meta_ralph_dashboard.py
Open: http://localhost:8586
"""

import json
import time
from datetime import datetime, timedelta
from pathlib import Path
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
from typing import Dict, List, Any, Optional
import threading
import webbrowser

# Paths - grounded in persistent storage per Constitution Rule 1
SPARK_DIR = Path.home() / ".spark"
RALPH_DIR = SPARK_DIR / "meta_ralph"
ADVISOR_DIR = SPARK_DIR / "advisor"

ROAST_HISTORY_FILE = RALPH_DIR / "roast_history.json"
OUTCOME_TRACKING_FILE = RALPH_DIR / "outcome_tracking.json"
LEARNINGS_STORE_FILE = RALPH_DIR / "learnings_store.json"
ADVICE_LOG_FILE = ADVISOR_DIR / "advice_log.jsonl"
EFFECTIVENESS_FILE = ADVISOR_DIR / "effectiveness.json"
RECENT_ADVICE_FILE = ADVISOR_DIR / "recent_advice.jsonl"

PORT = 8586


def load_json(path: Path) -> Dict:
    """Load JSON file safely."""
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def load_jsonl(path: Path, limit: int = 500) -> List[Dict]:
    """Load JSONL file safely, last N items."""
    if not path.exists():
        return []
    items = []
    try:
        with path.open("r", encoding="utf-8", errors="replace") as f:
            for line in f:
                if line.strip():
                    try:
                        items.append(json.loads(line))
                    except:
                        continue
    except:
        return []
    return items[-limit:]


def get_ralph_stats() -> Dict[str, Any]:
    """Get Meta Ralph statistics from storage."""
    roast_data = load_json(ROAST_HISTORY_FILE)
    outcome_data = load_json(OUTCOME_TRACKING_FILE)
    effectiveness = load_json(EFFECTIVENESS_FILE)

    # Extract stats from roast history
    history = roast_data.get("history", [])

    # Count verdicts from nested result structure
    verdicts = {"quality": 0, "needs_work": 0, "primitive": 0, "unknown": 0}
    scores_by_dimension = {
        "actionability": [],
        "novelty": [],
        "reasoning": [],
        "specificity": [],
        "outcome_linked": [],
        "total": []
    }

    recent_roasts = []
    for item in history[-100:]:  # Last 100 for analysis
        result = item.get("result", {})
        verdict = result.get("verdict", "unknown")
        if verdict:
            verdicts[verdict] = verdicts.get(verdict, 0) + 1

        score = result.get("score", {})
        for dim in scores_by_dimension:
            if dim in score:
                scores_by_dimension[dim].append(score[dim])

        # Build recent roasts list
        if result.get("original"):
            recent_roasts.append({
                "timestamp": item.get("timestamp", ""),
                "source": item.get("source", "unknown"),
                "text": result.get("original", "")[:100],
                "verdict": verdict,
                "total_score": score.get("total", 0),
                "trace_id": item.get("trace_id"),
                "scores": {
                    "act": score.get("actionability", 0),
                    "nov": score.get("novelty", 0),
                    "rea": score.get("reasoning", 0),
                    "spe": score.get("specificity", 0),
                    "out": score.get("outcome_linked", 0),
                },
                "issues": result.get("issues_found", []),
            })

    # Calculate averages
    avg_scores = {}
    for dim, values in scores_by_dimension.items():
        if values:
            avg_scores[dim] = sum(values) / len(values)
        else:
            avg_scores[dim] = 0

    # Outcome stats from tracking file
    records = outcome_data.get("records")
    if records is None:
        # Back-compat: older dashboards wrote {"outcomes": {...}}
        outcomes = outcome_data.get("outcomes", {})
        records = list(outcomes.values())

    def _is_good(outcome: Optional[str]) -> bool:
        o = (outcome or "").strip().lower()
        return o in ("good", "helpful", "success")

    def _is_bad(outcome: Optional[str]) -> bool:
        o = (outcome or "").strip().lower()
        return o in ("bad", "unhelpful", "failure")

    total_tracked = len(records)
    acted_on = sum(1 for r in records if r.get("acted_on"))
    good_outcomes = sum(1 for r in records if _is_good(r.get("outcome")))
    bad_outcomes = sum(1 for r in records if _is_bad(r.get("outcome")))

    return {
        "totals": {
            "roasted": roast_data.get("total_roasted", 0),
            "quality_passed": roast_data.get("quality_passed", 0),
            "primitive_rejected": roast_data.get("primitive_rejected", 0),
            "duplicates_caught": roast_data.get("duplicates_caught", 0),
            "refinements_made": roast_data.get("refinements_made", 0),
            "learnings_stored": len(load_json(LEARNINGS_STORE_FILE).get("learnings", {})),
        },
        "rates": {
            "pass_rate": roast_data.get("quality_passed", 0) / max(1, roast_data.get("total_roasted", 1)),
            "reject_rate": roast_data.get("primitive_rejected", 0) / max(1, roast_data.get("total_roasted", 1)),
        },
        "verdicts": verdicts,
        "avg_scores": avg_scores,
        "outcomes": {
            "total_tracked": total_tracked,
            "acted_on": acted_on,
            "good_outcomes": good_outcomes,
            "bad_outcomes": bad_outcomes,
            "effectiveness": good_outcomes / max(1, acted_on) if acted_on > 0 else 0,
        },
        "effectiveness": effectiveness,
        "recent_roasts": list(reversed(recent_roasts[-20:])),  # Most recent first
        "last_updated": roast_data.get("last_updated", "unknown"),
    }


def get_advice_analysis() -> Dict[str, Any]:
    """Analyze advice quality by source and tool."""
    recent_advice = load_jsonl(RECENT_ADVICE_FILE, limit=500)

    # Analyze by source
    by_source = {}
    by_tool = {}

    for advice in recent_advice:
        sources = advice.get("sources", [])
        tool = advice.get("tool", "unknown")

        for source in sources:
            if source not in by_source:
                by_source[source] = {"count": 0, "tools": set()}
            by_source[source]["count"] += 1
            by_source[source]["tools"].add(tool)

        if tool not in by_tool:
            by_tool[tool] = {"count": 0, "sources": set()}
        by_tool[tool]["count"] += 1
        for s in sources:
            by_tool[tool]["sources"].add(s)

    # Convert sets to lists for JSON
    for s in by_source.values():
        s["tools"] = list(s["tools"])
    for t in by_tool.values():
        t["sources"] = list(t["sources"])

    return {
        "total_advice": len(recent_advice),
        "by_source": by_source,
        "by_tool": by_tool,
    }


def get_ralph_recommendations(stats: Dict) -> List[Dict[str, str]]:
    """Generate actionable recommendations based on current stats."""
    recommendations = []
    avg = stats.get("avg_scores", {})
    rates = stats.get("rates", {})
    outcomes = stats.get("outcomes", {})

    # Check each dimension for weaknesses
    if avg.get("outcome_linked", 0) < 0.5:
        recommendations.append({
            "priority": "HIGH",
            "dimension": "Outcome-Linked",
            "score": f"{avg.get('outcome_linked', 0):.2f}/2.0",
            "issue": "Most learnings aren't linked to validated outcomes",
            "fix": "Add outcome tracking: '...which leads to [result]' or validate with real usage data",
            "ralph_says": "I'm learnding, but I don't know if it worked!"
        })

    if avg.get("specificity", 0) < 0.8:
        recommendations.append({
            "priority": "HIGH",
            "dimension": "Specificity",
            "score": f"{avg.get('specificity', 0):.2f}/2.0",
            "issue": "Learnings are too generic - 'use X' without context",
            "fix": "Add context: 'In [domain/situation], use X because Y'",
            "ralph_says": "My cat's breath is generic. I mean... my advice is!"
        })

    if avg.get("reasoning", 0) < 0.8:
        recommendations.append({
            "priority": "MEDIUM",
            "dimension": "Reasoning",
            "score": f"{avg.get('reasoning', 0):.2f}/2.0",
            "issue": "Learnings state WHAT but not WHY",
            "fix": "Add reasoning: '...because Z' to explain the logic",
            "ralph_says": "Why? Because reasons! That's why!"
        })

    if avg.get("novelty", 0) < 0.8:
        recommendations.append({
            "priority": "MEDIUM",
            "dimension": "Novelty",
            "score": f"{avg.get('novelty', 0):.2f}/2.0",
            "issue": "Many learnings are obvious or already known",
            "fix": "Filter out common knowledge, focus on surprising insights",
            "ralph_says": "I already know that water is wet!"
        })

    if rates.get("pass_rate", 0) < 0.5:
        recommendations.append({
            "priority": "INFO",
            "dimension": "Pass Rate",
            "score": f"{rates.get('pass_rate', 0)*100:.1f}%",
            "issue": "Less than half of learnings pass quality gate",
            "fix": "This is okay if rejected items are truly primitive. Check the PRIMITIVE list.",
            "ralph_says": "Half is better than none... I think?"
        })

    if outcomes.get("effectiveness", 0) < 0.7 and outcomes.get("acted_on", 0) > 10:
        recommendations.append({
            "priority": "HIGH",
            "dimension": "Effectiveness",
            "score": f"{outcomes.get('effectiveness', 0)*100:.1f}%",
            "issue": "Advice that's acted on isn't helping much",
            "fix": "Review which advice sources produce unhelpful advice and tune them",
            "ralph_says": "I said do the thing but it didn't work!"
        })

    if not recommendations:
        recommendations.append({
            "priority": "SUCCESS",
            "dimension": "Overall",
            "score": "Good!",
            "issue": "No major issues detected",
            "fix": "Keep monitoring and iterating",
            "ralph_says": "I'm a unitard! Wait, that's good right?"
        })

    return recommendations


def get_dashboard_data() -> Dict[str, Any]:
    """Get all dashboard data - fresh from storage each request."""
    ralph_stats = get_ralph_stats()
    return {
        "timestamp": datetime.now().isoformat(),
        "ralph": ralph_stats,
        "advice": get_advice_analysis(),
        "recommendations": get_ralph_recommendations(ralph_stats),
    }


# HTML Dashboard Template
HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Meta Ralph Quality Analyzer</title>
    <meta charset="utf-8">
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body {
            font-family: 'Segoe UI', system-ui, sans-serif;
            background: linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%);
            color: #e8e8e8;
            min-height: 100vh;
            padding: 20px;
        }
        .container { max-width: 1400px; margin: 0 auto; }

        /* Header */
        .header {
            display: flex;
            align-items: center;
            gap: 20px;
            margin-bottom: 30px;
            padding: 20px;
            background: rgba(255,255,255,0.05);
            border-radius: 15px;
            border: 1px solid rgba(255,255,255,0.1);
        }
        .ralph-icon {
            font-size: 64px;
            animation: wiggle 2s infinite;
        }
        @keyframes wiggle {
            0%, 100% { transform: rotate(-3deg); }
            50% { transform: rotate(3deg); }
        }
        .header-text h1 {
            font-size: 28px;
            color: #ffd700;
            text-shadow: 2px 2px 4px rgba(0,0,0,0.3);
        }
        .header-text p { color: #aaa; margin-top: 5px; }
        .timestamp {
            margin-left: auto;
            color: #888;
            font-size: 14px;
            text-align: right;
        }

        /* Grid Layout */
        .grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 20px;
            margin-bottom: 20px;
        }

        /* Cards */
        .card {
            background: rgba(255,255,255,0.05);
            border-radius: 15px;
            padding: 20px;
            border: 1px solid rgba(255,255,255,0.1);
            transition: transform 0.2s, box-shadow 0.2s;
        }
        .card:hover {
            transform: translateY(-2px);
            box-shadow: 0 8px 25px rgba(0,0,0,0.3);
        }
        .card h2 {
            font-size: 16px;
            color: #ffd700;
            margin-bottom: 15px;
            display: flex;
            align-items: center;
            gap: 8px;
        }

        /* Metrics */
        .metric {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 10px 0;
            border-bottom: 1px solid rgba(255,255,255,0.05);
        }
        .metric:last-child { border-bottom: none; }
        .metric-label { color: #aaa; }
        .metric-value {
            font-size: 20px;
            font-weight: bold;
            color: #4ade80;
        }
        .metric-value.warning { color: #fbbf24; }
        .metric-value.error { color: #f87171; }

        /* Verdict Bars */
        .verdict-bar {
            display: flex;
            height: 30px;
            border-radius: 8px;
            overflow: hidden;
            margin: 15px 0;
        }
        .verdict-quality { background: #22c55e; }
        .verdict-needs-work { background: #f59e0b; }
        .verdict-primitive { background: #ef4444; }
        .verdict-segment {
            display: flex;
            align-items: center;
            justify-content: center;
            color: white;
            font-size: 12px;
            font-weight: bold;
            min-width: 40px;
        }

        /* Score Dimensions */
        .score-grid {
            display: grid;
            grid-template-columns: repeat(5, 1fr);
            gap: 10px;
            margin-top: 15px;
        }
        .score-item {
            text-align: center;
            padding: 10px;
            background: rgba(0,0,0,0.2);
            border-radius: 8px;
        }
        .score-item .label {
            font-size: 11px;
            color: #888;
            text-transform: uppercase;
        }
        .score-item .value {
            font-size: 24px;
            font-weight: bold;
            color: #60a5fa;
        }

        /* Recent Roasts Table */
        .roasts-table {
            width: 100%;
            border-collapse: collapse;
            margin-top: 10px;
            font-size: 13px;
        }
        .roasts-table th {
            text-align: left;
            padding: 10px;
            background: rgba(0,0,0,0.2);
            color: #ffd700;
            font-weight: 600;
        }
        .roasts-table td {
            padding: 10px;
            border-bottom: 1px solid rgba(255,255,255,0.05);
            vertical-align: top;
        }
        .roasts-table tr:hover {
            background: rgba(255,255,255,0.03);
        }
        .verdict-badge {
            padding: 3px 8px;
            border-radius: 4px;
            font-size: 11px;
            font-weight: bold;
            text-transform: uppercase;
        }
        .verdict-badge.quality { background: #22c55e; color: white; }
        .verdict-badge.needs_work { background: #f59e0b; color: black; }
        .verdict-badge.primitive { background: #ef4444; color: white; }

        /* Score Pills */
        .score-pills {
            display: flex;
            gap: 4px;
            flex-wrap: wrap;
        }
        .score-pill {
            padding: 2px 6px;
            border-radius: 4px;
            font-size: 10px;
            background: rgba(255,255,255,0.1);
        }
        .score-pill.high { background: #22c55e33; color: #4ade80; }
        .score-pill.med { background: #f59e0b33; color: #fbbf24; }
        .score-pill.low { background: #ef444433; color: #f87171; }

        /* Issues List */
        .issues-list {
            font-size: 11px;
            color: #f87171;
            max-width: 200px;
        }

        /* Full Width Card */
        .full-width { grid-column: 1 / -1; }

        /* Ralph Quote */
        .ralph-quote {
            font-style: italic;
            color: #888;
            padding: 15px;
            background: rgba(0,0,0,0.2);
            border-radius: 8px;
            margin-top: 10px;
            border-left: 3px solid #ffd700;
        }

        /* Refresh Button */
        .refresh-btn {
            position: fixed;
            bottom: 20px;
            right: 20px;
            background: #ffd700;
            color: #1a1a2e;
            border: none;
            padding: 15px 25px;
            border-radius: 30px;
            font-weight: bold;
            cursor: pointer;
            box-shadow: 0 4px 15px rgba(255,215,0,0.3);
            transition: transform 0.2s;
        }
        .refresh-btn:hover {
            transform: scale(1.05);
        }

        /* Source effectiveness */
        .source-bar {
            display: flex;
            align-items: center;
            margin: 8px 0;
        }
        .source-name {
            width: 120px;
            font-size: 12px;
            color: #aaa;
        }
        .source-fill {
            flex: 1;
            height: 20px;
            background: rgba(255,255,255,0.1);
            border-radius: 4px;
            overflow: hidden;
        }
        .source-fill-inner {
            height: 100%;
            background: linear-gradient(90deg, #3b82f6, #60a5fa);
            transition: width 0.3s;
        }
        .source-count {
            width: 50px;
            text-align: right;
            font-size: 12px;
            color: #60a5fa;
        }

        /* Recommendations */
        .recommendation {
            background: rgba(0,0,0,0.2);
            border-radius: 10px;
            padding: 15px;
            margin-bottom: 10px;
            border-left: 4px solid #ffd700;
        }
        .recommendation.HIGH { border-left-color: #ef4444; }
        .recommendation.MEDIUM { border-left-color: #f59e0b; }
        .recommendation.INFO { border-left-color: #60a5fa; }
        .recommendation.SUCCESS { border-left-color: #22c55e; }
        .rec-header {
            display: flex;
            align-items: center;
            gap: 10px;
            margin-bottom: 8px;
        }
        .rec-priority {
            padding: 3px 8px;
            border-radius: 4px;
            font-size: 10px;
            font-weight: bold;
        }
        .rec-priority.HIGH { background: #ef4444; color: white; }
        .rec-priority.MEDIUM { background: #f59e0b; color: black; }
        .rec-priority.INFO { background: #60a5fa; color: white; }
        .rec-priority.SUCCESS { background: #22c55e; color: white; }
        .rec-dimension { font-weight: bold; color: #ffd700; }
        .rec-score { color: #888; font-size: 12px; }
        .rec-issue { color: #f87171; margin-bottom: 5px; }
        .rec-fix { color: #4ade80; margin-bottom: 8px; }
        .rec-ralph {
            font-style: italic;
            color: #888;
            font-size: 12px;
            border-top: 1px solid rgba(255,255,255,0.1);
            padding-top: 8px;
            margin-top: 8px;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <div class="ralph-icon">🧒</div>
            <div class="header-text">
                <h1>Meta Ralph Quality Analyzer</h1>
                <p>"Me fail English? That's unpossible!" - Ralph Wiggum</p>
            </div>
            <div class="timestamp">
                <div>Last updated</div>
                <div id="timestamp">Loading...</div>
            </div>
        </div>

        <div class="grid">
            <!-- Overview Card -->
            <div class="card">
                <h2>📊 Quality Overview</h2>
                <div class="metric">
                    <span class="metric-label">Total Roasted</span>
                    <span class="metric-value" id="total-roasted">-</span>
                </div>
                <div class="metric">
                    <span class="metric-label">Quality Passed</span>
                    <span class="metric-value" id="quality-passed">-</span>
                </div>
                <div class="metric">
                    <span class="metric-label">Pass Rate</span>
                    <span class="metric-value" id="pass-rate">-</span>
                </div>
                <div class="metric">
                    <span class="metric-label">Learnings Stored</span>
                    <span class="metric-value" id="learnings-stored">-</span>
                </div>
            </div>

            <!-- Verdict Distribution -->
            <div class="card">
                <h2>⚖️ Verdict Distribution</h2>
                <div class="verdict-bar">
                    <div class="verdict-segment verdict-quality" id="bar-quality" style="width: 33%">0</div>
                    <div class="verdict-segment verdict-needs-work" id="bar-needs-work" style="width: 33%">0</div>
                    <div class="verdict-segment verdict-primitive" id="bar-primitive" style="width: 33%">0</div>
                </div>
                <div class="metric">
                    <span class="metric-label">🟢 Quality</span>
                    <span class="metric-value" id="verdict-quality">-</span>
                </div>
                <div class="metric">
                    <span class="metric-label">🟡 Needs Work</span>
                    <span class="metric-value warning" id="verdict-needs-work">-</span>
                </div>
                <div class="metric">
                    <span class="metric-label">🔴 Primitive</span>
                    <span class="metric-value error" id="verdict-primitive">-</span>
                </div>
            </div>

            <!-- Outcome Tracking -->
            <div class="card">
                <h2>🎯 Outcome Tracking</h2>
                <div class="metric">
                    <span class="metric-label">Total Tracked</span>
                    <span class="metric-value" id="outcomes-tracked">-</span>
                </div>
                <div class="metric">
                    <span class="metric-label">Acted On</span>
                    <span class="metric-value" id="outcomes-acted">-</span>
                </div>
                <div class="metric">
                    <span class="metric-label">Good Outcomes</span>
                    <span class="metric-value" id="outcomes-good">-</span>
                </div>
                <div class="metric">
                    <span class="metric-label">Effectiveness Rate</span>
                    <span class="metric-value" id="effectiveness-rate">-</span>
                </div>
                <div class="ralph-quote" id="effectiveness-quote">
                    Loading Ralph's wisdom...
                </div>
            </div>

            <!-- Effectiveness by Source -->
            <div class="card">
                <h2>📡 Advice by Source</h2>
                <div id="source-bars">Loading...</div>
            </div>

            <!-- Average Scores -->
            <div class="card full-width">
                <h2>📈 Average Scores (5 Dimensions)</h2>
                <div class="score-grid">
                    <div class="score-item">
                        <div class="label">Actionability</div>
                        <div class="value" id="avg-actionability">-</div>
                    </div>
                    <div class="score-item">
                        <div class="label">Novelty</div>
                        <div class="value" id="avg-novelty">-</div>
                    </div>
                    <div class="score-item">
                        <div class="label">Reasoning</div>
                        <div class="value" id="avg-reasoning">-</div>
                    </div>
                    <div class="score-item">
                        <div class="label">Specificity</div>
                        <div class="value" id="avg-specificity">-</div>
                    </div>
                    <div class="score-item">
                        <div class="label">Outcome-Linked</div>
                        <div class="value" id="avg-outcome">-</div>
                    </div>
                </div>
            </div>

            <!-- Ralph's Recommendations -->
            <div class="card full-width">
                <h2>🧠 Ralph's Recommendations</h2>
                <div id="recommendations">Loading recommendations...</div>
            </div>

            <!-- Recent Roasts -->
            <div class="card full-width">
                <h2>🔥 Recent Roasts (Last 20)</h2>
                <table class="roasts-table">
                    <thead>
                        <tr>
                            <th>Time</th>
                            <th>Verdict</th>
                            <th>Score</th>
                            <th>Dimensions</th>
                            <th>Text Preview</th>
                            <th>Issues</th>
                            <th>Trace</th>
                        </tr>
                    </thead>
                    <tbody id="roasts-tbody">
                        <tr><td colspan="7">Loading...</td></tr>
                    </tbody>
                </table>
            </div>
        </div>
    </div>

    <button class="refresh-btn" onclick="loadData()">🔄 Refresh</button>

    <script>
        const RALPH_QUOTES = [
            "My cat's breath smells like cat food.",
            "I bent my wookie.",
            "I'm learnding!",
            "That's where I saw the leprechaun. He told me to burn things.",
            "My doctor said I wouldn't have so many nose bleeds if I kept my finger outta there.",
            "I found a moon rock in my nose!",
            "Slow down! I wanna see the crunchy!",
        ];

        function getScoreClass(score, max = 2) {
            const pct = score / max;
            if (pct >= 0.7) return 'high';
            if (pct >= 0.4) return 'med';
            return 'low';
        }

        function formatTime(isoString) {
            if (!isoString) return '-';
            const d = new Date(isoString);
            return d.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' });
        }

        async function loadData() {
            try {
                const resp = await fetch('/api/data');
                const data = await resp.json();

                // Update timestamp
                document.getElementById('timestamp').textContent =
                    new Date(data.timestamp).toLocaleString();

                const r = data.ralph;

                // Overview
                document.getElementById('total-roasted').textContent = r.totals.roasted;
                document.getElementById('quality-passed').textContent = r.totals.quality_passed;
                document.getElementById('pass-rate').textContent = (r.rates.pass_rate * 100).toFixed(1) + '%';
                document.getElementById('learnings-stored').textContent = r.totals.learnings_stored;

                // Verdicts
                const total = r.verdicts.quality + r.verdicts.needs_work + r.verdicts.primitive;
                document.getElementById('verdict-quality').textContent = r.verdicts.quality;
                document.getElementById('verdict-needs-work').textContent = r.verdicts.needs_work;
                document.getElementById('verdict-primitive').textContent = r.verdicts.primitive;

                // Verdict bars
                if (total > 0) {
                    document.getElementById('bar-quality').style.width = (r.verdicts.quality / total * 100) + '%';
                    document.getElementById('bar-quality').textContent = r.verdicts.quality;
                    document.getElementById('bar-needs-work').style.width = (r.verdicts.needs_work / total * 100) + '%';
                    document.getElementById('bar-needs-work').textContent = r.verdicts.needs_work;
                    document.getElementById('bar-primitive').style.width = (r.verdicts.primitive / total * 100) + '%';
                    document.getElementById('bar-primitive').textContent = r.verdicts.primitive;
                }

                // Outcomes
                document.getElementById('outcomes-tracked').textContent = r.outcomes.total_tracked;
                document.getElementById('outcomes-acted').textContent = r.outcomes.acted_on;
                document.getElementById('outcomes-good').textContent = r.outcomes.good_outcomes;
                document.getElementById('effectiveness-rate').textContent = (r.outcomes.effectiveness * 100).toFixed(1) + '%';

                // Ralph quote based on effectiveness
                const eff = r.outcomes.effectiveness;
                let quote = '';
                if (eff >= 0.9) quote = "I'm a unitard!";
                else if (eff >= 0.7) quote = "I'm learnding!";
                else if (eff >= 0.5) quote = "I bent my wookie.";
                else quote = RALPH_QUOTES[Math.floor(Math.random() * RALPH_QUOTES.length)];
                document.getElementById('effectiveness-quote').textContent = '"' + quote + '"';

                // Average scores
                document.getElementById('avg-actionability').textContent = r.avg_scores.actionability.toFixed(2);
                document.getElementById('avg-novelty').textContent = r.avg_scores.novelty.toFixed(2);
                document.getElementById('avg-reasoning').textContent = r.avg_scores.reasoning.toFixed(2);
                document.getElementById('avg-specificity').textContent = r.avg_scores.specificity.toFixed(2);
                document.getElementById('avg-outcome').textContent = r.avg_scores.outcome_linked.toFixed(2);

                // Source bars
                const sources = data.advice.by_source;
                const maxCount = Math.max(...Object.values(sources).map(s => s.count), 1);
                let sourceHtml = '';
                for (const [name, info] of Object.entries(sources).sort((a, b) => b[1].count - a[1].count).slice(0, 8)) {
                    const pct = (info.count / maxCount * 100);
                    sourceHtml += `
                        <div class="source-bar">
                            <div class="source-name">${name}</div>
                            <div class="source-fill">
                                <div class="source-fill-inner" style="width: ${pct}%"></div>
                            </div>
                            <div class="source-count">${info.count}</div>
                        </div>
                    `;
                }
                document.getElementById('source-bars').innerHTML = sourceHtml || '<p style="color:#888">No data yet</p>';

                // Recommendations
                let recsHtml = '';
                for (const rec of data.recommendations) {
                    recsHtml += `
                        <div class="recommendation ${rec.priority}">
                            <div class="rec-header">
                                <span class="rec-priority ${rec.priority}">${rec.priority}</span>
                                <span class="rec-dimension">${rec.dimension}</span>
                                <span class="rec-score">(${rec.score})</span>
                            </div>
                            <div class="rec-issue">Issue: ${rec.issue}</div>
                            <div class="rec-fix">Fix: ${rec.fix}</div>
                            <div class="rec-ralph">Ralph says: "${rec.ralph_says}"</div>
                        </div>
                    `;
                }
                document.getElementById('recommendations').innerHTML = recsHtml || '<p style="color:#4ade80">No issues detected!</p>';

                // Recent roasts table
                let tbody = '';
                for (const roast of r.recent_roasts) {
                    const verdictClass = roast.verdict || 'unknown';
                    const scores = roast.scores;
                    const traceLink = roast.trace_id ? `<a href="http://localhost:8585/mission?trace_id=${roast.trace_id}" target="_blank">trace</a>` : '-';
                    tbody += `
                        <tr>
                            <td>${formatTime(roast.timestamp)}</td>
                            <td><span class="verdict-badge ${verdictClass}">${roast.verdict || '?'}</span></td>
                            <td style="font-weight:bold;color:#60a5fa">${roast.total_score}</td>
                            <td>
                                <div class="score-pills">
                                    <span class="score-pill ${getScoreClass(scores.act)}">A:${scores.act}</span>
                                    <span class="score-pill ${getScoreClass(scores.nov)}">N:${scores.nov}</span>
                                    <span class="score-pill ${getScoreClass(scores.rea)}">R:${scores.rea}</span>
                                    <span class="score-pill ${getScoreClass(scores.spe)}">S:${scores.spe}</span>
                                    <span class="score-pill ${getScoreClass(scores.out)}">O:${scores.out}</span>
                                </div>
                            </td>
                            <td style="max-width:300px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">${roast.text}</td>
                            <td class="issues-list">${roast.issues.slice(0,2).join(', ')}</td>
                            <td>${traceLink}</td>
                        </tr>
                    `;
                }
                document.getElementById('roasts-tbody').innerHTML = tbody || '<tr><td colspan="7">No roasts yet</td></tr>';

            } catch (err) {
                console.error('Load error:', err);
            }
        }

        // Load on start
        loadData();

        // Auto-refresh every 10 seconds
        setInterval(loadData, 10000);
    </script>
</body>
</html>
"""


class DashboardHandler(SimpleHTTPRequestHandler):
    """HTTP handler for the dashboard."""

    def log_message(self, format, *args):
        """Suppress default logging."""
        pass

    def do_GET(self):
        parsed = urlparse(self.path)

        if parsed.path == "/" or parsed.path == "/index.html":
            self.send_response(200)
            self.send_header("Content-Type", "text/html")
            self.end_headers()
            self.wfile.write(HTML_TEMPLATE.encode())

        elif parsed.path == "/api/data":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            data = get_dashboard_data()
            self.wfile.write(json.dumps(data).encode())
        elif parsed.path == "/api/status":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"ok": True}).encode())
        elif parsed.path == "/health":
            self.send_response(200)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.end_headers()
            self.wfile.write(b"ok")

        else:
            self.send_error(404)


def main():
    """Start the dashboard server."""
    print(f"""
================================================================
        META RALPH QUALITY ANALYZER DASHBOARD
================================================================
  "Me fail English? That's unpossible!" - Ralph Wiggum

  Open: http://localhost:{PORT}
  Press Ctrl+C to stop
================================================================
""")

    server = ThreadingHTTPServer(("0.0.0.0", PORT), DashboardHandler)

    # Open browser
    def open_browser():
        time.sleep(0.5)
        webbrowser.open(f"http://localhost:{PORT}")

    threading.Thread(target=open_browser, daemon=True).start()

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nBye bye! My cat's breath smells like cat food.")
        server.shutdown()


if __name__ == "__main__":
    main()
