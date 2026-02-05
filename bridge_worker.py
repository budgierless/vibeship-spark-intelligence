#!/usr/bin/env python3
"""bridge_worker -- keep SPARK_CONTEXT.md fresh

This is the practical mechanism that makes Spark affect behavior in Clawdbot.
Clawdbot's spark-context hook injects SPARK_CONTEXT.md; this worker keeps it
updated automatically.

Design:
- Adaptive TTL loop (auto-tunes interval based on queue depth)
- Priority-aware event processing (failures/prompts first)
- Queue consumption (processed events are removed, queue stays bounded)
- Deep learning extraction (tool effectiveness, error patterns, workflows)
- Safe: best-effort, never crashes the host

Usage:
  python3 bridge_worker.py --interval 30

Optional:
  python3 bridge_worker.py --interval 30 --query "current task here"
"""

import argparse
import time
import threading

from lib.bridge_cycle import run_bridge_cycle, write_bridge_heartbeat
from lib.diagnostics import setup_component_logging, log_exception


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--interval", type=int, default=30, help="base seconds between updates (auto-tuned)")
    ap.add_argument("--query", default=None, help="optional fixed query to tailor context")
    ap.add_argument("--once", action="store_true", help="run one cycle then exit")
    args = ap.parse_args()

    setup_component_logging("bridge_worker")

    stop_event = threading.Event()

    def _shutdown(signum=None, frame=None):
        stop_event.set()

    try:
        import signal
        signal.signal(signal.SIGINT, _shutdown)
        signal.signal(signal.SIGTERM, _shutdown)
    except Exception:
        pass

    current_interval = max(10, int(args.interval))

    while not stop_event.is_set():
        try:
            stats = run_bridge_cycle(
                query=args.query,
                memory_limit=60,
                pattern_limit=200,
            )
            write_bridge_heartbeat(stats)

            # Auto-tune interval based on pipeline metrics
            pipeline_data = stats.get("pipeline")
            if pipeline_data:
                try:
                    from lib.pipeline import ProcessingMetrics, compute_next_interval
                    bp_level = pipeline_data.get("health", {}).get(
                        "backpressure_level", "healthy"
                    )
                    events_read = pipeline_data.get("events_read", 0)

                    # Create a lightweight metrics object for interval computation
                    m = ProcessingMetrics()
                    m.backpressure_level = bp_level
                    m.events_read = events_read
                    current_interval = compute_next_interval(
                        m, base_interval=args.interval
                    )
                except Exception:
                    current_interval = max(10, int(args.interval))
        except Exception as e:
            log_exception("bridge_worker", "bridge cycle failed", e)
            current_interval = max(10, int(args.interval))

        if args.once:
            break

        stop_event.wait(max(5, current_interval))


if __name__ == "__main__":
    main()
