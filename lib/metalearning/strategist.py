"""
Learning Strategist - Adjust learning strategies based on performance.

When learning is declining or stagnating, this adjusts
parameters to improve quality.
"""

import json
import logging
from dataclasses import dataclass, asdict, field
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime

from .evaluator import TrendAnalysis, get_evaluator

log = logging.getLogger("spark.metalearning")

STRATEGY_FILE = Path.home() / ".spark" / "metalearning" / "strategy.json"


@dataclass
class LearningStrategy:
    """Current learning strategy parameters."""
    # Thresholds
    promotion_threshold: float = 0.5
    high_value_threshold: float = 0.5
    outcome_confidence_threshold: float = 0.4

    # Weights for scoring
    cognitive_weight: float = 0.30
    outcome_weight: float = 0.20
    uniqueness_weight: float = 0.15
    actionability_weight: float = 0.15
    transferability_weight: float = 0.10
    domain_weight: float = 0.10

    # Chip settings
    auto_activate_threshold: float = 0.7
    trigger_deprecation_threshold: float = 0.2
    provisional_chip_confidence: float = 0.3

    # Session settings
    max_insights_per_session: int = 100
    outcome_lookback_minutes: int = 30

    def to_dict(self) -> Dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict) -> 'LearningStrategy':
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


@dataclass
class StrategyAdjustment:
    """A recorded strategy adjustment."""
    timestamp: str
    parameter: str
    old_value: float
    new_value: float
    reason: str
    trend_context: str

    def to_dict(self) -> Dict:
        return asdict(self)


class LearningStrategist:
    """Adjust learning strategies based on performance."""

    def __init__(self):
        self.strategy = self._load_strategy()
        self.adjustments: List[StrategyAdjustment] = []
        self._load_adjustments()

    def _load_strategy(self) -> LearningStrategy:
        """Load strategy from disk."""
        if not STRATEGY_FILE.exists():
            return LearningStrategy()

        try:
            with open(STRATEGY_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return LearningStrategy.from_dict(data.get("strategy", {}))
        except Exception as e:
            log.warning(f"Failed to load strategy: {e}")
            return LearningStrategy()

    def _load_adjustments(self):
        """Load adjustment history."""
        if not STRATEGY_FILE.exists():
            return

        try:
            with open(STRATEGY_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                for adj_data in data.get("adjustments", []):
                    self.adjustments.append(StrategyAdjustment(**adj_data))
        except Exception as e:
            log.warning(f"Failed to load adjustments: {e}")

    def _save_state(self):
        """Save strategy and adjustments to disk."""
        try:
            STRATEGY_FILE.parent.mkdir(parents=True, exist_ok=True)
            data = {
                "strategy": self.strategy.to_dict(),
                "adjustments": [a.to_dict() for a in self.adjustments[-50:]],
                "last_updated": datetime.now().isoformat(),
            }
            with open(STRATEGY_FILE, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            log.error(f"Failed to save strategy: {e}")

    def adjust_strategies(self, analysis: Optional[TrendAnalysis] = None) -> List[StrategyAdjustment]:
        """Adjust strategies based on trend analysis."""
        if analysis is None:
            evaluator = get_evaluator()
            analysis = evaluator.analyze_trends()

        adjustments_made = []

        # Adjust promotion threshold
        if analysis.value_trend < -0.2:
            # Getting worse at finding valuable insights - tighten threshold
            adj = self._adjust_parameter(
                "promotion_threshold",
                min(0.7, self.strategy.promotion_threshold + 0.05),
                f"Value trend declining ({analysis.value_trend:.2f})",
                analysis,
            )
            if adj:
                adjustments_made.append(adj)

        elif analysis.value_trend > 0.2 and self.strategy.promotion_threshold > 0.4:
            # Getting better - can relax slightly
            adj = self._adjust_parameter(
                "promotion_threshold",
                max(0.4, self.strategy.promotion_threshold - 0.03),
                f"Value trend improving ({analysis.value_trend:.2f})",
                analysis,
            )
            if adj:
                adjustments_made.append(adj)

        # Adjust outcome linking sensitivity
        if analysis.linkage_trend < -0.2:
            # Missing outcome links - lower threshold
            adj = self._adjust_parameter(
                "outcome_confidence_threshold",
                max(0.3, self.strategy.outcome_confidence_threshold - 0.05),
                f"Linkage trend declining ({analysis.linkage_trend:.2f})",
                analysis,
            )
            if adj:
                adjustments_made.append(adj)

        # Adjust chip activation sensitivity
        if analysis.coverage_trend < -0.2:
            # Missing chip matches - lower activation threshold
            adj = self._adjust_parameter(
                "auto_activate_threshold",
                max(0.5, self.strategy.auto_activate_threshold - 0.05),
                f"Coverage trend declining ({analysis.coverage_trend:.2f})",
                analysis,
            )
            if adj:
                adjustments_made.append(adj)

        # Adjust weights if quality is persistently low
        if analysis.current_avg_quality < 0.4:
            # Increase cognitive weight
            if self.strategy.cognitive_weight < 0.4:
                adj = self._adjust_parameter(
                    "cognitive_weight",
                    min(0.4, self.strategy.cognitive_weight + 0.05),
                    f"Quality too low ({analysis.current_avg_quality:.2f})",
                    analysis,
                )
                if adj:
                    adjustments_made.append(adj)

        self._save_state()
        return adjustments_made

    def _adjust_parameter(
        self,
        param: str,
        new_value: float,
        reason: str,
        analysis: TrendAnalysis,
    ) -> Optional[StrategyAdjustment]:
        """Adjust a single parameter."""
        old_value = getattr(self.strategy, param)

        # Don't adjust if change is too small
        if abs(new_value - old_value) < 0.01:
            return None

        setattr(self.strategy, param, new_value)

        adjustment = StrategyAdjustment(
            timestamp=datetime.now().isoformat(),
            parameter=param,
            old_value=old_value,
            new_value=new_value,
            reason=reason,
            trend_context=f"overall={analysis.overall_trend:.2f}",
        )

        self.adjustments.append(adjustment)
        log.info(f"Adjusted {param}: {old_value:.2f} -> {new_value:.2f} ({reason})")

        return adjustment

    def get_current_strategy(self) -> Dict:
        """Get current strategy as dict."""
        return self.strategy.to_dict()

    def get_adjustment_history(self, limit: int = 20) -> List[Dict]:
        """Get recent adjustment history."""
        return [a.to_dict() for a in self.adjustments[-limit:]]

    def reset_to_defaults(self):
        """Reset strategy to defaults."""
        self.strategy = LearningStrategy()
        self.adjustments.append(StrategyAdjustment(
            timestamp=datetime.now().isoformat(),
            parameter="all",
            old_value=0.0,
            new_value=0.0,
            reason="Manual reset to defaults",
            trend_context="n/a",
        ))
        self._save_state()
        log.info("Strategy reset to defaults")


# Singleton strategist
_strategist: Optional[LearningStrategist] = None


def get_strategist() -> LearningStrategist:
    """Get singleton strategist instance."""
    global _strategist
    if _strategist is None:
        _strategist = LearningStrategist()
    return _strategist


def adjust_strategies(analysis: Optional[TrendAnalysis] = None) -> List[StrategyAdjustment]:
    """Adjust strategies (convenience function)."""
    return get_strategist().adjust_strategies(analysis)
