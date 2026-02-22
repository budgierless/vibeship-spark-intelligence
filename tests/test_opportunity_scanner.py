from __future__ import annotations

import json
import time
from pathlib import Path
from types import SimpleNamespace

import lib.advisor as advisor_mod
import lib.opportunity_scanner as scanner
import lib.opportunity_scanner_adapter as scanner_adapter
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
    monkeypatch.setattr(scanner, "DECISIONS_FILE", tmp_path / "decisions.jsonl")
    monkeypatch.setattr(scanner, "SCANNER_ENABLED", True)
    monkeypatch.setattr(
        scanner,
        "_generate_llm_self_candidates",
        lambda **_k: ([], {"enabled": False, "attempted": False, "used": False, "provider": None, "error": None, "candidates": 0}),
    )
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
    # Scope fields should exist (even if None in test stubs).
    assert all("scope_type" in r for r in rows)
    assert all("scope_id" in r for r in rows)


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
        scanner_adapter,
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
    monkeypatch.setattr(scanner, "DECISIONS_FILE", tmp_path / "decisions.jsonl")
    monkeypatch.setattr(scanner, "SCANNER_ENABLED", True)
    monkeypatch.setattr(scanner, "SELF_MAX_ITEMS", 10)
    monkeypatch.setattr(scanner, "SELF_DEDUP_WINDOW_S", 3600.0)
    monkeypatch.setattr(scanner, "SELF_RECENT_LOOKBACK", 100)
    monkeypatch.setattr(
        scanner,
        "_generate_llm_self_candidates",
        lambda **_k: ([], {"enabled": False, "attempted": False, "used": False, "provider": None, "error": None, "candidates": 0}),
    )
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


def test_scan_runtime_opportunities_respects_scope_hint_and_passes_cooldown_key(monkeypatch, tmp_path: Path):
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
    monkeypatch.setattr(scanner, "DECISIONS_FILE", tmp_path / "decisions.jsonl")
    monkeypatch.setattr(scanner, "SCANNER_ENABLED", True)
    monkeypatch.setattr(scanner, "_track_meta_retrieval", lambda **_k: None)
    monkeypatch.setattr(scanner, "_track_meta_outcome", lambda **_k: None)

    seen = {}

    def _fake_llm(*, cooldown_key=None, **_k):
        seen["cooldown_key"] = cooldown_key
        return (
            [
                {
                    "category": "verification_gap",
                    "priority": "high",
                    "confidence": 0.8,
                    "question": "Test question from LLM",
                    "next_step": "Test next step",
                    "rationale": "Test rationale",
                    "source": "llm",
                    "llm_provider": "minimax",
                }
            ],
            {
                "enabled": True,
                "attempted": True,
                "used": True,
                "provider": "minimax",
                "error": None,
                "candidates": 1,
            },
        )

    monkeypatch.setattr(scanner, "_generate_llm_self_candidates", _fake_llm)

    events = [
        _mk_event(
            EventType.USER_PROMPT,
            payload={"text": "scope:operation op:marketing Improve our marketing workflow with verification gates."},
        ),
    ]
    out = scanner.scan_runtime_opportunities(events, stats={"errors": []}, query="", session_id="s1", persist=True)
    assert out["scope_type"] == "operation"
    assert out["scope_id"] == "marketing"
    assert seen.get("cooldown_key") == "operation:marketing"


def test_scan_runtime_opportunities_filters_dismissed_questions(monkeypatch, tmp_path: Path):
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
    monkeypatch.setattr(scanner, "DECISIONS_FILE", tmp_path / "decisions.jsonl")
    monkeypatch.setattr(scanner, "SCANNER_ENABLED", True)
    monkeypatch.setattr(
        scanner,
        "_generate_llm_self_candidates",
        lambda **_k: ([], {"enabled": False, "attempted": False, "used": False, "provider": None, "error": None, "candidates": 0}),
    )
    monkeypatch.setattr(scanner, "_track_meta_retrieval", lambda **_k: None)
    monkeypatch.setattr(scanner, "_track_meta_outcome", lambda **_k: None)

    q = "What exact outcome marks done, and how will Spark verify it?"
    scanner.DECISIONS_FILE.write_text(
        json.dumps(
            {
                "ts": time.time(),
                "action": "dismiss",
                "opportunity_id": "opp:test",
                "question_key": scanner._question_key(q),
                "note": "not relevant",
            }
        )
        + "\n",
        encoding="utf-8",
    )

    monkeypatch.setattr(
        scanner,
        "_derive_self_candidates",
        lambda **_k: [
            {
                "category": "outcome_clarity",
                "priority": "high",
                "confidence": 0.8,
                "question": q,
                "next_step": "Define acceptance check.",
                "rationale": "test",
            }
        ],
    )

    out = scanner.scan_runtime_opportunities(
        [
            _mk_event(EventType.USER_PROMPT, payload={"text": "Improve something with clear done criteria."}),
        ],
        stats={"errors": []},
        query="",
        session_id="s1",
        persist=True,
    )
    assert out["opportunities_found"] == 0
    assert out["persisted"] == 0


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
    monkeypatch.setattr(
        scanner,
        "_generate_llm_self_candidates",
        lambda **_k: ([], {"enabled": False, "attempted": False, "used": False, "provider": None, "error": None, "candidates": 0}),
    )
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


