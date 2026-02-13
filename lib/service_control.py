#!/usr/bin/env python3
"""Service control helpers for Spark daemons (sparkd, bridge_worker, dashboard, pulse, watchdog)."""

from __future__ import annotations

import json
import os
import signal
import subprocess
import sys
import time
from pathlib import Path
from typing import Optional
from urllib import request

from lib.ports import (
    DASHBOARD_STATUS_URL,
    DASHBOARD_URL,
    META_RALPH_HEALTH_URL,
    META_RALPH_URL,
    PULSE_DOCS_URL,
    PULSE_UI_URL,
    PULSE_URL,
    SPARKD_HEALTH_URL,
)


ROOT_DIR = Path(__file__).resolve().parents[1]
REPO_ENV_FILE = ROOT_DIR / ".env"


def _resolve_pulse_dir() -> Path:
    env_value = os.environ.get("SPARK_PULSE_DIR")
    if env_value:
        return Path(env_value).expanduser()

    candidates = [
        ROOT_DIR.parent / "vibeship-spark-pulse",
        Path.home() / "Desktop" / "vibeship-spark-pulse",
    ]
    for candidate in candidates:
        if (candidate / "app.py").exists():
            return candidate
    return candidates[0]


# External Spark Pulse directory (full-featured FastAPI app with neural visualization)
# This is the ONLY pulse that should run. No fallback to the primitive internal spark_pulse.py.
SPARK_PULSE_DIR = _resolve_pulse_dir()
STARTUP_READY_TIMEOUT_S = float(os.environ.get("SPARK_STARTUP_READY_TIMEOUT_S", "12"))
STARTUP_READY_POLL_S = float(os.environ.get("SPARK_STARTUP_READY_POLL_S", "0.4"))


def _get_pulse_command() -> list[str]:
    """Get the command to start Spark Pulse (external vibeship-spark-pulse only)."""
    import sys
    external_app = SPARK_PULSE_DIR / "app.py"
    if external_app.exists():
        return [sys.executable, str(external_app)]
    raise FileNotFoundError(
        f"Spark Pulse not found at {external_app}. "
        f"Clone vibeship-spark-pulse to {SPARK_PULSE_DIR} or set SPARK_PULSE_DIR env var."
    )


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


def _process_snapshot() -> list[tuple[int, str]]:
    if os.name == "nt":
        try:
            out = subprocess.check_output(
                [
                    "powershell",
                    "-NoProfile",
                    "-Command",
                    "Get-CimInstance Win32_Process | Select-Object ProcessId,CommandLine | ConvertTo-Json -Compress",
                ],
                text=True,
                errors="ignore",
            )
            data = json.loads(out) if out.strip() else []
            if isinstance(data, dict):
                data = [data]
            snapshot = []
            for row in data or []:
                try:
                    pid = int(row.get("ProcessId") or 0)
                except Exception:
                    pid = 0
                cmd = row.get("CommandLine") or ""
                if pid:
                    snapshot.append((pid, cmd))
            return snapshot
        except Exception:
            return []
    try:
        out = subprocess.check_output(
            ["ps", "-ax", "-o", "pid=,command="],
            text=True,
            errors="ignore",
        )
        snapshot = []
        for line in out.splitlines():
            parts = line.strip().split(None, 1)
            if not parts:
                continue
            try:
                pid = int(parts[0])
            except Exception:
                continue
            cmd = parts[1] if len(parts) > 1 else ""
            snapshot.append((pid, cmd))
        return snapshot
    except Exception:
        return []


def _cmd_matches(cmd: str, patterns: list[list[str]]) -> bool:
    for pattern in patterns:
        if pattern and all(k in cmd for k in pattern):
            return True
    return False


def _pulse_process_patterns() -> list[list[str]]:
    app_path = SPARK_PULSE_DIR / "app.py"
    app_str = str(app_path)
    patterns: list[list[str]] = [
        [SPARK_PULSE_DIR.name, "app.py"],
        ["vibeship-spark-pulse", "app.py"],
        [app_str],
    ]
    app_posix = app_str.replace("\\", "/")
    if app_posix != app_str:
        patterns.append([app_posix])

    deduped: list[list[str]] = []
    for pattern in patterns:
        if pattern and pattern not in deduped:
            deduped.append(pattern)
    return deduped


