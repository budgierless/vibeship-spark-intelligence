"""
Advisory Gate: Decides IF and WHEN to surface advice.

The gate is the critical intelligence layer between "we have advice" and
"we should show it." Most advisory systems fail because they show too much,
too often, at the wrong time. The gate prevents that.

Principles:
1. Suppress what's already obvious from context
2. Only surface at decision points or error-prone moments
3. Graduate authority: whisper → note → warning → block
4. Respect fatigue: don't repeat, don't flood
"""

from __future__ import annotations

import re
import time
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

from .diagnostics import log_debug

# ============= Authority Levels =============

class AuthorityLevel:
    """Graduated authority for advisory output."""
    SILENT = "silent"       # Log only, never emit (low confidence, tangential)
    WHISPER = "whisper"     # Available if asked, very brief
    NOTE = "note"           # Include in context block, non-blocking
    WARNING = "warning"     # Prominently shown, caution header
    BLOCK = "block"         # EIDOS blocks action (already exists)

# Score thresholds for authority assignment
AUTHORITY_THRESHOLDS = {
    AuthorityLevel.BLOCK: 0.95,     # Only proven critical safety issues
    AuthorityLevel.WARNING: 0.80,   # High confidence + proven failure history
    AuthorityLevel.NOTE: 0.50,      # Moderate confidence + relevant
    AuthorityLevel.WHISPER: 0.35,   # Low confidence or tangential
    # Below 0.35 → SILENT
}

# ============= Gate Configuration =============

# Max advice items to emit per tool call (prevent flooding)
MAX_EMIT_PER_CALL = 3

# Cooldown: don't emit for same tool within N seconds
TOOL_COOLDOWN_S = 30

# Don't repeat the same advice within N seconds
ADVICE_REPEAT_COOLDOWN_S = 600  # 10 minutes

# Phase-based relevance boosts
PHASE_RELEVANCE = {
    "exploration": {
        "context": 1.3,        # Architecture insights valuable here
        "wisdom": 1.0,
        "reasoning": 1.2,
        "user_understanding": 0.8,
        "self_awareness": 0.6,
    },
    "planning": {
        "reasoning": 1.4,      # Past decisions very relevant
        "context": 1.2,
        "wisdom": 1.3,
        "user_understanding": 1.1,
        "self_awareness": 0.7,
    },
    "implementation": {
        "self_awareness": 1.4,  # "You struggle with X" is critical here
        "context": 1.2,
        "reasoning": 1.1,
        "wisdom": 0.9,
        "user_understanding": 1.0,
    },
    "testing": {
        "self_awareness": 1.3,
        "context": 1.0,
        "reasoning": 1.0,
        "wisdom": 0.8,
        "user_understanding": 0.7,
    },
    "debugging": {
        "self_awareness": 1.5,  # Past failure patterns extremely relevant
        "reasoning": 1.4,
        "context": 1.2,
        "wisdom": 1.0,
        "user_understanding": 0.8,
    },
    "deployment": {
        "wisdom": 1.5,         # Safety principles matter most
        "context": 1.3,
        "self_awareness": 1.2,
        "reasoning": 1.0,
        "user_understanding": 0.8,
    },
}


def _clamp_float(value: Any, default: float, min_value: float, max_value: float) -> float:
    try:
        parsed = float(value)
    except Exception:
        parsed = float(default)
    return max(min_value, min(max_value, parsed))


