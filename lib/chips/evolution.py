"""
Chip Evolution - Enable chips to improve themselves.

Chips learn and evolve based on:
1. Which triggers produce valuable insights
2. Which triggers produce noise (false positives)
3. Patterns that should have matched but didn't
4. Domains that emerge from unmatched patterns
"""

import json
import yaml
import logging
import re
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple, Any
from datetime import datetime
from collections import defaultdict

from .scoring import InsightScore

log = logging.getLogger("spark.chips.evolution")

EVOLUTION_FILE = Path.home() / ".spark" / "chip_evolution.yaml"
PROVISIONAL_CHIPS_DIR = Path.home() / ".spark" / "provisional_chips"


@dataclass
class TriggerStats:
    """Statistics for a trigger."""
    trigger: str
    matches: int = 0
    high_value_matches: int = 0
    low_value_matches: int = 0
    last_match: str = ""

    @property
    def value_ratio(self) -> float:
        """Ratio of high-value to total matches."""
        if self.matches == 0:
            return 0.5
        return self.high_value_matches / self.matches

    @property
    def should_deprecate(self) -> bool:
        """Should this trigger be deprecated?"""
        return self.matches >= 10 and self.value_ratio < 0.2


@dataclass
class ChipEvolutionState:
    """Evolution state for a single chip."""
    chip_id: str
    trigger_stats: Dict[str, TriggerStats] = field(default_factory=dict)
    added_triggers: List[Dict] = field(default_factory=list)
    deprecated_triggers: List[Dict] = field(default_factory=list)
    last_evolved: str = ""

    def to_dict(self) -> Dict:
        return {
            "chip_id": self.chip_id,
            "trigger_stats": {k: asdict(v) for k, v in self.trigger_stats.items()},
            "added_triggers": self.added_triggers,
            "deprecated_triggers": self.deprecated_triggers,
            "last_evolved": self.last_evolved,
        }

    @classmethod
    def from_dict(cls, data: Dict) -> 'ChipEvolutionState':
        trigger_stats = {}
        for k, v in data.get("trigger_stats", {}).items():
            trigger_stats[k] = TriggerStats(**v)
        return cls(
            chip_id=data["chip_id"],
            trigger_stats=trigger_stats,
            added_triggers=data.get("added_triggers", []),
            deprecated_triggers=data.get("deprecated_triggers", []),
            last_evolved=data.get("last_evolved", ""),
        )


@dataclass
class ProvisionalChip:
    """A chip that emerged from patterns, not yet validated."""
    id: str
    name: str
    triggers: List[str]
    source_patterns: List[str]  # The patterns that led to creation
    confidence: float
    insight_count: int
    created_at: str
    validated: bool = False

    def to_dict(self) -> Dict:
        return asdict(self)


