#!/usr/bin/env python3
"""
Spark Daily Trend Research - Automated X/Twitter Intelligence Gathering

This script:
1. Searches X for trends in AI agents, vibe coding, ecosystems
2. Extracts insights and stores them in Spark cognitive learner
3. Generates content recommendations based on what's trending
4. Updates the dashboard data

Run daily via cron/scheduler or manually:
    python scripts/daily_trend_research.py

Live mode (uses X API via bearer token):
    python scripts/daily_trend_research.py --live

By default, live mode runs only high-priority topics (to reduce rate/latency).
"""

import sys
import json
import asyncio
import time
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Optional

# Add lib to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from lib.cognitive_learner import get_cognitive_learner, CognitiveCategory
from lib.x_research_events import process_x_research_through_chips, bulk_research_to_events
from lib.chip_merger import merge_chip_insights


# ============================================
# RESEARCH TOPICS - What to track daily
# ============================================

RESEARCH_TOPICS = {
    "vibe_coding": {
        "queries": [
            "vibe coding Claude AI",
            "Claude Code ship fast",
            "AI coding productivity",
        ],
        "category": CognitiveCategory.CONTEXT,
        "priority": "high"
    },
    "openclaw_moltbook": {
        "queries": [
            "OpenClaw Claude ecosystem",
            "Moltbook AI agent",
            "agent social network",
        ],
        "category": CognitiveCategory.CONTEXT,
        "priority": "high"
    },
    "base_ecosystem": {
        "queries": [
            "BASE chain AI agent token",
            "CLAWNCH agent launchpad",
        ],
        "category": CognitiveCategory.CONTEXT,
        "priority": "medium"
    },
    "solana_ai": {
        "queries": [
            "Solana AI agent meme token",
            "AI memecoin Solana launch",
        ],
        "category": CognitiveCategory.CONTEXT,
        "priority": "medium"
    },
    "bittensor": {
        "queries": [
            "Bittensor TAO subnet AI",
            "decentralized AI compute",
        ],
        "category": CognitiveCategory.CONTEXT,
        "priority": "medium"
    },
    "viral_patterns": {
        "queries": [
            "AI viral tweet engagement",
            "Claude tweet viral",
        ],
        "category": CognitiveCategory.REASONING,
        "priority": "high"
    },
}

# Content recommendation prompts based on trends
CONTENT_ANGLES = {
    "educational": "How-to guides and tutorials get high bookmarks",
    "holy_shit_moment": "AI doing unexpected things drives massive engagement",
    "tool_comparison": "Stack comparisons and tool lists get saved",
    "ecosystem_update": "Ecosystem news with specific numbers performs well",
    "contrarian": "Challenging conventional wisdom sparks discussion",
    "builder_story": "First-person building narratives resonate",
}


# Reply pattern topics to study for ConvoIQ
REPLY_STUDY_TOPICS = {
    "high_engagement_replies": {
        "queries": [
            "AI agent reply viral engagement",
            "best reply thread engagement",
        ],
        "priority": "medium",
    },
    "conversation_hooks": {
        "queries": [
            "conversation starter tweet hook",
            "quote tweet engagement strategy",
        ],
        "priority": "medium",
    },
}


def extract_insights_from_search(search_results: List[Dict], topic: str) -> List[Dict]:
    """Extract actionable insights from search results."""
    insights = []

    for tweet in search_results:
        text = tweet.get('text', '')
        likes = tweet.get('likes', 0)
        retweets = tweet.get('retweets', 0)

        # Only process tweets with some engagement
        if likes < 5 and retweets < 2:
            continue

        # Extract key patterns
        insight = {
            'topic': topic,
            'text': text[:500],
            'engagement': likes + retweets * 2,
            'timestamp': tweet.get('created_at'),
        }

        # Detect content type
        if any(word in text.lower() for word in ['how to', 'guide', 'tutorial', 'thread']):
            insight['content_type'] = 'educational'
        elif any(word in text.lower() for word in ['holy shit', 'insane', 'wtf', 'crazy']):
            insight['content_type'] = 'holy_shit_moment'
        elif any(word in text.lower() for word in ['vs', 'compared', 'better than', 'stack']):
            insight['content_type'] = 'comparison'
        elif any(word in text.lower() for word in ['launched', 'announced', 'new', 'just']):
            insight['content_type'] = 'news'
        else:
            insight['content_type'] = 'general'

        insights.append(insight)

    return insights


