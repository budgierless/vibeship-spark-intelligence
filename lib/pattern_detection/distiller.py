"""
PatternDistiller: Convert detected patterns into EIDOS Distillations.

This is the bridge between pattern detection and durable intelligence.
Instead of storing raw "User persistently asking about X" insights,
we distill patterns into actionable rules:

- HEURISTIC: "When X, do Y" (from successful patterns)
- ANTI_PATTERN: "Never do X because..." (from failed patterns)
- SHARP_EDGE: "Watch out for X in context Y" (from surprises)
- PLAYBOOK: Step-by-step procedure (from repeated sequences)

Only patterns that pass the memory gate become Distillations.
"""

import hashlib
import re
import time
from collections import Counter
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

from ..eidos.models import (
    Step, Distillation, DistillationType, Evaluation, ActionType
)
from ..eidos.store import get_store


@dataclass
class DistillationCandidate:
    """A potential distillation before memory gate scoring."""
    distillation: Distillation
    source_steps: List[Step]
    gate_score: float = 0.0
    gate_reasons: List[str] = None

    def __post_init__(self):
        if self.gate_reasons is None:
            self.gate_reasons = []


class PatternDistiller:
    """
    Analyze completed Steps and extract Distillations.

    This transforms the pattern detection output from noise into intelligence:
    - Groups similar steps by intent
    - Identifies successful vs failed patterns
    - Extracts generalizable rules
    - Applies memory gate to filter low-value distillations

    The key insight: We don't store "User wanted X" - we store
    "When user wants X, approach Y works because Z"
    """

    def __init__(
        self,
        min_occurrences: int = 2,  # Lowered from 3 for faster learning
        min_occurrences_critical: int = 1,  # CRITICAL tier: learn from single occurrence
        min_confidence: float = 0.6,
        gate_threshold: float = 0.5
    ):
        """
        Initialize the distiller.

        Args:
            min_occurrences: Minimum times a pattern must occur (default)
            min_occurrences_critical: Minimum for CRITICAL importance (fast-track)
            min_confidence: Minimum confidence for a distillation
            gate_threshold: Memory gate score threshold
        """
        self.min_occurrences = min_occurrences
        self.min_occurrences_critical = min_occurrences_critical
        self.min_confidence = min_confidence
        self.gate_threshold = gate_threshold
        self.store = get_store()

        # Statistics
        self._stats = {
            "steps_analyzed": 0,
            "candidates_generated": 0,
            "distillations_created": 0,
            "gate_rejections": 0,
            "critical_fast_tracked": 0,  # CRITICAL tier fast-track count
        }

    def distill_from_steps(self, steps: List[Step]) -> List[Distillation]:
        """
        Analyze completed Steps and extract Distillations.

        This is the main entry point. It:
        1. Groups steps by similar intent
        2. Analyzes success/failure patterns
        3. Generates distillation candidates
        4. Applies memory gate
        5. Saves passing distillations

        Args:
            steps: Completed Steps to analyze

        Returns:
            List of created Distillations
        """
        self._stats["steps_analyzed"] += len(steps)

        # Filter to only evaluated steps
        evaluated = [s for s in steps if s.evaluation != Evaluation.UNKNOWN]
        if len(evaluated) < self.min_occurrences:
            return []

        distillations = []

        # Strategy 1: User request patterns (heuristics/anti-patterns)
        user_distillations = self._distill_user_patterns(evaluated)
        distillations.extend(user_distillations)

        # Strategy 2: Tool effectiveness patterns
        tool_distillations = self._distill_tool_patterns(evaluated)
        distillations.extend(tool_distillations)

        # Strategy 3: Surprise patterns (sharp edges)
        surprise_distillations = self._distill_surprises(evaluated)
        distillations.extend(surprise_distillations)

        # Strategy 4: Lesson consolidation
        lesson_distillations = self._distill_lessons(evaluated)
        distillations.extend(lesson_distillations)

        return distillations

    # ==================== Strategy 1: User Patterns ====================

    def _distill_user_patterns(self, steps: List[Step]) -> List[Distillation]:
        """
        Distill patterns from user request handling.

        Groups steps by normalized intent and extracts:
        - HEURISTIC when success rate is high
        - ANTI_PATTERN when failure rate is high
        """
        distillations = []

        # Group by normalized intent
        intent_groups = self._group_by_intent(steps)

        for intent_key, group_steps in intent_groups.items():
            if len(group_steps) < self.min_occurrences:
                continue

            candidate = self._analyze_intent_group(intent_key, group_steps)
            if candidate and self._apply_memory_gate(candidate):
                # Save to store
                self.store.save_distillation(candidate.distillation)
                distillations.append(candidate.distillation)
                self._stats["distillations_created"] += 1
            elif candidate:
                self._stats["gate_rejections"] += 1

        return distillations

    def _group_by_intent(self, steps: List[Step]) -> Dict[str, List[Step]]:
        """Group steps by normalized intent for pattern analysis."""
        groups: Dict[str, List[Step]] = {}

        for step in steps:
            key = self._normalize_intent(step.intent)
            if key not in groups:
                groups[key] = []
            groups[key].append(step)

        return groups

    def _normalize_intent(self, intent: str) -> str:
        """Normalize intent for grouping similar requests."""
        if not intent:
            return "unknown"

        intent_lower = intent.lower()

        # Remove common prefixes
        for prefix in ["fulfill user request:", "user wants:", "request:"]:
            if intent_lower.startswith(prefix):
                intent_lower = intent_lower[len(prefix):].strip()

        # Extract action verbs
        action_keywords = {
            "push": "git_operations",
            "commit": "git_operations",
            "fix": "bug_fixing",
            "bug": "bug_fixing",
            "add": "feature_addition",
            "create": "feature_addition",
            "remove": "deletion",
            "delete": "deletion",
            "clean": "cleanup",
            "refactor": "refactoring",
            "test": "testing",
            "deploy": "deployment",
            "update": "modification",
            "change": "modification",
        }

        for keyword, category in action_keywords.items():
            if keyword in intent_lower:
                return f"intent:{category}"

        # Fallback: first 30 chars normalized
        normalized = re.sub(r'\s+', '_', intent_lower[:30])
        normalized = re.sub(r'[^a-z0-9_]', '', normalized)
        return f"intent:{normalized}"

    def _analyze_intent_group(
        self,
        intent_key: str,
        steps: List[Step]
    ) -> Optional[DistillationCandidate]:
        """Analyze a group of similar-intent steps and create distillation."""
        successes = [s for s in steps if s.evaluation == Evaluation.PASS]
        failures = [s for s in steps if s.evaluation == Evaluation.FAIL]

        total = len(successes) + len(failures)
        if total == 0:
            return None

        success_rate = len(successes) / total

        if success_rate >= self.min_confidence:
            # Create HEURISTIC from successful pattern
            return self._create_heuristic_candidate(intent_key, successes, success_rate)
        elif success_rate <= (1 - self.min_confidence):
            # Create ANTI_PATTERN from failure pattern
            return self._create_anti_pattern_candidate(intent_key, failures, 1 - success_rate)

        # No clear pattern
        return None

    def _create_heuristic_candidate(
        self,
        intent_key: str,
        successes: List[Step],
        confidence: float
    ) -> DistillationCandidate:
        """Create a HEURISTIC distillation from successful patterns."""
        # Find most common successful approach
        decisions = [s.decision for s in successes if s.decision and s.decision != "pending"]
        if not decisions:
            return None

        best_decision = Counter(decisions).most_common(1)[0][0]

        # Extract the intent category
        intent_desc = intent_key.replace("intent:", "").replace("_", " ")

        # Combine lessons for richer context
        lessons = [s.lesson for s in successes if s.lesson]
        combined_lesson = "; ".join(set(lessons[:3])) if lessons else ""

        distillation = Distillation(
            distillation_id="",  # Auto-generated
            type=DistillationType.HEURISTIC,
            statement=f"When user requests {intent_desc}, use approach: {best_decision[:150]}",
            domains=["user_interaction", intent_desc],
            triggers=[intent_key, intent_desc],
            source_steps=[s.step_id for s in successes[:10]],
            confidence=confidence,
        )

        self._stats["candidates_generated"] += 1

        return DistillationCandidate(
            distillation=distillation,
            source_steps=successes,
        )

    def _create_anti_pattern_candidate(
        self,
        intent_key: str,
        failures: List[Step],
        confidence: float
    ) -> DistillationCandidate:
        """Create an ANTI_PATTERN distillation from failure patterns."""
        # Find most common failed approach
        decisions = [s.decision for s in failures if s.decision and s.decision != "pending"]
        if not decisions:
            return None

        worst_decision = Counter(decisions).most_common(1)[0][0]

        # Extract the intent category
        intent_desc = intent_key.replace("intent:", "").replace("_", " ")

        distillation = Distillation(
            distillation_id="",
            type=DistillationType.ANTI_PATTERN,
            statement=f"When user requests {intent_desc}, avoid: {worst_decision[:150]}",
            domains=["user_interaction", intent_desc],
            anti_triggers=[intent_key],
            source_steps=[s.step_id for s in failures[:10]],
            confidence=confidence,
        )

        self._stats["candidates_generated"] += 1

        return DistillationCandidate(
            distillation=distillation,
            source_steps=failures,
        )

    # ==================== Strategy 2: Tool Patterns ====================

    def _distill_tool_patterns(self, steps: List[Step]) -> List[Distillation]:
        """
        Distill patterns about tool effectiveness.

        Identifies which tools work well for which intents.
        """
        distillations = []

        # Group by tool used
        tool_groups: Dict[str, List[Step]] = {}
        for step in steps:
            tool = step.action_details.get("tool_used", "")
            if not tool:
                continue
            if tool not in tool_groups:
                tool_groups[tool] = []
            tool_groups[tool].append(step)

        for tool, tool_steps in tool_groups.items():
            if len(tool_steps) < self.min_occurrences:
                continue

            successes = [s for s in tool_steps if s.evaluation == Evaluation.PASS]
            if len(successes) < 2:
                continue

            # What intents does this tool succeed at?
            success_intents = Counter(
                self._normalize_intent(s.intent) for s in successes
            ).most_common(2)

            if not success_intents:
                continue

            best_intent, count = success_intents[0]
            if count < 2:
                continue

            intent_desc = best_intent.replace("intent:", "").replace("_", " ")

            distillation = Distillation(
                distillation_id="",
                type=DistillationType.HEURISTIC,
                statement=f"Tool '{tool}' is effective for {intent_desc} requests ({count} successes)",
                domains=["tool_usage", tool.lower()],
                triggers=[f"tool:{tool}", intent_desc],
                source_steps=[s.step_id for s in successes[:5]],
                confidence=count / len(tool_steps),
            )

            candidate = DistillationCandidate(
                distillation=distillation,
                source_steps=successes,
            )

            if self._apply_memory_gate(candidate):
                self.store.save_distillation(distillation)
                distillations.append(distillation)
                self._stats["distillations_created"] += 1

        return distillations

    # ==================== Strategy 3: Surprises ====================

    def _distill_surprises(self, steps: List[Step]) -> List[Distillation]:
        """
        Distill SHARP_EDGE patterns from surprising outcomes.

        High surprise = prediction didn't match reality.
        These are valuable learning opportunities.
        """
        distillations = []

        # Find high-surprise steps
        surprises = [s for s in steps if s.surprise_level >= 0.5]
        if len(surprises) < 2:
            return []

        # Group surprises by intent
        intent_surprises: Dict[str, List[Step]] = {}
        for step in surprises:
            key = self._normalize_intent(step.intent)
            if key not in intent_surprises:
                intent_surprises[key] = []
            intent_surprises[key].append(step)

        for intent_key, surprise_steps in intent_surprises.items():
            if len(surprise_steps) < 2:
                continue

            intent_desc = intent_key.replace("intent:", "").replace("_", " ")

            # Extract what was surprising
            lessons = [s.lesson for s in surprise_steps if s.lesson]
            predictions = [s.prediction for s in surprise_steps if s.prediction]
            results = [s.result for s in surprise_steps if s.result]

            # Create sharp edge
            edge_description = f"Unexpected outcomes when handling {intent_desc}"
            if lessons:
                edge_description += f". Learned: {lessons[0][:100]}"

            distillation = Distillation(
                distillation_id="",
                type=DistillationType.SHARP_EDGE,
                statement=edge_description,
                domains=["gotchas", intent_desc],
                triggers=[intent_key],
                source_steps=[s.step_id for s in surprise_steps[:5]],
                confidence=0.7,  # Surprises are inherently uncertain
            )

            candidate = DistillationCandidate(
                distillation=distillation,
                source_steps=surprise_steps,
            )

            if self._apply_memory_gate(candidate):
                self.store.save_distillation(distillation)
                distillations.append(distillation)
                self._stats["distillations_created"] += 1

        return distillations

    # ==================== Strategy 4: Lesson Consolidation ====================

    def _distill_lessons(self, steps: List[Step]) -> List[Distillation]:
        """
        Consolidate similar lessons into policy distillations.

        When multiple steps produce similar lessons, consolidate
        into a reusable policy.
        """
        distillations = []

        # Extract and normalize lessons
        lessons = [(s, s.lesson) for s in steps if s.lesson and len(s.lesson) > 20]
        if len(lessons) < self.min_occurrences:
            return []

        # Simple clustering by keyword overlap
        lesson_clusters = self._cluster_lessons(lessons)

        for cluster_key, cluster_steps in lesson_clusters.items():
            if len(cluster_steps) < self.min_occurrences:
                continue

            # Synthesize a general policy from the cluster
            lessons_text = [s.lesson for s in cluster_steps]
            synthesized = self._synthesize_policy(lessons_text)

            if not synthesized:
                continue

            distillation = Distillation(
                distillation_id="",
                type=DistillationType.POLICY,
                statement=synthesized,
                domains=["learned_policy"],
                triggers=[cluster_key],
                source_steps=[s.step_id for s in cluster_steps[:5]],
                confidence=len(cluster_steps) / len(steps),  # More occurrences = higher confidence
            )

            candidate = DistillationCandidate(
                distillation=distillation,
                source_steps=cluster_steps,
            )

            if self._apply_memory_gate(candidate):
                self.store.save_distillation(distillation)
                distillations.append(distillation)
                self._stats["distillations_created"] += 1

        return distillations

    def _cluster_lessons(
        self,
        lessons: List[Tuple[Step, str]]
    ) -> Dict[str, List[Step]]:
        """Cluster lessons by keyword similarity."""
        clusters: Dict[str, List[Step]] = {}

        # Extract keywords from each lesson
        stop_words = {
            "the", "a", "an", "and", "or", "but", "if", "then", "so", "to",
            "of", "in", "on", "for", "with", "by", "is", "are", "was", "were",
            "be", "been", "being", "request", "user", "resolved", "failed"
        }

        for step, lesson in lessons:
            words = re.findall(r'\b[a-z]+\b', lesson.lower())
            keywords = [w for w in words if w not in stop_words and len(w) > 3]
            if not keywords:
                continue

            # Use first 3 keywords as cluster key
            cluster_key = "_".join(sorted(keywords[:3]))
            if cluster_key not in clusters:
                clusters[cluster_key] = []
            clusters[cluster_key].append(step)

        return clusters

    def _synthesize_policy(self, lessons: List[str]) -> Optional[str]:
        """Synthesize a general policy from multiple lessons."""
        if not lessons:
            return None

        # Find common structure
        # Simple approach: use the shortest lesson as base
        lessons_sorted = sorted(lessons, key=len)
        base = lessons_sorted[0]

        # Clean up for policy format
        if base.startswith("Request '"):
            # Extract the actionable part
            parts = base.split("resolved by:", 1)
            if len(parts) > 1:
                return f"Policy: For similar requests, {parts[1].strip()}"
            parts = base.split("failed", 1)
            if len(parts) > 1:
                return f"Policy: Avoid approach that led to failure in similar requests"

        return f"Policy: {base[:200]}"

    # ==================== Memory Gate ====================

    def _apply_memory_gate(self, candidate: DistillationCandidate) -> bool:
        """
        Apply memory gate to determine if distillation should persist.

        Scoring:
        - Impact (unblocked progress): +0.3
        - Novelty (new pattern): +0.2
        - Surprise (prediction != outcome): +0.3
        - Recurrence (3+ times): +0.2
        - Irreversible (high stakes): +0.4

        Threshold: score > 0.5
        """
        score = 0.0
        reasons = []

        steps = candidate.source_steps
        distillation = candidate.distillation

        # Impact: Did these steps make progress?
        progress_steps = [s for s in steps if s.progress_made]
        if len(progress_steps) > len(steps) * 0.5:
            score += 0.3
            reasons.append("impact:progress_made")

        # Novelty: Is this a new pattern?
        existing = self._find_similar_distillation(distillation)
        if not existing:
            score += 0.2
            reasons.append("novelty:new_pattern")
        else:
            # Update existing instead of creating new
            candidate.distillation = existing
            score += 0.1
            reasons.append("novelty:updates_existing")

        # Surprise: Were outcomes unexpected?
        surprises = [s for s in steps if s.surprise_level > 0.3]
        if len(surprises) > len(steps) * 0.3:
            score += 0.3
            reasons.append(f"surprise:{len(surprises)}_steps")

        # Recurrence: Multiple occurrences
        if len(steps) >= self.min_occurrences:
            score += 0.2
            reasons.append(f"recurrence:{len(steps)}_occurrences")

        # High stakes: Security, deployment, deletion
        high_stakes_keywords = ["deploy", "delete", "security", "auth", "payment", "production"]
        statement_lower = distillation.statement.lower()
        if any(kw in statement_lower for kw in high_stakes_keywords):
            score += 0.4
            reasons.append("high_stakes")

        # Evidence quality: Has validation
        validated = [s for s in steps if s.validated]
        if len(validated) > len(steps) * 0.5:
            score += 0.1
            reasons.append("evidence:validated")

        candidate.gate_score = score
        candidate.gate_reasons = reasons

        return score >= self.gate_threshold

    def _find_similar_distillation(self, candidate: Distillation) -> Optional[Distillation]:
        """Check if a similar distillation already exists."""
        # Get existing distillations of same type
        existing = self.store.get_distillations_by_type(candidate.type, limit=100)

        # Simple similarity check based on triggers and statement
        candidate_triggers = set(candidate.triggers)
        candidate_words = set(candidate.statement.lower().split())

        for dist in existing:
            dist_triggers = set(dist.triggers)
            dist_words = set(dist.statement.lower().split())

            # Check trigger overlap
            if candidate_triggers & dist_triggers:
                return dist

            # Check statement similarity
            overlap = len(candidate_words & dist_words) / max(len(candidate_words | dist_words), 1)
            if overlap > 0.6:
                return dist

        return None

    def get_stats(self) -> Dict[str, Any]:
        """Get distiller statistics."""
        return {
            **self._stats,
            "min_occurrences": self.min_occurrences,
            "min_occurrences_critical": self.min_occurrences_critical,
            "min_confidence": self.min_confidence,
            "gate_threshold": self.gate_threshold,
        }

    def get_effective_min_occurrences(self, importance_tier: str = "medium") -> int:
        """
        Get the effective minimum occurrences based on importance tier.

        CRITICAL tier items are fast-tracked with lower occurrence requirement.
        """
        if importance_tier.lower() == "critical":
            return self.min_occurrences_critical
        return self.min_occurrences


# Singleton instance
_distiller: Optional[PatternDistiller] = None


def get_pattern_distiller() -> PatternDistiller:
    """Get the global pattern distiller instance."""
    global _distiller
    if _distiller is None:
        _distiller = PatternDistiller()
    return _distiller
