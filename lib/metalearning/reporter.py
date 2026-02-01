"""
Meta-Learning Reporter - Generate reports on learning progress.

Creates human-readable reports on how well the system
is learning and evolving.
"""

import logging
from dataclasses import dataclass
from typing import Dict, List, Optional, Any
from datetime import datetime

from .evaluator import get_evaluator, TrendAnalysis
from .strategist import get_strategist

log = logging.getLogger("spark.metalearning")


@dataclass
class MetaLearningReport:
    """Complete meta-learning report."""
    generated_at: str

    # Session metrics
    sessions_analyzed: int
    total_insights: int
    avg_quality_score: float

    # Trends
    overall_trend: str  # "improving", "stable", "declining"
    value_trend: str
    coverage_trend: str

    # Strategy state
    current_strategy: Dict[str, float]
    recent_adjustments: List[Dict]

    # Recommendations
    recommendations: List[str]
    alerts: List[str]

    # Chip evolution
    chips_evolved: List[str]
    provisional_chips: List[str]

    def to_dict(self) -> Dict:
        return {
            "generated_at": self.generated_at,
            "sessions_analyzed": self.sessions_analyzed,
            "total_insights": self.total_insights,
            "avg_quality_score": self.avg_quality_score,
            "overall_trend": self.overall_trend,
            "value_trend": self.value_trend,
            "coverage_trend": self.coverage_trend,
            "current_strategy": self.current_strategy,
            "recent_adjustments": self.recent_adjustments,
            "recommendations": self.recommendations,
            "alerts": self.alerts,
            "chips_evolved": self.chips_evolved,
            "provisional_chips": self.provisional_chips,
        }

    def to_markdown(self) -> str:
        """Generate markdown report."""
        lines = [
            "# Meta-Learning Report",
            "",
            f"*Generated: {self.generated_at}*",
            "",
            "## Overview",
            "",
            f"| Metric | Value |",
            f"|--------|-------|",
            f"| Sessions Analyzed | {self.sessions_analyzed} |",
            f"| Total Insights | {self.total_insights} |",
            f"| Avg Quality Score | {self.avg_quality_score:.2f} |",
            "",
            "## Trends",
            "",
            f"| Dimension | Trend |",
            f"|-----------|-------|",
            f"| Overall | {self._trend_emoji(self.overall_trend)} {self.overall_trend} |",
            f"| Value Quality | {self._trend_emoji(self.value_trend)} {self.value_trend} |",
            f"| Chip Coverage | {self._trend_emoji(self.coverage_trend)} {self.coverage_trend} |",
            "",
        ]

        if self.alerts:
            lines.extend([
                "## Alerts",
                "",
            ])
            for alert in self.alerts:
                lines.append(f"- {alert}")
            lines.append("")

        if self.recommendations:
            lines.extend([
                "## Recommendations",
                "",
            ])
            for rec in self.recommendations:
                lines.append(f"- {rec}")
            lines.append("")

        if self.recent_adjustments:
            lines.extend([
                "## Recent Strategy Adjustments",
                "",
                "| Parameter | Change | Reason |",
                "|-----------|--------|--------|",
            ])
            for adj in self.recent_adjustments[:5]:
                lines.append(
                    f"| {adj['parameter']} | {adj['old_value']:.2f} → {adj['new_value']:.2f} | {adj['reason']} |"
                )
            lines.append("")

        if self.chips_evolved:
            lines.extend([
                "## Chip Evolution",
                "",
                f"Evolved chips: {', '.join(self.chips_evolved)}",
                "",
            ])

        if self.provisional_chips:
            lines.extend([
                "## Provisional Chips (Emerging Domains)",
                "",
                f"Detected: {', '.join(self.provisional_chips)}",
                "",
            ])

        return "\n".join(lines)

    def _trend_emoji(self, trend: str) -> str:
        """Get emoji for trend."""
        if trend == "improving":
            return "+"
        elif trend == "declining":
            return "-"
        else:
            return "="


class MetaLearningReporter:
    """Generate meta-learning reports."""

    def __init__(self):
        self.evaluator = get_evaluator()
        self.strategist = get_strategist()

    def generate_report(self, days: int = 7) -> MetaLearningReport:
        """Generate a comprehensive report."""
        # Get trend analysis
        analysis = self.evaluator.analyze_trends(days)

        # Get session history
        history = self.evaluator.get_session_history(50)

        # Calculate totals
        total_insights = sum(s.get("total_insights", 0) for s in history)
        avg_quality = 0.0
        if history:
            qualities = [s.get("quality_score", 0) for s in history]
            avg_quality = sum(qualities) / len(qualities)

        # Get strategy info
        strategy = self.strategist.get_current_strategy()
        adjustments = self.strategist.get_adjustment_history(10)

        # Get chip evolution info
        chips_evolved = []
        provisional_chips = []
        try:
            from ..chips.evolution import get_evolution
            evolution = get_evolution()
            for chip_id, state in evolution._state.items():
                if state.added_triggers or state.deprecated_triggers:
                    chips_evolved.append(chip_id)
            provisional_chips = [c.id for c in evolution.get_provisional_chips()]
        except Exception:
            pass  # Chip evolution not available

        return MetaLearningReport(
            generated_at=datetime.now().isoformat(),
            sessions_analyzed=analysis.sessions_analyzed,
            total_insights=total_insights,
            avg_quality_score=avg_quality,
            overall_trend=self._trend_label(analysis.overall_trend),
            value_trend=self._trend_label(analysis.value_trend),
            coverage_trend=self._trend_label(analysis.coverage_trend),
            current_strategy=strategy,
            recent_adjustments=adjustments,
            recommendations=analysis.recommendations,
            alerts=analysis.alerts,
            chips_evolved=chips_evolved,
            provisional_chips=provisional_chips,
        )

    def _trend_label(self, value: float) -> str:
        """Convert numeric trend to label."""
        if value > 0.15:
            return "improving"
        elif value < -0.15:
            return "declining"
        else:
            return "stable"


# Singleton reporter
_reporter: Optional[MetaLearningReporter] = None


def get_reporter() -> MetaLearningReporter:
    """Get singleton reporter instance."""
    global _reporter
    if _reporter is None:
        _reporter = MetaLearningReporter()
    return _reporter


def generate_report(days: int = 7) -> MetaLearningReport:
    """Generate report (convenience function)."""
    return get_reporter().generate_report(days)
