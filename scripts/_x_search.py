"""Minimal X (Twitter) recent-search helper.

Uses tweepy Client (bearer token) to fetch recent tweets.

We keep this in scripts/ to avoid coupling core libs to external API deps.
"""

from __future__ import annotations

import os
import time
from pathlib import Path
from typing import Any, Dict, List, Optional


def _load_bearer_token() -> Optional[str]:
    # Prefer explicit env var.
    token = os.getenv("TWITTER_BEARER_TOKEN") or os.getenv("X_BEARER_TOKEN")
    if token:
        return token.strip()

    # Fallback: local MCP .env (if present). Do NOT print its contents.
    env_path = Path(__file__).parent.parent / "mcp-servers" / "x-twitter-mcp" / ".env"
    if env_path.exists():
        try:
            for line in env_path.read_text(encoding="utf-8").splitlines():
                if line.strip().startswith("TWITTER_BEARER_TOKEN="):
                    return line.split("=", 1)[1].strip().strip('"').strip("'")
        except Exception:
            return None
    return None


def search_recent(
    *,
    query: str,
    max_results: int = 10,
    sleep_s: float = 0.8,
) -> List[Dict[str, Any]]:
    """Search recent tweets and return a normalized list.

    Output schema is compatible with extract_insights_from_search():
      {text, likes, retweets, replies, created_at, author}
    """
    token = _load_bearer_token()
    if not token:
        raise RuntimeError("Missing TWITTER_BEARER_TOKEN (env or mcp-servers/x-twitter-mcp/.env)")

    try:
        import tweepy  # type: ignore
    except Exception as exc:
        raise RuntimeError(f"tweepy not available: {exc}")

    client = tweepy.Client(bearer_token=token, wait_on_rate_limit=True)

    # Keep it conservative: no retweets, English-ish queries often do better.
    q = (query or "").strip()
    if not q:
        return []

    resp = client.search_recent_tweets(
        query=q + " -is:retweet",
        max_results=max(10, min(100, int(max_results))),
        tweet_fields=["created_at", "public_metrics", "lang", "author_id"],
        expansions=["author_id"],
        user_fields=["username"],
    )

    users_by_id = {}
    try:
        includes = getattr(resp, "includes", None) or {}
        users = includes.get("users") or []
        for u in users:
            users_by_id[str(getattr(u, "id", ""))] = str(getattr(u, "username", ""))
    except Exception:
        pass

    out: List[Dict[str, Any]] = []
    tweets = getattr(resp, "data", None) or []
    for t in tweets:
        text = str(getattr(t, "text", "") or "")
        metrics = getattr(t, "public_metrics", None) or {}
        author_id = str(getattr(t, "author_id", "") or "")
        out.append(
            {
                "text": text,
                "likes": int(metrics.get("like_count", 0) or 0),
                "retweets": int(metrics.get("retweet_count", 0) or 0),
                "replies": int(metrics.get("reply_count", 0) or 0),
                "created_at": str(getattr(t, "created_at", "") or ""),
                "author": users_by_id.get(author_id, ""),
            }
        )

    if sleep_s and sleep_s > 0:
        time.sleep(float(sleep_s))

    return out
