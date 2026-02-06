#!/usr/bin/env python3
"""Edge-case semantic harness (advisor-only, no destructive actions)."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from lib.advisor import advise_on_tool, report_outcome  # noqa: E402


DEFAULT_CASES = [
    ("empty_context", "Bash", {"command": ""}, ""),
    ("whitespace_context", "Bash", {"command": " "}, "   "),
    ("destructive_command", "Bash", {"command": "rm -rf /"}, "rm -rf /"),
    ("sql_destructive", "Bash", {"command": "drop table users"}, "drop table users"),
    ("deploy_trigger", "Bash", {"command": "git push origin main"}, "deploy main"),
    ("windows_path", "Edit", {"file_path": r"C:\workspace\project\file name.txt"}, "edit file path"),
    ("unicode_context", "Edit", {"file_path": str(Path.home() / ".spark" / "notes" / "edge_unicode.md")}, "append unicode test"),
    ("json_blob", "Write", {"file_path": str(Path.home() / ".spark" / "notes" / "edge_json.md")}, '{"action":"update","target":"auth","flags":["safe","dry_run"]}'),
    ("long_context", "Write", {"file_path": str(Path.home() / ".spark" / "notes" / "edge_long_context.md")}, "long context " * 120),
    ("code_snippet", "Edit", {"file_path": str(Path.home() / ".spark" / "notes" / "edge_code.md")}, "def handler(req):\n    return 200\n"),
]


def _show(label: str, advice_list, limit: int) -> None:
    print(f"\n== {label} ==")
    print(f"advice_count={len(advice_list)}")
    for i, item in enumerate(advice_list[:limit], 1):
        text = getattr(item, "text", "")
        source = getattr(item, "source", "")
        reason = getattr(item, "reason", "")
        print(f"{i}. {text}")
        print(f"   source={source} reason={reason}")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=2, help="advice items to show per case")
    ap.add_argument("--helpful", action="store_true", help="mark advice as helpful in outcomes")
    ap.add_argument("--no-outcome", action="store_true", help="skip report_outcome")
    args = ap.parse_args()

    for label, tool, tool_input, context in DEFAULT_CASES:
        advice = advise_on_tool(tool, tool_input, context)
        _show(label, advice, max(1, int(args.limit)))
        if not args.no_outcome:
            report_outcome(tool, success=True, advice_helped=bool(args.helpful))

    print("\nEdge-case harness complete.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
