#!/usr/bin/env python3
"""
Spark Observation Hook: Ultra-fast event capture + Surprise Detection

This hook is called by Claude Code to capture tool usage events.
It MUST complete quickly to avoid slowdown.

NEW: Also detects surprising outcomes (unexpected success/failure).

Usage in .claude/settings.json:
{
  "hooks": {
    "PreToolUse": [{"matcher": "", "hooks": [{"type": "command", "command": "python /path/to/spark/hooks/observe.py"}]}],
    "PostToolUse": [{"matcher": "", "hooks": [{"type": "command", "command": "python /path/to/spark/hooks/observe.py"}]}],
    "PostToolUseFailure": [{"matcher": "", "hooks": [{"type": "command", "command": "python /path/to/spark/hooks/observe.py"}]}]
  }
}
"""

import sys
import json
import time
from pathlib import Path

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from lib.queue import quick_capture, EventType
from lib.cognitive_learner import get_cognitive_learner
from lib.feedback import update_skill_effectiveness, update_self_awareness_reliability
from lib.diagnostics import log_debug

# ===== Prediction Tracking =====
# We track predictions made at PreToolUse to compare at PostToolUse

PREDICTION_FILE = Path.home() / ".spark" / "active_predictions.json"


def save_prediction(session_id: str, tool_name: str, prediction: dict):
    """Save a prediction for later comparison."""
    try:
        PREDICTION_FILE.parent.mkdir(parents=True, exist_ok=True)
        
        predictions = {}
        if PREDICTION_FILE.exists():
            predictions = json.loads(PREDICTION_FILE.read_text())
        
        # Key by session + tool
        key = f"{session_id}:{tool_name}"
        predictions[key] = {
            **prediction,
            "timestamp": time.time()
        }
        
        # Clean old predictions (> 5 min old)
        cutoff = time.time() - 300
        predictions = {
            k: v for k, v in predictions.items()
            if v.get("timestamp", 0) > cutoff
        }
        
        PREDICTION_FILE.write_text(json.dumps(predictions))
    except Exception as e:
        log_debug("observe", "save_prediction failed", e)
        pass


def get_prediction(session_id: str, tool_name: str) -> dict:
    """Get prediction made for this tool call."""
    try:
        if not PREDICTION_FILE.exists():
            return {}
        
        predictions = json.loads(PREDICTION_FILE.read_text())
        key = f"{session_id}:{tool_name}"
        pred = predictions.pop(key, {})
        
        # Save without this prediction
        PREDICTION_FILE.write_text(json.dumps(predictions))
        
        return pred
    except Exception as e:
        log_debug("observe", "get_prediction failed", e)
        return {}


def make_prediction(tool_name: str, tool_input: dict) -> dict:
    """
    Make a prediction about this tool call.
    
    This is where we estimate likelihood of success based on:
    - Tool type
    - Input patterns
    - Historical data
    """
    # Default: 70% confident it will succeed
    confidence = 0.7
    outcome = "success"
    reason = "default assumption"
    
    # Adjust based on tool type and input
    if tool_name == "Edit":
        # Edit without knowing file content is risky
        confidence = 0.5
        reason = "Edit can fail if content doesn't match"
    
    elif tool_name == "Bash":
        command = str(tool_input.get("command", ""))
        # Dangerous commands are risky
        if any(x in command for x in ["rm -rf", "sudo", "chmod"]):
            confidence = 0.4
            reason = "Dangerous command pattern"
        # Complex pipes are risky
        elif command.count("|") > 2:
            confidence = 0.5
            reason = "Complex pipe chain"
    
    elif tool_name == "Write":
        # Write is usually safe
        confidence = 0.85
        reason = "Write usually succeeds"
    
    elif tool_name == "Read":
        # Read can fail on missing files
        confidence = 0.75
        reason = "File might not exist"
    
    return {
        "outcome": outcome,
        "confidence": confidence,
        "reason": reason,
        "tool": tool_name,
    }


