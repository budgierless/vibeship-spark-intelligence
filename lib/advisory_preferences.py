"""User-facing advisory preference setup helpers.

Designed for a 1-2 question setup flow:
1) Memory mode: off / standard / replay
2) Guidance style: concise / balanced / coach
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict


TUNEABLES_PATH = Path.home() / ".spark" / "tuneables.json"
VALID_MEMORY_MODES = {"off", "standard", "replay"}
VALID_GUIDANCE_STYLES = {"concise", "balanced", "coach"}


def _read_json(path: Path) -> Dict[str, Any]:
    try:
        if not path.exists():
            return {}
        try:
            return json.loads(path.read_text(encoding="utf-8-sig"))
        except Exception:
            return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _write_json_atomic(path: Path, payload: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    tmp.replace(path)


def _normalize_memory_mode(value: Any) -> str:
    mode = str(value or "").strip().lower()
    if mode in VALID_MEMORY_MODES:
        return mode
    return "standard"


def _normalize_guidance_style(value: Any) -> str:
    style = str(value or "").strip().lower()
    if style in VALID_GUIDANCE_STYLES:
        return style
    return "balanced"


def _derived_overrides(memory_mode: str, guidance_style: str) -> Dict[str, Any]:
    # Replay sensitivity profile
    replay_defaults = {
        "off": {
            "replay_enabled": False,
            "replay_min_strict": 8,
            "replay_min_delta": 0.40,
            "replay_max_age_s": 7 * 86400,
            "replay_strict_window_s": 1200,
            "replay_min_context": 0.35,
            "replay_max_records": 1200,
        },
        "standard": {
            "replay_enabled": True,
            "replay_min_strict": 5,
            "replay_min_delta": 0.25,
            "replay_max_age_s": 14 * 86400,
            "replay_strict_window_s": 1200,
            "replay_min_context": 0.18,
            "replay_max_records": 2500,
        },
        "replay": {
            "replay_enabled": True,
            "replay_min_strict": 3,
            "replay_min_delta": 0.15,
            "replay_max_age_s": 30 * 86400,
            "replay_strict_window_s": 1200,
            "replay_min_context": 0.10,
            "replay_max_records": 4500,
        },
    }[memory_mode]

    # General advisory intensity profile
    style_defaults = {
        "concise": {
            "max_items": 5,
            "min_rank_score": 0.60,
        },
        "balanced": {
            "max_items": 8,
            "min_rank_score": 0.55,
        },
        "coach": {
            "max_items": 10,
            "min_rank_score": 0.50,
        },
    }[guidance_style]

    out = dict(replay_defaults)
    out.update(style_defaults)
    out["replay_mode"] = memory_mode
    out["guidance_style"] = guidance_style
    return out


def setup_questions(current: Dict[str, Any] | None = None) -> Dict[str, Any]:
    now = current or {}
    return {
        "current": {
            "memory_mode": _normalize_memory_mode(now.get("memory_mode")),
            "guidance_style": _normalize_guidance_style(now.get("guidance_style")),
        },
        "questions": [
            {
                "id": "memory_mode",
                "question": "How much should Spark use past outcomes to suggest alternatives?",
                "options": [
                    {
                        "value": "standard",
                        "label": "Standard (Recommended)",
                        "description": "Shows replay alternatives only when evidence is strong.",
                    },
                    {
                        "value": "off",
                        "label": "Off",
                        "description": "Disables replay/counterfactual advisories.",
                    },
                    {
                        "value": "replay",
                        "label": "Replay-heavy",
                        "description": "Surfaces more historical alternatives with lower trigger threshold.",
                    },
                ],
            },
            {
                "id": "guidance_style",
                "question": "How verbose should advisory guidance be?",
                "options": [
                    {
                        "value": "balanced",
                        "label": "Balanced (Recommended)",
                        "description": "Mix of concise warnings and deeper actionable guidance.",
                    },
                    {
                        "value": "concise",
                        "label": "Concise",
                        "description": "Fewer advisories, higher rank threshold.",
                    },
                    {
                        "value": "coach",
                        "label": "Coach",
                        "description": "More guidance depth and alternatives per step.",
                    },
                ],
            },
        ],
    }


def get_current_preferences(path: Path = TUNEABLES_PATH) -> Dict[str, Any]:
    data = _read_json(path)
    advisor = data.get("advisor") if isinstance(data.get("advisor"), dict) else {}
    memory_mode = _normalize_memory_mode(advisor.get("replay_mode"))
    guidance_style = _normalize_guidance_style(advisor.get("guidance_style"))
    effective = _derived_overrides(memory_mode, guidance_style)
    # Keep explicit overrides visible if present.
    for key in (
        "replay_enabled",
        "replay_min_strict",
        "replay_min_delta",
        "replay_max_age_s",
        "replay_strict_window_s",
        "replay_min_context",
        "replay_max_records",
        "max_items",
        "min_rank_score",
    ):
        if key in advisor:
            effective[key] = advisor.get(key)
    return {
        "memory_mode": memory_mode,
        "guidance_style": guidance_style,
        "effective": effective,
    }


def apply_preferences(
    *,
    memory_mode: Any = None,
    guidance_style: Any = None,
    path: Path = TUNEABLES_PATH,
    source: str = "manual",
) -> Dict[str, Any]:
    existing = get_current_preferences(path=path)
    resolved_mode = _normalize_memory_mode(memory_mode or existing.get("memory_mode"))
    resolved_style = _normalize_guidance_style(guidance_style or existing.get("guidance_style"))

    data = _read_json(path)
    advisor = data.setdefault("advisor", {})
    if not isinstance(advisor, dict):
        advisor = {}
        data["advisor"] = advisor

    derived = _derived_overrides(resolved_mode, resolved_style)
    for key, value in derived.items():
        advisor[key] = value

    data["updated_at"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
    data["advisory_preferences"] = {
        "memory_mode": resolved_mode,
        "guidance_style": resolved_style,
        "source": str(source or "manual"),
        "updated_at": data["updated_at"],
    }
    _write_json_atomic(path, data)

    # Best effort hot-reload for active process.
    try:
        from .advisor import reload_advisor_config

        runtime = reload_advisor_config()
    except Exception:
        runtime = {}

    return {
        "ok": True,
        "memory_mode": resolved_mode,
        "guidance_style": resolved_style,
        "effective": derived,
        "runtime": runtime,
        "path": str(path),
    }

