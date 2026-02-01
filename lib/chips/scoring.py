"""
Insight Scoring - Score insights for value and promotion.

Determines whether an insight is primitive (operational) or
valuable (cognitive) based on multiple dimensions.
"""

import re
import logging
from dataclasses import dataclass, asdict
from typing import Dict, List, Optional, Any, Set
from datetime import datetime

log = logging.getLogger("spark.chips.scoring")


@dataclass
class InsightScore:
    """Multi-dimensional score for an insight."""
    cognitive_value: float = 0.0    # Is this human-useful?
    outcome_linkage: float = 0.0    # Can we link to success/failure?
    uniqueness: float = 0.0         # Is this new information?
    actionability: float = 0.0      # Can this guide future actions?
    transferability: float = 0.0    # Applies beyond this project?
    domain_relevance: float = 0.0   # Relevant to active domain?

    @property
    def total(self) -> float:
        """Calculate weighted total score."""
        weights = {
            "cognitive_value": 0.30,
            "outcome_linkage": 0.20,
            "uniqueness": 0.15,
            "actionability": 0.15,
            "transferability": 0.10,
            "domain_relevance": 0.10,
        }
        return sum(getattr(self, k) * v for k, v in weights.items())

    @property
    def is_valuable(self) -> bool:
        """Quick check if insight is valuable enough."""
        return self.total >= 0.5

    @property
    def promotion_tier(self) -> str:
        """Determine promotion tier."""
        total = self.total
        if total >= 0.75:
            return "long_term"  # Permanent memory
        elif total >= 0.5:
            return "working"    # Project memory
        elif total >= 0.3:
            return "session"    # Session only
        else:
            return "discard"    # Don't store

    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        d = asdict(self)
        d["total"] = self.total
        d["promotion_tier"] = self.promotion_tier
        return d


# Patterns that indicate PRIMITIVE (operational) insights
PRIMITIVE_PATTERNS = [
    # Tool sequences
    r"(?i)^(read|edit|write|bash|glob|grep)\s*(->|→|then)\s*(read|edit|write|bash)",
    r"(?i)tool\s+(sequence|chain|pattern)",
    r"(?i)(success|failure)\s+rate",

    # Timing/metrics
    r"(?i)\d+\s*(ms|seconds?|minutes?)\s*(timeout|elapsed|took)",
    r"(?i)processed\s+\d+\s+(events?|files?|lines?)",

    # File operations without context
    r"(?i)^(modified|read|wrote|deleted)\s+file",
    r"(?i)^file\s+(exists|not found|created)",

    # Error counts without insight
    r"(?i)^\d+\s+errors?\s+(found|detected|fixed)",
]

# Patterns that indicate VALUABLE (cognitive) insights
VALUABLE_PATTERNS = [
    # Decisions and rationale
    r"(?i)(chose|decided|prefer|because|instead of|rather than)",
    r"(?i)(better|worse|tradeoff|balance)",

    # Domain knowledge
    r"(?i)(health|damage|physics|balance|gameplay)",  # Game
    r"(?i)(audience|campaign|brand|conversion)",      # Marketing
    r"(?i)(architecture|pattern|design|structure)",   # Engineering
    r"(?i)(user|customer|experience|feedback)",       # UX

    # Learning signals
    r"(?i)(learned|discovered|realized|found that)",
    r"(?i)(works better|fixed by|caused by|due to)",
    r"(?i)(should|shouldn't|must|avoid|prefer)",

    # Specific values with context
    r"(?i)(set|changed|adjusted|tuned)\s+\w+\s+to\s+\d+",
    r"(?i)\d+\s*(->|→|to)\s*\d+\s+(for|because|to)",
]

# Keywords that boost value
VALUE_BOOST_KEYWORDS = {
    "decision": 0.2,
    "rationale": 0.2,
    "preference": 0.15,
    "lesson": 0.2,
    "mistake": 0.15,
    "fixed": 0.1,
    "improved": 0.1,
    "because": 0.1,
    "tradeoff": 0.15,
    "balance": 0.1,
}

# Keywords that reduce value
VALUE_REDUCE_KEYWORDS = {
    "timeout": -0.1,
    "retry": -0.05,
    "sequence": -0.1,
    "pattern detected": -0.1,
    "tool used": -0.15,
    "file modified": -0.1,
}


