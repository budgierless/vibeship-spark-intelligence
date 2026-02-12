from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


def _load_module():
    root = Path(__file__).resolve().parents[1]
    module_path = root / "scripts" / "apply_chip_profile_r3.py"
    spec = importlib.util.spec_from_file_location("apply_chip_profile_r3", module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError("failed to load apply_chip_profile_r3")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_apply_r3_sets_chip_merge_defaults(tmp_path):
    mod = _load_module()
    tuneables = tmp_path / "tuneables.json"
    tuneables.write_text('{"chip_merge":{"duplicate_churn_ratio":0.9}}', encoding="utf-8")
    out = mod.apply_r3(tuneables)
    merge = out.get("chip_merge") or {}
    assert merge["duplicate_churn_ratio"] == 0.9
    assert merge["min_cognitive_value"] == 0.25
    assert merge["min_actionability"] == 0.15
    assert merge["min_transferability"] == 0.15
    assert merge["min_statement_len"] == 20
