"""
PatternAggregator: Combines all detectors and routes to CognitiveLearner.

Responsibilities:
1. Run all detectors on each event
2. Aggregate patterns when multiple detectors corroborate
3. Trigger inference when confidence >= threshold
4. Route patterns to appropriate CognitiveLearner methods
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from .base import DetectedPattern, PatternType
from .correction import CorrectionDetector
from .sentiment import SentimentDetector
from .repetition import RepetitionDetector
from .sequence import SequenceDetector


# Confidence threshold to trigger learning
CONFIDENCE_THRESHOLD = 0.7

# Patterns log file
PATTERNS_LOG = Path.home() / ".spark" / "detected_patterns.jsonl"


def _log_pattern(pattern: DetectedPattern):
    """Append pattern to log file."""
    try:
        PATTERNS_LOG.parent.mkdir(parents=True, exist_ok=True)
        with open(PATTERNS_LOG, "a") as f:
            f.write(json.dumps(pattern.to_dict()) + "\n")
    except Exception:
        pass


class PatternAggregator:
    """
    Aggregates patterns from all detectors.

    Flow:
    1. Event comes in
    2. Each detector processes it
    3. Patterns above threshold trigger learning
    4. Corroborated patterns (multiple detectors) get boosted
    """

    def __init__(self):
        self.detectors = [
            CorrectionDetector(),
            SentimentDetector(),
            RepetitionDetector(),
            SequenceDetector(),
        ]
        self._patterns_count = 0
        self._session_patterns: Dict[str, List[DetectedPattern]] = {}

    def process_event(self, event: Dict) -> List[DetectedPattern]:
        """
        Process event through all detectors.

        Returns list of detected patterns.
        """
        all_patterns: List[DetectedPattern] = []

        for detector in self.detectors:
            try:
                patterns = detector.process_event(event)
                all_patterns.extend(patterns)
            except Exception as e:
                # Log but don't fail
                pass

        # Aggregate corroborating patterns
        all_patterns = self._boost_corroborated(all_patterns)

        # Track patterns by session
        session_id = event.get("session_id", "unknown")
        if session_id not in self._session_patterns:
            self._session_patterns[session_id] = []

        for pattern in all_patterns:
            self._patterns_count += 1
            self._session_patterns[session_id].append(pattern)
            _log_pattern(pattern)

        # Trim session patterns
        if len(self._session_patterns[session_id]) > 100:
            self._session_patterns[session_id] = self._session_patterns[session_id][-100:]

        return all_patterns

    def _boost_corroborated(self, patterns: List[DetectedPattern]) -> List[DetectedPattern]:
        """
        Boost confidence when multiple patterns support the same insight.

        For example:
        - Correction + Frustration = stronger signal
        - Repetition + Frustration = user really wants this
        """
        if len(patterns) < 2:
            return patterns

        # Check for corroborating combinations
        pattern_types = {p.pattern_type for p in patterns}

        # Frustration + Correction = very strong signal
        if PatternType.CORRECTION in pattern_types and PatternType.FRUSTRATION in pattern_types:
            for p in patterns:
                if p.pattern_type in (PatternType.CORRECTION, PatternType.FRUSTRATION):
                    p.confidence = min(0.99, p.confidence + 0.15)
                    p.evidence.append("CORROBORATED: Correction + Frustration detected together")

        # Repetition + Frustration = persistent issue
        if PatternType.REPETITION in pattern_types and PatternType.FRUSTRATION in pattern_types:
            for p in patterns:
                if p.pattern_type in (PatternType.REPETITION, PatternType.FRUSTRATION):
                    p.confidence = min(0.99, p.confidence + 0.1)
                    p.evidence.append("CORROBORATED: Repetition + Frustration detected together")

        # Sequence failure + Frustration = approach problem
        if PatternType.SEQUENCE_FAILURE in pattern_types and PatternType.FRUSTRATION in pattern_types:
            for p in patterns:
                if p.pattern_type in (PatternType.SEQUENCE_FAILURE, PatternType.FRUSTRATION):
                    p.confidence = min(0.99, p.confidence + 0.1)
                    p.evidence.append("CORROBORATED: Tool failures + Frustration")

        return patterns

    def trigger_learning(self, patterns: List[DetectedPattern]) -> List[Dict]:
        """
        Route patterns to CognitiveLearner for insight creation.

        Only patterns above CONFIDENCE_THRESHOLD trigger learning.
        """
        from ..cognitive_learner import get_cognitive_learner, CognitiveCategory

        learner = get_cognitive_learner()
        insights_created = []

        for pattern in patterns:
            if pattern.confidence < CONFIDENCE_THRESHOLD:
                continue

            if not pattern.suggested_insight:
                continue

            # Map pattern type to cognitive category
            category_map = {
                PatternType.CORRECTION: CognitiveCategory.USER_UNDERSTANDING,
                PatternType.SATISFACTION: CognitiveCategory.USER_UNDERSTANDING,
                PatternType.FRUSTRATION: CognitiveCategory.SELF_AWARENESS,
                PatternType.REPETITION: CognitiveCategory.USER_UNDERSTANDING,
                PatternType.SEQUENCE_SUCCESS: CognitiveCategory.REASONING,
                PatternType.SEQUENCE_FAILURE: CognitiveCategory.SELF_AWARENESS,
            }

            category = category_map.get(pattern.pattern_type, CognitiveCategory.CONTEXT)

            # Create insight
            insight = learner.add_insight(
                category=category,
                insight=pattern.suggested_insight,
                context=f"Detected from {pattern.pattern_type.value} pattern",
                confidence=pattern.confidence,
            )

            insights_created.append({
                "pattern_type": pattern.pattern_type.value,
                "insight": pattern.suggested_insight,
                "confidence": pattern.confidence,
            })

        return insights_created

    def get_session_patterns(self, session_id: str) -> List[DetectedPattern]:
        """Get all patterns detected for a session."""
        return self._session_patterns.get(session_id, [])

    def get_stats(self) -> Dict[str, Any]:
        """Get aggregator statistics."""
        return {
            "total_patterns_detected": self._patterns_count,
            "active_sessions": len(self._session_patterns),
            "detectors": [d.get_stats() for d in self.detectors],
        }


# Singleton instance
_aggregator: Optional[PatternAggregator] = None


def get_aggregator() -> PatternAggregator:
    """Get the global pattern aggregator instance."""
    global _aggregator
    if _aggregator is None:
        _aggregator = PatternAggregator()
    return _aggregator
