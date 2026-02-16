#!/usr/bin/env python3
"""Apply benchmark-backed advisory/retrieval tuneables for high-quality retrieval."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict


def _deep_merge(base: Dict[str, Any], patch: Dict[str, Any]) -> Dict[str, Any]:
    out = dict(base)
    for key, value in patch.items():
        if isinstance(value, dict) and isinstance(out.get(key), dict):
            out[key] = _deep_merge(out.get(key) or {}, value)
        else:
            out[key] = value
    return out


def build_recommended_patch(retrieval_level: str = "2") -> Dict[str, Any]:
    level = str(retrieval_level or "2").strip()
    if level not in {"1", "2", "3"}:
        level = "2"
    return {
        "retrieval": {
            "level": level,
            "domain_profile_enabled": True,
            "overrides": {
                "intent_coverage_weight": 0.06,
                "support_boost_weight": 0.08,
                "reliability_weight": 0.04,
                "semantic_intent_min": 0.02,
            },
            "domain_profiles": {
                "memory": {
                    "semantic_limit": 12,
                    "max_queries": 4,
                    "agentic_query_limit": 4,
                    "lexical_weight": 0.40,
                    "intent_coverage_weight": 0.10,
                    "support_boost_weight": 0.10,
                    "reliability_weight": 0.05,
                    "semantic_intent_min": 0.03,
                    "min_results_no_escalation": 5,
                    "min_top_score_no_escalation": 0.74,
                },
                "coding": {
                    "semantic_limit": 11,
                    "lexical_weight": 0.34,
                    "intent_coverage_weight": 0.06,
                    "support_boost_weight": 0.08,
                    "reliability_weight": 0.04,
                    "semantic_intent_min": 0.02,
                },
                "x_social": {
                    "semantic_limit": 11,
                    "max_queries": 4,
                    "agentic_query_limit": 4,
                    "lexical_weight": 0.32,
                    "intent_coverage_weight": 0.08,
                    "support_boost_weight": 0.08,
                    "reliability_weight": 0.04,
                    "semantic_intent_min": 0.02,
                },
            },
        },
        "semantic": {
            "min_similarity": 0.50,
            "min_fusion_score": 0.45,
            "rescue_min_similarity": 0.30,
            "rescue_min_fusion_score": 0.20,
        },
        "advisor": {
            "max_items": 5,
            "max_advice_items": 5,
            "min_rank_score": 0.45,
        },
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="Apply benchmark-backed advisory/retrieval tuneables")
    ap.add_argument(
        "--path",
        default=str(Path.home() / ".spark" / "tuneables.json"),
        help="Tuneables JSON path",
    )
    ap.add_argument(
        "--retrieval-level",
        default="2",
        help="Retrieval profile level to pin (1|2|3, default 2)",
    )
    ap.add_argument(
        "--write",
        action="store_true",
        help="Persist changes (default is dry-run preview only)",
    )
    args = ap.parse_args()

    tuneables_path = Path(args.path)
    current: Dict[str, Any] = {}
    if tuneables_path.exists():
        try:
            current = json.loads(tuneables_path.read_text(encoding="utf-8-sig"))
            if not isinstance(current, dict):
                current = {}
        except Exception:
            current = {}

    patch = build_recommended_patch(args.retrieval_level)
    merged = _deep_merge(current, patch)

    print("Recommended advisory/retrieval tuneables patch:")
    print(json.dumps(patch, indent=2))
    print("")
    print(f"Target file: {tuneables_path}")
    if not args.write:
        print("Dry-run only. Re-run with --write to persist these changes.")
        return 0

    tuneables_path.parent.mkdir(parents=True, exist_ok=True)
    if tuneables_path.exists():
        ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        backup = tuneables_path.with_name(f"tuneables.backup_{ts}.json")
        backup.write_text(tuneables_path.read_text(encoding="utf-8-sig"), encoding="utf-8")
        print(f"Backup written: {backup}")
    tuneables_path.write_text(json.dumps(merged, indent=2), encoding="utf-8")
    print(f"Updated: {tuneables_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
