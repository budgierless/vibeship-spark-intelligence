from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from lib.chips.loader import Chip, ChipObserver
from lib.chips.router import TriggerMatch
from lib.chips import runtime as runtime_mod


class _DummyRegistry:
    def auto_activate_for_content(self, _content: str, _project_path: str | None = None):
        return []

    def get_active_chips(self, _project_path: str | None = None):
        return []


class _DummyRouter:
    def route_event(self, _event, _chips):
        return []


class _DummyEvolution:
    def record_match(self, *_args, **_kwargs):
        return None


def _chip(chip_id: str) -> Chip:
    return Chip(
        id=chip_id,
        name=chip_id,
        version="1.0.0",
        description="test",
        domains=[],
        triggers=[],
        observers=[],
        learners=[],
        outcomes_positive=[],
        outcomes_negative=[],
        outcomes_neutral=[],
        questions=[],
        trigger_patterns=[],
        trigger_events=[],
        trigger_tools=[],
        activation="opt_in",
        source_path=Path("chips") / f"{chip_id}.chip.yaml",
    )


def _build_runtime(monkeypatch, tmp_path):
    monkeypatch.setattr(runtime_mod, "ChipRegistry", lambda: _DummyRegistry())
    monkeypatch.setattr(runtime_mod, "ChipRouter", lambda: _DummyRouter())
    monkeypatch.setattr(runtime_mod, "get_evolution", lambda: _DummyEvolution())
    monkeypatch.setattr(runtime_mod, "CHIP_INSIGHTS_DIR", tmp_path / "chip_insights")
    return runtime_mod.ChipRuntime()


def test_observer_only_mode_skips_chip_level_matches(monkeypatch, tmp_path):
    monkeypatch.delenv("SPARK_CHIP_OBSERVER_ONLY", raising=False)
    runtime = _build_runtime(monkeypatch, tmp_path)
    assert runtime.observer_only_mode is True

    called = {"n": 0}

    def _spy(_match, _event):
        called["n"] += 1
        return None

    monkeypatch.setattr(runtime, "_execute_observer", _spy)

    match = TriggerMatch(
        chip=_chip("marketing"),
        observer=None,
        trigger="post_tool",
        confidence=0.95,
        content_snippet="post_tool",
    )
    out = runtime._process_matches([match], {"event_type": "post_tool"})
    assert out == []
    assert called["n"] == 0


def test_telemetry_observer_blocklist_skips_runtime_emission(monkeypatch, tmp_path):
    runtime = _build_runtime(monkeypatch, tmp_path)

    called = {"n": 0}

    def _spy(_match, _event):
        called["n"] += 1
        return None

    monkeypatch.setattr(runtime, "_execute_observer", _spy)

    observer = ChipObserver(
        name="post_tool_use",
        description="telemetry observer",
        triggers=["post_tool"],
        capture_required={},
        capture_optional={},
        extraction=[],
    )
    match = TriggerMatch(
        chip=_chip("vibecoding"),
        observer=observer,
        trigger="post_tool",
        confidence=0.95,
        content_snippet="post_tool",
    )

    out = runtime._process_matches([match], {"event_type": "post_tool"})
    assert out == []
    assert called["n"] == 0


def test_blocked_chip_ids_filter_runtime_chip_set(monkeypatch, tmp_path):
    monkeypatch.setenv("SPARK_CHIP_BLOCKED_IDS", "bench_core,spark-core")
    runtime = _build_runtime(monkeypatch, tmp_path)

    filtered = runtime._filter_runtime_chips(
        [_chip("bench_core"), _chip("spark-core"), _chip("marketing")]
    )
    assert [c.id for c in filtered] == ["marketing"]


def test_execute_observer_builds_learning_payload(monkeypatch, tmp_path):
    runtime = _build_runtime(monkeypatch, tmp_path)
    observer = ChipObserver(
        name="reply_effectiveness",
        description="captures outcomes",
        triggers=["reply performance"],
        capture_required={"outcome_type": "result type"},
        capture_optional={"likes": "like count"},
        extraction=[],
    )
    match = TriggerMatch(
        chip=_chip("social-convo"),
        observer=observer,
        trigger="reply performance",
        confidence=0.95,
        content_snippet="reply performance",
    )
    event = {
        "event_type": "post_tool",
        "outcome_type": "positive",
        "likes": 21,
        "status": "success",
        "content": "Reply got meaningful engagement on AI builders topic.",
    }

    insight = runtime._execute_observer(match, event)
    assert insight is not None
    payload = (insight.captured_data or {}).get("learning_payload")
    assert isinstance(payload, dict)
    assert runtime._is_learning_payload_valid(payload) is True
    assert "decision" in payload and "evidence" in payload


def test_runtime_gate_requires_valid_learning_payload(monkeypatch, tmp_path):
    runtime = _build_runtime(monkeypatch, tmp_path)
    runtime.require_learning_schema = True
    match = TriggerMatch(
        chip=_chip("marketing"),
        observer=None,
        trigger="post_tool",
        confidence=0.95,
        content_snippet="post_tool",
    )
    score = SimpleNamespace(
        promotion_tier="keep",
        total=0.9,
        outcome_linkage=0.2,
    )

    invalid = runtime_mod.ChipInsight(
        chip_id="marketing",
        observer_name="chip_level",
        trigger="post_tool",
        content="Useful content",
        captured_data={},
        confidence=0.95,
        timestamp="2026-02-13T00:00:00",
        event_summary="post_tool:Bash",
    )
    assert runtime._passes_runtime_gate(match, invalid, score) is False

    valid = runtime_mod.ChipInsight(
        chip_id="marketing",
        observer_name="reply_effectiveness",
        trigger="post_tool",
        content="Prefer reply patterns that show evidence.",
        captured_data={
            "learning_payload": {
                "schema_version": "v1",
                "decision": "Prefer this pattern for similar conversations.",
                "rationale": "Because reply outcome and engagement evidence support it.",
                "evidence": ["outcome_type=positive", "likes=21"],
                "expected_outcome": "Improve success rate on similar replies.",
            }
        },
        confidence=0.95,
        timestamp="2026-02-13T00:00:01",
        event_summary="post_tool:Bash",
    )
    assert runtime._passes_runtime_gate(match, valid, score) is True
