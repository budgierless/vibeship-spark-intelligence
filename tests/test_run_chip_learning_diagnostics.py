from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


def _load_module():
    root = Path(__file__).resolve().parents[1]
    module_path = root / "scripts" / "run_chip_learning_diagnostics.py"
    spec = importlib.util.spec_from_file_location("run_chip_learning_diagnostics", module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError("failed to load run_chip_learning_diagnostics")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_markdown_render_includes_core_metrics():
    mod = _load_module()
    report = {
        "generated_at": "2026-02-13T00:00:00+00:00",
        "limits": {"min_cognitive_value": 0.35},
        "rows_analyzed": 100,
        "merge_eligible": 3,
        "telemetry_rate": 0.9,
        "statement_yield_rate": 0.1,
        "learning_quality_pass_rate": 0.05,
        "chips": [
            {
                "chip_id": "marketing",
                "rows": 10,
                "telemetry_rate": 0.2,
                "statement_yield_rate": 0.4,
                "learning_quality_pass_rate": 0.3,
                "merge_eligible": 2,
                "sample_statements": ["Use evidence from campaign topic testing."],
            }
        ],
    }
    md = mod._md(report)
    assert "Chip Learning Diagnostics" in md
    assert "`marketing`" in md
    assert "Merge Eligible" in md
