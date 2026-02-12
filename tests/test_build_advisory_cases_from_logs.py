from __future__ import annotations

import importlib.util
import json
import sys
import time
from pathlib import Path


def _load_module():
    root = Path(__file__).resolve().parents[1]
    module_path = root / "benchmarks" / "build_advisory_cases_from_logs.py"
    spec = importlib.util.spec_from_file_location("build_advisory_cases_from_logs", module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError("failed to load build_advisory_cases_from_logs module")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_build_cases_from_recent_engine_rows(tmp_path):
    mod = _load_module()
    log = tmp_path / "advisory_engine.jsonl"
    now = time.time()
    rows = [
        {"ts": now - 10, "event": "no_emit", "tool": "Task", "error_code": "AE_GATE_SUPPRESSED", "route": "live"},
        {"ts": now - 9, "event": "no_emit", "tool": "Task", "error_code": "AE_GATE_SUPPRESSED", "route": "live"},
        {"ts": now - 8, "event": "emitted", "tool": "Read", "route": "live"},
    ]
    log.write_text("\n".join(json.dumps(r) for r in rows) + "\n", encoding="utf-8")

    cases = mod.build_cases(log, lookback_hours=1, limit=10)
    assert cases
    first = cases[0]
    assert first["tool"] == "Task"
    assert first["should_emit"] is False
