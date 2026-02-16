from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import lib.advisor as advisor_mod


@dataclass
class _FakeInsight:
    insight: str
    reliability: float = 0.9
    times_validated: int = 3
    context: str = ""


class _FakeMind:
    def get_stats(self):
        return {"last_sync": datetime.now(timezone.utc).isoformat()}


class _CognitiveWithInsights:
    def __init__(self, insights):
        self._insights = list(insights)

    def is_noise_insight(self, _text: str) -> bool:
        return False

    def get_insights_for_context(self, *_args, **_kwargs):
        return []

    def get_self_awareness_insights(self):
        return list(self._insights)


def _patch_runtime(monkeypatch, tmp_path: Path, cognitive) -> None:
    monkeypatch.setattr(advisor_mod, "ADVISOR_DIR", tmp_path)
    monkeypatch.setattr(advisor_mod, "ADVICE_LOG", tmp_path / "advice_log.jsonl")
    monkeypatch.setattr(advisor_mod, "EFFECTIVENESS_FILE", tmp_path / "effectiveness.json")
    monkeypatch.setattr(advisor_mod, "ADVISOR_METRICS", tmp_path / "metrics.json")
    monkeypatch.setattr(advisor_mod, "RECENT_ADVICE_LOG", tmp_path / "recent_advice.jsonl")
    monkeypatch.setattr(advisor_mod, "RETRIEVAL_ROUTE_LOG", tmp_path / "retrieval_router.jsonl")
    monkeypatch.setattr(advisor_mod, "get_cognitive_learner", lambda: cognitive)
    monkeypatch.setattr(advisor_mod, "get_mind_bridge", lambda: _FakeMind())
    monkeypatch.setattr(advisor_mod, "HAS_EIDOS", False)
    monkeypatch.setattr(advisor_mod, "MIN_RELIABILITY_FOR_ADVICE", 0.5)


def test_tool_specific_advice_ignores_plural_substring_noise(monkeypatch, tmp_path):
    cognitive = _CognitiveWithInsights(
        [
            _FakeInsight("I struggle with other tasks when the prompt is vague."),
            _FakeInsight("I fail when Task payload is under-specified."),
        ]
    )
    _patch_runtime(monkeypatch, tmp_path, cognitive)
    advisor = advisor_mod.SparkAdvisor()

    out = advisor._get_tool_specific_advice("Task")
    texts = [row.text for row in out]

    assert any("Task payload" in text for text in texts)
    assert all("other tasks" not in text for text in texts)


def test_tool_specific_advice_can_match_via_insight_context(monkeypatch, tmp_path):
    cognitive = _CognitiveWithInsights(
        [
            _FakeInsight(
                "Retry bursts caused request storms.",
                context="Observed with WebFetch under 429 pressure.",
            )
        ]
    )
    _patch_runtime(monkeypatch, tmp_path, cognitive)
    advisor = advisor_mod.SparkAdvisor()

    out = advisor._get_tool_specific_advice("WebFetch")

    assert out
    assert out[0].source == "self_awareness"


def test_should_be_careful_avoids_plural_false_positive(monkeypatch, tmp_path):
    cognitive = _CognitiveWithInsights(
        [_FakeInsight("I struggle with other tasks in long sessions.")]
    )
    _patch_runtime(monkeypatch, tmp_path, cognitive)
    advisor = advisor_mod.SparkAdvisor()

    cautious, reason = advisor.should_be_careful("Task")

    assert cautious is False
    assert reason == ""


def test_tool_specific_advice_respects_min_reliability(monkeypatch, tmp_path):
    cognitive = _CognitiveWithInsights(
        [_FakeInsight("I fail when Task plans are skipped.", reliability=0.2)]
    )
    _patch_runtime(monkeypatch, tmp_path, cognitive)
    advisor = advisor_mod.SparkAdvisor()

    out = advisor._get_tool_specific_advice("Task")

    assert out == []


def test_tool_specific_advice_filters_telemetry_error_labels(monkeypatch, tmp_path):
    cognitive = _CognitiveWithInsights(
        [
            _FakeInsight("I struggle with WebFetch_error tasks"),
            _FakeInsight("I fail when WebFetch retries are too aggressive."),
        ]
    )
    _patch_runtime(monkeypatch, tmp_path, cognitive)
    advisor = advisor_mod.SparkAdvisor()

    out = advisor._get_tool_specific_advice("WebFetch")
    texts = [row.text.lower() for row in out]

    assert any("retries are too aggressive" in text for text in texts)
    assert all("webfetch_error" not in text for text in texts)


def test_tool_specific_advice_filters_webfetch_fails_with_other_noise(monkeypatch, tmp_path):
    cognitive = _CognitiveWithInsights(
        [
            _FakeInsight("I struggle with WebFetch fails with other tasks"),
            _FakeInsight("I fail when WebFetch retries are too aggressive."),
        ]
    )
    _patch_runtime(monkeypatch, tmp_path, cognitive)
    advisor = advisor_mod.SparkAdvisor()

    out = advisor._get_tool_specific_advice("WebFetch")
    texts = [row.text.lower() for row in out]

    assert any("retries are too aggressive" in text for text in texts)
    assert all("fails with other tasks" not in text for text in texts)


def test_rank_score_heavily_penalizes_low_signal_telemetry_cautions(monkeypatch, tmp_path):
    cognitive = _CognitiveWithInsights([])
    _patch_runtime(monkeypatch, tmp_path, cognitive)

    class _DummyRalph:
        def get_insight_effectiveness(self, _insight_key):
            return 0.5

    monkeypatch.setattr("lib.meta_ralph.get_meta_ralph", lambda: _DummyRalph())

    advisor = advisor_mod.SparkAdvisor()
    good = advisor_mod.Advice(
        advice_id="good",
        insight_key="k-good",
        text="Use jittered retries when WebFetch returns 429 to avoid request storms.",
        confidence=0.8,
        source="self_awareness",
        context_match=0.8,
    )
    noisy = advisor_mod.Advice(
        advice_id="noisy",
        insight_key="k-noisy",
        text="[Caution] I struggle with WebFetch_error tasks",
        confidence=0.8,
        source="self_awareness",
        context_match=0.8,
    )

    assert advisor._rank_score(noisy) < advisor._rank_score(good) * 0.2


def test_should_drop_read_before_edit_on_unrelated_tools(monkeypatch, tmp_path):
    cognitive = _CognitiveWithInsights([])
    _patch_runtime(monkeypatch, tmp_path, cognitive)
    advisor = advisor_mod.SparkAdvisor()

    item = advisor_mod.Advice(
        advice_id="read-first",
        insight_key="k-read",
        text="Always Read a file before Edit to verify current content",
        confidence=0.9,
        source="cognitive",
        context_match=0.9,
    )

    assert advisor._should_drop_advice(item, tool_name="WebFetch") is True
    assert advisor._should_drop_advice(item, tool_name="Edit") is False
