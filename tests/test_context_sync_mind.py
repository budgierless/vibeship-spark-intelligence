from __future__ import annotations

from lib import context_sync
from lib.cognitive_learner import CognitiveCategory, CognitiveInsight


def test_build_compact_context_includes_mind_highlights(monkeypatch, tmp_path):
    insight = CognitiveInsight(
        category=CognitiveCategory.WISDOM,
        insight="Cognitive baseline",
        evidence=["x"],
        confidence=0.8,
        context="ctx",
        times_validated=3,
    )

    monkeypatch.setattr(context_sync, "_select_insights", lambda **_k: [insight])
    monkeypatch.setattr(context_sync, "_infer_mind_query", lambda _ctx: "recent auth work")
    monkeypatch.setattr(
        context_sync,
        "_load_mind_highlights",
        lambda _query, limit=1: [{"text": "Mind memory"}],
    )

    text, selected = context_sync.build_compact_context(project_dir=tmp_path, limit=1)

    assert "## Cognitive Insights" in text
    assert "## Mind Memory" in text
    assert selected == 2
