#!/usr/bin/env python3
"""Seed helper for advisory theory tests and local benchmark workflows."""

from __future__ import annotations

from typing import Iterable, List, Mapping


def should_keep_theory(theory: Mapping[str, object], quality_filter: str) -> bool:
    """Return whether a theory matches the requested quality bucket."""
    if theory is None:
        return False

    q = str(theory.get("quality", "")).strip().lower()
    quality = str(quality_filter or "").strip().lower()

    if quality == "all":
        return True
    return q == quality


def build_insight_text(theory: Mapping[str, object], source_tag: str) -> str:
    """Build one-line text for preview/display in logs and CLI output."""
    theory_id = str(theory.get("id", "unknown"))
    insight = str(theory.get("insight", "")).strip()
    return f"{source_tag}:{theory_id}:{insight}"


def seed_theories(
    *,
    theories: Iterable[Mapping[str, object]],
    quality: str = "all",
    source_tag: str = "seedtag",
    dry_run: bool = True,
    record_exposure: bool = False,
    limit: int = 0,
) -> dict:
    """Return a selection summary for a list of theories.

    This helper intentionally keeps behavior lightweight for tests: it filters
    theories, builds preview entries, and reports counts. No external systems
    are touched.
    """
    selected = [t for t in list(theories or []) if should_keep_theory(t, quality)]

    preview_cap = limit if isinstance(limit, int) and limit > 0 else None
    preview_items = list(selected if preview_cap is None else selected[:preview_cap])

    preview = []
    for theory in preview_items:
        insight_text = build_insight_text(theory, source_tag)
        row = {
            "id": str(theory.get("id", "")),
            "quality": theory.get("quality"),
            "text": insight_text,
        }
        if "category" in theory:
            row["category"] = theory.get("category")
        if "confidence" in theory:
            row["confidence"] = theory.get("confidence")
        if "context" in theory:
            row["context"] = theory.get("context")
        preview.append(row)

    inserted = 0 if dry_run else len(selected)
    return {
        "selected": len(selected),
        "inserted": inserted,
        "preview": preview,
        "quality_filter": quality,
        "record_exposure": bool(record_exposure),
    }


def main(argv: List[str] | None = None) -> int:
    # Lightweight CLI for manual ad hoc use:
    #  python benchmarks/seed_advisory_theories.py --quality good --dry-run 0
    import argparse

    parser = argparse.ArgumentParser(description="Seed advisory theories (compat helper)")
    parser.add_argument("--quality", default="all")
    parser.add_argument("--source", default="seedtag")
    parser.add_argument("--limit", type=int, default=20)
    parser.add_argument("--dry-run", action="store_true", default=True)
    args, _ = parser.parse_known_args(argv)

    # Example payload; real catalog mode can be implemented in the future.
    sample = [
        {"id": "good-1", "quality": "good", "insight": "Use trace-bound memory first."},
        {"id": "bad-1", "quality": "bad", "insight": "Fallback-only guidance."},
    ]

    result = seed_theories(theories=sample, quality=args.quality, source_tag=args.source, dry_run=args.dry_run, limit=args.limit)
    print(f"selected={result['selected']} inserted={result['inserted']}")
    if result["preview"]:
        print("preview:")
        for item in result["preview"]:
            print(f"- {item['text']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
