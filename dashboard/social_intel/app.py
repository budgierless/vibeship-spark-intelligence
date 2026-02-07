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

def read_jsonl(path: Path, limit: int = 5000) -> list[dict]:
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
    """Topics Spark is tracking - live from the research engine."""
    from lib.x_research import DEFAULT_TOPICS, CATEGORY_MIN_LIKES

    state = read_json(RESEARCH_STATE_PATH)
    topic_perf = state.get("topic_performance", {})
    session_num = state.get("sessions_run", 0)

    topics = []
    for t in DEFAULT_TOPICS:
        name = t["name"]
        tier = t.get("tier", 1)
        category = t.get("category", "core")
        min_likes = CATEGORY_MIN_LIKES.get(category, 50)
        perf = topic_perf.get(name, {})
        hits = perf.get("hits", 0)
        misses = perf.get("misses", 0)
        total = hits + misses
        hit_rate = round(hits / total, 2) if total > 0 else None
        consecutive_zeros = perf.get("consecutive_zeros", 0)
        skipped = consecutive_zeros >= 3

        # Determine trend from hit rate
        if total < 3:
            trend = "new"
        elif hit_rate and hit_rate > 0.5:
            trend = "rising"
        elif hit_rate and hit_rate > 0.2:
            trend = "stable"
        elif skipped:
            trend = "paused"
        else:
            trend = "declining"

        # Determine if topic runs this session
        active_this_session = True
        if tier == 2 and session_num % 2 != 0:
            active_this_session = False
        if tier == 3 and session_num % 3 != 0:
            active_this_session = False
        if skipped:
            active_this_session = False

        topics.append({
            "name": name,
            "category": category,
            "tier": tier,
            "query": t["query"],
            "min_likes": min_likes,
            "hit_rate": hit_rate,
            "hits": hits,
            "misses": misses,
            "sessions_tracked": total,
            "trend": trend,
            "skipped": skipped,
            "active_this_session": active_this_session,
        })

    # Add discovered topics from research state
    discovered = state.get("discovered_topics", [])
    for dt in discovered:
        topics.append({
            "name": dt["name"],
            "category": "discovered",
            "tier": 2,
            "query": dt.get("query", dt["name"]),
            "min_likes": CATEGORY_MIN_LIKES.get("discovered", 50),
            "hit_rate": None,
            "hits": 0,
            "misses": 0,
            "sessions_tracked": 0,
            "trend": "emerging",
            "skipped": False,
            "active_this_session": True,
        })

    return {"active_topics": topics, "session_num": session_num}


