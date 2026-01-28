"""
SequenceDetector: Detects successful/failed tool sequences.

MEDIUM VALUE - Learns approach patterns:

Success patterns:
- Read -> Edit (verify before modify)
- Glob -> Read -> Edit (find, verify, modify)
- Write -> Bash (create, run)

Failure patterns:
- Edit without Read (content mismatch)
- Bash with wrong paths (file_not_found)
- Multiple failed attempts

Helps learn:
1. What sequences work reliably
2. What sequences lead to failures
3. Approach preferences
"""

from collections import defaultdict
from typing import Any, Dict, List, Optional, Tuple

from .base import DetectedPattern, PatternDetector, PatternType


# Known good patterns (tool sequences that generally succeed)
GOOD_PATTERNS = {
    ("Read", "Edit"): "Verify content before editing",
    ("Glob", "Read"): "Find files then read them",
    ("Glob", "Read", "Edit"): "Find, verify, then edit",
    ("Read", "Write"): "Read existing then overwrite",
    ("Write", "Bash"): "Create file then execute",
}

# Known problematic patterns (tool sequences that often fail)
PROBLEMATIC_PATTERNS = {
    ("Edit",): "Edit without prior Read may cause content mismatch",
    ("Bash", "Bash", "Bash"): "Multiple Bash attempts may indicate confusion",
}

# Minimum sequence length to track
MIN_SEQUENCE_LENGTH = 2
MAX_SEQUENCE_LENGTH = 5


