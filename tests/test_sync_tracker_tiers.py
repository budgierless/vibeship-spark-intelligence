from __future__ import annotations

import lib.sync_tracker as sync_tracker_module


def test_get_stats_splits_core_and_optional_health(monkeypatch, tmp_path):
    monkeypatch.setattr(sync_tracker_module, "SYNC_STATS_FILE", tmp_path / "sync_stats.json")
    tracker = sync_tracker_module.SyncTracker()
    tracker.record_full_sync(
        {
            "openclaw": "written",
            "exports": "written",
            "cursor": "error",
        },
        items_per_adapter=3,
    )

    stats = tracker.get_stats()
    assert stats["core_ok"] == 2
    assert stats["core_error"] == 0
    assert stats["optional_error"] >= 1
    assert stats["core_healthy"] is True


def test_core_health_fails_when_core_adapter_errors(monkeypatch, tmp_path):
    monkeypatch.setattr(sync_tracker_module, "SYNC_STATS_FILE", tmp_path / "sync_stats.json")
    tracker = sync_tracker_module.SyncTracker()
    tracker.record_full_sync(
        {
            "openclaw": "error",
            "exports": "written",
        },
        items_per_adapter=2,
    )

    stats = tracker.get_stats()
    assert stats["core_error"] == 1
    assert stats["core_healthy"] is False