@app.get("/api/social-patterns")
async def api_social_patterns():
    """Psychological and social patterns - built from real research data."""
    x_social = get_chip_insights("x_social")
    engagement = get_chip_insights("engagement-pulse")
    social_convo = get_chip_insights("social-convo")

    # Pattern descriptions for each trigger type
    trigger_meta = {
        "curiosity_gap": {
            "name": "Curiosity Gap",
            "category": "emotional",
            "description": "Incomplete information creates tension that demands resolution",
        },
        "surprise": {
            "name": "Strategic Surprise",
            "category": "emotional",
            "description": "Counter-intuitive claims stop the scroll and force re-reading",
        },
        "validation": {
            "name": "Validation Through Specificity",
            "category": "cognitive",
            "description": "Making people feel seen and understood drives deep engagement",
        },
        "vulnerability": {
            "name": "Vulnerability Paradox",
            "category": "emotional",
            "description": "Admitting uncertainty builds more trust than showing competence",
        },
        "aspiration": {
            "name": "Aspiration Bridge",
            "category": "emotional",
            "description": "Connecting current reality to a better future pulls people forward",
        },
        "contrast": {
            "name": "Contrast Principle",
            "category": "cognitive",
            "description": "Juxtaposing extremes makes insights feel more profound",
        },
        "identity_signal": {
            "name": "Identity Signaling",
            "category": "social",
            "description": "Content that lets people declare who they are drives shares",
        },
    }

    # Count triggers across ALL tweets (not just high performers)
    trigger_counts: dict[str, int] = {}
    trigger_engagement: dict[str, list[int]] = {}
    trigger_examples: dict[str, str] = {}
    questions_likes: list[int] = []
    statements_likes: list[int] = []
    total_tweets_with_triggers = 0

    for source in [x_social, engagement]:
        for insight in source:
            fields = insight.get("captured_data", {}).get("fields", {})
            triggers = fields.get("emotional_triggers", [])
            likes = fields.get("likes", 0) or fields.get("total_engagement", 0)
            text = fields.get("tweet_text", "") or fields.get("content", "")

            if triggers:
                total_tweets_with_triggers += 1

            for t in triggers:
                trigger_counts[t] = trigger_counts.get(t, 0) + 1
                trigger_engagement.setdefault(t, []).append(likes)
                # Keep best example per trigger
                if likes > 0 and (t not in trigger_examples or likes > trigger_engagement[t][-2] if len(trigger_engagement[t]) > 1 else True):
                    if text and len(text) > 20:
                        trigger_examples[t] = text[:140]

            if text and "?" in text:
                questions_likes.append(likes)
            elif text:
                statements_likes.append(likes)

    # Build patterns sorted by observation count
    proven_patterns = []
    for trigger, count in sorted(trigger_counts.items(), key=lambda x: -x[1]):
        meta = trigger_meta.get(trigger, {
            "name": trigger.replace("_", " ").title(),
            "category": "discovered",
            "description": f"Pattern detected in {count} tweets",
        })
        avg_eng = round(sum(trigger_engagement[trigger]) / max(len(trigger_engagement[trigger]), 1), 1)
        proven_patterns.append({
            "name": meta["name"],
            "category": meta["category"],
            "description": meta["description"],
            "confidence": round(min(0.95, 0.5 + count / 200), 2),
            "observations": count,
            "avg_engagement": avg_eng,
            "example": trigger_examples.get(trigger, ""),
        })

    # Add structural patterns from data
    if questions_likes and statements_likes:
        q_avg = sum(questions_likes) / len(questions_likes)
        s_avg = sum(statements_likes) / len(statements_likes)
        if q_avg > s_avg:
            proven_patterns.append({
                "name": "Reply Barrier Reduction",
                "category": "structural",
                "description": f"Questions avg {q_avg:.0f} engagement vs statements {s_avg:.0f}",
                "confidence": round(min(0.9, 0.5 + len(questions_likes) / 500), 2),
                "observations": len(questions_likes),
                "avg_engagement": round(q_avg, 1),
                "example": "Questions outperform statements. Open loops outperform closed ones.",
            })

    # If no triggers found yet, show that we're still learning
    if not proven_patterns:
        proven_patterns = [{
            "name": "Collecting Data",
            "category": "system",
            "description": "Analyzing tweets to detect patterns. More research sessions needed.",
            "confidence": 0.1,
            "observations": 0,
            "example": "Patterns emerge after sufficient observations.",
        }]

    # Extract LLM-generated content strategies from engagement insights
    strategy_counts: dict[str, list[int]] = {}
    hook_counts: dict[str, int] = {}
    writing_counts: dict[str, int] = {}
    for insight in engagement:
        fields = insight.get("captured_data", {}).get("fields", {})
        strat = fields.get("content_strategy", "")
        likes = fields.get("likes", 0)
        if strat:
            strategy_counts.setdefault(strat, []).append(likes)
        for hook in fields.get("engagement_hooks", []):
            hook_counts[hook] = hook_counts.get(hook, 0) + 1
        for wp in fields.get("writing_patterns", []):
            writing_counts[wp] = writing_counts.get(wp, 0) + 1

    content_strategies = sorted(
        [{"strategy": s.replace("_", " ").title(), "count": len(v),
          "avg_engagement": round(sum(v) / len(v), 1)} for s, v in strategy_counts.items()],
        key=lambda x: -x["count"],
    )[:8]

    engagement_hooks = sorted(
        [{"hook": h.replace("_", " ").title(), "count": c} for h, c in hook_counts.items()],
        key=lambda x: -x["count"],
    )[:10]

    writing_patterns = sorted(
        [{"pattern": p.replace("_", " ").title(), "count": c} for p, c in writing_counts.items()],
        key=lambda x: -x["count"],
    )[:8]

    return {
        "proven_patterns": proven_patterns[:8],
        "content_strategies": content_strategies,
        "engagement_hooks": engagement_hooks,
        "writing_patterns": writing_patterns,
        "total_tweets_analyzed": len(x_social) + len(engagement),
        "tweets_with_triggers": total_tweets_with_triggers,
        "learning_areas": [
            f"Tracking {len(trigger_counts)} emotional trigger types across {len(x_social)} observations",
            f"Questions vs statements engagement ({len(questions_likes)} questions analyzed)",
            f"LLM-analyzed {len(strategy_counts)} content strategies from high performers",
            f"Identified {len(hook_counts)} engagement hooks and {len(writing_counts)} writing patterns",
            "How high-performing accounts use emotional layering",
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
    strategy_counts: dict[str, int] = {}
    hook_counts: dict[str, int] = {}
    lessons: list[str] = []
    llm_analyzed_count = 0

    for insight in engagement:
        fields = insight.get("captured_data", {}).get("fields", {})
        if fields.get("likes", 0) >= 50:
            hp_entry = {
                "content": fields.get("content", "")[:140],
                "likes": fields.get("likes", 0),
                "replies": fields.get("replies", 0),
                "user": fields.get("user_handle", "unknown"),
                "topic": fields.get("topic", "unknown"),
                "triggers": fields.get("emotional_triggers", []),
            }
            # Include LLM analysis fields if present
            if fields.get("llm_analysis"):
                llm_analyzed_count += 1
                llm = fields["llm_analysis"]
                hp_entry["content_strategy"] = fields.get("content_strategy", "")
                hp_entry["why_it_works"] = fields.get("why_it_works", "")
                hp_entry["engagement_hooks"] = fields.get("engagement_hooks", [])
                hp_entry["replicable_lesson"] = fields.get("replicable_lesson", "")
                # Aggregate for intelligence summary
                strat = fields.get("content_strategy", "")
                if strat:
                    strategy_counts[strat] = strategy_counts.get(strat, 0) + 1
                for hook in fields.get("engagement_hooks", []):
                    hook_counts[hook] = hook_counts.get(hook, 0) + 1
                lesson = fields.get("replicable_lesson", "")
                if lesson:
                    lessons.append(lesson)
            high_performers.append(hp_entry)

    # Top watched accounts
    accounts = watchlist.get("accounts", [])
    top_accounts = sorted(accounts, key=lambda a: a.get("priority", 0), reverse=True)[:10]

    # Build intelligence summary from LLM analysis
    intelligence = {}
    if llm_analyzed_count > 0:
        intelligence = {
            "llm_analyzed": llm_analyzed_count,
            "top_strategies": sorted(
                [{"strategy": s, "count": c} for s, c in strategy_counts.items()],
                key=lambda x: -x["count"],
            )[:8],
            "top_hooks": sorted(
                [{"hook": h, "count": c} for h, c in hook_counts.items()],
                key=lambda x: -x["count"],
            )[:10],
            "actionable_lessons": lessons[:10],
        }

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
        "intelligence": intelligence,
    }


@app.get("/api/filter-funnel")
async def api_filter_funnel():
    """Filter/distillation funnel — traces intelligence from raw data to final influence."""
    from collections import Counter, defaultdict

    engagement = get_chip_insights("engagement-pulse")
    evo_log = read_jsonl(SPARK_DIR / "x_evolution_log.jsonl", limit=500)
    evo_state = read_json(SPARK_DIR / "x_evolution_state.json")
    research = read_json(RESEARCH_STATE_PATH)

    # Stage 1: Research input
    total_analyzed = research.get("total_tweets_analyzed", 0) or 0

    # Stage 2: Engagement insights (passed threshold)
    total_insights = len(engagement)
    llm_analyzed = 0
    for ins in engagement:
        fields = ins.get("captured_data", {}).get("fields", {})
        if fields.get("why_it_works") or fields.get("replicable_lesson"):
            llm_analyzed += 1

    # Stage 3: Evolution events
    event_types = Counter()
    high_conf = 0
    med_conf = 0
    for e in evo_log:
        event_types[e.get("event_type", "unknown")] += 1
        c = e.get("confidence", 0)
        if c >= 0.7:
            high_conf += 1
        elif c >= 0.4:
            med_conf += 1

    # Stage 4: MetaRalph promotion
    promoted = evo_state.get("promoted_event_timestamps", [])
    filtered_count = high_conf - len(promoted) if high_conf > len(promoted) else 0

    # Trigger performance
    trigger_likes = defaultdict(list)
    strategy_likes = defaultdict(list)
    for ins in engagement:
        fields = ins.get("captured_data", {}).get("fields", {})
        likes = fields.get("likes", 0)
        for t in fields.get("emotional_triggers", []):
            trigger_likes[t].append(likes)
        strat = fields.get("content_strategy", "")
        if strat:
            strategy_likes[strat].append(likes)

    # Current weights
    weights = evo_state.get("voice_weights", {})
    trigger_weights = weights.get("triggers", {})
    strategy_weights = weights.get("strategies", {})

    # Build trigger performance list
    trigger_perf = []
    for t, likes_list in sorted(trigger_likes.items(), key=lambda x: -sum(x[1]) / max(len(x[1]), 1)):
        avg = sum(likes_list) / len(likes_list)
        w = trigger_weights.get(t, 1.0)
        trigger_perf.append({
            "trigger": t,
            "observations": len(likes_list),
            "avg_likes": round(avg),
            "weight": round(w, 3),
            "direction": "boosted" if w > 1.02 else "reduced" if w < 0.98 else "neutral",
        })

    # Build strategy performance list
    strategy_perf = []
    for s, likes_list in sorted(strategy_likes.items(), key=lambda x: -sum(x[1]) / max(len(x[1]), 1))[:10]:
        avg = sum(likes_list) / len(likes_list)
        w = strategy_weights.get(s, None)
        strategy_perf.append({
            "strategy": s,
            "observations": len(likes_list),
            "avg_likes": round(avg),
            "weight": round(w, 3) if w else None,
            "has_weight": w is not None,
        })

    # Global average for comparison
    all_likes = []
    for ins in engagement:
        fields = ins.get("captured_data", {}).get("fields", {})
        l = fields.get("likes", 0)
        if l:
            all_likes.append(l)
    global_avg = round(sum(all_likes) / max(len(all_likes), 1))

    return {
        "funnel": [
            {"stage": "Tweets Analyzed", "count": total_analyzed, "filter": "Research engine (min_faves threshold)", "rate": None},
            {"stage": "High Performers", "count": total_insights, "filter": "50+ likes engagement threshold", "rate": round((1 - total_insights / max(total_analyzed, 1)) * 100, 1) if total_analyzed else 0},
            {"stage": "LLM Analyzed", "count": llm_analyzed, "filter": "phi4-mini structured extraction", "rate": round((1 - llm_analyzed / max(total_insights, 1)) * 100, 1) if total_insights else 0},
            {"stage": "Evolution Events", "count": len(evo_log), "filter": "Min 3 observations + 15% shift cap", "rate": round((1 - len(evo_log) / max(total_insights, 1)) * 100, 1) if total_insights else 0},
            {"stage": "High Confidence", "count": high_conf, "filter": "Confidence >= 0.7", "rate": round((1 - high_conf / max(len(evo_log), 1)) * 100, 1) if evo_log else 0},
            {"stage": "Passed MetaRalph", "count": len(promoted), "filter": "Quality score >= 4/10", "rate": round((1 - len(promoted) / max(high_conf, 1)) * 100, 1) if high_conf else 0},
        ],
        "event_types": dict(event_types.most_common()),
        "metaralph": {
            "attempted": high_conf,
            "passed": len(promoted),
            "filtered": filtered_count,
            "filter_rate": round(filtered_count / max(high_conf, 1) * 100, 1),
            "promoted_at": promoted,
        },
        "trigger_performance": trigger_perf,
        "strategy_performance": strategy_perf,
        "global_avg_likes": global_avg,
        "active_trigger_weights": len(trigger_weights),
        "active_strategy_weights": len(strategy_weights),
        "eidos": _get_eidos_stats(),
        "cognitive_x_domain": _count_x_domain_insights(),
    }


def _get_eidos_stats() -> dict:
    """Get EIDOS distillation stats for the filter funnel."""
    try:
        import sqlite3
        eidos_path = SPARK_DIR / "eidos.db"
        if not eidos_path.exists():
            return {"episodes": 0, "distillations": 0, "rate": 0}
        conn = sqlite3.connect(str(eidos_path))
        episodes = conn.execute("SELECT COUNT(*) FROM episodes").fetchone()[0]
        distillations = conn.execute("SELECT COUNT(*) FROM distillations").fetchone()[0]
        success = conn.execute("SELECT COUNT(*) FROM episodes WHERE outcome='success'").fetchone()[0]
        conn.close()
        return {
            "episodes": episodes,
            "distillations": distillations,
            "rate": round(distillations / max(episodes, 1) * 100, 1),
            "success_episodes": success,
        }
    except Exception:
        return {"episodes": 0, "distillations": 0, "rate": 0, "success_episodes": 0}


def _count_x_domain_insights() -> int:
    """Count X-domain tagged cognitive insights."""
    ci = read_json(SPARK_DIR / "cognitive_insights.json")
    count = 0
    for key, val in ci.items():
        if isinstance(val, dict) and "x_social" in str(val.get("context", "")):
            count += 1
    return count


@app.get("/api/gaps")
async def api_gaps():
    """System gap diagnosis — shows where Spark Intelligence needs improvement."""
    try:
        from lib.x_evolution import get_evolution
        evo = get_evolution()
        return evo.diagnose_gaps()
    except Exception as e:
        return {
            "overall_health": "unknown",
            "total_gaps": 0,
            "gaps": [],
            "system_health": {},
            "error": str(e),
            "core_integration": {
                "cognitive_learner": False,
                "meta_ralph": False,
                "advisor": False,
                "eidos": False,
            },
        }


@app.get("/api/evolution")
async def api_evolution():
    """Real-time evolution tracking — shows how Spark is changing from X interactions."""
    evo_log_path = SPARK_DIR / "x_evolution_log.jsonl"
    evo_state_path = SPARK_DIR / "x_evolution_state.json"

    # Read evolution events (most recent first)
    events = read_jsonl(evo_log_path, limit=200)
    events.reverse()

    # Read evolution state
    state = read_json(evo_state_path)
    weights = state.get("voice_weights", {})
    tracked = state.get("tracked_replies", {})

    # Reply outcome stats
    outcomes = [v for v in tracked.values() if v.get("outcome")]
    hits = sum(1 for o in outcomes if o["outcome"] == "hit")
    misses = sum(1 for o in outcomes if o["outcome"] == "miss")
    normals = sum(1 for o in outcomes if o["outcome"] == "normal")
    total_outcomes = hits + misses + normals

    # Event type breakdown
    event_types: dict[str, int] = {}
    for e in events:
        etype = e.get("event_type", "unknown")
        event_types[etype] = event_types.get(etype, 0) + 1

    # Current trigger weights (evolved)
    trigger_weights = weights.get("triggers", {})
    boosted = sorted(
        [{"trigger": t, "weight": round(w, 2)} for t, w in trigger_weights.items() if w > 1.05],
        key=lambda x: -x["weight"],
    )
    reduced = sorted(
        [{"trigger": t, "weight": round(w, 2)} for t, w in trigger_weights.items() if w < 0.95],
        key=lambda x: x["weight"],
    )

    # Strategy weights
    strategy_weights = weights.get("strategies", {})
    top_strategies = sorted(
        [{"strategy": s, "weight": round(w, 2)} for s, w in strategy_weights.items()],
        key=lambda x: -x["weight"],
    )[:5]

    # Recent evolution timeline (last 20 events for display)
    timeline = []
    for e in events[:20]:
        timeline.append({
            "type": e.get("event_type", ""),
            "description": e.get("description", ""),
            "confidence": e.get("confidence", 0),
            "timestamp": e.get("timestamp", ""),
        })

    return {
        "total_evolutions": len(events),
        "evolution_types": event_types,
        "reply_tracking": {
            "total_tracked": len(tracked),
            "outcomes_measured": total_outcomes,
            "hits": hits,
            "misses": misses,
            "normals": normals,
            "hit_rate": round(hits / max(total_outcomes, 1), 2),
        },
        "voice_evolution": {
            "boosted_triggers": boosted,
            "reduced_triggers": reduced,
            "top_strategies": top_strategies,
        },
        "adopted_patterns": state.get("adopted_patterns", []),
        "evolved_interests": state.get("evolved_topic_interests", []),
        "timeline": timeline,
        "last_evolution": state.get("last_evolution"),
        "is_evolving": len(events) > 0,
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
