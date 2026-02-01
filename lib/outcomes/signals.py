"""
Outcome Signals - Detect success/failure from events.

Watches for signals in user messages, tool outputs, and
other events that indicate whether something worked.
"""

import re
import logging
from dataclasses import dataclass
from typing import Dict, List, Optional, Any
from datetime import datetime
from enum import Enum

log = logging.getLogger("spark.outcomes")


class OutcomeType(Enum):
    SUCCESS = "success"
    FAILURE = "failure"
    NEUTRAL = "neutral"


@dataclass
class Outcome:
    """A detected outcome signal."""
    type: OutcomeType
    confidence: float
    source: str          # Where the signal came from
    content: str         # The content that triggered detection
    context: str         # Surrounding context
    timestamp: str
    event_id: Optional[str] = None

    def to_dict(self) -> Dict:
        return {
            "type": self.type.value,
            "confidence": self.confidence,
            "source": self.source,
            "content": self.content,
            "context": self.context,
            "timestamp": self.timestamp,
            "event_id": self.event_id,
        }


class OutcomeSignals:
    """Detect outcome signals from events."""

    # Success patterns with confidence weights
    SUCCESS_PATTERNS = [
        # Strong success signals
        (r"(?i)\b(perfect|excellent|exactly what i (wanted|needed))\b", 0.95),
        (r"(?i)\b(works perfectly|that's it|nailed it)\b", 0.9),
        (r"(?i)\b(ship it|done|complete|finished)\b", 0.8),
        (r"(?i)\bthank(s| you)\b", 0.6),

        # Technical success
        (r"(?i)tests?\s+(pass|passed|passing|succeeded)", 0.9),
        (r"(?i)build\s+(success|succeeded|passed)", 0.9),
        (r"(?i)deployed?\s+(success|to production)", 0.85),
        (r"(?i)no\s+errors?", 0.7),
        (r"exit code 0", 0.8),

        # Approval signals
        (r"(?i)\b(approved?|lgtm|looks good)\b", 0.85),
        (r"(?i)\b(yes|yep|yeah|correct|right)\b", 0.5),
        (r"(?i)\b(great|good|nice|awesome)\b", 0.6),
    ]

    # Failure patterns with confidence weights
    FAILURE_PATTERNS = [
        # Strong failure signals
        (r"(?i)\b(wrong|broken|doesn't work|not working)\b", 0.9),
        (r"(?i)\b(failed?|failure|error|bug)\b", 0.8),
        (r"(?i)\b(ugh|damn|shit|wtf|argh)\b", 0.85),
        (r"(?i)\b(try again|redo|revert)\b", 0.8),

        # Technical failure
        (r"(?i)tests?\s+(fail|failed|failing)", 0.95),
        (r"(?i)build\s+(fail|failed|error)", 0.95),
        (r"(?i)(exception|traceback|stack trace)", 0.85),
        (r"exit code [1-9]", 0.9),

        # Rejection signals
        (r"(?i)\b(no|nope|nah|incorrect|wrong)\b", 0.6),
        (r"(?i)\b(actually|wait|hold on)\b", 0.5),
        (r"(?i)\b(that's not|not what i)\b", 0.8),
    ]

    def __init__(self):
        self._compiled_success = [(re.compile(p), c) for p, c in self.SUCCESS_PATTERNS]
        self._compiled_failure = [(re.compile(p), c) for p, c in self.FAILURE_PATTERNS]

    def detect(self, event: Dict) -> Optional[Outcome]:
        """Detect outcome signal from an event."""
        # Extract content to analyze
        content = self._extract_content(event)
        if not content or len(content) < 3:
            return None

        # Check for success patterns
        success_score = self._match_patterns(content, self._compiled_success)

        # Check for failure patterns
        failure_score = self._match_patterns(content, self._compiled_failure)

        # Determine outcome
        if success_score > failure_score and success_score > 0.4:
            return Outcome(
                type=OutcomeType.SUCCESS,
                confidence=success_score,
                source=self._get_source(event),
                content=content[:200],
                context=self._get_context(event),
                timestamp=datetime.now().isoformat(),
                event_id=event.get("id"),
            )
        elif failure_score > success_score and failure_score > 0.4:
            return Outcome(
                type=OutcomeType.FAILURE,
                confidence=failure_score,
                source=self._get_source(event),
                content=content[:200],
                context=self._get_context(event),
                timestamp=datetime.now().isoformat(),
                event_id=event.get("id"),
            )

        return None

    def _extract_content(self, event: Dict) -> str:
        """Extract content to analyze from event."""
        parts = []

        # User messages are most important
        if event.get("event_type") == "user_prompt":
            payload = event.get("data", {}).get("payload", {})
            if payload.get("role") == "user":
                parts.append(str(payload.get("text", "")))

        # Tool outputs
        output = event.get("output") or event.get("result", "")
        if isinstance(output, str):
            parts.append(output[:500])

        # Tool input for context
        inp = event.get("tool_input") or event.get("input", {})
        if isinstance(inp, dict):
            for v in inp.values():
                if isinstance(v, str) and len(v) < 500:
                    parts.append(v)

        return " ".join(parts)

    def _match_patterns(self, content: str, patterns: List) -> float:
        """Match patterns and return max confidence."""
        max_confidence = 0.0
        for pattern, confidence in patterns:
            if pattern.search(content):
                max_confidence = max(max_confidence, confidence)
        return max_confidence

    def _get_source(self, event: Dict) -> str:
        """Get source description for event."""
        event_type = event.get("event_type", "unknown")
        tool = event.get("tool_name") or event.get("tool", "")
        if tool:
            return f"{event_type}/{tool}"
        return event_type

    def _get_context(self, event: Dict) -> str:
        """Get context around the event."""
        parts = []
        if event.get("cwd"):
            parts.append(f"project: {event['cwd']}")
        if event.get("tool_name"):
            parts.append(f"tool: {event['tool_name']}")
        return ", ".join(parts)

    def detect_batch(self, events: List[Dict]) -> List[Outcome]:
        """Detect outcomes from a batch of events."""
        outcomes = []
        for event in events:
            outcome = self.detect(event)
            if outcome:
                outcomes.append(outcome)
        return outcomes


# Singleton detector
_detector: Optional[OutcomeSignals] = None


def get_detector() -> OutcomeSignals:
    """Get singleton detector instance."""
    global _detector
    if _detector is None:
        _detector = OutcomeSignals()
    return _detector


def detect_outcome(event: Dict) -> Optional[Outcome]:
    """Detect outcome from event (convenience function)."""
    return get_detector().detect(event)
