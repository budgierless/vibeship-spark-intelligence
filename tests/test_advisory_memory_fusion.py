from __future__ import annotations

import json

from lib import advisory_memory_fusion as fusion


def test_memory_bundle_includes_available_sources(monkeypatch):
    monkeypatch.setattr(fusion, "_collect_cognitive", lambda limit=6: [{"source": "cognitive", "text": "x", "confidence": 0.8, "created_at": 1.0}])
    monkeypatch.setattr(fusion, "_collect_eidos", lambda intent_text, limit=5: [{"source": "eidos", "text": "y", "confidence": 0.7, "created_at": 2.0}])
    monkeypatch.setattr(fusion, "_collect_chips", lambda limit=6: [])
    monkeypatch.setattr(fusion, "_collect_outcomes", lambda intent_text, limit=6: [])
    monkeypatch.setattr(fusion, "_collect_orchestration", lambda limit=5: [])
    monkeypatch.setattr(fusion, "_collect_mind", lambda intent_text, limit=4: [{"source": "mind", "text": "z", "confidence": 0.6, "created_at": 3.0}])

    bundle = fusion.build_memory_bundle(
        session_id="s1",
        intent_text="auth work",
        intent_family="auth_security",
        tool_name="Edit",
        include_mind=True,
    )

    assert bundle["evidence_count"] == 3
    assert bundle["memory_absent_declared"] is False
    assert bundle["sources"]["cognitive"]["count"] == 1
    assert bundle["sources"]["eidos"]["count"] == 1
    assert bundle["sources"]["mind"]["count"] == 1


def test_memory_bundle_marks_missing_source_observable(monkeypatch):
    monkeypatch.setattr(fusion, "_collect_cognitive", lambda limit=6: [])
    monkeypatch.setattr(fusion, "_collect_eidos", lambda intent_text, limit=5: [])
    monkeypatch.setattr(fusion, "_collect_chips", lambda limit=6: [])
    monkeypatch.setattr(fusion, "_collect_outcomes", lambda intent_text, limit=6: [])
    monkeypatch.setattr(fusion, "_collect_orchestration", lambda limit=5: (_ for _ in ()).throw(RuntimeError("boom")))

    bundle = fusion.build_memory_bundle(
        session_id="s1",
        intent_text="unknown",
        intent_family="emergent_other",
        tool_name="Read",
        include_mind=False,
    )

    assert "orchestration" in bundle["missing_sources"]
    assert bundle["sources"]["orchestration"]["available"] is False
    assert bundle["sources"]["orchestration"]["error"]


def test_memory_bundle_declares_absent_when_no_evidence(monkeypatch):
    monkeypatch.setattr(fusion, "_collect_cognitive", lambda limit=6: [])
    monkeypatch.setattr(fusion, "_collect_eidos", lambda intent_text, limit=5: [])
    monkeypatch.setattr(fusion, "_collect_chips", lambda limit=6: [])
    monkeypatch.setattr(fusion, "_collect_outcomes", lambda intent_text, limit=6: [])
    monkeypatch.setattr(fusion, "_collect_orchestration", lambda limit=5: [])

    bundle = fusion.build_memory_bundle(
        session_id="s1",
        intent_text="",
        intent_family="emergent_other",
        tool_name="Read",
    )

    assert bundle["evidence_count"] == 0
    assert bundle["memory_absent_declared"] is True


def test_memory_bundle_filters_tool_error_noise(monkeypatch):
    monkeypatch.setattr(
        fusion,
        "_collect_cognitive",
        lambda limit=6: [
            {"source": "cognitive", "text": "I struggle with tool_49_error tasks", "confidence": 0.9, "created_at": 2.0},
            {"source": "cognitive", "text": "Validate contract before merge", "confidence": 0.8, "created_at": 1.0},
        ],
    )
    monkeypatch.setattr(fusion, "_collect_eidos", lambda intent_text, limit=5: [])
    monkeypatch.setattr(fusion, "_collect_chips", lambda limit=6: [])
    monkeypatch.setattr(fusion, "_collect_outcomes", lambda intent_text, limit=6: [])
    monkeypatch.setattr(fusion, "_collect_orchestration", lambda limit=5: [])

    bundle = fusion.build_memory_bundle(
        session_id="s1",
        intent_text="",
        intent_family="emergent_other",
        tool_name="Read",
    )

    texts = [row.get("text") for row in bundle["evidence"]]
    assert "Validate contract before merge" in texts
    assert all("tool_49_error" not in str(t) for t in texts)


