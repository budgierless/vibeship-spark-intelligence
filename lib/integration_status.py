"""
Integration Status Checker for Spark Intelligence

Verifies that Spark is properly integrated with Claude Code.
Prevents being fooled by "test metrics" when real UX is broken.

Usage:
    python -m lib.integration_status
    spark status  # via CLI
"""

import json
import time
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Tuple

# Paths
CLAUDE_DIR = Path.home() / ".claude"
SPARK_DIR = Path.home() / ".spark"
SETTINGS_FILE = CLAUDE_DIR / "settings.json"
SPARK_HOOKS_FILE = CLAUDE_DIR / "spark-hooks.json"
QUEUE_DIR = SPARK_DIR / "queue"
EVENTS_FILE = QUEUE_DIR / "events.jsonl"
ADVICE_LOG = SPARK_DIR / "advisor" / "advice_log.jsonl"
RECENT_ADVICE = SPARK_DIR / "advisor" / "recent_advice.jsonl"
EFFECTIVENESS = SPARK_DIR / "advisor" / "effectiveness.json"


def check_settings_json() -> Tuple[bool, str]:
    """Check if ~/.claude/settings.json exists with Spark hooks."""
    if not SETTINGS_FILE.exists():
        return False, "Missing: ~/.claude/settings.json not found"

    try:
        settings = json.loads(SETTINGS_FILE.read_text())
        hooks = settings.get("hooks", {})

        required = ["PreToolUse", "PostToolUse", "PostToolUseFailure"]
        missing = [h for h in required if h not in hooks]

        if missing:
            return False, f"Missing hooks: {', '.join(missing)}"

        # Check if hooks point to observe.py
        for hook_type in required:
            hook_list = hooks.get(hook_type, [])
            if not hook_list:
                return False, f"{hook_type} has no hooks configured"

            has_spark = any(
                "observe.py" in str(h.get("hooks", [{}])[0].get("command", ""))
                for h in hook_list
            )
            if not has_spark:
                return False, f"{hook_type} doesn't call observe.py"

        return True, "settings.json configured correctly"
    except Exception as e:
        return False, f"Error reading settings.json: {e}"


def check_recent_events(minutes: int = 60) -> Tuple[bool, str]:
    """Check if we've received events in the last N minutes."""
    if not EVENTS_FILE.exists():
        return False, f"No events file: {EVENTS_FILE}"

    try:
        cutoff = time.time() - (minutes * 60)
        recent_count = 0

        with open(EVENTS_FILE, 'r', encoding='utf-8', errors='replace') as f:
            for line in f:
                try:
                    event = json.loads(line.strip())
                    ts = event.get("timestamp") or event.get("ts", 0)
                    if ts > cutoff:
                        recent_count += 1
                except:
                    continue

        if recent_count > 0:
            return True, f"{recent_count} events in last {minutes} min"
        else:
            return False, f"No events in last {minutes} min (file exists but stale)"
    except Exception as e:
        return False, f"Error reading events: {e}"


def check_advice_log_growing() -> Tuple[bool, str]:
    """Check if advice log is being written to."""
    log_file = RECENT_ADVICE if RECENT_ADVICE.exists() else ADVICE_LOG

    if not log_file.exists():
        return False, "No advice log found"

    try:
        # Check modification time
        mtime = log_file.stat().st_mtime
        age_hours = (time.time() - mtime) / 3600

        if age_hours > 24:
            return False, f"Advice log stale ({age_hours:.1f}h since last write)"

        # Count recent entries
        lines = log_file.read_text(encoding='utf-8', errors='replace').strip().split('\n')
        return True, f"{len(lines)} advice entries, last write {age_hours:.1f}h ago"
    except Exception as e:
        return False, f"Error reading advice log: {e}"


