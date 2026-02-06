from __future__ import annotations

import time

from lib.advisory_state import SessionState, resolve_recent_trace_id


def test_resolve_recent_trace_id_prefers_unresolved_pre_tool_call():
    now = time.time()
    state = SessionState(
        session_id="s1",
        recent_tools=[
            {
                "tool_name": "Edit",
                "timestamp": now - 4,
                "success": True,
                "trace_id": "trace-post",
            },
            {
                "tool_name": "Edit",
                "timestamp": now - 2,
                "success": None,
                "trace_id": "trace-pre",
            },
        ],
    )

    assert resolve_recent_trace_id(state, "Edit") == "trace-pre"


def test_resolve_recent_trace_id_ignores_stale_entries():
    now = time.time()
    state = SessionState(
        session_id="s2",
        recent_tools=[
            {
                "tool_name": "Bash",
                "timestamp": now - 900,
                "success": None,
                "trace_id": "trace-old",
            }
        ],
    )

    assert resolve_recent_trace_id(state, "Bash", max_age_s=120) is None
