"""
Spark X Research Engine - Autonomous intelligence gathering from X/Twitter.

Searches topics, studies high-performing content, tracks accounts,
detects trends, and stores everything as chip insights for the
Spark Neural dashboard.

Usage:
    from lib.x_research import SparkResearcher
    researcher = SparkResearcher()
    researcher.run_session()
"""

from __future__ import annotations

import json
import time
import re
from datetime import datetime, timezone, timedelta
from pathlib import Path

import tweepy
from dotenv import dotenv_values


# ── Paths ────────────────────────────────────────────────────
SPARK_DIR = Path.home() / ".spark"
CHIP_INSIGHTS_DIR = SPARK_DIR / "chip_insights"
WATCHLIST_PATH = SPARK_DIR / "x_watchlist.json"
RESEARCH_STATE_PATH = SPARK_DIR / "x_research_state.json"
ENV_PATH = Path(__file__).resolve().parent.parent / "mcp-servers" / "x-twitter-mcp" / ".env"

# ── Emotional trigger keywords (from social-convo chip) ──────
TRIGGER_KEYWORDS = {
    "curiosity_gap": ["nobody tells you", "here's what", "the thing about", "turns out", "actually", "secret", "hidden"],
    "surprise": ["unexpected", "counter-intuitive", "wrong about", "changed my mind", "plot twist", "didn't expect"],
    "validation": ["you're right", "exactly this", "finally someone", "not just me", "we all know", "this is it"],
    "vulnerability": ["I was wrong", "I don't know", "failed", "mistake", "struggling", "honestly", "scared"],
    "aspiration": ["imagine", "what if", "possible", "could be", "path to", "how I went from", "future"],
    "contrast": ["vs", "instead", "but actually", "common advice", "everyone thinks", "real difference"],
    "identity_signal": ["real builders", "if you know", "we don't", "our kind", "unlike most", "builders know"],
}

# ── Search topics ────────────────────────────────────────────
DEFAULT_TOPICS = [
    {"query": '"vibe coding" OR vibecoding', "name": "Vibe Coding", "category": "core"},
    {"query": '"claude code"', "name": "Claude Code", "category": "core"},
    {"query": '"AI agents" coding OR building', "name": "AI Agents", "category": "core"},
    {"query": '"self-improving AI" OR "self improving AI"', "name": "Self-Improving AI", "category": "core"},
    {"query": "AGI -spam -giveaway", "name": "AGI", "category": "frontier"},
    {"query": '"building in public" AI OR coding', "name": "Building in Public", "category": "culture"},
    {"query": '"agentic" coding OR systems OR framework', "name": "Agentic Systems", "category": "technical"},
    {"query": '"machine intelligence"', "name": "Machine Intelligence", "category": "frontier"},
    {"query": '"learning in public" AI OR code', "name": "Learning in Public", "category": "culture"},
    {"query": "cursor OR windsurf OR copilot AI coding", "name": "AI Coding Tools", "category": "technical"},
    {"query": '"prompt engineering" -course -free', "name": "Prompt Engineering", "category": "technical"},
    {"query": '"open source AI" model', "name": "Open Source AI", "category": "frontier"},
]


