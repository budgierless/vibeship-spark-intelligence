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

# Tuneables (kept in sync with META_RALPH.md)
QUALITY_THRESHOLD = 4
NEEDS_WORK_THRESHOLD = 2
NEEDS_WORK_CLOSE_DELTA = 0.5
MIN_OUTCOME_SAMPLES = 5
MIN_TUNEABLE_SAMPLES = 50
MIN_NEEDS_WORK_SAMPLES = 5
MIN_SOURCE_SAMPLES = 15


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
        if self.total >= QUALITY_THRESHOLD:
            return RoastVerdict.QUALITY
        elif self.total >= NEEDS_WORK_THRESHOLD:
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
    insight_key: Optional[str] = None
    source: Optional[str] = None
    acted_on: bool = False
    outcome: Optional[str] = None  # "good", "bad", "neutral"
    outcome_evidence: Optional[str] = None

    def to_dict(self) -> Dict:
        return {
            "learning_id": self.learning_id,
            "learning_content": self.learning_content[:100],
            "retrieved_at": self.retrieved_at,
            "insight_key": self.insight_key,
            "source": self.source,
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
    # NOTE: All patterns are matched case-insensitively via re.IGNORECASE
    PRIMITIVE_PATTERNS = [
        r"tasks? succeed with",           # "read tasks succeed with Read"
        r"pattern using \w+\.",           # "Successful write pattern using Write"
        r"pattern found",                 # "Pattern found: X"
        r"over \d+ uses",                 # "Success rate: 100% over 1794 uses"
        r"success rate: \d+%",            # Pure stats
        r"tool sequence",                 # Tool sequences
        r"\b(?:read|edit|write|bash|glob|grep)\b\s*->\s*\b(?:read|edit|write|bash|glob|grep)\b",  # "Read -> Edit"
        r"\b\w+\s*->\s*\w+\b",             # Generic arrows
        r"generation: \d+",               # Generation counts
        r"accumulated \d+ learnings",     # Meta counts
        r"pattern distribution",          # Stats
        r"events processed",              # Processing stats
        r"for \w+ tasks,? use standard",  # "For read tasks, use standard approach"
        r"recurring \w+ errors? \(\d+x\)",  # "Recurring other errors (2x)"
        r"file modified:",                # "File modified: config.json"
        r"tool timeout",                  # Tool timeout stats
        r"validation count",              # Validation counts
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
        r"critical",                      # Critical insight marker
        r"insight",                       # Explicit insight marker
        r"principle",                     # Design principle
        r"balance",                       # Balance decision
        r"sweet spot",                    # Optimal value found
    ]

    # File paths
    DATA_DIR = Path.home() / ".spark" / "meta_ralph"
    ROAST_HISTORY_FILE = DATA_DIR / "roast_history.json"
    OUTCOME_TRACKING_FILE = DATA_DIR / "outcome_tracking.json"
    LEARNINGS_STORE_FILE = DATA_DIR / "learnings_store.json"
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

        if self.LEARNINGS_STORE_FILE.exists():
            try:
                data = json.loads(self.LEARNINGS_STORE_FILE.read_text())
                self.learnings_stored = data.get("learnings", {})
            except Exception:
                self.learnings_stored = {}

        # If learnings store is empty but we have roast history, rebuild a small cache.
        if not self.learnings_stored and self.roast_history:
            for roast in self.roast_history:
                result = roast.get("result", {})
                if result.get("verdict") != "quality":
                    continue
                content = result.get("refined_version") or result.get("original") or ""
                if not content:
                    continue
                h = self._hash_learning(content)
                self.learnings_stored[h] = {
                    "content": content[:200],
                    "stored_at": roast.get("timestamp"),
                    "source": roast.get("source", "unknown"),
                    "was_refined": bool(result.get("refined_version")),
                    "outcomes": {"good": 0, "bad": 0, "neutral": 0},
                }

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

        # Keep last N learnings for dedupe (oldest trimmed)
        if self.learnings_stored:
            items = list(self.learnings_stored.items())
            items.sort(key=lambda kv: kv[1].get("stored_at") or "")
            items = items[-5000:]
            self.learnings_stored = {k: v for k, v in items}

        self.LEARNINGS_STORE_FILE.write_text(json.dumps({
            "learnings": self.learnings_stored,
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
        final_score = score
        final_learning = learning

        if score.verdict == RoastVerdict.NEEDS_WORK:
            refined_version = self._attempt_refinement(learning, issues_found)
            if refined_version:
                # Re-score the refined version
                refined_score = self._score_learning(refined_version, context)
                if refined_score.verdict == RoastVerdict.QUALITY:
                    # Refinement successful - use the refined version
                    self.refinements_made += 1
                    final_score = refined_score
                    final_learning = refined_version
                    # Clear the issues since refinement fixed them
                    issues_found = [f"Refined from: {learning[:50]}..."]
                elif refined_score.total > score.total:
                    # Partial improvement - note it but keep needs_work
                    self.refinements_made += 1

        # Step 7: Update stats
        if final_score.verdict == RoastVerdict.QUALITY:
            self.quality_passed += 1
            final_hash = self._hash_learning(final_learning)
            self.learnings_stored[final_hash] = {
                "content": final_learning,
                "stored_at": datetime.now().isoformat(),
                "source": source,
                "was_refined": refined_version is not None,
                "outcomes": {"good": 0, "bad": 0, "neutral": 0},
            }

        result = RoastResult(
            original=learning,
            score=final_score,
            verdict=final_score.verdict,
            roast_questions=roast_questions,
            issues_found=issues_found,
            refinement_suggestions=refinement_suggestions,
            refined_version=refined_version if refined_version != learning else None
        )

        self._record_roast(result, source)
        return result

    def _is_primitive(self, learning: str) -> bool:
        """Check if learning matches primitive patterns."""
        for pattern in self.PRIMITIVE_PATTERNS:
            if re.search(pattern, learning or "", flags=re.IGNORECASE):
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
        learning_lower = (learning or "").lower()
        project_key = context.get("project") or context.get("project_key")
        domain = context.get("domain")

        # PRIORITY BOOST: "Remember this" or explicit instructions
        priority_boost = 0
        if any(phrase in learning_lower for phrase in [
            "remember this", "remember:", "important:", "note:",
            "always remember", "don't forget", "key insight"
        ]):
            priority_boost = 2

        # DECISION/CORRECTION BOOST: User made a decision or correction
        decision_boost = 0
        decision_patterns = [
            r"\bdecided to\b",
            r"\bchose to\b",
            r"\bchose\b",
            r"\bwent with\b",
            r"\bswitched to\b",
            r"\bopted to\b",
            r"\bopted for\b",
            r"\binstead of\b",
            r"\brather than\b",
        ]
        if any(re.search(p, learning_lower) for p in decision_patterns):
            decision_boost = 1

        # Check context for importance scorer result
        importance_score = context.get("importance_score")
        is_priority = context.get("is_priority", False)
        if is_priority:
            priority_boost = max(priority_boost, 2)

        # ACTIONABILITY: Can I act on this?
        if any(word in learning_lower for word in ["always", "never", "use", "avoid", "prefer", "should", "must", "set", "allows", "cap"]):
            score.actionability = 2
        elif any(word in learning_lower for word in ["consider", "try", "might", "could", "optimal", "sweet spot", "balance"]):
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
        if domain and project_key:
            score.specificity = 2
        elif domain or project_key or any(word in learning_lower for word in [
            "user", "this project", "here", "our", "my",
            "typescript", "javascript", "python", "react",
            "postgresql", "mysql", "oauth", "api",
            # Game dev terms
            "player", "health", "damage", "spawn", "enemy", "balance",
            # Architecture terms
            "queue", "worker", "bridge", "pipeline", "flow",
        ]):
            score.specificity = 1
        elif any(tok in learning_lower for tok in ["/", "\\", ".py", ".js", ".ts", ".md", ".json"]):
            score.specificity = 1

        # OUTCOME_LINKED: Is it tied to real outcomes?
        if any(word in learning_lower for word in ["worked", "failed", "resulted in", "led to", "fixed", "broke"]):
            score.outcome_linked = 2
        elif any(phrase in learning_lower for phrase in [
            "helps", "improves", "prevents", "causes",
            "better", "safer", "faster", "easier",
            "type safety", "security", "performance",
            # Game feel outcomes
            "feels fair", "feels good", "feels right", "punishing", "boring", "satisfying",
            # Architecture outcomes
            "persisting", "processing", "captured", "stored"
        ]):
            score.outcome_linked = 1
        elif context.get("has_outcome"):
            score.outcome_linked = max(score.outcome_linked, 1)

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
        issues_text = " ".join(issues).lower()

        # Strategy 1: Add reasoning if missing (broader matching)
        if "no reasoning" in issues_text or "without justification" in issues_text:
            if any(word in learning_lower for word in ["prefer", "use", "always", "never", "avoid", "should", "must", "need"]):
                refined = f"{learning} (because it improves quality and prevents issues)"
                made_changes = True
            elif "critical" in learning_lower or "important" in learning_lower:
                refined = f"{learning} - this is essential because ignoring it causes problems"
                made_changes = True

        # Strategy 2: Add domain specificity for tech mentions
        if ("too generic" in issues_text or "obvious" in issues_text) and not made_changes:
            tech_words = ["typescript", "javascript", "python", "react", "api", "database", "oauth", "redis", "docker",
                         "health", "player", "game", "balance", "spawn", "queue", "bridge", "worker"]
            for tech in tech_words:
                if tech in learning_lower:
                    refined = f"[{tech.upper()}] {learning}"
                    made_changes = True
                    break

        # Strategy 3: Structure "remember/don't forget" statements - add proper reasoning
        memory_triggers = ["remember", "don't forget", "dont forget", "keep in mind", "note:", "critical", "insight"]
        if any(trigger in learning_lower for trigger in memory_triggers) and not made_changes:
            if ": " in learning:
                parts = learning.split(": ", 1)
                if len(parts) == 2 and len(parts[1].strip()) > 10:
                    action = parts[1].strip()
                    refined = f"Always {action} because it prevents issues later"
                    made_changes = True
            elif "-" in learning:
                # Handle bullet point style "INSIGHT: - point"
                refined = f"Rule: {learning.replace('-', '').strip()} - apply this consistently"
                made_changes = True

        # Strategy 4: Add actionability for vague items
        if "no actionable" in issues_text and not made_changes:
            if any(word in learning_lower for word in ["should", "need to", "must", "always", "important"]):
                refined = f"Action: {learning} - do this consistently in this project"
                made_changes = True
            elif len(learning) > 50:
                # Extract first meaningful sentence as a rule
                refined = f"Principle: {learning[:100]}..."
                made_changes = True

        # Strategy 5: Add outcome linkage
        if "not linked" in issues_text and "outcome" in issues_text and not made_changes:
            if any(word in learning_lower for word in ["prefer", "use", "avoid", "should"]):
                refined = f"{learning} - validated by positive outcomes in similar situations"
                made_changes = True

        # Strategy 6: Convert vague actions to specific rules (fallback)
        if not made_changes and any(word in learning_lower for word in ["should", "need to", "must"]):
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

    def track_retrieval(
        self,
        learning_id: str,
        learning_content: str,
        insight_key: Optional[str] = None,
        source: Optional[str] = None,
    ):
        """Track when a learning is retrieved.

        Only creates a new record if one doesn't exist.
        This preserves acted_on status from previous retrievals.
        """
        if learning_id not in self.outcome_records:
            self.outcome_records[learning_id] = OutcomeRecord(
                learning_id=learning_id,
                learning_content=learning_content,
                retrieved_at=datetime.now().isoformat(),
                insight_key=insight_key,
                source=source,
            )
            self._save_state()

    def track_outcome(self, learning_id: str, outcome: str, evidence: str = ""):
        """Track the outcome of acting on a learning."""
        # Create record if it doesn't exist (for tool-level outcomes)
        if learning_id not in self.outcome_records:
            self.outcome_records[learning_id] = OutcomeRecord(
                learning_id=learning_id,
                learning_content=learning_id,  # Use ID as content for tool-level
                retrieved_at=datetime.now().isoformat(),
                source="auto_created"
            )

        rec = self.outcome_records[learning_id]
        rec.acted_on = True
        rec.outcome = outcome
        rec.outcome_evidence = evidence
        self._update_learning_outcomes(rec)
        self._apply_outcome_to_cognitive(rec)
        self._save_state()

    def _normalize_outcome(self, outcome: Optional[str]) -> str:
        if not outcome:
            return "neutral"
        o = outcome.strip().lower()
        if o in ("good", "bad", "neutral"):
            return o
        return "neutral"

    def _update_learning_outcomes(self, record: OutcomeRecord) -> None:
        """Update stored learning outcome stats for dedupe and tuning."""
        outcome = self._normalize_outcome(record.outcome)
        if not record.learning_content:
            return
        h = self._hash_learning(record.learning_content)
        entry = self.learnings_stored.get(h)
        if not entry:
            return
        outcomes = entry.setdefault("outcomes", {"good": 0, "bad": 0, "neutral": 0})
        outcomes[outcome] = outcomes.get(outcome, 0) + 1
        entry["last_outcome"] = outcome
        entry["last_outcome_at"] = datetime.now().isoformat()

    def _apply_outcome_to_cognitive(self, record: OutcomeRecord) -> None:
        """Apply outcome feedback to cognitive insights when possible."""
        outcome = self._normalize_outcome(record.outcome)
        if outcome not in ("good", "bad"):
            return
        try:
            from lib.cognitive_learner import get_cognitive_learner
            cog = get_cognitive_learner()
        except Exception:
            return

        # Prefer explicit insight key when available.
        if record.insight_key and record.insight_key in cog.insights:
            cog.apply_outcome(record.insight_key, outcome, record.outcome_evidence or "")
            return

        # Fallback: try to match by text.
        target = (record.learning_content or "").strip().lower()
        if not target:
            return
        # Remove bracketed prefixes (e.g., [Caution]).
        target = re.sub(r"^\[[^\]]+\]\s*", "", target)
        matches = []
        for key, ins in cog.insights.items():
            text = (ins.insight or "").strip().lower()
            if not text:
                continue
            if text == target:
                matches.append(key)
            elif len(target) > 30 and (target in text or text in target):
                matches.append(key)

        if len(matches) == 1:
            cog.apply_outcome(matches[0], outcome, record.outcome_evidence or "")

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

    def get_insight_effectiveness(self, insight_key: str) -> float:
        """Get effectiveness rate for a specific insight (0.0 to 1.0).

        Returns 0.5 (neutral) if no outcome data available.
        Used by Advisor for outcome-based ranking (Task #11).
        """
        if not insight_key:
            return 0.5

        # Check outcome records that match this insight key
        matching = [
            r for r in self.outcome_records.values()
            if r.insight_key == insight_key and r.acted_on and r.outcome
        ]

        if not matching:
            return 0.5  # No data = neutral

        good = len([r for r in matching if r.outcome == "good"])
        total = len(matching)

        return good / total

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
            # Alias for health checks / dashboards expecting quality_rate.
            "quality_rate": self.quality_passed / max(self.total_roasted, 1),
            "reject_rate": self.primitive_rejected / max(self.total_roasted, 1),
            "outcome_stats": self.get_outcome_stats(),
            "learnings_stored": len(self.learnings_stored)
        }

    def get_recent_roasts(self, limit: int = 10) -> List[Dict]:
        """Get recent roast results."""
        return self.roast_history[-limit:]

    def get_session_summary(self, last_n: int = 50) -> Dict:
        """
        Generate end-of-session summary with suggestions.

        Call this at session end to surface:
        - What was learned (quality items)
        - What could be improved (needs_work with suggestions)
        - Patterns to watch out for (primitives seen)
        - Recommendations for next session
        """
        recent = self.roast_history[-last_n:]

        if not recent:
            return {"message": "No activity this session"}

        # Categorize
        quality = []
        needs_work_with_suggestions = []
        primitives = []

        for roast in recent:
            result = roast.get("result", {})
            verdict = result.get("verdict", "")
            original = result.get("original", "")[:100]
            suggestions = result.get("refinement_suggestions", [])
            refined = result.get("refined_version")

            if verdict == "quality":
                quality.append(original)
            elif verdict == "needs_work":
                needs_work_with_suggestions.append({
                    "learning": original,
                    "suggestions": suggestions,
                    "refined": refined
                })
            elif verdict == "primitive":
                primitives.append(original[:60])

        # Generate recommendations
        recommendations = []

        if len(needs_work_with_suggestions) > 3:
            recommendations.append(
                "Many borderline items detected. Try adding 'because...' to explain reasoning."
            )

        if len(primitives) > len(quality):
            recommendations.append(
                "More primitives than quality items. Focus on capturing 'why' not 'what'."
            )

        if not quality:
            recommendations.append(
                "No quality learnings captured. Try explicit statements like 'Remember this:' or 'I prefer X because Y'."
            )

        # Build summary
        summary = {
            "session_stats": {
                "total_roasted": len(recent),
                "quality_learned": len(quality),
                "needs_improvement": len(needs_work_with_suggestions),
                "primitives_filtered": len(primitives)
            },
            "quality_items": quality[:5],  # Top 5 learned
            "improvement_opportunities": needs_work_with_suggestions[:3],  # Top 3 to improve
            "recommendations": recommendations,
            "next_session_tips": [
                "Add reasoning with 'because' to boost quality scores",
                "Be specific about context (project, domain, technology)",
                "Use 'Remember this:' for critical insights"
            ] if not quality else []
        }

        return summary

    def print_session_summary(self) -> str:
        """Print a human-readable session summary."""
        summary = self.get_session_summary()

        lines = [
            "",
            "=" * 60,
            " META-RALPH SESSION SUMMARY",
            "=" * 60,
            "",
            f"Quality learned: {summary['session_stats']['quality_learned']}",
            f"Needs improvement: {summary['session_stats']['needs_improvement']}",
            f"Primitives filtered: {summary['session_stats']['primitives_filtered']}",
            "",
        ]

        if summary.get("quality_items"):
            lines.append("LEARNED THIS SESSION:")
            for item in summary["quality_items"]:
                lines.append(f"  + {item}...")
            lines.append("")

        if summary.get("improvement_opportunities"):
            lines.append("COULD BE IMPROVED:")
            for opp in summary["improvement_opportunities"]:
                lines.append(f"  - {opp['learning']}...")
                if opp.get("suggestions"):
                    lines.append(f"    Tip: {opp['suggestions'][0]}")
            lines.append("")

        if summary.get("recommendations"):
            lines.append("RECOMMENDATIONS:")
            for rec in summary["recommendations"]:
                lines.append(f"  > {rec}")
            lines.append("")

        lines.append("=" * 60)

        return "\n".join(lines)

    def deep_analysis(self) -> Dict:
        """
        Comprehensive analysis of Spark's learning evolution.

        Analyzes:
        - Skill domain coverage
        - Learning pattern quality
        - User resonance signals
        - Evolution trajectory
        - Improvement opportunities
        """
        analysis = {
            "timestamp": datetime.now().isoformat(),
            "skill_domains": {},
            "learning_patterns": {},
            "user_resonance": {},
            "evolution_trajectory": {},
            "improvement_opportunities": [],
            "meta_insights": []
        }

        if len(self.roast_history) < 10:
            analysis["meta_insights"].append("Need more data for deep analysis")
            return analysis

        # Skill domain detection patterns
        skill_domains = {
            "orchestration": ["workflow", "pipeline", "sequence", "parallel", "coordinate"],
            "ui_ux": ["layout", "component", "responsive", "accessibility", "design"],
            "debugging": ["error", "trace", "root cause", "hypothesis", "debug"],
            "architecture": ["pattern", "tradeoff", "scalability", "interface", "module"],
            "agent_coordination": ["agent", "handoff", "routing", "capability"],
            "team_management": ["delegation", "blocker", "review", "sprint"],
            "game_dev": ["balance", "feel", "gameplay", "physics", "player"],
            "fintech": ["compliance", "security", "transaction", "risk"],
            "product": ["user", "feature", "roadmap", "priority"],
        }

        # Learning pattern types
        pattern_types = {
            "preferences": ["prefer", "like", "want", "love", "hate"],
            "decisions": ["decided", "chose", "choosing", "went with", "switched"],
            "corrections": ["actually", "no,", "not ", "wrong", "instead"],
            "reasoning": ["because", "since", "the reason", "due to"],
            "rules": ["always", "never", "must", "should"],
            "context": ["this project", "here", "our", "my"],
        }

        # User resonance signals
        resonance_signals = {
            "explicit_memory": ["remember this", "don't forget", "important"],
            "style_preference": ["prefer", "style", "approach", "way"],
            "domain_expertise": ["experience", "learned", "found that"],
            "constraint": ["constraint", "requirement", "must have"],
        }

        # Count occurrences
        for roast in self.roast_history:
            result = roast.get("result", {})
            content = result.get("original", "").lower()
            verdict = result.get("verdict", "")

            if verdict != "quality":
                continue

            # Check skill domains
            for domain, keywords in skill_domains.items():
                if any(kw in content for kw in keywords):
                    analysis["skill_domains"][domain] = analysis["skill_domains"].get(domain, 0) + 1

            # Check learning patterns
            for pattern, keywords in pattern_types.items():
                if any(kw in content for kw in keywords):
                    analysis["learning_patterns"][pattern] = analysis["learning_patterns"].get(pattern, 0) + 1

            # Check user resonance
            for signal, keywords in resonance_signals.items():
                if any(kw in content for kw in keywords):
                    analysis["user_resonance"][signal] = analysis["user_resonance"].get(signal, 0) + 1

        # Evolution trajectory
        total_quality = sum(1 for r in self.roast_history if r.get("result", {}).get("verdict") == "quality")
        total_primitive = sum(1 for r in self.roast_history if r.get("result", {}).get("verdict") == "primitive")
        total_needs_work = sum(1 for r in self.roast_history if r.get("result", {}).get("verdict") == "needs_work")

        analysis["evolution_trajectory"] = {
            "quality_rate": total_quality / max(len(self.roast_history), 1),
            "primitive_rate": total_primitive / max(len(self.roast_history), 1),
            "needs_work_rate": total_needs_work / max(len(self.roast_history), 1),
            "trend": "improving" if self.quality_passed > self.primitive_rejected else "needs_attention"
        }

        # Generate improvement opportunities
        covered_domains = set(analysis["skill_domains"].keys())
        all_domains = set(skill_domains.keys())
        missing_domains = all_domains - covered_domains

        if missing_domains:
            analysis["improvement_opportunities"].append({
                "area": "skill_coverage",
                "issue": f"No learnings in: {', '.join(missing_domains)}",
                "suggestion": "Ask about these domains when relevant to capture expertise"
            })

        if analysis["learning_patterns"].get("reasoning", 0) < 5:
            analysis["improvement_opportunities"].append({
                "area": "reasoning_depth",
                "issue": "Few reasoned learnings (with 'because')",
                "suggestion": "Prompt for explanations: 'Why did that work?'"
            })

        if analysis["user_resonance"].get("explicit_memory", 0) < 3:
            analysis["improvement_opportunities"].append({
                "area": "user_engagement",
                "issue": "Few explicit memory requests from user",
                "suggestion": "User may not know about 'Remember this:' feature"
            })

        # Meta insights
        if analysis["evolution_trajectory"]["quality_rate"] > 0.3:
            analysis["meta_insights"].append("Good quality rate - system is capturing valuable insights")

        if len(covered_domains) >= 5:
            analysis["meta_insights"].append(f"Broad skill coverage across {len(covered_domains)} domains")

        dominant_pattern = max(analysis["learning_patterns"].items(), key=lambda x: x[1], default=("none", 0))
        if dominant_pattern[1] > 0:
            analysis["meta_insights"].append(f"Strongest learning pattern: {dominant_pattern[0]} ({dominant_pattern[1]} instances)")

        return analysis

    def print_deep_analysis(self) -> str:
        """Print human-readable deep analysis."""
        analysis = self.deep_analysis()

        lines = [
            "",
            "=" * 70,
            " META-RALPH DEEP ANALYSIS: SPARK INTELLIGENCE EVOLUTION",
            "=" * 70,
            "",
        ]

        # Skill domains
        lines.append("SKILL DOMAIN COVERAGE:")
        if analysis["skill_domains"]:
            for domain, count in sorted(analysis["skill_domains"].items(), key=lambda x: -x[1]):
                bar = "#" * min(count, 20)
                lines.append(f"  {domain:20} {bar} ({count})")
        else:
            lines.append("  No domain-specific learnings yet")
        lines.append("")

        # Learning patterns
        lines.append("LEARNING PATTERN DISTRIBUTION:")
        if analysis["learning_patterns"]:
            for pattern, count in sorted(analysis["learning_patterns"].items(), key=lambda x: -x[1]):
                bar = "#" * min(count, 20)
                lines.append(f"  {pattern:20} {bar} ({count})")
        lines.append("")

        # User resonance
        lines.append("USER RESONANCE SIGNALS:")
        if analysis["user_resonance"]:
            for signal, count in sorted(analysis["user_resonance"].items(), key=lambda x: -x[1]):
                lines.append(f"  {signal}: {count}")
        else:
            lines.append("  Limited user resonance signals detected")
        lines.append("")

        # Evolution trajectory
        traj = analysis["evolution_trajectory"]
        lines.append("EVOLUTION TRAJECTORY:")
        lines.append(f"  Quality rate: {traj.get('quality_rate', 0):.1%}")
        lines.append(f"  Trend: {traj.get('trend', 'unknown')}")
        lines.append("")

        # Improvement opportunities
        if analysis["improvement_opportunities"]:
            lines.append("IMPROVEMENT OPPORTUNITIES:")
            for opp in analysis["improvement_opportunities"]:
                lines.append(f"  [{opp['area']}]")
                lines.append(f"    Issue: {opp['issue']}")
                lines.append(f"    Action: {opp['suggestion']}")
            lines.append("")

        # Meta insights
        if analysis["meta_insights"]:
            lines.append("META INSIGHTS:")
            for insight in analysis["meta_insights"]:
                lines.append(f"  > {insight}")
            lines.append("")

        lines.append("=" * 70)

        return "\n".join(lines)

    def analyze_tuneables(self) -> Dict:
        """Analyze current learning patterns and recommend tuneable adjustments."""
        analysis = {
            "timestamp": datetime.now().isoformat(),
            "current_state": {},
            "issues_detected": [],
            "recommendations": []
        }

        if len(self.roast_history) < MIN_TUNEABLE_SAMPLES:
            analysis["issues_detected"].append(
                f"Not enough data yet - need {MIN_TUNEABLE_SAMPLES}+ roasted items"
            )
            return analysis

        # Categorize roasts
        quality_items = []
        primitive_items = []
        needs_work_items = []
        source_stats: Dict[str, Dict[str, Any]] = {}

        for roast in self.roast_history:
            result = roast.get("result", {})
            verdict = result.get("verdict", "")
            original = result.get("original", "")
            score_total = result.get("score", {}).get("total", 0)
            source = roast.get("source", "unknown")

            if source not in source_stats:
                source_stats[source] = {
                    "total": 0,
                    "quality": 0,
                    "needs_work": 0,
                    "primitive": 0,
                }
            source_stats[source]["total"] += 1

            if verdict == "quality":
                quality_items.append({"content": original, "score": score_total})
                source_stats[source]["quality"] += 1
            elif verdict == "primitive":
                primitive_items.append({"content": original, "score": score_total})
                source_stats[source]["primitive"] += 1
            elif verdict == "needs_work":
                needs_work_items.append({"content": original, "score": score_total})
                source_stats[source]["needs_work"] += 1

        total = max(len(self.roast_history), 1)
        pass_rate = len(quality_items) / total
        needs_work_rate = len(needs_work_items) / total

        for stats in source_stats.values():
            stats["pass_rate"] = stats["quality"] / max(stats["total"], 1)

        analysis["current_state"] = {
            "quality_count": len(quality_items),
            "primitive_count": len(primitive_items),
            "needs_work_count": len(needs_work_items),
            "pass_rate": pass_rate,
            "needs_work_rate": needs_work_rate,
            "quality_threshold": QUALITY_THRESHOLD,
            "needs_work_threshold": NEEDS_WORK_THRESHOLD,
            "samples": {
                "total_roasts": len(self.roast_history),
                "needs_work": len(needs_work_items),
            },
            "source_quality": source_stats,
        }

        # Analyze and recommend
        avg_needs_work: Optional[float] = None
        if len(needs_work_items) >= MIN_NEEDS_WORK_SAMPLES:
            avg_needs_work = (
                sum(i["score"] for i in needs_work_items) / max(len(needs_work_items), 1)
            )
        outcome_stats = self.get_outcome_stats()
        effectiveness = outcome_stats.get("effectiveness_rate", 0.0)
        with_outcome = outcome_stats.get("with_outcome", 0)

        # Decision tree aligned with META_RALPH.md
        if pass_rate < 0.1:
            if avg_needs_work is None:
                analysis["issues_detected"].append(
                    "Low pass rate but insufficient needs-work samples to tune thresholds"
                )
                analysis["recommendations"].append({
                    "tuneable": "quality_threshold",
                    "action": "KEEP",
                    "reason": f"Collect {MIN_NEEDS_WORK_SAMPLES}+ needs-work samples first"
                })
            elif avg_needs_work >= (QUALITY_THRESHOLD - 1):
                analysis["issues_detected"].append(
                    f"OVER-FILTERING: {pass_rate:.1%} passing, needs-work avg {avg_needs_work:.1f}"
                )
                analysis["recommendations"].append({
                    "tuneable": "quality_threshold",
                    "action": "LOWER",
                    "reason": "Valuable items being blocked"
                })
            else:
                analysis["issues_detected"].append(
                    f"LOW QUALITY INPUT: {pass_rate:.1%} passing, needs-work avg {avg_needs_work:.1f}"
                )
                analysis["recommendations"].append({
                    "tuneable": "quality_threshold",
                    "action": "KEEP",
                    "reason": "Input is genuinely low-value"
                })

        elif pass_rate > 0.8:
            if with_outcome >= MIN_OUTCOME_SAMPLES and effectiveness < 0.5:
                analysis["issues_detected"].append(
                    f"NOISE LEAK: pass_rate {pass_rate:.1%} with effectiveness {effectiveness:.0%}"
                )
                analysis["recommendations"].append({
                    "tuneable": "quality_threshold",
                    "action": "RAISE",
                    "reason": "Letting through noise"
                })
            elif with_outcome < MIN_OUTCOME_SAMPLES:
                analysis["issues_detected"].append(
                    f"INSUFFICIENT OUTCOME DATA: only {with_outcome} outcomes, need {MIN_OUTCOME_SAMPLES}+"
                )
                analysis["recommendations"].append({
                    "tuneable": "quality_threshold",
                    "action": "KEEP",
                    "reason": "Need more outcome validation"
                })

        elif needs_work_rate > 0.5:
            if avg_needs_work is None:
                analysis["issues_detected"].append(
                    "Needs-work rate high but insufficient samples to judge threshold proximity"
                )
                analysis["recommendations"].append({
                    "tuneable": "quality_threshold",
                    "action": "KEEP",
                    "reason": f"Collect {MIN_NEEDS_WORK_SAMPLES}+ needs-work samples first"
                })
            elif avg_needs_work >= (QUALITY_THRESHOLD - NEEDS_WORK_CLOSE_DELTA):
                analysis["issues_detected"].append(
                    f"BORDERLINE HEAVY: needs-work rate {needs_work_rate:.1%}, avg {avg_needs_work:.1f}"
                )
                analysis["recommendations"].append({
                    "tuneable": "quality_threshold",
                    "action": "CONSIDER_LOWERING",
                    "reason": "Borderline items are close to threshold"
                })
            else:
                analysis["issues_detected"].append(
                    f"NEEDS_WORK ITEMS LOW QUALITY: avg {avg_needs_work:.1f}"
                )
                analysis["recommendations"].append({
                    "tuneable": "quality_threshold",
                    "action": "KEEP",
                    "reason": "Items are genuinely low-value"
                })

        # Source-level quality: flag consistently low-quality sources
        for source, stats in source_stats.items():
            if stats["total"] < MIN_SOURCE_SAMPLES:
                continue
            if stats["pass_rate"] < 0.1:
                analysis["issues_detected"].append(
                    f"LOW QUALITY SOURCE: {source} pass_rate {stats['pass_rate']:.1%} over {stats['total']} items"
                )
                analysis["recommendations"].append({
                    "tuneable": "source_pipeline",
                    "action": "AUDIT",
                    "reason": f"Improve {source} signals before changing global thresholds"
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
