"""
Meta-Ralph Test Suite

Tests the quality gate for Spark's self-evolution.
Verifies cognitive vs operational classification and scoring accuracy.

Usage:
    python tests/test_meta_ralph.py
    pytest tests/test_meta_ralph.py -v
"""

import sys
import pytest
from pathlib import Path

# Add lib to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from lib.meta_ralph import MetaRalph, RoastVerdict


@pytest.fixture(autouse=True)
def _isolate_meta_ralph(tmp_path, monkeypatch):
    """Redirect MetaRalph's persistent state to a temp directory so tests
    don't leak across runs or pick up stale roast history from ~/.spark/."""
    data_dir = tmp_path / "meta_ralph"
    monkeypatch.setattr(MetaRalph, "DATA_DIR", data_dir)
    monkeypatch.setattr(MetaRalph, "ROAST_HISTORY_FILE", data_dir / "roast_history.json")
    monkeypatch.setattr(MetaRalph, "OUTCOME_TRACKING_FILE", data_dir / "outcome_tracking.json")
    monkeypatch.setattr(MetaRalph, "LEARNINGS_STORE_FILE", data_dir / "learnings_store.json")
    monkeypatch.setattr(MetaRalph, "SELF_ROAST_FILE", data_dir / "self_roast.json")


def test_primitive_detection():
    """Test that primitive patterns are correctly rejected."""
    ralph = MetaRalph()

    primitives = [
        "Read task succeeded with Read tool",
        "Success rate: 95% over 1000 uses",
        "Pattern using Write.",
        "Bash → Edit sequence detected",
        "For shell tasks, use standard approach",
    ]

    passed = 0
    for text in primitives:
        result = ralph.roast(text, source="test")
        if result.verdict == RoastVerdict.PRIMITIVE:
            passed += 1
        else:
            print(f"FAIL: Expected PRIMITIVE for: {text[:50]}")
            print(f"  Got: {result.verdict.value} (score {result.score.total})")

    print(f"Primitive detection: {passed}/{len(primitives)} correct")
    assert passed == len(primitives), (
        f"expected {len(primitives)} primitive detections, got {passed}"
    )


def test_quality_detection():
    """Test that quality patterns are correctly passed."""
    ralph = MetaRalph()

    quality = [
        "User prefers dark theme because it reduces eye strain during late night sessions",
        "Remember this: always validate input before database operations",
        "I decided to use TypeScript instead of JavaScript for better type safety",
        "For authentication, use OAuth with PKCE because it prevents token interception",
        "The user corrected me - they want PostgreSQL, not MySQL",
    ]

    passed = 0
    for text in quality:
        result = ralph.roast(text, source="test")
        if result.verdict == RoastVerdict.QUALITY:
            passed += 1
        else:
            print(f"FAIL: Expected QUALITY for: {text[:50]}")
            print(f"  Got: {result.verdict.value} (score {result.score.total})")

    print(f"Quality detection: {passed}/{len(quality)} correct")
    assert passed == len(quality), (
        f"expected {len(quality)} quality detections, got {passed}"
    )


def test_scoring_dimensions():
    """Test individual scoring dimensions."""
    ralph = MetaRalph()

    # Test reasoning detection
    result = ralph.roast("Use X because Y", source="test")
    assert result.score.reasoning >= 1, f"Expected reasoning >= 1, got {result.score.reasoning}"

    # Test actionability
    result = ralph.roast("Always validate input", source="test")
    assert result.score.actionability >= 1, f"Expected actionability >= 1, got {result.score.actionability}"

    # Test that priority/remember signals lead to quality verdict
    # (may be refined, so check verdict not raw novelty score)
    result = ralph.roast("Remember this: important project insight", source="test")
    assert result.verdict == RoastVerdict.QUALITY, f"Expected QUALITY for remember signal, got {result.verdict.value}"

    print("Scoring dimensions: PASSED")


def test_duplicate_detection():
    """Test that duplicates are caught."""
    ralph = MetaRalph()

    text = "User prefers dark theme for better focus"
    ralph.roast(text, source="test")
    result2 = ralph.roast(text, source="test")

    assert result2.verdict == RoastVerdict.DUPLICATE, f"Expected DUPLICATE, got {result2.verdict.value}"
    print("Duplicate detection: PASSED")


def test_context_boost():
    """Test that context (importance_score, is_priority) boosts scoring."""
    ralph = MetaRalph()

    # Use text that won't trigger refinement (already has reasoning)
    text = "Consider this approach because it works well"

    # Without priority context
    result1 = ralph.roast(text, source="test", context={})

    # Same text with priority context - should boost novelty
    result2 = ralph.roast(text + " v2", source="test", context={"is_priority": True, "importance_score": 0.9})

    # Priority context should boost novelty score
    assert result2.score.novelty >= result1.score.novelty, "Priority context should boost novelty"
    # Both should pass as quality
    assert result1.verdict == RoastVerdict.QUALITY, "Base text should be quality"
    assert result2.verdict == RoastVerdict.QUALITY, "Priority text should be quality"
    print("Context boost: PASSED")


def test_stats():
    """Test that stats are tracked correctly."""
    ralph = MetaRalph()

    # Roast a few items
    ralph.roast("Primitive: Bash → Edit", source="test")
    ralph.roast("Quality because reasoning here", source="test")

    stats = ralph.get_stats()
    assert stats["total_roasted"] >= 2, f"Expected total_roasted >= 2, got {stats['total_roasted']}"
    assert "pass_rate" in stats, "Missing pass_rate in stats"

    print("Stats tracking: PASSED")


def run_all_tests():
    """Run all tests and report results."""
    print("=" * 60)
    print(" META-RALPH TEST SUITE")
    print("=" * 60)
    print()

    tests = [
        ("Primitive Detection", test_primitive_detection),
        ("Quality Detection", test_quality_detection),
        ("Scoring Dimensions", test_scoring_dimensions),
        ("Duplicate Detection", test_duplicate_detection),
        ("Context Boost", test_context_boost),
        ("Stats Tracking", test_stats),
    ]

    passed = 0
    failed = 0

    for name, test_fn in tests:
        print(f"\n--- {name} ---")
        try:
            test_fn()
            passed += 1
        except AssertionError as e:
            print(f"ASSERTION FAILED: {e}")
            failed += 1
        except Exception as e:
            print(f"ERROR: {e}")
            failed += 1

    print()
    print("=" * 60)
    print(f" RESULTS: {passed} passed, {failed} failed")
    print("=" * 60)

    return failed == 0


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
