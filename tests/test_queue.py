import json
import time
from pathlib import Path

import lib.queue as queue


def _patch_queue_paths(tmp_path: Path, monkeypatch) -> None:
    queue_dir = tmp_path / "queue"
    monkeypatch.setattr(queue, "QUEUE_DIR", queue_dir)
    monkeypatch.setattr(queue, "EVENTS_FILE", queue_dir / "events.jsonl")
    monkeypatch.setattr(queue, "LOCK_FILE", queue_dir / ".queue.lock")


def test_quick_capture_and_read_recent_events(tmp_path, monkeypatch):
    _patch_queue_paths(tmp_path, monkeypatch)

    ok = queue.quick_capture(
        event_type=queue.EventType.USER_PROMPT,
        session_id="s1",
        data={"payload": {"text": "hello"}},
    )
    assert ok is True

    events = queue.read_recent_events(1)
    assert len(events) == 1
    assert events[0].event_type == queue.EventType.USER_PROMPT
    assert events[0].session_id == "s1"


def test_rotate_if_needed(tmp_path, monkeypatch):
    _patch_queue_paths(tmp_path, monkeypatch)
    monkeypatch.setattr(queue, "MAX_EVENTS", 4)

    queue.QUEUE_DIR.mkdir(parents=True, exist_ok=True)
    with queue.EVENTS_FILE.open("w", encoding="utf-8") as f:
        for i in range(6):
            event = queue.SparkEvent(
                event_type=queue.EventType.USER_PROMPT,
                session_id="s1",
                timestamp=time.time(),
                data={"i": i},
            )
            f.write(json.dumps(event.to_dict()) + "\n")

    rotated = queue.rotate_if_needed()
    assert rotated is True
    assert queue.count_events() == queue.MAX_EVENTS // 2
