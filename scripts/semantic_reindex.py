#!/usr/bin/env python3
"""Rebuild semantic index for cognitive insights."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from lib.semantic_retriever import SemanticIndex  # noqa: E402
from lib.cognitive_learner import get_cognitive_learner  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=0, help="max insights to index (0 = all)")
    ap.add_argument("--batch", type=int, default=100, help="batch size")
    args = ap.parse_args()

    learner = get_cognitive_learner()
    index = SemanticIndex()

    items = list(learner.insights.items())
    # Prioritize higher reliability first
    items.sort(key=lambda kv: getattr(kv[1], "reliability", 0.5), reverse=True)
    if args.limit and args.limit > 0:
        items = items[: args.limit]

    payload = []
    for key, insight in items:
        text = f"{getattr(insight, 'insight', '')} {getattr(insight, 'context', '')}".strip()
        if not text:
            continue
        payload.append((key, text))

    total = 0
    for i in range(0, len(payload), max(1, args.batch)):
        total += index.add_many(payload[i : i + args.batch])

    print(f"[semantic] indexed {total} items (of {len(payload)} eligible)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
