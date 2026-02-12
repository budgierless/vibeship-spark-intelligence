from __future__ import annotations

from types import SimpleNamespace

from lib import advisory_engine


def test_advice_rows_include_proof_refs_and_evidence_hash():
    item = SimpleNamespace(
        advice_id="aid-1",
        insight_key="reasoning:k1",
        text="Run focused tests after edit.",
        confidence=0.8,
        source="cognitive",
        context_match=0.7,
        reason="Recent failures on the same flow.",
    )

    rows = advisory_engine._advice_to_rows_with_proof([item], trace_id="trace-123")
    assert len(rows) == 1
    row = rows[0]
    assert row["proof_refs"]["trace_id"] == "trace-123"
    assert row["proof_refs"]["insight_key"] == "reasoning:k1"
    assert row["proof_refs"]["source"] == "cognitive"
    assert row["evidence_hash"]


def test_advice_rows_wrapper_works_without_trace_id():
    item = SimpleNamespace(
        advice_id="aid-2",
        insight_key="context:k2",
        text="Validate payload contract before merge.",
        confidence=0.6,
        source="advisor",
        context_match=0.5,
        reason="",
    )

    rows = advisory_engine._advice_to_rows([item])
    assert len(rows) == 1
    assert "trace_id" not in rows[0]["proof_refs"]
    assert rows[0]["proof_refs"]["advice_id"] == "aid-2"


def test_diagnostics_envelope_has_session_scope_and_provider():
    bundle = {
        "memory_absent_declared": False,
        "sources": {"cognitive": {"count": 2}, "eidos": {"count": 0}},
        "missing_sources": ["eidos"],
    }
    env = advisory_engine._diagnostics_envelope(
        session_id="session-1",
        trace_id="trace-1",
        route="packet_exact",
        session_context_key="ctx-1",
        scope="session",
        memory_bundle=bundle,
    )

    assert env["session_id"] == "session-1"
    assert env["trace_id"] == "trace-1"
    assert env["scope"] == "session"
    assert env["provider_path"] == "packet_store"
    assert env["source_counts"]["cognitive"] == 2
    assert "eidos" in env["missing_sources"]


def test_ensure_actionability_appends_command_when_missing(monkeypatch):
    monkeypatch.setattr(advisory_engine, "ACTIONABILITY_ENFORCE", True)
    meta = advisory_engine._ensure_actionability(
        "Validate auth inputs before changes.",
        "Edit",
        "build_delivery",
    )
    assert meta["added"] is True
    assert "`python -m pytest -q`" in meta["text"]


def test_ensure_actionability_keeps_existing_command(monkeypatch):
    monkeypatch.setattr(advisory_engine, "ACTIONABILITY_ENFORCE", True)
    meta = advisory_engine._ensure_actionability(
        "Run focused checks now: `python -m pytest -q`.",
        "Edit",
        "build_delivery",
    )
    assert meta["added"] is False


def test_delivery_badge_live_and_stale_states():
    now = 2000.0
    live = advisory_engine._derive_delivery_badge(
        [{"ts": 1995.0, "event": "emitted", "delivery_mode": "live"}],
        now_ts=now,
        stale_after_s=30.0,
    )
    stale = advisory_engine._derive_delivery_badge(
        [{"ts": 1500.0, "event": "emitted", "delivery_mode": "live"}],
        now_ts=now,
        stale_after_s=30.0,
    )
    assert live["state"] == "live"
    assert stale["state"] == "stale"


def test_engine_config_exposes_packet_fallback_flag(monkeypatch):
    monkeypatch.setattr(advisory_engine, "PACKET_FALLBACK_EMIT_ENABLED", False)
    advisory_engine.apply_engine_config({"packet_fallback_emit_enabled": True})
    cfg = advisory_engine.get_engine_config()
    assert cfg["packet_fallback_emit_enabled"] is True
