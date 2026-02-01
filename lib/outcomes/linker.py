"""
Outcome Linker - Link outcomes to insights.

When we detect a success/failure signal, link it back to
recent insights to validate or invalidate them.
"""

import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta

from .signals import Outcome, OutcomeType

log = logging.getLogger("spark.outcomes")

LINKS_FILE = Path.home() / ".spark" / "outcome_links.jsonl"


@dataclass
class OutcomeLink:
    """A link between an outcome and an insight."""
    outcome_id: str
    insight_id: str
    outcome_type: str
    confidence: float
    recency_weight: float  # How recent was the insight?
    context_match: float   # How well does context match?
    timestamp: str

    def to_dict(self) -> Dict:
        return {
            "outcome_id": self.outcome_id,
            "insight_id": self.insight_id,
            "outcome_type": self.outcome_type,
            "confidence": self.confidence,
            "recency_weight": self.recency_weight,
            "context_match": self.context_match,
            "timestamp": self.timestamp,
        }


class OutcomeLinker:
    """Link outcomes to insights for validation."""

    def __init__(self, max_recency_minutes: int = 30):
        self.max_recency_minutes = max_recency_minutes
        self._links: List[OutcomeLink] = []

    def link(self, outcome: Outcome, recent_insights: List[Dict]) -> List[OutcomeLink]:
        """Link an outcome to relevant recent insights."""
        links = []

        for insight in recent_insights:
            # Calculate recency weight
            recency = self._calculate_recency(insight.get("timestamp"))
            if recency <= 0:
                continue

            # Calculate context match
            context_match = self._calculate_context_match(outcome, insight)

            # Create link if relevant
            if recency > 0.2 or context_match > 0.5:
                link = OutcomeLink(
                    outcome_id=f"out_{hash(outcome.content)%100000}",
                    insight_id=insight.get("id") or f"ins_{hash(str(insight))%100000}",
                    outcome_type=outcome.type.value,
                    confidence=outcome.confidence * recency * max(0.5, context_match),
                    recency_weight=recency,
                    context_match=context_match,
                    timestamp=datetime.now().isoformat(),
                )
                links.append(link)
                self._links.append(link)

        # Persist links
        if links:
            self._save_links(links)

        return links

    def _calculate_recency(self, insight_timestamp: Optional[str]) -> float:
        """Calculate recency weight (0-1) based on how recent insight is."""
        if not insight_timestamp:
            return 0.5  # Unknown, assume moderate

        try:
            insight_time = datetime.fromisoformat(insight_timestamp)
            now = datetime.now()
            age_minutes = (now - insight_time).total_seconds() / 60

            if age_minutes > self.max_recency_minutes:
                return 0.0  # Too old
            elif age_minutes < 2:
                return 1.0  # Very recent
            else:
                # Linear decay
                return 1.0 - (age_minutes / self.max_recency_minutes)
        except Exception:
            return 0.5

    def _calculate_context_match(self, outcome: Outcome, insight: Dict) -> float:
        """Calculate how well outcome context matches insight."""
        score = 0.3  # Base

        outcome_content = outcome.content.lower()
        insight_content = str(insight.get("content", "")).lower()
        captured = insight.get("captured_data", {})

        # Check for shared keywords
        outcome_words = set(outcome_content.split())
        insight_words = set(insight_content.split())
        shared = outcome_words & insight_words
        if shared:
            score += min(0.3, len(shared) * 0.05)

        # Check for file path match
        if captured.get("file_path"):
            file_name = Path(captured["file_path"]).name.lower()
            if file_name in outcome_content:
                score += 0.3

        # Check for chip domain match
        chip_id = insight.get("chip_id", "")
        if chip_id:
            domain_keywords = {
                "game_dev": ["game", "player", "health", "level"],
                "marketing": ["campaign", "audience", "brand"],
                "vibecoding": ["component", "hook", "api"],
            }
            for kw in domain_keywords.get(chip_id, []):
                if kw in outcome_content:
                    score += 0.1
                    break

        return min(1.0, score)

    def _save_links(self, links: List[OutcomeLink]):
        """Persist links to disk."""
        try:
            LINKS_FILE.parent.mkdir(parents=True, exist_ok=True)
            with open(LINKS_FILE, 'a', encoding='utf-8') as f:
                for link in links:
                    f.write(json.dumps(link.to_dict()) + '\n')
        except Exception as e:
            log.error(f"Failed to save outcome links: {e}")

    def get_validation_score(self, insight_id: str) -> float:
        """Get cumulative validation score for an insight."""
        positive = 0.0
        negative = 0.0

        for link in self._links:
            if link.insight_id == insight_id:
                if link.outcome_type == "success":
                    positive += link.confidence
                elif link.outcome_type == "failure":
                    negative += link.confidence

        # Net validation score
        if positive + negative == 0:
            return 0.0
        return (positive - negative) / (positive + negative)

    def get_insight_outcomes(self, insight_id: str) -> List[OutcomeLink]:
        """Get all outcomes linked to an insight."""
        return [l for l in self._links if l.insight_id == insight_id]

    def load_links(self):
        """Load links from disk."""
        if not LINKS_FILE.exists():
            return

        try:
            with open(LINKS_FILE, 'r', encoding='utf-8') as f:
                for line in f:
                    if line.strip():
                        data = json.loads(line)
                        self._links.append(OutcomeLink(**data))
        except Exception as e:
            log.warning(f"Failed to load outcome links: {e}")


# Singleton linker
_linker: Optional[OutcomeLinker] = None


def get_linker() -> OutcomeLinker:
    """Get singleton linker instance."""
    global _linker
    if _linker is None:
        _linker = OutcomeLinker()
        _linker.load_links()
    return _linker


def link_outcomes(outcome: Outcome, insights: List[Dict]) -> List[OutcomeLink]:
    """Link outcome to insights (convenience function)."""
    return get_linker().link(outcome, insights)
