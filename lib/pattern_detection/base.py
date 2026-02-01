"""
Base classes for Pattern Detection Layer.

All detectors inherit from PatternDetector and emit DetectedPattern instances.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional


class PatternType(str, Enum):
    """Types of patterns we can detect."""
    CORRECTION = "correction"          # User correcting AI's understanding
    SATISFACTION = "satisfaction"      # User expressing satisfaction
    FRUSTRATION = "frustration"        # User expressing frustration
    REPETITION = "repetition"          # Same request multiple times
    STYLE = "style"                    # Working style preference


@dataclass
class DetectedPattern:
    """A pattern detected from events."""
    pattern_type: PatternType
    confidence: float              # 0.0-1.0 how confident we are
    evidence: List[str]            # What triggered this detection
    context: Dict[str, Any]        # Additional context
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    session_id: Optional[str] = None

    # For learning
    suggested_insight: Optional[str] = None
    suggested_category: Optional[str] = None  # Maps to CognitiveCategory

    def to_dict(self) -> Dict[str, Any]:
        return {
            "pattern_type": self.pattern_type.value,
            "confidence": self.confidence,
            "evidence": self.evidence,
            "context": self.context,
            "timestamp": self.timestamp,
            "session_id": self.session_id,
            "suggested_insight": self.suggested_insight,
            "suggested_category": self.suggested_category,
        }


class PatternDetector(ABC):
    """
    Base class for pattern detectors.

    Each detector:
    1. Receives events via process_event()
    2. Maintains internal state (session buffer, counts, etc.)
    3. Emits DetectedPattern when pattern is found
    """

    def __init__(self, name: str):
        self.name = name
        self._session_buffer: Dict[str, List[Dict]] = {}  # session_id -> events
        self._max_buffer_size = 50  # Keep last N events per session

    def _buffer_event(self, session_id: str, event: Dict):
        """Add event to session buffer."""
        if session_id not in self._session_buffer:
            self._session_buffer[session_id] = []

        self._session_buffer[session_id].append(event)

        # Trim to max size
        if len(self._session_buffer[session_id]) > self._max_buffer_size:
            self._session_buffer[session_id] = self._session_buffer[session_id][-self._max_buffer_size:]

    def _get_buffer(self, session_id: str) -> List[Dict]:
        """Get session buffer."""
        return self._session_buffer.get(session_id, [])

    def _clear_session(self, session_id: str):
        """Clear session buffer."""
        if session_id in self._session_buffer:
            del self._session_buffer[session_id]

    @abstractmethod
    def process_event(self, event: Dict) -> List[DetectedPattern]:
        """
        Process an event and return any detected patterns.

        Args:
            event: Raw event dict with keys like:
                - session_id: str
                - hook_event: str (UserPromptSubmit, PostToolUse, etc.)
                - tool_name: Optional[str]
                - tool_input: Optional[dict]
                - error: Optional[str]
                - payload: Optional[dict] (for messages)

        Returns:
            List of detected patterns (empty if none detected)
        """
        pass

    def get_stats(self) -> Dict[str, Any]:
        """Get detector statistics."""
        return {
            "name": self.name,
            "active_sessions": len(self._session_buffer),
            "total_buffered_events": sum(len(v) for v in self._session_buffer.values()),
        }