def test_collect_outcomes_prefers_intent_relevant_rows(monkeypatch):
    rows = [
        {"outcome_id": "o1", "text": "Fix auth token session mismatch with explicit session binding", "created_at": 10, "polarity": "pos"},
        {"outcome_id": "o2", "text": "Random social formatting advice about multiplier granted", "created_at": 20, "polarity": "pos"},
        {"outcome_id": "o3", "text": "Check auth timeout and token refresh path", "created_at": 30, "polarity": "neutral"},
    ]
    monkeypatch.setattr(fusion, "read_outcomes", lambda limit=60, since=0: rows)

    out = fusion._collect_outcomes("auth token timeout session", limit=2)
    texts = [str(r.get("text") or "") for r in out]
    joined = " | ".join(texts).lower()
    assert "auth token" in joined
    assert "session mismatch" in joined or "token refresh" in joined


def test_memory_bundle_prefers_intent_relevant_evidence(monkeypatch):
    monkeypatch.setattr(
        fusion,
        "_collect_cognitive",
        lambda limit=6: [
            {"source": "cognitive", "text": "Multiplier granted formatting pattern", "confidence": 0.9, "created_at": 5.0},
            {"source": "cognitive", "text": "Auth token session mismatch should be validated first", "confidence": 0.7, "created_at": 4.0},
        ],
    )
    monkeypatch.setattr(fusion, "_collect_eidos", lambda intent_text, limit=5: [])
    monkeypatch.setattr(fusion, "_collect_chips", lambda limit=6: [])
    monkeypatch.setattr(fusion, "_collect_outcomes", lambda intent_text, limit=6: [])
    monkeypatch.setattr(fusion, "_collect_orchestration", lambda limit=5: [])

    bundle = fusion.build_memory_bundle(
        session_id="s1",
        intent_text="auth token timeout and session binding",
        intent_family="auth_security",
        tool_name="Read",
    )
    texts = [str(row.get("text") or "") for row in bundle["evidence"]]
    joined = " | ".join(texts).lower()
    assert "auth token session mismatch" in joined
    assert "multiplier granted formatting pattern" not in joined


def test_collect_chips_parses_modern_content_schema(monkeypatch, tmp_path):
    monkeypatch.setattr(fusion, "CHIP_INSIGHTS_DIR", tmp_path)
    row = {
        "chip_id": "marketing",
        "observer_name": "campaign_observer",
        "content": "Improve conversion quality before increasing ad spend.",
        "timestamp": "2026-02-12T23:00:00+00:00",
        "captured_data": {"quality_score": {"total": 0.55}},
    }
    (tmp_path / "marketing.jsonl").write_text(json.dumps(row) + "\n", encoding="utf-8")

    out = fusion._collect_chips(limit=3)
    assert out
    assert out[0]["source"] == "chips"
    assert "conversion quality" in str(out[0]["text"]).lower()


def test_collect_chips_filters_telemetry_and_prefers_intent(monkeypatch, tmp_path):
    monkeypatch.setattr(fusion, "CHIP_INSIGHTS_DIR", tmp_path)
    telemetry = {
        "chip_id": "spark-core",
        "observer_name": "post_tool",
        "content": "[Spark Core Intelligence] user_prompt_signal: event_type: post_tool",
        "timestamp": "2026-02-12T23:00:00+00:00",
        "captured_data": {"quality_score": {"total": 0.9}},
    }
    marketing = {
        "chip_id": "marketing",
        "observer_name": "campaign_observer",
        "content": "Increase conversion quality before scaling ad spend.",
        "timestamp": "2026-02-12T23:00:01+00:00",
        "captured_data": {"quality_score": {"total": 0.6}},
    }
    (tmp_path / "spark-core.jsonl").write_text(json.dumps(telemetry) + "\n", encoding="utf-8")
    (tmp_path / "marketing.jsonl").write_text(json.dumps(marketing) + "\n", encoding="utf-8")

    out = fusion._collect_chips(
        limit=3,
        intent_text="marketing campaign conversion",
        intent_family="growth_marketing",
        tool_name="Task",
    )
    assert out
    joined = " | ".join(str(r.get("text") or "").lower() for r in out)
    assert "spark core intelligence" not in joined
    assert "conversion quality" in joined


def test_collect_chips_can_be_disabled_by_env(monkeypatch, tmp_path):
    monkeypatch.setenv("SPARK_ADVISORY_DISABLE_CHIPS", "1")
    monkeypatch.setattr(fusion, "CHIP_INSIGHTS_DIR", tmp_path)
    row = {
        "chip_id": "marketing",
        "observer_name": "campaign_observer",
        "content": "Increase conversion quality before scaling ad spend.",
        "timestamp": "2026-02-12T23:00:01+00:00",
        "captured_data": {"quality_score": {"total": 0.6}},
    }
    (tmp_path / "marketing.jsonl").write_text(json.dumps(row) + "\n", encoding="utf-8")
    out = fusion._collect_chips(limit=3, intent_text="marketing conversion", intent_family="growth", tool_name="Task")
    assert out == []
