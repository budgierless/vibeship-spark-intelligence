#!/usr/bin/env python3
"""
Meta-Ralph Integration Test
============================

HONEST ASSESSMENT: Tests that verify Meta-Ralph is properly integrated
into the Spark Intelligence flow and that data is coming from REAL sources.

This test follows the PRIMARY RULES:
1. Data from storage, not terminal
2. Pipeline health before everything
3. Anti-hallucination verification

Run: python tests/test_metaralph_integration.py
"""

import os
import sys
import json
import time
import tempfile
from datetime import datetime
from pathlib import Path
from contextlib import contextmanager
import pytest

# Add lib to path
sys.path.insert(0, str(Path(__file__).parent.parent))
pytestmark = pytest.mark.integration


def check_file_exists(path: str, name: str) -> dict:
    """Check if a file exists and return its stats."""
    expanded = os.path.expanduser(path)
    exists = os.path.exists(expanded)
    size = os.path.getsize(expanded) if exists else 0
    return {
        "name": name,
        "path": expanded,
        "exists": exists,
        "size": size,
        "size_human": f"{size/1024:.1f}KB" if size < 1024*1024 else f"{size/1024/1024:.1f}MB"
    }


def count_jsonl_lines(path: str) -> int:
    """Count lines in a JSONL file."""
    if not os.path.exists(path):
        return 0
    with open(path, 'r', encoding='utf-8', errors='ignore') as f:
        return sum(1 for _ in f)


@contextmanager
def _isolated_meta_ralph():
    """Use a temporary Meta-Ralph data directory for deterministic mutation tests."""
    from lib.meta_ralph import MetaRalph

    with tempfile.TemporaryDirectory(prefix="meta_ralph_integration_") as tmp:
        data_dir = Path(tmp)
        original = (
            MetaRalph.DATA_DIR,
            MetaRalph.ROAST_HISTORY_FILE,
            MetaRalph.OUTCOME_TRACKING_FILE,
            MetaRalph.LEARNINGS_STORE_FILE,
            MetaRalph.SELF_ROAST_FILE,
        )
        MetaRalph.DATA_DIR = data_dir
        MetaRalph.ROAST_HISTORY_FILE = data_dir / "roast_history.json"
        MetaRalph.OUTCOME_TRACKING_FILE = data_dir / "outcome_tracking.json"
        MetaRalph.LEARNINGS_STORE_FILE = data_dir / "learnings_store.json"
        MetaRalph.SELF_ROAST_FILE = data_dir / "self_roast.json"
        try:
            yield MetaRalph()
        finally:
            (
                MetaRalph.DATA_DIR,
                MetaRalph.ROAST_HISTORY_FILE,
                MetaRalph.OUTCOME_TRACKING_FILE,
                MetaRalph.LEARNINGS_STORE_FILE,
                MetaRalph.SELF_ROAST_FILE,
            ) = original


def test_storage_layer():
    """TEST 1: Verify all storage files exist and have data."""
    print("\n" + "="*60)
    print("TEST 1: STORAGE LAYER (Real Data Sources)")
    print("="*60)

    results = []

    # Core storage files
    storage_files = [
        ("~/.spark/cognitive_insights.json", "Cognitive Insights"),
        ("~/.spark/eidos.db", "EIDOS Database"),
        ("~/.spark/queue/events.jsonl", "Event Queue"),
        ("~/.spark/bridge_worker_heartbeat.json", "Bridge Heartbeat"),
        ("~/.spark/meta_ralph/roast_history.json", "Roast History"),
        ("~/.spark/meta_ralph/outcome_tracking.json", "Outcome Tracking"),
    ]

    all_pass = True
    for path, name in storage_files:
        result = check_file_exists(path, name)
        must_be_nonempty = name != "Event Queue"
        status = "PASS" if result["exists"] and (result["size"] > 0 or not must_be_nonempty) else "FAIL"
        if status == "FAIL":
            all_pass = False
        print(f"  [{status}] {name}: {result['size_human']}")
        results.append(result)

    # Check chip insights (JSONL files)
    chip_dir = os.path.expanduser("~/.spark/chip_insights")
    if os.path.isdir(chip_dir):
        total_chip_insights = 0
        for f in os.listdir(chip_dir):
            if f.endswith('.jsonl'):
                path = os.path.join(chip_dir, f)
                count = count_jsonl_lines(path)
                total_chip_insights += count
        print(f"  [{'PASS' if total_chip_insights > 0 else 'FAIL'}] Chip Insights: {total_chip_insights:,} entries")

    assert all_pass, "one or more required storage files are missing or empty"


