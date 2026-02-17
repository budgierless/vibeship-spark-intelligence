"""Consciousness bridge V1: local file contract reader + bounded mapper.

Low-risk helper module (not yet hard-wired into runtime-critical paths).
"""

from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any, Dict, Optional

DEFAULT_BRIDGE_PATH = (
    Path(os.environ.get("USERPROFILE", str(Path.home())))
    / ".spark"
    / "bridges"
    / "consciousness"
    / "emotional_context.v1.json"
)

DEFAULT_STRATEGY = {
    "response_pace": "balanced",
    "verbosity": "medium",
    "tone_shape": "grounded_warm",
    "ask_clarifying_question": False,
}


def _clamp(value: float, lo: float, hi: float) -> float:
    try:
        v = float(value)
    except Exception:
        return lo
    return max(lo, min(hi, v))


def _is_safe_boundaries(boundaries: Dict[str, Any]) -> bool:
    return bool(
        boundaries.get("user_guided") is True
        and boundaries.get("no_autonomous_objectives") is True
        and boundaries.get("no_manipulative_affect") is True
    )


def read_consciousness_bridge(path: Optional[Path] = None) -> Optional[Dict[str, Any]]:
    """Read and validate bridge payload. Returns None on soft failure."""
    target = path or DEFAULT_BRIDGE_PATH
    if not target.exists():
        return None

    try:
        payload = json.loads(target.read_text(encoding="utf-8"))
    except Exception:
        return None

    if payload.get("schema_version") != "bridge.v1":
        return None

    if not _is_safe_boundaries(payload.get("boundaries") or {}):
        return None

    # Freshness check: compare file mtime to advertised TTL
    ttl = int((payload.get("meta") or {}).get("ttl_seconds", 120))
    age_s = max(0, int(time.time() - target.stat().st_mtime))
    if age_s > max(5, ttl):
        return None

    return payload


def to_bounded_strategy(payload: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """Map bridge payload to advisory-safe strategy with strict bounds."""
    if not payload:
        return {
            "strategy": dict(DEFAULT_STRATEGY),
            "max_influence": 0.0,
            "source": "fallback",
        }

    guidance = payload.get("guidance") or {}
    boundaries = payload.get("boundaries") or {}

    strategy = {
        "response_pace": str(guidance.get("response_pace") or DEFAULT_STRATEGY["response_pace"]),
        "verbosity": str(guidance.get("verbosity") or DEFAULT_STRATEGY["verbosity"]),
        "tone_shape": str(guidance.get("tone_shape") or DEFAULT_STRATEGY["tone_shape"]),
        "ask_clarifying_question": bool(
            guidance.get("ask_clarifying_question", DEFAULT_STRATEGY["ask_clarifying_question"])
        ),
    }

    # Hard upper bound: emotional context is advisory only.
    max_influence = _clamp(boundaries.get("max_influence", 0.25), 0.0, 0.35)

    return {
        "strategy": strategy,
        "max_influence": max_influence,
        "source": "consciousness_bridge_v1",
    }


def resolve_strategy(path: Optional[Path] = None) -> Dict[str, Any]:
    """Convenience: read + map in one call, always returns safe dict."""
    payload = read_consciousness_bridge(path=path)
    return to_bounded_strategy(payload)
