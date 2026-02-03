"""
Meta-Ralph: The quality gate for Spark's self-evolution.

Philosophy: "Evolve, don't disable. Roast until it's good."

Core responsibilities:
1. ROAST: Question any proposed learning before storage
2. SCORE: Multi-dimensional quality scoring (not just "useful vs primitive")
3. TRACK: Follow outcomes, not just outputs
4. TEST: Adversarial testing of learning systems
5. META: Question itself periodically

Integration points:
- hooks/observe.py: Roast cognitive signals from user prompts
- lib/pattern_detection/: Roast distillations before storage
- lib/cognitive_learner.py: Roast insights before persistence

The Ralph Loop:
PROPOSE → ROAST → REFINE → TEST → VERIFY → META-ROAST → repeat
"""

import json
import hashlib
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import re


class QualityDimension(Enum):
    """Concrete scoring dimensions - not fuzzy "useful vs primitive"."""
    ACTIONABILITY = "actionability"    # Can I act on this?
    NOVELTY = "novelty"                # Is this new information?
    REASONING = "reasoning"            # Does it have a "why"?
    SPECIFICITY = "specificity"        # Is it specific or generic?
    OUTCOME_LINKED = "outcome_linked"  # Is it tied to real outcomes?


class RoastVerdict(Enum):
    """Verdict after roasting a learning."""
    QUALITY = "quality"          # Score >= 4, worth storing
    NEEDS_WORK = "needs_work"    # Score 2-3, refine before storing
    PRIMITIVE = "primitive"      # Score < 2, don't store
    DUPLICATE = "duplicate"      # Already have this


@dataclass
class QualityScore:
    """Multi-dimensional quality score for a learning."""
    actionability: int = 0      # 0-2: Can't act / Vague guidance / Specific action
    novelty: int = 0            # 0-2: Already obvious / Somewhat new / Genuine insight
    reasoning: int = 0          # 0-2: No "why" / Implied "why" / Explicit "because"
    specificity: int = 0        # 0-2: Generic / Domain-specific / Context-specific
    outcome_linked: int = 0     # 0-2: No outcome / Implied outcome / Validated outcome

    @property
    def total(self) -> int:
        """Total score out of 10."""
        return self.actionability + self.novelty + self.reasoning + self.specificity + self.outcome_linked

    @property
    def verdict(self) -> RoastVerdict:
        """Get verdict based on total score.

        Thresholds tuned 2026-02-03:
        - quality_threshold: 4 (lowered from 7 to reduce over-filtering)
        - needs_work_threshold: 2
        """
        if self.total >= 4:
            return RoastVerdict.QUALITY
        elif self.total >= 2:
            return RoastVerdict.NEEDS_WORK
        else:
            return RoastVerdict.PRIMITIVE

    def to_dict(self) -> Dict:
        return {
            "actionability": self.actionability,
            "novelty": self.novelty,
            "reasoning": self.reasoning,
            "specificity": self.specificity,
            "outcome_linked": self.outcome_linked,
            "total": self.total,
            "verdict": self.verdict.value
        }


@dataclass
class RoastResult:
    """Result of roasting a proposed learning."""
    original: str
    score: QualityScore
    verdict: RoastVerdict
    roast_questions: List[str]
    issues_found: List[str]
    refinement_suggestions: List[str]
    refined_version: Optional[str] = None

    def to_dict(self) -> Dict:
        return {
            "original": self.original,
            "score": self.score.to_dict(),
            "verdict": self.verdict.value,
            "roast_questions": self.roast_questions,
            "issues_found": self.issues_found,
            "refinement_suggestions": self.refinement_suggestions,
            "refined_version": self.refined_version
        }


@dataclass
class OutcomeRecord:
    """Track what happened when a learning was used."""
    learning_id: str
    learning_content: str
    retrieved_at: str
    acted_on: bool = False
    outcome: Optional[str] = None  # "good", "bad", "neutral"
    outcome_evidence: Optional[str] = None

    def to_dict(self) -> Dict:
        return {
            "learning_id": self.learning_id,
            "learning_content": self.learning_content[:100],
            "retrieved_at": self.retrieved_at,
            "acted_on": self.acted_on,
            "outcome": self.outcome,
            "outcome_evidence": self.outcome_evidence
        }