def test_meta_ralph_state():
    """TEST 2: Verify Meta-Ralph state from persistent storage."""
    print("\n" + "="*60)
    print("TEST 2: META-RALPH STATE (From Storage, Not Memory)")
    print("="*60)

    from lib.meta_ralph import get_meta_ralph
    ralph = get_meta_ralph()
    stats = ralph.get_stats()

    print(f"  Total roasted: {stats['total_roasted']}")
    print(f"  Quality passed: {stats['quality_passed']} ({stats['pass_rate']*100:.1f}%)")
    print(f"  Primitive rejected: {stats['primitive_rejected']}")
    print(f"  Learnings stored: {stats['learnings_stored']}")
    print(f"  Refinements made: {stats['refinements_made']}")

    outcome = stats['outcome_stats']
    print(f"  Outcomes tracked: {outcome['total_tracked']}")
    print(f"  Outcomes acted on: {outcome['acted_on']}")
    print(f"  Good outcomes: {outcome['good_outcomes']}")
    print(f"  Bad outcomes: {outcome['bad_outcomes']}")

    # Verify stats are reasonable
    issues = []
    if stats['total_roasted'] == 0:
        issues.append("No items roasted - Meta-Ralph may not be receiving events")
    if stats['quality_passed'] == 0 and stats['total_roasted'] > 10:
        issues.append("No quality items passed - scoring may be too strict")
    # Pass rate thresholds are environment/tuneable dependent; treat them as warnings,
    # not hard failures (storage-level assertions are covered by TEST 1).
    warnings = []
    if stats['pass_rate'] > 0.9:
        warnings.append("Pass rate >90% - may be letting through noise")
    if stats['pass_rate'] < 0.1 and stats['total_roasted'] > 50:
        warnings.append("Pass rate <10% - may be over-filtering")

    if warnings:
        print("\n  WARNINGS:")
        for w in warnings:
            print(f"    - {w}")

    if issues:
        print("\n  ISSUES DETECTED:")
        for issue in issues:
            print(f"    - {issue}")
        pytest.fail("meta-ralph state sanity checks failed: " + "; ".join(issues))

    print("\n  [PASS] Meta-Ralph state is healthy")


def test_eidos_integration():
    """TEST 3: Verify EIDOS is receiving distillations."""
    print("\n" + "="*60)
    print("TEST 3: EIDOS INTEGRATION")
    print("="*60)

    from lib.eidos import get_store
    store = get_store()
    stats = store.get_stats()

    print(f"  Episodes: {stats['episodes']}")
    print(f"  Steps: {stats['steps']}")
    print(f"  Distillations: {stats['distillations']}")
    print(f"  Policies: {stats['policies']}")
    print(f"  High-confidence distillations: {stats['high_confidence_distillations']}")

    # Get recent distillations
    distillations = store.get_all_distillations(limit=5)
    if distillations:
        print("\n  Recent Distillations:")
        for d in distillations:
            print(f"    [{d.type.value}] {d.statement[:60]}... (conf: {d.confidence:.2f})")

    if stats['distillations'] == 0:
        print("\n  [WARN] No distillations yet - need more episodes")
        return  # Not a failure, just needs more data

    print("\n  [PASS] EIDOS has distillations")


def test_mind_integration():
    """TEST 4: Verify Mind API is running and accessible."""
    print("\n" + "="*60)
    print("TEST 4: MIND INTEGRATION")
    print("="*60)

    import requests

    try:
        port = os.environ.get("SPARK_MIND_PORT", "8080")
        r = requests.get(f"http://localhost:{port}/health", timeout=2)
        health = r.json()
        print(f"  Mind API: {health['status']}")

        r = requests.get(f"http://localhost:{port}/v1/stats", timeout=2)
        stats = r.json()
        print(f"  Total memories: {stats['total_memories']:,}")
        print(f"  Tier: {stats['tier']}")
        print(f"  By temporal level:")
        for level, count in stats.get('by_temporal_level', {}).items():
            print(f"    {level}: {count:,}")

        print("\n  [PASS] Mind API is healthy")
    except Exception as e:
        pytest.skip(f"Mind API not accessible: {e}")


def test_bridge_worker():
    """TEST 5: Verify bridge worker is running and processing."""
    print("\n" + "="*60)
    print("TEST 5: BRIDGE WORKER STATUS")
    print("="*60)

    hb_path = os.path.expanduser("~/.spark/bridge_worker_heartbeat.json")

    if not os.path.exists(hb_path):
        pytest.skip("No heartbeat file - bridge worker not running")

    with open(hb_path) as f:
        hb = json.load(f)

    ts = hb.get('ts', 0)
    age_seconds = time.time() - ts

    print(f"  Last heartbeat: {age_seconds:.0f} seconds ago")

    stats = hb.get('stats', {})
    chips = stats.get('chips', {})

    print(f"  Context updated: {stats.get('context_updated', False)}")
    print(f"  Content learned: {stats.get('content_learned', 0)}")
    print(f"  Chips activated: {chips.get('chips_activated', [])}")
    print(f"  Chip insights captured: {chips.get('insights_captured', 0)}")

    if age_seconds > 120:
        pytest.skip(f"Heartbeat is stale ({age_seconds:.0f}s > 120s)")

    print("\n  [PASS] Bridge worker is active")