def generate_content_recommendations(insights: List[Dict]) -> List[Dict]:
    """Generate content recommendations based on trending insights."""
    recommendations = []

    # Group by topic
    by_topic = {}
    for insight in insights:
        topic = insight['topic']
        if topic not in by_topic:
            by_topic[topic] = []
        by_topic[topic].append(insight)

    # Generate recommendations
    for topic, topic_insights in by_topic.items():
        if not topic_insights:
            continue

        # Sort by engagement
        sorted_insights = sorted(topic_insights, key=lambda x: x['engagement'], reverse=True)
        top_insight = sorted_insights[0]

        # Determine best angle
        content_types = [i['content_type'] for i in sorted_insights[:5]]
        most_common = max(set(content_types), key=content_types.count)

        recommendations.append({
            'topic': topic,
            'suggested_angle': CONTENT_ANGLES.get(most_common, CONTENT_ANGLES['educational']),
            'trending_example': top_insight['text'][:200],
            'engagement_signal': top_insight['engagement'],
            'content_type': most_common,
            'priority': 'high' if top_insight['engagement'] > 100 else 'medium',
        })

    return sorted(recommendations, key=lambda x: x['engagement_signal'], reverse=True)


def store_daily_report(insights: List[Dict], recommendations: List[Dict]):
    """Store daily research report for dashboard."""
    report_dir = Path.home() / '.spark' / 'research_reports'
    report_dir.mkdir(parents=True, exist_ok=True)

    today = datetime.now().strftime('%Y-%m-%d')

    report = {
        'date': today,
        'generated_at': datetime.now().isoformat(),
        'insights_count': len(insights),
        'topics_covered': list(set(i['topic'] for i in insights)),
        'top_recommendations': recommendations[:5],
        'all_insights': insights,
        'content_ideas': [
            {
                'idea': r['suggested_angle'],
                'topic': r['topic'],
                'example': r['trending_example'],
                'priority': r['priority'],
            }
            for r in recommendations[:10]
        ]
    }

    # Save daily report
    report_file = report_dir / f'report_{today}.json'
    report_file.write_text(json.dumps(report, indent=2))

    # Update latest report symlink
    latest_file = report_dir / 'latest.json'
    latest_file.write_text(json.dumps(report, indent=2))

    print(f"Report saved to: {report_file}")
    return report


def inject_to_spark(insights: List[Dict]):
    """
    Process insights through the proper Spark learning pipeline.

    NEW FLOW (correct):
    1. Convert insights to X research events
    2. Process through chip system (market-intel chip)
    3. Chip captures domain-specific observations
    4. Merge chip insights into cognitive system
    5. Predictions generated from exposures
    6. Validation loop tests predictions against outcomes

    This is TRUE Spark evolution, not just storage.
    """
    # Only process high-engagement insights
    top_insights = sorted(insights, key=lambda x: x['engagement'], reverse=True)[:20]

    if not top_insights:
        print("No insights to process")
        return 0

    # Convert to research format for event pipeline
    research_results = []
    for insight in top_insights:
        research_results.append({
            "query": insight.get('topic', ''),
            "text": insight.get('text', ''),
            "engagement": insight.get('engagement', 0),
            "ecosystem": insight.get('topic', '').replace('_', ' '),
            "sentiment": "bullish" if insight.get('engagement', 0) > 50 else "neutral",
        })

    # Process through chip system
    print(f"Processing {len(research_results)} insights through chip system...")
    chip_stats = process_x_research_through_chips(research_results)
    print(f"  - Events created: {chip_stats['events_created']}")
    print(f"  - Chip insights captured: {chip_stats['insights_captured']}")
    print(f"  - Chips used: {chip_stats['chips_used']}")

    # Merge chip insights into cognitive system
    print("\nMerging chip insights into cognitive pipeline...")
    merge_stats = merge_chip_insights(min_confidence=0.6, limit=50)
    print(f"  - Processed: {merge_stats['processed']}")
    print(f"  - Merged: {merge_stats['merged']}")
    print(f"  - By chip: {merge_stats['by_chip']}")

    # Also do direct injection for high-value insights (as backup)
    # This ensures predictions are generated even if chip processing fails
    learner = get_cognitive_learner()
    direct_injected = 0
    for insight in top_insights[:5]:  # Top 5 only for direct injection
        topic_config = RESEARCH_TOPICS.get(insight['topic'], {})
        category = topic_config.get('category', CognitiveCategory.CONTEXT)

        learner.add_insight(
            category=category,
            insight=f"[{insight['topic']}] {insight['text'][:200]}",
            context=f"X research {datetime.now().strftime('%Y-%m-%d')} - engagement: {insight['engagement']}",
            confidence=min(0.95, 0.6 + (insight['engagement'] / 500)),
            record_exposure=True,  # This creates exposure → predictions
        )
        direct_injected += 1

    print(f"\nDirect injected (top 5): {direct_injected}")
    print(f"Total processed: {len(top_insights)}")

    return len(top_insights)


