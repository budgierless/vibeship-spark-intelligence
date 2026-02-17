"""
Intent Setter - Set learning intents based on mastery research.

Before observing, define what we're looking for.
This focuses learning on what matters for mastery.
"""

import json
import logging
import re
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime

from .mastery import get_researcher, DomainMastery

log = logging.getLogger("spark.research")

INTENTS_FILE = Path.home() / ".spark" / "research" / "intents.json"


def _unique_preserve_order(items: List[str], *, limit: int) -> List[str]:
    """Return first-seen unique strings in deterministic order."""
    seen = set()
    out: List[str] = []
    for item in items:
        text = re.sub(r"\s+", " ", str(item or "").strip())
        if not text:
            continue
        key = text.lower()
        if key in seen:
            continue
        seen.add(key)
        out.append(text)
        if len(out) >= max(0, int(limit)):
            break
    return out


@dataclass
class LearningIntent:
    """A specific thing to look for while learning."""
    name: str
    description: str
    triggers: List[str]  # Patterns that might indicate this
    positive_signals: List[str]  # Signs of doing it right
    negative_signals: List[str]  # Signs of doing it wrong
    priority: float = 0.5  # How important (0-1)
    domain: str = ""


@dataclass
class DomainIntent:
    """Complete learning intent for a domain session."""
    domain: str
    project_path: str

    # What to look for
    intents: List[LearningIntent] = field(default_factory=list)

    # Quick reference
    watch_for: List[str] = field(default_factory=list)  # Positive patterns
    warn_about: List[str] = field(default_factory=list)  # Anti-patterns

    # Focus areas (from user + mastery research)
    user_focus: List[str] = field(default_factory=list)
    mastery_focus: List[str] = field(default_factory=list)

    # Metadata
    created_at: str = ""
    based_on_mastery: bool = False

    def to_dict(self) -> Dict:
        d = asdict(self)
        d["intents"] = [asdict(i) for i in self.intents]
        return d

    @classmethod
    def from_dict(cls, data: Dict) -> 'DomainIntent':
        intents = [LearningIntent(**i) for i in data.pop("intents", [])]
        return cls(intents=intents, **{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


class IntentSetter:
    """Set and manage learning intents."""

    def __init__(self):
        self.researcher = get_researcher()
        self._active_intents: Dict[str, DomainIntent] = {}
        self._load_intents()

    def _load_intents(self):
        """Load active intents from disk."""
        if not INTENTS_FILE.exists():
            return

        try:
            with open(INTENTS_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                for project, intent_data in data.get("intents", {}).items():
                    self._active_intents[project] = DomainIntent.from_dict(intent_data)
        except Exception as e:
            log.warning(f"Failed to load intents: {e}")

    def _save_intents(self):
        """Save intents to disk."""
        try:
            INTENTS_FILE.parent.mkdir(parents=True, exist_ok=True)
            data = {
                "intents": {k: v.to_dict() for k, v in self._active_intents.items()},
                "last_updated": datetime.now().isoformat(),
            }
            with open(INTENTS_FILE, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            log.error(f"Failed to save intents: {e}")

    def set_intent(
        self,
        domain: str,
        project_path: str,
        user_focus: List[str] = None,
    ) -> DomainIntent:
        """
        Set learning intent for a domain/project.

        Combines:
        1. Mastery research (what experts say matters)
        2. User focus (what this user cares about)
        """
        # Research what mastery looks like
        mastery = self.researcher.research_domain(domain)

        # Build intents from mastery markers
        intents = []
        for marker in mastery.markers:
            intent = LearningIntent(
                name=marker.name,
                description=marker.description,
                triggers=self._extract_triggers(marker),
                positive_signals=marker.indicators,
                negative_signals=marker.anti_patterns,
                priority=marker.confidence,
                domain=domain,
            )
            intents.append(intent)

        # Build watch/warn lists
        watch_for = list(mastery.success_indicators)
        for marker in mastery.markers:
            watch_for.extend(marker.indicators[:2])  # Top 2 from each

        warn_about = list(mastery.common_mistakes)
        for marker in mastery.markers:
            warn_about.extend(marker.anti_patterns[:2])

        # Create domain intent
        domain_intent = DomainIntent(
            domain=domain,
            project_path=project_path,
            intents=intents,
            watch_for=watch_for[:10],  # Top 10
            warn_about=warn_about[:10],
            user_focus=user_focus or [],
            mastery_focus=mastery.core_principles[:5],
            created_at=datetime.now().isoformat(),
            based_on_mastery=len(mastery.markers) > 0,
        )

        self._active_intents[project_path] = domain_intent
        self._save_intents()

        log.info(f"Set learning intent for {domain}: {len(intents)} intents, {len(watch_for)} watch patterns")
        return domain_intent

    def _extract_triggers(self, marker) -> List[str]:
        """Extract trigger patterns from a mastery marker."""
        triggers = []

        # Extract key words from indicators
        for indicator in marker.indicators:
            words = indicator.lower().split()
            for word in words:
                if len(word) > 4 and word.isalpha():
                    triggers.append(word)

        return _unique_preserve_order(triggers, limit=10)

    def get_intent(self, project_path: str) -> Optional[DomainIntent]:
        """Get active intent for a project."""
        return self._active_intents.get(project_path)

    def check_against_intent(self, content: str, project_path: str) -> Dict[str, Any]:
        """
        Check content against active intent.

        Returns signals about whether content aligns with mastery.
        """
        intent = self.get_intent(project_path)
        if not intent:
            return {"has_intent": False}

        content_lower = content.lower()

        # Check for positive signals
        positive_matches = []
        for pattern in intent.watch_for:
            if pattern.lower() in content_lower:
                positive_matches.append(pattern)

        # Check for negative signals
        negative_matches = []
        for pattern in intent.warn_about:
            if pattern.lower() in content_lower:
                negative_matches.append(pattern)

        # Check against specific intents
        intent_matches = []
        for learning_intent in intent.intents:
            for trigger in learning_intent.triggers:
                if trigger in content_lower:
                    intent_matches.append(learning_intent.name)
                    break

        return {
            "has_intent": True,
            "domain": intent.domain,
            "positive_matches": positive_matches,
            "negative_matches": negative_matches,
            "intent_matches": _unique_preserve_order(intent_matches, limit=50),
            "alignment_score": self._calculate_alignment(positive_matches, negative_matches),
        }

    def _calculate_alignment(self, positive: List[str], negative: List[str]) -> float:
        """Calculate how well content aligns with mastery intent."""
        if not positive and not negative:
            return 0.5  # Neutral

        positive_score = len(positive) * 0.2
        negative_score = len(negative) * 0.3

        return max(0.0, min(1.0, 0.5 + positive_score - negative_score))

    def get_focus_summary(self, project_path: str) -> str:
        """Get a summary of what to focus on for a project."""
        intent = self.get_intent(project_path)
        if not intent:
            return "No learning intent set. Consider running domain research."

        lines = [
            f"## Learning Intent: {intent.domain}",
            "",
            "### Watch For (Mastery Signals)",
        ]
        for item in intent.watch_for[:5]:
            lines.append(f"- {item}")

        lines.extend([
            "",
            "### Warn About (Anti-Patterns)",
        ])
        for item in intent.warn_about[:5]:
            lines.append(f"- {item}")

        if intent.mastery_focus:
            lines.extend([
                "",
                "### Core Principles",
            ])
            for item in intent.mastery_focus:
                lines.append(f"- {item}")

        return "\n".join(lines)

    def add_user_focus(self, project_path: str, focus: str):
        """Add a user-specified focus area."""
        intent = self.get_intent(project_path)
        if intent and focus not in intent.user_focus:
            intent.user_focus.append(focus)
            self._save_intents()


# Singleton setter
_setter: Optional[IntentSetter] = None


def get_setter() -> IntentSetter:
    """Get singleton setter instance."""
    global _setter
    if _setter is None:
        _setter = IntentSetter()
    return _setter


def set_learning_intent(domain: str, project_path: str, user_focus: List[str] = None) -> DomainIntent:
    """Set learning intent (convenience function)."""
    return get_setter().set_intent(domain, project_path, user_focus)
