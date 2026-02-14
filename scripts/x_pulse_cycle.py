#!/usr/bin/env python3
"""x_pulse_cycle

Run a cheap X pulse check (via x-research-skill quick mode), ingest into Spark's
learner, then print a short trends/content brief.

This is intended for scheduled runs (wake-up + every 4h), without burning budget
on low-signal accounts.

Flow:
1) x-research-skill search (recent) with --quick + --no-replies
2) ingest results into SparkResearcher.ingest_mcp_results (so Spark learns)
3) generate a brief from stored insights (no extra API calls)

Usage:
  python scripts/x_pulse_cycle.py --since 4h --limit 25
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent


def run(cmd: list[str]) -> int:
    proc = subprocess.run(cmd)
    return int(proc.returncode)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--since", default="4h", help="x-research since window: 1h|4h|12h|1d|7d")
    ap.add_argument("--limit", type=int, default=25, help="Result limit for x-search")
    ap.add_argument("--topic", default="pulse", help="Topic label for Spark ingestion")
    ap.add_argument("--hours", type=float, default=4.0, help="Lookback window for brief")
    ap.add_argument("--save", default=None, help="Optional directory to save brief markdown")
    args = ap.parse_args()

    # One aggregated query to keep cost low; the downstream learner still extracts triggers/patterns.
    query = (
        '"vibe coding" OR vibecoding OR openclaw OR "AI agents" OR agentic '
        'OR claude OR anthropic OR openai OR chatgpt OR "local llm" OR ollama '
        'OR "llama.cpp" OR vllm OR AGI'
    )

    ingest = [
        sys.executable,
        str(PROJECT_ROOT / "scripts" / "x_research_ingest.py"),
        "search",
        query,
        "--topic",
        args.topic,
        "--quick",
        "--no-replies",
        "--limit",
        str(args.limit),
        "--since",
        args.since,
    ]

    rc = run(ingest)
    if rc != 0:
        raise SystemExit(rc)

    brief = [
        sys.executable,
        str(PROJECT_ROOT / "scripts" / "x_trends_brief.py"),
        "--hours",
        str(args.hours),
        "--limit",
        "8",
    ]
    if args.save:
        brief += ["--save", args.save]

    rc = run(brief)
    raise SystemExit(rc)


if __name__ == "__main__":
    main()
