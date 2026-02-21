"""
Project 2: Cold Start Learning Test

Tests whether explicit learning signals in code are captured by Spark.

Learning Markers Tested:
- REMEMBER: Critical information to retain
- DECISION: Explicit choice made
- PREFERENCE: User preference stated
- CORRECTION: Error correction
- BECAUSE: Reasoned statement
"""

import json
import time
from pathlib import Path
import pytest

# Baseline before test
BASELINE_FILE = Path.home() / '.spark' / 'iteration_baseline.json'
COGNITIVE_FILE = Path.home() / '.spark' / 'cognitive_insights.json'
BRIDGE_HEARTBEAT_FILE = Path.home() / '.spark' / 'bridge_worker_heartbeat.json'
pytestmark = pytest.mark.integration


def get_insight_count():
    """Get current cognitive insight count."""
    if COGNITIVE_FILE.exists():
        data = json.loads(COGNITIVE_FILE.read_text())
        return len(data)
    return 0


def get_insights_containing(text: str) -> list:
    """Find insights containing specific text."""
    if not COGNITIVE_FILE.exists():
        return []

    data = json.loads(COGNITIVE_FILE.read_text())
    matches = []
    for key, val in data.items():
        if isinstance(val, dict):
            insight = val.get('insight', '')
            if text.lower() in insight.lower():
                matches.append({'key': key, 'insight': insight[:100]})
    return matches


def _bridge_worker_recent(max_age_seconds: int = 180) -> bool:
    if not BRIDGE_HEARTBEAT_FILE.exists():
        return False
    try:
        data = json.loads(BRIDGE_HEARTBEAT_FILE.read_text(encoding="utf-8"))
        ts = float(data.get("ts") or 0.0)
        if ts <= 0.0:
            return False
        return (time.time() - ts) <= max_age_seconds
    except Exception:
        return False


def test_explicit_signals():
    """Test that explicit learning signals are captured."""
    if not _bridge_worker_recent():
        pytest.skip("bridge worker heartbeat missing/stale; integration prerequisite not met")
    if not COGNITIVE_FILE.exists():
        pytest.skip("cognitive_insights store missing; integration prerequisite not met")

    print("=" * 60)
    print("PROJECT 2: COLD START LEARNING TEST")
    print("=" * 60)

    before = get_insight_count()
    print(f"\nBaseline insights: {before}")

    # These are the explicit signals we want Spark to capture
    # They should be detected when this file is written/edited

    # REMEMBER: Health = 300 is the sweet spot for 3-4 hit kills
    # DECISION: Using SQLite over PostgreSQL because simplicity beats features here
    # PREFERENCE: I prefer snake_case for Python, camelCase for JS
    # CORRECTION: Not X, but Y - the original assumption was wrong
    # BECAUSE: We use retry logic because network calls are unreliable

    print("\nExplicit signals embedded in this file:")
    print("  - REMEMBER: Health = 300 for 3-4 hit kills")
    print("  - DECISION: SQLite over PostgreSQL for simplicity")
    print("  - PREFERENCE: snake_case for Python")
    print("  - CORRECTION: Y, not X")
    print("  - BECAUSE: Retry logic for unreliable network")

    print("\nSearching for captured signals...")

    # Search for our signals
    signals = [
        ("health", "REMEMBER"),
        ("sqlite", "DECISION"),
        ("snake_case", "PREFERENCE"),
        ("retry", "BECAUSE"),
    ]

    found = 0
    for term, signal_type in signals:
        matches = get_insights_containing(term)
        if matches:
            print(f"  [{signal_type}] Found {len(matches)} match(es) for '{term}'")
            for m in matches[:2]:
                print(f"    - {m['insight'][:60]}...")
            found += 1
        else:
            print(f"  [{signal_type}] No matches for '{term}'")

    after = get_insight_count()
    delta = after - before

    print(f"\n{'=' * 60}")
    print("RESULTS")
    print(f"{'=' * 60}")
    print(f"  Insights before: {before}")
    print(f"  Insights after:  {after}")
    print(f"  Delta:           {delta}")
    print(f"  Signals found:   {found}/4")
    print(f"\n  Status: {'PASS' if found >= 2 else 'NEEDS IMPROVEMENT'}")
    assert found >= 2, f"expected at least 2 captured signals, found {found}"


if __name__ == "__main__":
    test_explicit_signals()
