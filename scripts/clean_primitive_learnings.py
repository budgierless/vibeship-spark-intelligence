#!/usr/bin/env python3
"""
Clean primitive/operational learnings from cognitive_insights.json.

Phase 1 refactor: Remove all tool-sequence, usage, and operational patterns.
Keep only truly cognitive insights that a human would find useful.

Patterns to REMOVE (primitive):
- Tool sequences: "Read -> Edit", "Glob -> Glob -> Glob"
- Usage signals: "Heavy Bash usage (42 calls)"
- Success rates: "works (90% success)"
- Error categories: "Bash fails with windows_encoding"
- Overconfidence about tools: "Overconfident with Bash"
- Tool-specific struggles

Patterns to KEEP (cognitive):
- User preferences: "User prefers iterative fixes"
- Domain decisions: "Health=300 for balance"
- Explicit principles: "Ship fast, iterate faster"
- Cross-domain wisdom
"""

import json
import re
from pathlib import Path
from typing import Dict, Any, Tuple

INSIGHTS_FILE = Path.home() / ".spark" / "cognitive_insights.json"
CLEAN_FILE = Path.home() / ".spark" / "cognitive_insights.clean.json"


def is_primitive(key: str, insight: Dict[str, Any]) -> Tuple[bool, str]:
    """
    Check if an insight is primitive/operational.
    Returns (is_primitive, reason).
    """
    insight_text = insight.get("insight", "").lower()
    key_lower = key.lower()

    # Tool sequence patterns
    if "->" in insight_text or "→" in insight_text:
        return True, "tool_sequence"

    # Heavy usage signals
    if re.search(r"heavy \w+ usage", insight_text):
        return True, "usage_signal"

    # Success rate patterns
    if re.search(r"works \(\d+% success\)", insight_text):
        return True, "success_rate"

    # Tool-specific error categories
    if re.search(r"(bash|edit|read|write|glob|grep|task|webfetch) fails with", insight_text):
        return True, "error_category"

    # Tool-specific struggles
    if "struggle" in key_lower and any(tool in key_lower for tool in
        ["bash", "edit", "read", "write", "glob", "grep", "task", "webfetch"]):
        return True, "tool_struggle"

    # Overconfidence about tools
    if "overconfident" in insight_text and any(tool in insight_text for tool in
        ["bash", "edit", "read", "write", "glob", "grep", "task", "webfetch"]):
        return True, "tool_overconfidence"

    # Parallel tool patterns
    if "parallel" in key_lower and ("+" in insight_text or "parallel" in insight_text):
        return True, "parallel_pattern"

    # Signal patterns about tool usage
    if key_lower.startswith("signal:") and any(tool in insight_text for tool in
        ["bash", "edit", "read", "write", "glob", "grep", "task", "webfetch"]):
        return True, "tool_signal"

    # Principle patterns that are really tool sequences
    if key_lower.startswith("principle:") and re.search(r"for \w+:.*->", insight_text):
        return True, "sequence_principle"

    return False, "cognitive"


def clean_insights():
    """Remove primitive learnings and keep only cognitive ones."""
    if not INSIGHTS_FILE.exists():
        print("No cognitive_insights.json found")
        return

    data = json.loads(INSIGHTS_FILE.read_text())

    kept = {}
    removed_by_reason = {}

    for key, insight in data.items():
        is_prim, reason = is_primitive(key, insight)

        if is_prim:
            removed_by_reason[reason] = removed_by_reason.get(reason, 0) + 1
        else:
            kept[key] = insight

    print(f"\n=== Cognitive Insights Cleanup ===")
    print(f"Total insights: {len(data)}")
    print(f"Kept (cognitive): {len(kept)}")
    print(f"Removed (primitive): {len(data) - len(kept)}")
    print(f"\nRemoval breakdown:")
    for reason, count in sorted(removed_by_reason.items(), key=lambda x: -x[1]):
        print(f"  {reason}: {count}")

    # Show what was kept
    if kept:
        print(f"\n=== Kept Insights ({len(kept)}) ===")
        for key, insight in list(kept.items())[:10]:
            print(f"  - {key[:60]}...")
            print(f"    {insight.get('insight', '')[:80]}...")

    # Save cleaned version
    CLEAN_FILE.write_text(json.dumps(kept, indent=2))
    print(f"\nCleaned insights saved to: {CLEAN_FILE}")

    # Optionally replace the original
    response = input("\nReplace original file? (y/n): ").strip().lower()
    if response == 'y':
        INSIGHTS_FILE.write_text(json.dumps(kept, indent=2))
        print("Original file replaced.")
    else:
        print("Original file unchanged. Clean version available at:", CLEAN_FILE)


if __name__ == "__main__":
    clean_insights()
