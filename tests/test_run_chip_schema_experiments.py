from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


def _load_module():
    root = Path(__file__).resolve().parents[1]
    module_path = root / "scripts" / "run_chip_schema_experiments.py"
    spec = importlib.util.spec_from_file_location("run_chip_schema_experiments", module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError("failed to load run_chip_schema_experiments")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_objective_score_uses_weighted_metrics():
    mod = _load_module()
    metrics = {
        "capture_coverage": 0.7,
        "schema_payload_rate": 0.5,
        "schema_statement_rate": 0.4,
        "merge_eligible_rate": 0.3,
        "learning_quality_pass_rate": 0.8,
        "telemetry_rate": 0.9,
        "payload_valid_emission_rate": 0.75,
    }
    weights = {
        "capture_coverage": 0.3,
        "schema_payload_rate": 0.2,
        "schema_statement_rate": 0.3,
        "merge_eligible_rate": 0.2,
        "learning_quality_pass_rate": 0.1,
        "non_telemetry_rate": 0.1,
        "payload_valid_emission_rate": 0.1,
    }
    out = mod._objective_score(metrics, weights)
    assert out > 0.0
    assert out <= 1.0


def test_build_event_contains_required_fields():
    mod = _load_module()
    rng = __import__("random").Random(7)

    s = mod._build_event("social-convo", 0, rng)
    assert "tweet_id" in s and "outcome_type" in s

    e = mod._build_event("engagement-pulse", 0, rng)
    assert "tweet_id" in e and "snapshot_age" in e

    x = mod._build_event("x_social", 0, rng)
    assert "insight" in x and "confidence" in x
    assert isinstance(s.get("payload"), dict)
    assert isinstance(e.get("payload"), dict)
    assert isinstance(x.get("payload"), dict)


def test_promotion_gate_requires_candidate_beats_baseline_on_both():
    mod = _load_module()
    rows = [
        {"id": "A_schema_baseline", "objective": 0.7, "capture_coverage": 0.6},
        {"id": "B_schema_evidence2", "objective": 0.71, "capture_coverage": 0.59},
    ]
    out = mod._evaluate_promotion_gate(
        rows,
        baseline_id="A_schema_baseline",
        candidate_id="B_schema_evidence2",
        min_objective_delta=0.0,
        min_coverage_delta=0.0,
    )
    assert out["passed"] is False

    rows[1]["capture_coverage"] = 0.61
    out2 = mod._evaluate_promotion_gate(
        rows,
        baseline_id="A_schema_baseline",
        candidate_id="B_schema_evidence2",
        min_objective_delta=0.0,
        min_coverage_delta=0.0,
    )
    assert out2["passed"] is True


def test_promotion_gate_applies_candidate_quality_floors():
    mod = _load_module()
    rows = [
        {"id": "A", "objective": 0.7, "capture_coverage": 0.6, "telemetry_rate": 0.0, "schema_statement_rate": 1.0, "merge_eligible_rate": 0.2},
        {"id": "B", "objective": 0.75, "capture_coverage": 0.62, "telemetry_rate": 0.0, "schema_statement_rate": 1.0, "merge_eligible_rate": 0.0},
    ]
    out = mod._evaluate_promotion_gate(
        rows,
        baseline_id="A",
        candidate_id="B",
        min_objective_delta=0.0,
        min_coverage_delta=0.0,
        min_candidate_non_telemetry=0.9,
        min_candidate_schema_statement=0.9,
        min_candidate_merge_eligible=0.05,
    )
    assert out["passed"] is False
    assert "candidate_merge_eligible_below_floor" in out["reasons"]


def test_quality_effectively_empty_detects_zero_scores():
    mod = _load_module()
    assert mod._quality_effectively_empty({}) is True
    assert mod._quality_effectively_empty({"total": 0.0, "cognitive_value": 0.0}) is True
    assert mod._quality_effectively_empty({"total": 0.01}) is False


def test_stable_int_seed_is_deterministic():
    mod = _load_module()
    a = mod._stable_int_seed(20260217, "R3", "social-convo")
    b = mod._stable_int_seed(20260217, "R3", "social-convo")
    c = mod._stable_int_seed(20260217, "R3", "x_social")
    assert a == b
    assert a != c
