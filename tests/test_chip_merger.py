import json
from datetime import datetime, timedelta, timezone

from lib import chip_merger as cm


class _DummyCog:
    def add_insight(self, **_kwargs):
        return {"ok": True}

    def _generate_key(self, category, text):
        return f"{category.value}:{text[:10]}"


def _write_rows(path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row) + "\n")


def test_hash_is_stable_across_timestamps():
    first = cm._hash_insight("bench_core", "Prefer stable contracts in integrations")
    second = cm._hash_insight("bench_core", "Prefer stable contracts in integrations")
    assert first == second


def test_merge_skips_duplicate_content_in_same_run(tmp_path, monkeypatch):
    chip_dir = tmp_path / "chip_insights"
    state_file = tmp_path / "chip_merge_state.json"
    monkeypatch.setattr(cm, "CHIP_INSIGHTS_DIR", chip_dir)
    monkeypatch.setattr(cm, "MERGE_STATE_FILE", state_file)
    monkeypatch.setattr(cm, "get_cognitive_learner", lambda: _DummyCog())
    monkeypatch.setattr(cm, "record_exposures", lambda *args, **kwargs: 0)

    now = datetime.now(timezone.utc)
    rows = [
        {
            "chip_id": "bench_core",
            "content": "Use contract tests before broad refactors",
            "confidence": 0.9,
            "timestamp": (now - timedelta(seconds=1)).isoformat(),
            "captured_data": {"quality_score": {"total": 0.95}},
        },
        {
            "chip_id": "bench_core",
            "content": "Use contract tests before broad refactors",
            "confidence": 0.92,
            "timestamp": now.isoformat(),
            "captured_data": {"quality_score": {"total": 0.96}},
        },
    ]
    _write_rows(chip_dir / "bench_core.jsonl", rows)

    stats = cm.merge_chip_insights(limit=20, dry_run=False)

    assert stats["merged"] == 1
    assert stats["skipped_duplicate"] == 1


def test_low_quality_cooldown_suppresses_repeat_churn(tmp_path, monkeypatch):
    chip_dir = tmp_path / "chip_insights"
    state_file = tmp_path / "chip_merge_state.json"
    monkeypatch.setattr(cm, "CHIP_INSIGHTS_DIR", chip_dir)
    monkeypatch.setattr(cm, "MERGE_STATE_FILE", state_file)
    monkeypatch.setattr(cm, "get_cognitive_learner", lambda: _DummyCog())
    monkeypatch.setattr(cm, "record_exposures", lambda *args, **kwargs: 0)

    row = {
        "chip_id": "bench_core",
        "content": "vague weak note",
        "confidence": 0.9,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "captured_data": {"quality_score": {"total": 0.2}},
    }
    _write_rows(chip_dir / "bench_core.jsonl", [row])

    first = cm.merge_chip_insights(min_confidence=0.5, min_quality_score=0.7, limit=5, dry_run=False)
    second = cm.merge_chip_insights(min_confidence=0.5, min_quality_score=0.7, limit=5, dry_run=False)

    assert first["skipped_low_quality"] == 1
    assert second["skipped_low_quality"] == 0
    assert second["skipped_low_quality_cooldown"] == 1
