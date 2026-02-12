#!/usr/bin/env python3
"""Seed advisory theory examples into cognitive memory for realism runs.

This enables controlled memory payloads so advisory benchmarks can verify whether
semantic/cognitive retrieval surfaces the right guidance when it matters.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from lib.cognitive_learner import CognitiveCategory, get_cognitive_learner


def _normalize_quality(value: str) -> str:
    text = str(value or "").strip().lower()
    if text in {"good", "bad", "all"}:
        return text
    return "good"


def _coerce_conf(value: Any, default: float) -> float:
    try:
        conf = float(value)
    except Exception:
        conf = float(default)
    return max(0.05, min(0.99, conf))


def _category_from_text(value: Any) -> CognitiveCategory:
    text = str(value or "").strip().lower()
    mapping = {
        "self_awareness": CognitiveCategory.SELF_AWARENESS,
        "user_understanding": CognitiveCategory.USER_UNDERSTANDING,
        "reasoning": CognitiveCategory.REASONING,
        "context": CognitiveCategory.CONTEXT,
        "wisdom": CognitiveCategory.WISDOM,
        "meta_learning": CognitiveCategory.META_LEARNING,
        "communication": CognitiveCategory.COMMUNICATION,
        "creativity": CognitiveCategory.CREATIVITY,
    }
    return mapping.get(text, CognitiveCategory.WISDOM)


def load_theories(path: Path) -> List[Dict[str, Any]]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    rows = raw.get("theories", []) if isinstance(raw, dict) else raw
    if not isinstance(rows, list):
        raise ValueError("theory file must contain a list or object with 'theories' list")
    out: List[Dict[str, Any]] = []
    for row in rows:
        if isinstance(row, dict):
            out.append(row)
    return out


def should_keep_theory(theory: Dict[str, Any], quality: str) -> bool:
    q = str(theory.get("quality") or "").strip().lower()
    if quality == "all":
        return q in {"good", "bad"}
    return q == quality


def build_insight_text(theory: Dict[str, Any], source_tag: str) -> str:
    theory_id = str(theory.get("id") or "unknown").strip().lower()
    quality = str(theory.get("quality") or "unknown").strip().lower()
    insight = str(theory.get("insight") or "").strip()
    return f"[{source_tag}:{quality}:{theory_id}] {insight}".strip()


def seed_theories(
    *,
    theories: List[Dict[str, Any]],
    quality: str,
    source_tag: str,
    dry_run: bool,
    record_exposure: bool,
    limit: int,
) -> Dict[str, Any]:
    selected = [t for t in theories if should_keep_theory(t, quality=quality)]
    if limit > 0:
        selected = selected[:limit]

    preview: List[Dict[str, Any]] = []
    inserted = 0

    learner = None if dry_run else get_cognitive_learner()

    for theory in selected:
        insight_text = build_insight_text(theory, source_tag=source_tag)
        context = str(theory.get("context") or "").strip()
        systems = theory.get("systems") if isinstance(theory.get("systems"), list) else []
        if systems:
            context = (context + " | systems=" + ",".join(str(s) for s in systems if str(s).strip())).strip(" |")

        quality_label = str(theory.get("quality") or "").strip().lower()
        default_conf = 0.78 if quality_label == "good" else 0.2
        confidence = _coerce_conf(theory.get("confidence"), default_conf)
        category = _category_from_text(theory.get("category"))

        preview.append(
            {
                "id": str(theory.get("id") or ""),
                "quality": quality_label,
                "category": category.value,
                "confidence": confidence,
                "insight": insight_text,
                "context": context,
            }
        )

        if learner is not None:
            out = learner.add_insight(
                category=category,
                insight=insight_text,
                context=context,
                confidence=confidence,
                record_exposure=record_exposure,
                source=source_tag,
            )
            if out is not None:
                inserted += 1

    return {
        "quality": quality,
        "selected": len(selected),
        "inserted": inserted if not dry_run else 0,
        "dry_run": bool(dry_run),
        "preview": preview,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="Seed advisory theory catalog into cognitive memory")
    ap.add_argument(
        "--catalog",
        default=str(Path("benchmarks") / "data" / "advisory_theory_catalog_v1.json"),
        help="Path to theory catalog JSON",
    )
    ap.add_argument("--quality", default="good", choices=["good", "bad", "all"], help="Which theory quality to seed")
    ap.add_argument("--source-tag", default="advisory_realism_seed", help="Source tag prefix for seeded insights")
    ap.add_argument("--limit", type=int, default=0, help="Optional max theories to seed")
    ap.add_argument("--dry-run", action="store_true", help="Preview seeding without writing cognitive memory")
    ap.add_argument(
        "--record-exposure",
        action="store_true",
        help="Also create exposure records for seeded insights",
    )
    args = ap.parse_args()

    theories = load_theories(Path(args.catalog))
    result = seed_theories(
        theories=theories,
        quality=_normalize_quality(args.quality),
        source_tag=str(args.source_tag or "advisory_realism_seed").strip(),
        dry_run=bool(args.dry_run),
        record_exposure=bool(args.record_exposure),
        limit=max(0, int(args.limit)),
    )

    print(
        f"quality={result.get('quality')} "
        f"selected={int(result.get('selected', 0))} "
        f"inserted={int(result.get('inserted', 0))} "
        f"dry_run={bool(result.get('dry_run', False))}"
    )
    for row in list(result.get("preview") or [])[:5]:
        print(f"- {row.get('id')}: {str(row.get('insight') or '')[:120]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
