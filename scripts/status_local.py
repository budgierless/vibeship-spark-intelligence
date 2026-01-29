#!/usr/bin/env python3
"""Show local Spark service status (cross-platform)."""

from __future__ import annotations

import sys
import time
from pathlib import Path
from urllib import request


SPARK_DIR = Path(__file__).resolve().parent.parent


def _http_ok(url: str, timeout: float = 1.5) -> bool:
    try:
        req = request.Request(url, method="GET")
        with request.urlopen(req, timeout=timeout) as resp:
            return 200 <= resp.status < 300
    except Exception:
        return False


def _bridge_heartbeat_age() -> float | None:
    sys.path.insert(0, str(SPARK_DIR))
    from lib.bridge_cycle import bridge_heartbeat_age_s

    return bridge_heartbeat_age_s()


def _queue_counts() -> tuple[int, int, int]:
    sys.path.insert(0, str(SPARK_DIR))
    from lib.queue import count_events
    from lib.pattern_detection.worker import get_pattern_backlog
    from lib.validation_loop import get_validation_backlog

    return count_events(), get_pattern_backlog(), get_validation_backlog()


def main() -> None:
    sparkd_ok = _http_ok("http://127.0.0.1:8787/health")
    dash_ok = _http_ok("http://127.0.0.1:8585/api/status")
    hb_age = _bridge_heartbeat_age()

    print("")
    print(f"[spark] sparkd: {'RUNNING' if sparkd_ok else 'STOPPED'}")
    print(f"[spark] dashboard: {'RUNNING' if dash_ok else 'STOPPED'}")
    if hb_age is None:
        print("[spark] bridge_worker: UNKNOWN (no heartbeat)")
    else:
        status = "RUNNING" if hb_age <= 90 else "STALE"
        print(f"[spark] bridge_worker: {status} (last {int(hb_age)}s ago)")

    try:
        queue_count, pattern_backlog, validation_backlog = _queue_counts()
        print(
            f"[spark] queue: {queue_count} events (pattern backlog {pattern_backlog}, validation backlog {validation_backlog})"
        )
    except Exception as e:
        print(f"[spark] queue: error ({e})")

    print("")
    print("Dashboard: http://127.0.0.1:8585")


if __name__ == "__main__":
    main()
