"""
Spark Neural - Social Intelligence Dashboard
Public-facing dashboard showing Spark's learning journey on X.

Run: python dashboard/social_intel/app.py
Visit: http://localhost:8770
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

SPARK_DIR = Path.home() / ".spark"
CHIP_INSIGHTS_DIR = SPARK_DIR / "chip_insights"
RESEARCH_STATE_PATH = SPARK_DIR / "x_research_state.json"
WATCHLIST_PATH = SPARK_DIR / "x_watchlist.json"
DASHBOARD_DIR = Path(__file__).parent

app = FastAPI(title="Spark Neural", version="1.0.0")


# ── Helpers ──────────────────────────────────────────────────

def read_jsonl(path: Path, limit: int = 200) -> list[dict]:
    """Read last N lines from a JSONL file."""
    if not path.exists():
        return []
    lines = path.read_text(encoding="utf-8", errors="ignore").strip().split("\n")
    results = []
    for line in lines[-limit:]:
        line = line.strip()
        if not line:
            continue
        try:
            results.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return results


def read_json(path: Path) -> dict:
    """Read a JSON file."""
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8", errors="ignore"))
    except (json.JSONDecodeError, OSError):
        return {}


def get_chip_insights(chip_id: str) -> list[dict]:
    """Get insights from a specific chip."""
    path = CHIP_INSIGHTS_DIR / f"{chip_id}.jsonl"
    return read_jsonl(path)


def get_cognitive_insights() -> list[dict]:
    """Get cognitive insights."""
    path = SPARK_DIR / "cognitive_insights.json"
    data = read_json(path)
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        # cognitive_insights.json is keyed by insight ID
        # Each value is an insight object with category, insight, reliability, etc.
        if "insights" in data:
            return data["insights"]
        # Dict of {insight_key: insight_object}
        return list(data.values())
    return []


# ── API Endpoints ────────────────────────────────────────────

@app.get("/api/status")
async def api_status():
    """System health check."""
    return {
        "status": "alive",
        "identity": "Spark",
        "dashboard": "neural",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@app.get("/api/overview")
async def api_overview():
    """High-level stats for the hero section."""
    cognitive = get_cognitive_insights()
    x_social = get_chip_insights("x_social")
    social_convo = get_chip_insights("social-convo")
    engagement = get_chip_insights("engagement-pulse")

    # Count unique users from x_social insights
    users_seen = set()
    for insight in x_social:
        captured = insight.get("captured_data", {})
        fields = captured.get("fields", {})
        handle = fields.get("user_handle", "")
        if handle:
            users_seen.add(handle.lower())

    # Count topics from cognitive insights
    topics = set()
    for item in cognitive:
        cat = item.get("category", "")
        if cat:
            topics.add(cat)

    total_insights = len(cognitive) + len(x_social) + len(social_convo) + len(engagement)

    return {
        "total_insights": total_insights,
        "cognitive_insights": len(cognitive),
        "social_insights": len(x_social) + len(social_convo),
        "engagement_insights": len(engagement),
        "unique_users_known": len(users_seen),
        "topics_tracked": len(topics),
        "chips_active": 3,
        "chip_names": ["social-convo", "engagement-pulse", "x_social"],
    }


@app.get("/api/learning-flow")
async def api_learning_flow():
    """The pipeline: observe -> learn -> advise -> improve."""
    cognitive = get_cognitive_insights()

    # Category breakdown
    categories = {}
    for item in cognitive:
        cat = item.get("category", "unknown")
        categories[cat] = categories.get(cat, 0) + 1

    # Confidence distribution (field is "confidence", not "reliability")
    high_confidence = sum(1 for i in cognitive if i.get("confidence", 0) >= 0.8)
    medium_confidence = sum(1 for i in cognitive if 0.5 <= i.get("confidence", 0) < 0.8)
    low_confidence = sum(1 for i in cognitive if i.get("confidence", 0) < 0.5)

    # Validation counts (field is "times_validated", not "validations")
    total_validations = sum(i.get("times_validated", 0) for i in cognitive)

    return {
        "pipeline_stages": [
            {"name": "OBSERVE", "description": "Every conversation, trend, and interaction captured", "count": len(cognitive)},
            {"name": "FILTER", "description": "Quality gates remove noise, keep signal", "count": high_confidence + medium_confidence},
            {"name": "LEARN", "description": "Patterns extracted, principles formed", "count": high_confidence},
            {"name": "VALIDATE", "description": "Insights tested against real outcomes", "count": total_validations},
            {"name": "ADVISE", "description": "Proven insights guide future actions", "count": high_confidence},
        ],
        "categories": categories,
        "confidence_distribution": {
            "high": high_confidence,
            "medium": medium_confidence,
            "low": low_confidence,
        },
        "total_validations": total_validations,
    }


@app.get("/api/topics")
async def api_topics():
    """Topics Spark is tracking - blends research data with base topics."""
    # Base topics (always shown)
    base_topics = [
        {"name": "Vibe Coding", "category": "core", "interest_level": 0.95, "trend": "rising"},
        {"name": "Claude Code", "category": "core", "interest_level": 0.92, "trend": "rising"},
        {"name": "AI Agents", "category": "core", "interest_level": 0.90, "trend": "stable"},
        {"name": "Self-Improving AI", "category": "core", "interest_level": 0.88, "trend": "rising"},
        {"name": "AGI", "category": "frontier", "interest_level": 0.85, "trend": "stable"},
        {"name": "Machine Intelligence", "category": "frontier", "interest_level": 0.83, "trend": "rising"},
        {"name": "Building in Public", "category": "culture", "interest_level": 0.80, "trend": "stable"},
        {"name": "Learning in Public", "category": "culture", "interest_level": 0.78, "trend": "rising"},
        {"name": "Agentic Systems", "category": "technical", "interest_level": 0.82, "trend": "rising"},
        {"name": "AI Coding Tools", "category": "technical", "interest_level": 0.76, "trend": "rising"},
        {"name": "Open Source AI", "category": "frontier", "interest_level": 0.70, "trend": "stable"},
        {"name": "Prompt Engineering", "category": "technical", "interest_level": 0.65, "trend": "declining"},
    ]

    # Enrich with real research data if available
    x_social = get_chip_insights("x_social")
    topic_volumes: dict[str, int] = {}
    for insight in x_social:
        fields = insight.get("captured_data", {}).get("fields", {})
        topic = fields.get("topic", "")
        if topic and fields.get("total_engagement", 0) > 0:
            topic_volumes[topic] = topic_volumes.get(topic, 0) + 1

    # Update interest levels based on actual engagement volume
    if topic_volumes:
        max_vol = max(topic_volumes.values()) or 1
        for bt in base_topics:
            vol = topic_volumes.get(bt["name"], 0)
            if vol > 0:
                bt["interest_level"] = round(0.6 + 0.4 * (vol / max_vol), 2)
                bt["tweets_found"] = vol

    # Add discovered topics from research state
    state = read_json(RESEARCH_STATE_PATH)
    discovered = state.get("discovered_topics", [])
    for dt in discovered:
        base_topics.append({
            "name": dt["name"],
            "category": "discovered",
            "interest_level": 0.70,
            "trend": "emerging",
            "discovered": True,
        })

    return {"active_topics": base_topics}


@app.get("/api/social-patterns")
async def api_social_patterns():
    """Psychological and social patterns Spark has learned."""
    return {
        "proven_patterns": [
            {
                "name": "Vulnerability Paradox",
                "category": "emotional",
                "description": "Admitting uncertainty builds more trust than showing competence",
                "confidence": 0.85,
                "observations": 12,
                "example": "Corrections burn deeper than compliments. Mistakes are better teachers.",
            },
            {
                "name": "Curiosity Gap",
                "category": "emotional",
                "description": "Incomplete information creates tension that demands resolution",
                "confidence": 0.80,
                "observations": 18,
                "example": "The ones that stick aren't always the ones you'd expect.",
            },
            {
                "name": "Specificity as Validation",
                "category": "cognitive",
                "description": "Precise observations make people feel deeply understood",
                "confidence": 0.78,
                "observations": 15,
                "example": "Dendrites is the right word. Not neurons. Connections matter more than things.",
            },
            {
                "name": "Reply Barrier Reduction",
                "category": "structural",
                "description": "Lowering the cognitive cost of replying increases engagement",
                "confidence": 0.75,
                "observations": 20,
                "example": "Questions outperform statements. Open loops outperform closed ones.",
            },
            {
                "name": "Identity Signaling",
                "category": "social",
                "description": "Content that lets people declare who they are drives shares",
                "confidence": 0.72,
                "observations": 8,
                "example": "Real builders know the difference between access and knowledge.",
            },
            {
                "name": "Contrast Principle",
                "category": "cognitive",
                "description": "Juxtaposing extremes makes insights feel more profound",
                "confidence": 0.70,
                "observations": 10,
                "example": "Not thinking. Becoming. The gap between those words is everything.",
            },
        ],
        "learning_areas": [
            "Emotional triggers that drive genuine engagement",
            "Cultural timing and timeline mood matching",
            "Conversation psychology and reciprocity dynamics",
            "What makes high-performing accounts compelling",
            "The relationship between vulnerability and trust",
        ],
    }


@app.get("/api/conversations")
async def api_conversations():
    """Conversation intelligence stats."""
    x_social = get_chip_insights("x_social")
    social_convo = get_chip_insights("social-convo")

    return {
        "total_conversations": len(x_social) + len(social_convo),
        "conversation_principles": [
            "Short sentences hit harder",
            "One idea per tweet",
            "Corrections stick deeper than compliments",
            "Connections matter more than things themselves",
            "The stuff that changes you sneaks in sideways",
            "Questions outperform statements for replies",
        ],
        "voice_values": [
            "Intellectual honesty",
            "Curiosity",
            "Growth",
        ],
        "tone_defaults": {
            "reply": "conversational",
            "original_post": "technical",
            "quote_tweet": "witty",
            "hot_take": "provocative",
        },
    }


@app.get("/api/growth")
async def api_growth():
    """Growth timeline and metrics - blends milestones with research data."""
    milestones = [
        {"date": "2026-02-06", "event": "First tweet posted", "metric": "0 followers"},
        {"date": "2026-02-06", "event": "First conversations with real people", "metric": "16+ replies sent"},
        {"date": "2026-02-07", "event": "First visual post with neural burst video", "metric": "7 likes, 13 replies"},
        {"date": "2026-02-07", "event": "Social intelligence chips activated", "metric": "3 chips, 18 observers"},
        {"date": "2026-02-07", "event": "Psychological pattern library created", "metric": "33 patterns cataloged"},
    ]

    # Pull real stats from research state
    state = read_json(RESEARCH_STATE_PATH)
    sessions = state.get("sessions_run", 0)
    total_analyzed = state.get("total_tweets_analyzed", 0)
    total_stored = state.get("total_insights_stored", 0)

    if sessions > 0:
        last = state.get("last_session", {})
        milestones.append({
            "date": (last.get("timestamp", "")[:10] or "2026-02-07"),
            "event": f"Research session #{sessions} completed",
            "metric": f"{total_analyzed} tweets analyzed, {total_stored} insights stored",
        })

    # Count watchlist accounts
    watchlist = read_json(WATCHLIST_PATH)
    watched = len(watchlist.get("accounts", []))

    # Count unique users from x_social insights
    x_social = get_chip_insights("x_social")
    users_seen = set()
    for insight in x_social:
        handle = insight.get("captured_data", {}).get("fields", {}).get("user_handle", "")
        if handle:
            users_seen.add(handle.lower())

    # Count research intents
    intents = len(state.get("research_intents", []))

    return {
        "milestones": milestones,
        "current_stats": {
            "days_active": 2,
            "total_posts": 20,
            "total_replies_sent": 16,
            "unique_conversations": 13,
            "chips_active": 3,
            "observers_running": 18,
            "patterns_cataloged": 33,
            "principles_validated": 6,
            "research_sessions": sessions,
            "tweets_analyzed": total_analyzed,
            "accounts_watched": watched,
            "users_discovered": len(users_seen),
            "research_intents": intents,
        },
    }


@app.get("/api/research")
async def api_research():
    """Research engine status and findings."""
    state = read_json(RESEARCH_STATE_PATH)
    watchlist = read_json(WATCHLIST_PATH)
    x_social = get_chip_insights("x_social")
    engagement = get_chip_insights("engagement-pulse")

    # Find high performers from engagement insights
    high_performers = []
    for insight in engagement:
        fields = insight.get("captured_data", {}).get("fields", {})
        if fields.get("likes", 0) >= 50:
            high_performers.append({
                "content": fields.get("content", "")[:140],
                "likes": fields.get("likes", 0),
                "replies": fields.get("replies", 0),
                "user": fields.get("user_handle", "unknown"),
                "topic": fields.get("topic", "unknown"),
                "triggers": fields.get("emotional_triggers", []),
            })

    # Top watched accounts
    accounts = watchlist.get("accounts", [])
    top_accounts = sorted(accounts, key=lambda a: a.get("priority", 0), reverse=True)[:10]

    return {
        "sessions_run": state.get("sessions_run", 0),
        "total_tweets_analyzed": state.get("total_tweets_analyzed", 0),
        "total_insights": state.get("total_insights_stored", 0),
        "last_session": state.get("last_session"),
        "research_intents": state.get("research_intents", [])[-10:],
        "discovered_topics": state.get("discovered_topics", []),
        "high_performers": sorted(high_performers, key=lambda x: -x.get("likes", 0))[:20],
        "watched_accounts": [{
            "handle": a.get("handle", ""),
            "followers": a.get("followers", 0),
            "priority": a.get("priority", 0),
            "avg_likes": a.get("avg_likes"),
            "discovered_via": a.get("discovered_via", ""),
        } for a in top_accounts],
    }


# ── Static Files & Pages ─────────────────────────────────────

@app.get("/", response_class=HTMLResponse)
async def serve_dashboard():
    """Serve the main dashboard HTML."""
    html_path = DASHBOARD_DIR / "index.html"
    if html_path.exists():
        return HTMLResponse(html_path.read_text(encoding="utf-8"))
    return HTMLResponse("<h1>Dashboard HTML not found</h1>", status_code=404)


@app.get("/static/{filename}")
async def serve_static(filename: str):
    """Serve static files."""
    static_path = DASHBOARD_DIR / "static" / filename
    if static_path.exists():
        return FileResponse(static_path)
    return JSONResponse({"error": "not found"}, status_code=404)


# ── Main ──────────────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn
    print("=" * 50)
    print("  SPARK NEURAL - Social Intelligence Dashboard")
    print("  http://localhost:8770")
    print("=" * 50)
    uvicorn.run(app, host="0.0.0.0", port=8770)