def _pid_matches(pid: Optional[int], patterns: list[list[str]], snapshot: Optional[list[tuple[int, str]]] = None) -> bool:
    if not pid:
        return False
    if snapshot is None:
        snapshot = _process_snapshot()
    for spid, cmd in snapshot:
        if spid != pid:
            continue
        if _cmd_matches(cmd, patterns):
            return True
    return False


def _pid_alive_fallback(pid: Optional[int], snapshot: Optional[list[tuple[int, str]]] = None) -> bool:
    """Fallback when command line matching is unavailable (avoid duplicate spawns)."""
    if not pid:
        return False
    if snapshot is None:
        snapshot = _process_snapshot()
    if not snapshot:
        return _pid_alive(pid)
    for spid, cmd in snapshot:
        if spid != pid:
            continue
        if not cmd:
            return _pid_alive(pid)
        return False
    return False


def _any_process_matches(patterns: list[list[str]], snapshot: Optional[list[tuple[int, str]]] = None) -> bool:
    if not patterns:
        return False
    if snapshot is None:
        snapshot = _process_snapshot()
    for _, cmd in snapshot:
        if _cmd_matches(cmd, patterns):
            return True
    return False


def _find_pids_by_patterns(patterns: list[list[str]], snapshot: Optional[list[tuple[int, str]]] = None) -> list[int]:
    if not patterns:
        return []
    if snapshot is None:
        snapshot = _process_snapshot()
    matches = []
    for pid, cmd in snapshot:
        if _cmd_matches(cmd, patterns):
            matches.append(pid)
    return matches


def _http_ok(url: str, timeout: float = 1.5) -> bool:
    try:
        req = request.Request(url, method="GET")
        with request.urlopen(req, timeout=timeout) as resp:
            return 200 <= resp.status < 300
    except Exception:
        return False


def _pulse_ok() -> bool:
    """Pulse is healthy only when both app docs and UI respond."""
    return _http_ok(PULSE_DOCS_URL, timeout=2.0) and _http_ok(PULSE_UI_URL, timeout=2.0)


def _bridge_heartbeat_age() -> Optional[float]:
    from lib.bridge_cycle import bridge_heartbeat_age_s

    return bridge_heartbeat_age_s()


def _scheduler_heartbeat_age() -> Optional[float]:
    from spark_scheduler import scheduler_heartbeat_age_s

    return scheduler_heartbeat_age_s()


def _load_repo_env(path: Path = REPO_ENV_FILE) -> dict[str, str]:
    """Load simple KEY=VALUE pairs from repo .env file.

    This avoids requiring python-dotenv for daemon startup paths.
    """
    if not path.exists():
        return {}
    out: dict[str, str] = {}
    try:
        for raw in path.read_text(encoding="utf-8", errors="replace").splitlines():
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            if line.lower().startswith("export "):
                line = line[7:].strip()
            if "=" not in line:
                continue
            key, value = line.split("=", 1)
            key = key.strip()
            if not key:
                continue
            val = value.strip()
            if len(val) >= 2 and ((val[0] == '"' and val[-1] == '"') or (val[0] == "'" and val[-1] == "'")):
                val = val[1:-1]
            out[key] = val
    except Exception:
        return {}
    return out


def _env_for_child(log_dir: Path) -> dict:
    env = os.environ.copy()
    # Import repo-level .env values for daemon processes (e.g., API keys/models).
    for k, v in _load_repo_env().items():
        env.setdefault(k, v)
    env.setdefault("PYTHONUNBUFFERED", "1")
    env.setdefault("PYTHONIOENCODING", "utf-8")
    env.setdefault("SPARK_LOG_DIR", str(log_dir))
    return env


def _start_process(name: str, args: list[str], cwd: Optional[Path] = None) -> Optional[int]:
    _, log_dir = _ensure_dirs()
    log_path = log_dir / f"{name}.log"
    env = _env_for_child(log_dir)

    creationflags = 0
    if os.name == "nt":
        # CREATE_NO_WINDOW (0x08000000) prevents console windows from opening
        # DETACHED_PROCESS alone is NOT enough on Windows
        CREATE_NO_WINDOW = 0x08000000
        creationflags = (
            getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
            | CREATE_NO_WINDOW
        )

    with open(log_path, "a", encoding="utf-8", errors="replace") as log_f:
        proc = subprocess.Popen(
            args,
            stdout=log_f,
            stderr=log_f,
            env=env,
            cwd=str(cwd) if cwd else None,
            creationflags=creationflags,
            start_new_session=(os.name != "nt"),
        )
    _write_pid(name, proc.pid)
    return proc.pid


