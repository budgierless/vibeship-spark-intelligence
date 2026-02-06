"""
Cognitive Capture Test Suite

Tests the quality of data being captured by Spark's learning pipeline.
Run before and after tuning to measure improvement.

Usage:
    python tests/test_cognitive_capture.py baseline  # Save baseline
    python tests/test_cognitive_capture.py compare   # Compare to baseline
    python tests/test_cognitive_capture.py analyze   # Just analyze current
    python tests/test_cognitive_capture.py test      # Test filter accuracy
    python tests/test_cognitive_capture.py deep      # Run deep analysis
"""

import sys
import json
from pathlib import Path
from datetime import datetime
from dataclasses import dataclass, asdict
from typing import Dict, Optional
import pytest

# Add lib to path
sys.path.insert(0, str(Path(__file__).parent.parent))
pytestmark = pytest.mark.integration

from lib.meta_ralph import MetaRalph, get_meta_ralph


@pytest.fixture(autouse=True)
def _isolate_meta_ralph(tmp_path, monkeypatch):
    """Keep tests hermetic and avoid writing to shared ~/.spark state."""
    data_dir = tmp_path / "meta_ralph"
    monkeypatch.setattr(MetaRalph, "DATA_DIR", data_dir)
    monkeypatch.setattr(MetaRalph, "ROAST_HISTORY_FILE", data_dir / "roast_history.json")
    monkeypatch.setattr(MetaRalph, "OUTCOME_TRACKING_FILE", data_dir / "outcome_tracking.json")
    monkeypatch.setattr(MetaRalph, "LEARNINGS_STORE_FILE", data_dir / "learnings_store.json")
    monkeypatch.setattr(MetaRalph, "SELF_ROAST_FILE", data_dir / "self_roast.json")
    import lib.meta_ralph as meta_ralph_module
    monkeypatch.setattr(meta_ralph_module, "_meta_ralph", None)


@dataclass
class CaptureQualityMetrics:
    """Metrics for measuring capture quality."""
    timestamp: str

    # Quality metrics (from Meta-Ralph)
    total_roasted: int
    quality_passed: int
    needs_work: int
    primitive: int
    pass_rate: float

    # Score distribution
    score_distribution: Dict[int, int]
    avg_score: float

    # Content analysis
    has_reasoning: int
    has_preference: int
    has_decision: int
    has_correction: int

    # Cognitive density
    cognitive_density: float

    # Skill coverage
    skill_domains: Dict[str, int]


def analyze_roast_history() -> Dict:
    """Analyze the roast history for cognitive patterns."""
    roast_file = Path.home() / '.spark' / 'meta_ralph' / 'roast_history.json'

    if not roast_file.exists():
        return {"error": "No roast history found"}

    data = json.loads(roast_file.read_text())
    history = data.get('history', [])

    if not history:
        return {"error": "Empty roast history"}

    # Score distribution
    scores = {}
    has_reasoning = 0
    has_preference = 0
    has_decision = 0
    has_correction = 0

    # Skill domains
    skill_domains = {
        "product": 0, "debugging": 0, "ui_ux": 0, "orchestration": 0,
        "architecture": 0, "agent_coordination": 0, "team_management": 0,
        "game_dev": 0, "fintech": 0
    }

    skill_keywords = {
        "product": ["user", "feature", "roadmap", "priority"],
        "debugging": ["error", "trace", "root cause", "debug"],
        "ui_ux": ["layout", "component", "responsive", "design"],
        "orchestration": ["workflow", "pipeline", "sequence", "parallel"],
        "architecture": ["pattern", "tradeoff", "scalability", "interface"],
        "agent_coordination": ["agent", "handoff", "routing", "capability"],
        "team_management": ["delegation", "blocker", "review", "sprint"],
        "game_dev": ["balance", "feel", "gameplay", "physics"],
        "fintech": ["compliance", "security", "transaction", "risk"],
    }

    for roast in history:
        result = roast.get('result', {})
        score = result.get('score', {}).get('total', 0)
        verdict = result.get('verdict', '')
        scores[score] = scores.get(score, 0) + 1

        original = result.get('original', '').lower()

        # Cognitive signals
        if 'because' in original:
            has_reasoning += 1
        if any(w in original for w in ['prefer', 'like', 'want', 'love']):
            has_preference += 1
        if any(w in original for w in ['decided', 'chose', 'choosing', 'went with', 'switched to']):
            has_decision += 1
        if any(w in original for w in ['instead', 'actually', 'not ', "don't", 'wrong']):
            has_correction += 1

        # Skill domains (only count quality items)
        if verdict == 'quality':
            for domain, keywords in skill_keywords.items():
                if any(kw in original for kw in keywords):
                    skill_domains[domain] += 1

    total = len(history)
    quality = sum(1 for r in history if r.get('result', {}).get('verdict') == 'quality')
    needs_work = sum(1 for r in history if r.get('result', {}).get('verdict') == 'needs_work')
    primitive = sum(1 for r in history if r.get('result', {}).get('verdict') == 'primitive')

    avg_score = sum(k * v for k, v in scores.items()) / total if total > 0 else 0

    return {
        "total": total,
        "quality": quality,
        "needs_work": needs_work,
        "primitive": primitive,
        "pass_rate": quality / total if total > 0 else 0,
        "scores": scores,
        "avg_score": avg_score,
        "has_reasoning": has_reasoning,
        "has_preference": has_preference,
        "has_decision": has_decision,
        "has_correction": has_correction,
        "cognitive_density": (has_reasoning + has_preference + has_decision) / total if total > 0 else 0,
        "skill_domains": skill_domains
    }


