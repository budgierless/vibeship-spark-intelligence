#!/usr/bin/env python3
"""Show local Spark service status (cross-platform)."""

from __future__ import annotations

import sys
import time
from pathlib import Path
SPARK_DIR = Path(__file__).resolve().parent.parent


def _service_lines(bridge_stale_s: int = 90) -> list[str]:
    sys.path.insert(0, str(SPARK_DIR))
    from lib.service_control import service_status, format_status_lines

    status = service_status(bridge_stale_s=bridge_stale_s)
    return format_status_lines(status, bridge_stale_s=bridge_stale_s)


def _queue_counts() -> tuple[int, int, int]:
    sys.path.insert(0, str(SPARK_DIR))
    from lib.queue import count_events
    from lib.pattern_detection.worker import get_pattern_backlog
    from lib.validation_loop import get_validation_backlog

    return count_events(), get_pattern_backlog(), get_validation_backlog()


def _validation_state():
    sys.path.insert(0, str(SPARK_DIR))
    from lib.validation_loop import get_validation_state

    return get_validation_state()


def main() -> None:
    print("")
    for line in _service_lines():
        print(line)

    try:
        queue_count, pattern_backlog, validation_backlog = _queue_counts()
        print(
            f"[spark] queue: {queue_count} events (pattern backlog {pattern_backlog}, validation backlog {validation_backlog})"
        )
    except Exception as e:
        print(f"[spark] queue: error ({e})")

    try:
        vstate = _validation_state()
        last_ts = vstate.get("last_run_ts")
        if last_ts:
            age_s = max(0, int(time.time() - float(last_ts)))
            stats = vstate.get("last_stats") or {}
            print(
                f"[spark] validation: last {age_s}s (+{stats.get('validated', 0)} / -{stats.get('contradicted', 0)})"
            )
        else:
            print("[spark] validation: never run")
    except Exception as e:
        print(f"[spark] validation: error ({e})")

    print("")


if __name__ == "__main__":
    main()