def check_effectiveness() -> Tuple[bool, str]:
    """Check if effectiveness tracking is working."""
    if not EFFECTIVENESS.exists():
        return False, "No effectiveness.json found"

    try:
        data = json.loads(EFFECTIVENESS.read_text())
        total = data.get("total_advice_given", 0)
        followed = data.get("total_followed", 0)
        helpful = data.get("total_helpful", 0)

        if total == 0:
            return False, "No advice tracked yet"

        if followed > total:
            return False, (
                f"Invalid counters: followed ({followed}) > total advice ({total})"
            )
        if helpful > followed:
            return False, (
                f"Invalid counters: helpful ({helpful}) > followed ({followed})"
            )

        if followed == 0 and total > 100:
            return False, f"0 followed out of {total} advice (outcome loop broken)"

        rate = (followed / total * 100) if total > 0 else 0
        return True, f"{followed}/{total} followed ({rate:.1f}%), {helpful} helpful"
    except Exception as e:
        return False, f"Error reading effectiveness: {e}"


def check_pre_tool_events(minutes: int = 60) -> Tuple[bool, str]:
    """Check specifically for pre_tool events."""
    if not EVENTS_FILE.exists():
        return False, "No events file"

    try:
        cutoff = time.time() - (minutes * 60)
        pre_count = 0
        post_count = 0

        with open(EVENTS_FILE, 'r', encoding='utf-8', errors='replace') as f:
            for line in f:
                try:
                    event = json.loads(line.strip())
                    ts = event.get("timestamp") or event.get("ts", 0)
                    if ts > cutoff:
                        et = event.get("event_type", "").lower()
                        if "pre" in et:
                            pre_count += 1
                        elif "post" in et:
                            post_count += 1
                except:
                    continue

        if pre_count > 0 and post_count > 0:
            return True, f"pre_tool: {pre_count}, post_tool: {post_count}"
        elif pre_count == 0 and post_count == 0:
            return False, "No pre_tool or post_tool events (hooks not firing)"
        else:
            return False, f"Partial: pre={pre_count}, post={post_count}"
    except Exception as e:
        return False, f"Error: {e}"


def get_full_status() -> Dict:
    """Get complete integration status."""
    checks = [
        ("settings.json", check_settings_json()),
        ("Recent Events", check_recent_events(60)),
        ("Pre/Post Tool Events", check_pre_tool_events(60)),
        ("Advice Log", check_advice_log_growing()),
        ("Effectiveness Tracking", check_effectiveness()),
    ]

    results = []
    all_ok = True

    for name, (ok, msg) in checks:
        results.append({
            "check": name,
            "ok": ok,
            "message": msg
        })
        if not ok:
            all_ok = False

    return {
        "status": "HEALTHY" if all_ok else "DEGRADED",
        "timestamp": datetime.now().isoformat(),
        "checks": results,
        "all_ok": all_ok
    }


def print_status():
    """Print formatted status to console."""
    status = get_full_status()

    print("\n" + "=" * 60)
    print("  SPARK INTELLIGENCE - INTEGRATION STATUS")
    print("=" * 60)

    if status["all_ok"]:
        print("\n  STATUS: [OK] HEALTHY - All systems operational\n")
    else:
        print("\n  STATUS: [!!] DEGRADED - Issues detected\n")

    for check in status["checks"]:
        icon = "[OK]" if check["ok"] else "[!!]"
        print(f"  {icon} {check['check']}")
        print(f"    {check['message']}")
        print()

    if not status["all_ok"]:
        print("-" * 60)
        print("  FIX INSTRUCTIONS:")
        print("-" * 60)

        for check in status["checks"]:
            if not check["ok"]:
                if "settings.json" in check["check"]:
                    print("""
  1. Create ~/.claude/settings.json with:
     {
       "hooks": {
         "PreToolUse": [{"matcher":"","hooks":[{"type":"command",
           "command":"python /path/to/spark/hooks/observe.py"}]}],
         "PostToolUse": [...same...],
         "PostToolUseFailure": [...same...]
       }
     }
  2. Restart Claude Code
""")
                elif "Events" in check["check"]:
                    print("""
  - Hooks may not be firing. Check:
    a) settings.json has correct paths
    b) observe.py is executable
    c) Python is in PATH
    d) Restart Claude Code after config changes
""")
                elif "Effectiveness" in check["check"]:
                    print("""
  - Outcome loop is broken. Ensure:
    a) PostToolUse hook is configured
    b) report_outcome() is being called
    c) Check lib/bridge_cycle.py integration
""")

    print("=" * 60 + "\n")
    return status


if __name__ == "__main__":
    print_status()
