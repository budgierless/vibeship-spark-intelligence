"""
Pipeline Health Test Suite

Tests that verify the Spark Intelligence pipeline is operational according to
Intelligence_Flow.md and Intelligence_Flow_Map.md architecture.

PRINCIPLE: Never trust scoring metrics if the pipeline isn't running.
PRINCIPLE: Reality over metrics - if events aren't flowing, nothing is learning.

Architecture (from Intelligence_Flow.md):
    Sources (observe.py, sparkd.py)
        -> Queue (~/.spark/queue/events.jsonl)
        -> bridge_worker.py (every 60s)
        -> bridge_cycle.run_bridge_cycle
        -> {cognitive_learner, pattern_detection, eidos_store, chips}
        -> storage (cognitive_insights.json, eidos.db, chip_insights/)
        -> promoter -> CLAUDE.md/AGENTS.md

Usage:
    python tests/test_pipeline_health.py           # Full health check
    python tests/test_pipeline_health.py quick     # Quick status only
    python tests/test_pipeline_health.py flow      # Test event flow
    python tests/test_pipeline_health.py trace     # Trace a test event end-to-end
"""

import sys
import json
import time
import sqlite3
import os
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
import pytest

# Add lib to path
sys.path.insert(0, str(Path(__file__).parent.parent))
pytestmark = pytest.mark.integration

SPARK_DIR = Path.home() / '.spark'


@dataclass
class HealthCheck:
    """Result of a single health check."""
    name: str
    passed: bool
    message: str
    severity: str  # "critical", "warning", "info"
    details: Optional[Dict] = None


