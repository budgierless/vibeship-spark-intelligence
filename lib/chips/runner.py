"""
ChipRunner: Executes observers and extracts fields from events.

When an event triggers a chip:
1. Find matching observers
2. Extract required/optional fields
3. Store captured data
4. Trigger learners if enough data
"""

import re
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

from .loader import ChipSpec, ObserverSpec
from .store import get_chip_store


@dataclass
class CapturedData:
    """Data captured by an observer."""
    observer_name: str
    chip_id: str
    timestamp: str
    session_id: str
    fields: Dict[str, Any] = field(default_factory=dict)
    event_type: str = ""
    confidence: float = 1.0


class ChipRunner:
    """
    Runs chip observers on events and extracts data.

    Flow:
    1. Event comes in
    2. Find matching observers based on triggers
    3. Extract fields using extraction rules
    4. Store captured data
    5. Return insights if any
    """

    def __init__(self, spec: ChipSpec):
        self.spec = spec
        self.store = get_chip_store(spec.id)

    def process_event(self, event: Dict) -> List[Dict]:
        """
        Process an event through this chip's observers.

        Returns list of insights generated.
        """
        insights = []
        session_id = event.get("session_id", "unknown")
        event_content = self._get_event_content(event)

        # Find matching observers
        matching_observers = self._find_matching_observers(event_content)

        for observer in matching_observers:
            # Extract fields
            captured = self._extract_fields(observer, event, event_content)

            if captured.fields:
                # Store the captured data
                self.store.add_observation(captured)

                # Generate insight if we have required fields
                insight = self._generate_insight(observer, captured)
                if insight:
                    insights.append(insight)

        return insights

    def _get_event_content(self, event: Dict) -> str:
        """Extract searchable content from event."""
        parts = []

        for key in ("content", "text", "message", "prompt", "user_prompt", "description"):
            if key in event:
                parts.append(str(event[key]))

        payload = event.get("payload", {})
        if isinstance(payload, dict):
            for key in ("text", "content", "message", "prompt"):
                if key in payload:
                    parts.append(str(payload[key]))
        elif isinstance(payload, str):
            parts.append(payload)

        return " ".join(parts)

    def _find_matching_observers(self, content: str) -> List[ObserverSpec]:
        """Find observers whose triggers match the content."""
        matching = []
        content_lower = content.lower()

        for observer in self.spec.observers:
            for trigger in observer.triggers:
                if trigger.lower() in content_lower:
                    matching.append(observer)
                    break

        return matching

    def _extract_fields(self, observer: ObserverSpec, event: Dict, content: str) -> CapturedData:
        """Extract fields from event using observer's extraction rules."""
        captured = CapturedData(
            observer_name=observer.name,
            chip_id=self.spec.id,
            timestamp=datetime.utcnow().isoformat(),
            session_id=event.get("session_id", "unknown"),
            event_type=event.get("type") or event.get("hook_event", "unknown"),
        )

        # Try extraction rules first
        for extraction in observer.extraction:
            field_name = extraction.get("field", "")
            value = None

            # Pattern extraction
            patterns = extraction.get("patterns", [])
            for pattern in patterns:
                try:
                    match = re.search(pattern, content, re.IGNORECASE)
                    if match and match.groups():
                        value = match.group(1).strip()
                        break
                except re.error:
                    pass

            # Keyword extraction
            if not value:
                keywords = extraction.get("keywords", {})
                for keyword_value, keyword_patterns in keywords.items():
                    for kp in keyword_patterns:
                        if kp.lower() in content.lower():
                            value = keyword_value
                            break
                    if value:
                        break

            if value:
                captured.fields[field_name] = value

        # Try to extract required fields from event directly
        for field_name in observer.capture_required:
            if field_name not in captured.fields:
                # Check event and payload
                if field_name in event:
                    captured.fields[field_name] = event[field_name]
                elif isinstance(event.get("payload"), dict) and field_name in event["payload"]:
                    captured.fields[field_name] = event["payload"][field_name]

        # Try optional fields
        for field_name in observer.capture_optional:
            if field_name not in captured.fields:
                if field_name in event:
                    captured.fields[field_name] = event[field_name]
                elif isinstance(event.get("payload"), dict) and field_name in event["payload"]:
                    captured.fields[field_name] = event["payload"][field_name]

        # Calculate confidence based on required fields captured
        required_count = len(observer.capture_required)
        if required_count > 0:
            captured_required = sum(1 for f in observer.capture_required if f in captured.fields)
            captured.confidence = captured_required / required_count
        else:
            captured.confidence = 1.0

        return captured

    def _generate_insight(self, observer: ObserverSpec, captured: CapturedData) -> Optional[Dict]:
        """Generate an insight from captured data."""
        # Only generate if we have meaningful data
        if not captured.fields or captured.confidence < 0.5:
            return None

        # Build insight
        field_summary = ", ".join(f"{k}={v}" for k, v in list(captured.fields.items())[:5])

        return {
            "chip_id": self.spec.id,
            "chip_name": self.spec.name,
            "observer": observer.name,
            "insight": f"{observer.description}: {field_summary}",
            "confidence": captured.confidence,
            "context": f"Captured by {self.spec.name} chip",
            "timestamp": captured.timestamp,
            "session_id": captured.session_id,
        }

    def check_outcomes(self, data: Dict) -> Optional[Dict]:
        """
        Check if data matches any outcome conditions.

        Returns outcome insight if matched.
        """
        # Check positive outcomes
        for outcome in self.spec.outcomes_positive:
            if self._evaluate_condition(outcome.condition, data):
                return {
                    "type": "positive",
                    "insight": outcome.insight,
                    "weight": outcome.weight,
                    "action": outcome.action,
                }

        # Check negative outcomes
        for outcome in self.spec.outcomes_negative:
            if self._evaluate_condition(outcome.condition, data):
                return {
                    "type": "negative",
                    "insight": outcome.insight,
                    "weight": outcome.weight,
                    "action": outcome.action,
                }

        # Check neutral outcomes
        for outcome in self.spec.outcomes_neutral:
            if self._evaluate_condition(outcome.condition, data):
                return {
                    "type": "neutral",
                    "insight": outcome.insight,
                    "weight": outcome.weight,
                    "action": outcome.action,
                }

        return None

    def _evaluate_condition(self, condition: str, data: Dict) -> bool:
        """
        Evaluate a simple condition against data.

        Supports: field > value, field < value, field == value
        """
        if not condition:
            return False

        # Simple pattern: field op value
        match = re.match(r"(\w+)\s*(>|<|>=|<=|==|!=)\s*(.+)", condition)
        if not match:
            # Check if condition is a field name (truthy check)
            field = condition.strip()
            return bool(data.get(field))

        field, op, value = match.groups()
        field_value = data.get(field)

        if field_value is None:
            return False

        # Try numeric comparison
        try:
            field_num = float(field_value)
            value_num = float(value)

            if op == ">":
                return field_num > value_num
            elif op == "<":
                return field_num < value_num
            elif op == ">=":
                return field_num >= value_num
            elif op == "<=":
                return field_num <= value_num
            elif op == "==":
                return field_num == value_num
            elif op == "!=":
                return field_num != value_num
        except (ValueError, TypeError):
            pass

        # String comparison
        if op == "==":
            return str(field_value) == value.strip()
        elif op == "!=":
            return str(field_value) != value.strip()

        return False

    def get_stats(self) -> Dict[str, Any]:
        """Get runner statistics."""
        return {
            "chip_id": self.spec.id,
            "chip_name": self.spec.name,
            "observers": len(self.spec.observers),
            "learners": len(self.spec.learners),
            "store_stats": self.store.get_stats(),
        }
