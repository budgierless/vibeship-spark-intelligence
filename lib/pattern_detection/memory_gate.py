"""
MemoryGate: Decides what earns persistence.

The key insight from the EIDOS architecture:
> "Memory quality usually fails because everything gets stored."

This module provides scoring functions to determine if a piece of
information (Step, Distillation, or raw insight) should become
durable memory.

Scoring criteria:
- Impact: Did it unblock progress?
- Novelty: Is this a new pattern?
- Surprise: Did prediction match outcome?
- Recurrence: Has this happened multiple times?
- Irreversibility: Is this high-stakes?
- Evidence quality: Is there validation?

Only high-signal items (score > threshold) become durable memory.
Low-score items stay as short-lived cache only.
"""

import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set

from ..eidos.models import Step, Distillation, Evaluation


@dataclass
class GateScore:
    """Result of memory gate scoring."""
    score: float
    passes: bool
    reasons: List[str] = field(default_factory=list)
    breakdown: Dict[str, float] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "score": round(self.score, 3),
            "passes": self.passes,
            "reasons": self.reasons,
            "breakdown": {k: round(v, 3) for k, v in self.breakdown.items()},
        }


class MemoryGate:
    """
    Decides what earns persistence in durable memory.

    This is the quality control layer that prevents memory bloat
    while ensuring valuable insights are captured.

    Usage:
        gate = MemoryGate()
        score = gate.score_step(step)
        if score.passes:
            store.save_step(step)
    """

    # Default scoring weights
    WEIGHTS = {
        "impact": 0.30,      # Did it unblock progress?
        "novelty": 0.20,     # Is this new?
        "surprise": 0.30,    # Was outcome unexpected?
        "recurrence": 0.20,  # Multiple occurrences?
        "irreversible": 0.60, # High stakes? (raised from 0.40 - should dominate)
        "evidence": 0.10,    # Has validation?
    }

    # Keywords indicating high-stakes actions
    HIGH_STAKES_KEYWORDS = frozenset({
        "deploy", "production", "delete", "remove", "drop",
        "security", "auth", "authentication", "payment", "billing",
        "secret", "credential", "password", "key", "token",
        "database", "migration", "rollback", "backup",
    })

    def __init__(
        self,
        threshold: float = 0.5,
        weights: Optional[Dict[str, float]] = None,
        seen_patterns: Optional[Set[str]] = None
    ):
        """
        Initialize the memory gate.

        Args:
            threshold: Minimum score to pass (default 0.5)
            weights: Custom scoring weights
            seen_patterns: Set of previously seen pattern keys for novelty detection
        """
        self.threshold = threshold
        self.weights = weights or self.WEIGHTS.copy()
        self.seen_patterns = seen_patterns or set()

        # Statistics
        self._stats = {
            "total_evaluated": 0,
            "passed": 0,
            "rejected": 0,
            "avg_score": 0.0,
        }

    def score_step(self, step: Step) -> GateScore:
        """
        Score a Step for persistence worthiness.

        Args:
            step: The EIDOS Step to evaluate

        Returns:
            GateScore with score, pass/fail, and breakdown
        """
        self._stats["total_evaluated"] += 1

        score = 0.0
        reasons = []
        breakdown = {}

        # Impact: Did it make progress?
        impact_score = self._score_impact(step)
        score += impact_score
        breakdown["impact"] = impact_score
        if impact_score > 0:
            reasons.append(f"impact:{impact_score:.2f}")

        # Novelty: Is this new?
        novelty_score = self._score_novelty_step(step)
        score += novelty_score
        breakdown["novelty"] = novelty_score
        if novelty_score > 0:
            reasons.append("novelty:new_pattern")

        # Surprise: Prediction != outcome?
        surprise_score = self._score_surprise(step)
        score += surprise_score
        breakdown["surprise"] = surprise_score
        if surprise_score > 0:
            reasons.append(f"surprise:{step.surprise_level:.2f}")

        # Evidence: Has validation?
        evidence_score = self._score_evidence(step)
        score += evidence_score
        breakdown["evidence"] = evidence_score
        if evidence_score > 0:
            reasons.append("validated")

        # Irreversible: High stakes?
        stakes_score = self._score_stakes(step.intent + " " + step.decision)
        score += stakes_score
        breakdown["irreversible"] = stakes_score
        if stakes_score > 0:
            reasons.append("high_stakes")

        # Lesson quality: Has meaningful lesson?
        lesson_score = self._score_lesson(step)
        score += lesson_score
        breakdown["lesson"] = lesson_score
        if lesson_score > 0:
            reasons.append("has_lesson")

        passes = score >= self.threshold

        if passes:
            self._stats["passed"] += 1
        else:
            self._stats["rejected"] += 1

        # Update running average
        n = self._stats["total_evaluated"]
        self._stats["avg_score"] = (
            (self._stats["avg_score"] * (n - 1) + score) / n
        )

        return GateScore(
            score=score,
            passes=passes,
            reasons=reasons,
            breakdown=breakdown,
        )

    def score_distillation(self, distillation: Distillation, source_steps: Optional[List[Step]] = None) -> GateScore:
        """
        Score a Distillation for persistence worthiness.

        Args:
            distillation: The Distillation to evaluate
            source_steps: Optional source steps for richer scoring

        Returns:
            GateScore with score, pass/fail, and breakdown
        """
        self._stats["total_evaluated"] += 1

        score = 0.0
        reasons = []
        breakdown = {}

        # Evidence: Has source steps?
        if distillation.source_steps:
            evidence = min(len(distillation.source_steps) * 0.1, 0.3)
            score += evidence
            breakdown["evidence"] = evidence
            reasons.append(f"evidence:{len(distillation.source_steps)}_steps")

        # Confidence: High confidence?
        if distillation.confidence > 0.7:
            conf_score = self.weights["impact"] * (distillation.confidence - 0.5)
            score += conf_score
            breakdown["confidence"] = conf_score
            reasons.append(f"confidence:{distillation.confidence:.2f}")

        # Actionable: Has triggers?
        if distillation.triggers:
            score += 0.2
            breakdown["actionable"] = 0.2
            reasons.append("actionable")

        # Specificity: Not too generic?
        if len(distillation.statement) > 30 and len(distillation.statement) < 500:
            score += 0.1
            breakdown["specific"] = 0.1
            reasons.append("specific")

        # High stakes?
        stakes_score = self._score_stakes(distillation.statement)
        score += stakes_score
        breakdown["irreversible"] = stakes_score
        if stakes_score > 0:
            reasons.append("high_stakes")

        # Novelty: Not duplicate?
        novelty_score = self._score_novelty_distillation(distillation)
        score += novelty_score
        breakdown["novelty"] = novelty_score
        if novelty_score > 0:
            reasons.append("novel")

        # If source steps provided, analyze them too
        if source_steps:
            # Progress made across steps
            progress_count = sum(1 for s in source_steps if s.progress_made)
            if progress_count > len(source_steps) * 0.5:
                score += 0.15
                breakdown["step_impact"] = 0.15
                reasons.append("steps_made_progress")

        passes = score >= self.threshold

        if passes:
            self._stats["passed"] += 1
        else:
            self._stats["rejected"] += 1

        n = self._stats["total_evaluated"]
        self._stats["avg_score"] = (
            (self._stats["avg_score"] * (n - 1) + score) / n
        )

        return GateScore(
            score=score,
            passes=passes,
            reasons=reasons,
            breakdown=breakdown,
        )

    def score_raw_insight(self, text: str, context: Optional[Dict] = None) -> GateScore:
        """
        Score a raw insight text for persistence worthiness.

        This is for backward compatibility with cognitive_learner patterns
        that don't have full EIDOS structure.

        Args:
            text: The insight text
            context: Optional context dict

        Returns:
            GateScore with score, pass/fail, and breakdown
        """
        self._stats["total_evaluated"] += 1
        context = context or {}

        score = 0.0
        reasons = []
        breakdown = {}

        # Skip empty or very short
        if not text or len(text) < 10:
            return GateScore(score=0, passes=False, reasons=["too_short"])

        # Novelty
        pattern_key = self._normalize_for_dedup(text)
        if pattern_key not in self.seen_patterns:
            score += self.weights["novelty"]
            breakdown["novelty"] = self.weights["novelty"]
            reasons.append("novel")
            self.seen_patterns.add(pattern_key)

        # High stakes keywords
        stakes_score = self._score_stakes(text)
        score += stakes_score
        breakdown["irreversible"] = stakes_score
        if stakes_score > 0:
            reasons.append("high_stakes")

        # Specificity: Not too generic
        if len(text) > 30 and len(text) < 500:
            score += 0.15
            breakdown["specific"] = 0.15
            reasons.append("specific")

        # Has context from outcome?
        if context.get("has_outcome"):
            score += 0.2
            breakdown["has_outcome"] = 0.2
            reasons.append("outcome_linked")

        # Recurrence if provided
        if context.get("occurrence_count", 0) >= 3:
            score += self.weights["recurrence"]
            breakdown["recurrence"] = self.weights["recurrence"]
            reasons.append(f"recurrence:{context['occurrence_count']}")

        passes = score >= self.threshold

        if passes:
            self._stats["passed"] += 1
        else:
            self._stats["rejected"] += 1

        n = self._stats["total_evaluated"]
        self._stats["avg_score"] = (
            (self._stats["avg_score"] * (n - 1) + score) / n
        )

        return GateScore(
            score=score,
            passes=passes,
            reasons=reasons,
            breakdown=breakdown,
        )

    # ==================== Scoring Components ====================

    def _score_impact(self, step: Step) -> float:
        """Score based on whether step made progress."""
        if step.progress_made:
            return self.weights["impact"]
        if step.evidence_gathered:
            return self.weights["impact"] * 0.5
        return 0.0

    def _score_novelty_step(self, step: Step) -> float:
        """Score based on whether step represents a new pattern."""
        # Create a normalized key for deduplication
        key = self._normalize_for_dedup(f"{step.intent}:{step.decision}")

        if key in self.seen_patterns:
            return 0.0

        self.seen_patterns.add(key)
        return self.weights["novelty"]

    def _score_novelty_distillation(self, distillation: Distillation) -> float:
        """Score based on whether distillation is novel."""
        key = self._normalize_for_dedup(distillation.statement)

        if key in self.seen_patterns:
            return 0.0

        self.seen_patterns.add(key)
        return self.weights["novelty"]

    def _score_surprise(self, step: Step) -> float:
        """Score based on surprise level (prediction != outcome)."""
        if step.surprise_level >= 0.5:
            return self.weights["surprise"]
        if step.surprise_level >= 0.3:
            return self.weights["surprise"] * 0.5
        return 0.0

    def _score_evidence(self, step: Step) -> float:
        """Score based on validation quality."""
        if step.validated and step.validation_evidence:
            return self.weights["evidence"]
        if step.validated:
            return self.weights["evidence"] * 0.5
        return 0.0

    def _score_stakes(self, text: str) -> float:
        """Score based on presence of high-stakes keywords."""
        text_lower = text.lower()
        matches = sum(1 for kw in self.HIGH_STAKES_KEYWORDS if kw in text_lower)

        if matches >= 2:
            return self.weights["irreversible"]
        if matches == 1:
            return self.weights["irreversible"] * 0.5
        return 0.0

    def _score_lesson(self, step: Step) -> float:
        """Score based on lesson quality."""
        if not step.lesson:
            return 0.0
        if len(step.lesson) < 20:
            return 0.0
        if len(step.lesson) > 50:
            return 0.15
        return 0.1

    def _normalize_for_dedup(self, text: str) -> str:
        """Normalize text for deduplication."""
        if not text:
            return ""
        # Lowercase, remove extra whitespace, keep alphanumeric
        normalized = re.sub(r'\s+', ' ', text.lower().strip())
        normalized = re.sub(r'[^a-z0-9 ]', '', normalized)
        # Take first 100 chars for key
        return normalized[:100]

    # ==================== Batch Operations ====================

    def filter_steps(self, steps: List[Step]) -> List[Step]:
        """
        Filter steps to only those that pass the memory gate.

        Args:
            steps: List of steps to filter

        Returns:
            Steps that pass the gate
        """
        return [s for s in steps if self.score_step(s).passes]

    def filter_distillations(
        self,
        distillations: List[Distillation],
        source_steps_map: Optional[Dict[str, List[Step]]] = None
    ) -> List[Distillation]:
        """
        Filter distillations to only those that pass the memory gate.

        Args:
            distillations: List of distillations to filter
            source_steps_map: Optional mapping of distillation_id to source steps

        Returns:
            Distillations that pass the gate
        """
        source_steps_map = source_steps_map or {}

        return [
            d for d in distillations
            if self.score_distillation(
                d,
                source_steps_map.get(d.distillation_id)
            ).passes
        ]

    def get_stats(self) -> Dict[str, Any]:
        """Get gate statistics."""
        return {
            **self._stats,
            "threshold": self.threshold,
            "seen_patterns_count": len(self.seen_patterns),
            "pass_rate": (
                self._stats["passed"] / max(self._stats["total_evaluated"], 1)
            ),
        }

    def reset_seen_patterns(self):
        """Reset the seen patterns set (useful for testing or new sessions)."""
        self.seen_patterns.clear()


# Singleton instance
_gate: Optional[MemoryGate] = None


def get_memory_gate() -> MemoryGate:
    """Get the global memory gate instance."""
    global _gate
    if _gate is None:
        _gate = MemoryGate()
    return _gate
