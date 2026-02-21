#!/usr/bin/env python3
"""Pre-release privacy/safety guard for tracked repository files."""

from __future__ import annotations

import fnmatch
import ast
import os
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

AST_RISK_PATTERNS = {
    "subprocess_shell": {
        "match": lambda node: _is_subprocess_call_with_shell(node),
        "message": "subprocess call with shell=True",
    },
    "unsafe_eval_exec": {
        "match": lambda node: _is_eval_exec_call(node),
        "message": "built-in code execution path (eval/exec)",
    },
    "unsafe_yaml_load": {
        "match": lambda node: _is_yaml_load_without_loader(node),
        "message": "yaml.load without explicit Loader",
    },
    "pickle_load": {
        "match": lambda node: _is_pickle_load(node),
        "message": "pickle.load usage",
    },
}


def _is_subprocess_call_with_shell(node: ast.AST) -> bool:
    if not isinstance(node, ast.Call):
        return False
    target = _call_target(node.func)
    if target not in {"subprocess.call", "subprocess.run", "subprocess.Popen", "subprocess.check_output", "subprocess.getstatusoutput"}:
        return False
    for kw in node.keywords:
        if kw.arg == "shell" and isinstance(kw.value, ast.Constant) and kw.value.value is True:
            return True
    return False


def _is_eval_exec_call(node: ast.AST) -> bool:
    if not isinstance(node, ast.Call):
        return False
    return isinstance(node.func, ast.Name) and node.func.id in {"eval", "exec"}


def _is_yaml_load_without_loader(node: ast.AST) -> bool:
    if not isinstance(node, ast.Call):
        return False
    target = _call_target(node.func)
    if target != "yaml.load":
        return False
    if len(node.keywords) == 0:
        return True
    for kw in node.keywords:
        if kw.arg == "Loader":
            return False
    return True


def _is_pickle_load(node: ast.AST) -> bool:
    if not isinstance(node, ast.Call):
        return False
    target = _call_target(node.func)
    return target == "pickle.load"


def _call_target(func: ast.AST) -> str:
    if isinstance(func, ast.Name):
        return func.id
    if isinstance(func, ast.Attribute):
        base = _call_target(func.value)
        return f"{base}.{func.attr}"
    return ""


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

    if path.suffix == ".py":
        issues.extend(_scan_python_source(path, text, include_risk=_is_ast_risk_scan_allowed(path)))

    for label, pattern in FORBIDDEN_LINE_PATTERNS.items():
        if pattern.search(text):
            issues.append(f"{label}: matched pattern in tracked file content")

    return issues


def _is_ast_risk_scan_allowed(path: Path) -> bool:
    if path.as_posix().split("/")[0] == "tests" or "tests" in path.parts:
        return False
    if path.parent.name == "scripts" and path.name.startswith("test_"):
        return False
    return True


def _scan_python_source(path: Path, text: str, include_risk: bool) -> list[str]:
    issues: list[str] = []
    try:
        tree = ast.parse(text, filename=str(path))
    except SyntaxError as exc:
        issues.append(f"{path}:{exc.lineno or 0}:syntax_error: {exc.msg}")
        return issues

    if not include_risk:
        return issues

    for node in ast.walk(tree):
        lineno = getattr(node, "lineno", 0) or 0
        for item in AST_RISK_PATTERNS.values():
            if item["match"](node):
                issues.append(f"{path}:{lineno}:{item['message']}")

    return issues


def _run_dependency_audit() -> list[str]:
    findings: list[str] = []
    skip_audit = (Path(__file__).parent / "SKIP_DEP_AUDIT").exists()
    if skip_audit:
        return findings

    if (Path(__file__).parent / "SKIP_DEPENDENCY_AUDIT").exists():
        return findings

    env_skip = (os.environ.get("SPARK_RELEASE_SKIP_DEP_AUDIT", "").strip().lower() in {"1", "true", "yes", "on"})
    if env_skip:
        return findings

    try:
        result = subprocess.run(
            [sys.executable, "-m", "pip_audit", "--progress-spinner", "off", "--format", "json"],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
            check=False,
            timeout=60,
        )
    except Exception as exc:  # pragma: no cover
        return [f"dependency_audit: unable to run pip_audit ({exc})"]

    if result.returncode == 0:
        return findings

    if "No known vulnerabilities found" in (result.stdout or ""):
        return findings

    if result.stdout.strip():
        findings.append("dependency_audit: vulnerabilities or dependency warnings present")
    if result.stderr.strip():
        findings.append(f"dependency_audit_stderr: {result.stderr.strip()[:400]}")
    return findings


def main() -> int:
    files = _git_tracked_files()
    findings: list[str] = []

    for path_str in files:
        if _is_forbidden_file(path_str):
            findings.append(f"[forbidden_file] {path_str}")
            continue

        path = REPO_ROOT / path_str
        findings.extend(f"{path_str}: {issue}" for issue in _scan_file(path))

    findings.extend(_run_dependency_audit())

    if findings:
        print("Public release safety check failed. Blocked items:")
        for item in findings:
            print(f"- {item}")
        return 1

    print("Public release safety check passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