def apply_gate_config(cfg: Dict[str, Any]) -> Dict[str, List[str]]:
    """Apply advisory gate runtime tuneables."""
    global MAX_EMIT_PER_CALL
    global TOOL_COOLDOWN_S
    global ADVICE_REPEAT_COOLDOWN_S

    applied: List[str] = []
    warnings: List[str] = []
    if not isinstance(cfg, dict):
        return {"applied": applied, "warnings": warnings}

    if "max_emit_per_call" in cfg:
        try:
            MAX_EMIT_PER_CALL = max(1, min(10, int(cfg.get("max_emit_per_call") or 1)))
            applied.append("max_emit_per_call")
        except Exception:
            warnings.append("invalid_max_emit_per_call")

    if "tool_cooldown_s" in cfg:
        try:
            TOOL_COOLDOWN_S = max(1, min(3600, int(cfg.get("tool_cooldown_s") or 1)))
            applied.append("tool_cooldown_s")
        except Exception:
            warnings.append("invalid_tool_cooldown_s")

    if "advice_repeat_cooldown_s" in cfg:
        try:
            ADVICE_REPEAT_COOLDOWN_S = max(
                5, min(86400, int(cfg.get("advice_repeat_cooldown_s") or 5))
            )
            applied.append("advice_repeat_cooldown_s")
        except Exception:
            warnings.append("invalid_advice_repeat_cooldown_s")

    warning_threshold = _clamp_float(
        cfg.get("warning_threshold", AUTHORITY_THRESHOLDS.get(AuthorityLevel.WARNING, 0.8)),
        AUTHORITY_THRESHOLDS.get(AuthorityLevel.WARNING, 0.8),
        0.2,
        0.99,
    )
    note_threshold = _clamp_float(
        cfg.get("note_threshold", AUTHORITY_THRESHOLDS.get(AuthorityLevel.NOTE, 0.5)),
        AUTHORITY_THRESHOLDS.get(AuthorityLevel.NOTE, 0.5),
        0.1,
        0.95,
    )
    whisper_threshold = _clamp_float(
        cfg.get("whisper_threshold", AUTHORITY_THRESHOLDS.get(AuthorityLevel.WHISPER, 0.35)),
        AUTHORITY_THRESHOLDS.get(AuthorityLevel.WHISPER, 0.35),
        0.01,
        0.9,
    )

    if "warning_threshold" in cfg:
        applied.append("warning_threshold")
    if "note_threshold" in cfg:
        applied.append("note_threshold")
    if "whisper_threshold" in cfg:
        applied.append("whisper_threshold")

    # Keep threshold ordering sane: warning > note > whisper.
    if warning_threshold <= note_threshold:
        note_threshold = max(0.1, warning_threshold - 0.05)
        warnings.append("note_threshold_auto_adjusted")
    if note_threshold <= whisper_threshold:
        whisper_threshold = max(0.01, note_threshold - 0.05)
        warnings.append("whisper_threshold_auto_adjusted")

    AUTHORITY_THRESHOLDS[AuthorityLevel.WARNING] = warning_threshold
    AUTHORITY_THRESHOLDS[AuthorityLevel.NOTE] = note_threshold
    AUTHORITY_THRESHOLDS[AuthorityLevel.WHISPER] = whisper_threshold

    return {"applied": applied, "warnings": warnings}


def get_gate_config() -> Dict[str, Any]:
    return {
        "max_emit_per_call": int(MAX_EMIT_PER_CALL),
        "tool_cooldown_s": int(TOOL_COOLDOWN_S),
        "advice_repeat_cooldown_s": int(ADVICE_REPEAT_COOLDOWN_S),
        "warning_threshold": float(AUTHORITY_THRESHOLDS.get(AuthorityLevel.WARNING, 0.8)),
        "note_threshold": float(AUTHORITY_THRESHOLDS.get(AuthorityLevel.NOTE, 0.5)),
        "whisper_threshold": float(AUTHORITY_THRESHOLDS.get(AuthorityLevel.WHISPER, 0.35)),
    }


def get_tool_cooldown_s() -> int:
    return max(1, int(TOOL_COOLDOWN_S))


@dataclass
class GateDecision:
    """Result of the gate evaluation for a single advice item."""
    advice_id: str
    authority: str
    emit: bool
    reason: str
    adjusted_score: float
    original_score: float


@dataclass
class GateResult:
    """Aggregate gate result for all advice items."""
    decisions: List[GateDecision]
    emitted: List[GateDecision]      # Only items with emit=True
    suppressed: List[GateDecision]   # Items filtered out
    phase: str
    total_retrieved: int


