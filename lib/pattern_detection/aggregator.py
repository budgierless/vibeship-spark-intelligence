"""
PatternAggregator: Combines all detectors and routes to CognitiveLearner.

Responsibilities:
1. Run all detectors on each event
2. Aggregate patterns when multiple detectors corroborate
3. Trigger inference when confidence >= threshold
4. Route patterns to appropriate CognitiveLearner methods
"""

import json
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
import re

from .base import DetectedPattern, PatternType
from .correction import CorrectionDetector
from .sentiment import SentimentDetector
from .repetition import RepetitionDetector
from .semantic import SemanticIntentDetector
from .why import WhyDetector
from ..primitive_filter import is_primitive_text
from ..importance_scorer import get_importance_scorer, ImportanceTier


# Confidence threshold to trigger learning
CONFIDENCE_THRESHOLD = 0.7

# Patterns log file
PATTERNS_LOG = Path.home() / ".spark" / "detected_patterns.jsonl"
DEDUPE_TTL_SECONDS = 600


def _normalize_text(text: str) -> str:
    t = (text or "").strip().lower()
    t = re.sub(r"\s+", " ", t)
    t = re.sub(r"\s*\(\d+\s*calls?\)", "", t)
    t = re.sub(r"\s*\(\d+\)", "", t)
    return t.strip()


def _log_pattern(pattern: DetectedPattern):
    """Append pattern to log file."""
    try:
        PATTERNS_LOG.parent.mkdir(parents=True, exist_ok=True)
        with open(PATTERNS_LOG, "a") as f:
            f.write(json.dumps(pattern.to_dict()) + "\n")
    except Exception:
        pass