def _is_service_ready(name: str, bridge_stale_s: int = 90) -> bool:
    if name == "sparkd":
        return _http_ok(SPARKD_HEALTH_URL)
    if name == "dashboard":
        return _http_ok(DASHBOARD_STATUS_URL)
    if name == "pulse":
        return _pulse_ok()
    if name == "meta_ralph":
        return _http_ok(META_RALPH_HEALTH_URL)
    if name == "bridge_worker":
        hb_age = _bridge_heartbeat_age()
        return hb_age is not None and hb_age <= bridge_stale_s
    if name == "scheduler":
        hb_age = _scheduler_heartbeat_age()
        return hb_age is not None and hb_age <= bridge_stale_s * 2
    if name == "watchdog":
        pid = _read_pid("watchdog")
        return _pid_alive(pid)
    return False


def _wait_for_service_ready(name: str, pid: Optional[int], bridge_stale_s: int = 90) -> bool:
    if not pid:
        return False

    # Services without HTTP endpoints should at least remain alive.
    if name in ("watchdog", "scheduler"):
        return _pid_alive(pid)

    deadline = time.time() + max(0.5, STARTUP_READY_TIMEOUT_S)
    while time.time() < deadline:
        if not _pid_alive(pid):
            return False
        if _is_service_ready(name, bridge_stale_s=bridge_stale_s):
            return True
        time.sleep(max(0.1, STARTUP_READY_POLL_S))

    return _is_service_ready(name, bridge_stale_s=bridge_stale_s)


def _terminate_pid(pid: int, timeout_s: float = 5.0) -> bool:
    if os.name == "nt":
        try:
            subprocess.run(
                ["taskkill", "/PID", str(pid), "/T"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                check=False,
            )
        except Exception:
            return False
        end = time.time() + timeout_s
        while time.time() < end:
            if not _pid_alive(pid):
                return True
            time.sleep(0.2)
        try:
            subprocess.run(
                ["taskkill", "/PID", str(pid), "/T", "/F"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                check=False,
            )
        except Exception:
            return False
        return not _pid_alive(pid)

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
    include_pulse: bool = True,
) -> dict[str, Optional[list[str]]]:
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
        "meta_ralph": [sys.executable, str(ROOT_DIR / "meta_ralph_dashboard.py")],
        "scheduler": [sys.executable, str(ROOT_DIR / "spark_scheduler.py")],
        "watchdog": [
            sys.executable,
            "-m",
            "spark_watchdog",
            "--interval",
            str(watchdog_interval),
        ],
    }
    if include_pulse:
        try:
            cmds["pulse"] = _get_pulse_command()
        except FileNotFoundError:
            cmds["pulse"] = None
    if bridge_query:
        cmds["bridge_worker"].extend(["--query", bridge_query])
    return cmds


