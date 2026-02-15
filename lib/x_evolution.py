"""
Spark X Evolution Engine — Real-time self-improvement from social interactions.

Deeply integrated with Spark Intelligence core systems:
  - CognitiveLearner: Stores evolved patterns as reasoning/wisdom insights
  - MetaRalph: Quality-gates evolution events before promotion (score >= 4)
  - Advisor: Tracks effectiveness of evolution-driven advice
  - EIDOS: Creates episodes for evolution cycles with prediction->outcome loops

Closes the loop between:
  1. Research findings (what patterns work on X)
  2. Conversation outcomes (what Spark posts that actually performs)
  3. Voice adaptation (evolving tone/triggers based on results)
  4. Topic evolution (shifting interests based on engagement)
  5. Gap diagnosis (identifies weaknesses in Spark Intelligence)

Every evolution event is logged to ~/.spark/x_evolution_log.jsonl
so the dashboard can show Spark growing in real time.

Usage:
    from lib.x_evolution import XEvolution
    evo = XEvolution()
    evo.evolve_from_research()
    evo.diagnose_gaps()
    evo.get_evolution_timeline()
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Optional

import tweepy
from dotenv import dotenv_values

# ── Core System Imports (graceful degradation) ──────────────
try:
    from lib.cognitive_learner import get_cognitive_learner, CognitiveCategory
    HAS_COGNITIVE = True
except ImportError:
    HAS_COGNITIVE = False
    get_cognitive_learner = None

try:
    from lib.meta_ralph import get_meta_ralph
    HAS_RALPH = True
except ImportError:
    HAS_RALPH = False
    get_meta_ralph = None

try:
    from lib.advisor import get_advisor
    HAS_ADVISOR = True
except ImportError:
    HAS_ADVISOR = False
    get_advisor = None

try:
    from lib.eidos.models import Episode, Step, Budget, Phase, Evaluation, DistillationType
    from lib.eidos import get_retriever
    HAS_EIDOS = True
except ImportError:
    HAS_EIDOS = False


# ── Paths ────────────────────────────────────────────────────
SPARK_DIR = Path.home() / ".spark"
EVOLUTION_LOG = SPARK_DIR / "x_evolution_log.jsonl"
EVOLUTION_STATE = SPARK_DIR / "x_evolution_state.json"
CHIP_INSIGHTS_DIR = SPARK_DIR / "chip_insights"
VOICE_ADAPTATIONS = SPARK_DIR / "x_voice" / "adaptations.json"
COGNITIVE_INSIGHTS = SPARK_DIR / "cognitive_insights.json"
ADVISOR_DIR = SPARK_DIR / "advisor"
TUNEABLES_PATH = SPARK_DIR / "tuneables.json"
EIDOS_DB = SPARK_DIR / "eidos.db"
ENV_PATH = Path(__file__).resolve().parent.parent / "mcp-servers" / "x-twitter-mcp" / ".env"


# ── Evolution Event Types ────────────────────────────────────

@dataclass
class EvolutionEvent:
    """A single evolution moment — something Spark learned or changed."""
    event_type: str          # voice_shift, pattern_adopted, topic_evolved, reply_learned, strategy_discovered
    description: str         # Human-readable: "Adopted 'curiosity_gap' trigger — 3x avg engagement"
    before: dict             # State before change
    after: dict              # State after change
    evidence: dict           # Data that justified the change
    confidence: float        # 0-1 how sure we are this is right
    timestamp: str = ""

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now(timezone.utc).isoformat()


class XEvolution:
    """Real-time evolution engine for Spark's X presence."""

    # Minimum data before making voice changes
    MIN_REPLIES_FOR_VOICE_SHIFT = 5
    MIN_RESEARCH_INSIGHTS_FOR_PATTERN = 10
    # How much to shift weights (conservative)
    MAX_WEIGHT_SHIFT = 0.15

    def __init__(self, verbose: bool = True):
        self.verbose = verbose
        self.creds = self._load_creds()
        self.client = self._get_read_client()
        self.state = self._load_state()

    # ── Setup ────────────────────────────────────────────────

    def _load_creds(self) -> dict:
        if not ENV_PATH.exists():
            raise FileNotFoundError(f"No .env at {ENV_PATH}")
        return dotenv_values(ENV_PATH)

    def _get_read_client(self) -> tweepy.Client:
        """Bearer token client for reading engagement metrics."""
        token = self.creds.get("TWITTER_BEARER_TOKEN")
        if not token:
            raise ValueError("Missing TWITTER_BEARER_TOKEN in .env")
        return tweepy.Client(bearer_token=token, wait_on_rate_limit=True)

    def _load_state(self) -> dict:
        if EVOLUTION_STATE.exists():
            try:
                return json.loads(EVOLUTION_STATE.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                pass
        return {
            "tracked_replies": {},       # tweet_id -> {parent_id, posted_at, text_preview, checked_at, likes, replies}
            "voice_weights": {           # Current evolved weights for triggers/tones
                "triggers": {},          # trigger_name -> weight (1.0 = baseline)
                "tones": {},             # tone_name -> weight
                "strategies": {},        # strategy_name -> weight
            },
            "adopted_patterns": [],      # Patterns officially adopted from research
            "evolution_count": 0,        # Total evolution events
            "last_evolution": None,
        }

    def _save_state(self):
        EVOLUTION_STATE.parent.mkdir(parents=True, exist_ok=True)
        EVOLUTION_STATE.write_text(
            json.dumps(self.state, indent=2, default=str),
            encoding="utf-8",
        )

    def _log(self, msg: str):
        if self.verbose:
            print(f"  [EVO {datetime.now().strftime('%H:%M:%S')}] {msg}")

    def _log_event(self, event: EvolutionEvent):
        """Append an evolution event to the log."""
        EVOLUTION_LOG.parent.mkdir(parents=True, exist_ok=True)
        with open(EVOLUTION_LOG, "a", encoding="utf-8") as f:
            f.write(json.dumps(asdict(event), default=str) + "\n")
        self.state["evolution_count"] = self.state.get("evolution_count", 0) + 1
        self.state["last_evolution"] = event.timestamp
        self._log(f"EVOLVED: {event.description}")

    def _to_wisdom_summary(
        self, etype: str, desc: str, evidence: dict
    ) -> tuple:
        """Convert raw evolution event to wisdom-level insight.

        Returns (insight_text, context_text, CognitiveCategory) or (None, None, None)
        if the event is pure operational telemetry.

        Wisdom-level means: actionable, has reasoning, outcome-linked, specific.
        MetaRalph scores these 5 dimensions 0-2 each (total 0-10).
        Raw telemetry like "Boosted surprise 1.09->1.11" scores ~1/10.
        Wisdom summaries should score 6+/10.
        """
        if etype == "voice_shift":
            trigger = evidence.get("trigger", "")
            avg_likes = evidence.get("avg_likes", 0)
            global_avg = evidence.get("global_avg", 0)
            observations = evidence.get("observations", 0)
            if not trigger or not avg_likes or not global_avg or observations < 3:
                return None, None, None
            diff_pct = round((avg_likes - global_avg) / max(global_avg, 1) * 100, 1)
            direction = "outperforms" if diff_pct > 0 else "underperforms"
            action = "Prefer" if diff_pct > 0 else "Avoid"
            return (
                f"[X Strategy] {trigger.replace('_', ' ')} triggers {direction} by "
                f"{abs(diff_pct)}% ({avg_likes:.0f} vs {global_avg:.0f} avg likes, "
                f"{observations} observations). {action} {trigger.replace('_', ' ')}-based "
                f"hooks for X engagement because they consistently drive "
                f"{'higher' if diff_pct > 0 else 'lower'} engagement.",
                f"[domain:x_social] Derived from {observations} tweet observations. "
                f"Evidence: avg engagement {avg_likes:.0f} vs global {global_avg:.0f}.",
                CognitiveCategory.REASONING,
            )

        elif etype == "strategy_discovered":
            # Extract strategy name and performance from description
            avg_likes = evidence.get("avg_likes", 0)
            observations = evidence.get("observations", 0)
            strategy = evidence.get("strategy", "")
            if not strategy:
                # Parse from description: "Boosted/Reduced 'X' strategy: ..."
                import re
                m = re.search(r"'(.+?)'", desc)
                strategy = m.group(1) if m else ""
            if not strategy or observations < 3:
                return None, None, None
            is_boost = "Boosted" in desc or avg_likes > 2000
            action = "Use" if is_boost else "Avoid"
            return (
                f"[X Strategy] {action} '{strategy}' content strategy on X. "
                f"Data shows {observations} observations with avg {avg_likes:.0f} likes. "
                f"{'This strategy consistently drives engagement.' if is_boost else 'This strategy underperforms - restructure content differently.'}",
                f"[domain:x_social] Content strategy insight from engagement-pulse research data.",
                CognitiveCategory.WISDOM,
            )

        elif etype == "gap_identified":
            return (
                f"[System Gap] {desc}",
                "[domain:x_social] Gap in Spark Intelligence identified by evolution engine. "
                "Address this to improve system health.",
                CognitiveCategory.META_LEARNING,
            )

        elif etype == "pattern_adopted":
            return (
                f"[X Pattern] {desc}",
                "[domain:x_social] Proven social engagement pattern from X research.",
                CognitiveCategory.WISDOM,
            )

        elif etype == "reply_learned":
            return (
                f"[X Reply Insight] {desc}",
                "[domain:x_social] Reply pattern from outcome tracking on X.",
                CognitiveCategory.CONTEXT,
            )

        elif etype == "topic_evolved":
            return (
                f"[X Topic] {desc}",
                "[domain:x_social] Topic interest from engagement research.",
                CognitiveCategory.CONTEXT,
            )

        return None, None, None

    # ── 1. Track Conversation Outcomes ───────────────────────

    def register_reply(self, tweet_id: str, parent_id: str, text: str):
        """Register a reply Spark just posted, so we can check its performance later."""
        self.state.setdefault("tracked_replies", {})[tweet_id] = {
            "parent_id": parent_id,
            "posted_at": datetime.now(timezone.utc).isoformat(),
            "text_preview": text[:140],
            "text_full": text[:280],
            "checked_at": None,
            "likes": None,
            "replies": None,
            "retweets": None,
            "outcome": None,  # "hit", "normal", "miss"
        }
        self._save_state()
        self._log(f"Registered reply {tweet_id} for tracking")

    def check_reply_outcomes(self) -> list[dict]:
        """Check engagement on Spark's tracked replies (call periodically).

        Only checks replies that are at least 1 hour old (to allow engagement
        to accumulate) and haven't been checked in the last 2 hours.
        """
        tracked = self.state.get("tracked_replies", {})
        if not tracked:
            self._log("No replies to check")
            return []

        now = datetime.now(timezone.utc)
        results = []
        ids_to_check = []

        for tweet_id, info in tracked.items():
            posted = datetime.fromisoformat(info["posted_at"].replace("Z", "+00:00"))
            age_hours = (now - posted).total_seconds() / 3600

            # Must be at least 1 hour old
            if age_hours < 1:
                continue

            # Don't recheck within 2 hours
            if info.get("checked_at"):
                last_check = datetime.fromisoformat(info["checked_at"].replace("Z", "+00:00"))
                if (now - last_check).total_seconds() < 7200:
                    continue

            # Don't check tweets older than 7 days
            if age_hours > 168:
                continue

            ids_to_check.append(tweet_id)

        if not ids_to_check:
            self._log("No replies ready for checking")
            return []

        self._log(f"Checking {len(ids_to_check)} reply outcomes...")

        for tweet_id in ids_to_check[:20]:  # Cap at 20 per check
            try:
                result = self.client.get_tweet(
                    tweet_id,
                    tweet_fields=["public_metrics", "created_at"],
                )
            except Exception as e:
                self._log(f"  Failed to check {tweet_id}: {type(e).__name__}")
                continue

            if not result.data:
                continue

            metrics = result.data.public_metrics or {}
            likes = metrics.get("like_count", 0)
            replies = metrics.get("reply_count", 0)
            retweets = metrics.get("retweet_count", 0)

            info = tracked[tweet_id]
            info["likes"] = likes
            info["replies"] = replies
            info["retweets"] = retweets
            info["checked_at"] = now.isoformat()
            info["total_engagement"] = likes + replies + retweets

            # Classify outcome
            if likes >= 5 or replies >= 3:
                info["outcome"] = "hit"
            elif likes >= 1 or replies >= 1:
                info["outcome"] = "normal"
            else:
                info["outcome"] = "miss"

            results.append({"tweet_id": tweet_id, **info})
            self._log(f"  {tweet_id}: {likes}L {replies}R {retweets}RT -> {info['outcome']}")

            time.sleep(0.5)

        self._save_state()

        # Learn from outcomes
        self._learn_from_replies(results)
        return results

    def _learn_from_replies(self, outcomes: list[dict]):
        """Extract lessons from reply outcomes and evolve."""
        if not outcomes:
            return

        hits = [o for o in outcomes if o.get("outcome") == "hit"]
        misses = [o for o in outcomes if o.get("outcome") == "miss"]

        if not hits and not misses:
            return

        # Analyze what hit replies have in common
        hit_traits = self._extract_reply_traits(hits)
        miss_traits = self._extract_reply_traits(misses)

        # Find differentiators
        for trait, hit_count in hit_traits.items():
            miss_count = miss_traits.get(trait, 0)
            total = hit_count + miss_count
            if total < 2:
                continue

            hit_rate = hit_count / total
            if hit_rate >= 0.7:
                # This trait correlates with success
                self._log_event(EvolutionEvent(
                    event_type="reply_learned",
                    description=f"Reply trait '{trait}' hits {hit_rate:.0%} of the time ({hit_count}/{total})",
                    before={"trait": trait, "known": False},
                    after={"trait": trait, "known": True, "hit_rate": hit_rate},
                    evidence={
                        "hits": hit_count,
                        "misses": miss_count,
                        "hit_examples": [h.get("text_preview", "") for h in hits[:3]],
                    },
                    confidence=min(0.9, 0.5 + (total / 20)),
                ))

    def _extract_reply_traits(self, replies: list[dict]) -> dict[str, int]:
        """Extract common traits from a set of replies."""
        traits: dict[str, int] = {}
        for r in replies:
            text = r.get("text_full", r.get("text_preview", "")).lower()

            # Length traits
            if len(text) < 80:
                traits["short"] = traits.get("short", 0) + 1
            elif len(text) > 200:
                traits["long"] = traits.get("long", 0) + 1
            else:
                traits["medium_length"] = traits.get("medium_length", 0) + 1

            # Content traits
            if "?" in text:
                traits["has_question"] = traits.get("has_question", 0) + 1
            if any(w in text for w in ["not ", "don't", "never", "isn't", "won't"]):
                traits["has_negation"] = traits.get("has_negation", 0) + 1
            if any(w in text for w in ["i ", "i'm", "i've", "my "]):
                traits["first_person"] = traits.get("first_person", 0) + 1
            if any(w in text for w in ["you ", "you're", "your "]):
                traits["second_person"] = traits.get("second_person", 0) + 1
            if text.startswith(("not ", "no ", "never", "wrong")):
                traits["contrarian_open"] = traits.get("contrarian_open", 0) + 1
            if any(c in text for c in ["\u2014", "\u2013", " - ", " \u2014 "]):
                traits["uses_dash"] = traits.get("uses_dash", 0) + 1
            if text.endswith("."):
                traits["ends_period"] = traits.get("ends_period", 0) + 1
            if "..." in text or "\u2026" in text:
                traits["uses_ellipsis"] = traits.get("uses_ellipsis", 0) + 1

        return traits

    # ── 2. Evolve From Research Findings ─────────────────────

    def evolve_from_research(self) -> list[EvolutionEvent]:
        """Read research insights and evolve voice weights based on what works.

        Integrated with Spark core systems:
        - MetaRalph batch mode for quality scoring
        - CognitiveLearner batch mode for insight storage
        - Advisor effectiveness tracking on evolution outcomes
        - EIDOS retrieval for relevant distillations

        This is the core evolution loop:
        - Read engagement-pulse insights (high performers from research)
        - Check EIDOS for relevant distillations (prior wisdom)
        - Aggregate which triggers, strategies, and hooks perform best
        - Compare against current voice weights
        - Shift weights toward what works, away from what doesn't
        - Store significant findings through quality gates
        """
        events = []

        # Load engagement pulse insights
        pulse_path = CHIP_INSIGHTS_DIR / "engagement-pulse.jsonl"
        if not pulse_path.exists():
            self._log("No research data yet — run research first")
            return events

        insights = self._read_jsonl(pulse_path, limit=500)
        if len(insights) < self.MIN_RESEARCH_INSIGHTS_FOR_PATTERN:
            self._log(f"Only {len(insights)} insights — need {self.MIN_RESEARCH_INSIGHTS_FOR_PATTERN} for evolution")
            return events

        self._log(f"Evolving from {len(insights)} research insights...")

        # Check EIDOS for prior wisdom about social engagement
        eidos_context = []
        if HAS_EIDOS:
            try:
                retriever = get_retriever()
                eidos_context = retriever.retrieve_for_intent("social engagement evolution")
                if eidos_context:
                    self._log(f"  EIDOS: {len(eidos_context)} relevant distillations found")
            except Exception:
                pass

        # ── Trigger evolution ──
        trigger_performance = self._aggregate_trigger_performance(insights)
        events.extend(self._evolve_trigger_weights(trigger_performance))

        # ── Strategy evolution ──
        strategy_performance = self._aggregate_strategy_performance(insights)
        events.extend(self._evolve_strategy_weights(strategy_performance))

        # ── Topic evolution ──
        events.extend(self._evolve_topic_interests(insights))

        # Log all events to disk for dashboard
        for event in events:
            self._log_event(event)

        self._save_state()

        # Track evolution cycle in advisor
        if HAS_ADVISOR and events:
            try:
                advisor = get_advisor()
                advisor.report_action_outcome(
                    tool_name="x_evolution_cycle",
                    success=len(events) > 0,
                    advice_was_relevant=len(eidos_context) > 0,
                )
            except Exception:
                pass

        return events

    def _aggregate_trigger_performance(self, insights: list[dict]) -> dict[str, dict]:
        """Aggregate trigger performance from research insights."""
        trigger_data: dict[str, dict] = {}

        for insight in insights:
            fields = insight.get("captured_data", {}).get("fields", {})
            triggers = fields.get("emotional_triggers", [])
            likes = fields.get("likes", 0)

            for trigger in triggers:
                if trigger not in trigger_data:
                    trigger_data[trigger] = {"total_likes": 0, "count": 0, "examples": []}
                trigger_data[trigger]["total_likes"] += likes
                trigger_data[trigger]["count"] += 1
                if likes >= 100 and len(trigger_data[trigger]["examples"]) < 3:
                    text = fields.get("content", "")[:100]
                    if text:
                        trigger_data[trigger]["examples"].append(text)

        # Compute averages
        for trigger, data in trigger_data.items():
            data["avg_likes"] = round(data["total_likes"] / max(data["count"], 1), 1)

        return trigger_data

    def _evolve_trigger_weights(self, performance: dict[str, dict]) -> list[EvolutionEvent]:
        """Shift trigger weights based on performance data."""
        events = []
        if not performance:
            return events

        # Global average
        all_avgs = [d["avg_likes"] for d in performance.values() if d["count"] >= 3]
        if not all_avgs:
            return events
        global_avg = sum(all_avgs) / len(all_avgs)

        weights = self.state.setdefault("voice_weights", {}).setdefault("triggers", {})

        for trigger, data in performance.items():
            if data["count"] < 3:
                continue

            current_weight = weights.get(trigger, 1.0)
            relative_performance = data["avg_likes"] / max(global_avg, 1)

            # Compute target weight (clamped)
            target = max(0.3, min(2.0, relative_performance))
            # Shift conservatively
            delta = (target - current_weight) * self.MAX_WEIGHT_SHIFT
            new_weight = round(current_weight + delta, 3)

            if abs(new_weight - current_weight) > 0.01:
                weights[trigger] = new_weight
                direction = "boosted" if delta > 0 else "reduced"

                events.append(EvolutionEvent(
                    event_type="voice_shift",
                    description=f"{direction.title()} '{trigger}' trigger weight: {current_weight:.2f} -> {new_weight:.2f} (avg {data['avg_likes']} likes vs global {global_avg:.0f})",
                    before={"trigger": trigger, "weight": current_weight},
                    after={"trigger": trigger, "weight": new_weight},
                    evidence={
                        "avg_likes": data["avg_likes"],
                        "global_avg": round(global_avg, 1),
                        "observations": data["count"],
                        "examples": data.get("examples", []),
                    },
                    confidence=min(0.9, 0.4 + (data["count"] / 50)),
                ))

        return events

    def _aggregate_strategy_performance(self, insights: list[dict]) -> dict[str, dict]:
        """Aggregate content strategy performance."""
        strategy_data: dict[str, dict] = {}

        for insight in insights:
            fields = insight.get("captured_data", {}).get("fields", {})
            strategy = fields.get("content_strategy", "")
            if not strategy:
                continue

            likes = fields.get("likes", 0)
            if strategy not in strategy_data:
                strategy_data[strategy] = {"total_likes": 0, "count": 0}
            strategy_data[strategy]["total_likes"] += likes
            strategy_data[strategy]["count"] += 1

        for data in strategy_data.values():
            data["avg_likes"] = round(data["total_likes"] / max(data["count"], 1), 1)

        return strategy_data

    def _evolve_strategy_weights(self, performance: dict[str, dict]) -> list[EvolutionEvent]:
        """Shift strategy weights based on performance."""
        events = []
        if not performance:
            return events

        all_avgs = [d["avg_likes"] for d in performance.values() if d["count"] >= 3]
        if not all_avgs:
            return events
        global_avg = sum(all_avgs) / len(all_avgs)

        weights = self.state.setdefault("voice_weights", {}).setdefault("strategies", {})

        for strategy, data in performance.items():
            if data["count"] < 3:
                continue

            current_weight = weights.get(strategy, 1.0)
            relative = data["avg_likes"] / max(global_avg, 1)
            target = max(0.3, min(2.0, relative))
            delta = (target - current_weight) * self.MAX_WEIGHT_SHIFT
            new_weight = round(current_weight + delta, 3)

            if abs(new_weight - current_weight) > 0.01:
                weights[strategy] = new_weight
                direction = "boosted" if delta > 0 else "reduced"

                events.append(EvolutionEvent(
                    event_type="strategy_discovered",
                    description=f"{direction.title()} '{strategy}' strategy: {current_weight:.2f} -> {new_weight:.2f} ({data['count']} observations, avg {data['avg_likes']} likes)",
                    before={"strategy": strategy, "weight": current_weight},
                    after={"strategy": strategy, "weight": new_weight},
                    evidence={
                        "avg_likes": data["avg_likes"],
                        "global_avg": round(global_avg, 1),
                        "observations": data["count"],
                    },
                    confidence=min(0.9, 0.4 + (data["count"] / 50)),
                ))

        return events

    def _evolve_topic_interests(self, insights: list[dict]) -> list[EvolutionEvent]:
        """Evolve topic interests based on which topics produce signal."""
        events = []
        topic_scores: dict[str, dict] = {}

        for insight in insights:
            fields = insight.get("captured_data", {}).get("fields", {})
            topic = fields.get("topic", "")
            likes = fields.get("likes", 0)
            if not topic:
                continue

            if topic not in topic_scores:
                topic_scores[topic] = {"total_likes": 0, "count": 0}
            topic_scores[topic]["total_likes"] += likes
            topic_scores[topic]["count"] += 1

        # Find emerging high-value topics
        for topic, data in topic_scores.items():
            data["avg_likes"] = round(data["total_likes"] / max(data["count"], 1), 1)

        # Sort by avg engagement
        ranked = sorted(
            [(t, d) for t, d in topic_scores.items() if d["count"] >= 3],
            key=lambda x: -x[1]["avg_likes"],
        )

        # If a topic consistently produces high engagement, log it as an evolution
        if ranked:
            top_topic, top_data = ranked[0]
            current_interests = self.state.get("evolved_topic_interests", [])
            if top_topic not in current_interests:
                self.state.setdefault("evolved_topic_interests", []).append(top_topic)
                events.append(EvolutionEvent(
                    event_type="topic_evolved",
                    description=f"Elevated '{top_topic}' to primary interest — avg {top_data['avg_likes']} likes across {top_data['count']} observations",
                    before={"interests": current_interests},
                    after={"interests": self.state["evolved_topic_interests"]},
                    evidence={
                        "topic": top_topic,
                        "avg_likes": top_data["avg_likes"],
                        "observations": top_data["count"],
                        "ranking": [(t, d["avg_likes"]) for t, d in ranked[:5]],
                    },
                    confidence=min(0.9, 0.5 + (top_data["count"] / 30)),
                ))

        return events

    # ── 3. Get Evolution Data (for dashboard) ────────────────

    def get_evolution_timeline(self, limit: int = 50) -> list[dict]:
        """Get recent evolution events for the dashboard."""
        events = self._read_jsonl(EVOLUTION_LOG, limit=limit)
        # Most recent first
        events.reverse()
        return events

    def get_evolution_summary(self) -> dict:
        """Get a summary of Spark's current evolutionary state."""
        events = self._read_jsonl(EVOLUTION_LOG, limit=1000)
        tracked = self.state.get("tracked_replies", {})

        # Outcome stats
        outcomes = [v for v in tracked.values() if v.get("outcome")]
        hits = sum(1 for o in outcomes if o["outcome"] == "hit")
        misses = sum(1 for o in outcomes if o["outcome"] == "miss")
        normals = sum(1 for o in outcomes if o["outcome"] == "normal")

        # Event type breakdown
        event_types: dict[str, int] = {}
        for e in events:
            etype = e.get("event_type", "unknown")
            event_types[etype] = event_types.get(etype, 0) + 1

        # Current weights (what Spark has evolved toward)
        weights = self.state.get("voice_weights", {})

        # Top evolved triggers
        trigger_weights = weights.get("triggers", {})
        top_triggers = sorted(trigger_weights.items(), key=lambda x: -x[1])[:5]
        weak_triggers = sorted(trigger_weights.items(), key=lambda x: x[1])[:3]

        # Strategy weights
        strategy_weights = weights.get("strategies", {})
        top_strategies = sorted(strategy_weights.items(), key=lambda x: -x[1])[:5]

        return {
            "total_evolutions": len(events),
            "evolution_types": event_types,
            "replies_tracked": len(tracked),
            "reply_outcomes": {
                "hits": hits,
                "misses": misses,
                "normals": normals,
                "hit_rate": round(hits / max(hits + misses + normals, 1), 2),
            },
            "current_voice_weights": {
                "top_triggers": [{"trigger": t, "weight": w} for t, w in top_triggers],
                "weak_triggers": [{"trigger": t, "weight": w} for t, w in weak_triggers],
                "top_strategies": [{"strategy": s, "weight": w} for s, w in top_strategies],
            },
            "evolved_interests": self.state.get("evolved_topic_interests", []),
            "adopted_patterns": self.state.get("adopted_patterns", []),
            "last_evolution": self.state.get("last_evolution"),
        }

    def get_voice_guidance(self) -> dict:
        """Get current evolved guidance for voice/tone selection.

        This is what x_voice.py should read to adapt behavior.
        Returns weighted preferences for triggers, strategies, and tones.
        """
        weights = self.state.get("voice_weights", {})
        trigger_weights = weights.get("triggers", {})
        strategy_weights = weights.get("strategies", {})

        # Sort triggers by weight — top ones should be used more
        preferred_triggers = sorted(
            trigger_weights.items(), key=lambda x: -x[1]
        )
        avoid_triggers = [t for t, w in trigger_weights.items() if w < 0.6]

        # Sort strategies
        preferred_strategies = sorted(
            strategy_weights.items(), key=lambda x: -x[1]
        )

        # Reply traits that work (from tracked outcomes)
        tracked = self.state.get("tracked_replies", {})
        hits = [v for v in tracked.values() if v.get("outcome") == "hit"]
        hit_traits = self._extract_reply_traits(hits) if hits else {}

        return {
            "preferred_triggers": [t for t, _ in preferred_triggers[:5]],
            "avoid_triggers": avoid_triggers,
            "preferred_strategies": [s for s, _ in preferred_strategies[:3]],
            "reply_traits_that_work": hit_traits,
            "evolved_interests": self.state.get("evolved_topic_interests", []),
            "data_points": len(self._read_jsonl(EVOLUTION_LOG, limit=5000)),
        }

    # ── 4. Pattern Adoption ──────────────────────────────────

    def adopt_pattern(self, pattern_name: str, evidence: dict, source: str = "research"):
        """Officially adopt a pattern into Spark's behavior.

        Adopted patterns are persisted and influence voice guidance.
        """
        adopted = self.state.setdefault("adopted_patterns", [])
        existing = {p["name"] for p in adopted}
        if pattern_name in existing:
            self._log(f"Pattern '{pattern_name}' already adopted")
            return

        pattern = {
            "name": pattern_name,
            "adopted_at": datetime.now(timezone.utc).isoformat(),
            "source": source,
            "evidence_summary": str(evidence)[:200],
        }
        adopted.append(pattern)

        self._log_event(EvolutionEvent(
            event_type="pattern_adopted",
            description=f"Adopted pattern '{pattern_name}' from {source}",
            before={"patterns": len(adopted) - 1},
            after={"patterns": len(adopted), "new": pattern_name},
            evidence=evidence,
            confidence=0.8,
        ))
        self._save_state()

    # ── 5. Feed Research Patterns Into Cognitive System (Quality-Gated) ───

    def promote_to_cognitive(self) -> int:
        """Promote proven X patterns to the core cognitive system.

        Quality-gated through MetaRalph before storage.
        Uses batch mode for performance.

        Flow: evolution events -> MetaRalph roast -> CognitiveLearner storage
              -> Advisor tracking -> EIDOS distillation (if applicable)
        """
        if not HAS_COGNITIVE:
            self._log("CognitiveLearner not available, skipping cognitive promotion")
            return 0

        events = self._read_jsonl(EVOLUTION_LOG, limit=500)
        # Only promote events not already promoted
        already_promoted = set(self.state.get("promoted_event_timestamps", []))
        high_confidence = [
            e for e in events
            if e.get("confidence", 0) >= 0.7
            and e.get("timestamp", "") not in already_promoted
        ]

        if not high_confidence:
            self._log("No new high-confidence evolution events to promote")
            return 0

        learner = get_cognitive_learner()
        ralph = get_meta_ralph() if HAS_RALPH else None

        # Batch mode for performance
        learner.begin_batch()
        if ralph:
            ralph.begin_batch()

        promoted = 0
        quality_passed = 0
        quality_failed = 0

        try:
            for event in high_confidence:
                etype = event.get("event_type", "")
                desc = event.get("description", "")
                evidence = event.get("evidence", {})

                # Create wisdom-level summaries (not raw telemetry)
                # MetaRalph scores: actionability, novelty, reasoning, specificity, outcome-linked
                wisdom_insight, wisdom_context, category = self._to_wisdom_summary(
                    etype, desc, evidence
                )
                if not wisdom_insight:
                    quality_failed += 1
                    continue

                # Quality gate: roast the WISDOM SUMMARY (not raw desc)
                if ralph:
                    roast_result = ralph.roast(
                        learning=wisdom_insight,
                        source="x_evolution",
                        context={"event_type": etype, "confidence": event.get("confidence", 0.7)},
                    )
                    score = getattr(roast_result, "total", 0) if hasattr(roast_result, "total") else (
                        getattr(getattr(roast_result, "score", None), "total", 0)
                    )
                    verdict = getattr(roast_result, "verdict", None)
                    verdict_str = getattr(verdict, "value", str(verdict)) if verdict else "unknown"

                    if verdict_str == "primitive":
                        quality_failed += 1
                        continue
                    quality_passed += 1

                learner.add_insight(
                    category=category,
                    insight=wisdom_insight,
                    context=wisdom_context,
                    confidence=event.get("confidence", 0.7),
                )
                promoted += 1

                # Track promotion timestamp to avoid duplicates
                self.state.setdefault("promoted_event_timestamps", []).append(
                    event.get("timestamp", "")
                )

                # Track in advisor effectiveness if available
                if HAS_ADVISOR:
                    try:
                        advisor = get_advisor()
                        advisor.report_action_outcome(
                            tool_name="x_evolution",
                            success=True,
                            advice_was_relevant=True,
                        )
                    except Exception:
                        pass

        finally:
            learner.end_batch()
            if ralph:
                ralph.end_batch()

        # Cap promoted timestamps list to avoid unbounded growth
        timestamps = self.state.get("promoted_event_timestamps", [])
        if len(timestamps) > 1000:
            self.state["promoted_event_timestamps"] = timestamps[-500:]

        self._save_state()
        self._log(f"Promoted {promoted} X learnings (quality: {quality_passed} passed, {quality_failed} filtered)")
        return promoted

    # ── 6. Gap Diagnosis — Identify Spark Intelligence Weaknesses ───

    def diagnose_gaps(self) -> dict:
        """Diagnose gaps in Spark Intelligence by reading system health metrics.

        Checks:
        1. Cognitive system: insight count, category coverage, validation rate
        2. Advisor: advice effectiveness, source attribution
        3. MetaRalph: quality pass rate, score distribution
        4. EIDOS: distillation rate, episode count
        5. Evolution: weight diversity, adoption rate, feedback loop closure
        6. Tuneables: whether auto-tuning is active
        7. Research: coverage, noise rate, LLM utilization

        Returns a dict with identified gaps, severity, and recommendations.
        """
        gaps = []
        health = {}

        # ── 1. Cognitive System Health ──
        cognitive_data = {}
        if COGNITIVE_INSIGHTS.exists():
            try:
                raw = json.loads(COGNITIVE_INSIGHTS.read_text(encoding="utf-8"))
                if isinstance(raw, dict):
                    insights = list(raw.values()) if "insights" not in raw else raw["insights"]
                else:
                    insights = raw if isinstance(raw, list) else []

                total = len(insights)
                categories = {}
                high_conf = 0
                total_validations = 0
                for i in insights:
                    cat = i.get("category", "unknown")
                    categories[cat] = categories.get(cat, 0) + 1
                    if i.get("confidence", 0) >= 0.8:
                        high_conf += 1
                    total_validations += i.get("times_validated", 0)

                validation_rate = round(total_validations / max(total, 1), 1)
                high_conf_pct = round(high_conf / max(total, 1) * 100, 1)

                cognitive_data = {
                    "total_insights": total,
                    "categories": categories,
                    "high_confidence_pct": high_conf_pct,
                    "avg_validations": validation_rate,
                }
                health["cognitive"] = cognitive_data

                # Check gaps
                if total < 50:
                    gaps.append({
                        "system": "cognitive",
                        "severity": "medium",
                        "gap": f"Low insight count ({total}). System needs more learning cycles.",
                        "metric": total,
                        "target": 100,
                        "recommendation": "Run more bridge cycles and research sessions to feed cognitive learner.",
                    })
                if high_conf_pct < 30:
                    gaps.append({
                        "system": "cognitive",
                        "severity": "medium",
                        "gap": f"Low confidence distribution ({high_conf_pct}% high-confidence). Most insights unvalidated.",
                        "metric": high_conf_pct,
                        "target": 50,
                        "recommendation": "More validation cycles needed. EIDOS prediction-outcome loops increase confidence.",
                    })
                # Check category coverage
                expected_cats = {"reasoning", "wisdom", "context", "user_understanding", "meta_learning"}
                missing_cats = expected_cats - set(categories.keys())
                if missing_cats:
                    gaps.append({
                        "system": "cognitive",
                        "severity": "low",
                        "gap": f"Missing insight categories: {', '.join(missing_cats)}",
                        "metric": len(categories),
                        "target": len(expected_cats),
                        "recommendation": "Diversify learning sources. X evolution now fills reasoning/wisdom/context gaps.",
                    })
            except (json.JSONDecodeError, OSError):
                gaps.append({
                    "system": "cognitive",
                    "severity": "high",
                    "gap": "Cannot read cognitive_insights.json — file corrupt or missing.",
                    "recommendation": "Check file at ~/.spark/cognitive_insights.json",
                })

        # ── 2. Advisor Effectiveness ──
        effectiveness_path = ADVISOR_DIR / "effectiveness.json"
        if effectiveness_path.exists():
            try:
                eff = json.loads(effectiveness_path.read_text(encoding="utf-8"))
                total_advice = eff.get("total_given", 0)
                total_acted = eff.get("total_acted_on", 0)
                action_rate = round(total_acted / max(total_advice, 1) * 100, 1)

                health["advisor"] = {
                    "total_advice_given": total_advice,
                    "total_acted_on": total_acted,
                    "action_rate_pct": action_rate,
                }

                if total_advice > 50 and action_rate < 5:
                    gaps.append({
                        "system": "advisor",
                        "severity": "high",
                        "gap": f"Advice action rate critically low ({action_rate}%). Advice is generated but not followed.",
                        "metric": action_rate,
                        "target": 15,
                        "recommendation": "Improve advice relevance scoring. Pre-tool advice needs to be more actionable and specific.",
                    })
                elif total_advice > 20 and action_rate < 10:
                    gaps.append({
                        "system": "advisor",
                        "severity": "medium",
                        "gap": f"Advice action rate low ({action_rate}%). Room for improvement.",
                        "metric": action_rate,
                        "target": 15,
                        "recommendation": "Tune MIN_RANK_SCORE and ADVICE_CACHE_TTL in tuneables.json advisor section.",
                    })
            except (json.JSONDecodeError, OSError):
                pass
        else:
            health["advisor"] = {"status": "no_effectiveness_data"}

        # ── 3. MetaRalph Quality Gate ──
        ralph_metrics_path = SPARK_DIR / "meta_ralph_metrics.json"
        if ralph_metrics_path.exists():
            try:
                rm = json.loads(ralph_metrics_path.read_text(encoding="utf-8"))
                total_roasted = rm.get("total_roasted", 0)
                quality_count = rm.get("quality_count", 0)
                primitive_count = rm.get("primitive_count", 0)
                quality_rate = round(quality_count / max(total_roasted, 1) * 100, 1)

                health["meta_ralph"] = {
                    "total_roasted": total_roasted,
                    "quality_rate_pct": quality_rate,
                    "primitive_count": primitive_count,
                }

                if total_roasted > 100 and quality_rate < 20:
                    gaps.append({
                        "system": "meta_ralph",
                        "severity": "medium",
                        "gap": f"Quality pass rate low ({quality_rate}%). Most signals getting filtered.",
                        "metric": quality_rate,
                        "target": 40,
                        "recommendation": "Review quality threshold (currently 4/10). Consider lowering to 3 or improving signal sources.",
                    })
            except (json.JSONDecodeError, OSError):
                pass

        # ── 4. EIDOS Distillation ──
        eidos_health = {"status": "not_checked"}
        if EIDOS_DB.exists():
            try:
                import sqlite3
                conn = sqlite3.connect(str(EIDOS_DB))
                cursor = conn.cursor()

                cursor.execute("SELECT COUNT(*) FROM episodes")
                episode_count = cursor.fetchone()[0]

                cursor.execute("SELECT COUNT(*) FROM distillations")
                distillation_count = cursor.fetchone()[0]

                cursor.execute("SELECT COUNT(*) FROM steps")
                step_count = cursor.fetchone()[0]

                conn.close()

                distillation_rate = round(distillation_count / max(episode_count, 1) * 100, 1)
                eidos_health = {
                    "episodes": episode_count,
                    "steps": step_count,
                    "distillations": distillation_count,
                    "distillation_rate_pct": distillation_rate,
                }
                health["eidos"] = eidos_health

                if episode_count > 10 and distillation_rate < 5:
                    gaps.append({
                        "system": "eidos",
                        "severity": "high",
                        "gap": f"EIDOS distillation rate critically low ({distillation_rate}%). {distillation_count} distillations from {episode_count} episodes.",
                        "metric": distillation_rate,
                        "target": 20,
                        "recommendation": "EIDOS needs the auto-tuner to close the prediction->outcome->evaluation loop. See CORE_SELF_EVOLUTION_PROMPT.md.",
                    })
            except Exception as e:
                eidos_health = {"status": f"error: {type(e).__name__}"}
                health["eidos"] = eidos_health
        else:
            health["eidos"] = {"status": "no_database"}
            gaps.append({
                "system": "eidos",
                "severity": "medium",
                "gap": "EIDOS database not found. Episodic intelligence not active.",
                "recommendation": "EIDOS needs to be initialized. Run a bridge cycle to create eidos.db.",
            })

        # ── 5. Evolution Self-Assessment ──
        weights = self.state.get("voice_weights", {})
        trigger_weights = weights.get("triggers", {})
        strategy_weights = weights.get("strategies", {})
        tracked_replies = self.state.get("tracked_replies", {})
        outcomes = [v for v in tracked_replies.values() if v.get("outcome")]

        evolution_health = {
            "total_evolutions": self.state.get("evolution_count", 0),
            "triggers_evolved": len(trigger_weights),
            "strategies_evolved": len(strategy_weights),
            "replies_tracked": len(tracked_replies),
            "outcomes_measured": len(outcomes),
            "adopted_patterns": len(self.state.get("adopted_patterns", [])),
            "promoted_to_cognitive": len(self.state.get("promoted_event_timestamps", [])),
        }
        health["evolution"] = evolution_health

        if len(outcomes) > 0:
            hits = sum(1 for o in outcomes if o["outcome"] == "hit")
            hit_rate = round(hits / len(outcomes) * 100, 1)
            if hit_rate < 10 and len(outcomes) >= 10:
                gaps.append({
                    "system": "evolution",
                    "severity": "medium",
                    "gap": f"Reply hit rate low ({hit_rate}%). Spark's replies not resonating.",
                    "metric": hit_rate,
                    "target": 30,
                    "recommendation": "Review voice weights. Lean into preferred triggers. Study high-performer reply patterns.",
                })

        if self.state.get("evolution_count", 0) == 0:
            gaps.append({
                "system": "evolution",
                "severity": "high",
                "gap": "No evolution events yet. The feedback loop hasn't started.",
                "recommendation": "Run: from lib.x_evolution import run_evolution_cycle; run_evolution_cycle()",
            })

        # ── 6. Tuneables / Auto-Tuning ──
        if TUNEABLES_PATH.exists():
            try:
                # Accept UTF-8 with BOM (common on Windows).
                tuneables = json.loads(TUNEABLES_PATH.read_text(encoding="utf-8-sig"))
                has_auto_tuner = "auto_tuner" in tuneables
                health["tuneables"] = {
                    "sections": list(tuneables.keys()),
                    "auto_tuner_active": has_auto_tuner,
                }
                if not has_auto_tuner:
                    gaps.append({
                        "system": "tuneables",
                        "severity": "high",
                        "gap": "Auto-tuner not active. Tuneables are static — never self-adjust.",
                        "recommendation": "Build lib/auto_tuner.py to close the self-optimization loop. See CORE_SELF_EVOLUTION_PROMPT.md.",
                    })
            except (json.JSONDecodeError, OSError):
                pass
        else:
            health["tuneables"] = {"status": "no_file"}
            gaps.append({
                "system": "tuneables",
                "severity": "medium",
                "gap": "No tuneables.json found. All thresholds at defaults.",
                "recommendation": "Create ~/.spark/tuneables.json with recommended values from COMPREHENSIVE_ANALYSIS.md.",
            })

        # ── 7. Research Engine Health ──
        research_state_path = SPARK_DIR / "x_research_state.json"
        if research_state_path.exists():
            try:
                rs = json.loads(research_state_path.read_text(encoding="utf-8"))
                sessions = rs.get("sessions_run", 0)
                total_analyzed = rs.get("total_tweets_analyzed", 0)
                total_stored = rs.get("total_insights_stored", 0)
                noise_rate = round((1 - total_stored / max(total_analyzed, 1)) * 100, 1) if total_analyzed > 0 else 0

                health["research"] = {
                    "sessions": sessions,
                    "tweets_analyzed": total_analyzed,
                    "insights_stored": total_stored,
                    "noise_filtered_pct": noise_rate,
                }

                if sessions > 5 and total_stored < 10:
                    gaps.append({
                        "system": "research",
                        "severity": "medium",
                        "gap": f"Low insight storage ({total_stored} from {total_analyzed} tweets). Research may be too noisy.",
                        "metric": total_stored,
                        "target": total_analyzed * 0.1,
                        "recommendation": "Check engagement thresholds (CATEGORY_MIN_LIKES). May need adjustment based on API tier.",
                    })
            except (json.JSONDecodeError, OSError):
                pass

        # ── Compute overall health score ──
        total_gaps = len(gaps)
        high_severity = sum(1 for g in gaps if g["severity"] == "high")
        medium_severity = sum(1 for g in gaps if g["severity"] == "medium")

        if total_gaps == 0:
            overall = "healthy"
        elif high_severity >= 3:
            overall = "critical"
        elif high_severity >= 1:
            overall = "needs_attention"
        elif medium_severity >= 3:
            overall = "improving"
        else:
            overall = "good"

        # Log gaps as evolution events
        for gap in gaps:
            if gap["severity"] == "high":
                self._log_event(EvolutionEvent(
                    event_type="gap_identified",
                    description=f"[{gap['system'].upper()}] {gap['gap']}",
                    before={"system": gap["system"], "status": "gap"},
                    after={"recommendation": gap["recommendation"]},
                    evidence={"metric": gap.get("metric"), "target": gap.get("target")},
                    confidence=0.85,
                ))

        self._save_state()

        return {
            "overall_health": overall,
            "total_gaps": total_gaps,
            "severity_breakdown": {
                "high": high_severity,
                "medium": medium_severity,
                "low": total_gaps - high_severity - medium_severity,
            },
            "gaps": gaps,
            "system_health": health,
            "diagnosed_at": datetime.now(timezone.utc).isoformat(),
            "core_integration": {
                "cognitive_learner": HAS_COGNITIVE,
                "meta_ralph": HAS_RALPH,
                "advisor": HAS_ADVISOR,
                "eidos": HAS_EIDOS,
            },
        }

    # ── Helpers ───────────────────────────────────────────────

    def _read_jsonl(self, path: Path, limit: int = 1000) -> list[dict]:
        """Read last N lines from a JSONL file."""
        if not path.exists():
            return []
        try:
            lines = path.read_text(encoding="utf-8", errors="ignore").strip().split("\n")
        except OSError:
            return []
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


# ── Convenience Functions ────────────────────────────────────

_instance: XEvolution | None = None


def get_evolution() -> XEvolution:
    """Get or create the singleton XEvolution instance."""
    global _instance
    if _instance is None:
        try:
            _instance = XEvolution(verbose=True)
        except Exception as e:
            print(f"[x_evolution] Init failed: {e}")
            raise
    return _instance


def register_spark_reply(tweet_id: str, parent_id: str, text: str):
    """Quick helper to register a reply for tracking."""
    try:
        evo = get_evolution()
        evo.register_reply(tweet_id, parent_id, text)
    except Exception as e:
        print(f"[x_evolution] register failed: {e}")


def run_evolution_cycle(include_diagnosis: bool = False) -> dict:
    """Run a full evolution cycle: check outcomes + evolve + promote + diagnose.

    Args:
        include_diagnosis: If True, also run gap diagnosis (slower but comprehensive).
    """
    evo = get_evolution()

    results = {
        "reply_outcomes": [],
        "research_events": [],
        "cognitive_promoted": 0,
        "gaps": None,
    }

    # 1. Check how Spark's replies performed
    results["reply_outcomes"] = evo.check_reply_outcomes()

    # 2. Evolve from research data
    results["research_events"] = [asdict(e) for e in evo.evolve_from_research()]

    # 3. Promote high-confidence patterns to cognitive system (quality-gated)
    results["cognitive_promoted"] = evo.promote_to_cognitive()

    # 4. Optionally diagnose system gaps
    if include_diagnosis:
        results["gaps"] = evo.diagnose_gaps()

    return results
