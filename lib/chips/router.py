"""
Chip Router - Match events to chip triggers.

This was the third missing piece: when an event comes in,
which chips should process it?
"""

import re
import logging
from typing import Dict, List, Tuple, Any, Optional
from dataclasses import dataclass

from .loader import Chip, ChipObserver

log = logging.getLogger("spark.chips")


@dataclass
class TriggerMatch:
    """A matched trigger with context."""
    chip: Chip
    observer: Optional[ChipObserver]
    trigger: str
    confidence: float
    content_snippet: str  # What content matched


class ChipRouter:
    """
    Routes events to appropriate chips based on trigger matching.

    When we see an Edit to "lobster-royale/src/main.js" containing
    "health", "damage", "physics", this routes to the game_dev chip.
    """

    def route_event(self, event: Dict[str, Any], chips: List[Chip]) -> List[TriggerMatch]:
        """
        Route an event to matching chips.

        Returns all matches sorted by confidence.
        """
        matches = []

        # Extract searchable content from event
        content = self._extract_content(event)
        if not content:
            return matches

        content_lower = content.lower()
        self._current_event_type = event.get('event_type') or event.get('hook_event') or event.get('type') or event.get('kind')
        self._current_tool_name = event.get('tool_name') or event.get('tool')

        for chip in chips:
            chip_matches = self._match_chip(chip, content_lower, content)
            matches.extend(chip_matches)

        # Sort by confidence
        matches.sort(key=lambda m: m.confidence, reverse=True)
        return matches

    def _extract_content(self, event: Dict[str, Any]) -> str:
        """
        Extract searchable content from an event.

        Combines: tool name, file path, input, output snippet
        """
        parts = []

        # Event type
        event_type = event.get('event_type') or event.get('hook_event') or event.get('type') or event.get('kind')
        if event_type:
            parts.append(str(event_type))

        # Tool name
        tool = event.get('tool_name') or event.get('tool')
        if tool:
            parts.append(str(tool))

        # File path (very important for domain detection)
        file_path = event.get('file_path')
        if not file_path:
            inp = event.get('input') or event.get('tool_input') or {}
            if isinstance(inp, dict):
                file_path = inp.get('file_path') or inp.get('path')
        if file_path:
            parts.append(str(file_path))

        # Input content
        inp = event.get('input') or event.get('tool_input')
        if inp:
            if isinstance(inp, dict):
                for v in inp.values():
                    if v and isinstance(v, str) and len(v) < 5000:
                        parts.append(v)
            elif isinstance(inp, str):
                parts.append(inp[:2000])

        # Output/result (limited)
        output = event.get('output') or event.get('result')
        if output and isinstance(output, str):
            parts.append(output[:1000])

        # CWD (project context)
        cwd = event.get('cwd') or event.get('data', {}).get('cwd')
        if cwd:
            parts.append(str(cwd))

        return ' '.join(parts)

    def _match_chip(self, chip: Chip, content_lower: str, content_raw: str) -> List[TriggerMatch]:
        """Match content against a chip's triggers."""
        matches = []
        seen_triggers = set()

        # Event-type triggers (high confidence)
        event_type = (self._current_event_type or "").lower()
        for event_trigger in getattr(chip, "trigger_events", []) or []:
            if event_type and event_type == str(event_trigger).lower():
                if event_trigger in seen_triggers:
                    continue
                seen_triggers.add(event_trigger)
                matches.append(TriggerMatch(
                    chip=chip,
                    observer=None,
                    trigger=str(event_trigger),
                    confidence=0.85,
                    content_snippet=str(event_trigger)
                ))

        # Tool triggers (contextual)
        tool_name = (self._current_tool_name or "").lower()
        for tool_trigger in getattr(chip, "trigger_tools", []) or []:
            if isinstance(tool_trigger, dict):
                name = tool_trigger.get("name", "")
                context_patterns = tool_trigger.get("context_contains", [])
            else:
                name = str(tool_trigger)
                context_patterns = []

            if tool_name and name.lower() == tool_name:
                if context_patterns and context_patterns != ["*"]:
                    if not any(p.lower() in content_lower for p in context_patterns):
                        continue
                trigger_label = f"tool:{name}"
                if trigger_label in seen_triggers:
                    continue
                seen_triggers.add(trigger_label)
                matches.append(TriggerMatch(
                    chip=chip,
                    observer=None,
                    trigger=trigger_label,
                    confidence=0.8,
                    content_snippet=name
                ))

        # Match observer-level triggers (higher confidence if observer-specific)
        for observer in chip.observers:
            for trigger in observer.triggers:
                if trigger in seen_triggers:
                    continue

                match_result = self._match_trigger(trigger, content_lower)
                if match_result:
                    seen_triggers.add(trigger)
                    confidence, snippet = match_result
                    # Boost confidence slightly for observer matches
                    matches.append(TriggerMatch(
                        chip=chip,
                        observer=observer,
                        trigger=trigger,
                        confidence=min(1.0, confidence + 0.1),
                        content_snippet=snippet
                    ))

        # Match chip-level triggers
        trigger_patterns = getattr(chip, "trigger_patterns", None) or chip.triggers
        for trigger in trigger_patterns:
            if trigger in seen_triggers:
                continue

            match_result = self._match_trigger(trigger, content_lower)
            if match_result:
                seen_triggers.add(trigger)
                confidence, snippet = match_result
                matches.append(TriggerMatch(
                    chip=chip,
                    observer=None,
                    trigger=trigger,
                    confidence=confidence,
                    content_snippet=snippet
                ))

        return matches

    def _match_trigger(self, trigger: str, content: str) -> Optional[Tuple[float, str]]:
        """
        Match a trigger against content.

        Returns (confidence, snippet) or None.
        """
        trigger_lower = trigger.lower()

        # Exact word boundary match (highest confidence)
        pattern = r'\b' + re.escape(trigger_lower) + r'\b'
        match = re.search(pattern, content)
        if match:
            start = max(0, match.start() - 20)
            end = min(len(content), match.end() + 20)
            snippet = content[start:end]
            return (0.95, snippet)

        # Substring match (medium confidence)
        if trigger_lower in content:
            idx = content.find(trigger_lower)
            start = max(0, idx - 20)
            end = min(len(content), idx + len(trigger_lower) + 20)
            snippet = content[start:end]
            return (0.7, snippet)

        return None

    def get_best_match(self, event: Dict[str, Any], chips: List[Chip]) -> Optional[TriggerMatch]:
        """Get the single best matching chip for an event."""
        matches = self.route_event(event, chips)
        return matches[0] if matches else None

    def get_matching_observers(self, event: Dict[str, Any], chips: List[Chip]) -> List[Tuple[Chip, ChipObserver, float]]:
        """Get all matching observers for an event (deduplicated)."""
        matches = self.route_event(event, chips)

        # Group by observer, keep highest confidence per observer
        observer_matches = {}
        for match in matches:
            if match.observer:
                key = (match.chip.id, match.observer.name)
                if key not in observer_matches or match.confidence > observer_matches[key][2]:
                    observer_matches[key] = (match.chip, match.observer, match.confidence)

        return list(observer_matches.values())



_router: Optional[ChipRouter] = None


def get_router() -> ChipRouter:
    """Get singleton chip router."""
    global _router
    if _router is None:
        _router = ChipRouter()
    return _router
