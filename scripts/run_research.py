#!/usr/bin/env python3
"""
Spark X Research Runner - Autonomous intelligence gathering.

Run manually or via Windows Task Scheduler.

Usage:
    # Full research session (all phases)
    python scripts/run_research.py

    # Quick search only (no account study)
    python scripts/run_research.py --quick

    # Show current research state
    python scripts/run_research.py --status

    # Continuous mode - run every N hours
    python scripts/run_research.py --loop --interval 4

Schedule with Windows Task Scheduler:
    Action: Start a program
    Program: python
    Arguments: C:\\Users\\USER\\Desktop\\vibeship-spark-intelligence\\scripts\\run_research.py
    Start in: C:\\Users\\USER\\Desktop\\vibeship-spark-intelligence
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from lib.x_research import SparkResearcher, RESEARCH_STATE_PATH, WATCHLIST_PATH


def show_status():
    """Show current research state."""
    print("=" * 50)
    print("  SPARK RESEARCH STATUS")
    print("=" * 50)

    if RESEARCH_STATE_PATH.exists():
        state = json.loads(RESEARCH_STATE_PATH.read_text(encoding="utf-8"))
        print(f"  Sessions run:       {state.get('sessions_run', 0)}")
        print(f"  Tweets analyzed:    {state.get('total_tweets_analyzed', 0)}")
        print(f"  Insights stored:    {state.get('total_insights_stored', 0)}")

        last = state.get("last_session", {})
        if last:
            print(f"  Last session:       {last.get('timestamp', 'never')}")
            print(f"    Duration:         {last.get('duration_seconds', 0):.0f}s")
            print(f"    Insights:         {last.get('insights_generated', 0)}")
            print(f"    High performers:  {last.get('high_performers_found', 0)}")
            print(f"    Accounts found:   {last.get('accounts_discovered', 0)}")

        intents = state.get("research_intents", [])
        if intents:
            print(f"\n  Active research intents ({len(intents)}):")
            for intent in intents[-5:]:
                print(f"    - {intent}")

        discovered = state.get("discovered_topics", [])
        if discovered:
            print(f"\n  Discovered topics ({len(discovered)}):")
            for t in discovered[-5:]:
                print(f"    - {t['name']} (seen {t.get('discovery_count', '?')}x)")
    else:
        print("  No research sessions run yet.")

    if WATCHLIST_PATH.exists():
        wl = json.loads(WATCHLIST_PATH.read_text(encoding="utf-8"))
        accounts = wl.get("accounts", [])
        print(f"\n  Watchlist: {len(accounts)} accounts")
        for a in sorted(accounts, key=lambda x: x.get("priority", 0), reverse=True)[:10]:
            print(f"    @{a['handle']:20s}  {a.get('followers', 0):>8,} followers  "
                  f"priority={a.get('priority', 0)}  via={a.get('discovered_via', '?')}")
    else:
        print("\n  Watchlist: empty")

    print("=" * 50)


def run_session(quick: bool = False):
    """Run a research session."""
    print()
    print("=" * 50)
    print("  SPARK X RESEARCH ENGINE")
    print(f"  {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")
    print("=" * 50)
    print()

    researcher = SparkResearcher(verbose=True)

    if quick:
        # Quick mode: just search topics, skip account study
        print("  [QUICK MODE] Searching topics only...")
        high_performers = researcher.search_topics()
        researcher.analyze_patterns(high_performers)
        trends = researcher.detect_trends(high_performers)
        researcher.evolve(high_performers, trends)
        # Update state counters
        researcher.state["sessions_run"] = researcher.state.get("sessions_run", 0) + 1
        researcher.state["total_tweets_analyzed"] = (
            researcher.state.get("total_tweets_analyzed", 0)
            + sum(1 for i in researcher.session_insights
                  if i.get("observer") == "trend_observed" and i.get("captured_data", {}).get("fields", {}).get("tweet_text"))
        )
        researcher.state["total_insights_stored"] = (
            researcher.state.get("total_insights_stored", 0) + len(researcher.session_insights)
        )
        researcher.state["last_session"] = {
            "timestamp": researcher.session_start.isoformat(),
            "duration_seconds": (datetime.now(timezone.utc) - researcher.session_start).total_seconds(),
            "insights_generated": len(researcher.session_insights),
            "high_performers_found": len(high_performers),
            "mode": "quick",
        }
        researcher._save_state()
        researcher._save_watchlist()
        print(f"\n  Quick session done: {len(researcher.session_insights)} insights")
    else:
        summary = researcher.run_session()

    return researcher


def run_loop(interval_hours: float):
    """Run research sessions in a loop."""
    print(f"  CONTINUOUS MODE: Running every {interval_hours} hours")
    print(f"  Press Ctrl+C to stop\n")

    while True:
        try:
            run_session()
            next_run = datetime.now(timezone.utc).strftime('%H:%M UTC')
            print(f"\n  Next session in {interval_hours} hours (after {next_run})")
            time.sleep(interval_hours * 3600)
        except KeyboardInterrupt:
            print("\n  Stopped by user.")
            break
        except Exception as e:
            print(f"\n  ERROR: {e}")
            print(f"  Retrying in 15 minutes...")
            time.sleep(900)


def main():
    parser = argparse.ArgumentParser(description="Spark X Research Engine")
    parser.add_argument("--quick", action="store_true", help="Quick search only, skip account study")
    parser.add_argument("--status", action="store_true", help="Show research status")
    parser.add_argument("--loop", action="store_true", help="Run continuously")
    parser.add_argument("--interval", type=float, default=4, help="Hours between sessions (default: 4)")
    args = parser.parse_args()

    if args.status:
        show_status()
    elif args.loop:
        run_loop(args.interval)
    else:
        run_session(quick=args.quick)


if __name__ == "__main__":
    main()
