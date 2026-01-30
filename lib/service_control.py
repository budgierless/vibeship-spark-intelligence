#!/usr/bin/env python3
"""Service control helpers for Spark daemons (sparkd, bridge_worker, dashboard, watchdog)."""

from __future__ import annotations

import os
import signal
import subprocess
import sys
import time
from pathlib import Path
from typing import Optional
from urllib import request


SPARKD_URL = "http://127.0.0.1:8787/health"
DASHBOARD_URL = "http://127.0.0.1:8585/api/status"


def _pid_dir() -> Path:
    return Path.home() / ".spark" / "pids"


def _log_dir() -> Path:
    env_dir = os.environ.get("SPARK_LOG_DIR")
    if env_dir:
        return Path(env_dir).expanduser()
    return Path.home() / ".spark" / "logs"


def _ensure_dirs() -> tuple[Path, Path]:
    pid_dir = _pid_dir()
    log_dir = _log_dir()
    pid_dir.mkdir(parents=True, exist_ok=True)
    log_dir.mkdir(parents=True, exist_ok=True)
    return pid_dir, log_dir


def _pid_file(name: str) -> Path:
    return _pid_dir() / f"{name}.pid"


def _read_pid(name: str) -> Optional[int]:
    try:
        return int(_pid_file(name).read_text(encoding="utf-8").strip())
    except Exception:
        return None


def _write_pid(name: str, pid: int) -> None:
    _pid_file(name).write_text(str(pid), encoding="utf-8")


def _pid_alive(pid: Optional[int]) -> bool:
    if not pid:
        return False
    if os.name == "nt":
        try:
            out = subprocess.check_output(
                ["tasklist", "/FI", f"PID eq {pid}"],
                text=True,
                errors="ignore",
            )
            return str(pid) in out
        except Exception:
            return False
    try:
        os.kill(pid, 0)
        return True
    except PermissionError:
        return True
    except Exception:
        return False


def _http_ok(url: str, timeout: float = 1.5) -> bool:
    try:
        req = request.Request(url, method="GET")
        with request.urlopen(req, timeout=timeout) as resp:
            return 200 <= resp.status < 300
    except Exception:
        return False


def _bridge_heartbeat_age() -> Optional[float]:
    from lib.bridge_cycle import bridge_heartbeat_age_s

    return bridge_heartbeat_age_s()


def _env_for_child(log_dir: Path) -> dict:
    env = os.environ.copy()
    env.setdefault("PYTHONUNBUFFERED", "1")
    env.setdefault("PYTHONIOENCODING", "utf-8")
    env.setdefault("SPARK_LOG_DIR", str(log_dir))
    return env


def _start_process(name: str, args: list[str]) -> Optional[int]:
    _, log_dir = _ensure_dirs()
    log_path = log_dir / f"{name}.log"
    env = _env_for_child(log_dir)

    creationflags = 0
    if os.name == "nt":
        creationflags = (
            getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
            | getattr(subprocess, "DETACHED_PROCESS", 0)
        )

    with open(log_path, "a", encoding="utf-8", errors="replace") as log_f:
        proc = subprocess.Popen(
            args,
            stdout=log_f,
            stderr=log_f,
            env=env,
            creationflags=creationflags,
            start_new_session=(os.name != "nt"),
        )
    _write_pid(name, proc.pid)
    return proc.pid


