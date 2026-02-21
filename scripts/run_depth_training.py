#!/usr/bin/env python3
"""
DEPTH Training Runner for Spark Intelligence.

Launches autonomous DEPTH training sessions that make Spark smarter.
Discovers topics, trains through 10-level Socratic descents,
feeds results through Ralph quality gate, and accumulates knowledge.

Usage:
    python scripts/run_depth_training.py                  # 5 cycles
    python scripts/run_depth_training.py --cycles 10      # 10 cycles
    python scripts/run_depth_training.py --infinite       # Run forever
    python scripts/run_depth_training.py --topic "truth"  # Single topic
    python scripts/run_depth_training.py --status         # Show dashboard
"""

from __future__ import annotations

import asyncio
import argparse
import logging
import sys
from pathlib import Path

# Add project root to path
ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(name)s %(message)s",
)
log = logging.getLogger("depth_runner")


def check_prerequisites() -> bool:
    """Verify DEPTH server and Ollama are running."""
    import httpx

    ok = True

    # Check DEPTH server
    try:
        resp = httpx.get("http://localhost:5555/api/health", timeout=5.0)
        if resp.status_code == 200:
            print("  [OK] DEPTH server running on :5555")
        else:
            print("  [!!] DEPTH server responded but not healthy")
            ok = False
    except Exception:
        print("  [!!] DEPTH server not running. Start it:")
        print("       cd vibeship-depth-game && python server.py")
        ok = False

    # Check Ollama
    try:
        resp = httpx.get("http://localhost:11434/api/tags", timeout=5.0)
        if resp.status_code == 200:
            models = [m["name"] for m in resp.json().get("models", [])]
            if "phi4-mini" in models or "phi4-mini:latest" in models:
                print("  [OK] Ollama running with phi4-mini")
            else:
                print(f"  [!!] Ollama running but phi4-mini not found. Models: {models}")
                ok = False
        else:
            print("  [!!] Ollama not responding")
            ok = False
    except Exception:
        print("  [!!] Ollama not running. Start it: ollama serve")
        ok = False

    return ok


async def main():
    parser = argparse.ArgumentParser(
        description="DEPTH Training Runner for Spark Intelligence"
    )
    parser.add_argument("--cycles", type=int, default=5,
                        help="Number of training cycles (default: 5)")
    parser.add_argument("--infinite", action="store_true",
                        help="Run indefinitely")
    parser.add_argument("--topic", type=str,
                        help="Train on a specific topic only")
    parser.add_argument("--status", action="store_true",
                        help="Show training dashboard")
    parser.add_argument("--report", action="store_true",
                        help="Show weakness report")
    parser.add_argument("--quiet", action="store_true",
                        help="Minimal output")
    args = parser.parse_args()

    from lib.depth_trainer import (
        train, run_autonomous_loop, print_dashboard,
        get_weakness_report,
    )

    if args.status:
        print_dashboard()
        return

    if args.report:
        import json
        report = get_weakness_report()
        print(json.dumps(report, indent=2))
        return

    # Check prerequisites
    print("\n  Checking prerequisites...")
    if not check_prerequisites():
        print("\n  Fix the above issues and try again.")
        return

    print()

    if args.topic:
        await train(args.topic, verbose=not args.quiet)
    else:
        cycles = 0 if args.infinite else args.cycles
        await run_autonomous_loop(
            max_cycles=cycles,
            verbose=not args.quiet,
        )


if __name__ == "__main__":
    asyncio.run(main())
