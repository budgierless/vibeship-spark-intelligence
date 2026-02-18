#!/usr/bin/env python3
"""Archive repetitive advisory self-review reports into docs/archive."""

from __future__ import annotations

import argparse
import shutil
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Move old '*_advisory_self_review.md' reports into a run archive folder."
    )
    parser.add_argument(
        "--source",
        default="docs/reports",
        help="Source reports directory (default: docs/reports).",
    )
    parser.add_argument(
        "--target",
        default="docs/archive/docs/reports_self_review",
        help="Archive destination directory (tracked).",
    )
    parser.add_argument(
        "--keep-latest",
        type=int,
        default=3,
        help="How many latest files to keep in source (default: 3).",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Apply file moves. Without this flag, runs as dry-run.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    source = Path(args.source)
    target = Path(args.target)

    if not source.exists():
        raise SystemExit(f"Source directory does not exist: {source}")

    files = sorted(source.glob("*_advisory_self_review.md"), key=lambda p: p.name)
    keep_latest = max(0, args.keep_latest)

    if keep_latest >= len(files):
        print(f"No archive action needed: found={len(files)} keep_latest={keep_latest}")
        return 0

    keep = set(files[-keep_latest:]) if keep_latest > 0 else set()
    to_move = [p for p in files if p not in keep]

    print(f"Found self-review reports: {len(files)}")
    print(f"Keeping latest in source: {len(keep)}")
    print(f"Archiving to '{target}': {len(to_move)}")

    for src in to_move:
        dst = target / src.name
        print(f"- {src} -> {dst}")
        if args.apply:
            target.mkdir(parents=True, exist_ok=True)
            shutil.move(str(src), str(dst))

    if not args.apply:
        print("Dry-run only. Re-run with --apply to move files.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
