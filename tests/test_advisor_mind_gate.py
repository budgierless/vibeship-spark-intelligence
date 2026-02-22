from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

import lib.advisor as advisor_mod
from lib.advisor import Advice


class _DummyCognitive:
    def is_noise_insight(self, _text: str) -> bool:
        return False

    def get_insights_for_context(self, *_args, **_kwargs):
        return []

    def get_self_awareness_insights(self):
        return []


class _FakeMind:
    def __init__(self, last_sync: str) -> None:
        self._last_sync = last_sync

    def get_stats(self):
        return {"last_sync": self._last_sync}


def _patch_advisor_runtime(monkeypatch, tmp_path: Path, last_sync: str) -> None:
    monkeypatch.setattr(advisor_mod, "ADVISOR_DIR", tmp_path)
    monkeypatch.setattr(advisor_mod, "ADVICE_LOG", tmp_path / "advice_log.jsonl")
    monkeypatch.setattr(advisor_mod, "EFFECTIVENESS_FILE", tmp_path / "effectiveness.json")
    monkeypatch.setattr(advisor_mod, "ADVISOR_METRICS", tmp_path / "metrics.json")
    monkeypatch.setattr(advisor_mod, "RECENT_ADVICE_LOG", tmp_path / "recent_advice.jsonl")
    monkeypatch.setattr(advisor_mod, "RETRIEVAL_ROUTE_LOG", tmp_path / "retrieval_router.jsonl")
    monkeypatch.setattr(advisor_mod, "HAS_EIDOS", False)
    monkeypatch.setattr(advisor_mod, "HAS_REQUESTS", True)
    monkeypatch.setattr(advisor_mod, "get_cognitive_learner", lambda: _DummyCognitive())
    monkeypatch.setattr(advisor_mod, "get_mind_bridge", lambda: _FakeMind(last_sync))
    monkeypatch.setattr(advisor_mod, "MIND_MAX_STALE_SECONDS", 60.0)
    monkeypatch.setattr(advisor_mod, "MIND_STALE_ALLOW_IF_EMPTY", True)
    monkeypatch.setattr(advisor_mod, "MIN_RANK_SCORE", 0.0)


def _patch_non_mind_sources(monkeypatch, bank_items):
    monkeypatch.setattr(advisor_mod.SparkAdvisor, "_get_bank_advice", lambda _s, _c: list(bank_items))
    monkeypatch.setattr(advisor_mod.SparkAdvisor, "_get_cognitive_advice", lambda _s, _t, _c, _sc=None: [])
    monkeypatch.setattr(advisor_mod.SparkAdvisor, "_get_chip_advice", lambda _s, _c: [])
    monkeypatch.setattr(advisor_mod.SparkAdvisor, "_get_tool_specific_advice", lambda _s, _t: [])
    monkeypatch.setattr(advisor_mod.SparkAdvisor, "_get_opportunity_advice", lambda _s, **_k: [])
    monkeypatch.setattr(advisor_mod.SparkAdvisor, "_get_surprise_advice", lambda _s, _t, _c: [])
    monkeypatch.setattr(advisor_mod.SparkAdvisor, "_get_skill_advice", lambda _s, _c: [])
    monkeypatch.setattr(advisor_mod.SparkAdvisor, "_get_convo_advice", lambda _s, _t, _c: [])
    monkeypatch.setattr(advisor_mod.SparkAdvisor, "_get_engagement_advice", lambda _s, _t, _c: [])
    monkeypatch.setattr(advisor_mod.SparkAdvisor, "_get_niche_advice", lambda _s, _t, _c: [])
    monkeypatch.setattr(advisor_mod.SparkAdvisor, "_rank_advice", lambda _s, items: list(items))
    monkeypatch.setattr(advisor_mod.SparkAdvisor, "_rank_score", lambda _s, _item: 1.0)


def _advice(advice_id: str, text: str, source: str) -> Advice:
    return Advice(
        advice_id=advice_id,
        insight_key=f"{source}:{advice_id}",
        text=text,
        confidence=0.9,
        source=source,
        context_match=0.9,
        reason="test",
    )


def test_stale_mind_skipped_when_other_sources_exist(monkeypatch, tmp_path):
    stale_sync = (datetime.now(timezone.utc) - timedelta(hours=4)).isoformat()
    _patch_advisor_runtime(monkeypatch, tmp_path, stale_sync)
    _patch_non_mind_sources(monkeypatch, [_advice("b1", "bank result", "bank")])

    calls = {"mind": 0}

    def _mind(_self, _context):
        calls["mind"] += 1
        return [_advice("m1", "mind result", "mind")]

    monkeypatch.setattr(advisor_mod.SparkAdvisor, "_get_mind_advice", _mind)

    advisor = advisor_mod.SparkAdvisor()
    out = advisor.advise("Read", {"file_path": "a.py"}, "diagnose retrieval", include_mind=True)

    assert out
    assert calls["mind"] == 0
    assert any(item.source == "bank" for item in out)


