"""
Unified entry point for storing cognitive insights.

ALL paths that write to the cognitive store MUST go through
validate_and_store_insight(). This ensures every insight is:
1. Roasted by Meta-Ralph (quality gate)
2. Checked by cognitive noise filter
3. Quarantined on exception (fail-open)

Bypass paths closed (Batch 2):
- memory_capture.py commit_learning()
- feedback_loop.py _process_decision/outcome/preference()
- chip_merger.py distillation
- cognitive_signals.py extract_cognitive_signals()
- pipeline.py store_deep_learnings() floor

Rollback: Set flow.validate_and_store_enabled=false in tuneables.json
"""

from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any, Dict, Optional

from .diagnostics import log_debug

# Tuneable rollback switch
_ENABLED: Optional[bool] = None
TELEMETRY_FILE = Path.home() / ".spark" / "validate_and_store_telemetry.json"

# Telemetry counters (flushed periodically)
_counters: Dict[str, int] = {}
_flush_counter = 0
_FLUSH_INTERVAL = 20


def _is_enabled() -> bool:
    """Check if unified validation is enabled (cached)."""
    global _ENABLED
    if _ENABLED is not None:
        return _ENABLED
    # Check env var override first
    env = os.getenv("SPARK_VALIDATE_AND_STORE", "")
    if env == "0":
        _ENABLED = False
        return False
    if env == "1":
        _ENABLED = True
        return True
    # Check tuneables
    try:
        from .tuneables import get_tuneable
        val = get_tuneable("flow.validate_and_store_enabled", True)
        _ENABLED = bool(val)
    except Exception:
        _ENABLED = True
    return _ENABLED


def _record(counter: str) -> None:
    """Increment a telemetry counter, flush periodically."""
    global _flush_counter
    _counters[counter] = _counters.get(counter, 0) + 1
    _flush_counter += 1
    if _flush_counter >= _FLUSH_INTERVAL:
        _flush_counter = 0
        try:
            existing: Dict[str, Any] = {}
            if TELEMETRY_FILE.exists():
                existing = json.loads(TELEMETRY_FILE.read_text(encoding="utf-8"))
            for k, v in _counters.items():
                existing[k] = existing.get(k, 0) + v
            existing["_last_flush"] = time.time()
            TELEMETRY_FILE.write_text(json.dumps(existing, indent=2), encoding="utf-8")
            _counters.clear()
        except Exception:
            pass


def validate_and_store_insight(
    text: str,
    category,  # CognitiveCategory
    context: str = "",
    confidence: float = 0.7,
    source: str = "unknown",
    *,
    record_exposure: bool = True,
) -> bool:
    """
    Validate an insight through Meta-Ralph and store in cognitive learner.

    This is the ONLY sanctioned entry point for cognitive insight writes.

    Pipeline:
        1. Meta-Ralph roast (quality gate)
        2. Cognitive add_insight (has built-in noise filter)
        3. On Meta-Ralph exception → quarantine (fail-open)

    Returns:
        True if stored, False if rejected or quarantined.
    """
    if not text or not str(text).strip():
        return False

    # Rollback switch: bypass validation, direct write
    if not _is_enabled():
        try:
            from .cognitive_learner import get_cognitive_learner
            cog = get_cognitive_learner()
            result = cog.add_insight(
                category=category,
                insight=text,
                context=context,
                confidence=confidence,
                source=source,
                record_exposure=record_exposure,
            )
            return result is not None
        except Exception as e:
            log_debug("validate_and_store", "bypass_write_failed", e)
            return False

    _record("total_attempted")

    # Step 1: Meta-Ralph quality gate
    try:
        from .meta_ralph import get_meta_ralph, RoastVerdict
        ralph = get_meta_ralph()
        roast_result = ralph.roast(text, source=source)
        verdict = roast_result.verdict

        if verdict == RoastVerdict.PRIMITIVE:
            _record("roast_primitive")
            return False

        if verdict == RoastVerdict.DUPLICATE:
            _record("roast_duplicate")
            return False

        if verdict == RoastVerdict.NEEDS_WORK:
            # Use refined version if available, otherwise try original
            text = roast_result.refined_version or text
            _record("roast_needs_work")

        if verdict == RoastVerdict.QUALITY:
            # Use refined version if Meta-Ralph improved it
            text = roast_result.refined_version or text
            _record("roast_quality")

    except Exception as e:
        # Fail-open: quarantine the insight and continue
        _record("quarantined")
        try:
            from .advisory_quarantine import record_quarantine_item
            record_quarantine_item(
                text=text,
                reason=f"meta_ralph_exception: {e}",
                source=source,
                stage="validate_and_store",
                extra={"category": str(category), "confidence": confidence},
            )
        except Exception:
            pass
        log_debug("validate_and_store", "meta_ralph_failed_quarantined", e)
        return False

    # Step 2: Store through cognitive learner (has built-in noise filter)
    try:
        from .cognitive_learner import get_cognitive_learner
        cog = get_cognitive_learner()
        result = cog.add_insight(
            category=category,
            insight=text,
            context=context,
            confidence=confidence,
            source=source,
            record_exposure=record_exposure,
        )
        if result is not None:
            _record("stored")
            return True
        else:
            _record("noise_filtered")
            return False
    except Exception as e:
        _record("storage_failed")
        log_debug("validate_and_store", "cognitive_store_failed", e)
        return False
