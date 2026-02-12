from __future__ import annotations

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