def get_metrics() -> CaptureQualityMetrics:
    """Get current capture quality metrics."""
    analysis = analyze_roast_history()

    return CaptureQualityMetrics(
        timestamp=datetime.now().isoformat(),
        total_roasted=analysis.get("total", 0),
        quality_passed=analysis.get("quality", 0),
        needs_work=analysis.get("needs_work", 0),
        primitive=analysis.get("primitive", 0),
        pass_rate=analysis.get("pass_rate", 0),
        score_distribution=analysis.get("scores", {}),
        avg_score=analysis.get("avg_score", 0),
        has_reasoning=analysis.get("has_reasoning", 0),
        has_preference=analysis.get("has_preference", 0),
        has_decision=analysis.get("has_decision", 0),
        has_correction=analysis.get("has_correction", 0),
        cognitive_density=analysis.get("cognitive_density", 0),
        skill_domains=analysis.get("skill_domains", {})
    )


def print_metrics(metrics: CaptureQualityMetrics, label: str = "Current"):
    """Print metrics in a readable format."""
    print(f"\n{'='*60}")
    print(f" {label} CAPTURE QUALITY METRICS")
    print(f" {metrics.timestamp}")
    print(f"{'='*60}\n")

    print("META-RALPH FILTERING:")
    print(f"  Total roasted: {metrics.total_roasted}")
    print(f"  Quality passed: {metrics.quality_passed} ({metrics.pass_rate:.1%})")
    print(f"  Needs work: {metrics.needs_work}")
    print(f"  Primitive: {metrics.primitive}")
    print(f"  Avg score: {metrics.avg_score:.1f}/10")
    print()

    print("SCORE DISTRIBUTION:")
    for score in sorted(metrics.score_distribution.keys(), reverse=True):
        count = metrics.score_distribution[score]
        bar = "#" * min(count, 30)
        print(f"  Score {score}: {bar} ({count})")
    print()

    print("COGNITIVE SIGNALS:")
    print(f"  Has reasoning ('because'): {metrics.has_reasoning}")
    print(f"  Has preference ('prefer'): {metrics.has_preference}")
    print(f"  Has decision ('decided'): {metrics.has_decision}")
    print(f"  Has correction ('instead'): {metrics.has_correction}")
    print(f"  Cognitive density: {metrics.cognitive_density:.1%}")
    print()

    print("SKILL DOMAIN COVERAGE:")
    for domain, count in sorted(metrics.skill_domains.items(), key=lambda x: -x[1]):
        if count > 0:
            bar = "#" * min(count, 20)
            print(f"  {domain:20} {bar} ({count})")
    print()

    # Quality grade
    grade = "F"
    if metrics.cognitive_density > 0.5:
        grade = "A"
    elif metrics.cognitive_density > 0.3:
        grade = "B"
    elif metrics.cognitive_density > 0.15:
        grade = "C"
    elif metrics.cognitive_density > 0.05:
        grade = "D"

    print(f"OVERALL GRADE: {grade}")
    print(f"  (Based on cognitive density: {metrics.cognitive_density:.1%})")


def save_baseline(metrics: CaptureQualityMetrics):
    """Save metrics as baseline for comparison."""
    baseline_file = Path.home() / '.spark' / 'capture_baseline.json'
    baseline_file.parent.mkdir(parents=True, exist_ok=True)
    baseline_file.write_text(json.dumps(asdict(metrics), indent=2))
    print(f"\nBaseline saved to: {baseline_file}")


def load_baseline() -> Optional[CaptureQualityMetrics]:
    """Load baseline metrics."""
    baseline_file = Path.home() / '.spark' / 'capture_baseline.json'
    if not baseline_file.exists():
        return None
    data = json.loads(baseline_file.read_text())
    return CaptureQualityMetrics(**data)


