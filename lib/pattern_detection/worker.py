"""Pattern detection worker: process queued events outside hooks."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List, Optional

from lib.queue import read_events, count_events, EventType
from .aggregator import get_aggregator


STATE_FILE = Path.home() / ".spark" / "pattern_detection_state.json"


def _load_state() -> Dict:
    if not STATE_FILE.exists():
        return {"offset": 0}
    try:
        return json.loads(STATE_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {"offset": 0}


def _save_state(state: Dict) -> None:
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(state, indent=2), encoding="utf-8")


def _hook_event_from_type(event_type: EventType) -> str:
    mapping = {
        EventType.USER_PROMPT: "UserPromptSubmit",
        EventType.PRE_TOOL: "PreToolUse",
        EventType.POST_TOOL: "PostToolUse",
        EventType.POST_TOOL_FAILURE: "PostToolUseFailure",
        EventType.SESSION_START: "SessionStart",
        EventType.SESSION_END: "SessionEnd",
    }
    return mapping.get(event_type, "Unknown")


def process_pattern_events(limit: int = 200) -> int:
    """Process new queued events and run pattern detection."""
    state = _load_state()
    offset = int(state.get("offset", 0))

    # Handle queue rotation or truncation
    total = count_events()
    if total < offset:
        offset = max(0, total - limit)

    events = read_events(limit=limit, offset=offset)
    if not events:
        return 0

    aggregator = get_aggregator()
    processed = 0

    for ev in events:
        hook_event = (ev.data or {}).get("hook_event") or _hook_event_from_type(ev.event_type)
        payload = (ev.data or {}).get("payload")

        pattern_event = {
            "session_id": ev.session_id,
            "hook_event": hook_event,
            "tool_name": ev.tool_name,
            "tool_input": ev.tool_input,
            "payload": payload,
        }

        if ev.error:
            pattern_event["error"] = ev.error

        patterns = aggregator.process_event(pattern_event)
        if patterns:
            aggregator.trigger_learning(patterns)

        processed += 1

    state["offset"] = offset + processed
    _save_state(state)
    return processed


def get_pattern_backlog() -> int:
    """Return the count of queued events not yet processed by pattern detection."""
    state = _load_state()
    try:
        offset = int(state.get("offset", 0))
    except Exception:
        offset = 0
    total = count_events()
    if total < offset:
        offset = total
    return max(0, total - offset)

