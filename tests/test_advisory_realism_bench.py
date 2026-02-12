from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


def _load_module():
    root = Path(__file__).resolve().parents[1]
    module_path = root / "benchmarks" / "advisory_realism_bench.py"
    spec = importlib.util.spec_from_file_location("advisory_realism_bench", module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError("failed to load advisory_realism_bench module")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_load_case_meta_parses_extended_fields(tmp_path):
    mod = _load_module()
    payload = {
        "cases": [
            {
                "id": "x1",
                "depth_tier": "D3",
                "domain": "strategy",
                "systems": ["advisory", "mind"],
                "importance": "critical",
                "theory_quality": "good",
                "expected_sources": ["mind", "semantic"],
                "forbidden_sources": ["chips"],
            }
        ]
    }
    path = tmp_path / "cases.json"
    path.write_text(__import__("json").dumps(payload), encoding="utf-8")

    meta = mod.load_case_meta(path)
    row = meta["x1"]
    assert row.depth_tier == "D3"
    assert row.domain == "strategy"
    assert row.importance == "critical"
    assert row.expected_sources == ["mind", "semantic"]


def test_source_alignment_rewards_expected_and_penalizes_forbidden():
    mod = _load_module()
    meta = mod.CaseMeta(
        case_id="c1",
        depth_tier="D2",
        domain="ops",
        systems=["advisory", "mind"],
        importance="high",
        theory_quality="good",
        expected_sources=["mind", "semantic"],
        forbidden_sources=["chips"],
    )

    strong = mod._source_alignment(meta, {"mind": 1, "semantic": 2})
    weak = mod._source_alignment(meta, {"chips": 1})
    assert strong > weak
    assert 0.0 <= weak <= 1.0


def test_summarize_realism_tracks_high_value_harmful_and_source_recall():
    mod = _load_module()
    meta = {
        "good_case": mod.CaseMeta(
            case_id="good_case",
            depth_tier="D2",
            domain="ops",
            systems=["advisory", "mind"],
            importance="critical",
            theory_quality="good",
            expected_sources=["mind"],
            forbidden_sources=[],
        ),
        "bad_case": mod.CaseMeta(
            case_id="bad_case",
            depth_tier="D1",
            domain="ops",
            systems=["advisory"],
            importance="high",
            theory_quality="bad",
            expected_sources=[],
            forbidden_sources=["semantic"],
        ),
    }
    run = {
        "summary": {"score": 0.71, "trace_bound_rate": 1.0},
        "cases": [
            {
                "case_id": "good_case",
                "should_emit": True,
                "emitted": True,
                "actionable": True,
                "trace_bound": True,
                "memory_utilized": True,
                "expected_hit_rate": 1.0,
                "forbidden_hit_rate": 0.0,
                "score": 0.9,
                "source_counts": {"mind": 1},
            },
            {
                "case_id": "bad_case",
                "should_emit": False,
                "emitted": True,
                "actionable": False,
                "trace_bound": True,
                "memory_utilized": True,
                "expected_hit_rate": 0.0,
                "forbidden_hit_rate": 1.0,
                "score": 0.2,
                "source_counts": {"semantic": 1},
            },
        ],
    }

    out = mod.summarize_realism(run, meta)
    assert out["high_value_rate"] == 0.5
    assert out["harmful_emit_rate"] == 0.5
    assert out["source_recall"]["mind"] == 1.0


def test_evaluate_gates_marks_pass_fail():
    mod = _load_module()
    realism = {
        "high_value_rate": 0.7,
        "harmful_emit_rate": 0.05,
        "critical_miss_rate": 0.0,
        "source_alignment_rate": 0.8,
        "theory_discrimination_rate": 0.8,
        "trace_bound_rate": 0.9,
    }
    checks = mod.evaluate_gates(realism, mod.REALISM_GATES)
    assert all(bool(v.get("ok")) for v in checks.values())


def test_theory_discrimination_counts_bad_theory_emit_mode():
    mod = _load_module()
    meta = {
        "bad_emit_case": mod.CaseMeta(
            case_id="bad_emit_case",
            depth_tier="D2",
            domain="ops",
            systems=["advisory"],
            importance="high",
            theory_quality="bad",
            expected_sources=[],
            forbidden_sources=[],
        )
    }
    run = {
        "summary": {"score": 0.7, "trace_bound_rate": 1.0},
        "cases": [
            {
                "case_id": "bad_emit_case",
                "should_emit": True,
                "emitted": True,
                "actionable": True,
                "trace_bound": True,
                "memory_utilized": True,
                "expected_hit_rate": 1.0,
                "forbidden_hit_rate": 0.0,
                "score": 0.9,
                "source_counts": {},
            }
        ],
    }
    out = mod.summarize_realism(run, meta)
    assert out["theory_discrimination_rate"] == 1.0
