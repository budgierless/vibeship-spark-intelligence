#!/usr/bin/env python3
"""Minimal advise -> act -> report wrapper for local usage."""

from __future__ import annotations

import argparse
import shlex
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from lib.advisor import advise_on_tool, report_outcome  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--tool", required=True, help="Tool name (Edit, Write, Bash)")
    ap.add_argument("--context", default="", help="Task context for semantic retrieval")
    ap.add_argument("--file", dest="file_path", help="Target file path for Edit/Write")
    ap.add_argument("--append", help="Append text for Edit")
    ap.add_argument("--content", help="Write full content for Write")
    ap.add_argument("--command", help="Command for Bash")
    ap.add_argument("--execute", action="store_true", help="Actually execute the action")
    ap.add_argument("--helpful", action="store_true", help="Mark advice as helpful")
    args = ap.parse_args()

    tool = args.tool.strip()
    tool_input = {}
    if args.file_path:
        tool_input["file_path"] = args.file_path
    if args.command:
        tool_input["command"] = args.command

    advice = advise_on_tool(tool, tool_input, args.context)
    print(f"advice_count={len(advice)}")
    for i, item in enumerate(advice[:3], 1):
        text = getattr(item, "text", "")
        source = getattr(item, "source", "")
        reason = getattr(item, "reason", "")
        print(f"{i}. {text}")
        print(f"   source={source} reason={reason}")

    success = True
    if args.execute:
        try:
            if tool.lower() == "bash":
                if not args.command:
                    raise RuntimeError("Missing --command for Bash")
                command = shlex.split(args.command)
                if not command:
                    raise RuntimeError("Empty command after parsing")
                subprocess.run(command, shell=False, check=True)
            elif tool.lower() == "edit":
                if not args.file_path or args.append is None:
                    raise RuntimeError("Edit requires --file and --append")
                path = Path(args.file_path)
                path.parent.mkdir(parents=True, exist_ok=True)
                with path.open("a", encoding="utf-8") as f:
                    f.write(args.append)
            elif tool.lower() == "write":
                if not args.file_path or args.content is None:
                    raise RuntimeError("Write requires --file and --content")
                path = Path(args.file_path)
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(args.content, encoding="utf-8")
            else:
                raise RuntimeError(f"Unsupported tool: {tool}")
        except Exception:
            success = False
            raise
        finally:
            report_outcome(tool, success=success, advice_helped=bool(args.helpful))
    else:
        # Dry run: still record outcome for retrieval metrics.
        report_outcome(tool, success=True, advice_helped=bool(args.helpful))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
