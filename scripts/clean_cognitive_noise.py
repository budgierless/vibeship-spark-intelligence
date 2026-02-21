#!/usr/bin/env python3
"""One-time cleanup: remove operational noise from cognitive_insights.json.

Removes cycle summaries and other telemetry that dominates the retrieval path.
Creates a backup before cleaning.
"""
import json
import shutil
from pathlib import Path
from datetime import datetime

INSIGHTS_PATH = Path.home() / ".spark" / "cognitive_insights.json"

def main():
    if not INSIGHTS_PATH.exists():
        print("No cognitive_insights.json found.")
        return

    data = json.loads(INSIGHTS_PATH.read_text(encoding="utf-8"))
    total = len(data)
    print(f"Total insights: {total}")

    # Patterns to remove
    removed = {}
    kept = {}
    remove_reasons = {
        "cycle_summary": 0,
        "tool_telemetry": 0,
        "system_gap": 0,
        "empty": 0,
    }

    for key, value in data.items():
        text = ""
        if isinstance(value, dict):
            text = value.get("insight", "")
        elif isinstance(value, str):
            text = value

        remove = False
        reason = ""

        # Cycle summaries
        if text.startswith("Cycle summary:") or "cycle_summary" in key:
            remove = True
            reason = "cycle_summary"
        # Tool telemetry
        elif text.startswith("[System Gap] [TUNEABLES]"):
            remove = True
            reason = "system_gap"
        elif not text.strip():
            remove = True
            reason = "empty"

        if remove:
            removed[key] = value
            remove_reasons[reason] = remove_reasons.get(reason, 0) + 1
        else:
            kept[key] = value

    print(f"\nRemoval breakdown:")
    for reason, count in sorted(remove_reasons.items(), key=lambda x: -x[1]):
        if count:
            print(f"  {reason}: {count}")
    print(f"\nKept: {len(kept)} ({100*len(kept)/total:.1f}%)")
    print(f"Removed: {len(removed)} ({100*len(removed)/total:.1f}%)")

    if not removed:
        print("Nothing to clean.")
        return

    # Backup
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = INSIGHTS_PATH.parent / f"cognitive_insights_backup_{ts}.json"
    shutil.copy2(INSIGHTS_PATH, backup_path)
    print(f"\nBackup: {backup_path}")

    # Write cleaned file
    INSIGHTS_PATH.write_text(json.dumps(kept, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Cleaned cognitive_insights.json written ({len(kept)} insights)")


if __name__ == "__main__":
    main()