# ===== Event Type Mapping =====

def get_event_type(hook_event_name: str) -> EventType:
    """Map hook event name to Spark event type."""
    mapping = {
        "SessionStart": EventType.SESSION_START,
        "UserPromptSubmit": EventType.USER_PROMPT,
        "PreToolUse": EventType.PRE_TOOL,
        "PostToolUse": EventType.POST_TOOL,
        "PostToolUseFailure": EventType.POST_TOOL_FAILURE,
        "Stop": EventType.STOP,
        "SessionEnd": EventType.SESSION_END,
    }
    return mapping.get(hook_event_name, EventType.POST_TOOL)


# ===== Learning Functions =====

def learn_from_failure(tool_name: str, error: str, tool_input: dict):
    """Extract learning from a failure event."""
    try:
        cognitive = get_cognitive_learner()
        error_lower = error.lower() if error else ""
        
        if "not found in file" in error_lower:
            cognitive.learn_assumption_failure(
                assumption="File content matches expectations",
                reality="Always Read before Edit to verify current content",
                context=f"Edit failed on {tool_input.get('file_path', 'unknown file')}"
            )
        elif "no such file" in error_lower or "not found" in error_lower:
            cognitive.learn_assumption_failure(
                assumption="File exists at expected path",
                reality="Use Glob to search for files before operating on them",
                context=f"{tool_name} failed: file not found"
            )
        elif "permission denied" in error_lower:
            cognitive.learn_blind_spot(
                what_i_missed="File permissions before operation",
                how_i_discovered=f"{tool_name} failed with permission denied"
            )
        
        cognitive.learn_struggle_area(
            task_type=f"{tool_name}_error",
            failure_reason=error[:200]
        )
    except Exception as e:
        log_debug("observe", "learn_from_failure failed", e)
        pass


def learn_from_success(tool_name: str, tool_input: dict, data: dict):
    """Extract learning from a success event."""
    try:
        cognitive = get_cognitive_learner()
        
        if tool_name == "Edit":
            if data.get("preceded_by_read"):
                cognitive.learn_why(
                    what_worked="Read then Edit sequence",
                    why_it_worked="Verifying content before editing prevents mismatch errors",
                    context="File editing workflow"
                )
    except Exception as e:
        log_debug("observe", "learn_from_success failed", e)
        pass


def check_for_surprise(session_id: str, tool_name: str, success: bool, error: str = None):
    """
    Check if outcome was surprising compared to prediction.
    
    This is where "aha moments" are born!
    """
    try:
        from lib.aha_tracker import get_aha_tracker, SurpriseType
        
        prediction = get_prediction(session_id, tool_name)
        if not prediction:
            return  # No prediction to compare
        
        predicted_success = prediction.get("outcome", "success") == "success"
        confidence = prediction.get("confidence", 0.5)
        
        tracker = get_aha_tracker()
        
        # Unexpected failure (thought it would succeed)
        if predicted_success and not success:
            confidence_gap = confidence  # High confidence + failure = high surprise
            if confidence_gap >= 0.5:
                tracker.capture_surprise(
                    surprise_type=SurpriseType.UNEXPECTED_FAILURE,
                    predicted=f"Success ({confidence:.0%} confident): {prediction.get('reason', '')}",
                    actual=f"Failed: {error[:100] if error else 'unknown error'}",
                    confidence_gap=confidence_gap,
                    context={
                        "tool": tool_name,
                        "prediction_reason": prediction.get("reason"),
                    },
                    lesson=f"Overestimated {tool_name} success likelihood" if confidence > 0.7 else None
                )
        
        # Unexpected success (thought it would fail)
        elif not predicted_success and success:
            confidence_gap = 1 - confidence  # Low confidence + success = high surprise
            if confidence_gap >= 0.5:
                tracker.capture_surprise(
                    surprise_type=SurpriseType.UNEXPECTED_SUCCESS,
                    predicted=f"Failure ({1-confidence:.0%} expected): {prediction.get('reason', '')}",
                    actual="Succeeded!",
                    confidence_gap=confidence_gap,
                    context={
                        "tool": tool_name,
                        "prediction_reason": prediction.get("reason"),
                    },
                    lesson=f"Underestimated {tool_name} - works better than expected" if confidence < 0.4 else None
                )
                
    except Exception as e:
        log_debug("observe", "check_for_surprise failed", e)
        pass


