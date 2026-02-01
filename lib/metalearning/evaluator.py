"""
Learning Evaluator - Evaluate how well we're learning.

Analyzes sessions and trends to determine if our learning
is improving, stagnating, or declining.
"""

import json
import logging
from dataclasses import dataclass, asdict, field
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from statistics import mean, stdev

log = logging.getLogger("spark.metalearning")

METRICS_FILE = Path.home() / ".spark" / "metalearning" / "metrics.json"


@dataclass
class LearningReport:
    """Report on learning effectiveness for a session."""
    session_id: str
    project_path: str
    timestamp: str

    # Core metrics
    total_insights: int = 0
    high_value_count: int = 0
    promoted_count: int = 0
    outcome_linked_count: int = 0

    # Derived metrics
    @property
    def high_value_ratio(self) -> float:
        if self.total_insights == 0:
            return 0.0
        return self.high_value_count / self.total_insights

    @property
    def promotion_ratio(self) -> float:
        if self.total_insights == 0:
            return 0.0
        return self.promoted_count / self.total_insights

    @property
    def outcome_linkage_ratio(self) -> float:
        if self.total_insights == 0:
            return 0.0
        return self.outcome_linked_count / self.total_insights

    # Chip coverage
    chips_activated: List[str] = field(default_factory=list)
    events_matched: int = 0
    events_total: int = 0

    @property
    def chip_coverage(self) -> float:
        if self.events_total == 0:
            return 0.0
        return self.events_matched / self.events_total

    # Domain info
    domain: str = ""
    new_domain_detected: bool = False

    # Quality score
    @property
    def quality_score(self) -> float:
        """Overall quality score for the session."""
        weights = {
            "high_value_ratio": 0.35,
            "outcome_linkage_ratio": 0.25,
            "chip_coverage": 0.25,
            "promotion_ratio": 0.15,
        }
        return sum(
            getattr(self, metric) * weight
            for metric, weight in weights.items()
        )

    def to_dict(self) -> Dict:
        d = asdict(self)
        d["high_value_ratio"] = self.high_value_ratio
        d["promotion_ratio"] = self.promotion_ratio
        d["outcome_linkage_ratio"] = self.outcome_linkage_ratio
        d["chip_coverage"] = self.chip_coverage
        d["quality_score"] = self.quality_score
        return d


@dataclass
class TrendAnalysis:
    """Analysis of learning trends over time."""
    sessions_analyzed: int
    time_range_days: int

    # Trend directions (-1 to 1, negative = declining)
    value_trend: float = 0.0
    coverage_trend: float = 0.0
    linkage_trend: float = 0.0
    overall_trend: float = 0.0

    # Current state
    current_avg_quality: float = 0.0
    best_quality: float = 0.0
    worst_quality: float = 0.0

    # Recommendations
    recommendations: List[str] = field(default_factory=list)
    alerts: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict:
        return asdict(self)