class PipelineHealthChecker:
    """
    Verifies Spark Intelligence pipeline health according to Intelligence_Flow.md.

    REMEMBER: A pipeline with perfect scoring but no flow is worthless.
    The goal is to catch disconnected components BEFORE wasting time on tuning.
    """

    def __init__(self):
        self.checks: List[HealthCheck] = []

    def _add_check(self, name: str, passed: bool, message: str,
                   severity: str = "warning", details: Dict = None):
        self.checks.append(HealthCheck(name, passed, message, severity, details))

    # =========================================================================
    # LAYER 1: Source Layer Checks
    # =========================================================================

    def check_observe_hook_exists(self) -> bool:
        """Verify observe.py hook file exists."""
        hook_file = Path(__file__).parent.parent / 'hooks' / 'observe.py'
        exists = hook_file.exists()
        self._add_check(
            "observe.py exists",
            exists,
            f"Hook file: {hook_file}" if exists else f"Missing: {hook_file}",
            "critical"
        )
        return exists

    # =========================================================================
    # LAYER 2: Queue Layer Checks
    # =========================================================================

    def check_queue_exists(self) -> bool:
        """Verify queue file exists and is accessible."""
        queue_file = SPARK_DIR / 'queue' / 'events.jsonl'
        exists = queue_file.exists()

        if exists:
            size = queue_file.stat().st_size
            age = datetime.now() - datetime.fromtimestamp(queue_file.stat().st_mtime)
            self._add_check(
                "Queue file exists",
                True,
                f"Size: {size:,} bytes, Last modified: {age.seconds}s ago",
                "info",
                {"size": size, "age_seconds": age.seconds}
            )
        else:
            self._add_check(
                "Queue file exists",
                False,
                f"Queue file missing: {queue_file}",
                "critical"
            )
        return exists

    def check_queue_recent_events(self) -> Tuple[bool, int]:
        """Check if there are recent events in the queue."""
        try:
            from lib.queue import read_recent_events
            events = read_recent_events(50)
            count = len(events)

            # Check for events in last hour
            # SparkEvent has .timestamp as a float (unix timestamp)
            recent_count = 0
            one_hour_ago = datetime.now().timestamp() - 3600
            for event in events:
                # SparkEvent is a dataclass with timestamp attribute
                ts = getattr(event, 'timestamp', None)
                if ts and ts > one_hour_ago:
                    recent_count += 1

            self._add_check(
                "Queue has events",
                count > 0,
                f"Total events: {count}, Recent (1h): {recent_count}",
                "warning" if count == 0 else "info",
                {"total": count, "recent_1h": recent_count}
            )
            return count > 0, count
        except Exception as e:
            self._add_check(
                "Queue has events",
                False,
                f"Error reading queue: {e}",
                "critical"
            )
            return False, 0

    # =========================================================================
    # LAYER 3: Bridge Worker Checks (CRITICAL)
    # =========================================================================

    def check_bridge_worker_heartbeat(self) -> Tuple[bool, int]:
        """
        Check bridge_worker heartbeat - THE MOST IMPORTANT CHECK.
        If bridge_worker isn't running, nothing gets processed.
        """
        heartbeat_file = SPARK_DIR / 'bridge_worker_heartbeat.json'

        if not heartbeat_file.exists():
            self._add_check(
                "Bridge worker heartbeat",
                False,
                "No heartbeat file - bridge_worker is NOT running!",
                "critical"
            )
            return False, -1

        try:
            data = json.loads(heartbeat_file.read_text())

            # Handle both 'ts' (unix timestamp) and 'timestamp' (ISO format)
            ts = data.get('ts') or data.get('timestamp')

            if ts:
                # If it's a number (unix timestamp), convert to age directly
                if isinstance(ts, (int, float)):
                    age = time.time() - ts
                else:
                    # ISO format string
                    heartbeat_time = datetime.fromisoformat(str(ts))
                    age = (datetime.now() - heartbeat_time).total_seconds()

                # Bridge worker runs every 60s, so heartbeat should be < 120s old
                fresh = age < 120
                self._add_check(
                    "Bridge worker heartbeat",
                    fresh,
                    f"Age: {int(age)}s" + (" (STALE - worker may be dead!)" if not fresh else " (fresh)"),
                    "critical" if not fresh else "info",
                    {"age_seconds": int(age), "last_heartbeat": str(ts)}
                )
                return fresh, int(age)
            else:
                self._add_check(
                    "Bridge worker heartbeat",
                    False,
                    "Heartbeat file has no timestamp",
                    "critical"
                )
                return False, -1
        except Exception as e:
            self._add_check(
                "Bridge worker heartbeat",
                False,
                f"Error reading heartbeat: {e}",
                "critical"
            )
            return False, -1

    # =========================================================================
    # LAYER 4: Processing Components Checks
    # =========================================================================

    def check_meta_ralph_active(self) -> Tuple[bool, Dict]:
        """Check if Meta-Ralph is receiving and processing events."""
        try:
            from lib.meta_ralph import get_meta_ralph
            ralph = get_meta_ralph()
            stats = ralph.get_stats()

            total = stats.get('total_roasted', 0)
            active = total > 0
            quality_rate = stats.get('quality_rate')
            if quality_rate is None:
                quality_rate = stats.get('pass_rate', 0)

            self._add_check(
                "Meta-Ralph receiving events",
                active,
                f"Total roasted: {total}, Quality rate: {quality_rate:.1%}",
                "warning" if not active else "info",
                stats
            )
            return active, stats
        except Exception as e:
            self._add_check(
                "Meta-Ralph receiving events",
                False,
                f"Error checking Meta-Ralph: {e}",
                "warning"
            )
            return False, {}

    def check_trace_binding(self) -> Tuple[bool, Dict]:
        """Check if trace_id bindings exist on steps/evidence/outcomes."""
        trace_info = {
            "steps_missing": 0,
            "evidence_missing": 0,
            "outcomes_missing": 0,
        }
        ok = True
        try:
            from lib.eidos import get_store, get_evidence_store
            store = get_store()
            with sqlite3.connect(store.db_path) as conn:
                row = conn.execute(
                    "SELECT COUNT(*) FROM steps WHERE trace_id IS NULL OR trace_id = ''"
                ).fetchone()
                trace_info["steps_missing"] = int(row[0] or 0)
        except Exception:
            ok = False

        try:
            from lib.eidos import get_evidence_store
            ev_store = get_evidence_store()
            with sqlite3.connect(ev_store.db_path) as conn:
                cols = conn.execute("PRAGMA table_info(evidence)").fetchall()
                has_trace = any(c[1] == "trace_id" for c in cols)
                if has_trace:
                    row = conn.execute(
                        "SELECT COUNT(*) FROM evidence WHERE trace_id IS NULL OR trace_id = ''"
                    ).fetchone()
                    trace_info["evidence_missing"] = int(row[0] or 0)
        except Exception:
            ok = False

        try:
            from lib.outcome_log import OUTCOMES_FILE
            if OUTCOMES_FILE.exists():
                with OUTCOMES_FILE.open("r", encoding="utf-8") as f:
                    for line in f:
                        if not line.strip():
                            continue
                        try:
                            row = json.loads(line)
                        except Exception:
                            continue
                        if not row.get("trace_id"):
                            trace_info["outcomes_missing"] += 1
        except Exception:
            ok = False

        missing_total = (
            trace_info["steps_missing"]
            + trace_info["evidence_missing"]
            + trace_info["outcomes_missing"]
        )
        self._add_check(
            "Trace binding",
            ok and missing_total == 0,
            f"Missing trace_id - steps: {trace_info['steps_missing']}, "
            f"evidence: {trace_info['evidence_missing']}, "
            f"outcomes: {trace_info['outcomes_missing']}",
            "warning" if missing_total else "info",
            trace_info,
        )
        return missing_total == 0, trace_info

    def check_cognitive_learner_storage(self) -> Tuple[bool, int]:
        """Check if cognitive insights are being stored."""
        insights_file = SPARK_DIR / 'cognitive_insights.json'

        if not insights_file.exists():
            self._add_check(
                "Cognitive insights storage",
                False,
                "No cognitive_insights.json - nothing stored yet",
                "warning"
            )
            return False, 0

        try:
            data = json.loads(insights_file.read_text())

            # cognitive_insights.json stores insights as key-value pairs
            # Keys are like "category:insight_title"
            # Each value is an insight dict with created_at, text, etc.
            if isinstance(data, dict):
                # Count all keys (each key is an insight)
                count = len(data)

                # Check for recent insights
                recent_count = 0
                one_day_ago = datetime.now() - timedelta(days=1)
                for key, insight in list(data.items())[-100:]:  # Check last 100
                    if isinstance(insight, dict):
                        ts = insight.get('created_at', '')
                        if ts:
                            try:
                                insight_time = datetime.fromisoformat(ts)
                                if insight_time > one_day_ago:
                                    recent_count += 1
                            except:
                                pass
            else:
                # Fallback for array format
                insights = data.get('insights', []) if isinstance(data, dict) else []
                count = len(insights)
                recent_count = 0

            self._add_check(
                "Cognitive insights storage",
                count > 0,
                f"Total: {count}, Recent (24h): {recent_count}",
                "info" if count > 0 else "warning",
                {"total": count, "recent_24h": recent_count}
            )
            return count > 0, count
        except Exception as e:
            self._add_check(
                "Cognitive insights storage",
                False,
                f"Error reading insights: {e}",
                "warning"
            )
            return False, 0

    def check_pattern_aggregator(self) -> Tuple[bool, Dict]:
        """Check if pattern aggregator is receiving events."""
        try:
            from lib.pattern_detection import get_aggregator, get_pattern_backlog
            agg = get_aggregator()
            stats = agg.get_stats()

            logged = stats.get('total_patterns_logged', 0)
            detected = stats.get('total_patterns_detected', 0)
            backlog = get_pattern_backlog()
            active = (logged > 0) or (detected > 0)

            self._add_check(
                "Pattern aggregator active",
                active,
                f"Logged: {logged}, In-memory: {detected}, Backlog: {backlog}",
                "warning" if not active else "info",
                {**stats, "backlog": backlog}
            )
            return active, stats
        except Exception as e:
            self._add_check(
                "Pattern aggregator active",
                False,
                f"Error checking aggregator: {e}",
                "warning"
            )
            return False, {}

    def check_eidos_store(self) -> Tuple[bool, Dict]:
        """Check EIDOS store for distillations."""
        try:
            from lib.eidos import get_store
            store = get_store()
            stats = store.get_stats()

            episodes = stats.get('episodes', 0)
            steps = stats.get('steps', 0)
            distillations = stats.get('distillations', 0)

            active = episodes > 0 or steps > 0 or distillations > 0
            self._add_check(
                "EIDOS store active",
                active,
                f"Episodes: {episodes}, Steps: {steps}, Distillations: {distillations}",
                "info" if active else "warning",
                stats
            )
            return active, stats
        except Exception as e:
            self._add_check(
                "EIDOS store active",
                False,
                f"Error checking EIDOS: {e}",
                "warning"
            )
            return False, {}

    # =========================================================================
    # LAYER 5: Output/Promotion Checks
    # =========================================================================

    def check_promoter_activity(self) -> Tuple[bool, Dict]:
        """Check if promoter has promoted any insights."""
        try:
            from lib.promoter import get_promotion_stats
            stats = get_promotion_stats()

            promoted = stats.get('total_promoted', 0)
            pending = stats.get('pending', 0)

            self._add_check(
                "Promoter activity",
                promoted > 0,
                f"Promoted: {promoted}, Pending: {pending}",
                "info",
                stats
            )
            return promoted > 0, stats
        except Exception as e:
            # Promoter may not have stats function, check files instead
            claude_md = Path(__file__).parent.parent / 'CLAUDE.md'
            if claude_md.exists():
                try:
                    content = claude_md.read_text(encoding='utf-8')
                    has_learnings = 'SPARK_LEARNINGS_START' in content
                    self._add_check(
                        "Promoter activity",
                        has_learnings,
                        "CLAUDE.md has learnings section" if has_learnings else "No learnings in CLAUDE.md",
                        "info"
                    )
                    return has_learnings, {}
                except Exception as read_error:
                    self._add_check(
                        "Promoter activity",
                        False,
                        f"Could not read CLAUDE.md: {read_error}",
                        "warning"
                    )
                    return False, {}
            return False, {}

    # =========================================================================
    # LAYER 6: Mind Integration Checks
    # =========================================================================

    def check_mind_connection(self) -> Tuple[bool, Dict]:
        """Check connection to Mind API."""
        try:
            import requests
            port = os.environ.get("SPARK_MIND_PORT", "8080")
            response = requests.get(f"http://localhost:{port}/health", timeout=2)
            healthy = response.status_code == 200

            if healthy:
                # Get stats too
                stats_response = requests.get(f"http://localhost:{port}/v1/stats", timeout=2)
                if stats_response.status_code == 200:
                    stats = stats_response.json()
                    self._add_check(
                        "Mind API connection",
                        True,
                        f"Connected - {stats.get('total_memories', 0)} memories",
                        "info",
                        stats
                    )
                    return True, stats

            self._add_check(
                "Mind API connection",
                False,
                "Mind API not responding",
                "warning"
            )
            return False, {}
        except Exception as e:
            self._add_check(
                "Mind API connection",
                False,
                f"Cannot connect to Mind: {e}",
                "warning"
            )
            return False, {}

    # =========================================================================
    # COMPOUND CHECKS: Flow Verification
    # =========================================================================

    def verify_queue_to_bridge_flow(self) -> bool:
        """Verify events are flowing from queue to bridge."""
        queue_ok, queue_count = self.check_queue_recent_events()
        bridge_ok, bridge_age = self.check_bridge_worker_heartbeat()

        if not bridge_ok:
            self._add_check(
                "Queue -> Bridge flow",
                False,
                "Bridge worker not running - queue events not being processed!",
                "critical"
            )
            return False

        if queue_count == 0:
            self._add_check(
                "Queue -> Bridge flow",
                True,  # Not necessarily broken, just empty
                "Queue empty - no events to process",
                "info"
            )
            return True

        self._add_check(
            "Queue -> Bridge flow",
            True,
            f"Bridge running (age {bridge_age}s), queue has {queue_count} events",
            "info"
        )
        return True

    def verify_bridge_to_storage_flow(self) -> bool:
        """Verify bridge is storing processed insights."""
        ralph_ok, ralph_stats = self.check_meta_ralph_active()
        storage_ok, storage_count = self.check_cognitive_learner_storage()

        if ralph_stats.get('total_roasted', 0) > 0 and storage_count == 0:
            self._add_check(
                "Bridge -> Storage flow",
                False,
                "Meta-Ralph processing events but nothing stored! (Session 2 bug)",
                "critical"
            )
            return False

        self._add_check(
            "Bridge -> Storage flow",
            storage_ok,
            f"Ralph roasted: {ralph_stats.get('total_roasted', 0)}, Stored: {storage_count}",
            "info" if storage_ok else "warning"
        )
        return storage_ok

    # =========================================================================
    # Main Health Check
    # =========================================================================

    def run_full_check(self) -> Dict:
        """Run all health checks and return summary."""
        self.checks = []  # Reset

        print("\n" + "=" * 70)
        print(" SPARK INTELLIGENCE PIPELINE HEALTH CHECK")
        print(" Based on: Intelligence_Flow.md + Intelligence_Flow_Map.md")
        print("=" * 70)

        # Layer 1: Sources
        print("\n[LAYER 1: Sources]")
        self.check_observe_hook_exists()

        # Layer 2: Queue
        print("\n[LAYER 2: Queue]")
        self.check_queue_exists()
        self.check_queue_recent_events()

        # Layer 3: Bridge Worker (CRITICAL)
        print("\n[LAYER 3: Bridge Worker - CRITICAL]")
        self.check_bridge_worker_heartbeat()

        # Layer 4: Processing
        print("\n[LAYER 4: Processing Components]")
        self.check_meta_ralph_active()
        self.check_cognitive_learner_storage()
        self.check_pattern_aggregator()
        self.check_eidos_store()
        self.check_trace_binding()

        # Layer 5: Output
        print("\n[LAYER 5: Output/Promotion]")
        self.check_promoter_activity()

        # Layer 6: Mind
        print("\n[LAYER 6: Mind Integration]")
        self.check_mind_connection()

        # Flow Verification
        print("\n[FLOW VERIFICATION]")
        self.verify_queue_to_bridge_flow()
        self.verify_bridge_to_storage_flow()

        # Print results
        self._print_results()

        return self._get_summary()

    def run_quick_check(self) -> Dict:
        """Run minimal critical checks only."""
        self.checks = []

        print("\n" + "=" * 50)
        print(" QUICK PIPELINE HEALTH CHECK")
        print("=" * 50)

        self.check_bridge_worker_heartbeat()
        self.check_queue_recent_events()
        self.check_meta_ralph_active()
        self.check_cognitive_learner_storage()

        self._print_results()
        return self._get_summary()

    def _print_results(self):
        """Print check results."""
        print("\n" + "-" * 50)
        print(" RESULTS")
        print("-" * 50)

        critical_failures = []
        warnings = []

        for check in self.checks:
            status = "PASS" if check.passed else "FAIL"
            # Use ASCII-safe symbols for Windows compatibility
            icon = "[OK]" if check.passed else ("[!!]" if check.severity == "critical" else "[??]")
            print(f"  {icon} [{status}] {check.name}")
            print(f"       {check.message}")

            if not check.passed:
                if check.severity == "critical":
                    critical_failures.append(check)
                else:
                    warnings.append(check)

        print("\n" + "-" * 50)

        if critical_failures:
            print("\n CRITICAL ISSUES (must fix before tuning):")
            for check in critical_failures:
                print(f"   - {check.name}: {check.message}")

        if warnings:
            print("\n WARNINGS (should investigate):")
            for check in warnings:
                print(f"   - {check.name}: {check.message}")

        if not critical_failures and not warnings:
            print("\n ALL CHECKS PASSED - Pipeline is healthy!")

        print()

    def _get_summary(self) -> Dict:
        """Get summary as dictionary."""
        passed = sum(1 for c in self.checks if c.passed)
        failed = len(self.checks) - passed
        critical = sum(1 for c in self.checks if not c.passed and c.severity == "critical")

        return {
            "total_checks": len(self.checks),
            "passed": passed,
            "failed": failed,
            "critical_failures": critical,
            "healthy": critical == 0,
            "checks": [
                {
                    "name": c.name,
                    "passed": c.passed,
                    "message": c.message,
                    "severity": c.severity
                }
                for c in self.checks
            ]
        }


