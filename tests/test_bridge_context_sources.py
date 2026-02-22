from __future__ import annotations

from types import SimpleNamespace

import lib.bridge as bridge_mod


def test_generate_active_context_labels_true_source_prefixes(monkeypatch):
    monkeypatch.setattr(
        bridge_mod,
        "get_contextual_insights",
        lambda _query, limit=6: [
            {"source": "cognitive", "category": "self_awareness", "text": "cog"},
            {"source": "bank", "category": "memory", "text": "bank"},
            {"source": "taste", "category": "taste:ui_design", "text": "taste"},
            {"source": "mind", "category": "principle", "text": "mind"},
        ],
    )
    monkeypatch.setattr(bridge_mod, "get_relevant_skills", lambda _query, limit=3: [])
    monkeypatch.setattr(bridge_mod, "get_high_value_insights", lambda: [])
    monkeypatch.setattr(bridge_mod, "get_failure_warnings", lambda: [])
    monkeypatch.setattr(bridge_mod, "get_recent_lessons", lambda: [])
    monkeypatch.setattr(bridge_mod, "get_strong_opinions", lambda: [])
    monkeypatch.setattr(bridge_mod, "get_growth_moments", lambda: [])
    monkeypatch.setattr(bridge_mod, "load_profile", lambda _cwd: None)
    monkeypatch.setattr(bridge_mod, "record_exposures", lambda *a, **k: None)
    monkeypatch.setattr(bridge_mod, "infer_latest_session_id", lambda: "s1")
    monkeypatch.setattr(bridge_mod, "infer_latest_trace_id", lambda _sid: "t1")

    out = bridge_mod.generate_active_context("diagnose retrieval")

    assert "- [self_awareness] cog" in out
    assert "- [bank:memory] bank" in out
    assert "- [taste:taste:ui_design] taste" in out
    assert "- [mind:principle] mind" in out


def test_contextual_insights_reserve_mind_slot(monkeypatch):
    class _FakeCog:
        def get_insights_for_context(self, _query, limit=6):
            return [
                SimpleNamespace(
                    category=SimpleNamespace(value="reasoning"),
                    insight="cognitive one",
                    reliability=0.9,
                    times_validated=5,
                ),
                SimpleNamespace(
                    category=SimpleNamespace(value="reasoning"),
                    insight="cognitive two",
                    reliability=0.8,
                    times_validated=3,
                ),
            ]

    class _FakeMind:
        def retrieve_relevant(self, _query, limit=5):
            return [{"content": "mind memory line", "content_type": "principle", "memory_id": "m-1"}]

    monkeypatch.setattr("lib.cognitive_learner.CognitiveLearner", _FakeCog)
    monkeypatch.setattr("lib.mind_bridge.MindBridge", _FakeMind)
    monkeypatch.setattr(bridge_mod, "bank_retrieve", lambda *_a, **_k: [])
    monkeypatch.setattr(bridge_mod, "CONTEXT_MIND_RESERVED_SLOTS", 1)

    out = bridge_mod.get_contextual_insights("auth regression", limit=2)
    assert len(out) == 2
    assert any(item.get("source") == "mind" for item in out)
