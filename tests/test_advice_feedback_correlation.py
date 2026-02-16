from __future__ import annotations

import json

import lib.advice_feedback as af


def _patch_paths(monkeypatch, tmp_path):
    monkeypatch.setattr(af, "REQUESTS_FILE", tmp_path / "advice_feedback_requests.jsonl")
    monkeypatch.setattr(af, "FEEDBACK_FILE", tmp_path / "advice_feedback.jsonl")
    monkeypatch.setattr(af, "STATE_FILE", tmp_path / "advice_feedback_state.json")


def test_record_advice_request_requires_trace_id(monkeypatch, tmp_path):
    _patch_paths(monkeypatch, tmp_path)

    ok = af.record_advice_request(
        session_id="s1",
        tool="Edit",
        advice_ids=["a1"],
        trace_id=None,
    )

    assert ok is False
    assert not af.REQUESTS_FILE.exists()


def test_record_advice_request_writes_correlation_fields(monkeypatch, tmp_path):
    _patch_paths(monkeypatch, tmp_path)

    ok = af.record_advice_request(
        session_id="s1",
        tool="Edit",
        advice_ids=["a1", "a2"],
        trace_id="trace-1",
        min_interval_s=0,
    )

    assert ok is True
    row = json.loads(af.REQUESTS_FILE.read_text(encoding="utf-8").splitlines()[-1])
    assert row["schema_version"] == af.CORRELATION_SCHEMA_VERSION
    assert row["trace_id"] == "trace-1"
    assert isinstance(row.get("run_id"), str) and row["run_id"]
    assert row["primary_advisory_id"] == "a1"
    assert isinstance(row.get("advisory_group_key"), str) and row["advisory_group_key"]
    assert row["session_kind"] == "other"
    assert row["is_subagent"] is False
    assert row["depth_hint"] >= 1


def test_record_feedback_uses_deterministic_run_id_when_missing(monkeypatch, tmp_path):
    _patch_paths(monkeypatch, tmp_path)

    ok1 = af.record_feedback(
        advice_ids=["a1", "a2"],
        tool="Read",
        helpful=True,
        followed=True,
        trace_id="trace-abc",
    )
    ok2 = af.record_feedback(
        advice_ids=["a1", "a2"],
        tool="Read",
        helpful=False,
        followed=True,
        trace_id="trace-abc",
    )

    assert ok1 and ok2
    rows = [json.loads(x) for x in af.FEEDBACK_FILE.read_text(encoding="utf-8").splitlines()]
    assert len(rows) == 2
    assert rows[0]["schema_version"] == af.CORRELATION_SCHEMA_VERSION
    assert rows[0]["run_id"] == rows[1]["run_id"]
    assert rows[0]["advisory_group_key"] == rows[1]["advisory_group_key"]


def test_record_feedback_includes_subagent_lineage(monkeypatch, tmp_path):
    _patch_paths(monkeypatch, tmp_path)

    ok = af.record_feedback(
        advice_ids=["a1"],
        tool="Edit",
        helpful=True,
        followed=True,
        trace_id="trace-xyz",
        session_id="agent:spark-ship:subagent:abc-123",
    )

    assert ok is True
    row = json.loads(af.FEEDBACK_FILE.read_text(encoding="utf-8").splitlines()[-1])
    assert row["session_kind"] == "subagent"
    assert row["is_subagent"] is True
    assert row["depth_hint"] == 2
    assert row["session_tree_key"] == "agent:spark-ship"