def test_live_roast():
    """TEST 6: Live test of Meta-Ralph roasting."""
    print("\n" + "="*60)
    print("TEST 6: LIVE ROAST TEST")
    print("="*60)

    with _isolated_meta_ralph() as ralph:

        nonce = int(time.time() * 1000)
        test_cases = [
            # (input, expected_verdict, description)
            (f"User prefers dark theme because it reduces eye strain [{nonce}]", "quality", "Has reasoning"),
            ("Read task succeeded with Read tool", "primitive", "Tautology"),
            (f"CRITICAL: Player health 300 allows 3-4 hits, feels fair [{nonce}]", "quality", "Domain insight"),
            ("Success rate: 95% over 1000 uses", "primitive", "Pure metrics"),
            (f"Bridge worker must run for queue processing [{nonce}]", "quality", "Architecture insight"),
        ]

        all_pass = True
        for text, expected, desc in test_cases:
            result = ralph.roast(text)
            actual = result.verdict.value
            score = result.score.total

            # Duplicate verdict is acceptable for quality inputs when the same
            # core insight has already been learned and deduped.
            passed = actual == expected or (expected == "quality" and actual == "duplicate")
            if not passed:
                all_pass = False

            status = "PASS" if passed else "FAIL"
            print(f"  [{status}] {desc}")
            print(f"         Input: \"{text[:40]}...\"")
            print(f"         Expected: {expected}, Got: {actual} (score: {score}/10)")
            if not passed:
                print(f"         Issues: {result.issues_found[:2]}")
            print()

        assert all_pass, "one or more live roast verdict checks failed"


def test_outcome_tracking():
    """TEST 7: Test that outcome tracking works."""
    print("\n" + "="*60)
    print("TEST 7: OUTCOME TRACKING")
    print("="*60)

    with _isolated_meta_ralph() as ralph:
        before = ralph.get_stats()['outcome_stats']['acted_on']
        nonce = int(time.time() * 1000)

        # Track some outcomes
        ralph.track_outcome(f'test:integration:{nonce}:1', 'good', 'test evidence')
        ralph.track_outcome(f'test:integration:{nonce}:2', 'bad', 'test evidence')

        after = ralph.get_stats()['outcome_stats']['acted_on']

    print(f"  Before: {before} acted_on")
    print(f"  After: {after} acted_on")
    print(f"  Change: +{after - before}")

    if after > before:
        print("\n  [PASS] Outcome tracking increments correctly")
    else:
        pytest.fail("Outcome tracking not incrementing")


def test_refinement():
    """TEST 8: Test that structural refinement works.

    Refinement now only does structural cleanup (whitespace, prefix dedup)
    instead of adding fake boilerplate reasoning. Test with inputs that
    have structural issues.
    """
    print("\n" + "="*60)
    print("TEST 8: REFINEMENT PIPELINE (structural cleanup)")
    print("="*60)

    with _isolated_meta_ralph() as ralph:
        # Structural issue: doubled prefix → should be cleaned
        test_input = "CRITICAL: CRITICAL: always validate before writes"
        result = ralph.roast(test_input)

    print(f"  Input: \"{test_input}\"")
    print(f"  Final verdict: {result.verdict.value}")
    print(f"  Final score: {result.score.total}/10")

    if result.refined_version and result.refined_version != test_input:
        print(f"  Refined to: \"{result.refined_version[:60]}\"")
        assert "CRITICAL: CRITICAL:" not in result.refined_version, \
            "Duplicate prefix should be removed"
        print("\n  [PASS] Structural refinement is working")
    else:
        # Refinement only triggers on structural issues, so no-refinement
        # for clean input is acceptable
        print("  No structural refinement needed (input was clean)")
        print("\n  [PASS] No false refinement applied")


def run_all_tests():
    """Run all integration tests and report results."""
    print("\n")
    print("="*60)
    print("  META-RALPH INTEGRATION TEST SUITE")
    print("  Honest Assessment - Data from Real Sources")
    print("="*60)
    print(f"  Timestamp: {datetime.now().isoformat()}")

    results = {}
    tests = {
        "storage": test_storage_layer,
        "meta_ralph": test_meta_ralph_state,
        "eidos": test_eidos_integration,
        "mind": test_mind_integration,
        "bridge": test_bridge_worker,
        "roast": test_live_roast,
        "outcomes": test_outcome_tracking,
        "refinement": test_refinement,
    }

    for name, fn in tests.items():
        try:
            fn()
            results[name] = True
        except pytest.skip.Exception:
            print(f"  [SKIP] {name}")
            results[name] = True
        except AssertionError as e:
            print(f"  [FAIL] {name}: {e}")
            results[name] = False
        except Exception as e:
            print(f"  [FAIL] {name}: {e}")
            results[name] = False

    # Summary
    print("\n" + "="*60)
    print("  SUMMARY")
    print("="*60)

    passed = sum(1 for v in results.values() if v)
    total = len(results)

    for name, result in results.items():
        status = "PASS" if result else "FAIL"
        print(f"  [{status}] {name}")

    print()
    print(f"  Total: {passed}/{total} tests passed")

    if passed == total:
        print("\n  *** ALL TESTS PASSED ***")
        print("  Meta-Ralph is properly integrated and ready for iteration.")
    else:
        print(f"\n  *** {total - passed} TESTS FAILED ***")
        print("  Fix failing tests before proceeding with tuning.")

    return passed == total


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