def scan_niche_accounts(search_results: List[Dict]) -> int:
    """Scan search results for niche accounts to track.

    Feeds discovered accounts through the NicheMapper to build
    the relationship network.

    Args:
        search_results: Tweets with author info

    Returns:
        Number of accounts discovered
    """
    try:
        from lib.niche_mapper import get_niche_mapper
    except ImportError:
        print("NicheNet not available, skipping niche scan")
        return 0

    mapper = get_niche_mapper()
    discovered = 0

    seen = set()
    for tweet in search_results:
        author = tweet.get("author", "")
        if not author or author in seen:
            continue
        seen.add(author)

        engagement = tweet.get("likes", 0) + tweet.get("retweets", 0)
        if engagement < 5:
            continue

        # Determine relevance from engagement and content
        relevance = min(0.9, 0.3 + engagement / 200)
        topics = []
        text = tweet.get("text", "").lower()
        for keyword in ["ai", "agent", "coding", "build", "deploy", "token"]:
            if keyword in text:
                topics.append(keyword)

        mapper.discover_account(
            handle=author,
            topics=topics,
            relevance=relevance,
            discovered_via="daily_trend_research",
        )
        discovered += 1

    if discovered:
        print(f"NicheNet: discovered {discovered} accounts from trend research")

    return discovered


def study_reply_patterns(search_results: List[Dict]) -> int:
    """Study high-engagement replies for ConvoIQ conversation DNA.

    Feeds reply patterns through the ConvoIQ analyzer to extract
    conversation DNA and learn what makes replies land.

    Args:
        search_results: Tweets with engagement data

    Returns:
        Number of patterns extracted
    """
    try:
        from lib.convo_analyzer import get_convo_analyzer
    except ImportError:
        print("ConvoIQ not available, skipping reply study")
        return 0

    analyzer = get_convo_analyzer()
    patterns_found = 0

    for tweet in search_results:
        text = tweet.get("text", "")
        likes = tweet.get("likes", 0)
        replies = tweet.get("replies", 0)
        retweets = tweet.get("retweets", 0)

        # Only study tweets with meaningful engagement
        if likes < 10 and replies < 3:
            continue

        dna = analyzer.study_reply(
            reply_text=text,
            engagement={"likes": likes, "replies": replies, "retweets": retweets},
            parent_text=tweet.get("parent_text", ""),
            topic_tags=tweet.get("tags", []),
        )
        if dna:
            patterns_found += 1

    if patterns_found:
        print(f"ConvoIQ: extracted {patterns_found} conversation DNA patterns")

    return patterns_found


