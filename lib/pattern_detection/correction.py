"""
CorrectionDetector: Detects user corrections.

HIGH VALUE - Direct preference learning signals:
- "no, I meant..."
- "not that"
- "actually, I wanted..."
- "wrong"
- "that's not what I asked"
- "could you instead..."

When user corrects AI, we learn:
1. What AI did wrong
2. What user actually wanted
3. Context for future similar situations
"""

import re
from typing import Any, Dict, List, Optional

from .base import DetectedPattern, PatternDetector, PatternType


# Correction signal patterns with confidence weights
CORRECTION_PATTERNS = [
    # Direct negations (high confidence)
    (r"\bno[,.]?\s*(i\s+meant|that'?s\s+not|i\s+wanted)", 0.95),
    (r"\bnot\s+that\b", 0.9),
    (r"\bwrong\b", 0.85),
    (r"\bthat'?s\s+not\s+(what|right|correct)", 0.9),

    # Polite corrections (medium confidence)
    (r"\bactually[,.]?\s*(i|could|can|let'?s)", 0.8),
    (r"\bi\s+meant\b", 0.85),
    (r"\bi\s+wanted\b", 0.75),
    (r"\bcould\s+you\s+instead\b", 0.85),
    (r"\blet'?s\s+(go\s+with|try|do)\s+", 0.7),

    # Implicit corrections (lower confidence)
    (r"\binstead[,.]?\s+(of|let'?s|can)", 0.7),
    (r"\bforget\s+(that|it|about)", 0.75),
    (r"\bscratch\s+that\b", 0.85),
    (r"\bnever\s*mind\b", 0.7),

    # Clarifications that imply correction
    (r"\bi\s+should\s+clarify\b", 0.65),
    (r"\bto\s+be\s+clear\b", 0.6),
    (r"\bwhat\s+i\s+mean(t)?\s+is\b", 0.75),
]


def _extract_correction_context(text: str, match_start: int) -> Dict[str, str]:
    """Extract what was wrong and what user wants from correction text."""
    # Get text after the correction signal
    after_match = text[match_start:].strip()

    # Try to extract "not X, but Y" patterns
    not_but = re.search(r"not\s+(.+?)[,.]?\s*but\s+(.+?)(?:[.!?]|$)", after_match, re.I)
    if not_but:
        return {
            "rejected": not_but.group(1).strip(),
            "wanted": not_but.group(2).strip(),
        }

    # Try to extract "instead of X, do Y"
    instead = re.search(r"instead\s+of\s+(.+?)[,.]?\s*(.+?)(?:[.!?]|$)", after_match, re.I)
    if instead:
        return {
            "rejected": instead.group(1).strip(),
            "wanted": instead.group(2).strip(),
        }

    # Otherwise just capture what follows
    return {
        "wanted": after_match[:100] if len(after_match) > 100 else after_match,
    }


class CorrectionDetector(PatternDetector):
    """
    Detects when user is correcting AI's understanding or output.

    This is HIGH VALUE for learning because:
    - User explicitly states what was wrong
    - User explicitly states what they wanted
    - Strong signal for preference learning
    """

    def __init__(self):
        super().__init__("CorrectionDetector")
        self._recent_tool_actions: Dict[str, List[Dict]] = {}  # session -> recent AI actions

    def _buffer_tool_action(self, session_id: str, tool_name: str, tool_input: Dict):
        """Track recent AI actions to correlate with corrections."""
        if session_id not in self._recent_tool_actions:
            self._recent_tool_actions[session_id] = []

        self._recent_tool_actions[session_id].append({
            "tool": tool_name,
            "input": tool_input,
        })

        # Keep only last 5 actions
        if len(self._recent_tool_actions[session_id]) > 5:
            self._recent_tool_actions[session_id] = self._recent_tool_actions[session_id][-5:]

    def _get_recent_action(self, session_id: str) -> Optional[Dict]:
        """Get most recent AI action that might be being corrected."""
        actions = self._recent_tool_actions.get(session_id, [])
        return actions[-1] if actions else None

    def process_event(self, event: Dict) -> List[DetectedPattern]:
        """
        Process event and detect correction patterns.

        Looks for correction signals in user messages.
        """
        patterns: List[DetectedPattern] = []
        session_id = event.get("session_id", "unknown")
        hook_event = event.get("hook_event", "")

        # Track AI actions (tool use)
        if hook_event in ("PostToolUse", "PostToolUseFailure"):
            tool_name = event.get("tool_name")
            tool_input = event.get("tool_input", {})
            if tool_name:
                self._buffer_tool_action(session_id, tool_name, tool_input)
            return patterns

        # Look for corrections in user messages
        if hook_event == "UserPromptSubmit":
            payload = event.get("payload", {})
            text = payload.get("text", "") if isinstance(payload, dict) else ""

            if not text:
                text = event.get("prompt", "") or event.get("user_prompt", "")

            if not text:
                return patterns

            text_lower = text.lower()

            # Check each correction pattern
            best_match = None
            best_confidence = 0.0

            for pattern, confidence in CORRECTION_PATTERNS:
                match = re.search(pattern, text_lower)
                if match and confidence > best_confidence:
                    best_match = match
                    best_confidence = confidence

            if best_match and best_confidence >= 0.6:
                # Extract context about what's being corrected
                correction_context = _extract_correction_context(text, best_match.start())

                # Get what AI just did (might be what's being corrected)
                recent_action = self._get_recent_action(session_id)

                # Build evidence
                evidence = [
                    f"User said: {text[:150]}...",
                    f"Matched pattern: {best_match.group(0)}",
                ]

                context = {
                    "user_text": text,
                    "correction_signal": best_match.group(0),
                    **correction_context,
                }

                if recent_action:
                    evidence.append(f"After AI used: {recent_action['tool']}")
                    context["preceding_action"] = recent_action

                # Create suggested insight
                suggested_insight = None
                if "rejected" in correction_context:
                    suggested_insight = f"User prefers '{correction_context.get('wanted', 'alternative')}' over '{correction_context['rejected']}'"
                elif "wanted" in correction_context:
                    suggested_insight = f"User wanted: {correction_context['wanted']}"

                patterns.append(DetectedPattern(
                    pattern_type=PatternType.CORRECTION,
                    confidence=best_confidence,
                    evidence=evidence,
                    context=context,
                    session_id=session_id,
                    suggested_insight=suggested_insight,
                    suggested_category="user_understanding",
                ))

        return patterns
