"""
Learning Utilization Test Suite

Tests that verify stored learnings are actually being used and providing value.

PRINCIPLE: Storing learnings that never get used is as bad as not learning at all.
PRINCIPLE: The full loop is: Learn -> Store -> Retrieve -> Use -> Outcome -> Validate

Usage:
    python tests/test_learning_utilization.py           # Full utilization report
    python tests/test_learning_utilization.py quick     # Quick status
    python tests/test_learning_utilization.py analyze   # Deep analysis
"""

import sys
import json
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Tuple
from dataclasses import dataclass

# Add lib to path
sys.path.insert(0, str(Path(__file__).parent.parent))

SPARK_DIR = Path.home() / '.spark'


@dataclass
class UtilizationMetrics:
    """Metrics for learning utilization."""
    total_stored: int
    total_retrieved: int
    actionable_retrieved: int
    ignored_non_actionable: int
    retrieval_rate: float
    acted_on: int
    acted_on_rate: float
    good_outcomes: int
    bad_outcomes: int
    effectiveness_rate: float
    utilization_grade: str


class LearningUtilizationChecker:
    """
    Verifies the complete learning utilization loop:

    LEARN -> STORE -> RETRIEVE -> USE -> OUTCOME -> VALIDATE
       ^                                              |
       |______________________________________________|
    """

    def __init__(self):
        self.issues: List[str] = []
        self.recommendations: List[str] = []

    def get_stored_learnings_count(self) -> int:
        """Get count of stored cognitive insights."""
        insights_file = SPARK_DIR / 'cognitive_insights.json'
        if not insights_file.exists():
            return 0
        try:
            data = json.loads(insights_file.read_text())
            # cognitive_insights.json stores as key-value pairs
            if isinstance(data, dict):
                return len(data)
            return len(data.get('insights', []))
        except:
            return 0

    def get_outcome_stats(self) -> Dict:
        """Get outcome tracking stats from Meta-Ralph."""
        try:
            from lib.meta_ralph import get_meta_ralph
            return get_meta_ralph().get_outcome_stats()
        except Exception as e:
            return {"error": str(e)}

    def get_advisor_stats(self) -> Dict:
        """Get advisor activity stats."""
        try:
            from lib.advisor import get_advisor
            advisor = get_advisor()
            # Check if advisor has stats method
            if hasattr(advisor, 'get_stats'):
                return advisor.get_stats()
            else:
                # Try to get basic info
                return {
                    "advice_cache_size": len(getattr(advisor, '_advice_cache', {})),
                    "status": "running"
                }
        except Exception as e:
            return {"error": str(e)}

    def calculate_metrics(self) -> UtilizationMetrics:
        """Calculate comprehensive utilization metrics."""
        stored = self.get_stored_learnings_count()
        outcome_stats = self.get_outcome_stats()

        if "error" in outcome_stats:
            # Return empty metrics on error
            return UtilizationMetrics(
                total_stored=stored,
                total_retrieved=0,
                actionable_retrieved=0,
                ignored_non_actionable=0,
                retrieval_rate=0.0,
                acted_on=0,
                acted_on_rate=0.0,
                good_outcomes=0,
                bad_outcomes=0,
                effectiveness_rate=0.0,
                utilization_grade="?"
            )

        retrieved = outcome_stats.get('total_tracked', 0)
        actionable = outcome_stats.get('actionable_tracked', retrieved)
        ignored_non_actionable = outcome_stats.get(
            'ignored_non_actionable',
            max(0, retrieved - actionable),
        )
        acted_on = outcome_stats.get('acted_on', 0)
        good = outcome_stats.get('good_outcomes', 0)
        bad = outcome_stats.get('bad_outcomes', 0)

        # Calculate rates
        retrieval_rate = retrieved / max(stored, 1)
        acted_on_rate = acted_on / max(actionable, 1) if actionable > 0 else 0.0
        effectiveness = outcome_stats.get('effectiveness_rate', 0.0)

        # Calculate grade
        grade = self._calculate_grade(retrieval_rate, acted_on_rate, effectiveness, stored, retrieved)

        return UtilizationMetrics(
            total_stored=stored,
            total_retrieved=retrieved,
            actionable_retrieved=actionable,
            ignored_non_actionable=ignored_non_actionable,
            retrieval_rate=retrieval_rate,
            acted_on=acted_on,
            acted_on_rate=acted_on_rate,
            good_outcomes=good,
            bad_outcomes=bad,
            effectiveness_rate=effectiveness,
            utilization_grade=grade
        )

    def _calculate_grade(self, retrieval_rate: float, acted_on_rate: float,
                         effectiveness: float, stored: int, retrieved: int) -> str:
        """Calculate utilization grade A-F."""
        # If nothing stored, grade is F
        if stored == 0:
            return "F"

        # If nothing retrieved, grade is F
        if retrieved == 0:
            return "F"

        # Cap retrieval rate at 1.0 (100%)
        retrieval_rate = min(retrieval_rate, 1.0)

        # Weight: 30% retrieval, 30% acted-on, 40% effectiveness
        score = (retrieval_rate * 0.3 + acted_on_rate * 0.3 + effectiveness * 0.4)

        if score >= 0.8:
            return "A"
        elif score >= 0.6:
            return "B"
        elif score >= 0.4:
            return "C"
        elif score >= 0.2:
            return "D"
        else:
            return "F"

    def diagnose_issues(self, metrics: UtilizationMetrics) -> List[str]:
        """Diagnose utilization issues and provide recommendations."""
        issues = []
        recommendations = []

        # Issue 1: Low retrieval rate
        if metrics.total_stored > 0 and metrics.retrieval_rate < 0.1:
            issues.append("LOW RETRIEVAL: Less than 10% of stored learnings are being retrieved")
            recommendations.append("Check advisor.py - is it calling get_relevant_learnings()?")
            recommendations.append("Verify advisor is integrated with observe.py PreToolUse")

        # Issue 2: Retrieved but not acted on
        if metrics.total_retrieved > 0 and metrics.acted_on_rate < 0.3:
            issues.append("LOW ACTION RATE: Learnings are retrieved but not acted on")
            recommendations.append("Learnings may not be actionable enough - check scoring")
            recommendations.append("Check if advice is being surfaced to user/agent")

        # Issue 3: Low effectiveness
        if metrics.acted_on > 0 and metrics.effectiveness_rate < 0.5:
            issues.append("LOW EFFECTIVENESS: Acted-on learnings aren't helping")
            recommendations.append("Review quality of stored learnings")
            recommendations.append("Consider demoting low-effectiveness learnings")

        # Issue 4: All zeros
        if metrics.total_retrieved == 0 and metrics.total_stored > 0:
            issues.append("ZERO UTILIZATION: Stored learnings never retrieved")
            recommendations.append("Outcome tracking may be broken - check track_retrieval() calls")
            recommendations.append("Verify observe.py is calling advisor.advise()")

        # Issue 5: No stored learnings
        if metrics.total_stored == 0:
            issues.append("NOTHING STORED: No learnings in storage")
            recommendations.append("Run pipeline health check: python tests/test_pipeline_health.py")
            recommendations.append("Check if Meta-Ralph is storing quality items")

        self.issues = issues
        self.recommendations = recommendations
        return issues

    def print_report(self, metrics: UtilizationMetrics):
        """Print comprehensive utilization report."""
        print("\n" + "=" * 70)
        print(" LEARNING UTILIZATION REPORT")
        print(" Verifying: Learn -> Store -> Retrieve -> Use -> Outcome")
        print("=" * 70)

        # Metrics
        print("\n[UTILIZATION METRICS]")
        print(f"  Total Stored:      {metrics.total_stored}")
        print(f"  Total Retrieved:   {metrics.total_retrieved} ({metrics.retrieval_rate:.1%} of stored)")
        print(
            f"  Actionable Pool:   {metrics.actionable_retrieved} "
            f"(ignored non-actionable: {metrics.ignored_non_actionable})"
        )
        print(f"  Acted On:          {metrics.acted_on} ({metrics.acted_on_rate:.1%} of actionable)")
        print(f"  Good Outcomes:     {metrics.good_outcomes}")
        print(f"  Bad Outcomes:      {metrics.bad_outcomes}")
        print(f"  Effectiveness:     {metrics.effectiveness_rate:.1%}")

        # Grade
        print(f"\n[UTILIZATION GRADE: {metrics.utilization_grade}]")

        grade_desc = {
            "A": "Excellent - Learnings are being used and providing value",
            "B": "Good - Solid utilization with room for improvement",
            "C": "Fair - Moderate utilization, some issues to address",
            "D": "Poor - Low utilization, significant gaps",
            "F": "Failing - Learnings are not being used",
            "?": "Unknown - Could not calculate metrics"
        }
        print(f"  {grade_desc.get(metrics.utilization_grade, 'Unknown')}")

        # Issues
        if self.issues:
            print("\n[ISSUES DETECTED]")
            for issue in self.issues:
                print(f"  - {issue}")

        if self.recommendations:
            print("\n[RECOMMENDATIONS]")
            for rec in self.recommendations:
                print(f"  - {rec}")

        # The Loop visualization (ASCII-safe for Windows)
        print("\n[THE UTILIZATION LOOP]")
        print("""
    LEARN ------> STORE ------> RETRIEVE ------> USE ------> OUTCOME
      ^           ({stored})      ({retrieved})    ({acted})   ({good}/{bad})
      |                                                            |
      +------------------ VALIDATE & IMPROVE ---------------------+
        """.format(
            stored=metrics.total_stored,
            retrieved=metrics.total_retrieved,
            acted=metrics.acted_on,
            good=metrics.good_outcomes,
            bad=metrics.bad_outcomes
        ))

        # Target metrics
        print("[TARGET METRICS]")
        print("  Retrieval Rate:   >10% of stored")
        print("  Acted On Rate:    >50% of retrieved")
        print("  Effectiveness:    >60% of acted on")

        print("\n" + "-" * 70)

    def run_quick_check(self):
        """Run quick status check."""
        print("\n" + "=" * 50)
        print(" QUICK UTILIZATION CHECK")
        print("=" * 50)

        metrics = self.calculate_metrics()

        print(f"\nStored: {metrics.total_stored}")
        print(f"Retrieved: {metrics.total_retrieved} ({metrics.retrieval_rate:.1%})")
        print(
            f"Actionable: {metrics.actionable_retrieved} "
            f"(ignored: {metrics.ignored_non_actionable})"
        )
        print(f"Acted On: {metrics.acted_on} ({metrics.acted_on_rate:.1%})")
        print(f"Effectiveness: {metrics.effectiveness_rate:.1%}")
        print(f"\nGrade: {metrics.utilization_grade}")

        if metrics.utilization_grade in ("F", "D"):
            print("\nWARNING: Low utilization - learnings may not be providing value")

    def run_full_report(self):
        """Run full utilization report."""
        metrics = self.calculate_metrics()
        self.diagnose_issues(metrics)
        self.print_report(metrics)

        return metrics.utilization_grade != "F"

    def run_analysis(self):
        """Run deep analysis of utilization patterns."""
        print("\n" + "=" * 70)
        print(" DEEP UTILIZATION ANALYSIS")
        print("=" * 70)

        # Get all available data
        metrics = self.calculate_metrics()
        advisor_stats = self.get_advisor_stats()

        print("\n[META-RALPH OUTCOME TRACKING]")
        outcome_stats = self.get_outcome_stats()
        if "error" not in outcome_stats:
            for key, value in outcome_stats.items():
                print(f"  {key}: {value}")
        else:
            print(f"  Error: {outcome_stats['error']}")

        print("\n[ADVISOR STATUS]")
        if "error" not in advisor_stats:
            for key, value in advisor_stats.items():
                print(f"  {key}: {value}")
        else:
            print(f"  Error: {advisor_stats['error']}")

        # Check for specific patterns
        print("\n[UTILIZATION PATTERNS]")

        if metrics.total_stored > 0 and metrics.total_retrieved == 0:
            print("  PATTERN: Zero retrievals")
            print("    Cause: track_retrieval() never called")
            print("    Fix: Check advisor.advise() calls ralph.track_retrieval()")

        if metrics.total_retrieved > 0 and metrics.acted_on == 0:
            print("  PATTERN: Retrieved but never acted on")
            print("    Cause: track_outcome() never called with acted_on=True")
            print("    Fix: Check report_outcome() sets acted_on properly")

        if metrics.good_outcomes == 0 and metrics.bad_outcomes == 0 and metrics.acted_on > 0:
            print("  PATTERN: Acted on but no outcomes recorded")
            print("    Cause: track_outcome() not called with outcome value")
            print("    Fix: Check PostToolUse calls report_outcome()")

        # Recommendations summary
        self.diagnose_issues(metrics)
        if self.recommendations:
            print("\n[ACTION ITEMS]")
            for i, rec in enumerate(self.recommendations, 1):
                print(f"  {i}. {rec}")


def main():
    """Main entry point."""
    mode = sys.argv[1] if len(sys.argv) > 1 else "full"

    checker = LearningUtilizationChecker()

    if mode == "quick":
        checker.run_quick_check()
    elif mode == "analyze":
        checker.run_analysis()
    else:
        success = checker.run_full_report()
        sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
