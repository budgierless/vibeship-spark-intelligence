#!/usr/bin/env python3
"""Pre-release privacy/safety guard for tracked repository files."""

from __future__ import annotations

import fnmatch
import re
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = Path(__file__).resolve()

FORBIDDEN_FILENAMES = [
    "CLAUDE.md",
    "*test_output.txt",
    "*_test_output.txt",
    "*_test_out.txt",
    "*_test_err.txt",
    "C*Users*test_output*.txt",
]

FORBIDDEN_LINE_PATTERNS = {
    "windows_users_path": re.compile(r"[\"']([A-Za-z]:\\Users\\[^\"']+)[\"']", re.IGNORECASE),
    "private_key": re.compile(r"BEGIN (?:RSA|EC|OPENSSH|PRIVATE) PRIVATE KEY"),
    "x509_cert": re.compile(r"BEGIN CERTIFICATE"),
    "aws_key": re.compile(r"AKIA[0-9A-Z]{16}"),
    "github_pat": re.compile(r"gh[pous]_[A-Za-z0-9]{36}"),
    "slack_token": re.compile(r"xox[baprs]-[0-9]{10,12}-[0-9]{10,12}-[A-Za-z0-9]{24}"),
    "bearer_blob": re.compile(r"\bBearer\s+[A-Za-z0-9._-]{30,}\b"),
}


def _git_tracked_files() -> list[str]:
    result = subprocess.run(
        ["git", "ls-files"],
        cwd=str(REPO_ROOT),
        check=True,
        capture_output=True,
        text=True,
    )
    return [line.strip() for line in result.stdout.splitlines() if line.strip()]


def _is_forbidden_file(path: str) -> bool:
    base = Path(path).name
    for pattern in FORBIDDEN_FILENAMES:
        if fnmatch.fnmatch(base, pattern) or fnmatch.fnmatch(path, pattern):
            return True
    return False


def _scan_file(path: Path) -> list[str]:
    if path.resolve() == SCRIPT_PATH:
        return []

    issues: list[str] = []
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return issues

    for label, pattern in FORBIDDEN_LINE_PATTERNS.items():
        if pattern.search(text):
            issues.append(f"{label}: matched pattern in tracked file content")

    return issues


def main() -> int:
    files = _git_tracked_files()
    findings: list[str] = []

    for path_str in files:
        if _is_forbidden_file(path_str):
            findings.append(f"[forbidden_file] {path_str}")
            continue

        path = REPO_ROOT / path_str
        findings.extend(f"{path_str}: {issue}" for issue in _scan_file(path))

    if findings:
        print("Public release safety check failed. Blocked items:")
        for item in findings:
            print(f"- {item}")
        return 1

    print("Public release safety check passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