class SparkResearcher:
    """Autonomous X research engine for Spark Intelligence."""

    ENGAGEMENT_MIN = 50       # Minimum likes for "high performer"
    SEARCH_DELAY = 2.5        # Seconds between API searches
    LOOKUP_DELAY = 1.0        # Seconds between lookups
    MAX_RESULTS = 50          # Results per search query
    TWEETS_PER_ACCOUNT = 10   # Recent tweets to check per watched account

    def __init__(self, verbose: bool = True):
        self.verbose = verbose
        self.creds = self._load_creds()
        self.client = self._get_client()
        self.state = self._load_state()
        self.watchlist = self._load_watchlist()
        self.session_insights: list[dict] = []
        self.session_accounts_discovered: list[dict] = []
        self.session_start = datetime.now(timezone.utc)

    # ── Setup ────────────────────────────────────────────────

    def _load_creds(self) -> dict:
        if not ENV_PATH.exists():
            raise FileNotFoundError(f"No .env at {ENV_PATH}")
        creds = dotenv_values(ENV_PATH)
        for key in ["TWITTER_BEARER_TOKEN"]:
            if not creds.get(key):
                raise ValueError(f"Missing {key} in .env")
        return creds

    def _get_client(self) -> tweepy.Client:
        """Bearer token client for read operations."""
        return tweepy.Client(
            bearer_token=self.creds["TWITTER_BEARER_TOKEN"],
            wait_on_rate_limit=True,
        )

    def _load_state(self) -> dict:
        if RESEARCH_STATE_PATH.exists():
            try:
                return json.loads(RESEARCH_STATE_PATH.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                pass
        return {
            "sessions_run": 0,
            "total_tweets_analyzed": 0,
            "total_insights_stored": 0,
            "topics": DEFAULT_TOPICS,
            "discovered_topics": [],
            "research_intents": [
                "Find what makes vibe coding tweets go viral",
                "Identify top accounts in the AI agent space",
                "Learn which emotional triggers drive replies vs likes",
                "Discover emerging topics before they peak",
            ],
            "last_session": None,
            "last_since_ids": {},
        }

    def _load_watchlist(self) -> dict:
        if WATCHLIST_PATH.exists():
            try:
                return json.loads(WATCHLIST_PATH.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                pass
        return {"accounts": [], "updated_at": None}

    def _save_state(self):
        RESEARCH_STATE_PATH.write_text(
            json.dumps(self.state, indent=2, default=str),
            encoding="utf-8",
        )

    def _save_watchlist(self):
        self.watchlist["updated_at"] = datetime.now(timezone.utc).isoformat()
        WATCHLIST_PATH.write_text(
            json.dumps(self.watchlist, indent=2, default=str),
            encoding="utf-8",
        )

    def _log(self, msg: str):
        if self.verbose:
            print(f"  [{datetime.now().strftime('%H:%M:%S')}] {msg}")

    # ── Core: Store insights ─────────────────────────────────

    def store_insight(self, chip_id: str, observer: str, fields: dict, meta: dict | None = None):
        """Write an insight to chip JSONL file."""
        CHIP_INSIGHTS_DIR.mkdir(parents=True, exist_ok=True)
        insight = {
            "chip_id": chip_id,
            "observer": observer,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "captured_data": {"fields": fields},
        }
        if meta:
            insight["meta"] = meta

        path = CHIP_INSIGHTS_DIR / f"{chip_id}.jsonl"
        with open(path, "a", encoding="utf-8") as f:
            f.write(json.dumps(insight, default=str) + "\n")

        self.session_insights.append(insight)

    # ── Phase 1: Topic Search ────────────────────────────────

    def search_topics(self) -> list[dict]:
        """Search all tracked topics and find high-performing content."""
        self._log("PHASE 1: Topic Search")
        all_topics = self.state.get("topics", DEFAULT_TOPICS) + self.state.get("discovered_topics", [])
        high_performers = []
        topic_stats = {}

        for topic in all_topics:
            query = topic["query"] + " -is:retweet lang:en"
            name = topic["name"]
            self._log(f"  Searching: {name}")

            try:
                since_id = self.state.get("last_since_ids", {}).get(name)
                result = self.client.search_recent_tweets(
                    query=query,
                    max_results=min(self.MAX_RESULTS, 100),
                    since_id=since_id,
                    tweet_fields=["public_metrics", "created_at", "author_id", "conversation_id"],
                    user_fields=["username", "name", "public_metrics", "description"],
                    expansions=["author_id"],
                )
            except tweepy.errors.TooManyRequests:
                self._log(f"    Rate limited, skipping {name}")
                time.sleep(15)
                continue
            except tweepy.errors.TwitterServerError:
                self._log(f"    Server error, skipping {name}")
                continue
            except Exception as e:
                self._log(f"    Error: {type(e).__name__}: {str(e)[:100]}")
                continue

            tweets = result.data or []
            users = {u.id: u for u in (result.includes or {}).get("users", [])}

            # Track newest tweet ID for next run
            if tweets:
                newest_id = max(t.id for t in tweets)
                self.state.setdefault("last_since_ids", {})[name] = str(newest_id)

            # Analyze each tweet
            topic_total = 0
            topic_high = 0
            for tweet in tweets:
                topic_total += 1
                metrics = tweet.public_metrics or {}
                likes = metrics.get("like_count", 0)
                replies = metrics.get("reply_count", 0)
                retweets = metrics.get("retweet_count", 0)
                total_engagement = likes + replies + retweets

                author = users.get(tweet.author_id)
                author_handle = f"@{author.username}" if author else "unknown"
                author_followers = (author.public_metrics or {}).get("followers_count", 0) if author else 0

                # Analyze emotional triggers in content
                triggers_found = self._detect_triggers(tweet.text)

                # Store every tweet as a basic observation
                self.store_insight("x_social", "trend_observed", {
                    "topic": name,
                    "category": topic.get("category", "unknown"),
                    "tweet_text": tweet.text[:200],
                    "likes": likes,
                    "replies": replies,
                    "retweets": retweets,
                    "total_engagement": total_engagement,
                    "user_handle": author_handle,
                    "user_followers": author_followers,
                    "emotional_triggers": triggers_found,
                    "posted_at": tweet.created_at.isoformat() if tweet.created_at else None,
                })

                # High performer analysis
                if likes >= self.ENGAGEMENT_MIN:
                    topic_high += 1
                    engagement_rate = round(likes / max(author_followers, 1) * 100, 2)

                    analysis = {
                        "tweet_id": str(tweet.id),
                        "topic": name,
                        "content": tweet.text[:280],
                        "likes": likes,
                        "replies": replies,
                        "retweets": retweets,
                        "engagement_rate": engagement_rate,
                        "user_handle": author_handle,
                        "user_followers": author_followers,
                        "emotional_triggers": triggers_found,
                        "has_question": "?" in tweet.text,
                        "has_link": "http" in tweet.text,
                        "length": len(tweet.text),
                        "posted_at": tweet.created_at.isoformat() if tweet.created_at else None,
                    }
                    high_performers.append(analysis)

                    # Store as high-engagement insight
                    self.store_insight("engagement-pulse", "high_performer_detected", analysis)

                    # Check if author should be on the watchlist
                    if author and author_followers >= 500:
                        self._maybe_add_to_watchlist(author, name, total_engagement)

            topic_stats[name] = {"total": topic_total, "high_performers": topic_high}
            self._log(f"    Found {topic_total} tweets, {topic_high} high performers")
            time.sleep(self.SEARCH_DELAY)

        # Store topic stats as a session summary
        self.store_insight("x_social", "topic_cycle", {
            "stats": topic_stats,
            "total_searched": sum(s["total"] for s in topic_stats.values()),
            "total_high_performers": sum(s["high_performers"] for s in topic_stats.values()),
            "session_time": self.session_start.isoformat(),
        })

        self._log(f"  Topic search complete: {len(high_performers)} high performers found")
        return high_performers

    # ── Phase 2: Account Study ───────────────────────────────

    def study_accounts(self) -> list[dict]:
        """Study watchlist accounts' recent activity."""
        self._log("PHASE 2: Account Study")
        accounts = self.watchlist.get("accounts", [])
        if not accounts:
            self._log("  No accounts on watchlist yet, skipping")
            return []

        account_insights = []
        # Study up to 10 accounts per session to stay within rate limits
        study_batch = sorted(accounts, key=lambda a: a.get("priority", 0), reverse=True)[:10]

        for account in study_batch:
            handle = account.get("handle", "").lstrip("@")
            if not handle:
                continue

            self._log(f"  Studying @{handle}")

            try:
                # Get user info
                user_result = self.client.get_user(
                    username=handle,
                    user_fields=["public_metrics", "description", "created_at"],
                )
                if not user_result.data:
                    self._log(f"    User not found: @{handle}")
                    continue

                user = user_result.data
                user_id = user.id

                time.sleep(self.LOOKUP_DELAY)

                # Get recent tweets
                tweets_result = self.client.get_users_tweets(
                    id=user_id,
                    max_results=self.TWEETS_PER_ACCOUNT,
                    tweet_fields=["public_metrics", "created_at"],
                    exclude=["retweets"],
                )
            except tweepy.errors.TooManyRequests:
                self._log(f"    Rate limited, stopping account study")
                break
            except Exception as e:
                self._log(f"    Error studying @{handle}: {str(e)[:80]}")
                time.sleep(self.LOOKUP_DELAY)
                continue

            tweets = tweets_result.data or []
            if not tweets:
                continue

            # Analyze their recent performance
            total_likes = 0
            total_replies = 0
            hits = []  # tweets that significantly outperformed
            misses = []

            avg_likes = account.get("avg_likes", 0) or 10  # baseline

            for tweet in tweets:
                m = tweet.public_metrics or {}
                likes = m.get("like_count", 0)
                replies = m.get("reply_count", 0)
                total_likes += likes
                total_replies += replies

                triggers = self._detect_triggers(tweet.text)

                if likes > avg_likes * 2:
                    hits.append({
                        "text": tweet.text[:200],
                        "likes": likes,
                        "replies": replies,
                        "triggers": triggers,
                    })
                elif likes < avg_likes * 0.3 and likes < 5:
                    misses.append({
                        "text": tweet.text[:200],
                        "likes": likes,
                        "triggers": triggers,
                    })

            new_avg = round(total_likes / max(len(tweets), 1), 1)

            insight = {
                "user_handle": f"@{handle}",
                "user_followers": (user.public_metrics or {}).get("followers_count", 0),
                "tweets_analyzed": len(tweets),
                "avg_likes": new_avg,
                "avg_replies": round(total_replies / max(len(tweets), 1), 1),
                "hits": len(hits),
                "misses": len(misses),
                "hit_examples": hits[:3],
                "miss_examples": misses[:2],
                "trend": "rising" if new_avg > avg_likes * 1.1 else "declining" if new_avg < avg_likes * 0.9 else "stable",
            }
            account_insights.append(insight)

            # Store as chip insight
            self.store_insight("x_social", "influencer_study", insight)

            # Update account in watchlist with new avg
            account["avg_likes"] = new_avg
            account["last_studied"] = datetime.now(timezone.utc).isoformat()

            time.sleep(self.LOOKUP_DELAY)

        self._log(f"  Studied {len(account_insights)} accounts")
        return account_insights

    # ── Phase 3: Pattern Analysis ────────────────────────────

    def analyze_patterns(self, high_performers: list[dict]) -> list[dict]:
        """Analyze what makes high-performing content work."""
        self._log("PHASE 3: Pattern Analysis")

        if not high_performers:
            self._log("  No high performers to analyze")
            return []

        # Aggregate trigger effectiveness
        trigger_counts: dict[str, int] = {}
        trigger_engagement: dict[str, list[int]] = {}
        question_likes = []
        statement_likes = []
        short_likes = []  # < 100 chars
        long_likes = []   # >= 100 chars

        for hp in high_performers:
            likes = hp.get("likes", 0)
            for trigger in hp.get("emotional_triggers", []):
                trigger_counts[trigger] = trigger_counts.get(trigger, 0) + 1
                trigger_engagement.setdefault(trigger, []).append(likes)

            if hp.get("has_question"):
                question_likes.append(likes)
            else:
                statement_likes.append(likes)

            if hp.get("length", 0) < 100:
                short_likes.append(likes)
            else:
                long_likes.append(likes)

        # Calculate trigger effectiveness ranking
        trigger_ranking = []
        for trigger, count in sorted(trigger_counts.items(), key=lambda x: -x[1]):
            avg_eng = round(sum(trigger_engagement[trigger]) / len(trigger_engagement[trigger]), 1)
            trigger_ranking.append({
                "trigger": trigger,
                "count": count,
                "avg_engagement": avg_eng,
            })

        # Content patterns
        patterns = {
            "trigger_ranking": trigger_ranking[:10],
            "question_vs_statement": {
                "questions": {
                    "count": len(question_likes),
                    "avg_likes": round(sum(question_likes) / max(len(question_likes), 1), 1),
                },
                "statements": {
                    "count": len(statement_likes),
                    "avg_likes": round(sum(statement_likes) / max(len(statement_likes), 1), 1),
                },
            },
            "length_effect": {
                "short": {
                    "count": len(short_likes),
                    "avg_likes": round(sum(short_likes) / max(len(short_likes), 1), 1),
                },
                "long": {
                    "count": len(long_likes),
                    "avg_likes": round(sum(long_likes) / max(len(long_likes), 1), 1),
                },
            },
            "top_topics": self._rank_topics(high_performers),
            "sample_size": len(high_performers),
        }

        self.store_insight("social-convo", "pattern_analysis", patterns)
        self._log(f"  Analyzed {len(high_performers)} high performers")
        self._log(f"  Top triggers: {[t['trigger'] for t in trigger_ranking[:3]]}")
        return [patterns]

    # ── Phase 4: Trend Detection ─────────────────────────────

    def detect_trends(self, topic_results: list[dict]) -> list[dict]:
        """Detect emerging vs declining trends based on this session vs history."""
        self._log("PHASE 4: Trend Detection")

        # Compare current session volume per topic against historical
        prev_sessions = self.state.get("topic_history", [])

        current_volumes = {}
        for hp in topic_results:
            topic = hp.get("topic", "unknown")
            current_volumes[topic] = current_volumes.get(topic, 0) + 1

        trends = []
        for topic, count in current_volumes.items():
            # Check against previous sessions
            prev_counts = [
                s.get(topic, 0)
                for s in prev_sessions[-5:]  # Last 5 sessions
            ]
            prev_avg = sum(prev_counts) / max(len(prev_counts), 1) if prev_counts else 0

            if prev_avg == 0:
                direction = "new"
            elif count > prev_avg * 1.5:
                direction = "surging"
            elif count > prev_avg * 1.1:
                direction = "rising"
            elif count < prev_avg * 0.5:
                direction = "declining"
            else:
                direction = "stable"

            trend = {
                "topic": topic,
                "current_volume": count,
                "previous_avg": round(prev_avg, 1),
                "direction": direction,
            }
            trends.append(trend)

            if direction in ("surging", "new"):
                self.store_insight("x_social", "trend_observed", {
                    "topic": topic,
                    "direction": direction,
                    "volume": count,
                    "previous_avg": round(prev_avg, 1),
                    "significance": "high" if direction == "surging" else "medium",
                })

        # Save current volumes to history
        self.state.setdefault("topic_history", []).append(current_volumes)
        # Keep last 20 sessions
        self.state["topic_history"] = self.state["topic_history"][-20:]

        self._log(f"  Trends: {', '.join(f'{t['topic']}={t['direction']}' for t in trends[:5])}")
        return trends

    # ── Phase 5: Self-Evolution ──────────────────────────────

    def evolve(self, high_performers: list[dict], trends: list[dict]):
        """Generate new research goals based on findings."""
        self._log("PHASE 5: Self-Evolution")

        new_intents = []

        # If a topic is surging, create intent to dig deeper
        for trend in trends:
            if trend["direction"] in ("surging", "new"):
                intent = f"Deep dive into '{trend['topic']}' - volume surging ({trend['current_volume']} tweets)"
                if intent not in self.state.get("research_intents", []):
                    new_intents.append(intent)

        # If certain triggers dominate high performers, create learning intent
        trigger_counts: dict[str, int] = {}
        for hp in high_performers:
            for t in hp.get("emotional_triggers", []):
                trigger_counts[t] = trigger_counts.get(t, 0) + 1
        top_triggers = sorted(trigger_counts.items(), key=lambda x: -x[1])[:3]
        for trigger, count in top_triggers:
            if count >= 5:
                intent = f"Study why '{trigger}' trigger appears in {count} high-performing tweets"
                if intent not in self.state.get("research_intents", []):
                    new_intents.append(intent)

        # If we found new interesting accounts, create study intents
        for acct in self.session_accounts_discovered[:5]:
            handle = acct.get("handle", "")
            intent = f"Study @{handle}'s content strategy - discovered via high engagement"
            new_intents.append(intent)

        # Discover new search topics from high performer content
        self._discover_topics(high_performers)

        # Store intents
        if new_intents:
            self.state.setdefault("research_intents", []).extend(new_intents[:10])
            # Cap at 30 intents
            self.state["research_intents"] = self.state["research_intents"][-30:]
            self._log(f"  New research intents: {len(new_intents)}")
            for intent in new_intents[:3]:
                self._log(f"    + {intent}")

        # Store evolution insight
        self.store_insight("x_social", "social_learning", {
            "type": "self_evolution",
            "new_intents": new_intents,
            "new_accounts_discovered": len(self.session_accounts_discovered),
            "new_topics_discovered": len(self.state.get("discovered_topics", [])),
            "total_intents": len(self.state.get("research_intents", [])),
        })

    # ── Main Entry Point ─────────────────────────────────────

    def run_session(self) -> dict:
        """Run a complete research session."""
        self._log("=" * 50)
        self._log("SPARK RESEARCH SESSION STARTING")
        self._log(f"Session #{self.state.get('sessions_run', 0) + 1}")
        self._log(f"Watchlist: {len(self.watchlist.get('accounts', []))} accounts")
        self._log(f"Intents: {len(self.state.get('research_intents', []))}")
        self._log("=" * 50)

        # Phase 1: Search topics
        high_performers = self.search_topics()

        # Phase 2: Study watched accounts
        account_insights = self.study_accounts()

        # Phase 3: Analyze patterns
        patterns = self.analyze_patterns(high_performers)

        # Phase 4: Detect trends
        trends = self.detect_trends(high_performers)

        # Phase 5: Self-evolve
        self.evolve(high_performers, trends)

        # Update state
        self.state["sessions_run"] = self.state.get("sessions_run", 0) + 1
        self.state["total_tweets_analyzed"] = (
            self.state.get("total_tweets_analyzed", 0)
            + sum(1 for i in self.session_insights if i["observer"] == "trend_observed")
        )
        self.state["total_insights_stored"] = (
            self.state.get("total_insights_stored", 0) + len(self.session_insights)
        )
        self.state["last_session"] = {
            "timestamp": self.session_start.isoformat(),
            "duration_seconds": (datetime.now(timezone.utc) - self.session_start).total_seconds(),
            "insights_generated": len(self.session_insights),
            "high_performers_found": len(high_performers),
            "accounts_studied": len(account_insights),
            "accounts_discovered": len(self.session_accounts_discovered),
        }

        # Save everything
        self._save_state()
        self._save_watchlist()

        summary = {
            "session": self.state["sessions_run"],
            "insights": len(self.session_insights),
            "high_performers": len(high_performers),
            "accounts_studied": len(account_insights),
            "accounts_discovered": len(self.session_accounts_discovered),
            "trends": len(trends),
            "duration": self.state["last_session"]["duration_seconds"],
        }

        self._log("")
        self._log("=" * 50)
        self._log("SESSION COMPLETE")
        self._log(f"  Insights generated: {summary['insights']}")
        self._log(f"  High performers found: {summary['high_performers']}")
        self._log(f"  Accounts studied: {summary['accounts_studied']}")
        self._log(f"  New accounts discovered: {summary['accounts_discovered']}")
        self._log(f"  Duration: {summary['duration']:.0f}s")
        self._log("=" * 50)

        return summary

    # ── Helpers ───────────────────────────────────────────────

    def _detect_triggers(self, text: str) -> list[str]:
        """Detect emotional triggers in text."""
        text_lower = text.lower()
        found = []
        for trigger, keywords in TRIGGER_KEYWORDS.items():
            for kw in keywords:
                if kw.lower() in text_lower:
                    found.append(trigger)
                    break
        return found

    def _maybe_add_to_watchlist(self, user, topic: str, engagement: int):
        """Add a user to the watchlist if they're interesting enough."""
        handle = user.username
        existing = {a["handle"].lower() for a in self.watchlist.get("accounts", [])}
        if handle.lower() in existing:
            return

        followers = (user.public_metrics or {}).get("followers_count", 0)
        description = user.description or ""

        account = {
            "handle": handle,
            "name": user.name,
            "followers": followers,
            "description": description[:200],
            "discovered_via": topic,
            "discovery_engagement": engagement,
            "added_at": datetime.now(timezone.utc).isoformat(),
            "priority": min(10, engagement // 100),
            "avg_likes": None,
            "last_studied": None,
        }

        self.watchlist.setdefault("accounts", []).append(account)
        self.session_accounts_discovered.append(account)
        self._log(f"    + Watchlist: @{handle} ({followers} followers, via {topic})")

    def _rank_topics(self, high_performers: list[dict]) -> list[dict]:
        """Rank topics by number of high performers."""
        counts: dict[str, dict] = {}
        for hp in high_performers:
            topic = hp.get("topic", "unknown")
            if topic not in counts:
                counts[topic] = {"count": 0, "total_likes": 0}
            counts[topic]["count"] += 1
            counts[topic]["total_likes"] += hp.get("likes", 0)

        ranked = [
            {"topic": t, "high_performers": d["count"], "total_likes": d["total_likes"]}
            for t, d in sorted(counts.items(), key=lambda x: -x[1]["count"])
        ]
        return ranked

    def _discover_topics(self, high_performers: list[dict]):
        """Look for new topics in high-performing content."""
        # Simple keyword extraction from high performers
        word_counts: dict[str, int] = {}
        existing_names = {t["name"].lower() for t in self.state.get("topics", [])}
        existing_names.update(t["name"].lower() for t in self.state.get("discovered_topics", []))

        interesting_bigrams = [
            "neural network", "fine tuning", "context window", "token limit",
            "open source", "model training", "inference speed", "reasoning model",
            "code generation", "pair programming", "dev tools", "API design",
            "autonomous agent", "tool use", "chain of thought", "multi modal",
        ]

        for hp in high_performers:
            text = hp.get("content", "").lower()
            for bigram in interesting_bigrams:
                if bigram in text and bigram not in existing_names:
                    word_counts[bigram] = word_counts.get(bigram, 0) + 1

        # If a bigram appears in 3+ high performers, suggest it as a topic
        for bigram, count in word_counts.items():
            if count >= 3:
                new_topic = {
                    "query": f'"{bigram}"',
                    "name": bigram.title(),
                    "category": "discovered",
                    "discovered_at": datetime.now(timezone.utc).isoformat(),
                    "discovery_count": count,
                }
                self.state.setdefault("discovered_topics", []).append(new_topic)
                self._log(f"    + New topic discovered: {bigram.title()} (seen {count}x)")
