"""
SentimentDetector: Detects user satisfaction/frustration.

HIGH VALUE - Tracks emotional signals:

Satisfaction signals:
- "perfect", "great", "exactly", "thanks", "nice"
- Successful completion after few attempts

Frustration signals:
- "ugh", "still not working", "again?", "why"
- Multiple failed attempts
- Escalating language

This helps learn:
1. What approaches work well (satisfaction)
2. What approaches cause problems (frustration)
3. User patience thresholds
"""

import re
from typing import Any, Dict, List

from .base import DetectedPattern, PatternDetector, PatternType


# Satisfaction signals with confidence weights
SATISFACTION_PATTERNS = [
    # Strong positive
    (r"\bperfect\b", 0.95),
    (r"\bexactly\s+(what|right)", 0.9),
    (r"\bawesome\b", 0.85),
    (r"\bexcellent\b", 0.85),
    (r"\bamazing\b", 0.8),

    # Medium positive
    (r"\bgreat\b(?!\s+deal)", 0.75),  # "great" but not "great deal of trouble"
    (r"\bnice\b", 0.7),
    (r"\bgood\s+(job|work)\b", 0.8),
    (r"\bthanks?\b", 0.6),  # Thanks is weak signal alone
    (r"\bthank\s+you\b", 0.65),
    (r"\bthat\s+works\b", 0.75),
    (r"\blooks\s+good\b", 0.7),

    # Subtle positive
    (r"\byeah\s+that'?s\s+it\b", 0.75),
    (r"\byep\b", 0.6),
    (r"\bcool\b", 0.6),
    (r"\bnailed\s+it\b", 0.85),
]

# Frustration signals with confidence weights
FRUSTRATION_PATTERNS = [
    # Strong frustration
    (r"\bugh\b", 0.9),
    (r"\bstill\s+(not|doesn'?t|won'?t|can'?t)\s+work", 0.95),
    (r"\bwhy\s+(isn'?t|doesn'?t|won'?t|can'?t)", 0.85),
    (r"\bnot\s+again\b", 0.85),
    (r"\bagain\s*[?!]", 0.8),
    (r"\bwhat\s+the\b", 0.8),  # "what the heck/hell"

    # Medium frustration
    (r"\bfrustrat", 0.9),  # frustrated, frustrating
    (r"\bconfus", 0.7),    # confused, confusing
    (r"\bbroke\s+(it|something)\b", 0.8),
    (r"\bthis\s+is\s+(broken|wrong|bad)\b", 0.85),
    (r"\bsame\s+(error|problem|issue)\b", 0.8),
    (r"\bkeep\s+(getting|seeing|having)\b", 0.75),

    # Impatience
    (r"\bi\s+said\b", 0.7),  # "I said X, not Y"
    (r"\bi\s+already\s+(told|said|asked)\b", 0.85),
    (r"\bcome\s+on\b", 0.75),
    (r"\bseriously\s*[?!]", 0.8),
]

# Amplifiers that increase confidence
AMPLIFIERS = [
    (r"\breally\b", 0.1),
    (r"\bso\b", 0.1),
    (r"\bvery\b", 0.1),
    (r"[!]{2,}", 0.15),   # Multiple exclamation marks
    (r"[?]{2,}", 0.1),    # Multiple question marks
]


