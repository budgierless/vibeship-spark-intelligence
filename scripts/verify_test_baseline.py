#!/usr/bin/env python3
"""Run a minimal, release-confidence pytest baseline."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
BASELINE_TARGETS_FILE = Path(__file__).resolve().parent / "test_baseline_targets.txt"


def _load_targets() -> list[str]:
    if not BASELINE_TARGETS_FILE.exists():
        return []

    targets: list[str] = []
    for raw_line in BASELINE_TARGETS_FILE.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        targets.append(line)
    return targets


def _validate_targets(targets: list[str]) -> int:
    missing: list[str] = []
    for target in targets:
        path = REPO_ROOT / target
        if not path.exists():
            missing.append(target)
    if missing:
        print("Release baseline target missing:")
        for path in missing:
            print(f"- {path}")
        return 1
    return 0


def main() -> int:
    targets = _load_targets()
    if not targets:
        print("No baseline targets configured in scripts/test_baseline_targets.txt")
        return 0

    code = _validate_targets(targets)
    if code:
        return code

    cmd = [sys.executable, "-m", "pytest", "-q", *targets]
    result = subprocess.run(cmd, cwd=REPO_ROOT)
    if result.returncode != 0:
        print("Release baseline tests failed.")
        return result.returncode

    print("Release baseline passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
