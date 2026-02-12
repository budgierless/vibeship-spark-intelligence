from __future__ import annotations

from pathlib import Path

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
