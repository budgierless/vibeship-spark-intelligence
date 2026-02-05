"""
EIDOS Integration: Connect EIDOS to Claude Code Hooks

This module bridges the EIDOS intelligence system with the Claude Code
hook system. It provides functions to:

1. Create Episodes when sessions start
2. Create Steps for each tool call (with prediction/result/evaluation)
3. Run Control Plane checks before tools execute
4. Capture Evidence from tool outputs
5. Run Distillation when sessions end

The Vertical Loop:
Action → Prediction → Outcome → Evaluation → Policy Update → Distillation → Mandatory Reuse
"""

import json
import os
import time
import hashlib
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from .models import (
    Episode, Step, Distillation, Policy,
    Budget, Phase, Outcome, Evaluation, ActionType
)
from .control_plane import get_control_plane, ControlDecision
from .memory_gate import MemoryGate, score_step_importance
from .distillation_engine import get_distillation_engine
from .store import get_store
from .evidence_store import get_evidence_store, Evidence, EvidenceType, create_evidence_from_tool
from .guardrails import GuardrailEngine
from .escalation import build_escalation, EscalationType
from .validation import validate_step, get_deferred_tracker

# Elevated Control Layer
from .elevated_control import (
    get_elevated_control_plane,
    WatcherAlert, EscapeProtocolResult,
    validate_step_envelope
)
from .minimal_mode import get_minimal_mode_controller


# ===== Session/Episode Tracking =====

ACTIVE_EPISODES_FILE = Path.home() / ".spark" / "eidos_active_episodes.json"
ACTIVE_STEPS_FILE = Path.home() / ".spark" / "eidos_active_steps.json"

# Stale episode threshold: episodes older than 30 min with no end_ts are abandoned
STALE_EPISODE_THRESHOLD_S = 1800


def _load_active_episodes() -> Dict[str, str]:
    """Load session_id -> episode_id mapping."""
    try:
        if ACTIVE_EPISODES_FILE.exists():
            return json.loads(ACTIVE_EPISODES_FILE.read_text())
    except Exception:
        pass
    return {}


def _save_active_episodes(mapping: Dict[str, str]):
    """Save session_id -> episode_id mapping."""
    try:
        ACTIVE_EPISODES_FILE.parent.mkdir(parents=True, exist_ok=True)
        ACTIVE_EPISODES_FILE.write_text(json.dumps(mapping))
    except Exception:
        pass


def _load_active_step(session_id: str) -> Optional[Dict]:
    """Load the active step for a session (used between pre and post tool)."""
    try:
        if ACTIVE_STEPS_FILE.exists():
            steps = json.loads(ACTIVE_STEPS_FILE.read_text())
            return steps.get(session_id)
    except Exception:
        pass
    return None


def _save_active_step(session_id: str, step_data: Optional[Dict]):
    """Save the active step for a session."""
    try:
        ACTIVE_STEPS_FILE.parent.mkdir(parents=True, exist_ok=True)
        steps = {}
        if ACTIVE_STEPS_FILE.exists():
            steps = json.loads(ACTIVE_STEPS_FILE.read_text())

        if step_data:
            steps[session_id] = step_data
        elif session_id in steps:
            del steps[session_id]

        # Clean old entries (> 10 min)
        cutoff = time.time() - 600
        steps = {k: v for k, v in steps.items() if v.get("timestamp", 0) > cutoff}

        ACTIVE_STEPS_FILE.write_text(json.dumps(steps))
    except Exception:
        pass


# ===== Episode Management =====

def get_or_create_episode(
    session_id: str,
    goal: str = "",
    cwd: str = ""
) -> Episode:
    """Get existing episode for session or create new one.

    If no goal is provided, a generic placeholder is used and can be
    refined later via ``update_episode_goal``.
    """
    store = get_store()
    mapping = _load_active_episodes()

    if session_id in mapping:
        episode = store.get_episode(mapping[session_id])
        if episode and episode.outcome == Outcome.IN_PROGRESS:
            # Check if episode is stale (no activity for STALE_EPISODE_THRESHOLD_S)
            elapsed = time.time() - episode.start_ts
            if elapsed > STALE_EPISODE_THRESHOLD_S and episode.step_count > 0:
                # Auto-close stale episode with partial outcome
                _auto_close_episode(store, episode)
                del mapping[session_id]
                _save_active_episodes(mapping)
                # Fall through to create a new one
            else:
                return episode

    # Derive a meaningful goal from cwd if none provided
    effective_goal = goal or _derive_goal_from_cwd(cwd)

    # Create new episode
    episode = Episode(
        episode_id="",
        goal=effective_goal,
        success_criteria="Complete user request successfully",
        constraints=[f"Working directory: {cwd}"] if cwd else [],
        budget=Budget(max_steps=50, max_time_seconds=1800)  # 30 min default
    )
    store.save_episode(episode)

    # Save mapping
    mapping[session_id] = episode.episode_id

    # Clean old mappings (keep last 100)
    if len(mapping) > 100:
        mapping = dict(list(mapping.items())[-100:])

    _save_active_episodes(mapping)

    return episode


