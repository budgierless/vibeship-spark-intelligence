from __future__ import annotations

import json
import time
from pathlib import Path
from types import SimpleNamespace

import lib.advisor as advisor_mod
import lib.opportunity_scanner as scanner
from lib.queue import EventType
from lib.soul_upgrade import SoulState


def _mk_event(
    event_type: EventType,
    *,
    session_id: str = "s1",
    tool_name: str = "",
    tool_input: dict | None = None,
    payload: dict | None = None,
):
    return SimpleNamespace(
        event_type=event_type,
        session_id=session_id,
        tool_name=tool_name,
        tool_input=tool_input or {},
        data={"payload": payload or {}},
    )


def test_scan_runtime_opportunities_filters_telemetry_and_persists(monkeypatch, tmp_path: Path):
    monkeypatch.setattr(
        scanner,
        "fetch_soul_state",
        lambda session_id="default": SoulState(
            ok=True,
            mood="builder",
            soul_kernel={"non_harm": True, "service": True, "clarity": True},
            source="test",
        ),
    )
    monkeypatch.setattr(scanner, "SELF_FILE", tmp_path / "self_opportunities.jsonl")
    monkeypatch.setattr(scanner, "OUTCOME_FILE", tmp_path / "outcomes.jsonl")
    monkeypatch.setattr(scanner, "SCANNER_ENABLED", True)
    monkeypatch.setattr(scanner, "_track_meta_retrieval", lambda **_k: None)
    monkeypatch.setattr(scanner, "_track_meta_outcome", lambda **_k: None)

    events = [
        _mk_event(
            EventType.USER_PROMPT,
            payload={"text": "Let's improve Spark reliability and make the loop better."},
        ),
        _mk_event(
            EventType.USER_PROMPT,
            payload={"text": "I struggle with tool_1_error tasks"},
        ),
        _mk_event(
            EventType.POST_TOOL,
            tool_name="Edit",
            tool_input={"content": "def build_loop():\n    return True\n"},
        ),
    ]

    out = scanner.scan_runtime_opportunities(
        events,
        stats={"errors": ["pipeline"]},
        query="evolve Spark intelligence loop",
        session_id="s1",
        persist=True,
    )

    assert out["enabled"] is True
    assert out["opportunities_found"] >= 1
    assert out["telemetry_filtered"] >= 1
    assert scanner.SELF_FILE.exists()
    rows = [
        json.loads(line)
        for line in scanner.SELF_FILE.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    assert len(rows) == out["persisted"]
    assert all("tool_1_error" not in (r.get("question") or "") for r in rows)


def test_generate_user_opportunities_respects_conservative_mode(monkeypatch):
    monkeypatch.setattr(
        scanner,
        "fetch_soul_state",
        lambda session_id="default": SoulState(
            ok=True,
            mood="builder",
            soul_kernel={"non_harm": True, "service": False, "clarity": True},
            source="test",
        ),
    )
    monkeypatch.setattr(scanner, "SCANNER_ENABLED", True)
    monkeypatch.setattr(scanner, "USER_SCAN_ENABLED", True)
    monkeypatch.setattr(scanner, "USER_MAX_ITEMS", 4)

    rows = scanner.generate_user_opportunities(
        tool_name="Task",
        context="Improve Spark autonomy strategy for launch",
        task_context="",
        session_id="s1",
        persist=False,
    )

    assert rows
    assert all(r["mode"] == "conservative" for r in rows)
    assert all(r.get("category") != "compounding" for r in rows)


def test_generate_user_opportunities_disabled_by_default_mode(monkeypatch):
    monkeypatch.setattr(scanner, "SCANNER_ENABLED", True)
    monkeypatch.setattr(scanner, "USER_SCAN_ENABLED", False)

    rows = scanner.generate_user_opportunities(
        tool_name="Task",
        context="Improve Spark strategy",
        task_context="",
        session_id="s1",
        persist=False,
    )

    assert rows == []


class _DummyCognitive:
    def is_noise_insight(self, _text: str) -> bool:
        return False

    def get_insights_for_context(self, *_args, **_kwargs):
        return []

    def get_self_awareness_insights(self):
        return []


def test_advisor_can_surface_opportunity_source(monkeypatch, tmp_path: Path):
    monkeypatch.setattr(advisor_mod, "ADVISOR_DIR", tmp_path)
    monkeypatch.setattr(advisor_mod, "ADVICE_LOG", tmp_path / "advice_log.jsonl")
    monkeypatch.setattr(advisor_mod, "EFFECTIVENESS_FILE", tmp_path / "effectiveness.json")
    monkeypatch.setattr(advisor_mod, "ADVISOR_METRICS", tmp_path / "metrics.json")
    monkeypatch.setattr(advisor_mod, "RECENT_ADVICE_LOG", tmp_path / "recent_advice.jsonl")
    monkeypatch.setattr(advisor_mod, "RETRIEVAL_ROUTE_LOG", tmp_path / "retrieval_router.jsonl")
    monkeypatch.setattr(advisor_mod, "HAS_EIDOS", False)
    monkeypatch.setattr(advisor_mod, "HAS_REQUESTS", False)
    monkeypatch.setattr(advisor_mod, "get_cognitive_learner", lambda: _DummyCognitive())
    monkeypatch.setattr(advisor_mod, "get_mind_bridge", lambda: None)
    monkeypatch.setattr(advisor_mod, "MIN_RANK_SCORE", 0.0)

    monkeypatch.setattr(advisor_mod.SparkAdvisor, "_get_bank_advice", lambda _s, _c: [])
    monkeypatch.setattr(advisor_mod.SparkAdvisor, "_get_cognitive_advice", lambda _s, _t, _c, _sc=None: [])
    monkeypatch.setattr(advisor_mod.SparkAdvisor, "_get_chip_advice", lambda _s, _c: [])
    monkeypatch.setattr(advisor_mod.SparkAdvisor, "_get_tool_specific_advice", lambda _s, _t: [])
    monkeypatch.setattr(advisor_mod.SparkAdvisor, "_get_surprise_advice", lambda _s, _t, _c: [])
    monkeypatch.setattr(advisor_mod.SparkAdvisor, "_get_skill_advice", lambda _s, _c: [])
    monkeypatch.setattr(advisor_mod.SparkAdvisor, "_get_convo_advice", lambda _s, _t, _c: [])
    monkeypatch.setattr(advisor_mod.SparkAdvisor, "_get_engagement_advice", lambda _s, _t, _c: [])
    monkeypatch.setattr(advisor_mod.SparkAdvisor, "_get_niche_advice", lambda _s, _t, _c: [])
    monkeypatch.setattr(advisor_mod.SparkAdvisor, "_rank_advice", lambda _s, items: list(items))
    monkeypatch.setattr(advisor_mod.SparkAdvisor, "_rank_score", lambda _s, _item: 1.0)

    monkeypatch.setattr(
        scanner,
        "generate_user_opportunities",
        lambda **_kwargs: [
            {
                "category": "outcome_clarity",
                "question": "What is the measurable success condition?",
                "next_step": "Define one acceptance check.",
                "confidence": 0.7,
                "context_match": 0.8,
                "rationale": "test",
            }
        ],
    )

    advisor = advisor_mod.SparkAdvisor()
    out = advisor.advise(
        "Task",
        {},
        "improve spark opportunity loop",
        include_mind=False,
        track_retrieval=False,
    )

    assert any(item.source == "opportunity" for item in out)


def test_scan_runtime_opportunities_filters_recent_repeats(monkeypatch, tmp_path: Path):
    monkeypatch.setattr(
        scanner,
        "fetch_soul_state",
        lambda session_id="default": SoulState(
            ok=True,
            mood="builder",
            soul_kernel={"non_harm": True, "service": True, "clarity": True},
            source="test",
        ),
    )
    monkeypatch.setattr(scanner, "SELF_FILE", tmp_path / "self_opportunities.jsonl")
    monkeypatch.setattr(scanner, "OUTCOME_FILE", tmp_path / "outcomes.jsonl")
    monkeypatch.setattr(scanner, "SCANNER_ENABLED", True)
    monkeypatch.setattr(scanner, "SELF_MAX_ITEMS", 10)
    monkeypatch.setattr(scanner, "SELF_DEDUP_WINDOW_S", 3600.0)
    monkeypatch.setattr(scanner, "SELF_RECENT_LOOKBACK", 100)
    monkeypatch.setattr(scanner, "_track_meta_retrieval", lambda **_k: None)
    monkeypatch.setattr(scanner, "_track_meta_outcome", lambda **_k: None)

    prior = {
        "ts": time.time(),
        "session_id": "s1",
        "scope": "self",
        "question": "What exact outcome marks done, and how will Spark verify it?",
    }
    scanner.SELF_FILE.write_text(json.dumps(prior) + "\n", encoding="utf-8")

    events = [
        _mk_event(
            EventType.USER_PROMPT,
            payload={"text": "Let's improve Spark reliability and autonomy for this task."},
        ),
        _mk_event(
            EventType.POST_TOOL,
            tool_name="Edit",
            tool_input={"content": "def refactor_loop():\n    return True\n"},
        ),
    ]

    out = scanner.scan_runtime_opportunities(
        events,
        stats={"errors": ["pipeline"]},
        query="improve Spark delivery quality",
        session_id="s1",
        persist=False,
    )

    questions = [str(r.get("question") or "") for r in out.get("self_opportunities") or []]
    assert not any("What exact outcome marks done" in q for q in questions)
    assert out.get("dedup_recent_filtered", 0) >= 1


def test_select_diverse_self_rows_prefers_category_spread():
    candidates = [
        {
            "category": "assumption_audit",
            "priority": "high",
            "confidence": 0.9,
            "question": "Which assumption keeps failing, and what evidence would quickly disprove it?",
        },
        {
            "category": "assumption_audit",
            "priority": "medium",
            "confidence": 0.8,
            "question": "Which assumption is most likely wrong right now?",
        },
        {
            "category": "reversibility",
            "priority": "medium",
            "confidence": 0.7,
            "question": "What is the safest reversible step if this change regresses?",
        },
    ]

    selected, _filtered = scanner._select_diverse_self_rows(candidates, max_items=2, recent_keys=set())
    cats = [str(r.get("category") or "") for r in selected]
    assert "assumption_audit" in cats
    assert "reversibility" in cats


def test_scan_runtime_opportunities_tracks_acted_outcomes(monkeypatch, tmp_path: Path):
    monkeypatch.setattr(
        scanner,
        "fetch_soul_state",
        lambda session_id="default": SoulState(
            ok=True,
            mood="builder",
            soul_kernel={"non_harm": True, "service": True, "clarity": True},
            source="test",
        ),
    )
    monkeypatch.setattr(scanner, "SELF_FILE", tmp_path / "self_opportunities.jsonl")
    monkeypatch.setattr(scanner, "OUTCOME_FILE", tmp_path / "outcomes.jsonl")
    monkeypatch.setattr(scanner, "SCANNER_ENABLED", True)
    monkeypatch.setattr(scanner, "_track_meta_retrieval", lambda **_k: None)
    monkeypatch.setattr(scanner, "_track_meta_outcome", lambda **_k: None)

    prior = {
        "ts": time.time() - 5,
        "session_id": "s1",
        "trace_id": "trace-1",
        "opportunity_id": "opp:test:1",
        "scope": "self",
        "mode": "conscious",
        "category": "verification_gap",
        "question": "What is the smallest proof that this change works before the next edit?",
    }
    scanner.SELF_FILE.write_text(json.dumps(prior) + "\n", encoding="utf-8")

    events = [
        _mk_event(
            EventType.USER_PROMPT,
            payload={"text": "I ran pytest to verify the change and confirm behavior.", "trace_id": "trace-1"},
        ),
    ]

    out = scanner.scan_runtime_opportunities(
        events,
        stats={"validation": {"matched": 1}},
        query="",
        session_id="s1",
        persist=True,
    )

    assert out["outcomes_tracked"] >= 1
    assert out["outcomes_improved"] >= 1
    rows = [
        json.loads(line)
        for line in scanner.OUTCOME_FILE.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    assert rows
    assert rows[-1]["opportunity_id"] == "opp:test:1"
    assert rows[-1]["acted_on"] is True
    assert rows[-1]["outcome"] == "good"
    assert rows[-1]["strict_trace_match"] is True


def test_promote_high_performing_opportunities_emits_candidates(monkeypatch, tmp_path: Path):
    monkeypatch.setattr(scanner, "SELF_FILE", tmp_path / "self_opportunities.jsonl")
    monkeypatch.setattr(scanner, "OUTCOME_FILE", tmp_path / "outcomes.jsonl")
    monkeypatch.setattr(scanner, "PROMOTION_FILE", tmp_path / "promoted_opportunities.jsonl")
    monkeypatch.setattr(scanner, "PROMOTION_MIN_SUCCESSES", 2)
    monkeypatch.setattr(scanner, "PROMOTION_MIN_EFFECTIVENESS", 0.6)

    self_rows = [
        {
            "ts": time.time() - 40,
            "session_id": "s1",
            "opportunity_id": "opp:a",
            "category": "verification_gap",
            "question": "What is the smallest proof that this change works before the next edit?",
            "next_step": "Run one focused command/test that validates the changed behavior.",
        },
        {
            "ts": time.time() - 30,
            "session_id": "s1",
            "opportunity_id": "opp:b",
            "category": "verification_gap",
            "question": "What is the smallest proof that this change works before the next edit?",
            "next_step": "Run one focused command/test that validates the changed behavior.",
        },
    ]
    scanner.SELF_FILE.write_text(
        "".join(json.dumps(r) + "\n" for r in self_rows),
        encoding="utf-8",
    )

    outcome_rows = [
        {"ts": time.time() - 20, "opportunity_id": "opp:a", "acted_on": True, "outcome": "good", "strict_trace_match": True},
        {"ts": time.time() - 10, "opportunity_id": "opp:b", "acted_on": True, "outcome": "good", "strict_trace_match": True},
    ]
    scanner.OUTCOME_FILE.write_text(
        "".join(json.dumps(r) + "\n" for r in outcome_rows),
        encoding="utf-8",
    )

    promoted = scanner.promote_high_performing_opportunities(limit=3, persist=True)

    assert promoted
    assert promoted[0]["good"] >= 2
    assert "eidos_observation" in promoted[0]
    assert scanner.PROMOTION_FILE.exists()
