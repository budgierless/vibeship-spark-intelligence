from __future__ import annotations

import json

import lib.advisor as advisor_mod
import lib.advisory_preferences as prefs


def test_setup_questions_has_two_questions_and_normalized_current():
    payload = prefs.setup_questions({"memory_mode": "bad-value", "guidance_style": "COACH"})

    assert payload["current"]["memory_mode"] == "standard"
    assert payload["current"]["guidance_style"] == "coach"
    assert len(payload["questions"]) == 2
    assert payload["questions"][0]["id"] == "memory_mode"
    assert payload["questions"][1]["id"] == "guidance_style"


def test_apply_preferences_persists_tuneables_and_metadata(monkeypatch, tmp_path):
    tuneables = tmp_path / "tuneables.json"
    monkeypatch.setattr(
        advisor_mod,
        "reload_advisor_config",
        lambda: {"replay_mode": "replay", "guidance_style": "coach"},
    )

    out = prefs.apply_preferences(
        memory_mode="replay",
        guidance_style="coach",
        path=tuneables,
        source="test",
    )
    data = json.loads(tuneables.read_text(encoding="utf-8"))

    assert out["ok"] is True
    assert out["memory_mode"] == "replay"
    assert out["guidance_style"] == "coach"
    assert out["runtime"]["replay_mode"] == "replay"
    assert out["runtime"]["guidance_style"] == "coach"
    assert data["advisor"]["replay_mode"] == "replay"
    assert data["advisor"]["guidance_style"] == "coach"
    assert data["advisor"]["replay_enabled"] is True
    assert data["advisor"]["max_items"] == 10
    assert data["advisor"]["min_rank_score"] == 0.5
    assert data["advisory_preferences"]["memory_mode"] == "replay"
    assert data["advisory_preferences"]["guidance_style"] == "coach"
    assert data["advisory_preferences"]["source"] == "test"


def test_get_current_preferences_preserves_explicit_overrides(tmp_path):
    tuneables = tmp_path / "tuneables.json"
    tuneables.write_text(
        json.dumps(
            {
                "advisor": {
                    "replay_mode": "standard",
                    "guidance_style": "balanced",
                    "max_items": 3,
                    "replay_min_context": 0.42,
                }
            }
        ),
        encoding="utf-8",
    )

    out = prefs.get_current_preferences(path=tuneables)

    assert out["memory_mode"] == "standard"
    assert out["guidance_style"] == "balanced"
    assert out["effective"]["max_items"] == 3
    assert out["effective"]["replay_min_context"] == 0.42