class SequenceDetector(PatternDetector):
    """
    Detects tool usage sequences and their outcomes.

    Tracks sequences of tool calls within a session and correlates
    with success/failure to learn what patterns work.
    """

    def __init__(self):
        super().__init__("SequenceDetector")
        # session_id -> list of (tool_name, success: bool)
        self._tool_history: Dict[str, List[Tuple[str, bool]]] = {}
        # session_id -> count of consecutive failures
        self._failure_streak: Dict[str, int] = {}
        # Track detected sequences to avoid duplicates
        self._detected_sequences: Dict[str, set] = {}

    def _add_tool_event(self, session_id: str, tool_name: str, success: bool):
        """Add a tool event to history."""
        if session_id not in self._tool_history:
            self._tool_history[session_id] = []
            self._detected_sequences[session_id] = set()

        self._tool_history[session_id].append((tool_name, success))

        # Update failure streak
        if session_id not in self._failure_streak:
            self._failure_streak[session_id] = 0

        if not success:
            self._failure_streak[session_id] += 1
        else:
            self._failure_streak[session_id] = 0

        # Keep only last 20 events
        if len(self._tool_history[session_id]) > 20:
            self._tool_history[session_id] = self._tool_history[session_id][-20:]

    def _get_recent_sequence(self, session_id: str, length: int) -> List[Tuple[str, bool]]:
        """Get the most recent N tool events."""
        history = self._tool_history.get(session_id, [])
        return history[-length:] if len(history) >= length else history

    def _check_known_patterns(self, session_id: str) -> List[DetectedPattern]:
        """Check for known good/bad patterns in recent history."""
        patterns = []
        history = self._tool_history.get(session_id, [])

        if len(history) < MIN_SEQUENCE_LENGTH:
            return patterns

        # Check for good patterns
        for length in range(MIN_SEQUENCE_LENGTH, min(len(history) + 1, MAX_SEQUENCE_LENGTH + 1)):
            recent = history[-length:]
            tool_sequence = tuple(t[0] for t in recent)
            all_success = all(t[1] for t in recent)

            # Check if this matches a known good pattern
            if tool_sequence in GOOD_PATTERNS and all_success:
                seq_key = f"good:{tool_sequence}"
                if seq_key in self._detected_sequences.get(session_id, set()):
                    continue

                self._detected_sequences[session_id].add(seq_key)

                patterns.append(DetectedPattern(
                    pattern_type=PatternType.SEQUENCE_SUCCESS,
                    confidence=0.85,
                    evidence=[
                        f"Sequence: {' -> '.join(tool_sequence)}",
                        f"Why good: {GOOD_PATTERNS[tool_sequence]}",
                    ],
                    context={
                        "sequence": list(tool_sequence),
                        "all_success": True,
                        "known_pattern": True,
                    },
                    session_id=session_id,
                    suggested_insight=f"Pattern '{' -> '.join(tool_sequence)}' works well: {GOOD_PATTERNS[tool_sequence]}",
                    suggested_category="reasoning",
                ))

        # Check for problematic patterns
        for prob_seq, reason in PROBLEMATIC_PATTERNS.items():
            if len(history) >= len(prob_seq):
                recent = history[-len(prob_seq):]
                tool_sequence = tuple(t[0] for t in recent)
                any_failure = any(not t[1] for t in recent)

                if tool_sequence == prob_seq and any_failure:
                    seq_key = f"bad:{tool_sequence}"
                    if seq_key in self._detected_sequences.get(session_id, set()):
                        continue

                    self._detected_sequences[session_id].add(seq_key)

                    patterns.append(DetectedPattern(
                        pattern_type=PatternType.SEQUENCE_FAILURE,
                        confidence=0.8,
                        evidence=[
                            f"Sequence: {' -> '.join(tool_sequence)}",
                            f"Problem: {reason}",
                        ],
                        context={
                            "sequence": list(tool_sequence),
                            "any_failure": True,
                            "known_problematic": True,
                        },
                        session_id=session_id,
                        suggested_insight=f"Pattern '{' -> '.join(tool_sequence)}' risky: {reason}",
                        suggested_category="self_awareness",
                    ))

        return patterns

    def _detect_failure_streak(self, session_id: str) -> List[DetectedPattern]:
        """Detect when there are multiple consecutive failures."""
        patterns = []
        streak = self._failure_streak.get(session_id, 0)

        if streak >= 3:
            history = self._tool_history.get(session_id, [])
            recent_failures = [t[0] for t in history[-streak:] if not t[1]]

            seq_key = f"streak:{streak}:{tuple(recent_failures)}"
            if seq_key in self._detected_sequences.get(session_id, set()):
                return patterns

            self._detected_sequences[session_id].add(seq_key)

            confidence = min(0.95, 0.7 + (streak - 3) * 0.1)

            patterns.append(DetectedPattern(
                pattern_type=PatternType.SEQUENCE_FAILURE,
                confidence=confidence,
                evidence=[
                    f"{streak} consecutive failures",
                    f"Failed tools: {', '.join(recent_failures)}",
                ],
                context={
                    "streak_length": streak,
                    "failed_tools": recent_failures,
                },
                session_id=session_id,
                suggested_insight=f"Struggling with {', '.join(set(recent_failures))} - approach may need rethinking",
                suggested_category="self_awareness",
            ))

        return patterns

    def _detect_new_success_pattern(self, session_id: str) -> List[DetectedPattern]:
        """Detect new successful patterns not in known patterns."""
        patterns = []
        history = self._tool_history.get(session_id, [])

        if len(history) < 3:
            return patterns

        # Look at the last successful sequence
        recent = history[-4:]  # Check last 4
        if not recent or not recent[-1][1]:  # Last must be success
            return patterns

        # Find the start of this successful run
        success_run = []
        for tool, success in reversed(recent):
            if success:
                success_run.insert(0, tool)
            else:
                break

        if len(success_run) >= 3:
            tool_sequence = tuple(success_run)

            # Skip if it's a known pattern
            if tool_sequence in GOOD_PATTERNS:
                return patterns

            seq_key = f"new_success:{tool_sequence}"
            if seq_key in self._detected_sequences.get(session_id, set()):
                return patterns

            self._detected_sequences[session_id].add(seq_key)

            patterns.append(DetectedPattern(
                pattern_type=PatternType.SEQUENCE_SUCCESS,
                confidence=0.7,  # Lower confidence for unknown patterns
                evidence=[
                    f"Successful sequence: {' -> '.join(tool_sequence)}",
                    f"Length: {len(tool_sequence)} tools",
                ],
                context={
                    "sequence": list(tool_sequence),
                    "all_success": True,
                    "known_pattern": False,
                },
                session_id=session_id,
                suggested_insight=f"Sequence '{' -> '.join(tool_sequence)}' worked well",
                suggested_category="reasoning",
            ))

        return patterns

    def process_event(self, event: Dict) -> List[DetectedPattern]:
        """Process event and detect sequence patterns."""
        patterns = []
        session_id = event.get("session_id", "unknown")
        hook_event = event.get("hook_event", "")
        tool_name = event.get("tool_name")

        # Track tool events
        if hook_event == "PostToolUse" and tool_name:
            self._add_tool_event(session_id, tool_name, success=True)

            # Check for patterns
            patterns.extend(self._check_known_patterns(session_id))
            patterns.extend(self._detect_new_success_pattern(session_id))

        elif hook_event == "PostToolUseFailure" and tool_name:
            self._add_tool_event(session_id, tool_name, success=False)

            # Check for failure patterns
            patterns.extend(self._check_known_patterns(session_id))
            patterns.extend(self._detect_failure_streak(session_id))

        return patterns
