#!/usr/bin/env python3
"""Run the release pytest baseline with optional non-blocking checks."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
BASELINE_TARGETS_FILE = Path(__file__).resolve().parent / "test_baseline_targets.txt"
BASELINE_OPTIONAL_TARGETS_FILE = Path(__file__).resolve().parent / "test_baseline_optional_targets.txt"
BROAD_BASELINE_ARGS = [
    "-q",
    "-m",
    "not integration",
    "--ignore=tests/test_compact_chip_insights.py",
    "--ignore=tests/test_trace_hud.py",
]


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


def _load_optional_targets() -> list[str]:
    if not BASELINE_OPTIONAL_TARGETS_FILE.exists():
        return []

    targets: list[str] = []
    for raw_line in BASELINE_OPTIONAL_TARGETS_FILE.read_text(encoding="utf-8").splitlines():
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


def _validate_optional_targets(targets: list[str]) -> list[str]:
    missing: list[str] = []
    for target in targets:
        if not (REPO_ROOT / target).exists():
            missing.append(target)
    return missing


def _run_pytest(targets: list[str], *, allow_failure: bool = False) -> tuple[int, int]:
    if not targets:
        return (0, 0)

    cmd = [sys.executable, "-m", "pytest", "-q", *targets]
    result = subprocess.run(cmd, cwd=REPO_ROOT)
    if result.returncode != 0:
        return (result.returncode if not allow_failure else 0, result.returncode)
    return (0, 0)


def _run_pytest_args(args: list[str], *, allow_failure: bool = False) -> tuple[int, int]:
    if not args:
        return (0, 0)
    cmd = [sys.executable, "-m", "pytest", *args]
    result = subprocess.run(cmd, cwd=REPO_ROOT)
    if result.returncode != 0:
        return (result.returncode if not allow_failure else 0, result.returncode)
    return (0, 0)


def main() -> int:
    targets = _load_targets()
    if not targets:
        print("No baseline targets configured in scripts/test_baseline_targets.txt")
        return 0

    code = _validate_targets(targets)
    if code:
        return code
    mandatory_code, _ = _run_pytest(targets, allow_failure=False)
    if mandatory_code != 0:
        print("Release baseline tests failed.")
        return mandatory_code

    broad_code, _ = _run_pytest_args(BROAD_BASELINE_ARGS, allow_failure=False)
    if broad_code != 0:
        print("Release broad baseline failed.")
        return broad_code

    optional_targets = _load_optional_targets()
    optional_missing = _validate_optional_targets(optional_targets)
    if optional_missing:
        print("Optional baseline target missing (skipping):")
        for path in optional_missing:
            print(f"- {path}")
        optional_targets = [t for t in optional_targets if t not in optional_missing]

    if optional_targets:
        print("Running optional baseline checks:")
        for target in optional_targets:
            print(f"- {target}")
        _, optional_raw = _run_pytest(optional_targets, allow_failure=True)
    else:
        optional_raw = 0
    if optional_targets:
        if optional_raw == 0:
            # Keep output consistent for CI logs.
            print("Release optional baseline checks passed.")
        else:
            print("Release optional baseline checks reported failures (non-blocking).")

    print("Release mandatory baseline passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