def _terminate_pid(pid: int, timeout_s: float = 5.0) -> bool:
    if os.name == "nt":
        try:
            subprocess.run(
                ["taskkill", "/PID", str(pid), "/T", "/F"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                check=False,
            )
            return True
        except Exception:
            return False

    try:
        os.kill(pid, signal.SIGTERM)
    except Exception:
        return False

    end = time.time() + timeout_s
    while time.time() < end:
        if not _pid_alive(pid):
            return True
        time.sleep(0.2)
    return not _pid_alive(pid)


def _service_cmds(
    bridge_interval: int = 30,
    bridge_query: Optional[str] = None,
    watchdog_interval: int = 60,
) -> dict[str, list[str]]:
    cmds = {
        "sparkd": [sys.executable, "-m", "sparkd"],
        "bridge_worker": [
            sys.executable,
            "-m",
            "bridge_worker",
            "--interval",
            str(bridge_interval),
        ],
        "dashboard": [sys.executable, "-m", "dashboard"],
        "watchdog": [
            sys.executable,
            "-m",
            "spark_watchdog",
            "--interval",
            str(watchdog_interval),
        ],
    }
    if bridge_query:
        cmds["bridge_worker"].extend(["--query", bridge_query])
    return cmds


def service_status(bridge_stale_s: int = 90) -> dict[str, dict]:
    sparkd_ok = _http_ok(SPARKD_URL)
    dash_ok = _http_ok(DASHBOARD_URL)
    hb_age = _bridge_heartbeat_age()

    sparkd_pid = _read_pid("sparkd")
    dash_pid = _read_pid("dashboard")
    bridge_pid = _read_pid("bridge_worker")
    watchdog_pid = _read_pid("watchdog")

    sparkd_running = sparkd_ok or _pid_alive(sparkd_pid)
    dash_running = dash_ok or _pid_alive(dash_pid)
    bridge_running = (hb_age is not None and hb_age <= bridge_stale_s) or _pid_alive(bridge_pid)
    watchdog_running = _pid_alive(watchdog_pid)

    return {
        "sparkd": {
            "running": sparkd_running,
            "healthy": sparkd_ok,
            "pid": sparkd_pid,
        },
        "dashboard": {
            "running": dash_running,
            "healthy": dash_ok,
            "pid": dash_pid,
        },
        "bridge_worker": {
            "running": bridge_running,
            "heartbeat_age_s": hb_age,
            "pid": bridge_pid,
        },
        "watchdog": {
            "running": watchdog_running,
            "pid": watchdog_pid,
        },
        "log_dir": str(_log_dir()),
    }


def start_services(
    bridge_interval: int = 30,
    bridge_query: Optional[str] = None,
    watchdog_interval: int = 60,
    include_dashboard: bool = True,
    include_watchdog: bool = True,
    bridge_stale_s: int = 90,
) -> dict[str, str]:
    cmds = _service_cmds(
        bridge_interval=bridge_interval,
        bridge_query=bridge_query,
        watchdog_interval=watchdog_interval,
    )
    statuses = service_status(bridge_stale_s=bridge_stale_s)
    results: dict[str, str] = {}

    order = ["sparkd", "bridge_worker", "dashboard", "watchdog"]
    if not include_dashboard:
        order.remove("dashboard")
    if not include_watchdog:
        order.remove("watchdog")

    for name in order:
        current = statuses.get(name, {})
        if current.get("running"):
            results[name] = "already_running"
            continue
        pid = _start_process(name, cmds[name])
        results[name] = f"started:{pid}" if pid else "failed"

    return results


def ensure_services(
    bridge_interval: int = 30,
    bridge_query: Optional[str] = None,
    watchdog_interval: int = 60,
    include_dashboard: bool = True,
    include_watchdog: bool = True,
    bridge_stale_s: int = 90,
) -> dict[str, str]:
    return start_services(
        bridge_interval=bridge_interval,
        bridge_query=bridge_query,
        watchdog_interval=watchdog_interval,
        include_dashboard=include_dashboard,
        include_watchdog=include_watchdog,
        bridge_stale_s=bridge_stale_s,
    )


def stop_services() -> dict[str, str]:
    results: dict[str, str] = {}
    for name in ["watchdog", "dashboard", "bridge_worker", "sparkd"]:
        pid = _read_pid(name)
        if not pid:
            results[name] = "no_pid"
            continue
        if _pid_alive(pid):
            ok = _terminate_pid(pid)
            results[name] = "stopped" if ok else "failed"
        else:
            results[name] = "not_running"
        try:
            _pid_file(name).unlink(missing_ok=True)
        except Exception:
            pass
    return results


def format_status_lines(status: dict[str, dict], bridge_stale_s: int = 90) -> list[str]:
    lines: list[str] = []
    sparkd = status.get("sparkd", {})
    dash = status.get("dashboard", {})
    bridge = status.get("bridge_worker", {})
    watchdog = status.get("watchdog", {})

    lines.append(
        f"[spark] sparkd: {'RUNNING' if sparkd.get('running') else 'STOPPED'}"
        + (" (healthy)" if sparkd.get("healthy") else "")
    )
    lines.append(
        f"[spark] dashboard: {'RUNNING' if dash.get('running') else 'STOPPED'}"
        + (" (healthy)" if dash.get("healthy") else "")
    )
    hb_age = bridge.get("heartbeat_age_s")
    if hb_age is None:
        if bridge.get("running"):
            lines.append("[spark] bridge_worker: RUNNING (no heartbeat)")
        else:
            lines.append("[spark] bridge_worker: UNKNOWN (no heartbeat)")
    else:
        status_label = "RUNNING" if hb_age <= bridge_stale_s else "STALE"
        lines.append(f"[spark] bridge_worker: {status_label} (last {int(hb_age)}s ago)")
    lines.append(
        f"[spark] watchdog: {'RUNNING' if watchdog.get('running') else 'STOPPED'}"
    )
    log_dir = status.get("log_dir")
    if log_dir:
        lines.append(f"[spark] logs: {log_dir}")
    lines.append("Dashboard: http://127.0.0.1:8585")
    return lines
