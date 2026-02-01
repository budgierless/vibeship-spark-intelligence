"""
X Research Event Pipeline - Convert X/Twitter research into Spark events.

Instead of directly injecting insights, this module creates EVENTS that
flow through the chip system, allowing the market-intel chip to:
1. Observe the raw research data
2. Extract structured domain insights
3. Store chip insights that can be validated
4. Eventually promote high-confidence insights

This is the CORRECT way to evolve Spark from X research.
"""

import json
import time
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime

from lib.queue import EventType


RESEARCH_EVENTS_FILE = Path.home() / ".spark" / "x_research_events.jsonl"


def create_x_research_event(
    query: str,
    tweet_text: str,
    author: str = "",
    engagement: int = 0,
    ecosystem: str = "",
    sentiment: str = "neutral",
    source_url: str = "",
    metadata: Optional[Dict] = None,
) -> Dict[str, Any]:
    """
    Create a research event that the chip system can process.

    Args:
        query: The search query used
        tweet_text: The tweet content
        author: Tweet author handle
        engagement: Total engagement (likes + retweets)
        ecosystem: Which ecosystem (moltbook, openclaw, base, solana, bittensor)
        sentiment: bullish, bearish, neutral
        source_url: Link to the tweet
        metadata: Any additional metadata

    Returns:
        Event dict ready for chip processing
    """
    return {
        "event_type": "x_research",
        "tool_name": "XResearch",
        "timestamp": time.time(),
        "session_id": f"research_{datetime.now().strftime('%Y%m%d')}",
        "data": {
            "query": query,
            "content": tweet_text,
            "author": author,
            "engagement": engagement,
            "ecosystem": ecosystem,
            "sentiment": sentiment,
            "source_url": source_url,
            **(metadata or {}),
        },
        "input": {
            "query": query,
            "content": tweet_text,
        },
    }


def store_research_events(events: List[Dict[str, Any]]) -> int:
    """Store research events for later processing."""
    if not events:
        return 0

    RESEARCH_EVENTS_FILE.parent.mkdir(parents=True, exist_ok=True)
    with RESEARCH_EVENTS_FILE.open("a", encoding="utf-8") as f:
        for event in events:
            f.write(json.dumps(event, ensure_ascii=False) + "\n")

    return len(events)


def read_pending_research_events(limit: int = 100) -> List[Dict[str, Any]]:
    """Read pending research events for chip processing."""
    if not RESEARCH_EVENTS_FILE.exists():
        return []

    try:
        lines = RESEARCH_EVENTS_FILE.read_text().splitlines()
        events = []
        for line in lines[-limit:]:
            if line.strip():
                events.append(json.loads(line))
        return events
    except Exception:
        return []


def process_x_research_through_chips(
    research_results: List[Dict[str, Any]],
    project_path: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Process X research results through the chip system.

    This is the main entry point for X research → Spark learning.

    Args:
        research_results: List of research results with keys:
            - query: Search query
            - text: Tweet content
            - author: Author handle
            - engagement: Engagement count
            - ecosystem: Which ecosystem
        project_path: Optional project path for chip activation

    Returns:
        Stats about processing
    """
    from lib.chips.runtime import get_runtime

    stats = {
        "events_created": 0,
        "insights_captured": 0,
        "chips_used": set(),
    }

    runtime = get_runtime()

    for result in research_results:
        # Create event from research result
        event = create_x_research_event(
            query=result.get("query", ""),
            tweet_text=result.get("text", ""),
            author=result.get("author", ""),
            engagement=result.get("engagement", 0),
            ecosystem=result.get("ecosystem", ""),
            sentiment=result.get("sentiment", "neutral"),
            source_url=result.get("url", ""),
        )

        stats["events_created"] += 1

        # Process through chip system
        insights = runtime.process_event(event, project_path)
        stats["insights_captured"] += len(insights)

        for insight in insights:
            stats["chips_used"].add(insight.chip_id)

    # Store events for audit trail (map 'text' to 'tweet_text' if needed)
    events = []
    for r in research_results:
        text = r.get("text") or r.get("tweet_text", "")
        if text:
            events.append(create_x_research_event(
                query=r.get("query", ""),
                tweet_text=text,
                author=r.get("author", ""),
                engagement=r.get("engagement", 0),
                ecosystem=r.get("ecosystem", ""),
                sentiment=r.get("sentiment", "neutral"),
                source_url=r.get("url", ""),
            ))
    store_research_events(events)

    stats["chips_used"] = list(stats["chips_used"])
    return stats


def bulk_research_to_events(
    tweets: List[Dict[str, Any]],
    ecosystem: str,
    query: str = "",
) -> List[Dict[str, Any]]:
    """
    Convert a batch of tweets to research events.

    Args:
        tweets: List of tweet dicts (from MCP or API)
        ecosystem: Which ecosystem these relate to
        query: The search query used

    Returns:
        List of event dicts ready for chip processing
    """
    events = []

    for tweet in tweets:
        # Handle different tweet formats
        text = tweet.get("text") or tweet.get("content") or ""
        author = tweet.get("author") or tweet.get("user", {}).get("screen_name", "")
        likes = tweet.get("likes") or tweet.get("favorite_count", 0)
        retweets = tweet.get("retweets") or tweet.get("retweet_count", 0)
        engagement = likes + retweets

        # Determine sentiment from text
        sentiment = "neutral"
        text_lower = text.lower()
        if any(w in text_lower for w in ["bullish", "moon", "huge", "amazing", "love"]):
            sentiment = "bullish"
        elif any(w in text_lower for w in ["bearish", "dump", "scam", "terrible", "hate"]):
            sentiment = "bearish"

        events.append(create_x_research_event(
            query=query,
            tweet_text=text,
            author=author,
            engagement=engagement,
            ecosystem=ecosystem,
            sentiment=sentiment,
        ))

    return events
