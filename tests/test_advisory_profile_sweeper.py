from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


def _load_module():
    root = Path(__file__).resolve().parents[1]
    module_path = root / "benchmarks" / "advisory_profile_sweeper.py"
    spec = importlib.util.spec_from_file_location("advisory_profile_sweeper", module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError("failed to load advisory_profile_sweeper module")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_build_candidate_profiles_and_subset():
    mod = _load_module()
    candidates = mod.build_candidate_profiles(
        advisory_text_repeat_grid=[1800, 3600],
        tool_cooldown_grid=[90, 120],
        advice_repeat_grid=[1800, 3600],
        min_rank_score_grid=[0.45, 0.5],
        max_items_grid=[4, 5],
        max_emit_per_call=1,
    )
    assert candidates
    assert all("name" in c for c in candidates)
    subset = mod.select_candidate_subset(candidates, max_candidates=3)
    assert 1 <= len(subset) <= 3


def test_objective_score_penalizes_no_emit_and_repeat():
    mod = _load_module()
    w = mod.SweepWeights()
    a = mod.objective_score(
        {
            "score": 0.8,
            "no_emit_rate": 0.1,
            "repetition_penalty_rate": 0.1,
            "actionability_rate": 0.8,
            "trace_bound_rate": 0.8,
        },
        w,
    )
    b = mod.objective_score(
        {
            "score": 0.8,
            "no_emit_rate": 0.5,
            "repetition_penalty_rate": 0.4,
            "actionability_rate": 0.8,
            "trace_bound_rate": 0.8,
        },
        w,
    )
    assert a > b
