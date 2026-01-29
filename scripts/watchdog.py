#!/usr/bin/env python3
"""Lightweight Spark watchdog: restarts critical workers and warns on queue growth."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Optional
from urllib import request


SPARK_DIR = Path(__file__).resolve().parent.parent
LOG_DIR = Path.home() / ".spark" / "logs"
STATE_FILE = Path.home() / ".spark" / "watchdog_state.json"


def _ensure_log_dir() -> Path:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    return LOG_DIR


def _log(msg: str) -> None:
    ts = time.strftime("%Y-%m-%d %H:%M:%S")
    line = f"[watchdog] {ts} {msg}"
    try:
        _ensure_log_dir()
        with open(LOG_DIR / "watchdog.log", "a", encoding="utf-8", errors="replace") as f:
            f.write(line + "\n")
    except Exception:
        pass
    print(line)


def _http_ok(url: str, timeout: float = 1.5) -> bool:
    try:
        req = request.Request(url, method="GET")
        with request.urlopen(req, timeout=timeout) as resp:
            return 200 <= resp.status < 300
    except Exception:
        return False


def _process_exists(keyword: str) -> bool:
    try:
        if os.name == "nt":
            out = subprocess.check_output(
                ["wmic", "process", "get", "CommandLine,ProcessId"],
                text=True,
                errors="ignore",
            )
        else:
            out = subprocess.check_output(
                ["ps", "-ax", "-o", "pid=,command="],
                text=True,
                errors="ignore",
            )
        return any(keyword in line for line in out.splitlines())
    except Exception:
        return False


def _start_process(name: str, args: list[str]) -> bool:
    try:
        _ensure_log_dir()
        log_path = LOG_DIR / f"{name}.log"
        env = os.environ.copy()
        env["SPARK_LOG_DIR"] = str(LOG_DIR)
        creationflags = 0
        if os.name == "nt":
            creationflags = (
                getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
                | getattr(subprocess, "DETACHED_PROCESS", 0)
            )
        with open(log_path, "a", encoding="utf-8", errors="replace") as log_f:
            subprocess.Popen(
                args,
                cwd=str(SPARK_DIR),
                stdout=log_f,
                stderr=log_f,
                env=env,
                creationflags=creationflags,
                start_new_session=(os.name != "nt"),
            )
        _log(f"started {name}")
        return True
    except Exception as e:
        _log(f"failed to start {name}: {e}")
        return False


def _load_state() -> dict:
    if not STATE_FILE.exists():
        return {}
    try:
        return json.loads(STATE_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _save_state(state: dict) -> None:
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(state, indent=2), encoding="utf-8")


def _queue_counts() -> tuple[int, int]:
    sys.path.insert(0, str(SPARK_DIR))
    from lib.queue import count_events
    from lib.pattern_detection.worker import get_pattern_backlog

    return count_events(), get_pattern_backlog()


def _bridge_heartbeat_age() -> Optional[float]:
    sys.path.insert(0, str(SPARK_DIR))
    from lib.bridge_cycle import bridge_heartbeat_age_s

    return bridge_heartbeat_age_s()


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--interval", type=int, default=60, help="seconds between checks")
    ap.add_argument("--max-queue", type=int, default=500, help="warn if queue exceeds this")
    ap.add_argument("--queue-warn-mins", type=int, default=5, help="minutes before warning")
    ap.add_argument("--bridge-stale-s", type=int, default=90, help="heartbeat stale threshold")
    ap.add_argument("--once", action="store_true", help="run one check and exit")
    ap.add_argument("--no-restart", action="store_true", help="only report, never restart")
    args = ap.parse_args()

    _ensure_log_dir()
    _log("watchdog started")

    state = _load_state()
    over_since = float(state.get("queue_over_since") or 0.0)
    last_warn = float(state.get("queue_last_warn") or 0.0)

    while True:
        # sparkd
        sparkd_ok = _http_ok("http://127.0.0.1:8787/health")
        if not sparkd_ok:
            if _process_exists("sparkd.py"):
                _log("sparkd unhealthy but process exists")
            elif not args.no_restart:
                _start_process("sparkd", [sys.executable, str(SPARK_DIR / "sparkd.py")])

        # dashboard
        dash_ok = _http_ok("http://127.0.0.1:8585/api/status")
        if not dash_ok:
            if _process_exists("dashboard.py"):
                _log("dashboard unhealthy but process exists")
            elif not args.no_restart:
                _start_process("dashboard", [sys.executable, str(SPARK_DIR / "dashboard.py")])

        # bridge_worker
        hb_age = _bridge_heartbeat_age()
        bridge_ok = hb_age is not None and hb_age <= args.bridge_stale_s
        if not bridge_ok:
            if _process_exists("bridge_worker.py"):
                _log("bridge_worker heartbeat stale but process exists")
            elif not args.no_restart:
                _start_process(
                    "bridge_worker",
                    [sys.executable, str(SPARK_DIR / "bridge_worker.py"), "--interval", "30"],
                )

        # queue pressure warning
        try:
            queue_count, backlog = _queue_counts()
            if queue_count > args.max_queue:
                now = time.time()
                if over_since <= 0:
                    over_since = now
                if now - over_since >= args.queue_warn_mins * 60:
                    if now - last_warn >= 60:
                        _log(f"queue high: {queue_count} events (backlog {backlog})")
                        last_warn = now
            else:
                over_since = 0.0
        except Exception as e:
            _log(f"queue check failed: {e}")

        state["queue_over_since"] = over_since
        state["queue_last_warn"] = last_warn
        _save_state(state)

        if args.once:
            break
        time.sleep(max(10, int(args.interval)))


if __name__ == "__main__":
    main()
