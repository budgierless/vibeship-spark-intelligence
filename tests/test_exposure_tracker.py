import json
import time

from lib import exposure_tracker as et


def _read_jsonl(path):
    rows = []
    if not path.exists():
        return rows
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            rows.append(json.loads(line))
    return rows


def test_sync_context_dedupes_recent_signatures(tmp_path, monkeypatch):
    exposures_file = tmp_path / "exposures.jsonl"
    last_file = tmp_path / "last_exposure.json"
    monkeypatch.setattr(et, "EXPOSURES_FILE", exposures_file)
    monkeypatch.setattr(et, "LAST_EXPOSURE_FILE", last_file)

    now = time.time()
    seed = {
        "ts": now - 10,
        "source": "sync_context",
        "insight_key": "ins:1",
        "category": "reasoning",
        "text": "Use strict parser for stable outputs",
        "session_id": "s1",
        "trace_id": "t1",
    }
    exposures_file.write_text(json.dumps(seed) + "\n", encoding="utf-8")

    written = et.record_exposures(
        source="sync_context",
        items=[{"insight_key": "ins:1", "category": "reasoning", "text": "Use strict parser for stable outputs"}],
        session_id="s2",
        trace_id="t2",
    )
    rows = _read_jsonl(exposures_file)

    assert written == 0
    assert len(rows) == 1


def test_sync_context_project_caps_write_volume(tmp_path, monkeypatch):
    exposures_file = tmp_path / "exposures.jsonl"
    last_file = tmp_path / "last_exposure.json"
    monkeypatch.setattr(et, "EXPOSURES_FILE", exposures_file)
    monkeypatch.setattr(et, "LAST_EXPOSURE_FILE", last_file)

    items = []
    for i in range(10):
        items.append(
            {
                "insight_key": f"project:milestone:{i}",
                "category": "project_milestone",
                "text": f"milestone {i}",
            }
        )

    written = et.record_exposures(
        source="sync_context:project",
        items=items,
        session_id="s1",
        trace_id="t1",
    )
    rows = _read_jsonl(exposures_file)

    assert written == 4
    assert len(rows) == 4
    assert all(r.get("source") == "sync_context:project" for r in rows)


def test_unthrottled_source_keeps_all_items(tmp_path, monkeypatch):
    exposures_file = tmp_path / "exposures.jsonl"
    last_file = tmp_path / "last_exposure.json"
    monkeypatch.setattr(et, "EXPOSURES_FILE", exposures_file)
    monkeypatch.setattr(et, "LAST_EXPOSURE_FILE", last_file)

    items = [{"insight_key": f"warn:{i}", "category": "warning", "text": f"warning {i}"} for i in range(7)]
    written = et.record_exposures(
        source="spark_context:warnings",
        items=items,
        session_id="s1",
        trace_id="t1",
    )
    rows = _read_jsonl(exposures_file)

    assert written == 7
    assert len(rows) == 7


def test_record_exposures_redacts_secrets(tmp_path, monkeypatch):
    exposures_file = tmp_path / "exposures.jsonl"
    last_file = tmp_path / "last_exposure.json"
    monkeypatch.setattr(et, "EXPOSURES_FILE", exposures_file)
    monkeypatch.setattr(et, "LAST_EXPOSURE_FILE", last_file)

    text = "Authorization: Bearer API_TOKEN_SANDBOX api_key=api_key_placeholder sk-REDACTED_TEST"
    written = et.record_exposures(
        source="spark_context:warnings",
        items=[{"insight_key": "k1", "category": "warning", "text": text}],
        session_id="s1",
        trace_id="t1",
    )

    assert written == 1
    rows = _read_jsonl(exposures_file)
    assert len(rows) == 1
    saved = rows[0]["text"]
    assert "API_TOKEN_SANDBOX" not in saved
    assert "api_key_placeholder" not in saved
    assert "sk-REDACTED" not in saved
    assert "[REDACTED" in saved