def test_event_flow():
    """
    Test that an event can flow through the complete pipeline.
    This is the ULTIMATE test - proves the architecture is connected.
    """
    print("\n" + "=" * 70)
    print(" END-TO-END EVENT FLOW TEST")
    print(" Traces: observe.py -> queue -> bridge -> storage")
    print("=" * 70)

    from lib.queue import quick_capture, EventType

    # Create a unique test event
    test_id = f"test_{int(time.time())}"
    test_content = f"[PIPELINE_TEST:{test_id}] Remember this: testing pipeline flow works correctly"
    session_id = "pipeline_test"

    print(f"\n1. Emitting test event: {test_id}")

    # Capture to queue
    quick_capture(
        event_type=EventType.USER_PROMPT,
        session_id=session_id,
        data={
            "payload": {"role": "user", "text": test_content},
            "source": "pipeline_test",
            "kind": "message",
        },
        trace_id=f"pipeline-{test_id}",
    )

    print("   Event written to queue")

    # Check if it's in queue
    from lib.queue import read_recent_events
    events = read_recent_events(10)

    found_in_queue = any(
        test_id in str(getattr(e, 'data', {}) or {})
        for e in events
    )

    print(f"2. Event in queue: {'YES' if found_in_queue else 'NO'}")

    if not found_in_queue:
        print("   FAIL: Event not found in queue!")
        pytest.fail("event not found in queue after capture")

    # Check bridge worker
    checker = PipelineHealthChecker()
    bridge_ok, age = checker.check_bridge_worker_heartbeat()

    if not bridge_ok:
        print("\n3. Bridge worker: NOT RUNNING!")
        print("   Cannot trace event through pipeline.")
        print("   Start bridge_worker and try again.")
        pytest.skip("bridge worker heartbeat missing/stale during event flow test")

    print(f"3. Bridge worker: Running (heartbeat {age}s ago)")
    print("   Next cycle will process this event")

    # Note: We can't wait for bridge cycle in a test, but we can verify the setup
    print("\n4. To verify end-to-end:")
    print("   - Wait 60s for bridge cycle")
    print("   - Then run: python -c \"")
    print("     from lib.meta_ralph import get_meta_ralph")
    print("     for r in get_meta_ralph().get_recent_roasts(10):")
    print(f"         if '{test_id}' in str(r): print('FOUND in Meta-Ralph!')\"")


def main():
    """Main entry point."""
    mode = sys.argv[1] if len(sys.argv) > 1 else "full"

    checker = PipelineHealthChecker()

    if mode == "quick":
        summary = checker.run_quick_check()
    elif mode == "flow":
        test_event_flow()
        return
    elif mode == "trace":
        test_event_flow()
        return
    else:
        summary = checker.run_full_check()

    # Exit with error if critical failures
    if summary.get("critical_failures", 0) > 0:
        print("\nPIPELINE NOT HEALTHY - Fix critical issues before tuning!")
        sys.exit(1)
    else:
        print("\nPipeline healthy - safe to proceed with tuning.")
        sys.exit(0)


if __name__ == "__main__":
    main()
