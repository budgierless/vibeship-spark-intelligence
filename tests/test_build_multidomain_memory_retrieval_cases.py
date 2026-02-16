from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path


def _load_module():
    root = Path(__file__).resolve().parents[1]
    module_path = root / "scripts" / "build_multidomain_memory_retrieval_cases.py"
    spec = importlib.util.spec_from_file_location("build_multidomain_memory_retrieval_cases", module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError("failed to load build_multidomain_memory_retrieval_cases")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_build_cases_infers_domain_and_labels(tmp_path):
    mod = _load_module()
    payload = {
        "cases": [
            {
                "id": "c1",
                "query": "debug python traceback in module",
                "relevant_contains": [],
                "notes": "from user",
            },
            {
                "id": "c2",
                "prompt": "tweet engagement strategy and reply quality",
                "expected_contains": ["engagement", "quality"],
                "notes": "social case",
            },
        ]
    }
    path = tmp_path / "cases.json"
    path.write_text(json.dumps(payload), encoding="utf-8")

    out = mod.build_cases([path])
    assert len(out) == 2
    by_id = {row["id"]: row for row in out}
    assert by_id["c1"]["domain"] == "coding"
    assert by_id["c1"]["relevant_contains"]  # extracted fallback labels
    assert by_id["c2"]["domain"] == "x_social"
    assert "engagement" in by_id["c2"]["relevant_contains"]
