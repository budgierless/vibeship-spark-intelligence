"""
EIDOS Minimal Mode: Fallback When Smart Agent Melts Down

When the system is in trouble, switch to a dumb but reliable mode.

MINIMAL MODE:
- Only diagnostics
- No refactors
- No broad changes
- Only reduce scope & run tests

Triggered by:
- Repeated watcher firings
- Low confidence + low evidence
- Budget nearly exhausted

This keeps you from burning hours on fancy reasoning when stuck.
"""

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

from .models import Episode, Step, Phase, Evaluation


class MinimalModeReason(Enum):
    """Why we entered minimal mode."""
    REPEATED_WATCHERS = "repeated_watchers"
    LOW_CONFIDENCE = "low_confidence"
    LOW_EVIDENCE = "low_evidence"
    BUDGET_CRITICAL = "budget_critical"
    ESCAPE_PROTOCOL = "escape_protocol"
    MANUAL_TRIGGER = "manual_trigger"


@dataclass
class MinimalModeState:
    """State of minimal mode."""
    active: bool = False
    reason: Optional[MinimalModeReason] = None
    entered_at: Optional[float] = None
    step_count_at_entry: int = 0

    # Restrictions
    edits_allowed: bool = False
    writes_allowed: bool = False
    refactors_allowed: bool = False
    new_features_allowed: bool = False

    # What IS allowed
    reads_allowed: bool = True
    diagnostics_allowed: bool = True
    tests_allowed: bool = True
    simplify_allowed: bool = True

    # Exit conditions
    exit_requires_evidence: bool = True
    exit_requires_hypothesis: bool = True
    min_steps_before_exit: int = 3

    def to_dict(self) -> Dict[str, Any]:
        return {
            "active": self.active,
            "reason": self.reason.value if self.reason else None,
            "entered_at": self.entered_at,
            "step_count_at_entry": self.step_count_at_entry,
            "edits_allowed": self.edits_allowed,
            "writes_allowed": self.writes_allowed,
            "refactors_allowed": self.refactors_allowed,
            "new_features_allowed": self.new_features_allowed,
            "reads_allowed": self.reads_allowed,
            "diagnostics_allowed": self.diagnostics_allowed,
            "tests_allowed": self.tests_allowed,
            "simplify_allowed": self.simplify_allowed,
        }


# Tools allowed in minimal mode
MINIMAL_MODE_ALLOWED_TOOLS = {
    "Read",
    "Glob",
    "Grep",
    "Bash",  # Only for diagnostics/tests
}

# Bash commands allowed in minimal mode (read-only + tests)
MINIMAL_MODE_BASH_PATTERNS = [
    "ls", "cat", "head", "tail", "grep", "find", "echo",
    "test", "pytest", "npm test", "yarn test", "jest",
    "node", "python -c", "python -m pytest",
    "git status", "git log", "git diff", "git show",
]

# Bash commands BLOCKED in minimal mode
MINIMAL_MODE_BASH_BLOCKED = [
    "rm", "mv", "cp", "mkdir", "touch",
    "git add", "git commit", "git push", "git checkout",
    "npm install", "pip install", "yarn add",
]