def test_sanitize_llm_self_rows_filters_telemetry_noise():
    rows = scanner._sanitize_llm_self_rows(
        {
            "opportunities": [
                {
                    "category": "assumption_audit",
                    "priority": "medium",
                    "confidence": 0.8,
                    "question": "I struggle with tool_49_error tasks",
                    "next_step": "Check trace_id and heartbeat status code",
                    "rationale": "bad telemetry row",
                },
                {
                    "category": "verification_gap",
                    "priority": "high",
                    "confidence": 0.83,
                    "question": "What proof test validates this edit?",
                    "next_step": "Run one focused pytest command for the changed path.",
                    "rationale": "good row",
                },
            ]
        }
    )
    assert len(rows) == 1
    assert rows[0]["category"] == "verification_gap"


def test_scan_runtime_opportunities_merges_llm_candidates(monkeypatch, tmp_path: Path):
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
    monkeypatch.setattr(
        scanner,
        "_generate_llm_self_candidates",
        lambda **_k: (
            [
                {
                    "category": "assumption_audit",
                    "priority": "high",
                    "confidence": 0.9,
                    "question": "Which hidden assumption should Spark test first?",
                    "next_step": "Write one falsifiable hypothesis and test it.",
                    "rationale": "LLM generated",
                }
            ],
            {"enabled": True, "attempted": True, "used": True, "provider": "minimax", "error": None, "candidates": 1},
        ),
    )
    monkeypatch.setattr(scanner, "_track_meta_retrieval", lambda **_k: None)
    monkeypatch.setattr(scanner, "_track_meta_outcome", lambda **_k: None)

    out = scanner.scan_runtime_opportunities(
        [
            _mk_event(EventType.USER_PROMPT, payload={"text": "Improve Spark improvement loop quality"}),
            _mk_event(EventType.POST_TOOL, tool_name="Edit", tool_input={"content": "def x():\n    return 1\n"}),
        ],
        stats={},
        query="",
        session_id="s1",
        persist=False,
    )

    questions = [str(r.get("question") or "") for r in out.get("self_opportunities") or []]
    assert any("hidden assumption" in q for q in questions)
    assert out.get("llm", {}).get("used") is True
    assert out.get("llm", {}).get("provider") == "minimax"


def test_generate_llm_self_candidates_blocks_deepseek(monkeypatch):
    monkeypatch.setattr(scanner, "LLM_ENABLED", True)
    monkeypatch.setattr(scanner, "LLM_PROVIDER", "deepseek")
    monkeypatch.setattr(scanner, "LLM_MIN_CONTEXT_CHARS", 10)
    monkeypatch.setattr(scanner, "LLM_COOLDOWN_S", 0.0)
    scanner._LAST_LLM_ATTEMPT_BY_KEY.clear()

    rows, meta = scanner._generate_llm_self_candidates(
        prompts=["Improve Spark autonomy with measurable checks"],
        edits=["def x(): return True"],
        query="",
        stats={},
        kernel_ok=True,
        session_id="s1",
    )

    assert rows == []
    assert meta.get("attempted") is False
    assert str(meta.get("error") or "").startswith("provider_blocked:")


