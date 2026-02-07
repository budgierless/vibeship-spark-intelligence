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
import urllib.request
import urllib.error
from datetime import datetime, timezone, timedelta
from pathlib import Path

import tweepy
from dotenv import dotenv_values


# ── Local LLM Config ─────────────────────────────────────────
OLLAMA_URL = "http://localhost:11434/api/generate"
OLLAMA_MODEL = "phi4-mini"
OLLAMA_TIMEOUT = 30  # seconds per request


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

# ── Engagement thresholds per topic category ─────────────────
# Used to build min_faves:N into queries so the API only returns viral tweets.
CATEGORY_MIN_LIKES = {
    "core": 50,        # Niche topics (vibecoding) - only proven viral
    "technical": 75,   # Broader tech topics - higher bar
    "frontier": 100,   # Very broad topics (AGI) - must be genuinely viral
    "culture": 75,     # Culture topics must prove real signal
    "discovered": 50,  # Discovered topics - still need to prove value
}

# ── Search topics (tiered) ──────────────────────────────────
# tier 1: searched every session (core identity)
# tier 2: searched every other session (important, rotatable)
# tier 3: searched every 3rd session (frontier/experimental)
DEFAULT_TOPICS = [
    # ── Tier 1: Every session (core identity) ──
    {"query": '"vibe coding" OR vibecoding', "name": "Vibe Coding", "category": "core", "tier": 1},
    {"query": '"claude code" OR (claude coding agent)', "name": "Claude Code", "category": "core", "tier": 1},
    {"query": '"AI agents" (coding OR building OR framework)', "name": "AI Agents", "category": "core", "tier": 1},
    {"query": '(claude OR anthropic) (coding OR agent OR tool OR API)', "name": "Claude Ecosystem", "category": "core", "tier": 1},
    {"query": '"agentic" (coding OR systems OR framework OR workflow)', "name": "Agentic Systems", "category": "technical", "tier": 1},

    # ── Tier 2: Every other session ──
    {"query": 'cursor OR windsurf OR copilot AI coding -ad -promo', "name": "AI Coding Tools", "category": "technical", "tier": 2},
    {"query": '"prompt engineering" -course -free -giveaway', "name": "Prompt Engineering", "category": "technical", "tier": 2},
    {"query": '"building in public" ("AI" OR "vibe coding" OR "claude" OR "AI agent")', "name": "Building in Public (AI)", "category": "culture", "tier": 2},
    {"query": '"AI code" OR "code generation" OR "AI coding assistant" -course', "name": "AI Code Generation", "category": "technical", "tier": 2},
    {"query": '"model context protocol" OR "MCP server" OR ("tool use" AI agent)', "name": "MCP / Tool Use", "category": "technical", "tier": 2},

    # ── Tier 3: Every 3rd session ──
    {"query": 'AGI (coding OR agents OR building OR tools) -spam -giveaway -subscribe', "name": "AGI", "category": "frontier", "tier": 3},
    {"query": '"self-improving" OR "open source AI" OR "autonomous AI" (coding OR agents)', "name": "Frontier AI", "category": "frontier", "tier": 3},
    {"query": '"learning in public" ("AI" OR "vibe coding" OR "coding with AI")', "name": "Learning in Public (AI)", "category": "culture", "tier": 3},
    {"query": '"pair programming" AI OR "coding with AI" OR "AI copilot"', "name": "AI Pair Programming", "category": "culture", "tier": 3},
]


