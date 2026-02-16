from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import SimpleNamespace


def _load_module():
    root = Path(__file__).resolve().parents[1]
    module_path = root / "benchmarks" / "memory_retrieval_ab.py"
    spec = importlib.util.spec_from_file_location("memory_retrieval_ab", module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError("failed to load memory_retrieval_ab module")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_classify_error_kind_mapping():
    mod = _load_module()

    assert mod.classify_error_kind("HTTP 401 unauthorized token missing") == "auth"
    assert mod.classify_error_kind("request timeout after 30s") == "timeout"
    assert mod.classify_error_kind("blocked by policy guardrail") == "policy"
    assert mod.classify_error_kind("connection refused by upstream") == "transport"
    assert mod.classify_error_kind("unhandled exception") == "unknown"


def test_compute_case_metrics_with_labels():
    mod = _load_module()

    case = mod.EvalCase(
        case_id="c1",
        query="auth token rotation",
        relevant_insight_keys=["key-2"],
        relevant_contains=[],
        notes="",
    )
    items = [
        mod.RetrievedItem(
            insight_key="key-1",
            text="first result",
            source="hybrid",
            semantic_score=0.9,
            fusion_score=0.9,
            score=0.9,
            why="",
        ),
        mod.RetrievedItem(
            insight_key="key-2",
            text="matching result",
            source="hybrid",
            semantic_score=0.8,
            fusion_score=0.8,
            score=0.8,
            why="",
        ),
    ]

    metrics = mod.compute_case_metrics(case, items, 2)
    assert metrics.hits == 1
    assert metrics.label_count == 1
    assert metrics.precision_at_k == 0.5
    assert metrics.recall_at_k == 1.0
    assert metrics.mrr == 0.5
    assert metrics.top1_hit is False


def test_compute_case_metrics_without_labels():
    mod = _load_module()
    case = mod.EvalCase(case_id="c2", query="any", notes="")
    items = []

    metrics = mod.compute_case_metrics(case, items, 5)
    assert metrics.precision_at_k is None
    assert metrics.recall_at_k is None
    assert metrics.mrr is None
    assert metrics.top1_hit is None
    assert metrics.hits == 0
    assert metrics.label_count == 0


def test_hybrid_lexical_scores_boost_term_frequency():
    mod = _load_module()
    scores = mod.hybrid_lexical_scores(
        "auth token session rollback",
        [
            "auth token session rollback",
            "auth token session rollback rollback",
        ],
        bm25_mix=0.9,
    )
    assert len(scores) == 2
    assert scores[1] > scores[0]


def test_retrieve_hybrid_filters_low_signal_candidates():
    mod = _load_module()

    class _Retriever:
        def retrieve(self, _query: str, _insights, limit: int = 8):
            return [
                SimpleNamespace(
                    insight_key="noise-1",
                    insight_text="I struggle with WebFetch_error tasks",
                    semantic_sim=0.86,
                    trigger_conf=0.0,
                    fusion_score=0.86,
                    source_type="semantic",
                    why="noise",
                ),
                SimpleNamespace(
                    insight_key="good-1",
                    insight_text="Use jittered retries to stabilize WebFetch transport timeouts.",
                    semantic_sim=0.83,
                    trigger_conf=0.0,
                    fusion_score=0.83,
                    source_type="semantic",
                    why="good",
                ),
            ][:limit]

    insights = {
        "noise-1": SimpleNamespace(insight="I struggle with WebFetch_error tasks", reliability=0.4),
        "good-1": SimpleNamespace(insight="Use jittered retries to stabilize WebFetch transport timeouts.", reliability=0.7),
    }
    out = mod.retrieve_hybrid(
        retriever=_Retriever(),
        insights=insights,
        query="webfetch transport timeout retries",
        top_k=3,
        candidate_k=8,
        lexical_weight=0.3,
        intent_coverage_weight=0.25,
        support_boost_weight=0.12,
        reliability_weight=0.1,
        semantic_intent_min=0.0,
        strict_filter=True,
        agentic=False,
    )
    keys = [row.insight_key for row in out]
    assert "noise-1" not in keys
    assert "good-1" in keys


def test_retrieve_hybrid_support_boost_rewards_cross_query_consistency():
    mod = _load_module()

    class _Retriever:
        def retrieve(self, query: str, _insights, limit: int = 8):
            if "failure pattern and fix" in query:
                return [
                    SimpleNamespace(
                        insight_key="shared",
                        insight_text="auth token session rollback fallback checklist",
                        semantic_sim=0.72,
                        trigger_conf=0.0,
                        fusion_score=0.72,
                        source_type="semantic",
                        why="facet",
                    )
                ][:limit]
            return [
                SimpleNamespace(
                    insight_key="shared",
                    insight_text="auth token session rollback fallback checklist",
                    semantic_sim=0.72,
                    trigger_conf=0.0,
                    fusion_score=0.72,
                    source_type="semantic",
                    why="primary",
                ),
                SimpleNamespace(
                    insight_key="one-off",
                    insight_text="auth token rollback note",
                    semantic_sim=0.78,
                    trigger_conf=0.0,
                    fusion_score=0.78,
                    source_type="semantic",
                    why="primary",
                ),
            ][:limit]

    insights = {
        "shared": SimpleNamespace(insight="auth token session rollback fallback checklist", reliability=0.6),
        "one-off": SimpleNamespace(insight="auth token rollback note", reliability=0.6),
    }
    out = mod.retrieve_hybrid(
        retriever=_Retriever(),
        insights=insights,
        query="auth token session rollback investigation",
        top_k=2,
        candidate_k=10,
        lexical_weight=0.0,
        intent_coverage_weight=0.0,
        support_boost_weight=0.35,
        reliability_weight=0.0,
        semantic_intent_min=0.0,
        strict_filter=True,
        agentic=True,
    )
    assert out
    assert out[0].insight_key == "shared"
