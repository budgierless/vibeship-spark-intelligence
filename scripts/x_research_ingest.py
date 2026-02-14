#!/usr/bin/env python3
"""x_research_ingest

Run the external x-research CLI (Bun/TS) for ad-hoc searches, then ingest the
results into Spark's internal X research learner so Spark actually *learns* from
manual research.

This bridges:
- OpenClaw skill:   ~/.openclaw/workspace/skills/x-research (bun x-search.ts)
- Spark learner:    lib/x_research.py (SparkResearcher.ingest_mcp_results)

By default this script:
- runs a recent-search query via x-search.ts with --json
- maps results into ingest_mcp_results() shape
- stores learnings to ~/.spark/chip_insights/* via store_insight()

Usage:
  python scripts/x_research_ingest.py search "query" --topic "ai_agents" --quick --limit 25 --since 1d

Notes:
- Requires Bun installed.
- Requires X creds present in mcp-servers/x-twitter-mcp/.env (already used by SparkResearcher).
- Does NOT print or log bearer tokens.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path


DEFAULT_SKILL_DIR = Path(os.environ.get(
    "X_RESEARCH_SKILL_DIR",
    r"C:\Users\USER\.openclaw\workspace\skills\x-research",
))
DEFAULT_PS1 = DEFAULT_SKILL_DIR / "x-search.ps1"


def run_x_search_json(argv: list[str]) -> list[dict]:
    # Run via PowerShell wrapper so X_BEARER_TOKEN can be sourced safely.
    cmd = [
        "powershell",
        "-NoProfile",
        "-ExecutionPolicy",
        "Bypass",
        "-File",
        str(DEFAULT_PS1),
        *argv,
        "--json",
    ]

    # We capture stdout (JSON) and allow stderr (cost / save path) for user visibility.
    proc = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8")
    if proc.returncode != 0:
        sys.stderr.write(proc.stderr or "")
        raise SystemExit(proc.returncode)

    out = proc.stdout.strip()
    if not out:
        return []
    try:
        data = json.loads(out)
    except json.JSONDecodeError:
        # If some non-JSON slipped into stdout, show context
        sys.stderr.write("x-search did not return valid JSON on stdout.\n")
        sys.stderr.write(out[:2000] + "\n")
        raise

    if not isinstance(data, list):
        raise ValueError("Expected JSON list of tweets")
    return data


def map_for_ingest(tweets: list[dict], topic: str) -> list[dict]:
    mapped: list[dict] = []
    for t in tweets:
        metrics = t.get("metrics") or {}
        mapped.append(
            {
                "text": t.get("text", ""),
                "likes": int(metrics.get("likes", 0) or 0),
                "replies": int(metrics.get("replies", 0) or 0),
                "retweets": int(metrics.get("retweets", 0) or 0),
                "user_handle": "@" + str(t.get("username") or "unknown"),
                "user_followers": 0,  # not provided by x-search skill currently
                "topic": topic,
                "tweet_url": t.get("tweet_url"),
                "created_at": t.get("created_at"),
            }
        )
    return mapped


def main() -> None:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)

    sp = sub.add_parser("search", help="Search X (recent, last 7d) then ingest into Spark learner")
    sp.add_argument("query", help="Search query")
    sp.add_argument("--topic", default="ad_hoc", help="Topic label used for Spark ingestion")
    sp.add_argument("--limit", type=int, default=25, help="Max results to request from x-search")
    sp.add_argument("--since", default=None, help="1h|3h|12h|1d|7d or ISO timestamp")
    sp.add_argument("--quick", action="store_true", help="Use x-search quick mode")
    sp.add_argument("--no-replies", action="store_true")

    args = ap.parse_args()

    if not DEFAULT_PS1.exists():
        raise SystemExit(
            f"Missing x-research skill at {DEFAULT_PS1}. Set X_RESEARCH_SKILL_DIR or clone the skill."
        )

    if args.cmd == "search":
        x_argv = ["search", args.query, "--limit", str(args.limit)]
        if args.quick:
            x_argv.append("--quick")
        if args.no_replies:
            x_argv.append("--no-replies")
        if args.since:
            x_argv += ["--since", args.since]

        tweets = run_x_search_json(x_argv)
        mapped = map_for_ingest(tweets, topic=args.topic)

        # Ingest to Spark learner
        sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
        from lib.x_research import SparkResearcher  # noqa

        r = SparkResearcher(verbose=True, dry_run=False)
        r.ingest_mcp_results(mapped)

        print(f"Ingested={len(mapped)} (pre-filter) topic={args.topic}")


if __name__ == "__main__":
    main()