def compare_to_baseline(current: CaptureQualityMetrics, baseline: CaptureQualityMetrics):
    """Compare current metrics to baseline."""
    print(f"\n{'='*60}")
    print(" COMPARISON: BASELINE vs CURRENT")
    print(f"{'='*60}\n")

    def delta(curr, base, higher_is_better=True):
        diff = curr - base
        pct = (diff / base * 100) if base != 0 else 0
        arrow = "+" if diff > 0 else ""
        status = "BETTER" if (diff > 0) == higher_is_better else "WORSE"
        return f"{arrow}{diff:.2f} ({arrow}{pct:.1f}%) [{status}]"

    print(f"{'Metric':<25} {'Baseline':>12} {'Current':>12} {'Change':>25}")
    print("-" * 75)

    print(f"{'Pass rate':<25} {baseline.pass_rate:>11.1%} {current.pass_rate:>11.1%} {delta(current.pass_rate, baseline.pass_rate):>25}")
    print(f"{'Avg score':<25} {baseline.avg_score:>11.1f} {current.avg_score:>11.1f} {delta(current.avg_score, baseline.avg_score):>25}")
    print(f"{'Cognitive density':<25} {baseline.cognitive_density:>11.1%} {current.cognitive_density:>11.1%} {delta(current.cognitive_density, baseline.cognitive_density):>25}")
    print(f"{'Has reasoning':<25} {baseline.has_reasoning:>12} {current.has_reasoning:>12} {delta(current.has_reasoning, baseline.has_reasoning):>25}")
    print(f"{'Has preference':<25} {baseline.has_preference:>12} {current.has_preference:>12} {delta(current.has_preference, baseline.has_preference):>25}")


def test_filter_accuracy():
    """Test the filter accuracy with sample data."""
    print("\n" + "="*60)
    print(" TESTING FILTER ACCURACY")
    print("="*60 + "\n")

    ralph = MetaRalph()

    # Sample cognitive inputs (should pass)
    cognitive_samples = [
        "User prefers dark theme because it reduces eye strain during late night sessions",
        "Remember this: always validate input before database operations",
        "I decided to use TypeScript instead of JavaScript for better type safety",
        "The user corrected me - they want PostgreSQL, not MySQL",
        "For authentication, use OAuth with PKCE because it prevents token interception",
    ]

    # Sample operational inputs (should fail)
    operational_samples = [
        "Read task succeeded with Read tool",
        "Success rate: 95% over 1000 uses",
        "For shell tasks, use standard approach",
        "Pattern found: Edit follows Read",
        "File modified: config.json",
    ]

    print("COGNITIVE SAMPLES (should pass):")
    cognitive_passed = 0
    for sample in cognitive_samples:
        result = ralph.roast(sample, source="test")
        passed = "PASS" if result.verdict.value == "quality" else "FAIL"
        if result.verdict.value == "quality":
            cognitive_passed += 1
        print(f"  [{passed}] (score {result.score.total}) {sample[:50]}...")

    print(f"\n  Result: {cognitive_passed}/{len(cognitive_samples)} passed\n")

    print("OPERATIONAL SAMPLES (should fail):")
    operational_passed = 0
    for sample in operational_samples:
        result = ralph.roast(sample, source="test")
        passed = "PASS" if result.verdict.value == "quality" else "FAIL"
        if result.verdict.value == "quality":
            operational_passed += 1
        print(f"  [{passed}] (score {result.score.total}) {sample[:50]}...")

    print(f"\n  Result: {operational_passed}/{len(operational_samples)} passed (want 0)\n")

    # Calculate accuracy
    correct = cognitive_passed + (len(operational_samples) - operational_passed)
    total = len(cognitive_samples) + len(operational_samples)
    accuracy = correct / total

    print(f"FILTER ACCURACY: {accuracy:.1%}")
    print(f"  Correctly passed cognitive: {cognitive_passed}/{len(cognitive_samples)}")
    print(f"  Correctly blocked operational: {len(operational_samples) - operational_passed}/{len(operational_samples)}")
    assert 0.0 <= accuracy <= 1.0, f"accuracy out of bounds: {accuracy}"
    assert accuracy >= 0.6, f"filter accuracy too low: {accuracy:.1%}"


def run_deep_analysis():
    """Run and print deep analysis."""
    ralph = get_meta_ralph()
    print(ralph.print_deep_analysis())


def main():
    if len(sys.argv) < 2:
        mode = "analyze"
    else:
        mode = sys.argv[1]

    if mode == "baseline":
        metrics = get_metrics()
        print_metrics(metrics, "BASELINE")
        save_baseline(metrics)

    elif mode == "compare":
        baseline = load_baseline()
        if baseline is None:
            print("No baseline found. Run with 'baseline' first.")
            return
        current = get_metrics()
        print_metrics(baseline, "BASELINE")
        print_metrics(current, "CURRENT")
        compare_to_baseline(current, baseline)

    elif mode == "analyze":
        metrics = get_metrics()
        print_metrics(metrics, "CURRENT")

    elif mode == "test":
        test_filter_accuracy()

    elif mode == "deep":
        run_deep_analysis()

    else:
        print(f"Unknown mode: {mode}")
        print("Usage: python test_cognitive_capture.py [baseline|compare|analyze|test|deep]")


if __name__ == "__main__":
    main()