def evaluate(
    advice_items: list,
    state,  # SessionState
    tool_name: str,
    tool_input: Optional[dict] = None,
) -> GateResult:
    """
    Evaluate all advice items through the gate.

    Args:
        advice_items: List of Advice objects from advisor.py
        state: SessionState from advisory_state
        tool_name: Current tool being invoked
        tool_input: Tool input dict

    Returns:
        GateResult with decisions on what to emit
    """
    from .advisory_state import is_tool_suppressed, had_recent_read

    decisions = []
    phase = state.task_phase if state else "implementation"

    for advice in advice_items:
        decision = _evaluate_single(
            advice, state, tool_name, tool_input, phase
        )
        decisions.append(decision)

    # Sort by adjusted score descending
    decisions.sort(key=lambda d: d.adjusted_score, reverse=True)

    # Apply emission budget
    emitted = []
    suppressed = []
    emit_count = 0

    for d in decisions:
        if not d.emit:
            suppressed.append(d)
            continue

        if emit_count >= MAX_EMIT_PER_CALL:
            d.emit = False
            d.reason = f"budget exhausted ({MAX_EMIT_PER_CALL} max)"
            suppressed.append(d)
            continue

        emitted.append(d)
        emit_count += 1

    return GateResult(
        decisions=decisions,
        emitted=emitted,
        suppressed=suppressed,
        phase=phase,
        total_retrieved=len(advice_items),
    )


def _evaluate_single(
    advice,
    state,
    tool_name: str,
    tool_input: Optional[dict],
    phase: str,
) -> GateDecision:
    """Evaluate a single advice item through all gate filters."""
    from .advisory_state import is_tool_suppressed, had_recent_read

    advice_id = getattr(advice, "advice_id", "") or ""
    text = getattr(advice, "text", "") or ""
    confidence = getattr(advice, "confidence", 0.5) or 0.5
    source = getattr(advice, "source", "unknown") or "unknown"
    context_match = getattr(advice, "context_match", 0.5) or 0.5
    insight_key = getattr(advice, "insight_key", "") or ""

    # Base score from advisor ranking
    base_score = confidence * context_match

    # ---- Filter 1: Already shown? ----
    if state and advice_id in (state.shown_advice_ids or []):
        return GateDecision(
            advice_id=advice_id,
            authority=AuthorityLevel.SILENT,
            emit=False,
            reason="already shown this session",
            adjusted_score=0.0,
            original_score=base_score,
        )

    # ---- Filter 2: Tool suppressed? ----
    if state and is_tool_suppressed(state, tool_name):
        return GateDecision(
            advice_id=advice_id,
            authority=AuthorityLevel.SILENT,
            emit=False,
            reason=f"tool {tool_name} on cooldown",
            adjusted_score=0.0,
            original_score=base_score,
        )

    # ---- Filter 3: Obvious-from-context suppression ----
    suppressed, suppression_reason = _check_obvious_suppression(
        text, tool_name, tool_input, state
    )
    if suppressed:
        return GateDecision(
            advice_id=advice_id,
            authority=AuthorityLevel.SILENT,
            emit=False,
            reason=suppression_reason,
            adjusted_score=0.0,
            original_score=base_score,
        )

    # ---- Score Adjustment: Phase relevance ----
    phase_boosts = PHASE_RELEVANCE.get(phase, {})
    # Infer category from insight_key or source
    category = _infer_category(insight_key, source)
    phase_multiplier = phase_boosts.get(category, 1.0)
    adjusted_score = base_score * phase_multiplier

    # ---- Score Adjustment: Negative advisory boost ----
    # Advice about what NOT to do is more valuable than advice about what to do
    if _is_negative_advisory(text):
        adjusted_score *= 1.3

    # ---- Score Adjustment: Failure-context boost ----
    # If we're debugging, cautions get a big boost
    if state and state.consecutive_failures >= 1 and _is_caution(text):
        adjusted_score *= 1.5

    # ---- Determine authority level ----
    authority = _assign_authority(adjusted_score, confidence, text, source)

    # ---- Final emit decision ----
    emit = authority in (AuthorityLevel.NOTE, AuthorityLevel.WARNING)

    return GateDecision(
        advice_id=advice_id,
        authority=authority,
        emit=emit,
        reason=f"phase={phase}, score={adjusted_score:.2f}, authority={authority}",
        adjusted_score=adjusted_score,
        original_score=base_score,
    )