def update_episode_goal(session_id: str, goal: str):
    """Update the goal of an active episode with a more specific description.

    Called when we get richer context (e.g., from a UserPromptSubmit event).
    """
    store = get_store()
    mapping = _load_active_episodes()
    if session_id not in mapping:
        return
    episode = store.get_episode(mapping[session_id])
    if not episode or episode.outcome != Outcome.IN_PROGRESS:
        return
    # Only update if current goal is generic
    if episode.goal and not episode.goal.startswith("Session in"):
        return
    episode.goal = goal[:200]
    store.save_episode(episode)


def _derive_goal_from_cwd(cwd: str) -> str:
    """Derive a meaningful goal from the working directory."""
    if not cwd:
        return "Session in unknown project"
    # Extract the last directory component
    parts = cwd.replace("\\", "/").rstrip("/").split("/")
    project = parts[-1] if parts else "unknown"
    return f"Session in {project}"


def _auto_close_episode(store, episode: Episode):
    """Auto-close a stale episode and run distillation."""
    steps = store.get_episode_steps(episode.episode_id)
    passed = sum(1 for s in steps if s.evaluation == Evaluation.PASS)
    failed = sum(1 for s in steps if s.evaluation == Evaluation.FAIL)

    if failed > passed:
        outcome = Outcome.FAILURE
    elif passed > 0:
        outcome = Outcome.PARTIAL
    else:
        outcome = Outcome.ESCALATED

    episode.outcome = outcome
    episode.phase = Phase.CONSOLIDATE
    episode.end_ts = time.time()
    episode.final_evaluation = f"Auto-closed: {passed} passed, {failed} failed out of {len(steps)} steps"
    store.save_episode(episode)

    # Run distillation on auto-closed episodes
    if steps:
        _run_distillation(episode, steps)


def complete_episode(
    session_id: str,
    outcome: Outcome = Outcome.SUCCESS,
    final_evaluation: str = ""
) -> Optional[Episode]:
    """
    Complete an episode and run distillation.

    Called when session ends or user explicitly completes a task.
    """
    store = get_store()
    mapping = _load_active_episodes()

    if session_id not in mapping:
        return None

    episode = store.get_episode(mapping[session_id])
    if not episode:
        return None

    # Determine outcome from step data if not explicitly set
    steps = store.get_episode_steps(episode.episode_id)
    if outcome == Outcome.SUCCESS and steps:
        passed = sum(1 for s in steps if s.evaluation == Evaluation.PASS)
        failed = sum(1 for s in steps if s.evaluation == Evaluation.FAIL)
        if failed > 0 and passed == 0:
            outcome = Outcome.FAILURE
        elif failed > passed:
            outcome = Outcome.PARTIAL

    # Build evaluation summary if none provided
    if not final_evaluation and steps:
        passed = sum(1 for s in steps if s.evaluation == Evaluation.PASS)
        failed = sum(1 for s in steps if s.evaluation == Evaluation.FAIL)
        final_evaluation = f"{passed} passed, {failed} failed out of {len(steps)} steps"

    # Update episode
    episode.outcome = outcome
    episode.phase = Phase.CONSOLIDATE
    episode.end_ts = time.time()
    episode.final_evaluation = final_evaluation
    store.save_episode(episode)

    # Run distillation
    if steps:
        _run_distillation(episode, steps)

    # Remove from active
    del mapping[session_id]
    _save_active_episodes(mapping)

    return episode