# ===== Main =====

def main():
    """Main hook entry point."""
    try:
        input_data = json.load(sys.stdin)
    except (json.JSONDecodeError, Exception) as e:
        log_debug("observe", "input JSON decode failed", e)
        sys.exit(0)
    
    session_id = input_data.get("session_id", "unknown")
    hook_event = input_data.get("hook_event_name", "unknown")
    tool_name = input_data.get("tool_name")
    tool_input = input_data.get("tool_input", {})
    
    event_type = get_event_type(hook_event)
    
    # ===== PreToolUse: Make prediction =====
    if event_type == EventType.PRE_TOOL and tool_name:
        prediction = make_prediction(tool_name, tool_input)
        save_prediction(session_id, tool_name, prediction)
    
    # ===== PostToolUse: Check for surprise =====
    if event_type == EventType.POST_TOOL and tool_name:
        check_for_surprise(session_id, tool_name, success=True)
        learn_from_success(tool_name, tool_input, {})
        try:
            update_self_awareness_reliability(tool_name, success=True)
            query = tool_name
            if isinstance(tool_input, dict):
                for k in ("command", "path", "file_path", "filePath"):
                    v = tool_input.get(k)
                    if isinstance(v, str) and v:
                        query = f"{query} {v[:120]}"
                        break
            update_skill_effectiveness(query, success=True, limit=2)
        except Exception:
            pass
    
    # ===== PostToolUseFailure: Check for surprise + learn =====
    if event_type == EventType.POST_TOOL_FAILURE and tool_name:
        error = (
            input_data.get("tool_error") or
            input_data.get("error") or
            input_data.get("tool_result") or
            ""
        )
        check_for_surprise(session_id, tool_name, success=False, error=str(error))
        learn_from_failure(tool_name, error, tool_input)
        try:
            update_self_awareness_reliability(tool_name, success=False)
            query = tool_name
            if isinstance(tool_input, dict):
                for k in ("command", "path", "file_path", "filePath"):
                    v = tool_input.get(k)
                    if isinstance(v, str) and v:
                        query = f"{query} {v[:120]}"
                        break
            update_skill_effectiveness(query, success=False, limit=2)
        except Exception:
            pass
    
    # Queue the event
    data = {
        "hook_event": hook_event,
        "cwd": input_data.get("cwd"),
    }

    # If this is a user prompt submit, try to capture the prompt text in a
    # portable shape that downstream systems expect:
    #   data.payload = { role: "user", text: "..." }
    # This keeps Spark core platform-agnostic and makes memory capture work.
    if hook_event == "UserPromptSubmit":
        txt = (
            input_data.get("prompt") or
            input_data.get("user_prompt") or
            input_data.get("text") or
            input_data.get("message") or
            ""
        )
        if isinstance(txt, dict):
            txt = txt.get("text") or ""
        txt = str(txt).strip()
        if txt:
            data["payload"] = {"role": "user", "text": txt}
            data["source"] = "claude_code"
            data["kind"] = "message"
    
    kwargs = {}
    if tool_name:
        kwargs["tool_name"] = tool_name
        kwargs["tool_input"] = tool_input
    
    if event_type == EventType.POST_TOOL_FAILURE:
        error = input_data.get("tool_error") or input_data.get("error") or ""
        if error:
            kwargs["error"] = str(error)[:500]
    
    quick_capture(event_type, session_id, data, **kwargs)
    sys.exit(0)


if __name__ == "__main__":
    main()
