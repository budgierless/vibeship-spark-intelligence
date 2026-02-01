"""
EIDOS Guardrails: Hard Gates for Quality Enforcement

These guardrails are NOT suggestions. They BLOCK actions that violate
intelligence principles.

Guardrails:
1. Progress Contract (existing in control_plane)
2. Memory Binding (existing in control_plane)
3. Outcome Enforcement (existing in control_plane)
4. Loop Watchers (existing in control_plane)
5. Phase Control (existing in control_plane)
6. Evidence Before Modification (NEW) - Forces diagnostic evidence after failed edits
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set

from .models import Episode, Step, Phase, Evaluation, ActionType


class ViolationType(Enum):
    """Types of guardrail violations."""
    EVIDENCE_BEFORE_MODIFICATION = "evidence_before_modification"
    PHASE_VIOLATION = "phase_violation"
    BUDGET_EXCEEDED = "budget_exceeded"
    MEMORY_REQUIRED = "memory_required"
    VALIDATION_REQUIRED = "validation_required"


@dataclass
class GuardrailResult:
    """Result of a guardrail check."""
    passed: bool
    violation: Optional[ViolationType] = None
    message: str = ""
    required_actions: List[str] = field(default_factory=list)
    suggestions: List[str] = field(default_factory=list)


# Actions allowed in each phase
PHASE_ALLOWED_ACTIONS: Dict[Phase, Set[str]] = {
    Phase.EXPLORE: {'Read', 'Glob', 'Grep', 'WebSearch', 'WebFetch', 'AskUser', 'Task'},
    Phase.DIAGNOSE: {'Read', 'Glob', 'Grep', 'Bash', 'Test', 'AskUser'},
    Phase.EXECUTE: {'Read', 'Edit', 'Write', 'Bash', 'Test', 'NotebookEdit'},
    Phase.CONSOLIDATE: {'Read', 'Reflect', 'Distill'},
    Phase.ESCALATE: {'Summarize', 'AskUser', 'AskUserQuestion'},
}

# Edit tools that modify files
EDIT_TOOLS = {'Edit', 'Write', 'NotebookEdit'}

# Diagnostic intent keywords
DIAGNOSTIC_INTENTS = {
    'diagnose', 'reproduce', 'isolate', 'narrow', 'investigate',
    'understand', 'analyze', 'debug', 'trace', 'examine'
}


class EvidenceBeforeModificationGuard:
    """
    Guardrail 6: Evidence Before Modification

    After 2 failed edit attempts on the same issue, the agent is FORBIDDEN
    to edit code until diagnostic evidence is gathered.

    Required before resuming edits:
    - Reproduce reliably
    - Narrow scope
    - Identify discriminating signal
    - Create minimal reproduction
    """

    def __init__(self, failure_threshold: int = 2):
        self.failure_threshold = failure_threshold

    def check(
        self,
        episode: Episode,
        step: Step,
        recent_steps: List[Step]
    ) -> GuardrailResult:
        """Check if edit is allowed based on evidence requirements."""
        # Only applies to tool calls
        if step.action_type != ActionType.TOOL_CALL:
            return GuardrailResult(passed=True)

        # Only applies to edit tools
        tool = step.action_details.get('tool', '')
        if tool not in EDIT_TOOLS:
            return GuardrailResult(passed=True)

        # Count failed edit attempts on same target
        file_path = step.action_details.get('file_path', '')
        failed_edits = self._count_failed_edits(recent_steps, file_path)

        if failed_edits >= self.failure_threshold:
            if not self._has_diagnostic_evidence(recent_steps):
                return GuardrailResult(
                    passed=False,
                    violation=ViolationType.EVIDENCE_BEFORE_MODIFICATION,
                    message=f"{failed_edits} failed edits on {file_path}. Must gather evidence before modifying.",
                    required_actions=[
                        "reproduce_reliably",
                        "narrow_scope",
                        "identify_discriminating_signal",
                        "create_minimal_reproduction"
                    ],
                    suggestions=[
                        "Add logging to understand the flow",
                        "Write a minimal test that fails",
                        "Isolate the specific line/function causing the issue",
                        "Document what you've tried and why it failed"
                    ]
                )

        return GuardrailResult(passed=True)

    def _count_failed_edits(self, steps: List[Step], file_path: str) -> int:
        """Count failed edit attempts on a specific file."""
        count = 0
        for step in steps:
            if step.action_type != ActionType.TOOL_CALL:
                continue
            tool = step.action_details.get('tool', '')
            if tool not in EDIT_TOOLS:
                continue
            step_path = step.action_details.get('file_path', '')
            if step_path == file_path and step.evaluation == Evaluation.FAIL:
                count += 1
        return count

    def _has_diagnostic_evidence(self, steps: List[Step]) -> bool:
        """Check if diagnostic evidence exists in recent steps."""
        for step in steps:
            # Check for diagnostic reasoning steps
            if step.action_type == ActionType.REASONING:
                intent_lower = step.intent.lower()
                if any(keyword in intent_lower for keyword in DIAGNOSTIC_INTENTS):
                    return True

            # Check for lessons that indicate understanding
            if step.lesson and len(step.lesson) > 50:
                lesson_lower = step.lesson.lower()
                if any(keyword in lesson_lower for keyword in ['root cause', 'because', 'the issue is', 'found that']):
                    return True

        return False


class PhaseViolationGuard:
    """
    Check if an action violates the current phase's allowed actions.
    """

    def check(
        self,
        episode: Episode,
        step: Step
    ) -> GuardrailResult:
        """Check if action is allowed in current phase."""
        if step.action_type != ActionType.TOOL_CALL:
            return GuardrailResult(passed=True)

        tool = step.action_details.get('tool', '')
        allowed = PHASE_ALLOWED_ACTIONS.get(episode.phase, set())

        if tool and tool not in allowed:
            return GuardrailResult(
                passed=False,
                violation=ViolationType.PHASE_VIOLATION,
                message=f"Action '{tool}' not allowed in phase '{episode.phase.value}'.",
                suggestions=[f"Allowed actions in {episode.phase.value}: {', '.join(sorted(allowed))}"]
            )

        return GuardrailResult(passed=True)


class GuardrailEngine:
    """
    Unified guardrail engine that runs all checks.
    """

    def __init__(self):
        self.evidence_guard = EvidenceBeforeModificationGuard()
        self.phase_guard = PhaseViolationGuard()

    def check_all(
        self,
        episode: Episode,
        step: Step,
        recent_steps: List[Step]
    ) -> List[GuardrailResult]:
        """Run all guardrail checks and return results."""
        results = []

        # Evidence Before Modification
        result = self.evidence_guard.check(episode, step, recent_steps)
        if not result.passed:
            results.append(result)

        # Phase Violation
        result = self.phase_guard.check(episode, step)
        if not result.passed:
            results.append(result)

        return results

    def is_blocked(
        self,
        episode: Episode,
        step: Step,
        recent_steps: List[Step]
    ) -> Optional[GuardrailResult]:
        """Check if action is blocked by any guardrail."""
        violations = self.check_all(episode, step, recent_steps)
        return violations[0] if violations else None
