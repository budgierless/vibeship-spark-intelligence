from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


def _load_module():
    root = Path(__file__).resolve().parents[1]
    module_path = root / "benchmarks" / "seed_advisory_theories.py"
    spec = importlib.util.spec_from_file_location("seed_advisory_theories", module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError("failed to load seed_advisory_theories module")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_should_keep_theory_respects_quality():
    mod = _load_module()
    theory = {"quality": "good"}
    assert mod.should_keep_theory(theory, "good") is True
    assert mod.should_keep_theory(theory, "bad") is False
    assert mod.should_keep_theory(theory, "all") is True


def test_build_insight_text_includes_source_and_id():
    mod = _load_module()
    text = mod.build_insight_text(
        {"id": "abc", "quality": "good", "insight": "Use trace-bound learning."},
        source_tag="seedtag",
    )
    assert "seedtag" in text
    assert "abc" in text
    assert "Use trace-bound learning." in text


def test_seed_theories_dry_run_returns_preview_only():
    mod = _load_module()
    theories = [
        {
            "id": "g1",
            "quality": "good",
            "category": "reasoning",
            "insight": "Tie advice to outcomes.",
            "context": "ops",
            "confidence": 0.8,
        },
        {
            "id": "b1",
            "quality": "bad",
            "category": "context",
            "insight": "Use one global fix.",
            "context": "anti-pattern",
            "confidence": 0.2,
        },
    ]

    out = mod.seed_theories(
        theories=theories,
        quality="good",
        source_tag="advisory_realism_seed",
        dry_run=True,
        record_exposure=False,
        limit=0,
    )
    assert out["selected"] == 1
    assert out["inserted"] == 0
    assert len(out["preview"]) == 1
    assert out["preview"][0]["id"] == "g1"