class MinimalModeController:
    """
    Controller for minimal mode.

    When the smart agent is struggling, this provides a
    reliable, constrained fallback.
    """

    def __init__(self):
        self.state = MinimalModeState()
        self.history: List[Dict[str, Any]] = []

    def should_enter(
        self,
        episode: Episode,
        watcher_trigger_count: int = 0,
        recent_steps: List[Step] = None
    ) -> Tuple[bool, Optional[MinimalModeReason]]:
        """
        Check if we should enter minimal mode.

        Triggers:
        - Watcher fired 3+ times
        - Confidence < 0.3 AND no evidence in 3 steps
        - Budget > 80% used
        """
        recent_steps = recent_steps or []

        # Trigger: Repeated watcher firings
        if watcher_trigger_count >= 3:
            return True, MinimalModeReason.REPEATED_WATCHERS

        # Trigger: Low confidence + low evidence
        if len(episode.confidence_history) >= 3:
            recent_conf = episode.confidence_history[-3:]
            avg_conf = sum(recent_conf) / len(recent_conf)
            if avg_conf < 0.3 and episode.no_evidence_streak >= 3:
                return True, MinimalModeReason.LOW_CONFIDENCE

        # Trigger: Budget critical
        if episode.budget_percentage_used() >= 0.8:
            return True, MinimalModeReason.BUDGET_CRITICAL

        # Trigger: Escape protocol was triggered
        if episode.escape_protocol_triggered:
            return True, MinimalModeReason.ESCAPE_PROTOCOL

        return False, None

    def enter(self, episode: Episode, reason: MinimalModeReason):
        """Enter minimal mode."""
        self.state = MinimalModeState(
            active=True,
            reason=reason,
            entered_at=time.time(),
            step_count_at_entry=episode.step_count,
        )

        self.history.append({
            "event": "enter",
            "reason": reason.value,
            "episode_id": episode.episode_id,
            "step_count": episode.step_count,
            "timestamp": time.time(),
        })

    def exit(self, episode: Episode, reason: str = ""):
        """Exit minimal mode."""
        if not self.state.active:
            return

        self.history.append({
            "event": "exit",
            "reason": reason,
            "episode_id": episode.episode_id,
            "step_count": episode.step_count,
            "duration_steps": episode.step_count - self.state.step_count_at_entry,
            "timestamp": time.time(),
        })

        self.state = MinimalModeState()

    def can_exit(self, episode: Episode, recent_steps: List[Step]) -> Tuple[bool, str]:
        """
        Check if we can exit minimal mode.

        Requires:
        - At least min_steps_before_exit steps taken
        - New evidence gathered
        - New hypothesis formed
        """
        if not self.state.active:
            return True, "Not in minimal mode"

        steps_in_minimal = episode.step_count - self.state.step_count_at_entry

        if steps_in_minimal < self.state.min_steps_before_exit:
            return False, f"Need {self.state.min_steps_before_exit - steps_in_minimal} more diagnostic steps"

        # Check for evidence
        if self.state.exit_requires_evidence:
            has_evidence = any(s.evidence_gathered for s in recent_steps[-3:])
            if not has_evidence:
                return False, "Need new evidence before exiting minimal mode"

        # Check for hypothesis
        if self.state.exit_requires_hypothesis:
            has_hypothesis = any(s.hypothesis for s in recent_steps[-3:])
            if not has_hypothesis:
                return False, "Need new hypothesis before exiting minimal mode"

        return True, "Ready to exit minimal mode"

    def check_action_allowed(
        self,
        tool_name: str,
        tool_input: Dict[str, Any]
    ) -> Tuple[bool, str]:
        """
        Check if an action is allowed in minimal mode.

        Returns (allowed, reason).
        """
        if not self.state.active:
            return True, ""

        # Check tool
        if tool_name not in MINIMAL_MODE_ALLOWED_TOOLS:
            return False, f"Tool '{tool_name}' blocked in minimal mode"

        # Special handling for Bash
        if tool_name == "Bash":
            command = str(tool_input.get("command", "")).lower()

            # Check blocked patterns
            for blocked in MINIMAL_MODE_BASH_BLOCKED:
                if blocked in command:
                    return False, f"Command '{blocked}' blocked in minimal mode"

            # Check if it's a diagnostic/test command
            is_allowed = any(allowed in command for allowed in MINIMAL_MODE_BASH_PATTERNS)
            if not is_allowed:
                return False, "Only diagnostic/test commands allowed in minimal mode"

        # Check file operations
        if tool_name in ("Edit", "Write"):
            if not self.state.edits_allowed:
                return False, "Edits blocked in minimal mode - only diagnostics allowed"

        return True, ""

    def get_allowed_actions(self) -> List[str]:
        """Get list of allowed actions in minimal mode."""
        return [
            "Read files to gather information",
            "Glob/Grep to search codebase",
            "Run tests to verify state",
            "Run diagnostic commands (ls, cat, git status)",
            "Simplify scope (identify smallest failing unit)",
            "Form hypotheses about root cause",
        ]

    def get_blocked_actions(self) -> List[str]:
        """Get list of blocked actions in minimal mode."""
        return [
            "Edit files",
            "Write new files",
            "Refactor code",
            "Add new features",
            "Install dependencies",
            "Commit changes",
        ]

    def get_guidance(self) -> str:
        """Get guidance for operating in minimal mode."""
        return """
MINIMAL MODE ACTIVE

You are in minimal mode because the smart approach isn't working.

ALLOWED:
- Read files and gather information
- Search the codebase
- Run tests and diagnostics
- Simplify the problem scope

NOT ALLOWED:
- Edit or write files
- Refactor code
- Add features
- Make broad changes

YOUR GOAL:
1. Find the smallest failing unit
2. Gather concrete evidence
3. Form a testable hypothesis
4. Only then request to exit minimal mode

Remember: "If progress is unclear, stop acting and change the question."
"""

    def get_stats(self) -> Dict[str, Any]:
        """Get minimal mode statistics."""
        entries = [h for h in self.history if h["event"] == "enter"]
        exits = [h for h in self.history if h["event"] == "exit"]

        return {
            "currently_active": self.state.active,
            "reason": self.state.reason.value if self.state.reason else None,
            "times_entered": len(entries),
            "times_exited": len(exits),
            "avg_duration_steps": (
                sum(e.get("duration_steps", 0) for e in exits) / len(exits)
                if exits else 0
            ),
        }


# Singleton
_minimal_mode_controller = None


def get_minimal_mode_controller() -> MinimalModeController:
    """Get singleton minimal mode controller."""
    global _minimal_mode_controller
    if _minimal_mode_controller is None:
        _minimal_mode_controller = MinimalModeController()
    return _minimal_mode_controller
