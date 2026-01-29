#!/usr/bin/env python3
"""bridge_worker — keep SPARK_CONTEXT.md fresh

This is the practical mechanism that makes Spark affect behavior in Clawdbot.
Clawdbot's spark-context hook injects SPARK_CONTEXT.md; this worker keeps it
updated automatically.

Design:
- small TTL loop
- task-aware (infers focus from recent events)
- safe: best-effort, never crashes the host

Usage:
  python3 bridge_worker.py --interval 60

Optional:
  python3 bridge_worker.py --interval 60 --query "current task here"
"""

import argparse
import time

from lib.bridge_cycle import run_bridge_cycle, write_bridge_heartbeat
from lib.diagnostics import setup_component_logging


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--interval", type=int, default=60, help="seconds between updates")
    ap.add_argument("--query", default=None, help="optional fixed query to tailor context")
    ap.add_argument("--once", action="store_true", help="run one cycle then exit")
    args = ap.parse_args()

    setup_component_logging("bridge_worker")

    while True:
        stats = run_bridge_cycle(
            query=args.query,
            memory_limit=60,
            pattern_limit=200,
        )
        write_bridge_heartbeat(stats)

        if args.once:
            break

        time.sleep(max(10, int(args.interval)))


if __name__ == "__main__":
    main()
