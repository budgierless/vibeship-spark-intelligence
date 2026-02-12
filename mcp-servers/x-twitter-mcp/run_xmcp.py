#!/usr/bin/env python3
"""Launch the XMCP server with credentials loaded from local .env."""

from __future__ import annotations

import os
import sys
from pathlib import Path

from dotenv import dotenv_values


ENV_PATH = Path(__file__).parent / ".env"
REQUIRED_KEYS = (
    "TWITTER_API_KEY",
    "TWITTER_API_SECRET",
    "TWITTER_ACCESS_TOKEN",
    "TWITTER_ACCESS_TOKEN_SECRET",
    "TWITTER_BEARER_TOKEN",
)


def _load_env() -> None:
    if ENV_PATH.exists():
        values = dotenv_values(ENV_PATH)
        for key, value in values.items():
            if key and value and not os.environ.get(key):
                os.environ[key] = value

    missing = [key for key in REQUIRED_KEYS if not os.environ.get(key)]
    if missing:
        print(
            f"ERROR: Missing required X credentials: {', '.join(missing)}",
            file=sys.stderr,
        )
        print(f"Checked: {ENV_PATH}", file=sys.stderr)
        sys.exit(1)

    os.environ.setdefault("X_MCP_PROFILE", "creator")


def main() -> None:
    _load_env()
    try:
        from xmcp import run
    except Exception as exc:
        print(f"ERROR: Could not import xmcp: {exc}", file=sys.stderr)
        sys.exit(1)
    run()


if __name__ == "__main__":
    main()
