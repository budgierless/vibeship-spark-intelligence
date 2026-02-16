from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


def _load_module():
    root = Path(__file__).resolve().parents[1]
    module_path = root / "scripts" / "apply_advisory_wow_tuneables.py"
    spec = importlib.util.spec_from_file_location("apply_advisory_wow_tuneables", module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError("failed to load apply_advisory_wow_tuneables")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_build_recommended_patch_contains_domain_profiles():
    mod = _load_module()
    patch = mod.build_recommended_patch("2")
    retrieval = patch.get("retrieval") or {}
    domains = retrieval.get("domain_profiles") or {}
    assert retrieval.get("level") == "2"
    assert retrieval.get("domain_profile_enabled") is True
    assert "memory" in domains
    assert float((domains.get("memory") or {}).get("lexical_weight", 0.0)) >= 0.35


def test_deep_merge_preserves_existing_keys():
    mod = _load_module()
    base = {
        "semantic": {"enabled": True, "min_similarity": 0.58},
        "retrieval": {"level": "1", "overrides": {"lexical_weight": 0.2}},
    }
    patch = {
        "semantic": {"min_similarity": 0.5},
        "retrieval": {"level": "2", "overrides": {"intent_coverage_weight": 0.1}},
    }
    merged = mod._deep_merge(base, patch)
    assert merged["semantic"]["enabled"] is True
    assert merged["semantic"]["min_similarity"] == 0.5
    assert merged["retrieval"]["level"] == "2"
    assert merged["retrieval"]["overrides"]["lexical_weight"] == 0.2
    assert merged["retrieval"]["overrides"]["intent_coverage_weight"] == 0.1
