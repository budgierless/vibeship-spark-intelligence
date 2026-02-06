#!/usr/bin/env python3
"""Compact chip insight JSONL files to reduce telemetry bloat."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Dict


def _compact_file(path: Path, keep_lines: int, apply: bool) -> Dict[str, int]:
    if keep_lines <= 0:
        return {"before": 0, "after": 0}
    if not path.exists():
        return {"before": 0, "after": 0}

    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    before = len(lines)
    kept = lines[-keep_lines:] if before > keep_lines else lines
    after = len(kept)

    if apply and before != after:
        tmp = path.with_suffix(path.suffix + ".tmp")
        payload = "\n".join(kept)
        if payload:
            payload += "\n"
        tmp.write_text(payload, encoding="utf-8")
        tmp.replace(path)

    return {"before": before, "after": after}


def main() -> int:
    parser = argparse.ArgumentParser(description="Compact ~/.spark/chip_insights/*.jsonl")
    parser.add_argument("--keep-lines", type=int, default=2000, help="lines to keep per chip file")
    parser.add_argument("--apply", action="store_true", help="write changes (default is dry-run)")
    args = parser.parse_args()

    chip_dir = Path.home() / ".spark" / "chip_insights"
    files = sorted(chip_dir.glob("*.jsonl"))

    print(f"chip_dir={chip_dir}")
    print(f"files={len(files)} keep_lines={args.keep_lines} apply={args.apply}")

    total_before = 0
    total_after = 0
    for path in files:
        res = _compact_file(path, args.keep_lines, args.apply)
        total_before += res["before"]
        total_after += res["after"]
        if res["before"] != res["after"]:
            print(f"{path.name}: {res['before']} -> {res['after']}")
        else:
            print(f"{path.name}: {res['before']} (unchanged)")

    print(f"TOTAL: {total_before} -> {total_after}")
    if not args.apply:
        print("Dry-run only. Re-run with --apply to write compacted files.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