def service_status(bridge_stale_s: int = 90, include_pulse_probe: bool = True) -> dict[str, dict]:
    sparkd_ok = _http_ok(SPARKD_HEALTH_URL)
    dash_ok = _http_ok(DASHBOARD_STATUS_URL)
    pulse_ok = _pulse_ok() if include_pulse_probe else False
    meta_ok = _http_ok(META_RALPH_HEALTH_URL)
    hb_age = _bridge_heartbeat_age()

    sched_hb_age = _scheduler_heartbeat_age()

    sparkd_pid = _read_pid("sparkd")
    dash_pid = _read_pid("dashboard")
    pulse_pid = _read_pid("pulse")
    meta_pid = _read_pid("meta_ralph")
    bridge_pid = _read_pid("bridge_worker")
    scheduler_pid = _read_pid("scheduler")
    watchdog_pid = _read_pid("watchdog")

    snapshot = _process_snapshot()
    sparkd_keys = [["-m sparkd"], ["sparkd.py"]]
    dash_keys = [["-m dashboard"], ["dashboard.py"]]
    pulse_keys = _pulse_process_patterns()
    meta_keys = [["meta_ralph_dashboard.py"]]
    bridge_keys = [["-m bridge_worker"], ["bridge_worker.py"]]
    scheduler_keys = [["spark_scheduler.py"]]
    watchdog_keys = [["-m spark_watchdog"], ["spark_watchdog.py"], ["scripts/watchdog.py"]]

    sparkd_running = (
        sparkd_ok
        or _pid_matches(sparkd_pid, sparkd_keys, snapshot)
        or _any_process_matches(sparkd_keys, snapshot)
        or _pid_alive_fallback(sparkd_pid, snapshot)
    )
    dash_running = (
        dash_ok
        or _pid_matches(dash_pid, dash_keys, snapshot)
        or _any_process_matches(dash_keys, snapshot)
        or _pid_alive_fallback(dash_pid, snapshot)
    )
    pulse_running = (
        pulse_ok
        or _pid_matches(pulse_pid, pulse_keys, snapshot)
        or _any_process_matches(pulse_keys, snapshot)
    )
    meta_running = (
        meta_ok
        or _pid_matches(meta_pid, meta_keys, snapshot)
        or _any_process_matches(meta_keys, snapshot)
        or _pid_alive_fallback(meta_pid, snapshot)
    )
    bridge_running = (
        (hb_age is not None and hb_age <= bridge_stale_s)
        or _pid_matches(bridge_pid, bridge_keys, snapshot)
        or _any_process_matches(bridge_keys, snapshot)
        or _pid_alive_fallback(bridge_pid, snapshot)
    )
    scheduler_running = (
        (sched_hb_age is not None and sched_hb_age <= bridge_stale_s * 2)
        or _pid_matches(scheduler_pid, scheduler_keys, snapshot)
        or _any_process_matches(scheduler_keys, snapshot)
        or _pid_alive_fallback(scheduler_pid, snapshot)
    )
    watchdog_running = (
        _pid_matches(watchdog_pid, watchdog_keys, snapshot)
        or _any_process_matches(watchdog_keys, snapshot)
        or _pid_alive_fallback(watchdog_pid, snapshot)
    )

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
        "pulse": {
            "running": pulse_running,
            "healthy": pulse_ok,
            "pid": pulse_pid,
        },
        "meta_ralph": {
            "running": meta_running,
            "healthy": meta_ok,
            "pid": meta_pid,
        },
        "bridge_worker": {
            "running": bridge_running,
            "heartbeat_age_s": hb_age,
            "pid": bridge_pid,
        },
        "scheduler": {
            "running": scheduler_running,
            "heartbeat_age_s": sched_hb_age,
            "pid": scheduler_pid,
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
    include_pulse: bool = True,
    include_meta_ralph: bool = True,
    include_watchdog: bool = True,
    bridge_stale_s: int = 90,
) -> dict[str, str]:
    cmds = _service_cmds(
        bridge_interval=bridge_interval,
        bridge_query=bridge_query,
        watchdog_interval=watchdog_interval,
        include_pulse=include_pulse,
    )
    statuses = service_status(bridge_stale_s=bridge_stale_s)
    results: dict[str, str] = {}

    order = ["sparkd", "bridge_worker", "scheduler", "dashboard", "pulse", "meta_ralph", "watchdog"]
    if not include_dashboard:
        order.remove("dashboard")
    if not include_pulse:
        order.remove("pulse")
    if not include_meta_ralph:
        order.remove("meta_ralph")
    if not include_watchdog:
        order.remove("watchdog")

    for name in order:
        current = statuses.get(name, {})
        if current.get("running"):
            results[name] = "already_running"
            continue
        cmd = cmds.get(name)
        if not cmd:
            results[name] = "unavailable"
            continue
        process_cwd = SPARK_PULSE_DIR if name == "pulse" else ROOT_DIR
        pid = _start_process(name, cmd, cwd=process_cwd)
        if not pid:
            results[name] = "failed"
            continue
        ready = _wait_for_service_ready(name, pid, bridge_stale_s=bridge_stale_s)
        results[name] = f"started:{pid}" if ready else f"started_unhealthy:{pid}"

    return results


