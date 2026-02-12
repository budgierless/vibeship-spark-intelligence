#!/usr/bin/env python3
"""Grid-search tuning for memory retrieval A/B systems.

Tunes systems independently, then compares their best configurations:
- embeddings_only
- hybrid
- hybrid_agentic
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Sequence, Tuple

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from benchmarks.memory_retrieval_ab import SUPPORTED_SYSTEMS, load_cases, run_system_for_case, summarize_system
from lib.cognitive_learner import get_cognitive_learner
from lib.semantic_retriever import SemanticRetriever


def _parse_float_grid(raw: str) -> List[float]:
    vals = []
    for part in (raw or "").split(","):
        part = part.strip()
        if not part:
            continue
        vals.append(float(part))
    if not vals:
        raise ValueError("empty float grid")
    return vals


def _parse_int_grid(raw: str) -> List[int]:
    vals = []
    for part in (raw or "").split(","):
        part = part.strip()
        if not part:
            continue
        vals.append(int(part))
    if not vals:
        raise ValueError("empty int grid")
    return vals


def _parse_systems(raw: str) -> List[str]:
    systems = [s.strip() for s in (raw or "").split(",") if s.strip()]
    bad = [s for s in systems if s not in SUPPORTED_SYSTEMS]
    if bad:
        raise ValueError(f"unsupported systems: {', '.join(bad)}")
    if not systems:
        raise ValueError("at least one system required")
    return systems


def _reset_embedding_backend(backend: str) -> None:
    os.environ["SPARK_EMBED_BACKEND"] = backend
    # Reset backend selector cache.
    import lib.embeddings as embeddings

    embeddings._BACKEND = None


def _score(summary: Dict[str, Any]) -> Tuple[float, float, float, float, float, float]:
    # Quality first, then reliability, then latency.
    return (
        float(summary.get("mrr") or -1.0),
        float(summary.get("precision_at_k") or -1.0),
        float(summary.get("top1_hit_rate") or -1.0),
        float(summary.get("non_empty_rate") or 0.0),
        -float(summary.get("error_rate") or 0.0),
        -float(summary.get("latency_ms_p95") or 0.0),
    )


def _evaluate(
    *,
    system: str,
    cases: Sequence[Any],
    insights: Dict[str, Any],
    noise_filter: Any,
    top_k: int,
    candidate_k: int,
    lexical_weight: float,
    min_similarity: float,
    min_fusion_score: float,
) -> Dict[str, Any]:
    retriever = SemanticRetriever()
    retriever.config["triggers_enabled"] = False
    retriever.config["log_retrievals"] = False
    retriever.config["min_similarity"] = float(min_similarity)
    retriever.config["min_fusion_score"] = float(min_fusion_score)

    rows: List[Dict[str, Any]] = []
    for case in cases:
        rows.append(
            run_system_for_case(
                system=system,
                case=case,
                retriever=retriever,
                insights=insights,
                noise_filter=noise_filter,
                top_k=top_k,
                candidate_k=candidate_k,
                lexical_weight=lexical_weight,
            )
        )
    summary = summarize_system(system, rows)
    return {
        "summary": summary,
        "rows": rows,
        "params": {
            "candidate_k": candidate_k,
            "lexical_weight": lexical_weight,
            "min_similarity": min_similarity,
            "min_fusion_score": min_fusion_score,
        },
    }


def _search_best(
    *,
    system: str,
    train_cases: Sequence[Any],
    insights: Dict[str, Any],
    noise_filter: Any,
    top_k: int,
    candidate_grid: Sequence[int],
    lexical_grid: Sequence[float],
    min_similarity_grid: Sequence[float],
    min_fusion_grid: Sequence[float],
) -> Dict[str, Any]:
    best: Dict[str, Any] | None = None
    trials = 0
    for candidate_k in candidate_grid:
        # embeddings_only does not use lexical/fusion gates in its path.
        effective_lexical = lexical_grid if system != "embeddings_only" else [0.0]
        effective_min_sim = min_similarity_grid if system != "embeddings_only" else [0.0]
        effective_min_fusion = min_fusion_grid if system != "embeddings_only" else [0.0]
        for lexical in effective_lexical:
            for min_sim in effective_min_sim:
                for min_fusion in effective_min_fusion:
                    trials += 1
                    run = _evaluate(
                        system=system,
                        cases=train_cases,
                        insights=insights,
                        noise_filter=noise_filter,
                        top_k=top_k,
                        candidate_k=int(candidate_k),
                        lexical_weight=float(lexical),
                        min_similarity=float(min_sim),
                        min_fusion_score=float(min_fusion),
                    )
                    if best is None or _score(run["summary"]) > _score(best["summary"]):
                        best = run
    assert best is not None
    best["trials"] = trials
    return best


def main() -> int:
    parser = argparse.ArgumentParser(description="Tune memory retrieval systems and compare best configs")
    parser.add_argument(
        "--cases",
        default=str(Path("benchmarks") / "data" / "memory_retrieval_eval_real_user_2026_02_12.json"),
        help="Path to benchmark cases JSON",
    )
    parser.add_argument(
        "--systems",
        default="embeddings_only,hybrid_agentic",
        help=f"Comma-separated systems ({', '.join(SUPPORTED_SYSTEMS)})",
    )
    parser.add_argument("--backend", default="tfidf", help="Embedding backend: tfidf|fastembed")
    parser.add_argument("--top-k", type=int, default=5)
    parser.add_argument("--train-ratio", type=float, default=0.7, help="Train split ratio")
    parser.add_argument("--candidate-grid", default="20,40,60")
    parser.add_argument("--lexical-grid", default="0.15,0.35,0.55,0.75")
    parser.add_argument("--min-similarity-grid", default="0.0,0.2,0.35,0.5")
    parser.add_argument("--min-fusion-grid", default="0.0,0.15,0.3,0.45")
    parser.add_argument("--case-limit", type=int, default=0)
    parser.add_argument("--out", default=str(Path("benchmarks") / "out" / "memory_retrieval_ab_tuning_report.json"))
    args = parser.parse_args()

    _reset_embedding_backend(args.backend)
    systems = _parse_systems(args.systems)
    cases = load_cases(Path(args.cases))
    if args.case_limit and args.case_limit > 0:
        cases = cases[: args.case_limit]
    if len(cases) < 4:
        raise ValueError("need at least 4 cases for train/dev split")

    split = max(1, min(len(cases) - 1, int(len(cases) * float(args.train_ratio))))
    train_cases = cases[:split]
    dev_cases = cases[split:]

    learner = get_cognitive_learner()
    insights = dict(getattr(learner, "insights", {}) or {})
    noise_filter = getattr(learner, "is_noise_insight", None)

    candidate_grid = _parse_int_grid(args.candidate_grid)
    lexical_grid = _parse_float_grid(args.lexical_grid)
    min_similarity_grid = _parse_float_grid(args.min_similarity_grid)
    min_fusion_grid = _parse_float_grid(args.min_fusion_grid)

    tuned: Dict[str, Any] = {}
    comparison_dev: List[Dict[str, Any]] = []
    comparison_full: List[Dict[str, Any]] = []

    for system in systems:
        best_train = _search_best(
            system=system,
            train_cases=train_cases,
            insights=insights,
            noise_filter=noise_filter,
            top_k=max(1, int(args.top_k)),
            candidate_grid=candidate_grid,
            lexical_grid=lexical_grid,
            min_similarity_grid=min_similarity_grid,
            min_fusion_grid=min_fusion_grid,
        )

        params = best_train["params"]
        dev_run = _evaluate(
            system=system,
            cases=dev_cases,
            insights=insights,
            noise_filter=noise_filter,
            top_k=max(1, int(args.top_k)),
            candidate_k=int(params["candidate_k"]),
            lexical_weight=float(params["lexical_weight"]),
            min_similarity=float(params["min_similarity"]),
            min_fusion_score=float(params["min_fusion_score"]),
        )
        full_run = _evaluate(
            system=system,
            cases=cases,
            insights=insights,
            noise_filter=noise_filter,
            top_k=max(1, int(args.top_k)),
            candidate_k=int(params["candidate_k"]),
            lexical_weight=float(params["lexical_weight"]),
            min_similarity=float(params["min_similarity"]),
            min_fusion_score=float(params["min_fusion_score"]),
        )

        tuned[system] = {
            "trials": best_train["trials"],
            "best_train": {
                "params": params,
                "summary": best_train["summary"],
            },
            "best_dev": {
                "params": params,
                "summary": dev_run["summary"],
            },
            "best_full": {
                "params": params,
                "summary": full_run["summary"],
            },
        }
        comparison_dev.append(dev_run["summary"])
        comparison_full.append(full_run["summary"])

    comparison_dev_sorted = sorted(comparison_dev, key=_score, reverse=True)
    comparison_full_sorted = sorted(comparison_full, key=_score, reverse=True)

    report = {
        "meta": {
            "timestamp_utc": datetime.now(timezone.utc).isoformat(),
            "backend": args.backend,
            "cases_file": str(args.cases),
            "case_count": len(cases),
            "train_count": len(train_cases),
            "dev_count": len(dev_cases),
            "systems": systems,
            "top_k": int(args.top_k),
            "candidate_grid": candidate_grid,
            "lexical_grid": lexical_grid,
            "min_similarity_grid": min_similarity_grid,
            "min_fusion_grid": min_fusion_grid,
            "insight_count": len(insights),
            "python": sys.version.split()[0],
        },
        "tuned": tuned,
        "comparison": {
            "dev": comparison_dev_sorted,
            "full": comparison_full_sorted,
            "winner_dev": comparison_dev_sorted[0]["system"] if comparison_dev_sorted else "none",
            "winner_full": comparison_full_sorted[0]["system"] if comparison_full_sorted else "none",
        },
    }

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(report, indent=2), encoding="utf-8")

    print(f"[tune] wrote {out_path}")
    print(f"[tune] backend={args.backend}")
    print(f"[tune] winner_dev={report['comparison']['winner_dev']}")
    print(f"[tune] winner_full={report['comparison']['winner_full']}")
    for system in systems:
        item = tuned[system]
        params = item["best_full"]["params"]
        summary = item["best_full"]["summary"]
        print(
            f"[tune] {system}: params={params} "
            f"mrr={summary.get('mrr')} p@k={summary.get('precision_at_k')} "
            f"top1={summary.get('top1_hit_rate')} p95={summary.get('latency_ms_p95')}ms"
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