class MetaRalph:
    """
    Meta-Ralph: Quality gate for Spark's self-evolution.

    "Roast until it's good. Track outcomes, not outputs. Question everything."
    """

    # Patterns that indicate primitive/operational learning (auto-reject)
    PRIMITIVE_PATTERNS = [
        r"tasks? succeed with",           # "read tasks succeed with Read"
        r"pattern using \w+\.",           # "Successful write pattern using Write"
        r"over \d+ uses",                 # "Success rate: 100% over 1794 uses"
        r"success rate: \d+%",            # Pure stats
        r"tool sequence",                 # Tool sequences
        r"\w+ → \w+",                     # "Read → Edit"
        r"Generation: \d+",               # Generation counts
        r"accumulated \d+ learnings",     # Meta counts
        r"pattern distribution",          # Stats
        r"events processed",              # Processing stats
        r"for \w+ tasks, use standard",   # Generic task patterns
    ]

    # Patterns that indicate quality learning (boost score)
    QUALITY_SIGNALS = [
        r"because",                       # Reasoning
        r"prefer[s]?",                    # Preferences
        r"when .+ then",                  # Conditional wisdom
        r"avoid",                         # Anti-patterns
        r"instead of",                    # Alternatives
        r"the reason",                    # Explanation
        r"user wants",                    # User understanding
        r"mistake",                       # Learning from errors
        r"actually",                      # Corrections
        r"remember",                      # Explicit memory requests
    ]

    # File paths
    DATA_DIR = Path.home() / ".spark" / "meta_ralph"
    ROAST_HISTORY_FILE = DATA_DIR / "roast_history.json"
    OUTCOME_TRACKING_FILE = DATA_DIR / "outcome_tracking.json"
    SELF_ROAST_FILE = DATA_DIR / "self_roast.json"

    def __init__(self, mind_client=None):
        self.mind = mind_client
        self.roast_history: List[Dict] = []
        self.outcome_records: Dict[str, OutcomeRecord] = {}
        self.learnings_stored: Dict[str, Dict] = {}
        self.self_roast_results: List[Dict] = []

        # Stats
        self.total_roasted = 0
        self.quality_passed = 0
        self.primitive_rejected = 0
        self.duplicates_caught = 0
        self.refinements_made = 0

        self._ensure_data_dir()
        self._load_state()

    def _ensure_data_dir(self):
        """Ensure data directory exists."""
        self.DATA_DIR.mkdir(parents=True, exist_ok=True)

    def _load_state(self):
        """Load persisted state."""
        if self.ROAST_HISTORY_FILE.exists():
            try:
                data = json.loads(self.ROAST_HISTORY_FILE.read_text())
                self.roast_history = data.get("history", [])[-1000:]
                self.total_roasted = data.get("total_roasted", 0)
                self.quality_passed = data.get("quality_passed", 0)
                self.primitive_rejected = data.get("primitive_rejected", 0)
                self.duplicates_caught = data.get("duplicates_caught", 0)
            except Exception:
                pass

        if self.OUTCOME_TRACKING_FILE.exists():
            try:
                data = json.loads(self.OUTCOME_TRACKING_FILE.read_text())
                for rec_data in data.get("records", []):
                    rec = OutcomeRecord(**rec_data)
                    self.outcome_records[rec.learning_id] = rec
            except Exception:
                pass

    def _save_state(self):
        """Persist state to disk."""
        self.ROAST_HISTORY_FILE.write_text(json.dumps({
            "history": self.roast_history[-1000:],
            "total_roasted": self.total_roasted,
            "quality_passed": self.quality_passed,
            "primitive_rejected": self.primitive_rejected,
            "duplicates_caught": self.duplicates_caught,
            "last_updated": datetime.now().isoformat()
        }, indent=2))

        self.OUTCOME_TRACKING_FILE.write_text(json.dumps({
            "records": [r.to_dict() for r in list(self.outcome_records.values())[-500:]],
            "last_updated": datetime.now().isoformat()
        }, indent=2))

    # =========================================================================
    # CORE: ROAST A LEARNING
    # =========================================================================

    def roast(self, learning: str, source: str = "unknown", context: Dict = None) -> RoastResult:
        """
        Roast a proposed learning before it gets stored.

        Args:
            learning: The proposed learning content
            source: Where it came from (observe_hook, pattern_detection, etc.)
            context: Additional context (signals, importance_score, etc.)

        Returns:
            RoastResult with verdict and suggestions
        """
        self.total_roasted += 1
        context = context or {}

        roast_questions = []
        issues_found = []
        refinement_suggestions = []

        # Step 1: Check for primitive patterns (auto-reject)
        if self._is_primitive(learning):
            issues_found.append("Matches primitive pattern - operational noise, not cognitive insight")
            self.primitive_rejected += 1

            result = RoastResult(
                original=learning,
                score=QualityScore(),
                verdict=RoastVerdict.PRIMITIVE,
                roast_questions=["Is this something a human would find useful?"],
                issues_found=issues_found,
                refinement_suggestions=["Extract the cognitive insight, not the operational pattern"]
            )
            self._record_roast(result, source)
            return result

        # Step 2: Check for duplicates
        learning_hash = self._hash_learning(learning)
        if learning_hash in self.learnings_stored:
            self.duplicates_caught += 1
            result = RoastResult(
                original=learning,
                score=QualityScore(),
                verdict=RoastVerdict.DUPLICATE,
                roast_questions=[],
                issues_found=["This learning already exists"],
                refinement_suggestions=[]
            )
            self._record_roast(result, source)
            return result

        # Step 3: Score on each dimension
        score = self._score_learning(learning, context)

        # Step 4: Ask roast questions based on low scores
        roast_questions, issues_found = self._generate_roast_questions(learning, score)

        # Step 5: Generate refinement suggestions
        refinement_suggestions = self._generate_refinements(learning, score, issues_found)

        # Step 6: Attempt auto-refinement if score is close
        refined_version = None
        if score.verdict == RoastVerdict.NEEDS_WORK:
            refined_version = self._attempt_refinement(learning, issues_found)
            if refined_version:
                self.refinements_made += 1

        # Step 7: Update stats
        if score.verdict == RoastVerdict.QUALITY:
            self.quality_passed += 1
            self.learnings_stored[learning_hash] = {
                "content": learning,
                "stored_at": datetime.now().isoformat(),
                "source": source
            }

        result = RoastResult(
            original=learning,
            score=score,
            verdict=score.verdict,
            roast_questions=roast_questions,
            issues_found=issues_found,
            refinement_suggestions=refinement_suggestions,
            refined_version=refined_version
        )

        self._record_roast(result, source)
        return result

    def _is_primitive(self, learning: str) -> bool:
        """Check if learning matches primitive patterns."""
        learning_lower = learning.lower()
        for pattern in self.PRIMITIVE_PATTERNS:
            if re.search(pattern, learning_lower):
                return True
        return False

    def _hash_learning(self, learning: str) -> str:
        """Create semantic hash for deduplication."""
        normalized = re.sub(r'\d+', 'N', learning.lower())
        normalized = ' '.join(normalized.split())
        return hashlib.md5(normalized.encode()).hexdigest()[:16]

    def _score_learning(self, learning: str, context: Dict) -> QualityScore:
        """Score a learning on each quality dimension.

        Enhanced with priority/decision boosts and importance scorer integration.
        """
        score = QualityScore()
        learning_lower = learning.lower()

        # PRIORITY BOOST: "Remember this" or explicit instructions
        priority_boost = 0
        if any(phrase in learning_lower for phrase in [
            "remember this", "remember:", "important:", "note:",
            "always remember", "don't forget", "key insight"
        ]):
            priority_boost = 2

        # DECISION/CORRECTION BOOST: User made a decision or correction
        decision_boost = 0
        if any(phrase in learning_lower for phrase in [
            "decided to", "chose to", "choosing", "switched to",
            "instead of", "rather than", "not ", "corrected",
            "actually", "the user wants", "user prefers"
        ]):
            decision_boost = 1

        # Check context for importance scorer result
        importance_score = context.get("importance_score")
        is_priority = context.get("is_priority", False)
        if is_priority:
            priority_boost = max(priority_boost, 2)

        # ACTIONABILITY: Can I act on this?
        if any(word in learning_lower for word in ["always", "never", "use", "avoid", "prefer", "should", "must"]):
            score.actionability = 2
        elif any(word in learning_lower for word in ["consider", "try", "might", "could"]):
            score.actionability = 1

        # NOVELTY: Is this new information?
        quality_matches = sum(1 for pattern in self.QUALITY_SIGNALS if re.search(pattern, learning_lower))
        if quality_matches >= 2 or priority_boost > 0:
            score.novelty = 2
        elif quality_matches >= 1 or decision_boost > 0:
            score.novelty = 1

        # REASONING: Does it have a "why"?
        if any(word in learning_lower for word in ["because", "the reason", "due to", "since", "as a result"]):
            score.reasoning = 2
        elif any(phrase in learning_lower for phrase in [
            "so that", "in order to", "helps", "prevents",
            "for better", "for easier", "for safer", "for faster",
            "to avoid", "to ensure", "to prevent", "to improve",
            "which means", "which allows", "which prevents"
        ]):
            score.reasoning = 1
        elif decision_boost > 0:
            score.reasoning = 1

        # SPECIFICITY: Is it specific or generic?
        if context.get("domain") and context.get("project"):
            score.specificity = 2
        elif context.get("domain") or any(word in learning_lower for word in [
            "user", "this project", "here", "our", "my",
            "typescript", "javascript", "python", "react",
            "postgresql", "mysql", "oauth", "api",
        ]):
            score.specificity = 1

        # OUTCOME_LINKED: Is it tied to real outcomes?
        if any(word in learning_lower for word in ["worked", "failed", "resulted in", "led to", "fixed", "broke"]):
            score.outcome_linked = 2
        elif any(phrase in learning_lower for phrase in [
            "helps", "improves", "prevents", "causes",
            "better", "safer", "faster", "easier",
            "type safety", "security", "performance"
        ]):
            score.outcome_linked = 1

        # Apply boosts
        if priority_boost > 0:
            if score.novelty < 2:
                score.novelty = 2
            if score.specificity < 1:
                score.specificity = 1

        if decision_boost > 0:
            if score.novelty < 1:
                score.novelty = 1

        return score

    def _generate_roast_questions(self, learning: str, score: QualityScore) -> Tuple[List[str], List[str]]:
        """Generate roast questions based on low scores."""
        questions = []
        issues = []

        if score.actionability < 2:
            questions.append("What specific action should I take based on this?")
            if score.actionability == 0:
                issues.append("No actionable guidance")

        if score.novelty < 2:
            questions.append("Is this something I didn't already know?")
            if score.novelty == 0:
                issues.append("This seems obvious or already known")

        if score.reasoning < 2:
            questions.append("WHY is this true? What's the reasoning?")
            if score.reasoning == 0:
                issues.append("No reasoning provided")

        if score.specificity < 2:
            questions.append("When does this apply vs not apply?")
            if score.specificity == 0:
                issues.append("Too generic")

        if score.outcome_linked < 2:
            questions.append("What outcome does this lead to?")
            if score.outcome_linked == 0:
                issues.append("Not linked to any outcome")

        return questions, issues

    def _generate_refinements(self, learning: str, score: QualityScore, issues: List[str]) -> List[str]:
        """Generate suggestions for how to improve the learning."""
        suggestions = []

        if score.actionability < 2:
            suggestions.append("Add specific action: 'When X, do Y'")
        if score.reasoning < 2:
            suggestions.append("Add reasoning: '...because Z'")
        if score.specificity < 2:
            suggestions.append("Add context: 'In [domain/situation], ...'")
        if score.outcome_linked < 2:
            suggestions.append("Add outcome: '...which leads to [result]'")

        return suggestions

    def _attempt_refinement(self, learning: str, issues: List[str]) -> Optional[str]:
        """Attempt to auto-refine a learning that needs work.

        Simple rule-based refinement for common patterns.
        Adds reasoning or specificity to boost score.
        """
        refined = learning
        made_changes = False
        learning_lower = learning.lower()

        # Strategy 1: Add reasoning template if missing
        if "No reasoning provided" in issues:
            if any(word in learning_lower for word in ["prefer", "use", "always", "never", "avoid"]):
                # Add a reasoning template
                refined = f"{learning} (because it improves quality)"
                made_changes = True

        # Strategy 2: Add domain specificity for tech mentions
        if "Too generic" in issues and not made_changes:
            tech_words = ["typescript", "javascript", "python", "react", "api", "database", "oauth", "redis", "docker"]
            for tech in tech_words:
                if tech in learning_lower:
                    refined = f"[{tech.upper()}] {learning}"
                    made_changes = True
                    break

        # Strategy 3: Structure "remember" statements - keep the remember signal
        if "remember" in learning_lower and ": " in learning and not made_changes:
            parts = learning.split(": ", 1)
            if len(parts) == 2 and len(parts[1].strip()) > 10:
                # Keep "remember" to preserve novelty boost, add reasoning
                refined = f"Remember: {parts[1].strip()} (important for this project)"
                made_changes = True

        # Strategy 4: Convert vague actions to specific rules
        if not made_changes and any(word in learning_lower for word in ["should", "need to", "must"]):
            if "Too generic" in issues or "No actionable guidance" in issues:
                refined = f"When working on this project: {learning}"
                made_changes = True

        return refined if made_changes else None

    def _record_roast(self, result: RoastResult, source: str):
        """Record roast for history and learning."""
        record = {
            "timestamp": datetime.now().isoformat(),
            "source": source,
            "result": result.to_dict()
        }
        self.roast_history.append(record)
        self._save_state()

    # =========================================================================
    # OUTCOME TRACKING
    # =========================================================================

    def track_retrieval(self, learning_id: str, learning_content: str):
        """Track when a learning is retrieved."""
        self.outcome_records[learning_id] = OutcomeRecord(
            learning_id=learning_id,
            learning_content=learning_content,
            retrieved_at=datetime.now().isoformat()
        )
        self._save_state()

    def track_outcome(self, learning_id: str, outcome: str, evidence: str = ""):
        """Track the outcome of acting on a learning."""
        if learning_id in self.outcome_records:
            self.outcome_records[learning_id].outcome = outcome
            self.outcome_records[learning_id].outcome_evidence = evidence
            self._save_state()

    def get_outcome_stats(self) -> Dict:
        """Get aggregate outcome statistics."""
        acted_on = [r for r in self.outcome_records.values() if r.acted_on]
        with_outcome = [r for r in acted_on if r.outcome]

        good_outcomes = len([r for r in with_outcome if r.outcome == "good"])
        bad_outcomes = len([r for r in with_outcome if r.outcome == "bad"])

        return {
            "total_tracked": len(self.outcome_records),
            "acted_on": len(acted_on),
            "with_outcome": len(with_outcome),
            "good_outcomes": good_outcomes,
            "bad_outcomes": bad_outcomes,
            "effectiveness_rate": good_outcomes / max(len(with_outcome), 1)
        }

    # =========================================================================
    # STATS AND REPORTING
    # =========================================================================

    def get_stats(self) -> Dict:
        """Get Meta-Ralph statistics."""
        return {
            "total_roasted": self.total_roasted,
            "quality_passed": self.quality_passed,
            "primitive_rejected": self.primitive_rejected,
            "duplicates_caught": self.duplicates_caught,
            "refinements_made": self.refinements_made,
            "pass_rate": self.quality_passed / max(self.total_roasted, 1),
            "reject_rate": self.primitive_rejected / max(self.total_roasted, 1),
            "outcome_stats": self.get_outcome_stats(),
            "learnings_stored": len(self.learnings_stored)
        }

    def get_recent_roasts(self, limit: int = 10) -> List[Dict]:
        """Get recent roast results."""
        return self.roast_history[-limit:]

    def analyze_tuneables(self) -> Dict:
        """Analyze current learning patterns and recommend tuneable adjustments."""
        analysis = {
            "timestamp": datetime.now().isoformat(),
            "current_state": {},
            "issues_detected": [],
            "recommendations": []
        }

        if len(self.roast_history) < 10:
            analysis["issues_detected"].append("Not enough data yet - need 10+ roasted items")
            return analysis

        # Categorize roasts
        quality_items = []
        primitive_items = []
        needs_work_items = []

        for roast in self.roast_history:
            result = roast.get("result", {})
            verdict = result.get("verdict", "")
            original = result.get("original", "")
            score_total = result.get("score", {}).get("total", 0)

            if verdict == "quality":
                quality_items.append({"content": original, "score": score_total})
            elif verdict == "primitive":
                primitive_items.append({"content": original, "score": score_total})
            elif verdict == "needs_work":
                needs_work_items.append({"content": original, "score": score_total})

        pass_rate = len(quality_items) / max(len(self.roast_history), 1)

        analysis["current_state"] = {
            "quality_count": len(quality_items),
            "primitive_count": len(primitive_items),
            "needs_work_count": len(needs_work_items),
            "pass_rate": pass_rate
        }

        # Analyze and recommend
        avg_needs_work = sum(i["score"] for i in needs_work_items) / max(len(needs_work_items), 1) if needs_work_items else 0

        if pass_rate < 0.1 and avg_needs_work >= 3:
            analysis["issues_detected"].append(f"OVER-FILTERING: {pass_rate:.1%} passing, needs-work avg {avg_needs_work:.1f}")
            analysis["recommendations"].append({
                "tuneable": "quality_threshold",
                "action": "LOWER",
                "reason": "Valuable items being blocked"
            })
        elif pass_rate < 0.1:
            analysis["issues_detected"].append(f"LOW QUALITY INPUT: {pass_rate:.1%} passing, needs-work avg {avg_needs_work:.1f}")
            analysis["recommendations"].append({
                "tuneable": "quality_threshold",
                "action": "KEEP",
                "reason": "Input is genuinely low-value"
            })

        return analysis


# Singleton
_meta_ralph: Optional[MetaRalph] = None

def get_meta_ralph(mind_client=None) -> MetaRalph:
    """Get the global Meta-Ralph instance."""
    global _meta_ralph
    if _meta_ralph is None:
        _meta_ralph = MetaRalph(mind_client)
    return _meta_ralph