def _run_distillation(episode: Episode, steps: List[Step]):
    """Run distillation on a completed episode, filtering low-value outputs."""
    store = get_store()
    engine = get_distillation_engine()
    reflection = engine.reflect_on_episode(episode, steps)
    candidates = engine.generate_distillations(episode, steps, reflection)

    for candidate in candidates:
        # Filter out primitive/low-value distillations before saving
        if _is_primitive_distillation(candidate.statement):
            continue
        # Require minimum confidence
        if candidate.confidence < 0.4:
            continue
        distillation = engine.finalize_distillation(candidate)
        store.save_distillation(distillation)


def _is_primitive_distillation(statement: str) -> bool:
    """Check if a distillation is primitive/operational rather than genuine wisdom.

    The test: would a human find this useful to know next time?

    Rejects:
    - Tool effectiveness statements ("Tool X is effective")
    - Generic approach restating ("use approach: git push")
    - Sequence patterns ("A -> B -> C")
    - Test-result echoes ("test passes")
    - Tautological policy ("for X requests, do X")

    Keeps:
    - Domain decisions ("Use UTC for token timestamps")
    - User preferences ("user prefers iterative fixes")
    - Architecture insights ("why X over Y")
    - Actionable cautions ("Always Read before Edit")
    """
    import re
    s = statement.lower().strip()

    # Too short to be useful
    if len(s) < 20:
        return True

    # Primitive patterns to reject
    primitive_patterns = [
        r"is effective for",
        r"success rate",
        r"over \d+ uses",
        r"sequence.*->",
        r"tool '.*' is effective",
        r"took \d+ steps",
        r"could optimize discovery",
        r"^\w+ integration test",        # "EIDOS integration test passes"
        r"use approach:",                  # "use approach: git push origin main"
        r"for similar requests",           # tautological policy
        r"\(\d+ successes?\)",             # "(3 successes)"
        r"unexpected outcomes when handling",  # too vague
    ]
    for pat in primitive_patterns:
        if re.search(pat, s):
            return True

    return False


# ===== Step Management =====

def create_step_before_action(
    session_id: str,
    tool_name: str,
    tool_input: Dict[str, Any],
    prediction: Dict[str, Any],
    trace_id: Optional[str] = None
) -> Tuple[Optional[Step], Optional[ControlDecision]]:
    """
    Create a step BEFORE the tool executes.

    This implements the EIDOS vertical loop with Elevated Control:
    1. State intent and decision
    2. Make prediction (with hypothesis and stop condition)
    3. Check elevated control plane (watchers, escape protocol)
    4. Return step and control decision

    Returns:
        (Step, ControlDecision) - Step to complete later, control decision
    """
    episode = get_or_create_episode(session_id, cwd=tool_input.get("cwd", ""))
    store = get_store()
    elevated = get_elevated_control_plane()
    guardrails = GuardrailEngine()
    minimal = get_minimal_mode_controller()

    if not trace_id:
        raw = f"{session_id}|{tool_name}|{time.time()}"
        trace_id = hashlib.sha1(raw.encode("utf-8")).hexdigest()[:16]

    # Retrieve relevant distillations/memories for this step
    retrieved_memory_ids = []
    memory_cited = False
    memory_absent = True
    try:
        from .retriever import get_retriever
        retriever = get_retriever()
        intent_str = f"{tool_name} {str(tool_input)[:100]}"
        distillations = retriever.retrieve_for_intent(intent_str)
        if distillations:
            retrieved_memory_ids = [d.distillation_id for d in distillations[:5]]
            memory_cited = True
            memory_absent = False
    except Exception:
        pass  # Graceful degradation if retriever fails

    # Create step with FULL Step Envelope
    step = Step(
        step_id="",
        episode_id=episode.episode_id,
        trace_id=trace_id,
        intent=f"Execute {tool_name}",
        decision=f"Use {tool_name} tool",
        hypothesis=prediction.get("reason", ""),  # Falsifiable hypothesis
        alternatives=[],
        assumptions=_extract_assumptions(tool_name, tool_input),
        prediction=prediction.get("reason", "Tool will succeed"),
        stop_condition=f"If {tool_name} fails twice, diagnose before retry",  # Required
        confidence_before=prediction.get("confidence", 0.5),
        budget_snapshot={
            "step_count": episode.step_count,
            "max_steps": episode.budget.max_steps,
            "percentage_used": episode.budget_percentage_used(),
        },
        action_type=ActionType.TOOL_CALL,
        action_details={
            "tool": tool_name,
            **{k: str(v)[:200] for k, v in tool_input.items() if k != "content"}
        },
        retrieved_memories=retrieved_memory_ids,
        memory_cited=memory_cited,
        memory_absent_declared=memory_absent,
    )

    # Minimal mode gate
    allowed_mm, mm_reason = minimal.check_action_allowed(tool_name, tool_input)
    if not allowed_mm:
        return step, ControlDecision(
            allowed=False,
            message=mm_reason,
            required_action="diagnostics only until minimal mode exits"
        )

    # Get recent steps for context
    recent_steps = store.get_episode_steps(episode.episode_id)[-10:]

    # Check legacy guardrails first
    guard_result = guardrails.is_blocked(episode, step, recent_steps)
    if guard_result:
        return step, ControlDecision(
            allowed=False,
            message=guard_result.message,
            required_action="; ".join(guard_result.required_actions)
        )

    # Check elevated control plane (includes watchers and escape protocol)
    allowed, alerts, escape_result = elevated.check_before_action(
        episode, step, recent_steps, memories_exist=bool(retrieved_memory_ids)
    )

    if not allowed:
        # Build message from alerts or escape result
        if escape_result:
            message = f"ESCAPE PROTOCOL: {escape_result.reason}\n{escape_result.summary}"
            required = escape_result.discriminating_test
        elif alerts:
            message = "; ".join([a.message for a in alerts])
            required = alerts[0].required_output if alerts else ""
        else:
            message = "Action blocked by control plane"
            required = ""

        return step, ControlDecision(
            allowed=False,
            message=message,
            required_action=required
        )

    # Save step data for post-action completion (including retrieved distillation IDs)
    _save_active_step(session_id, {
        "step_id": step.step_id,
        "episode_id": episode.episode_id,
        "tool_name": tool_name,
        "prediction": prediction,
        "trace_id": trace_id,
        "timestamp": time.time(),
        "retrieved_distillation_ids": retrieved_memory_ids,
    })

    # Update episode step count
    episode.step_count += 1
    store.save_episode(episode)

    return step, ControlDecision(allowed=True, message="")


