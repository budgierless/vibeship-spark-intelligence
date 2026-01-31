"""
Safety policy stubs for chip guardrails.

These utilities are intentionally lightweight and conservative. They do not
depend on external services and can be enforced locally.
"""

from dataclasses import dataclass
import re
from typing import Any, Dict, Iterable, List, Optional


@dataclass
class PolicyDecision:
    allowed: bool
    reason: str
    severity: str = "info"


class SafetyPolicy:
    """Policy evaluation for chip specs and insights."""

    def __init__(self, block_patterns: Optional[Iterable[str]] = None):
        self._patterns: List[re.Pattern] = [
            re.compile(p, re.IGNORECASE) for p in (block_patterns or [])
        ]

    def check_text(self, text: str) -> PolicyDecision:
        """Block text that matches a banned pattern."""
        if not text:
            return PolicyDecision(True, "empty")
        for pattern in self._patterns:
            if pattern.search(text):
                return PolicyDecision(False, f"blocked by pattern: {pattern.pattern}", "high")
        return PolicyDecision(True, "ok")

    def requires_human_approval(self, spec: Dict[str, Any]) -> bool:
        """High-risk chips should require explicit approval for evolution."""
        chip = (spec or {}).get("chip", {}) if isinstance(spec, dict) else {}
        return chip.get("risk_level") == "high"

    @classmethod
    def from_chip_spec(cls, spec: Dict[str, Any]) -> "SafetyPolicy":
        """Create a policy using harm_avoidance hints from the chip spec."""
        chip = (spec or {}).get("chip", {}) if isinstance(spec, dict) else {}
        harm = chip.get("harm_avoidance") or []
        # Interpret harm_avoidance entries as simple patterns if provided.
        patterns = [re.escape(str(h)) for h in harm if h]
        return cls(block_patterns=patterns)