def test_generate_llm_self_candidates_honors_forced_provider(monkeypatch):
    monkeypatch.setattr(scanner, "LLM_ENABLED", True)
    monkeypatch.setattr(scanner, "LLM_PROVIDER", "minimax")
    monkeypatch.setattr(scanner, "LLM_TIMEOUT_S", 0.5)
    monkeypatch.setattr(scanner, "LLM_MIN_CONTEXT_CHARS", 10)
    monkeypatch.setattr(scanner, "LLM_COOLDOWN_S", 0.0)
    scanner._LAST_LLM_ATTEMPT_BY_KEY.clear()

    class _DummySynth:
        AI_TIMEOUT_S = 1.0

        @staticmethod
        def _get_provider_chain(_preferred=None):
            return ["minimax", "ollama"]

        @staticmethod
        def _query_provider(provider, _prompt):
            if provider != "minimax":
                raise AssertionError("forced provider should prevent fallback calls")
            return '{"opportunities":[{"category":"verification_gap","priority":"high","confidence":0.8,"question":"What proof validates this change?","next_step":"Run one focused test.","rationale":"Need evidence."}]}'

    monkeypatch.setitem(__import__("sys").modules, "lib.advisory_synthesizer", _DummySynth)

    rows, meta = scanner._generate_llm_self_candidates(
        prompts=["Improve scanner quality"],
        edits=["def x(): return True"],
        query="",
        stats={},
        kernel_ok=True,
        session_id="s1",
    )

    assert len(rows) == 1
    assert meta.get("used") is True
    assert meta.get("provider") == "minimax"


def test_generate_llm_self_candidates_surfaces_empty_or_timeout(monkeypatch):
    monkeypatch.setattr(scanner, "LLM_ENABLED", True)
    monkeypatch.setattr(scanner, "LLM_PROVIDER", "minimax")
    monkeypatch.setattr(scanner, "LLM_TIMEOUT_S", 0.1)
    monkeypatch.setattr(scanner, "LLM_MIN_CONTEXT_CHARS", 10)
    monkeypatch.setattr(scanner, "LLM_COOLDOWN_S", 0.0)
    scanner._LAST_LLM_ATTEMPT_BY_KEY.clear()

    class _DummySynth:
        AI_TIMEOUT_S = 1.0

        @staticmethod
        def _get_provider_chain(_preferred=None):
            return ["minimax"]

        @staticmethod
        def _query_provider(_provider, _prompt):
            return None

    monkeypatch.setitem(__import__("sys").modules, "lib.advisory_synthesizer", _DummySynth)

    rows, meta = scanner._generate_llm_self_candidates(
        prompts=["Improve scanner quality"],
        edits=["def x(): return True"],
        query="",
        stats={},
        kernel_ok=True,
        session_id="s1",
    )

    assert rows == []
    assert meta.get("attempted") is True
    assert meta.get("used") is False
    assert str(meta.get("error") or "").startswith("minimax:empty_or_timeout")


def test_generate_llm_self_candidates_respects_cooldown(monkeypatch):
    monkeypatch.setattr(scanner, "LLM_ENABLED", True)
    monkeypatch.setattr(scanner, "LLM_PROVIDER", "minimax")
    monkeypatch.setattr(scanner, "LLM_TIMEOUT_S", 0.1)
    monkeypatch.setattr(scanner, "LLM_COOLDOWN_S", 9999.0)
    monkeypatch.setattr(scanner, "LLM_MIN_CONTEXT_CHARS", 10)
    scanner._LAST_LLM_ATTEMPT_BY_KEY.clear()

    class _DummySynth:
        AI_TIMEOUT_S = 1.0

        @staticmethod
        def _get_provider_chain(_preferred=None):
            return ["minimax"]

        @staticmethod
        def _query_provider(_provider, _prompt):
            return '{"opportunities":[{"category":"verification_gap","priority":"high","confidence":0.8,"question":"What proof validates this change?","next_step":"Run one focused test.","rationale":"Need evidence."}]}'

    monkeypatch.setitem(__import__("sys").modules, "lib.advisory_synthesizer", _DummySynth)

    rows1, meta1 = scanner._generate_llm_self_candidates(
        prompts=["Improve scanner quality"],
        edits=["def x(): return True"],
        query="",
        stats={},
        kernel_ok=True,
        session_id="s_cool",
    )
    assert len(rows1) == 1
    assert meta1.get("attempted") is True

    rows2, meta2 = scanner._generate_llm_self_candidates(
        prompts=["Improve scanner quality"],
        edits=["def x(): return True"],
        query="",
        stats={},
        kernel_ok=True,
        session_id="s_cool",
    )
    assert rows2 == []
    assert meta2.get("attempted") is False
    assert meta2.get("skipped_reason") == "cooldown"