class ChipEvolution:
    """Manage chip evolution and improvement."""

    def __init__(self):
        self._state: Dict[str, ChipEvolutionState] = {}
        self._provisional_chips: Dict[str, ProvisionalChip] = {}
        self._unmatched_valuable: List[Dict] = []  # Valuable insights that didn't match any chip
        self._load_state()

    def _load_state(self):
        """Load evolution state from disk."""
        if EVOLUTION_FILE.exists():
            try:
                with open(EVOLUTION_FILE, 'r', encoding='utf-8') as f:
                    data = yaml.safe_load(f) or {}
                    for chip_id, chip_data in data.get("chips", {}).items():
                        self._state[chip_id] = ChipEvolutionState.from_dict(chip_data)
                    for chip_data in data.get("provisional_chips", []):
                        chip = ProvisionalChip(**chip_data)
                        self._provisional_chips[chip.id] = chip
            except Exception as e:
                log.warning(f"Failed to load evolution state: {e}")

    def _save_state(self):
        """Save evolution state to disk."""
        try:
            EVOLUTION_FILE.parent.mkdir(parents=True, exist_ok=True)
            data = {
                "chips": {k: v.to_dict() for k, v in self._state.items()},
                "provisional_chips": [c.to_dict() for c in self._provisional_chips.values()],
                "last_updated": datetime.now().isoformat(),
            }
            with open(EVOLUTION_FILE, 'w', encoding='utf-8') as f:
                yaml.dump(data, f, default_flow_style=False)
        except Exception as e:
            log.error(f"Failed to save evolution state: {e}")

    def record_match(self, chip_id: str, trigger: str, score: InsightScore):
        """Record a trigger match with its quality score."""
        if chip_id not in self._state:
            self._state[chip_id] = ChipEvolutionState(chip_id=chip_id)

        state = self._state[chip_id]

        if trigger not in state.trigger_stats:
            state.trigger_stats[trigger] = TriggerStats(trigger=trigger)

        stats = state.trigger_stats[trigger]
        stats.matches += 1
        stats.last_match = datetime.now().isoformat()

        if score.total >= 0.5:
            stats.high_value_matches += 1
        else:
            stats.low_value_matches += 1

        self._save_state()

    def record_unmatched_valuable(self, insight: Dict, score: InsightScore):
        """Record a valuable insight that didn't match any chip."""
        if score.total >= 0.6:
            self._unmatched_valuable.append({
                "content": insight.get("content", ""),
                "captured_data": insight.get("captured_data", {}),
                "score": score.total,
                "timestamp": datetime.now().isoformat(),
            })
            # Keep only recent unmatched
            if len(self._unmatched_valuable) > 100:
                self._unmatched_valuable = self._unmatched_valuable[-100:]

    def evolve_chip(self, chip_id: str) -> Dict[str, Any]:
        """Run evolution cycle for a chip."""
        if chip_id not in self._state:
            return {"changes": []}

        state = self._state[chip_id]
        changes = []

        # Find triggers to deprecate
        for trigger, stats in state.trigger_stats.items():
            if stats.should_deprecate:
                already_deprecated = any(
                    d["trigger"] == trigger for d in state.deprecated_triggers
                )
                if not already_deprecated:
                    state.deprecated_triggers.append({
                        "trigger": trigger,
                        "deprecated_at": datetime.now().isoformat(),
                        "reason": f"Low value ratio: {stats.value_ratio:.2f}",
                        "matches": stats.matches,
                    })
                    changes.append({
                        "type": "deprecate_trigger",
                        "trigger": trigger,
                        "reason": f"Only {stats.value_ratio:.0%} high-value matches",
                    })

        # Find new triggers from valuable unmatched patterns
        new_triggers = self._find_candidate_triggers(chip_id)
        for trigger_info in new_triggers:
            already_added = any(
                a["trigger"] == trigger_info["trigger"] for a in state.added_triggers
            )
            if not already_added:
                state.added_triggers.append({
                    "trigger": trigger_info["trigger"],
                    "added_at": datetime.now().isoformat(),
                    "source": trigger_info["source"],
                    "provisional": True,
                })
                changes.append({
                    "type": "add_trigger",
                    "trigger": trigger_info["trigger"],
                    "source": trigger_info["source"],
                })

        state.last_evolved = datetime.now().isoformat()
        self._save_state()

        return {"changes": changes}

    def _find_candidate_triggers(self, chip_id: str) -> List[Dict]:
        """Find candidate triggers from unmatched valuable insights."""
        # Domain keywords by chip
        domain_keywords = {
            "game_dev": ["game", "player", "enemy", "level", "spawn", "physics", "collision"],
            "marketing": ["campaign", "audience", "brand", "funnel", "conversion"],
            "vibecoding": ["component", "hook", "state", "api", "deploy"],
            "biz-ops": ["revenue", "cost", "growth", "churn"],
        }

        chip_keywords = domain_keywords.get(chip_id, [])
        if not chip_keywords:
            return []

        candidates = []

        for item in self._unmatched_valuable:
            content = item.get("content", "").lower()

            # Check if this insight seems relevant to this chip
            relevance = sum(1 for kw in chip_keywords if kw in content)
            if relevance < 2:
                continue

            # Extract potential new triggers
            words = re.findall(r'\b[a-z]{4,}\b', content)
            word_counts = defaultdict(int)
            for word in words:
                if word not in chip_keywords:  # New word
                    word_counts[word] += 1

            for word, count in word_counts.items():
                if count >= 2:  # Appears multiple times
                    candidates.append({
                        "trigger": word,
                        "source": "unmatched_valuable",
                        "relevance": relevance,
                    })

        # Dedupe and sort by relevance
        seen = set()
        unique = []
        for c in sorted(candidates, key=lambda x: -x["relevance"]):
            if c["trigger"] not in seen:
                seen.add(c["trigger"])
                unique.append(c)
                if len(unique) >= 3:  # Max 3 new triggers per evolution
                    break

        return unique

    def suggest_new_chip(self) -> Optional[ProvisionalChip]:
        """Analyze unmatched valuable insights to suggest a new chip."""
        if len(self._unmatched_valuable) < 5:
            return None

        # Cluster by common words
        word_docs = defaultdict(list)
        for i, item in enumerate(self._unmatched_valuable):
            content = item.get("content", "").lower()
            words = set(re.findall(r'\b[a-z]{4,}\b', content))
            for word in words:
                word_docs[word].append(i)

        # Find words that appear in multiple insights
        common_words = [
            (word, docs)
            for word, docs in word_docs.items()
            if len(docs) >= 3
        ]

        if not common_words:
            return None

        # Sort by frequency
        common_words.sort(key=lambda x: -len(x[1]))

        # Take top 5 as triggers
        triggers = [word for word, _ in common_words[:5]]

        # Generate provisional chip
        chip_id = f"provisional_{triggers[0]}"

        if chip_id in self._provisional_chips:
            # Update existing
            existing = self._provisional_chips[chip_id]
            existing.insight_count += 1
            existing.confidence = min(1.0, existing.confidence + 0.1)
            return existing

        # Create new provisional chip
        chip = ProvisionalChip(
            id=chip_id,
            name=f"Provisional: {triggers[0].title()}",
            triggers=triggers,
            source_patterns=[item["content"][:100] for item in self._unmatched_valuable[:3]],
            confidence=0.3,
            insight_count=len(self._unmatched_valuable),
            created_at=datetime.now().isoformat(),
        )

        self._provisional_chips[chip_id] = chip
        self._save_state()

        log.info(f"Created provisional chip: {chip_id} with triggers {triggers}")
        return chip

    def get_active_triggers(self, chip_id: str) -> List[str]:
        """Get active (non-deprecated) triggers for a chip."""
        if chip_id not in self._state:
            return []

        state = self._state[chip_id]
        deprecated = {d["trigger"] for d in state.deprecated_triggers}

        # Original + added - deprecated
        triggers = []
        for trigger, stats in state.trigger_stats.items():
            if trigger not in deprecated:
                triggers.append(trigger)

        for added in state.added_triggers:
            if added["trigger"] not in deprecated:
                triggers.append(added["trigger"])

        return list(set(triggers))

    def get_evolution_stats(self, chip_id: str) -> Dict:
        """Get evolution statistics for a chip."""
        if chip_id not in self._state:
            return {"status": "no_data"}

        state = self._state[chip_id]

        high_value_triggers = []
        low_value_triggers = []

        for trigger, stats in state.trigger_stats.items():
            if stats.value_ratio >= 0.7:
                high_value_triggers.append(trigger)
            elif stats.value_ratio < 0.3:
                low_value_triggers.append(trigger)

        return {
            "chip_id": chip_id,
            "triggers_tracked": len(state.trigger_stats),
            "triggers_added": len(state.added_triggers),
            "triggers_deprecated": len(state.deprecated_triggers),
            "high_value_triggers": high_value_triggers,
            "low_value_triggers": low_value_triggers,
            "last_evolved": state.last_evolved,
        }

    def get_provisional_chips(self) -> List[ProvisionalChip]:
        """Get all provisional chips."""
        return list(self._provisional_chips.values())

    def validate_provisional_chip(self, chip_id: str) -> bool:
        """Validate a provisional chip for promotion to full chip."""
        if chip_id not in self._provisional_chips:
            return False

        chip = self._provisional_chips[chip_id]

        # Check validation criteria
        if chip.insight_count >= 10 and chip.confidence >= 0.7:
            chip.validated = True
            self._save_state()
            log.info(f"Validated provisional chip: {chip_id}")
            return True

        return False


# Singleton evolution manager
_evolution: Optional[ChipEvolution] = None


def get_evolution() -> ChipEvolution:
    """Get singleton evolution instance."""
    global _evolution
    if _evolution is None:
        _evolution = ChipEvolution()
    return _evolution
