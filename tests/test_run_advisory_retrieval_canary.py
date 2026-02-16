from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


def _load_module():
    root = Path(__file__).resolve().parents[1]
    module_path = root / "scripts" / "run_advisory_retrieval_canary.py"
    spec = importlib.util.spec_from_file_location("run_advisory_retrieval_canary", module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError("failed to load run_advisory_retrieval_canary")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_evaluate_passes_when_all_thresholds_met():
    mod = _load_module()
    memory_report = {"weighted": {"mrr": 0.5, "domain_gate_pass_rate": 0.8}}
    advisory_report = {"winner": {"profile": "baseline", "summary": {"score": 0.75}}}
    out = mod._evaluate(
        memory_report=memory_report,
        advisory_report=advisory_report,
        mrr_min=0.4,
        gate_pass_rate_min=0.6,
        advisory_score_min=0.7,
    )
    assert out["all_pass"] is True
    assert all(out["checks"].values())


def test_evaluate_fails_when_thresholds_missed():
    mod = _load_module()
    memory_report = {"weighted": {"mrr": 0.2, "domain_gate_pass_rate": 0.2}}
    advisory_report = {"winner": {"profile": "strict", "summary": {"score": 0.5}}}
    out = mod._evaluate(
        memory_report=memory_report,
        advisory_report=advisory_report,
        mrr_min=0.4,
        gate_pass_rate_min=0.6,
        advisory_score_min=0.7,
    )
    assert out["all_pass"] is False
    assert not all(out["checks"].values())