def complete_step_after_action(
    session_id: str,
    tool_name: str,
    success: bool,
    result: str = "",
    error: str = ""
) -> Optional[Step]:
    """
    Complete a step AFTER the tool executes.

    This implements the EIDOS vertical loop with Elevated Control:
    1. Record result with validation evidence
    2. Evaluate against prediction
    3. Calculate surprise and confidence delta
    4. Extract lesson
    5. Process through elevated control plane
    6. Score for memory persistence
    """
    step_data = _load_active_step(session_id)
    if not step_data or step_data.get("tool_name") != tool_name:
        return None

    episode = get_or_create_episode(session_id)
    store = get_store()
    elevated = get_elevated_control_plane()
    gate = MemoryGate()

    prediction = step_data.get("prediction", {})
    trace_id = step_data.get("trace_id")
    predicted_success = prediction.get("outcome", "success") == "success"
    confidence_before = prediction.get("confidence", 0.5)

    # Calculate evaluation
    if success:
        evaluation = Evaluation.PASS
    else:
        evaluation = Evaluation.FAIL

    # Calculate surprise
    surprise = 0.0
    if predicted_success and not success:
        surprise = confidence_before  # High confidence + failure = surprise
    elif not predicted_success and success:
        surprise = 1 - confidence_before  # Low confidence + success = surprise

    # Extract lesson
    lesson = _extract_lesson(tool_name, success, error, prediction)

    # Update confidence
    confidence_after = confidence_before
    if success:
        confidence_after = min(1.0, confidence_before + 0.1)
    else:
        confidence_after = max(0.1, confidence_before - 0.2)

    confidence_delta = confidence_after - confidence_before

    # Create completed step with FULL envelope
    step = Step(
        step_id=step_data.get("step_id", ""),
        episode_id=episode.episode_id,
        trace_id=trace_id,
        intent=f"Execute {tool_name}",
        decision=f"Use {tool_name} tool",
        hypothesis=prediction.get("reason", ""),
        prediction=prediction.get("reason", ""),
        stop_condition=f"If {tool_name} fails twice, diagnose",
        confidence_before=confidence_before,
        action_type=ActionType.TOOL_CALL,
        action_details={"tool": tool_name},
        result=result[:500] if result else (error[:500] if error else ""),
        validation_evidence=f"exit_code={'0' if success else '1'}; output_length={len(result or error or '')}",
        evaluation=evaluation,
        surprise_level=surprise,
        lesson=lesson,
        confidence_after=confidence_after,
        confidence_delta=confidence_delta,
        validated=True,
        validation_method="test:passed" if success else "test:failed",
        is_valid=True,
        evidence_gathered=bool(result or error),
        progress_made=success,
        memory_absent_declared=True,  # For now
    )

    # Save step
    store.save_step(step)

    # Process through elevated control plane
    new_phase, messages = elevated.process_after_action(episode, step)

    # Close feedback loop: mark retrieved distillations as helped/not-helped
    _update_distillation_feedback(step_data, success)

    # Score for memory persistence
    score = gate.score_step(step, context={"domain": "general"})
    if not score.is_durable:
        gate.set_cache_expiry(step.step_id, hours=24)

    # Capture evidence
    if result or error:
        ev_store = get_evidence_store()
        evidence = create_evidence_from_tool(
            step_id=step.step_id,
            tool_name=tool_name,
            output=error if error else result,
            exit_code=0 if success else 1,
            trace_id=trace_id,
        )
        ev_store.save(evidence)

    # Update episode phase if needed
    if new_phase != episode.phase:
        episode.phase = new_phase
        store.save_episode(episode)

    # Clear active step
    _save_active_step(session_id, None)

    return step