class SentimentDetector(PatternDetector):
    """
    Detects satisfaction and frustration signals.

    Tracks:
    - Explicit sentiment signals in text
    - Session sentiment trend (escalating frustration)
    - Context of what triggered the sentiment
    """

    def __init__(self):
        super().__init__("SentimentDetector")
        self._session_sentiment: Dict[str, List[Dict]] = {}  # session -> recent sentiments

    def _track_sentiment(self, session_id: str, sentiment: str, confidence: float):
        """Track sentiment for trend detection."""
        if session_id not in self._session_sentiment:
            self._session_sentiment[session_id] = []

        self._session_sentiment[session_id].append({
            "sentiment": sentiment,
            "confidence": confidence,
        })

        # Keep last 10
        if len(self._session_sentiment[session_id]) > 10:
            self._session_sentiment[session_id] = self._session_sentiment[session_id][-10:]

    def _get_trend(self, session_id: str) -> str:
        """Check if frustration is escalating."""
        history = self._session_sentiment.get(session_id, [])
        if len(history) < 3:
            return "neutral"

        # Count recent frustration signals
        recent = history[-5:]
        frustration_count = sum(1 for s in recent if s["sentiment"] == "frustration")

        if frustration_count >= 3:
            return "escalating_frustration"
        elif frustration_count >= 2:
            return "mild_frustration"
        return "neutral"

    def _calculate_confidence(self, text: str, base_confidence: float) -> float:
        """Adjust confidence based on amplifiers."""
        confidence = base_confidence
        text_lower = text.lower()

        for pattern, boost in AMPLIFIERS:
            if re.search(pattern, text_lower):
                confidence = min(0.99, confidence + boost)

        return confidence

    def process_event(self, event: Dict) -> List[DetectedPattern]:
        """Process event and detect sentiment patterns."""
        patterns: List[DetectedPattern] = []
        session_id = event.get("session_id", "unknown")
        hook_event = event.get("hook_event", "")

        # Only analyze user messages
        if hook_event != "UserPromptSubmit":
            return patterns

        payload = event.get("payload", {})
        text = payload.get("text", "") if isinstance(payload, dict) else ""

        if not text:
            text = event.get("prompt", "") or event.get("user_prompt", "")

        if not text:
            return patterns

        text_lower = text.lower()

        # Check satisfaction patterns
        best_satisfaction = None
        best_sat_confidence = 0.0

        for pattern, confidence in SATISFACTION_PATTERNS:
            match = re.search(pattern, text_lower)
            if match and confidence > best_sat_confidence:
                best_satisfaction = match
                best_sat_confidence = confidence

        # Check frustration patterns
        best_frustration = None
        best_frust_confidence = 0.0

        for pattern, confidence in FRUSTRATION_PATTERNS:
            match = re.search(pattern, text_lower)
            if match and confidence > best_frust_confidence:
                best_frustration = match
                best_frust_confidence = confidence

        # Emit strongest signal (satisfaction or frustration)
        if best_sat_confidence > best_frust_confidence and best_sat_confidence >= 0.6:
            final_confidence = self._calculate_confidence(text, best_sat_confidence)
            self._track_sentiment(session_id, "satisfaction", final_confidence)

            patterns.append(DetectedPattern(
                pattern_type=PatternType.SATISFACTION,
                confidence=final_confidence,
                evidence=[
                    f"User said: {text[:100]}...",
                    f"Matched: {best_satisfaction.group(0)}",
                ],
                context={
                    "user_text": text,
                    "signal": best_satisfaction.group(0),
                },
                session_id=session_id,
                suggested_insight="User expressed satisfaction with the response",
                suggested_category="user_understanding",
            ))

        elif best_frust_confidence >= 0.6:
            final_confidence = self._calculate_confidence(text, best_frust_confidence)
            self._track_sentiment(session_id, "frustration", final_confidence)

            # Check trend
            trend = self._get_trend(session_id)

            evidence = [
                f"User said: {text[:100]}...",
                f"Matched: {best_frustration.group(0)}",
            ]

            if trend == "escalating_frustration":
                evidence.append("TREND: Frustration is escalating")
                final_confidence = min(0.99, final_confidence + 0.1)

            patterns.append(DetectedPattern(
                pattern_type=PatternType.FRUSTRATION,
                confidence=final_confidence,
                evidence=evidence,
                context={
                    "user_text": text,
                    "signal": best_frustration.group(0),
                    "trend": trend,
                },
                session_id=session_id,
                suggested_insight="User expressed frustration with the response",
                suggested_category="self_awareness",
            ))

        # Buffer this event for context
        self._buffer_event(session_id, event)

        return patterns
