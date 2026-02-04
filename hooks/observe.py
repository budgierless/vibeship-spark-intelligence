#!/usr/bin/env python3
"""
Spark Observation Hook: Ultra-fast event capture + Surprise Detection + EIDOS Integration

This hook is called by Claude Code to capture tool usage events.
It MUST complete quickly to avoid slowdown.

EIDOS Integration:
- PreToolUse: Create Episode/Step, make prediction, check control plane
- PostToolUse: Complete Step, evaluate prediction, capture evidence
- PostToolUseFailure: Complete Step with error, learn from failure

The Vertical Loop:
Action → Prediction → Outcome → Evaluation → Policy Update → Distillation → Mandatory Reuse

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
import os
import hashlib
from pathlib import Path
from typing import Optional

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from lib.queue import quick_capture, EventType
from lib.cognitive_learner import get_cognitive_learner
from lib.feedback import update_skill_effectiveness, update_self_awareness_reliability
from lib.diagnostics import log_debug
from lib.outcome_checkin import record_checkin_request
from lib.pattern_detection import get_aggregator

# EIDOS Integration
EIDOS_ENABLED = os.environ.get("SPARK_EIDOS_ENABLED", "1") == "1"

if EIDOS_ENABLED:
    try:
        from lib.eidos.integration import (
            create_step_before_action,
            complete_step_after_action,
            should_block_action,
            get_or_create_episode,
            complete_episode,
            generate_escalation,
        )
        from lib.eidos.models import Outcome
        EIDOS_AVAILABLE = True
    except ImportError as e:
        log_debug("observe", "EIDOS import failed", e)
        EIDOS_AVAILABLE = False
else:
    EIDOS_AVAILABLE = False

# ===== Prediction Tracking =====
# We track predictions made at PreToolUse to compare at PostToolUse

PREDICTION_FILE = Path.home() / ".spark" / "active_predictions.json"
CHECKIN_MIN_S = int(os.environ.get("SPARK_OUTCOME_CHECKIN_MIN_S", "1800"))
ADVICE_FEEDBACK_ENABLED = os.environ.get("SPARK_ADVICE_FEEDBACK", "1") == "1"
ADVICE_FEEDBACK_PROMPT = os.environ.get("SPARK_ADVICE_FEEDBACK_PROMPT", "1") == "1"
ADVICE_FEEDBACK_MIN_S = int(os.environ.get("SPARK_ADVICE_FEEDBACK_MIN_S", "600"))


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


# ===== Domain Detection =====

# Domain triggers for auto-detection (Improvement #6: Skill Domain Coverage)
DOMAIN_TRIGGERS = {
    "game_dev": [
        "player", "spawn", "physics", "collision", "balance", "gameplay",
        "difficulty", "level", "enemy", "health", "damage", "score",
        "inventory", "quest", "boss", "npc", "animation", "sprite",
        "tilemap", "hitbox", "frame rate", "fps", "game loop", "state machine",
    ],
    "fintech": [
        "payment", "transaction", "compliance", "risk", "audit", "kyc", "aml",
        "pci", "ledger", "settlement", "clearing", "fraud", "reconciliation",
        "banking", "wallet", "transfer", "fee", "interest", "loan", "credit",
    ],
    "marketing": [
        "audience", "campaign", "conversion", "roi", "funnel", "messaging",
        "channel", "brand", "engagement", "ctr", "impression", "retention",
        "acquisition", "segmentation", "persona", "content", "seo", "ad",
    ],
    "product": [
        "user", "feature", "feedback", "priority", "roadmap", "mvp",
        "backlog", "sprint", "story", "epic", "milestone", "release",
        "launch", "metric", "kpi", "adoption", "onboarding",
    ],
    "orchestration": [
        "workflow", "pipeline", "sequence", "parallel", "coordination",
        "handoff", "trigger", "event", "queue", "scheduler", "cron",
        "dag", "task", "step", "stage", "job", "batch",
    ],
    "architecture": [
        "pattern", "tradeoff", "scalability", "coupling", "interface",
        "abstraction", "modularity", "layer", "microservice", "monolith",
        "api", "contract", "schema", "migration", "refactor", "decouple",
    ],
    "agent_coordination": [
        "agent", "capability", "routing", "specialization", "collaboration",
        "escalation", "delegation", "context", "prompt", "chain", "tool",
        "memory", "reasoning", "planning", "retrieval", "rag",
    ],
    "team_management": [
        "delegation", "blocker", "review", "sprint", "standup", "retro",
        "pr", "merge", "conflict", "branch", "deploy", "release",
        "oncall", "incident", "postmortem",
    ],
    "ui_ux": [
        "layout", "component", "responsive", "accessibility", "a11y",
        "interaction", "animation", "modal", "form", "validation",
        "navigation", "menu", "button", "input", "dropdown", "theme",
        "dark mode", "mobile", "tablet", "desktop", "breakpoint",
    ],
    "debugging": [
        "error", "trace", "root cause", "hypothesis", "reproduce",
        "bisect", "isolate", "stacktrace", "breakpoint", "log",
        "assert", "crash", "exception", "bug", "regression", "flaky",
    ],
}


def detect_domain(text: str) -> Optional[str]:
    """
    Detect the domain from text content.

    Returns the domain with most trigger matches, or None if no clear match.
    """
    if not text:
        return None

    text_lower = text.lower()
    domain_scores = {}

    for domain, triggers in DOMAIN_TRIGGERS.items():
        score = sum(1 for t in triggers if t in text_lower)
        if score > 0:
            domain_scores[domain] = score

    if not domain_scores:
        return None

    # Return domain with highest score (at least 1 match)
    best_domain = max(domain_scores, key=domain_scores.get)
    return best_domain


def _make_trace_id(*parts: str) -> str:
    raw = "|".join(str(p or "") for p in parts).encode("utf-8")
    return hashlib.sha1(raw).hexdigest()[:16]


# ===== Cognitive Signal Extraction =====

# Patterns that indicate high-value cognitive content
COGNITIVE_PATTERNS = {
    "remember": [
        r"remember (this|that)",
        r"don't forget",
        r"important:",
        r"note:",
        r"always remember",
        r"keep in mind",
    ],
    "preference": [
        r"i (prefer|like|want|love|hate)",
        r"(prefer|like|want) (to |the )?",
        r"my preference",
        r"i'd rather",
    ],
    "decision": [
        r"(i |we |let's )(decided?|chose?|choosing|went with)",
        r"instead of",
        r"rather than",
        r"switched to",
        r"going with",
    ],
    "correction": [
        r"(no|not|wrong|incorrect|actually)",
        r"i meant",
        r"that's not",
        r"should be",
        r"fix that",
    ],
    "reasoning": [
        r"because",
        r"the reason",
        r"since",
        r"so that",
        r"in order to",
    ],
}

import re

def extract_cognitive_signals(text: str, session_id: str, trace_id: Optional[str] = None):
    """
    Extract cognitive signals from user messages and route to Meta-Ralph.

    Uses three scoring systems:
    1. Domain detection (context-aware learning)
    2. Pattern-based signal detection (fast)
    3. Importance scorer (semantic, more accurate)

    This is where we capture the GOOD stuff:
    - User preferences
    - Explicit decisions
    - Corrections/feedback
    - Reasoned statements
    """
    if not text or len(text) < 10:
        return

    text_lower = text.lower()
    signals_found = []

    # Detect domain for context-aware learning (Improvement #6)
    detected_domain = detect_domain(text)

    # Also use importance scorer for semantic analysis (with domain context)
    importance_score = None
    try:
        from lib.importance_scorer import get_importance_scorer
        scorer = get_importance_scorer(domain=detected_domain)
        importance_result = scorer.score(text)
        importance_score = importance_result.score

        # If importance scorer says it's valuable, add its signals
        if importance_score >= 0.5:
            signals_found.extend(importance_result.signals_detected)
    except Exception as e:
        log_debug("observe", "importance scorer failed", e)

    # Check each pattern category
    for category, patterns in COGNITIVE_PATTERNS.items():
        for pattern in patterns:
            if re.search(pattern, text_lower):
                signals_found.append(category)
                break

    # If any cognitive signals found, extract and roast
    if signals_found:
        try:
            # Get Meta-Ralph to evaluate (local import)
            from lib.meta_ralph import get_meta_ralph

            ralph = get_meta_ralph()

            # Extract the learning (use the full text if it's short, otherwise summarize)
            learning = text[:500] if len(text) <= 500 else text[:500] + "..."

            # Roast it with importance score + domain context
            result = ralph.roast(
                learning,
                source="user_prompt",
                context={
                    "signals": signals_found,
                    "session_id": session_id,
                    "trace_id": trace_id,
                    "importance_score": importance_score,
                    "is_priority": importance_score and importance_score >= 0.7,
                    "domain": detected_domain,  # Improvement #6: Domain context
                }
            )

            # Store quality items in cognitive learner
            if result.verdict.value == "quality":
                log_debug("observe", f"COGNITIVE CAPTURED: [{signals_found}] {text[:50]}...", None)

                # Determine category based on signals
                from lib.cognitive_learner import CognitiveCategory
                category = CognitiveCategory.USER_UNDERSTANDING  # default

                if "preference" in signals_found:
                    category = CognitiveCategory.USER_UNDERSTANDING
                elif "decision" in signals_found:
                    category = CognitiveCategory.REASONING
                elif "reasoning" in signals_found:
                    category = CognitiveCategory.REASONING
                elif "correction" in signals_found:
                    category = CognitiveCategory.CONTEXT
                elif "remember" in signals_found:
                    category = CognitiveCategory.WISDOM

                # Store the insight with domain context
                cognitive = get_cognitive_learner()
                domain_ctx = f", domain: {detected_domain}" if detected_domain else ""
                stored = cognitive.add_insight(
                    category=category,
                    insight=learning,
                    context=f"signals: {signals_found}, session: {session_id}{domain_ctx}",
                    confidence=0.7 + (importance_score * 0.2 if importance_score else 0)
                )

                if stored:
                    log_debug("observe", f"STORED: {category.value} - {learning[:40]}...", None)

        except Exception as e:
            log_debug("observe", "cognitive extraction failed", e)


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
    trace_id = input_data.get("trace_id")
    
    # ===== PreToolUse: Make prediction + Get advice + EIDOS step creation =====
    if event_type == EventType.PRE_TOOL and tool_name:
        trace_id = _make_trace_id(session_id, tool_name, hook_event, time.time())
        prediction = make_prediction(tool_name, tool_input)

        # Get advice from Advisor (tracks retrieval in Meta-Ralph)
        try:
            from lib.advisor import advise_on_tool
            advice = advise_on_tool(tool_name, tool_input, trace_id=trace_id)
            if advice:
                log_debug("observe", f"Got {len(advice)} advice items for {tool_name}", None)
                if ADVICE_FEEDBACK_ENABLED:
                    try:
                        from lib.advice_feedback import record_advice_request
                        record_advice_request(
                            session_id=session_id,
                            tool=tool_name,
                            advice_ids=[a.advice_id for a in advice],
                            min_interval_s=ADVICE_FEEDBACK_MIN_S,
                        )
                    except Exception:
                        pass
        except Exception as e:
            log_debug("observe", "advisor failed", e)
        save_prediction(session_id, tool_name, prediction)

        # EIDOS: Create step and check control plane
        if EIDOS_AVAILABLE:
            try:
                step, decision = create_step_before_action(
                    session_id=session_id,
                    tool_name=tool_name,
                    tool_input=tool_input,
                    prediction=prediction,
                    trace_id=trace_id
                )
                if step and step.trace_id:
                    trace_id = step.trace_id

                # If EIDOS blocks the action, output blocking message
                if decision and not decision.allowed:
                    # Write to stderr so Claude Code sees it
                    sys.stderr.write(f"[EIDOS] BLOCKED: {decision.message}\n")
                    if decision.required_action:
                        sys.stderr.write(f"[EIDOS] Required: {decision.required_action}\n")
            except Exception as e:
                log_debug("observe", "EIDOS pre-action failed", e)
    
    # ===== PostToolUse: Check for surprise + Track outcome + EIDOS step completion =====
    if event_type == EventType.POST_TOOL and tool_name:
        check_for_surprise(session_id, tool_name, success=True)
        learn_from_success(tool_name, tool_input, {})

        # EIDOS: Complete step with success
        if EIDOS_AVAILABLE:
            try:
                result = input_data.get("tool_result", "")
                if isinstance(result, dict):
                    result = json.dumps(result)[:500]
                elif result:
                    result = str(result)[:500]

                step = complete_step_after_action(
                    session_id=session_id,
                    tool_name=tool_name,
                    success=True,
                    result=result
                )
                if step and step.trace_id:
                    trace_id = step.trace_id
            except Exception as e:
                log_debug("observe", "EIDOS post-action failed", e)

        # Track outcome in Advisor (flows to Meta-Ralph)
        try:
            from lib.advisor import report_outcome
            # Only mark advice as helpful with explicit evidence (avoid hallucinated outcomes).
            report_outcome(tool_name, success=True, advice_helped=False, trace_id=trace_id)
        except Exception as e:
            log_debug("observe", "outcome tracking failed", e)

        # COGNITIVE SIGNAL EXTRACTION FROM CODE CONTENT
        # Analyze code comments, docstrings for learning signals like REMEMBER:, PRINCIPLE:, CORRECTION:
        if tool_name in ("Write", "Edit") and isinstance(tool_input, dict):
            # For Write: analyze "content", for Edit: analyze "new_string"
            content = tool_input.get("content") or tool_input.get("new_string") or ""
            if content and len(content) > 50:  # Skip tiny writes
                try:
                    # Extract signals from the written/edited content
                    extract_cognitive_signals(content, session_id, trace_id=trace_id)
                    log_debug("observe", f"Analyzed {tool_name} content for cognitive signals ({len(content)} chars)")
                except Exception as e:
                    log_debug("observe", f"{tool_name} content signal extraction failed", e)

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
    
    # ===== PostToolUseFailure: Check for surprise + Track outcome + learn + EIDOS step completion =====
    if event_type == EventType.POST_TOOL_FAILURE and tool_name:
        error = (
            input_data.get("tool_error") or
            input_data.get("error") or
            input_data.get("tool_result") or
            ""
        )
        check_for_surprise(session_id, tool_name, success=False, error=str(error))
        learn_from_failure(tool_name, error, tool_input)

        # Track failure outcome in Advisor (flows to Meta-Ralph)
        try:
            from lib.advisor import report_outcome
            report_outcome(tool_name, success=False, advice_helped=False, trace_id=trace_id)
        except Exception as e:
            log_debug("observe", "failure outcome tracking failed", e)

        # EIDOS: Complete step with failure
        if EIDOS_AVAILABLE:
            try:
                step = complete_step_after_action(
                    session_id=session_id,
                    tool_name=tool_name,
                    success=False,
                    error=str(error)[:500] if error else ""
                )
                if step and step.trace_id:
                    trace_id = step.trace_id
            except Exception as e:
                log_debug("observe", "EIDOS post-failure failed", e)

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
            trace_id = _make_trace_id(session_id, "user_prompt", txt, time.time())
            data["payload"] = {"role": "user", "text": txt}
            data["source"] = "claude_code"
            data["kind"] = "message"

            # COGNITIVE SIGNAL EXTRACTION
            # Look for high-value cognitive signals in user messages
            extract_cognitive_signals(txt, session_id, trace_id=trace_id)
    
    if trace_id:
        data["trace_id"] = trace_id

    kwargs = {}
    if tool_name:
        kwargs["tool_name"] = tool_name
        kwargs["tool_input"] = tool_input
    if trace_id:
        kwargs["trace_id"] = trace_id
    
    if event_type == EventType.POST_TOOL_FAILURE:
        error = input_data.get("tool_error") or input_data.get("error") or ""
        if error:
            kwargs["error"] = str(error)[:500]
    
    quick_capture(event_type, session_id, data, **kwargs)

    # Feed event to pattern aggregator (enables pattern detection + distillation)
    try:
        aggregator = get_aggregator()
        event_data = {
            "event_type": event_type.value,
            "session_id": session_id,
            "tool_name": tool_name,
            "tool_input": tool_input,
            "hook_event": hook_event,
            "trace_id": trace_id,
            **data
        }
        aggregator.process_event(event_data)
    except Exception as e:
        log_debug("observe", "aggregator failed", e)

    # Optional: emit a lightweight outcome check-in request at session end.
    if hook_event in ("Stop", "SessionEnd") and os.environ.get("SPARK_OUTCOME_CHECKIN") == "1":
        recorded = record_checkin_request(
            session_id=session_id,
            event=hook_event,
            reason="session_end",
            min_interval_s=CHECKIN_MIN_S,
        )
        if recorded and os.environ.get("SPARK_OUTCOME_CHECKIN_PROMPT") == "1":
            sys.stderr.write("[SPARK] Outcome check-in: run `spark outcome`\\n")

    # Optional: prompt for advice feedback at session end.
    if hook_event in ("Stop", "SessionEnd") and ADVICE_FEEDBACK_PROMPT:
        try:
            from lib.advice_feedback import has_recent_requests
            if has_recent_requests():
                sys.stderr.write("[SPARK] Advice feedback pending: run `spark advice-feedback --pending`\\n")
        except Exception:
            pass

    # EIDOS: Complete episode on session end (triggers distillation)
    if hook_event in ("Stop", "SessionEnd") and EIDOS_AVAILABLE:
        try:
            episode = complete_episode(session_id, Outcome.SUCCESS)
            if episode:
                log_debug("observe", f"EIDOS episode {episode.episode_id} completed", None)
        except Exception as e:
            log_debug("observe", "EIDOS episode completion failed", e)

    sys.exit(0)


if __name__ == "__main__":
    main()