# ===== Helper Functions =====

def _update_distillation_feedback(step_data: Dict, success: bool):
    """Close the feedback loop: mark retrieved distillations as helped/not-helped.

    Uses the distillation IDs that were stored during the pre-action step,
    avoiding redundant re-queries. This is the critical missing piece --
    without it, distillations accumulate without ever knowing if they help.
    """
    distillation_ids = step_data.get("retrieved_distillation_ids", [])
    if not distillation_ids:
        return

    try:
        from .retriever import get_retriever
        retriever = get_retriever()
        for did in distillation_ids:
            retriever.record_usage(did, helped=success)
    except Exception:
        pass  # Never break the main flow


def _extract_assumptions(tool_name: str, tool_input: Dict) -> List[str]:
    """Extract assumptions for a tool call."""
    assumptions = []

    if tool_name == "Edit":
        assumptions.append("File exists at specified path")
        assumptions.append("old_string exists in file content")
    elif tool_name == "Read":
        assumptions.append("File exists and is readable")
    elif tool_name == "Write":
        assumptions.append("Parent directory exists")
        assumptions.append("Have write permissions")
    elif tool_name == "Bash":
        assumptions.append("Command is valid")
        assumptions.append("Required tools are installed")
    elif tool_name == "Glob":
        assumptions.append("Pattern will match files")
    elif tool_name == "Grep":
        assumptions.append("Pattern exists in searched files")

    return assumptions


def _extract_lesson(
    tool_name: str,
    success: bool,
    error: str,
    prediction: Dict
) -> str:
    """Extract a lesson from the tool execution result.

    Only returns non-empty lessons when there is genuine signal:
    - Surprising outcomes (high confidence wrong)
    - Actionable error patterns
    - Skips empty/generic lessons to avoid noise
    """
    confidence = prediction.get("confidence", 0.5)
    error_lower = error.lower() if error else ""

    if success:
        # Only generate lesson for genuinely surprising success
        if confidence < 0.35:
            return f"{tool_name} succeeded at {confidence:.0%} confidence - this pattern is more reliable than expected"
        # Successful as predicted -- no lesson needed, avoid noise
        return ""

    # Failure lessons -- only for actionable patterns
    if "not found in file" in error_lower:
        return "Always Read file before Edit to verify content matches"
    elif "no such file" in error_lower or "does not exist" in error_lower:
        return "Verify file exists with Glob before operating on it"
    elif "permission denied" in error_lower:
        return "Check file permissions before write operations"
    elif "timeout" in error_lower:
        return "Consider breaking into smaller operations or increasing timeout"
    elif "syntax error" in error_lower:
        return "Validate syntax before execution"
    elif "connection refused" in error_lower:
        return "Verify service is running before connecting"

    # Only flag high-confidence failures as lessons
    if confidence > 0.75:
        return f"Overconfident ({confidence:.0%}) on {tool_name} - reassess: {error[:60]}" if error else ""

    # Low/medium confidence failure -- not surprising, skip noise
    return ""


# ===== Convenience Functions =====