def ensure_services(
    bridge_interval: int = 30,
    bridge_query: Optional[str] = None,
    watchdog_interval: int = 60,
    include_dashboard: bool = True,
    include_pulse: bool = True,
    include_meta_ralph: bool = True,
    include_watchdog: bool = True,
    bridge_stale_s: int = 90,
) -> dict[str, str]:
    return start_services(
        bridge_interval=bridge_interval,
        bridge_query=bridge_query,
        watchdog_interval=watchdog_interval,
        include_dashboard=include_dashboard,
        include_pulse=include_pulse,
        include_meta_ralph=include_meta_ralph,
        include_watchdog=include_watchdog,
        bridge_stale_s=bridge_stale_s,
    )


def stop_services() -> dict[str, str]:
    results: dict[str, str] = {}
    snapshot = _process_snapshot()
    for name in ["watchdog", "meta_ralph", "pulse", "dashboard", "scheduler", "bridge_worker", "sparkd"]:
        pid = _read_pid(name)
        patterns = {
            "sparkd": [["-m sparkd"], ["sparkd.py"]],
            "bridge_worker": [["-m bridge_worker"], ["bridge_worker.py"]],
            "scheduler": [["spark_scheduler.py"]],
            "dashboard": [["-m dashboard"], ["dashboard.py"]],
            "pulse": _pulse_process_patterns(),
            "meta_ralph": [["meta_ralph_dashboard.py"]],
            "watchdog": [["-m spark_watchdog"], ["spark_watchdog.py"], ["scripts/watchdog.py"]],
        }.get(name, [])

        matched_pids = _find_pids_by_patterns(patterns, snapshot)
        killed_any = False

        if matched_pids:
            for mpid in matched_pids:
                if _terminate_pid(mpid):
                    killed_any = True
            results[name] = "stopped" if killed_any else "failed"
        elif pid and _pid_matches(pid, patterns, snapshot):
            if _pid_alive(pid):
                ok = _terminate_pid(pid)
                killed_any = ok
                results[name] = "stopped" if ok else "failed"
            else:
                results[name] = "not_running"
        else:
            results[name] = "pid_mismatch" if pid else "no_pid"

        try:
            _pid_file(name).unlink(missing_ok=True)
        except Exception:
            pass
    return results


def format_status_lines(status: dict[str, dict], bridge_stale_s: int = 90) -> list[str]:
    lines: list[str] = []
    sparkd = status.get("sparkd", {})
    dash = status.get("dashboard", {})
    pulse = status.get("pulse", {})
    meta = status.get("meta_ralph", {})
    bridge = status.get("bridge_worker", {})
    scheduler = status.get("scheduler", {})
    watchdog = status.get("watchdog", {})

    lines.append(
        f"[spark] sparkd: {'RUNNING' if sparkd.get('running') else 'STOPPED'}"
        + (" (healthy)" if sparkd.get("healthy") else "")
    )
    lines.append(
        f"[spark] dashboard: {'RUNNING' if dash.get('running') else 'STOPPED'}"
        + (" (healthy)" if dash.get("healthy") else "")
    )
    lines.append(
        f"[spark] pulse: {'RUNNING' if pulse.get('running') else 'STOPPED'}"
        + (" (healthy)" if pulse.get("healthy") else "")
    )
    lines.append(
        f"[spark] meta_ralph: {'RUNNING' if meta.get('running') else 'STOPPED'}"
        + (" (healthy)" if meta.get("healthy") else "")
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
    sched_hb = scheduler.get("heartbeat_age_s")
    if sched_hb is None:
        if scheduler.get("running"):
            lines.append("[spark] scheduler: RUNNING (no heartbeat)")
        else:
            lines.append("[spark] scheduler: STOPPED")
    else:
        sched_label = "RUNNING" if sched_hb <= bridge_stale_s * 2 else "STALE"
        lines.append(f"[spark] scheduler: {sched_label} (last {int(sched_hb)}s ago)")
    lines.append(
        f"[spark] watchdog: {'RUNNING' if watchdog.get('running') else 'STOPPED'}"
    )
    log_dir = status.get("log_dir")
    if log_dir:
        lines.append(f"[spark] logs: {log_dir}")
    lines.append(
        f"[spark] pulse_dir: {SPARK_PULSE_DIR}"
        + ("" if (SPARK_PULSE_DIR / "app.py").exists() else " (app.py missing)")
    )
    lines.append(f"Dashboard: {DASHBOARD_URL}")
    lines.append(f"Spark Pulse: {PULSE_URL}")
    lines.append(f"Meta-Ralph: {META_RALPH_URL}")
    return lines