def _check_obvious_suppression(
    text: str,
    tool_name: str,
    tool_input: Optional[dict],
    state,
) -> Tuple[bool, str]:
    """Check if advice is obvious from context and should be suppressed."""
    from .advisory_state import had_recent_read

    text_lower = text.lower()

    # "Read before Edit" suppression: if the file was recently Read, don't say it
    if tool_name == "Edit" and "read before edit" in text_lower:
        file_path = ""
        if isinstance(tool_input, dict):
            file_path = str(tool_input.get("file_path", ""))
        if state and file_path and had_recent_read(state, file_path, within_s=120):
            return True, "file was recently Read, advice redundant"

    # Suppress generic tool advice when tool is being used correctly
    if tool_name == "Read" and "read" in text_lower and "before" not in text_lower:
        return True, "generic Read advice while already Reading"

    # Suppress deployment warnings during exploration phase
    if state and state.task_phase == "exploration":
        if any(w in text_lower for w in ("deploy", "push to prod", "release")):
            return True, "deployment advice during exploration phase"

    return False, ""


def _is_negative_advisory(text: str) -> bool:
    """Check if advice is about what NOT to do (higher value)."""
    negative_patterns = [
        r"\bdon'?t\b", r"\bavoid\b", r"\bnever\b", r"\bwatch out\b",
        r"\bcaution\b", r"\bwarning\b", r"\bcareful\b", r"\bdanger\b",
        r"\bpast failure\b", r"\bfailed when\b", r"\bbroke\b",
    ]
    text_lower = text.lower()
    return any(re.search(p, text_lower) for p in negative_patterns)


def _is_caution(text: str) -> bool:
    """Check if advice is a caution/warning."""
    return bool(re.search(
        r"\[caution\]|\[past failure\]|\[warning\]|⚠|❗",
        text, re.IGNORECASE
    ))


def _infer_category(insight_key: str, source: str) -> str:
    """Infer insight category from key or source."""
    if not insight_key:
        return source or "unknown"

    # insight_key format: "category:specific_key" or "prefix:key"
    parts = insight_key.split(":", 1)
    if len(parts) >= 1:
        prefix = parts[0].lower()
        category_map = {
            "self_awareness": "self_awareness",
            "struggle": "self_awareness",
            "user_understanding": "user_understanding",
            "user_pref": "user_understanding",
            "comm_style": "user_understanding",
            "reasoning": "reasoning",
            "context": "context",
            "wisdom": "wisdom",
            "meta_learning": "meta_learning",
            "creativity": "creativity",
            "communication": "communication",
        }
        return category_map.get(prefix, source or "unknown")
    return source or "unknown"


def _assign_authority(
    score: float,
    confidence: float,
    text: str,
    source: str,
) -> str:
    """Assign authority level based on score, confidence, and content."""
    # Block level is handled by EIDOS, not here

    # Warning: high score + proven pattern
    if score >= AUTHORITY_THRESHOLDS[AuthorityLevel.WARNING]:
        if _is_caution(text) or _is_negative_advisory(text):
            return AuthorityLevel.WARNING
        # High score but not a caution → still a note (don't over-warn)
        return AuthorityLevel.NOTE

    if score >= AUTHORITY_THRESHOLDS[AuthorityLevel.NOTE]:
        return AuthorityLevel.NOTE

    if score >= AUTHORITY_THRESHOLDS[AuthorityLevel.WHISPER]:
        return AuthorityLevel.WHISPER

    return AuthorityLevel.SILENT