def should_block_action(session_id: str, tool_name: str, tool_input: Dict) -> Optional[str]:
    """
    Quick check if action should be blocked.

    Returns blocking message or None if allowed.
    """
    episode = get_or_create_episode(session_id)
    store = get_store()
    control = get_control_plane()
    guardrails = GuardrailEngine()
    minimal = get_minimal_mode_controller()

    allowed_mm, mm_reason = minimal.check_action_allowed(tool_name, tool_input)
    if not allowed_mm:
        return mm_reason

    # Create minimal step for checking
    step = Step(
        step_id="",
        episode_id=episode.episode_id,
        intent=f"Execute {tool_name}",
        decision=f"Use {tool_name}",
        action_type=ActionType.TOOL_CALL,
        action_details={"tool": tool_name, **tool_input}
    )

    recent_steps = store.get_episode_steps(episode.episode_id)[-10:]

    # Check guardrails
    guard_result = guardrails.is_blocked(episode, step, recent_steps)
    if guard_result:
        return guard_result.message

    # Check control plane
    decision = control.check_before_action(episode, step, recent_steps)
    if not decision.allowed:
        return decision.message

    return None


def get_active_episode_stats(session_id: str) -> Dict[str, Any]:
    """Get stats for the active episode."""
    episode = get_or_create_episode(session_id)
    store = get_store()
    steps = store.get_episode_steps(episode.episode_id)

    passed = len([s for s in steps if s.evaluation == Evaluation.PASS])
    failed = len([s for s in steps if s.evaluation == Evaluation.FAIL])

    return {
        "episode_id": episode.episode_id,
        "goal": episode.goal,
        "phase": episode.phase.value,
        "outcome": episode.outcome.value,
        "step_count": len(steps),
        "passed": passed,
        "failed": failed,
        "budget_remaining": episode.budget.max_steps - len(steps),
        "elapsed_seconds": time.time() - episode.start_ts,
    }


def generate_escalation(session_id: str, blocker: str) -> str:
    """Generate an escalation report for the current episode."""
    episode = get_or_create_episode(session_id)
    store = get_store()
    steps = store.get_episode_steps(episode.episode_id)

    # Determine escalation type
    if episode.is_budget_exceeded():
        esc_type = EscalationType.BUDGET
    elif any(c >= 3 for c in episode.error_counts.values()):
        esc_type = EscalationType.LOOP
    else:
        esc_type = EscalationType.BLOCKED

    escalation = build_escalation(episode, steps, esc_type, blocker)
    return escalation.to_yaml()


def get_eidos_health() -> Dict[str, Any]:
    """Get EIDOS system health summary for observability.

    Returns a dict with:
    - episode stats (total, active, completed, success rate)
    - distillation stats (total, used, helped, feedback ratio)
    - step stats (total, pass rate)
    - stale episode count
    """
    store = get_store()
    stats = store.get_stats()

    # Count stale episodes
    now = time.time()
    stale_count = 0
    try:
        recent = store.get_recent_episodes(limit=50)
        for ep in recent:
            if (ep.outcome == Outcome.IN_PROGRESS and
                    now - ep.start_ts > STALE_EPISODE_THRESHOLD_S):
                stale_count += 1
    except Exception:
        pass

    # Distillation feedback ratio
    dist_total = stats.get("distillations", 0)
    dist_used = 0
    dist_helped = 0
    try:
        all_dist = store.get_all_distillations(limit=100)
        dist_used = sum(1 for d in all_dist if d.times_used > 0)
        dist_helped = sum(1 for d in all_dist if d.times_helped > 0)
    except Exception:
        pass

    return {
        "episodes": {
            "total": stats.get("episodes", 0),
            "success_rate": stats.get("success_rate", 0),
            "stale": stale_count,
        },
        "steps": {
            "total": stats.get("steps", 0),
        },
        "distillations": {
            "total": dist_total,
            "used": dist_used,
            "helped": dist_helped,
            "feedback_ratio": dist_helped / max(dist_used, 1),
            "high_confidence": stats.get("high_confidence_distillations", 0),
        },
        "policies": stats.get("policies", 0),
    }


def cleanup_stale_episodes() -> int:
    """Clean up stale in_progress episodes. Returns count cleaned."""
    store = get_store()
    now = time.time()
    cleaned = 0

    try:
        recent = store.get_recent_episodes(limit=100)
        for ep in recent:
            if (ep.outcome == Outcome.IN_PROGRESS and
                    now - ep.start_ts > STALE_EPISODE_THRESHOLD_S and
                    ep.step_count > 0):
                _auto_close_episode(store, ep)
                cleaned += 1
    except Exception:
        pass

    return cleaned
