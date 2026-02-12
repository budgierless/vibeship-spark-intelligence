"""Runtime artifact cleanup helpers for bridge cycles."""

from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any, Dict, List, Optional


RUNTIME_FILE_TTLS = {
    "bridge_worker_heartbeat.json": 6 * 3600,
    "scheduler_heartbeat.json": 6 * 3600,
    "sparkd_heartbeat.json": 6 * 3600,
}
TMP_FILE_GLOBS = (
    "tmp_chat_*.json",
    "tmp_chat_*.py",
    "tmp_*.tmp",
)
TMP_FILE_MAX_AGE_S = 24 * 3600
PID_KEYS = ("sparkd", "bridge", "tailer", "pulse")


def _pid_alive(pid: int) -> bool:
    if pid <= 0:
        return False
    try:
        os.kill(pid, 0)
        return True
    except PermissionError:
        return True
    except OSError:
        return False
    except Exception:
        return False


def _safe_unlink(path: Path) -> bool:
    try:
        path.unlink()
        return True
    except Exception:
        return False


def cleanup_runtime_artifacts(
    *,
    repo_root: Optional[Path] = None,
    runtime_dir: Optional[Path] = None,
    pid_state_file: Optional[Path] = None,
    now_ts: Optional[float] = None,
) -> Dict[str, Any]:
    """Prune stale runtime files and temporary artifacts."""
    now = float(now_ts or time.time())
    root = Path(repo_root) if repo_root else Path(__file__).resolve().parent.parent
    spark_dir = Path(runtime_dir) if runtime_dir else Path.home() / ".spark"
    pid_file = Path(pid_state_file) if pid_state_file else (root / "scripts" / ".spark_pids.json")

    removed_runtime: List[str] = []
    removed_tmp: List[str] = []
    removed_pid_state = False

    for name, ttl_s in RUNTIME_FILE_TTLS.items():
        path = spark_dir / name
        if not path.exists():
            continue
        try:
            age_s = now - path.stat().st_mtime
        except Exception:
            continue
        if age_s <= float(ttl_s):
            continue
        if _safe_unlink(path):
            removed_runtime.append(path.name)

    if pid_file.exists():
        remove_pid_file = False
        try:
            data = json.loads(pid_file.read_text(encoding="utf-8"))
            pids = [
                int(data.get(key))
                for key in PID_KEYS
                if isinstance(data.get(key), int) or str(data.get(key, "")).isdigit()
            ]
            if not pids:
                remove_pid_file = True
            else:
                remove_pid_file = not any(_pid_alive(int(pid)) for pid in pids)
        except Exception:
            remove_pid_file = True
        if remove_pid_file and _safe_unlink(pid_file):
            removed_pid_state = True

    for pattern in TMP_FILE_GLOBS:
        for path in root.glob(pattern):
            if not path.is_file():
                continue
            try:
                age_s = now - path.stat().st_mtime
            except Exception:
                continue
            if age_s <= TMP_FILE_MAX_AGE_S:
                continue
            if _safe_unlink(path):
                removed_tmp.append(path.name)

    return {
        "runtime_removed": len(removed_runtime),
        "tmp_removed": len(removed_tmp),
        "pid_state_removed": int(removed_pid_state),
        "removed_runtime_files": removed_runtime[:10],
        "removed_tmp_files": removed_tmp[:10],
    }