class InsightScorer:
    """Score insights for promotion decisions."""

    def __init__(self):
        self._seen_content: Set[str] = set()
        self._domain_keywords: Dict[str, List[str]] = {
            "game_dev": ["health", "damage", "physics", "player", "enemy", "level", "spawn", "collision"],
            "marketing": ["audience", "campaign", "brand", "conversion", "engagement", "funnel"],
            "vibecoding": ["component", "hook", "state", "render", "api", "route", "deploy"],
            "biz-ops": ["revenue", "cost", "margin", "growth", "churn", "retention"],
        }

    def score(self, insight: Dict, context: Optional[Dict] = None) -> InsightScore:
        """Score an insight across all dimensions."""
        content = insight.get("content", "")
        captured_data = insight.get("captured_data", {})

        score = InsightScore(
            cognitive_value=self._score_cognitive_value(content, captured_data),
            uniqueness=self._score_uniqueness(content),
            actionability=self._score_actionability(content),
            transferability=self._score_transferability(content, captured_data),
            domain_relevance=self._score_domain_relevance(content, insight.get("chip_id"), context),
        )

        # Outcome linkage is scored separately when outcomes are detected
        score.outcome_linkage = insight.get("outcome_score", 0.0)

        return score

    def _score_cognitive_value(self, content: str, captured_data: Dict) -> float:
        """Score how cognitively valuable (human-useful) the insight is."""
        score = 0.5  # Start neutral

        # Check for primitive patterns (reduce score)
        for pattern in PRIMITIVE_PATTERNS:
            if re.search(pattern, content):
                score -= 0.2

        # Check for valuable patterns (increase score)
        for pattern in VALUABLE_PATTERNS:
            if re.search(pattern, content):
                score += 0.15

        # Check for value keywords
        content_lower = content.lower()
        for keyword, boost in VALUE_BOOST_KEYWORDS.items():
            if keyword in content_lower:
                score += boost

        for keyword, reduction in VALUE_REDUCE_KEYWORDS.items():
            if keyword in content_lower:
                score += reduction  # reduction is negative

        # Boost if there's meaningful change data
        if captured_data.get("change_summary"):
            change = captured_data["change_summary"]
            # Specific numbers with context are valuable
            if re.search(r"numbers?:\s*\[", change):
                score += 0.1
            if "added:" in change:
                score += 0.1

        # Ensure bounds
        return max(0.0, min(1.0, score))

    def _score_uniqueness(self, content: str) -> float:
        """Score how unique/new this insight is."""
        # Normalize content for comparison
        normalized = content.lower().strip()
        content_hash = hash(normalized)

        # Check if we've seen similar content
        if content_hash in self._seen_content:
            return 0.1  # Duplicate

        # Check for very similar content (fuzzy)
        for seen in self._seen_content:
            if self._similarity(normalized, seen) > 0.8:
                return 0.3  # Very similar

        # New content
        self._seen_content.add(normalized)
        return 0.9

    def _similarity(self, a: str, b: str) -> float:
        """Simple word-overlap similarity."""
        if isinstance(b, int):  # It's a hash
            return 0.0
        words_a = set(a.split())
        words_b = set(b.split())
        if not words_a or not words_b:
            return 0.0
        intersection = words_a & words_b
        union = words_a | words_b
        return len(intersection) / len(union)

    def _score_actionability(self, content: str) -> float:
        """Score how actionable the insight is."""
        score = 0.3  # Base

        # Actionable patterns
        actionable_patterns = [
            (r"(?i)(should|must|always|never|avoid|prefer)", 0.3),
            (r"(?i)(next time|in future|going forward)", 0.2),
            (r"(?i)(fix|solution|workaround|approach)", 0.2),
            (r"(?i)(set|use|configure|enable|disable)\s+\w+\s+to", 0.2),
        ]

        for pattern, boost in actionable_patterns:
            if re.search(pattern, content):
                score += boost

        return min(1.0, score)

    def _score_transferability(self, content: str, captured_data: Dict) -> float:
        """Score how transferable to other projects."""
        score = 0.3  # Base

        # Universal patterns transfer well
        universal_patterns = [
            (r"(?i)(always|never|best practice|anti-pattern)", 0.3),
            (r"(?i)(validate|test|check|verify) (input|output|data)", 0.2),
            (r"(?i)(error handling|edge case|boundary)", 0.2),
        ]

        for pattern, boost in universal_patterns:
            if re.search(pattern, content):
                score += boost

        # Project-specific patterns don't transfer
        specific_patterns = [
            (r"(?i)(this project|here we|in this codebase)", -0.2),
            (r"(?i)(file|path|directory)\s+['\"]?[A-Za-z0-9_/\\]+", -0.1),
        ]

        for pattern, reduction in specific_patterns:
            if re.search(pattern, content):
                score += reduction

        return max(0.0, min(1.0, score))

    def _score_domain_relevance(self, content: str, chip_id: Optional[str], context: Optional[Dict]) -> float:
        """Score relevance to the active domain."""
        if not chip_id:
            return 0.5  # Neutral

        # Check if content matches domain keywords
        keywords = self._domain_keywords.get(chip_id, [])
        if not keywords:
            return 0.5

        content_lower = content.lower()
        matches = sum(1 for kw in keywords if kw in content_lower)

        if matches == 0:
            return 0.2  # Triggered but not relevant
        elif matches == 1:
            return 0.6
        elif matches == 2:
            return 0.8
        else:
            return 1.0

    def score_batch(self, insights: List[Dict], context: Optional[Dict] = None) -> List[tuple]:
        """Score a batch of insights."""
        results = []
        for insight in insights:
            score = self.score(insight, context)
            results.append((insight, score))
        return results

    def filter_valuable(self, insights: List[Dict], threshold: float = 0.5) -> List[tuple]:
        """Filter to only valuable insights."""
        scored = self.score_batch(insights)
        return [(i, s) for i, s in scored if s.total >= threshold]


# Singleton scorer
_scorer: Optional[InsightScorer] = None


def get_scorer() -> InsightScorer:
    """Get singleton scorer instance."""
    global _scorer
    if _scorer is None:
        _scorer = InsightScorer()
    return _scorer


def score_insight(insight: Dict, context: Optional[Dict] = None) -> InsightScore:
    """Score a single insight (convenience function)."""
    return get_scorer().score(insight, context)
