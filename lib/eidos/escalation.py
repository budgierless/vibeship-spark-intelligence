"""
EIDOS Escalation: Intelligent Recognition of Limits

Escalation is NOT failure. It's intelligent recognition of limits.

Escalation Types:
- BUDGET: Step/time limit exhausted
- LOOP: Same error 3x, same file 4x, no progress 5 steps
- CONFIDENCE: Dropped below 0.2
- BLOCKED: Guardrail violation
- UNKNOWN: No relevant memory AND high uncertainty

Request Types:
- INFO: Missing context or knowledge
- DECISION: Choice between valid approaches
- HELP: Stuck, need human intervention
- REVIEW: Uncertain about risky action
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional
import time
import json

from .models import Episode, Step, Phase, Outcome, Evaluation


class EscalationType(Enum):
    """Why the episode is escalating."""
    BUDGET = "budget"           # Budget exhausted
    LOOP = "loop"               # Loop detected
    CONFIDENCE = "confidence"   # Confidence collapsed
    BLOCKED = "blocked"         # Guardrail blocked action
    UNKNOWN = "unknown"         # Unknown territory


class RequestType(Enum):
    """What kind of help is needed."""
    INFO = "info"           # Missing context or knowledge
    DECISION = "decision"   # Choice between approaches
    HELP = "help"           # Stuck, need intervention
    REVIEW = "review"       # Uncertain about risky action


@dataclass
class Attempt:
    """Record of an attempted approach."""
    approach: str
    result: str
    why_failed: str


@dataclass
class EvidenceGathered:
    """Evidence collected during the episode."""
    type: str
    finding: str


@dataclass
class MinimalReproduction:
    """Minimal reproduction of an issue (if applicable)."""
    description: str
    steps_to_reproduce: List[str]
    expected: str
    actual: str
    environment: Dict[str, str] = field(default_factory=dict)


@dataclass
class SuggestedOption:
    """Suggested option for a decision."""
    option: str
    tradeoff: str


@dataclass
class Escalation:
    """
    Complete escalation output structure.

    This is what gets surfaced to the user when the agent
    needs help.
    """
    episode_id: str
    escalation_type: EscalationType

    # Summary
    goal: str
    progress: str
    blocker: str

    # History
    attempts: List[Attempt] = field(default_factory=list)
    evidence_gathered: List[EvidenceGathered] = field(default_factory=list)

    # Current understanding
    current_hypothesis: str = ""
    minimal_reproduction: Optional[MinimalReproduction] = None

    # Request
    request_type: RequestType = RequestType.HELP
    specific_question: str = ""
    suggested_options: List[SuggestedOption] = field(default_factory=list)

    # Metadata
    created_at: float = field(default_factory=time.time)
    step_count: int = 0
    elapsed_seconds: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        result = {
            "episode_id": self.episode_id,
            "escalation_type": self.escalation_type.value,
            "summary": {
                "goal": self.goal,
                "progress": self.progress,
                "blocker": self.blocker,
            },
            "attempts": [
                {"approach": a.approach, "result": a.result, "why_failed": a.why_failed}
                for a in self.attempts
            ],
            "evidence_gathered": [
                {"type": e.type, "finding": e.finding}
                for e in self.evidence_gathered
            ],
            "current_hypothesis": self.current_hypothesis,
            "request_type": self.request_type.value,
            "specific_question": self.specific_question,
            "suggested_options": [
                {"option": o.option, "tradeoff": o.tradeoff}
                for o in self.suggested_options
            ],
            "created_at": self.created_at,
            "step_count": self.step_count,
            "elapsed_seconds": self.elapsed_seconds,
        }

        if self.minimal_reproduction:
            result["minimal_reproduction"] = {
                "description": self.minimal_reproduction.description,
                "steps_to_reproduce": self.minimal_reproduction.steps_to_reproduce,
                "expected": self.minimal_reproduction.expected,
                "actual": self.minimal_reproduction.actual,
                "environment": self.minimal_reproduction.environment,
            }

        return result

    def to_yaml(self) -> str:
        """Format escalation as YAML for readability."""
        lines = [
            f"escalation:",
            f"  episode_id: \"{self.episode_id}\"",
            f"  escalation_type: {self.escalation_type.value.upper()}",
            f"",
            f"  summary:",
            f"    goal: \"{self.goal}\"",
            f"    progress: \"{self.progress}\"",
            f"    blocker: \"{self.blocker}\"",
        ]

        if self.attempts:
            lines.append(f"")
            lines.append(f"  attempts:")
            for a in self.attempts:
                lines.append(f"    - approach: \"{a.approach}\"")
                lines.append(f"      result: \"{a.result}\"")
                lines.append(f"      why_failed: \"{a.why_failed}\"")

        if self.evidence_gathered:
            lines.append(f"")
            lines.append(f"  evidence_gathered:")
            for e in self.evidence_gathered:
                lines.append(f"    - type: \"{e.type}\"")
                lines.append(f"      finding: \"{e.finding}\"")

        if self.current_hypothesis:
            lines.append(f"")
            lines.append(f"  current_hypothesis: \"{self.current_hypothesis}\"")

        if self.minimal_reproduction:
            lines.append(f"")
            lines.append(f"  minimal_reproduction:")
            lines.append(f"    description: \"{self.minimal_reproduction.description}\"")
            lines.append(f"    steps_to_reproduce:")
            for step in self.minimal_reproduction.steps_to_reproduce:
                lines.append(f"      - \"{step}\"")
            lines.append(f"    expected: \"{self.minimal_reproduction.expected}\"")
            lines.append(f"    actual: \"{self.minimal_reproduction.actual}\"")

        lines.append(f"")
        lines.append(f"  request_type: {self.request_type.value.upper()}")
        lines.append(f"  specific_question: \"{self.specific_question}\"")

        if self.suggested_options:
            lines.append(f"")
            lines.append(f"  suggested_options:")
            for o in self.suggested_options:
                lines.append(f"    - option: \"{o.option}\"")
                lines.append(f"      tradeoff: \"{o.tradeoff}\"")

        return "\n".join(lines)


class EscalationBuilder:
    """
    Builder for creating escalation reports from episode state.
    """

    def build(
        self,
        episode: Episode,
        steps: List[Step],
        escalation_type: EscalationType,
        blocker: str
    ) -> Escalation:
        """Build an escalation report from episode and steps."""
        # Calculate elapsed time
        elapsed = time.time() - episode.start_ts if episode.start_ts else 0

        # Extract attempts from failed steps
        attempts = self._extract_attempts(steps)

        # Extract evidence from steps with lessons
        evidence = self._extract_evidence(steps)

        # Determine current hypothesis from last diagnostic step
        hypothesis = self._extract_hypothesis(steps)

        # Determine request type and question
        request_type, question = self._determine_request(
            escalation_type, steps, blocker
        )

        # Generate suggested options if decision type
        options = []
        if request_type == RequestType.DECISION:
            options = self._generate_options(steps, blocker)

        # Determine progress summary
        progress = self._summarize_progress(steps)

        return Escalation(
            episode_id=episode.episode_id,
            escalation_type=escalation_type,
            goal=episode.goal,
            progress=progress,
            blocker=blocker,
            attempts=attempts,
            evidence_gathered=evidence,
            current_hypothesis=hypothesis,
            request_type=request_type,
            specific_question=question,
            suggested_options=options,
            step_count=len(steps),
            elapsed_seconds=elapsed,
        )

    def _extract_attempts(self, steps: List[Step]) -> List[Attempt]:
        """Extract failed attempts from steps."""
        attempts = []
        for step in steps:
            if step.evaluation == Evaluation.FAIL:
                attempts.append(Attempt(
                    approach=step.decision[:100] if step.decision else "Unknown approach",
                    result=step.result[:100] if step.result else "Unknown result",
                    why_failed=step.lesson[:100] if step.lesson else "Unknown reason"
                ))
        return attempts[-5:]  # Last 5 attempts

    def _extract_evidence(self, steps: List[Step]) -> List[EvidenceGathered]:
        """Extract evidence from step lessons."""
        evidence = []
        for step in steps:
            if step.lesson and step.evaluation != Evaluation.UNKNOWN:
                evidence.append(EvidenceGathered(
                    type=step.action_type.value if step.action_type else "observation",
                    finding=step.lesson[:150]
                ))
        return evidence[-5:]  # Last 5 pieces of evidence

    def _extract_hypothesis(self, steps: List[Step]) -> str:
        """Extract current hypothesis from steps."""
        # Look for most recent step with high confidence
        for step in reversed(steps):
            if step.confidence_after > 0.5 and step.lesson:
                return step.lesson[:200]
        return ""

    def _determine_request(
        self,
        escalation_type: EscalationType,
        steps: List[Step],
        blocker: str
    ) -> tuple:
        """Determine request type and specific question."""
        # Default to HELP
        request_type = RequestType.HELP

        if escalation_type == EscalationType.BUDGET:
            request_type = RequestType.HELP
            question = f"Budget exhausted with {len(steps)} steps. Need guidance on how to proceed."

        elif escalation_type == EscalationType.LOOP:
            request_type = RequestType.DECISION
            question = "Detected loop pattern. Which approach should I try next?"

        elif escalation_type == EscalationType.CONFIDENCE:
            request_type = RequestType.INFO
            question = "Confidence dropped significantly. What context am I missing?"

        elif escalation_type == EscalationType.BLOCKED:
            request_type = RequestType.REVIEW
            question = f"Action blocked: {blocker}. Please confirm how to proceed."

        elif escalation_type == EscalationType.UNKNOWN:
            request_type = RequestType.INFO
            question = "No relevant memory found and high uncertainty. What should I know?"

        else:
            question = f"Escalated: {blocker}"

        return request_type, question

    def _generate_options(
        self,
        steps: List[Step],
        blocker: str
    ) -> List[SuggestedOption]:
        """Generate suggested options for decision requests."""
        options = []

        # Get unique approaches tried
        tried = set()
        for step in steps:
            if step.decision:
                tried.add(step.decision[:50])

        # Suggest alternatives
        if "edit" in blocker.lower() or "modify" in blocker.lower():
            options.append(SuggestedOption(
                option="Gather more diagnostic evidence before editing",
                tradeoff="Slower but more likely to succeed"
            ))
            options.append(SuggestedOption(
                option="Try a different approach entirely",
                tradeoff="May require rethinking the solution"
            ))
        else:
            options.append(SuggestedOption(
                option="Continue with current approach",
                tradeoff="Risk of more failures"
            ))
            options.append(SuggestedOption(
                option="Escalate to human for guidance",
                tradeoff="Requires human time"
            ))

        return options[:4]  # Max 4 options

    def _summarize_progress(self, steps: List[Step]) -> str:
        """Summarize progress made."""
        passed = len([s for s in steps if s.evaluation == Evaluation.PASS])
        failed = len([s for s in steps if s.evaluation == Evaluation.FAIL])
        total = len(steps)

        if passed > 0 and failed == 0:
            return f"Made good progress: {passed}/{total} steps succeeded"
        elif passed > failed:
            return f"Partial progress: {passed} succeeded, {failed} failed"
        elif passed == 0:
            return f"Struggling: {failed} failed attempts so far"
        else:
            return f"Mixed results: {passed} passed, {failed} failed"


def build_escalation(
    episode: Episode,
    steps: List[Step],
    escalation_type: EscalationType,
    blocker: str
) -> Escalation:
    """Convenience function to build an escalation."""
    builder = EscalationBuilder()
    return builder.build(episode, steps, escalation_type, blocker)
