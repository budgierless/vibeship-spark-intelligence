#!/usr/bin/env python3
"""One-command semantic runbook (health -> config -> harness -> summary)."""

from __future__ import annotations

import json
import sqlite3
import shlex
import subprocess
import sys
from pathlib import Path


def run_cmd(cmd: str, label: str) -> None:
    print(f"\n== {label} ==")
    argv = shlex.split(cmd)
    proc = subprocess.run(
        argv,
        shell=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if proc.stdout:
        print(proc.stdout.rstrip())
    if proc.stderr:
        print(proc.stderr.rstrip())
    if proc.returncode != 0:
        raise SystemExit(f"[ERROR] {label} failed (code {proc.returncode})")


def check_env_vars() -> None:
    print("\n== Env Vars (cloud providers) ==")
    import os
    keys = [
        "OPENAI_API_KEY",
        "ANTHROPIC_API_KEY",
        "COHERE_API_KEY",
        "MISTRAL_API_KEY",
        "GEMINI_API_KEY",
        "AZURE_OPENAI_API_KEY",
        "AZURE_OPENAI_ENDPOINT",
        "TOGETHER_API_KEY",
        "GROQ_API_KEY",
        "MINIMAX_API_KEY",
    ]
    for key in keys:
        print(f"{key} = {'set' if os.environ.get(key) else '(not set)'}")


def check_tuneables() -> dict:
    path = Path.home() / ".spark" / "tuneables.json"
    if not path.exists():
        raise SystemExit(f"[ERROR] Missing tuneables: {path}")
    data = json.loads(path.read_text(encoding="utf-8"))
    semantic = data.get("semantic", {}) or {}
    triggers = data.get("triggers", {}) or {}
    if not semantic.get("enabled", False):
        raise SystemExit("[ERROR] semantic.enabled is false")
    if not triggers.get("enabled", False):
        raise SystemExit("[ERROR] triggers.enabled is false")
    print("\n== Tuneables ==")
    print(f"semantic.enabled = {semantic.get('enabled')}")
    print(f"semantic.min_similarity = {semantic.get('min_similarity')}")
    print(f"semantic.min_fusion_score = {semantic.get('min_fusion_score')}")
    print(f"semantic.exclude_categories = {semantic.get('exclude_categories', [])}")
    print(f"triggers.enabled = {triggers.get('enabled')}")
    rules_file = triggers.get("rules_file")
    if rules_file and not Path(rules_file).expanduser().exists():
        raise SystemExit(f"[ERROR] triggers.rules_file missing: {rules_file}")
    return data


def check_index(require_nonempty: bool = True) -> int:
    db = Path.home() / ".spark" / "semantic" / "insights_vec.sqlite"
    if not db.exists():
        raise SystemExit(f"[ERROR] Missing semantic index: {db}")
    try:
        con = sqlite3.connect(db)
        cur = con.execute("select count(*) from insights_vec")
        count = int(cur.fetchone()[0])
    finally:
        con.close()
    print(f"\n== Semantic Index ==\nrows={count}")
    if require_nonempty and count == 0:
        raise SystemExit("[ERROR] Semantic index is empty (run python -m spark.index_embeddings --all)")
    return count


def tail_jsonl(path: Path, label: str, max_lines: int = 1) -> None:
    print(f"\n== {label} ==")
    if not path.exists():
        print(f"(missing) {path}")
        return
    if path.suffix == ".json":
        try:
            data = json.loads(path.read_text(encoding="utf-8", errors="replace"))
            print(json.dumps(data, indent=2))
            return
        except Exception:
            pass
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    for line in lines[-max_lines:]:
        print(line)


def main() -> int:
    run_cmd("python -m spark.cli health", "Health Check")
    run_cmd("python -m spark.cli services", "Services Check")
    check_env_vars()
    check_tuneables()
    check_index(require_nonempty=True)

    run_cmd("python scripts/semantic_harness.py --limit 5", "Semantic Harness")
    run_cmd("python scripts/edge_case_harness.py --limit 2 --no-outcome", "Edge-Case Harness")

    logs = Path.home() / ".spark" / "logs" / "semantic_retrieval.jsonl"
    tail_jsonl(logs, "Semantic Retrieval Log (last 2)", max_lines=2)
    metrics = Path.home() / ".spark" / "advisor" / "metrics.json"
    tail_jsonl(metrics, "Advisor Metrics (raw)", max_lines=1)

    print("\nRunbook complete.")
    print("Next: use scripts/advise_act.py for real tasks.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
