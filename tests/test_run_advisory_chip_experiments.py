from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


def _load_module():
    root = Path(__file__).resolve().parents[1]
    module_path = root / "scripts" / "run_advisory_chip_experiments.py"
    spec = importlib.util.spec_from_file_location("run_advisory_chip_experiments", module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError("failed to load run_advisory_chip_experiments")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_source_hit_rates_distinguish_advice_vs_evidence():
    mod = _load_module()
    winner = {
        "cases": [
            {
                "source_counts": {"chips": 4, "mind": 2, "semantic": 1},
                "advice_source_counts": {"cognitive": 1},
            },
            {
                "source_counts": {"chips": 3},
                "advice_source_counts": {"chip": 1},
            },
        ]
    }
    out = mod._winner_source_hit_rates(winner)
    assert out["chip_hit_case_rate"] == 0.5
    assert out["chip_evidence_case_rate"] == 1.0
    assert out["mind_hit_case_rate"] == 0.0
    assert out["mind_evidence_case_rate"] == 0.5
    assert out["semantic_hit_case_rate"] == 0.0
    assert out["semantic_evidence_case_rate"] == 0.5


def test_source_hit_rates_empty_cases():
    mod = _load_module()
    out = mod._winner_source_hit_rates({"cases": []})
    assert out["chip_hit_case_rate"] == 0.0
    assert out["chip_evidence_case_rate"] == 0.0