def test_stale_mind_used_when_no_other_sources(monkeypatch, tmp_path):
    stale_sync = (datetime.now(timezone.utc) - timedelta(hours=4)).isoformat()
    _patch_advisor_runtime(monkeypatch, tmp_path, stale_sync)
    _patch_non_mind_sources(monkeypatch, [])

    calls = {"mind": 0}

    def _mind(_self, _context):
        calls["mind"] += 1
        return [_advice("m2", "mind fallback", "mind")]

    monkeypatch.setattr(advisor_mod.SparkAdvisor, "_get_mind_advice", _mind)

    advisor = advisor_mod.SparkAdvisor()
    out = advisor.advise("Read", {"file_path": "b.py"}, "diagnose retrieval", include_mind=True)

    assert calls["mind"] == 1
    assert out
    assert out[0].source == "mind"


def test_cache_key_includes_include_mind_flag(monkeypatch, tmp_path):
    fresh_sync = datetime.now(timezone.utc).isoformat()
    _patch_advisor_runtime(monkeypatch, tmp_path, fresh_sync)

    advisor = advisor_mod.SparkAdvisor()
    k_no_mind = advisor._cache_key("Read", "ctx", {"file_path": "x.py"}, "task", include_mind=False)
    k_with_mind = advisor._cache_key("Read", "ctx", {"file_path": "x.py"}, "task", include_mind=True)

    assert k_no_mind != k_with_mind


def test_mind_slot_reserved_when_configured(monkeypatch, tmp_path):
    fresh_sync = datetime.now(timezone.utc).isoformat()
    _patch_advisor_runtime(monkeypatch, tmp_path, fresh_sync)

    bank_items = [
        _advice("b1", "bank 1", "bank"),
        _advice("b2", "bank 2", "bank"),
        _advice("b3", "bank 3", "bank"),
    ]
    monkeypatch.setattr(advisor_mod.SparkAdvisor, "_get_bank_advice", lambda _s, _c: list(bank_items))
    monkeypatch.setattr(advisor_mod.SparkAdvisor, "_get_cognitive_advice", lambda _s, _t, _c, _sc=None: [])
    monkeypatch.setattr(advisor_mod.SparkAdvisor, "_get_chip_advice", lambda _s, _c: [])
    monkeypatch.setattr(advisor_mod.SparkAdvisor, "_get_tool_specific_advice", lambda _s, _t: [])
    monkeypatch.setattr(advisor_mod.SparkAdvisor, "_get_opportunity_advice", lambda _s, **_k: [])
    monkeypatch.setattr(advisor_mod.SparkAdvisor, "_get_surprise_advice", lambda _s, _t, _c: [])
    monkeypatch.setattr(advisor_mod.SparkAdvisor, "_get_skill_advice", lambda _s, _c: [])
    monkeypatch.setattr(advisor_mod.SparkAdvisor, "_get_convo_advice", lambda _s, _t, _c: [])
    monkeypatch.setattr(advisor_mod.SparkAdvisor, "_get_engagement_advice", lambda _s, _t, _c: [])
    monkeypatch.setattr(advisor_mod.SparkAdvisor, "_get_niche_advice", lambda _s, _t, _c: [])

    def _mind(_self, _context):
        return [_advice("m1", "mind 1", "mind")]

    monkeypatch.setattr(advisor_mod.SparkAdvisor, "_get_mind_advice", _mind)
    monkeypatch.setattr(advisor_mod, "MAX_ADVICE_ITEMS", 3)
    monkeypatch.setattr(advisor_mod, "MIN_RANK_SCORE", 0.0)
    monkeypatch.setattr(advisor_mod, "MIND_RESERVE_SLOTS", 1)
    monkeypatch.setattr(advisor_mod, "MIND_RESERVE_MIN_RANK", 0.45)

    score_map = {"b1": 0.95, "b2": 0.90, "b3": 0.85, "m1": 0.50}
    monkeypatch.setattr(
        advisor_mod.SparkAdvisor,
        "_rank_score",
        lambda _s, item: score_map.get(getattr(item, "advice_id", ""), 0.0),
    )
    monkeypatch.setattr(
        advisor_mod.SparkAdvisor,
        "_rank_advice",
        lambda _s, items: sorted(items, key=lambda item: score_map.get(getattr(item, "advice_id", ""), 0.0), reverse=True),
    )

    advisor = advisor_mod.SparkAdvisor()
    out = advisor.advise("Read", {"file_path": "c.py"}, "mind reserve check", include_mind=True)

    assert len(out) == 3
    assert any(item.source == "mind" for item in out)