def _is_operational_insight(text: str) -> bool:
    """Return True for tool-telemetry or sequence-style insights."""
    try:
        from ..promoter import is_operational_insight
        return is_operational_insight(text)
    except Exception:
        return False


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
            SemanticIntentDetector(),
            WhyDetector(),  # Phase 4: Capture reasoning and principles
        ]
        self._patterns_count = 0
        self._session_patterns: Dict[str, List[DetectedPattern]] = {}
        self._recent_pattern_keys: Dict[str, Dict[str, float]] = {}
        # Importance scoring stats
        self._importance_stats = {
            "critical": 0,
            "high": 0,
            "medium": 0,
            "low": 0,
            "ignored": 0,
        }

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

        # De-dupe patterns within a TTL window to avoid spammy insights.
        all_patterns = self._dedupe_patterns(session_id, all_patterns)

        # Drop primitive/operational suggestions early.
        filtered: List[DetectedPattern] = []
        for pattern in all_patterns:
            suggested = pattern.suggested_insight or ""
            if suggested and is_primitive_text(suggested):
                continue
            filtered.append(pattern)
        all_patterns = filtered

        for pattern in all_patterns:
            self._patterns_count += 1
            self._session_patterns[session_id].append(pattern)
            _log_pattern(pattern)

        # Trim session patterns
        if len(self._session_patterns[session_id]) > 100:
            self._session_patterns[session_id] = self._session_patterns[session_id][-100:]

        return all_patterns

    def _pattern_key(self, pattern: DetectedPattern) -> str:
        base = pattern.suggested_insight or " ".join(pattern.evidence[:1]) or ""
        return f"{pattern.pattern_type.value}:{_normalize_text(base)}"

    def _dedupe_patterns(self, session_id: str, patterns: List[DetectedPattern]) -> List[DetectedPattern]:
        now = time.time()
        if session_id not in self._recent_pattern_keys:
            self._recent_pattern_keys[session_id] = {}

        recent = self._recent_pattern_keys[session_id]
        # Prune expired keys
        for k, ts in list(recent.items()):
            if now - ts > DEDUPE_TTL_SECONDS:
                del recent[k]

        out: List[DetectedPattern] = []
        for p in patterns:
            key = self._pattern_key(p)
            if not key or key in recent:
                continue
            recent[key] = now
            out.append(p)
        return out

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

        return patterns

    def trigger_learning(self, patterns: List[DetectedPattern]) -> List[Dict]:
        """
        Route patterns to CognitiveLearner for insight creation.

        Uses ImportanceScorer to assess importance at INGESTION time.
        This is the key improvement: importance != repetition.
        """
        from ..cognitive_learner import get_cognitive_learner, CognitiveCategory

        learner = get_cognitive_learner()
        scorer = get_importance_scorer()
        insights_created = []

        for pattern in patterns:
            if not pattern.suggested_insight:
                continue
            if is_primitive_text(pattern.suggested_insight):
                continue
            if _is_operational_insight(pattern.suggested_insight):
                continue

            # NEW: Score importance at ingestion, not just confidence
            importance = scorer.score(
                pattern.suggested_insight,
                context={
                    "source": pattern.pattern_type.value,
                    "has_outcome": bool(pattern.context.get("outcome")),
                }
            )

            # Combine pattern confidence with importance score
            # Critical/High importance can bypass low confidence threshold
            effective_confidence = pattern.confidence

            if importance.tier == ImportanceTier.CRITICAL:
                # Critical importance always learns, even with lower confidence
                effective_confidence = max(pattern.confidence, 0.85)
            elif importance.tier == ImportanceTier.HIGH:
                # High importance gets boosted
                effective_confidence = max(pattern.confidence, importance.score)
            elif importance.tier == ImportanceTier.IGNORE:
                # Ignore tier never learns
                self._importance_stats["ignored"] = self._importance_stats.get("ignored", 0) + 1
                continue

            # Apply original confidence threshold, but with importance-adjusted confidence
            if effective_confidence < CONFIDENCE_THRESHOLD:
                continue

            # Map pattern type to cognitive category (override if detector suggests one)
            category_map = {
                PatternType.CORRECTION: CognitiveCategory.USER_UNDERSTANDING,
                PatternType.SATISFACTION: CognitiveCategory.USER_UNDERSTANDING,
                PatternType.FRUSTRATION: CognitiveCategory.SELF_AWARENESS,
                PatternType.REPETITION: CognitiveCategory.USER_UNDERSTANDING,
                PatternType.STYLE: CognitiveCategory.USER_UNDERSTANDING,
            }

            category = category_map.get(pattern.pattern_type, CognitiveCategory.CONTEXT)
            if pattern.suggested_category:
                try:
                    category = CognitiveCategory(pattern.suggested_category)
                except Exception:
                    pass

            # Create insight with importance metadata
            insight = learner.add_insight(
                category=category,
                insight=pattern.suggested_insight,
                context=f"Detected from {pattern.pattern_type.value} pattern (importance: {importance.tier.value})",
                confidence=effective_confidence,
            )

            # Track importance distribution
            self._importance_stats[importance.tier.value] = (
                self._importance_stats.get(importance.tier.value, 0) + 1
            )

            insight_info = {
                "pattern_type": pattern.pattern_type.value,
                "insight": pattern.suggested_insight,
                "confidence": effective_confidence,
                "importance_tier": importance.tier.value,
                "importance_score": importance.score,
                "importance_reasons": importance.reasons,
            }

            # === INTELLIGENCE SYSTEM INTEGRATION ===

            # 1. Check for contradictions with existing beliefs
            try:
                from ..contradiction_detector import check_for_contradiction
                contradiction = check_for_contradiction(pattern.suggested_insight)
                if contradiction:
                    insight_info["contradiction_detected"] = {
                        "existing": contradiction.existing_text[:100],
                        "type": contradiction.contradiction_type.value,
                        "confidence": contradiction.confidence,
                    }
            except Exception:
                pass

            # 2. Identify knowledge gaps (what we don't know)
            try:
                from ..curiosity_engine import identify_knowledge_gaps
                gaps = identify_knowledge_gaps(pattern.suggested_insight)
                if gaps:
                    insight_info["knowledge_gaps"] = [
                        {"type": g.gap_type.value, "question": g.question}
                        for g in gaps[:2]
                    ]
            except Exception:
                pass

            # 3. Feed to hypothesis tracker (pattern -> hypothesis)
            try:
                from ..hypothesis_tracker import observe_for_hypothesis
                hypothesis = observe_for_hypothesis(
                    pattern.suggested_insight,
                    domain=pattern.context.get("domain", "")
                )
                if hypothesis:
                    insight_info["hypothesis_generated"] = {
                        "id": hypothesis.hypothesis_id,
                        "statement": hypothesis.statement[:100],
                        "confidence": hypothesis.confidence,
                    }
            except Exception:
                pass

            insights_created.append(insight_info)

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
            "importance_distribution": self._importance_stats,
        }


# Singleton instance
_aggregator: Optional[PatternAggregator] = None


def get_aggregator() -> PatternAggregator:
    """Get the global pattern aggregator instance."""
    global _aggregator
    if _aggregator is None:
        _aggregator = PatternAggregator()
    return _aggregator