class SparkResearcher:
    """Autonomous X research engine for Spark Intelligence."""

    ENGAGEMENT_MIN = 50       # Minimum likes for "high performer"
    SEARCH_DELAY = 2.5        # Seconds between API searches
    LOOKUP_DELAY = 1.0        # Seconds between lookups
    MAX_RESULTS = 100         # Results per search query (API max)
    TWEETS_PER_ACCOUNT = 15   # Recent tweets to check per watched account (was 30)
    MAX_ACCOUNTS_PER_SESSION = 5  # Accounts to study per session (was 10)

    # ── Credit budget ──
    SESSION_BUDGET = 800      # Max tweet reads per session
    MONTHLY_BUDGET = 10000    # Twitter Basic plan cap

    def __init__(self, verbose: bool = True, dry_run: bool = False):
        self.verbose = verbose
        self.dry_run = dry_run
        self.creds = self._load_creds()
        self.client = self._get_client()
        self.state = self._load_state()
        self.watchlist = self._load_watchlist()
        self.session_insights: list[dict] = []
        self.session_accounts_discovered: list[dict] = []
        self.session_start = datetime.now(timezone.utc)
        # Budget tracking
        self.session_api_calls = 0
        self.session_tweet_reads = 0

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

    # ── Budget tracking ───────────────────────────────────────

    def _track_api_call(self, call_type: str, tweet_count: int = 0):
        """Track an API call against session and monthly budgets."""
        self.session_api_calls += 1
        self.session_tweet_reads += tweet_count
        month_key = datetime.now(timezone.utc).strftime("%Y-%m")
        monthly = self.state.setdefault("monthly_usage", {})
        month_data = monthly.setdefault(month_key, {"calls": 0, "reads": 0})
        month_data["calls"] += 1
        month_data["reads"] += tweet_count

    def _budget_remaining(self) -> int:
        """Tweet reads remaining in this session's budget."""
        return max(0, self.SESSION_BUDGET - self.session_tweet_reads)

    def _monthly_remaining(self) -> int:
        """Tweet reads remaining this month."""
        month_key = datetime.now(timezone.utc).strftime("%Y-%m")
        used = self.state.get("monthly_usage", {}).get(month_key, {}).get("reads", 0)
        return max(0, self.MONTHLY_BUDGET - used)

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
        """Search all tracked topics and find high-performing content.

        Upgrades over v1:
        - min_faves:N in query strings (API-level viral filtering)
        - sort_order="relevancy" (best results first)
        - Tiered topic schedule (tier 1 every session, tier 2/3 rotated)
        - Adaptive skip for topics with consecutive zero results
        - Budget-gated API calls
        - Only stores high-performer tweets (no noise)
        """
        self._log("PHASE 1: Topic Search")
        # Always use code-defined topics (not state) + any discovered topics
        all_topics = list(DEFAULT_TOPICS) + self.state.get("discovered_topics", [])
        high_performers = []
        topic_stats = {}
        session_num = self.state.get("sessions_run", 0)

        for topic in all_topics:
            name = topic["name"]
            tier = topic.get("tier", 1)
            category = topic.get("category", "core")

            # ── Tier gating: skip topics not scheduled this session ──
            if tier == 2 and session_num % 2 != 0:
                continue
            if tier == 3 and session_num % 3 != 0:
                continue

            # ── Adaptive skip: topics that returned 0 for 3+ sessions ──
            perf = self.state.get("topic_performance", {}).get(name, {})
            consecutive_zeros = perf.get("consecutive_zeros", 0)
            if consecutive_zeros >= 3:
                # Re-check after 10 skipped sessions
                if consecutive_zeros < 13:
                    self._log(f"  Skipping: {name} (0 results for {consecutive_zeros} sessions)")
                    continue
                else:
                    perf["consecutive_zeros"] = 0  # Reset, give it another chance

            # ── Budget check ──
            if self._budget_remaining() < 100:
                self._log(f"  Budget exhausted ({self.session_tweet_reads} reads), stopping searches")
                break

            # ── Build viral-filtered query ──
            min_likes = CATEGORY_MIN_LIKES.get(category, 30)
            query = topic["query"] + f" min_faves:{min_likes} -is:retweet lang:en"

            self._log(f"  Searching: {name} (tier {tier}, min_faves:{min_likes})")

            if self.dry_run:
                self._log(f"    [DRY RUN] Query: {query}")
                continue

            try:
                since_id = self.state.get("last_since_ids", {}).get(name)
                result = self.client.search_recent_tweets(
                    query=query,
                    max_results=min(self.MAX_RESULTS, 100),
                    since_id=since_id,
                    sort_order="relevancy",
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
            except tweepy.errors.BadRequest as e:
                # min_faves might not be supported on our tier - fallback
                err_msg = str(e)[:120]
                if "min_faves" in err_msg.lower() or "operator" in err_msg.lower():
                    self._log(f"    min_faves not supported, retrying without")
                    query = topic["query"] + " -is:retweet lang:en"
                    try:
                        result = self.client.search_recent_tweets(
                            query=query,
                            max_results=50,  # Reduced since no pre-filter
                            since_id=since_id,
                            sort_order="relevancy",
                            tweet_fields=["public_metrics", "created_at", "author_id", "conversation_id"],
                            user_fields=["username", "name", "public_metrics", "description"],
                            expansions=["author_id"],
                        )
                    except Exception as e2:
                        self._log(f"    Fallback also failed: {type(e2).__name__}")
                        continue
                else:
                    self._log(f"    Bad request: {err_msg}")
                    continue
            except Exception as e:
                self._log(f"    Error: {type(e).__name__}: {str(e)[:100]}")
                continue

            tweets = result.data or []
            users = {u.id: u for u in (result.includes or {}).get("users", [])}
            self._track_api_call("search", len(tweets))

            # Track newest tweet ID for next run
            if tweets:
                newest_id = max(t.id for t in tweets)
                self.state.setdefault("last_since_ids", {})[name] = str(newest_id)

            # ── Analyze tweets (only store high performers) ──
            topic_total = len(tweets)
            topic_high = 0
            for tweet in tweets:
                metrics = tweet.public_metrics or {}
                likes = metrics.get("like_count", 0)
                replies = metrics.get("reply_count", 0)
                retweets = metrics.get("retweet_count", 0)
                total_engagement = likes + replies + retweets

                author = users.get(tweet.author_id)
                author_handle = f"@{author.username}" if author else "unknown"
                author_followers = (author.public_metrics or {}).get("followers_count", 0) if author else 0

                # Only fully analyze tweets above engagement threshold
                if likes < self.ENGAGEMENT_MIN:
                    continue

                topic_high += 1
                triggers_found = self._detect_triggers(tweet.text)
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

                # Deep LLM analysis for high performers
                llm_analysis = self._llm_analyze_tweet(tweet.text, likes, replies, name)
                if llm_analysis:
                    analysis["llm_analysis"] = llm_analysis
                    llm_triggers = llm_analysis.get("emotional_triggers", [])
                    analysis["emotional_triggers"] = list(set(triggers_found + llm_triggers))
                    analysis["content_strategy"] = llm_analysis.get("content_strategy", "unknown")
                    analysis["engagement_hooks"] = llm_analysis.get("engagement_hooks", [])
                    analysis["writing_patterns"] = llm_analysis.get("writing_patterns", [])
                    analysis["why_it_works"] = llm_analysis.get("why_it_works", "")
                    analysis["replicable_lesson"] = llm_analysis.get("replicable_lesson", "")

                high_performers.append(analysis)
                self.store_insight("engagement-pulse", "high_performer_detected", analysis)

                # Check if author should be on the watchlist
                if author and author_followers >= 500:
                    self._maybe_add_to_watchlist(author, name, total_engagement)

            # ── Update topic performance tracking ──
            tp = self.state.setdefault("topic_performance", {})
            topic_perf = tp.setdefault(name, {"hits": 0, "misses": 0, "consecutive_zeros": 0, "last_hit_session": 0})
            if topic_high > 0:
                topic_perf["hits"] += 1
                topic_perf["consecutive_zeros"] = 0
                topic_perf["last_hit_session"] = session_num
            else:
                topic_perf["misses"] += 1
                if topic_total == 0:
                    topic_perf["consecutive_zeros"] += 1

            topic_stats[name] = {"total": topic_total, "high_performers": topic_high}
            self._log(f"    Found {topic_total} tweets, {topic_high} high performers")
            time.sleep(self.SEARCH_DELAY)

        # Store topic stats as a session summary
        self.store_insight("x_social", "topic_cycle", {
            "stats": topic_stats,
            "total_searched": sum(s["total"] for s in topic_stats.values()),
            "total_high_performers": sum(s["high_performers"] for s in topic_stats.values()),
            "session_time": self.session_start.isoformat(),
            "budget_used": self.session_tweet_reads,
        })

        self._log(f"  Topic search complete: {len(high_performers)} high performers found")
        self._log(f"  Budget used: {self.session_tweet_reads} reads ({self._budget_remaining()} remaining)")
        return high_performers

    # ── Phase 2: Account Study ───────────────────────────────

    def study_accounts(self) -> list[dict]:
        """Study watchlist accounts' recent activity.

        Optimized: skips conversation-tier, prioritizes unstudied accounts,
        caps at MAX_ACCOUNTS_PER_SESSION, budget-gated.
        """
        self._log("PHASE 2: Account Study")
        accounts = self.watchlist.get("accounts", [])
        if not accounts:
            self._log("  No accounts on watchlist yet, skipping")
            return []

        if self.dry_run:
            self._log("  [DRY RUN] Would study accounts, skipping")
            return []

        account_insights = []

        # Skip conversation-tier (0-follower reply partners waste credits)
        eligible = [a for a in accounts if a.get("relationship") != "conversation"]
        # Unstudied first, then by staleness
        unstudied = [a for a in eligible if not a.get("last_studied")]
        studied = [a for a in eligible if a.get("last_studied")]
        studied.sort(key=lambda a: a.get("last_studied", ""))  # Oldest first
        study_batch = (
            sorted(unstudied, key=lambda a: a.get("priority", 0), reverse=True)
            + studied
        )[:self.MAX_ACCOUNTS_PER_SESSION]

        for account in study_batch:
            handle = account.get("handle", "").lstrip("@")
            if not handle:
                continue

            # Budget check before each account study
            if self._budget_remaining() < 50:
                self._log(f"  Budget low ({self._budget_remaining()} remaining), stopping account study")
                break

            self._log(f"  Studying @{handle}")

            try:
                # Get user info
                user_result = self.client.get_user(
                    username=handle,
                    user_fields=["public_metrics", "description", "created_at"],
                )
                self._track_api_call("user_lookup", 0)

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
            self._track_api_call("user_tweets", len(tweets))
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
                    hit = {
                        "text": tweet.text[:200],
                        "likes": likes,
                        "replies": replies,
                        "triggers": triggers,
                    }
                    # Deep analysis for significant hits (50+ likes)
                    if likes >= self.ENGAGEMENT_MIN:
                        llm_result = self._llm_analyze_tweet(
                            tweet.text, likes, replies, f"@{handle} study"
                        )
                        if llm_result:
                            hit["llm_analysis"] = llm_result
                            hit["content_strategy"] = llm_result.get("content_strategy", "")
                            hit["why_it_works"] = llm_result.get("why_it_works", "")
                    hits.append(hit)
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

        # LLM-powered aggregations
        strategy_counts: dict[str, list[int]] = {}
        hook_counts: dict[str, int] = {}
        writing_pattern_counts: dict[str, int] = {}
        lessons: list[str] = []

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

            # LLM-generated fields
            strategy = hp.get("content_strategy", "")
            if strategy:
                strategy_counts.setdefault(strategy, []).append(likes)
            for hook in hp.get("engagement_hooks", []):
                hook_counts[hook] = hook_counts.get(hook, 0) + 1
            for wp in hp.get("writing_patterns", []):
                writing_pattern_counts[wp] = writing_pattern_counts.get(wp, 0) + 1
            lesson = hp.get("replicable_lesson", "")
            if lesson:
                lessons.append(lesson)

        # Calculate trigger effectiveness ranking
        trigger_ranking = []
        for trigger, count in sorted(trigger_counts.items(), key=lambda x: -x[1]):
            avg_eng = round(sum(trigger_engagement[trigger]) / len(trigger_engagement[trigger]), 1)
            trigger_ranking.append({
                "trigger": trigger,
                "count": count,
                "avg_engagement": avg_eng,
            })

        # Content strategy ranking (from LLM)
        strategy_ranking = []
        for strategy, likes_list in sorted(strategy_counts.items(), key=lambda x: -len(x[1])):
            strategy_ranking.append({
                "strategy": strategy,
                "count": len(likes_list),
                "avg_engagement": round(sum(likes_list) / len(likes_list), 1),
            })

        # Engagement hooks ranking (from LLM)
        hook_ranking = sorted(
            [{"hook": h, "count": c} for h, c in hook_counts.items()],
            key=lambda x: -x["count"],
        )[:15]

        # Writing patterns ranking (from LLM)
        writing_ranking = sorted(
            [{"pattern": p, "count": c} for p, c in writing_pattern_counts.items()],
            key=lambda x: -x["count"],
        )[:10]

        # Content patterns
        patterns = {
            "trigger_ranking": trigger_ranking[:10],
            "strategy_ranking": strategy_ranking[:10],
            "engagement_hooks": hook_ranking,
            "writing_patterns": writing_ranking,
            "replicable_lessons": lessons[:10],
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
            "llm_analyzed": sum(1 for hp in high_performers if hp.get("llm_analysis")),
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

        # ── Adaptive tier promotion/demotion ──
        for topic in DEFAULT_TOPICS:
            name = topic["name"]
            perf = self.state.get("topic_performance", {}).get(name, {})
            total = perf.get("hits", 0) + perf.get("misses", 0)
            if total >= 5:
                hit_rate = perf["hits"] / total
                old_tier = topic.get("tier", 1)
                if hit_rate > 0.6 and old_tier > 1:
                    topic["tier"] = old_tier - 1
                    self._log(f"  Promoted '{name}' to tier {topic['tier']} (hit rate: {hit_rate:.0%})")
                elif hit_rate < 0.1 and old_tier < 3:
                    topic["tier"] = old_tier + 1
                    self._log(f"  Demoted '{name}' to tier {topic['tier']} (hit rate: {hit_rate:.0%})")

        # Store evolution insight
        self.store_insight("x_social", "social_learning", {
            "type": "self_evolution",
            "new_intents": new_intents,
            "new_accounts_discovered": len(self.session_accounts_discovered),
            "new_topics_discovered": len(self.state.get("discovered_topics", [])),
            "total_intents": len(self.state.get("research_intents", [])),
        })

    # ── Main Entry Point ─────────────────────────────────────

    # ── MCP Signal Ingestion ─────────────────────────────────

    def ingest_mcp_results(self, tweets: list[dict]):
        """Process tweets gathered via MCP tools (zero bearer_token cost).

        Accepts a list of dicts with keys: text, likes, replies, retweets,
        user_handle, user_followers, topic.
        """
        self._log(f"Ingesting {len(tweets)} tweets from MCP")
        for tweet in tweets:
            likes = tweet.get("likes", 0)
            if likes < self.ENGAGEMENT_MIN:
                continue

            triggers = self._detect_triggers(tweet.get("text", ""))
            topic = tweet.get("topic", "mcp_feed")

            analysis = {
                "topic": topic,
                "content": tweet.get("text", "")[:280],
                "likes": likes,
                "replies": tweet.get("replies", 0),
                "retweets": tweet.get("retweets", 0),
                "user_handle": tweet.get("user_handle", "unknown"),
                "user_followers": tweet.get("user_followers", 0),
                "emotional_triggers": triggers,
                "source": "mcp",
            }

            llm_result = self._llm_analyze_tweet(
                tweet.get("text", ""), likes, tweet.get("replies", 0), topic,
            )
            if llm_result:
                analysis["llm_analysis"] = llm_result
                analysis["emotional_triggers"] = list(set(triggers + llm_result.get("emotional_triggers", [])))
                analysis["content_strategy"] = llm_result.get("content_strategy", "")
                analysis["why_it_works"] = llm_result.get("why_it_works", "")
                analysis["replicable_lesson"] = llm_result.get("replicable_lesson", "")

            self.store_insight("engagement-pulse", "high_performer_detected", analysis)
        self._log(f"  Ingested {len(self.session_insights)} insights from MCP")

    # ── Main Entry Point ─────────────────────────────────────

    def run_session(self) -> dict:
        """Run a complete research session."""
        session_num = self.state.get("sessions_run", 0) + 1

        # Budget info at start
        monthly_remaining = self._monthly_remaining()
        sessions_est = monthly_remaining // max(self.SESSION_BUDGET, 1)

        self._log("=" * 50)
        self._log("SPARK RESEARCH SESSION STARTING")
        self._log(f"Session #{session_num}")
        self._log(f"Watchlist: {len(self.watchlist.get('accounts', []))} accounts")
        self._log(f"Intents: {len(self.state.get('research_intents', []))}")
        self._log(f"Budget: {monthly_remaining}/{self.MONTHLY_BUDGET} reads remaining (~{sessions_est} sessions)")
        if self.dry_run:
            self._log("MODE: DRY RUN (no API calls)")
        self._log("=" * 50)

        # Auto-reduce session budget if monthly budget is tight
        if monthly_remaining < self.SESSION_BUDGET * 3:
            old_budget = self.SESSION_BUDGET
            self.SESSION_BUDGET = max(100, monthly_remaining // 3)
            self._log(f"  Budget tight! Reduced session budget: {old_budget} -> {self.SESSION_BUDGET}")

        # Phase 1: Search topics
        high_performers = self.search_topics()

        # Phase 2: Study watched accounts (every other session)
        if session_num % 2 == 0:
            account_insights = self.study_accounts()
        else:
            self._log("PHASE 2: Account Study (skipped - odd session, alternating)")
            account_insights = []

        # Phase 3: Analyze patterns
        patterns = self.analyze_patterns(high_performers)

        # Phase 4: Detect trends
        trends = self.detect_trends(high_performers)

        # Phase 5: Self-evolve (includes adaptive topic promotion/demotion)
        self.evolve(high_performers, trends)

        # Update state
        self.state["sessions_run"] = session_num
        self.state["total_tweets_analyzed"] = (
            self.state.get("total_tweets_analyzed", 0) + self.session_tweet_reads
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
            "api_calls": self.session_api_calls,
            "tweet_reads": self.session_tweet_reads,
            "monthly_remaining": self._monthly_remaining(),
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
            "api_calls": self.session_api_calls,
            "tweet_reads": self.session_tweet_reads,
            "monthly_remaining": self._monthly_remaining(),
        }

        self._log("")
        self._log("=" * 50)
        self._log("SESSION COMPLETE")
        self._log(f"  Insights generated: {summary['insights']}")
        self._log(f"  High performers found: {summary['high_performers']}")
        self._log(f"  Accounts studied: {summary['accounts_studied']}")
        self._log(f"  New accounts discovered: {summary['accounts_discovered']}")
        self._log(f"  API calls: {summary['api_calls']} ({summary['tweet_reads']} tweet reads)")
        self._log(f"  Monthly budget remaining: {summary['monthly_remaining']}")
        self._log(f"  Duration: {summary['duration']:.0f}s")
        self._log("=" * 50)

        return summary

    # ── Helpers ───────────────────────────────────────────────

    def _detect_triggers(self, text: str) -> list[str]:
        """Fast keyword-based trigger detection for all tweets."""
        text_lower = text.lower()
        found = []
        for trigger, keywords in TRIGGER_KEYWORDS.items():
            for kw in keywords:
                if kw.lower() in text_lower:
                    found.append(trigger)
                    break
        return found

    def _llm_available(self) -> bool:
        """Check if Ollama is reachable (cached per session)."""
        if hasattr(self, "_ollama_ok"):
            return self._ollama_ok
        try:
            req = urllib.request.Request(
                "http://localhost:11434/api/tags",
                method="GET",
            )
            with urllib.request.urlopen(req, timeout=3) as resp:
                self._ollama_ok = resp.status == 200
        except Exception:
            self._ollama_ok = False
            self._log("  LLM (Ollama) not available - using keyword analysis only")
        return self._ollama_ok

    def _call_ollama(self, prompt: str) -> str | None:
        """Call local Ollama API. Returns response text or None on failure."""
        try:
            payload = json.dumps({
                "model": OLLAMA_MODEL,
                "prompt": prompt,
                "stream": False,
                "options": {"temperature": 0.3, "num_predict": 300},
            }).encode("utf-8")
            req = urllib.request.Request(
                OLLAMA_URL,
                data=payload,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=OLLAMA_TIMEOUT) as resp:
                result = json.loads(resp.read().decode("utf-8"))
                return result.get("response", "")
        except Exception as e:
            self._log(f"    LLM call failed: {type(e).__name__}")
            return None

    def _llm_analyze_tweet(self, text: str, likes: int, replies: int, topic: str) -> dict | None:
        """Deep-analyze a high-performing tweet using local LLM.

        Returns a structured analysis dict or None if LLM unavailable.
        Only called for tweets above ENGAGEMENT_MIN (50+ likes).
        """
        if not self._llm_available():
            return None

        prompt = f"""Analyze this high-performing tweet ({likes} likes, {replies} replies) from the "{topic}" space.

TWEET:
\"\"\"{text}\"\"\"

Return a JSON object with EXACTLY these fields (no markdown, no explanation, just the JSON):
{{
  "emotional_triggers": ["list of emotional hooks used, e.g. curiosity_gap, aspiration, contrast, vulnerability, identity_signal, surprise, validation, urgency, social_proof, authority"],
  "content_strategy": "one of: hot_take, educational, storytelling, announcement, question, thread_hook, contrarian, celebration, call_to_action",
  "engagement_hooks": ["specific techniques: e.g. open_loop, bold_claim, personal_story, data_point, metaphor, list_format, controversy, relatable_pain"],
  "writing_patterns": ["structural elements: e.g. short_sentences, line_breaks, emoji_use, all_caps_emphasis, rhetorical_question, imperative_verb"],
  "why_it_works": "one sentence explaining why this specific tweet performs well",
  "replicable_lesson": "one actionable takeaway for creating similar content"
}}"""

        raw = self._call_ollama(prompt)
        if not raw:
            return None

        # Extract JSON from response (LLM might wrap it in markdown)
        try:
            # Try direct parse first
            return json.loads(raw.strip())
        except json.JSONDecodeError:
            pass

        # Try extracting from markdown code block
        match = re.search(r"\{[\s\S]*\}", raw)
        if match:
            try:
                return json.loads(match.group())
            except json.JSONDecodeError:
                pass

        self._log(f"    LLM returned unparseable response, skipping")
        return None

    def _maybe_add_to_watchlist(self, user, topic: str, engagement: int):
        """Add a user to the watchlist if they're interesting enough.

        Relationship types:
          - learn_from: High-value accounts we follow to learn from.
            Criteria: 5K+ followers OR exceptional engagement rate (50+ likes
            with <5K followers). These are accounts producing consistent
            insight in our tracked topics.
          - watch: Accounts worth monitoring but not following yet.
            Discovered via high engagement but don't meet learn_from bar.
          - conversation: People we've interacted with (set manually).
        """
        handle = user.username
        existing = {a["handle"].lower() for a in self.watchlist.get("accounts", [])}
        if handle.lower() in existing:
            return

        followers = (user.public_metrics or {}).get("followers_count", 0)
        description = user.description or ""

        # Determine relationship: follow with purpose
        engagement_rate = engagement / max(followers, 1) * 100
        if followers >= 5000 or (engagement >= 50 and engagement_rate >= 2.0):
            relationship = "learn_from"
        else:
            relationship = "watch"

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
            "relationship": relationship,
            "following": False,
        }

        self.watchlist.setdefault("accounts", []).append(account)
        self.session_accounts_discovered.append(account)
        tag = "LEARN" if relationship == "learn_from" else "WATCH"
        self._log(f"    + [{tag}] @{handle} ({followers} followers, via {topic})")

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
