import json
import os
import time

from lib import runtime_hygiene as rh


def _touch(path, ts):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("{}", encoding="utf-8")
    os.utime(path, (ts, ts))


def test_cleanup_removes_stale_runtime_and_tmp_files(tmp_path):
    now = time.time()
    repo_root = tmp_path / "repo"
    runtime_dir = tmp_path / "spark"
    pid_file = repo_root / "scripts" / ".spark_pids.json"

    stale_runtime = runtime_dir / "bridge_worker_heartbeat.json"
    stale_tmp = repo_root / "tmp_chat_old.json"
    _touch(stale_runtime, now - (8 * 3600))
    _touch(stale_tmp, now - (30 * 3600))
    pid_file.parent.mkdir(parents=True, exist_ok=True)
    pid_file.write_text("{}", encoding="utf-8")

    stats = rh.cleanup_runtime_artifacts(
        repo_root=repo_root,
        runtime_dir=runtime_dir,
        pid_state_file=pid_file,
        now_ts=now,
    )

    assert stats["runtime_removed"] == 1
    assert stats["tmp_removed"] == 1
    assert stats["pid_state_removed"] == 1
    assert not stale_runtime.exists()
    assert not stale_tmp.exists()
    assert not pid_file.exists()


def test_cleanup_keeps_fresh_files(tmp_path, monkeypatch):
    now = time.time()
    repo_root = tmp_path / "repo"
    runtime_dir = tmp_path / "spark"
    pid_file = repo_root / "scripts" / ".spark_pids.json"

    fresh_runtime = runtime_dir / "bridge_worker_heartbeat.json"
    fresh_tmp = repo_root / "tmp_chat_payload.json"
    _touch(fresh_runtime, now - 120)
    _touch(fresh_tmp, now - 120)
    pid_file.parent.mkdir(parents=True, exist_ok=True)
    pid_file.write_text(json.dumps({"sparkd": 999999}), encoding="utf-8")

    monkeypatch.setattr(rh, "_pid_alive", lambda _pid: True)

    stats = rh.cleanup_runtime_artifacts(
        repo_root=repo_root,
        runtime_dir=runtime_dir,
        pid_state_file=pid_file,
        now_ts=now,
    )

    assert stats["runtime_removed"] == 0
    assert stats["tmp_removed"] == 0
    assert stats["pid_state_removed"] == 0
    assert fresh_runtime.exists()
    assert fresh_tmp.exists()
    assert pid_file.exists()


def test_cleanup_removes_pid_file_when_all_pids_dead(tmp_path, monkeypatch):
    now = time.time()
    repo_root = tmp_path / "repo"
    runtime_dir = tmp_path / "spark"
    pid_file = repo_root / "scripts" / ".spark_pids.json"
    pid_file.parent.mkdir(parents=True, exist_ok=True)
    pid_file.write_text(json.dumps({"sparkd": 123, "bridge": 456}), encoding="utf-8")

    monkeypatch.setattr(rh, "_pid_alive", lambda _pid: False)

    stats = rh.cleanup_runtime_artifacts(
        repo_root=repo_root,
        runtime_dir=runtime_dir,
        pid_state_file=pid_file,
        now_ts=now,
    )

    assert stats["pid_state_removed"] == 1
    assert not pid_file.exists()