class LearningEvaluator:
    """Evaluate learning effectiveness across sessions."""

    def __init__(self):
        self._reports: List[LearningReport] = []
        self._load_history()

    def _load_history(self):
        """Load historical reports."""
        if not METRICS_FILE.exists():
            return

        try:
            with open(METRICS_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                for report_data in data.get("reports", []):
                    # Handle dataclass fields properly
                    chips = report_data.pop("chips_activated", [])
                    report = LearningReport(**{
                        k: v for k, v in report_data.items()
                        if k in LearningReport.__dataclass_fields__ and k != "chips_activated"
                    })
                    report.chips_activated = chips
                    self._reports.append(report)
        except Exception as e:
            log.warning(f"Failed to load learning history: {e}")

    def _save_history(self):
        """Save reports to disk."""
        try:
            METRICS_FILE.parent.mkdir(parents=True, exist_ok=True)
            data = {
                "reports": [r.to_dict() for r in self._reports[-100:]],  # Keep last 100
                "last_updated": datetime.now().isoformat(),
            }
            with open(METRICS_FILE, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            log.error(f"Failed to save learning history: {e}")

    def evaluate_session(
        self,
        insights: List[Dict],
        events: List[Dict],
        project_path: str,
        domain: str = "",
    ) -> LearningReport:
        """Evaluate a session's learning effectiveness."""
        session_id = f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        # Count high-value insights
        high_value = sum(
            1 for i in insights
            if i.get("score", {}).get("total", 0) >= 0.5
        )

        # Count promoted insights
        promoted = sum(
            1 for i in insights
            if i.get("score", {}).get("promotion_tier") in ["working", "long_term"]
        )

        # Count outcome-linked insights
        outcome_linked = sum(
            1 for i in insights
            if i.get("outcome_score", 0) > 0
        )

        # Get chip info
        chips = list(set(i.get("chip_id", "") for i in insights if i.get("chip_id")))
        events_matched = len(insights)

        report = LearningReport(
            session_id=session_id,
            project_path=project_path,
            timestamp=datetime.now().isoformat(),
            total_insights=len(insights),
            high_value_count=high_value,
            promoted_count=promoted,
            outcome_linked_count=outcome_linked,
            chips_activated=chips,
            events_matched=events_matched,
            events_total=len(events),
            domain=domain,
        )

        self._reports.append(report)
        self._save_history()

        log.info(f"Session quality score: {report.quality_score:.2f}")
        return report

    def analyze_trends(self, days: int = 7) -> TrendAnalysis:
        """Analyze learning trends over recent sessions."""
        cutoff = datetime.now() - timedelta(days=days)

        recent = [
            r for r in self._reports
            if datetime.fromisoformat(r.timestamp) > cutoff
        ]

        if len(recent) < 2:
            return TrendAnalysis(
                sessions_analyzed=len(recent),
                time_range_days=days,
                recommendations=["Need more sessions for trend analysis"],
            )

        # Calculate trends
        qualities = [r.quality_score for r in recent]
        value_ratios = [r.high_value_ratio for r in recent]
        coverages = [r.chip_coverage for r in recent]
        linkages = [r.outcome_linkage_ratio for r in recent]

        analysis = TrendAnalysis(
            sessions_analyzed=len(recent),
            time_range_days=days,
            value_trend=self._calculate_trend(value_ratios),
            coverage_trend=self._calculate_trend(coverages),
            linkage_trend=self._calculate_trend(linkages),
            overall_trend=self._calculate_trend(qualities),
            current_avg_quality=mean(qualities[-5:]) if len(qualities) >= 5 else mean(qualities),
            best_quality=max(qualities),
            worst_quality=min(qualities),
        )

        # Generate recommendations
        analysis.recommendations = self._generate_recommendations(analysis, recent)
        analysis.alerts = self._generate_alerts(analysis, recent)

        return analysis

    def _calculate_trend(self, values: List[float]) -> float:
        """Calculate trend direction (-1 to 1)."""
        if len(values) < 2:
            return 0.0

        # Simple linear regression slope normalized
        n = len(values)
        x_mean = (n - 1) / 2
        y_mean = mean(values)

        numerator = sum((i - x_mean) * (v - y_mean) for i, v in enumerate(values))
        denominator = sum((i - x_mean) ** 2 for i in range(n))

        if denominator == 0:
            return 0.0

        slope = numerator / denominator

        # Normalize to -1 to 1 range
        return max(-1.0, min(1.0, slope * n))

    def _generate_recommendations(self, analysis: TrendAnalysis, reports: List[LearningReport]) -> List[str]:
        """Generate recommendations based on trends."""
        recs = []

        if analysis.value_trend < -0.2:
            recs.append("Value quality declining - consider tightening promotion thresholds")

        if analysis.coverage_trend < -0.2:
            recs.append("Chip coverage declining - review chip triggers for gaps")

        if analysis.linkage_trend < -0.2:
            recs.append("Outcome linkage declining - increase outcome detection sensitivity")

        if analysis.current_avg_quality < 0.4:
            recs.append("Overall quality low - focus on high-value insight detection")

        # Check for missing domains
        domains = [r.domain for r in reports if r.domain]
        if len(set(domains)) < len(reports) * 0.5:
            recs.append("Many sessions without domain context - improve domain detection")

        return recs

    def _generate_alerts(self, analysis: TrendAnalysis, reports: List[LearningReport]) -> List[str]:
        """Generate alerts for critical issues."""
        alerts = []

        if analysis.overall_trend < -0.4:
            alerts.append("ALERT: Significant decline in learning quality")

        recent_quality = mean([r.quality_score for r in reports[-3:]]) if len(reports) >= 3 else 0
        if recent_quality < 0.3:
            alerts.append("ALERT: Recent sessions have very low quality scores")

        if all(r.outcome_linked_count == 0 for r in reports[-5:]) and len(reports) >= 5:
            alerts.append("ALERT: No outcome linking in last 5 sessions")

        return alerts

    def get_session_history(self, limit: int = 20) -> List[Dict]:
        """Get recent session history."""
        return [r.to_dict() for r in self._reports[-limit:]]


# Singleton evaluator
_evaluator: Optional[LearningEvaluator] = None


def get_evaluator() -> LearningEvaluator:
    """Get singleton evaluator instance."""
    global _evaluator
    if _evaluator is None:
        _evaluator = LearningEvaluator()
    return _evaluator


def evaluate_session(insights: List[Dict], events: List[Dict], project_path: str, domain: str = "") -> LearningReport:
    """Evaluate a session (convenience function)."""
    return get_evaluator().evaluate_session(insights, events, project_path, domain)