def run_research_with_mcp():
    """Legacy: print structure for manual mode.

    Kept for backwards compatibility.
    """
    print("""
    =====================================================
    DAILY TREND RESEARCH SYSTEM
    =====================================================

    Modes:

    1) LIVE MODE:
       python scripts/daily_trend_research.py --live

       Uses X API (bearer token) if available to fetch recent tweets,
       then extracts insights + injects into Spark.

    2) MANUAL MODE:
       Provide search results data yourself:
       python scripts/daily_trend_research.py --manual

    =====================================================
    """)

    return {
        'status': 'ready',
        'topics': list(RESEARCH_TOPICS.keys()),
        'queries': [q for t in RESEARCH_TOPICS.values() for q in t['queries']],
    }


def run_live_mode(
    *,
    topics: Optional[List[str]] = None,
    high_only: bool = True,
    per_query: int = 12,
) -> Dict[str, Any]:
    """Run live X searches and process results through Spark pipeline."""
    from scripts._x_search import search_recent

    selected = topics
    if not selected:
        if high_only:
            selected = [k for k, v in RESEARCH_TOPICS.items() if v.get('priority') == 'high']
        else:
            selected = list(RESEARCH_TOPICS.keys())

    search_data: Dict[str, List[Dict]] = {}
    total_tweets = 0

    for topic in selected:
        cfg = RESEARCH_TOPICS.get(topic)
        if not cfg:
            continue
        topic_results: List[Dict] = []
        for q in cfg.get('queries', []):
            try:
                rows = search_recent(query=q, max_results=per_query)
            except Exception as e:
                print(f"LIVE search failed for '{q}': {e}")
                rows = []
            topic_results.extend(rows)

        # Deduplicate by text
        seen = set()
        deduped: List[Dict] = []
        for r in topic_results:
            t = (r.get('text') or '').strip()
            key = t[:280]
            if not key or key in seen:
                continue
            seen.add(key)
            deduped.append(r)

        search_data[topic] = deduped
        total_tweets += len(deduped)
        print(f"LIVE: {topic}: {len(deduped)} tweets")

    stats = manual_mode_with_data(search_data)
    stats['live_topics'] = selected
    stats['live_tweets_total'] = total_tweets
    return stats


def manual_mode_with_data(search_data: Dict[str, List[Dict]]):
    """Process manually provided search data."""
    all_insights = []

    for topic, results in search_data.items():
        insights = extract_insights_from_search(results, topic)
        all_insights.extend(insights)
        print(f"Extracted {len(insights)} insights from {topic}")

    # Generate recommendations
    recommendations = generate_content_recommendations(all_insights)
    print(f"\nGenerated {len(recommendations)} content recommendations")

    # Store report
    report = store_daily_report(all_insights, recommendations)

    # Inject to Spark
    injected = inject_to_spark(all_insights)

    return {
        'insights_extracted': len(all_insights),
        'recommendations': len(recommendations),
        'injected_to_spark': injected,
        'report': report,
    }


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='Spark Daily Trend Research')
    parser.add_argument('--manual', action='store_true', help='Run in manual mode (provide your own search data)')
    parser.add_argument('--live', action='store_true', help='Run live X searches (requires TWITTER_BEARER_TOKEN)')
    parser.add_argument('--all-topics', action='store_true', help='In live mode: include medium-priority topics too')
    parser.add_argument('--topics', nargs='*', default=None, help='In live mode: explicit topic keys to run')
    parser.add_argument('--per-query', type=int, default=12, help='In live mode: max tweets per query (10-100)')
    parser.add_argument('--show-topics', action='store_true', help='Show research topics')
    args = parser.parse_args()

    if args.show_topics:
        print("Research Topics:")
        for topic, config in RESEARCH_TOPICS.items():
            print(f"\n{topic} (priority: {config['priority']})")
            for q in config['queries']:
                print(f"  - {q}")
        raise SystemExit(0)

    if args.live:
        stats = run_live_mode(
            topics=args.topics,
            high_only=not bool(args.all_topics),
            per_query=int(args.per_query),
        )
        print(json.dumps(stats, indent=2))
        raise SystemExit(0)

    result = run_research_with_mcp()
    print(json.dumps(result, indent=2))
