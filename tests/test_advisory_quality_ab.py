from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path


def _load_module():
    root = Path(__file__).resolve().parents[1]
    module_path = root / "benchmarks" / "advisory_quality_ab.py"
    spec = importlib.util.spec_from_file_location("advisory_quality_ab", module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError("failed to load advisory_quality_ab module")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_evaluate_text_expectations():
    mod = _load_module()
    text = "Use precise checks. Next check: `python -m pytest -q`."
    expected, forbidden = mod.evaluate_text_expectations(
        text,
        expected_contains=["next check", "pytest"],
        forbidden_contains=["multiplier granted", "money printer"],
    )
    assert expected == 1.0
    assert forbidden == 0.0


def test_score_case_prefers_correct_emission_and_actionability():
    mod = _load_module()
    strong = mod.score_case(
        should_emit=True,
        emitted=True,
        expected_hit_rate=1.0,
        forbidden_hit_rate=0.0,
        actionable=True,
        trace_bound=True,
        memory_utilized=True,
    )
    weak = mod.score_case(
        should_emit=True,
        emitted=False,
        expected_hit_rate=0.0,
        forbidden_hit_rate=1.0,
        actionable=False,
        trace_bound=False,
        memory_utilized=False,
    )
    assert strong > weak
    assert strong <= 1.0
    assert weak >= 0.0


def test_load_cases_parses_seed_format(tmp_path):
    mod = _load_module()
    payload = {
        "cases": [
            {
                "id": "c1",
                "tool": "Read",
                "prompt": "Inspect implementation",
                "tool_input": {"file_path": "a.py"},
                "should_emit": True,
                "expected_contains": ["next check"],
                "forbidden_contains": ["noise"],
            }
        ]
    }
    path = tmp_path / "cases.json"
    path.write_text(json.dumps(payload), encoding="utf-8")

    cases = mod.load_cases(path)
    assert len(cases) == 1
    assert cases[0].case_id == "c1"
    assert cases[0].tool == "Read"
    assert cases[0].tool_input["file_path"] == "a.py"


def test_summarize_profile_repetition_penalty_applies():
    mod = _load_module()
    results = [
        mod.CaseResult(
            case_id="a",
            tool="Read",
            should_emit=True,
            emitted=True,
            route="live",
            event="emitted",
            error_code="",
            trace_bound=True,
            expected_hit_rate=1.0,
            forbidden_hit_rate=0.0,
            actionable=True,
            memory_utilized=True,
            text_preview="first",
            score=0.9,
        ),
        mod.CaseResult(
            case_id="b",
            tool="Read",
            should_emit=True,
            emitted=True,
            route="live",
            event="emitted",
            error_code="",
            trace_bound=True,
            expected_hit_rate=1.0,
            forbidden_hit_rate=0.0,
            actionable=True,
            memory_utilized=True,
            text_preview="second",
            score=0.9,
        ),
    ]
    no_repeat = mod.summarize_profile(
        profile_name="p1",
        case_results=results,
        latencies=[100, 120],
        emitted_texts=["alpha", "beta"],
    )
    repeated = mod.summarize_profile(
        profile_name="p1",
        case_results=results,
        latencies=[100, 120],
        emitted_texts=["alpha", "alpha"],
    )
    assert repeated.repetition_penalty_rate > no_repeat.repetition_penalty_rate
    assert repeated.score < no_repeat.score


def test_summarize_profile_tracks_no_emit_error_codes():
    mod = _load_module()
    results = [
        mod.CaseResult(
            case_id="a",
            tool="Read",
            should_emit=True,
            emitted=False,
            route="live",
            event="no_emit",
            error_code="AE_GATE_SUPPRESSED",
            trace_bound=True,
            expected_hit_rate=0.0,
            forbidden_hit_rate=0.0,
            actionable=False,
            memory_utilized=True,
            text_preview="",
            score=0.5,
        ),
        mod.CaseResult(
            case_id="b",
            tool="Read",
            should_emit=True,
            emitted=False,
            route="live",
            event="no_emit",
            error_code="AE_GATE_SUPPRESSED",
            trace_bound=True,
            expected_hit_rate=0.0,
            forbidden_hit_rate=0.0,
            actionable=False,
            memory_utilized=True,
            text_preview="",
            score=0.5,
        ),
        mod.CaseResult(
            case_id="c",
            tool="Read",
            should_emit=True,
            emitted=False,
            route="live",
            event="no_emit",
            error_code="AE_DUPLICATE_SUPPRESSED",
            trace_bound=True,
            expected_hit_rate=0.0,
            forbidden_hit_rate=0.0,
            actionable=False,
            memory_utilized=True,
            text_preview="",
            score=0.5,
        ),
    ]
    summary = mod.summarize_profile(
        profile_name="p1",
        case_results=results,
        latencies=[100, 110, 120],
        emitted_texts=[],
    )
    assert summary.no_emit_error_codes[0][0] == "AE_GATE_SUPPRESSED"
    assert summary.no_emit_error_codes[0][1] == 2
