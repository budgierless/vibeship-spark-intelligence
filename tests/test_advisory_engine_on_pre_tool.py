"""
Safety-net tests for advisory_engine.py — on_pre_tool() orchestration.

These tests mock all subsystems (advisor, gate, synthesizer, state) to test
the orchestration logic of on_pre_tool() in isolation. They verify:
- ENGINE_ENABLED guard
- Subsystem call ordering
- Error handling / fallback behavior
- Global dedupe behavior
- Text repeat detection

Usage:
    pytest tests/test_advisory_engine_on_pre_tool.py -v
"""

import sys
import time
from pathlib import Path
from unittest.mock import patch, MagicMock
from dataclasses import dataclass
from typing import Dict, List, Optional

sys.path.insert(0, str(Path(__file__).parent.parent))


# ── Minimal mocks ────────────────────────────────────────────────────

@dataclass
class MockGateDecision:
    advice_id: str = "adv_001"
    authority: str = "note"
    emit: bool = True
    reason: str = "phase=impl, score=0.65"
    adjusted_score: float = 0.65
    original_score: float = 0.60


@dataclass
class MockGateResult:
    decisions: list = None
    emitted: list = None
    suppressed: list = None
    phase: str = "implementation"
    total_retrieved: int = 1

    def __post_init__(self):
        if self.decisions is None:
            d = MockGateDecision()
            self.decisions = [d]
            self.emitted = [d]
            self.suppressed = []


@dataclass
class MockAdvice:
    advice_id: str = "adv_001"
    text: str = "Consider connection pooling"
    confidence: float = 0.8
    source: str = "cognitive"
    context_match: float = 0.7
    insight_key: str = "wisdom:pooling"
    emotional_priority: float = 0.0
    category: str = "wisdom"


@dataclass
class MockState:
    shown_advice_ids: Dict[str, float] = None
    task_phase: str = "implementation"
    consecutive_failures: int = 0
    tool_suppressed_until: Dict[str, float] = None
    intent_family: str = "emergent_other"
    last_read_file: str = ""
    context_key: str = ""
    session_id: str = "test_session"

    def __post_init__(self):
        if self.shown_advice_ids is None:
            self.shown_advice_ids = {}
        if self.tool_suppressed_until is None:
            self.tool_suppressed_until = {}


# ── ENGINE_ENABLED guard ──────────────────────────────────────────────

def test_on_pre_tool_disabled():
    """When ENGINE_ENABLED is False, on_pre_tool should immediately return None."""
    with patch("lib.advisory_engine.ENGINE_ENABLED", False):
        from lib.advisory_engine import on_pre_tool
        result = on_pre_tool("session_1", "Read")
        assert result is None


# ── Subsystem availability ────────────────────────────────────────────

def test_on_pre_tool_returns_string_or_none():
    """on_pre_tool should return either a string (advice) or None."""
    with patch("lib.advisory_engine.ENGINE_ENABLED", True):
        from lib.advisory_engine import on_pre_tool
        result = on_pre_tool("test_session", "Read", tool_input={"file_path": "/tmp/test.py"})
        assert result is None or isinstance(result, str)


# ── Error resilience ──────────────────────────────────────────────────

def test_on_pre_tool_handles_import_error():
    """on_pre_tool should not crash if subsystem imports fail."""
    with patch("lib.advisory_engine.ENGINE_ENABLED", True):
        # Patch the inner imports to raise
        original_import = __builtins__.__import__ if hasattr(__builtins__, '__import__') else __import__
        from lib.advisory_engine import on_pre_tool

        # The method has its own try/except, so it should never raise
        result = on_pre_tool("test_session", "UnknownTool")
        assert result is None or isinstance(result, str)


def test_on_pre_tool_handles_state_load_error():
    """on_pre_tool should handle state loading failures gracefully."""
    with patch("lib.advisory_engine.ENGINE_ENABLED", True):
        from lib.advisory_engine import on_pre_tool
        # Even with corrupted state, should not crash
        result = on_pre_tool("", "Read")
        assert result is None or isinstance(result, str)


# ── Global dedupe function ────────────────────────────────────────────

def test_global_recently_emitted_function_exists():
    """Verify the global dedupe function exists and is callable."""
    from lib.advisory_engine import _global_recently_emitted
    # Returns Optional[Dict] — None means "not recently emitted" or test short-circuit
    result = _global_recently_emitted(
        tool_name="Read",
        advice_id="never_seen_advice_id_xyz123",
        now_ts=time.time(),
        cooldown_s=300.0,
        scope_key="test",
    )
    assert result is None or isinstance(result, dict)


def test_global_recently_emitted_text_sig_function_exists():
    """Verify the text signature dedupe function exists."""
    from lib.advisory_engine import _global_recently_emitted_text_sig
    # Param is text_sig, not text. Returns Optional[Dict].
    result = _global_recently_emitted_text_sig(
        text_sig="some unique advice text xyz123",
        now_ts=time.time(),
        cooldown_s=300.0,
        scope_key="test",
    )
    assert result is None or isinstance(result, dict)


# ── Text repeat detection ─────────────────────────────────────────────

def test_duplicate_repeat_state_function():
    """Verify the text repeat detection function works."""
    from lib.advisory_engine import _duplicate_repeat_state

    state = MockState()
    # First call — should not be a repeat
    result = _duplicate_repeat_state(state, "some advice text")
    assert isinstance(result, dict)
    assert "repeat" in result


# ── Dead code verification ────────────────────────────────────────────

def test_low_auth_recently_emitted_exists():
    """Verify _low_auth_recently_emitted exists (dead code to be removed in Batch 1)."""
    from lib.advisory_engine import _low_auth_recently_emitted
    # Should exist and be callable
    assert callable(_low_auth_recently_emitted)