def test_extract_json_candidate_handles_think_wrapped_multiple_json_objects():
    # Some providers (notably MiniMax) can return a think block that itself includes JSON,
    # then the real output JSON afterwards.
    raw = (
        "<think> reason {\"foo\": 1} more </think>\n"
        "{\"opportunities\":[{\"category\":\"assumption_audit\",\"priority\":\"high\",\"confidence\":0.72,"
        "\"question\":\"What assumption could break this?\",\"next_step\":\"List top 1 assumption and test it.\","
        "\"rationale\":\"Assumptions drive hidden risk.\"}]}"
    )
    obj = scanner._extract_json_candidate(raw)
    assert isinstance(obj, dict)
    assert "opportunities" in obj


def test_extract_json_candidate_prefers_post_think_final_payload():
    # Ensure we do not accidentally parse an echoed schema JSON inside <think>.
    raw = (
        "<think> Output schema: {\"opportunities\":[{\"category\":\"...\",\"priority\":\"...\",\"confidence\":0.72,"
        "\"question\":\"...\",\"next_step\":\"...\",\"rationale\":\"...\"}]} </think>\n"
        "{\"opportunities\":[{\"category\":\"verification_gap\",\"priority\":\"high\",\"confidence\":0.8,"
        "\"question\":\"What proof validates this change?\",\"next_step\":\"Run one focused test.\",\"rationale\":\"Need evidence.\"}]}"
    )
    obj = scanner._extract_json_candidate(raw)
    rows = scanner._sanitize_llm_self_rows(obj)
    assert len(rows) == 1


def test_scan_runtime_opportunities_does_not_repersist_recent_duplicates(tmp_path, monkeypatch):
    # Isolate persistence to temp files.
    monkeypatch.setattr(scanner, "SELF_FILE", tmp_path / "self.jsonl")
    monkeypatch.setattr(scanner, "OUTCOME_FILE", tmp_path / "outcomes.jsonl")
    monkeypatch.setattr(scanner, "SCANNER_ENABLED", True)
    monkeypatch.setattr(scanner, "LLM_ENABLED", False)
    monkeypatch.setattr(scanner, "SELF_DEDUP_WINDOW_S", 3600.0)
    monkeypatch.setattr(scanner, "SELF_RECENT_LOOKBACK", 200)

    out1 = scanner.scan_runtime_opportunities(
        [_mk_event(EventType.USER_PROMPT, payload={"text": "Improve opportunity scanner reliability and usefulness"})],
        stats={},
        query="",
        session_id="s_dup",
        persist=True,
    )
    assert out1.get("persisted", 0) >= 1
    n1 = len((tmp_path / "self.jsonl").read_text(encoding="utf-8").splitlines())

    out2 = scanner.scan_runtime_opportunities(
        [_mk_event(EventType.USER_PROMPT, payload={"text": "Improve opportunity scanner reliability and usefulness"})],
        stats={},
        query="",
        session_id="s_dup",
        persist=True,
    )
    n2 = len((tmp_path / "self.jsonl").read_text(encoding="utf-8").splitlines())

    # Second run may still output repeated items, but it should not keep appending
    # identical questions into history inside the dedup window.
    assert n2 == n1


def test_select_diverse_self_rows_returns_empty_if_all_recent():
    candidates = [
        {
            "category": "humanity_guardrail",
            "priority": "medium",
            "confidence": 0.7,
            "question": "How does this help people and reduce downside?",
            "next_step": "State benefit and harm check.",
            "rationale": "x",
        }
    ]
    rk = {scanner._question_key("How does this help people and reduce downside?")}
    selected, filtered = scanner._select_diverse_self_rows(candidates, max_items=3, recent_keys=rk)
    assert selected == []
    assert filtered >= 1


def test_scan_runtime_opportunities_emits_nothing_when_no_context(monkeypatch, tmp_path):
    # No events + empty query should not emit evergreen prompts.
    monkeypatch.setattr(scanner, "SELF_FILE", tmp_path / "self.jsonl")
    monkeypatch.setattr(scanner, "OUTCOME_FILE", tmp_path / "outcomes.jsonl")
    monkeypatch.setattr(scanner, "SCANNER_ENABLED", True)
    monkeypatch.setattr(scanner, "LLM_ENABLED", True)

    out = scanner.scan_runtime_opportunities([], stats={}, query="", session_id="s0", persist=False)
    assert out.get("opportunities_found") == 0
    assert out.get("self_opportunities") == []
