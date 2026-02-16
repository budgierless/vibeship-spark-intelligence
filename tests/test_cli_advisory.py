from __future__ import annotations

import json
from types import SimpleNamespace

import spark.cli as spark_cli


def _args(**kwargs):
    defaults = {
        "advisory_cmd": "show",
        "json": False,
        "source": "test",
        "memory_mode": None,
        "guidance_style": None,
    }
    defaults.update(kwargs)
    return SimpleNamespace(**defaults)


def test_cmd_advisory_show_json(monkeypatch, capsys):
    monkeypatch.setattr(
        spark_cli,
        "get_current_advisory_preferences",
        lambda: {
            "memory_mode": "standard",
            "guidance_style": "balanced",
            "effective": {"replay_enabled": True},
        },
    )
    monkeypatch.setattr(
        spark_cli,
        "_get_advisory_runtime_state",
        lambda: {"available": True, "engine_enabled": True, "emitter_enabled": True},
    )

    spark_cli.cmd_advisory(_args(advisory_cmd="show", json=True))
    payload = json.loads(capsys.readouterr().out)

    assert payload["memory_mode"] == "standard"
    assert payload["guidance_style"] == "balanced"
    assert payload["effective"]["replay_enabled"] is True
    assert payload["runtime"]["available"] is True


def test_cmd_advisory_setup_applies_current_when_non_interactive(monkeypatch):
    monkeypatch.setattr(
        spark_cli,
        "get_current_advisory_preferences",
        lambda: {
            "memory_mode": "standard",
            "guidance_style": "balanced",
            "effective": {"replay_enabled": True},
        },
    )
    monkeypatch.setattr(
        spark_cli,
        "get_advisory_setup_questions",
        lambda current: {
            "current": current,
            "questions": [
                {
                    "id": "memory_mode",
                    "question": "Q1",
                    "options": [{"value": "standard"}, {"value": "off"}, {"value": "replay"}],
                },
                {
                    "id": "guidance_style",
                    "question": "Q2",
                    "options": [{"value": "balanced"}, {"value": "concise"}, {"value": "coach"}],
                },
            ],
        },
    )

    calls = {}

    def _fake_apply(memory_mode=None, guidance_style=None, source=""):
        calls["memory_mode"] = memory_mode
        calls["guidance_style"] = guidance_style
        calls["source"] = source
        return {
            "memory_mode": memory_mode,
            "guidance_style": guidance_style,
            "effective": {"replay_enabled": memory_mode != "off"},
        }

    monkeypatch.setattr(spark_cli, "apply_advisory_preferences", _fake_apply)

    spark_cli.cmd_advisory(_args(advisory_cmd="setup", source="spark_cli_setup"))

    assert calls["memory_mode"] == "standard"
    assert calls["guidance_style"] == "balanced"
    assert calls["source"] == "spark_cli_setup"


def test_cmd_advisory_set_defaults_to_on_when_empty(monkeypatch):
    calls = {}

    def _fake_apply(memory_mode=None, guidance_style=None, source=""):
        calls["memory_mode"] = memory_mode
        calls["guidance_style"] = guidance_style
        calls["source"] = source
        return {
            "memory_mode": memory_mode,
            "guidance_style": guidance_style,
            "effective": {"replay_enabled": True},
        }

    monkeypatch.setattr(spark_cli, "apply_advisory_preferences", _fake_apply)

    spark_cli.cmd_advisory(_args(advisory_cmd="set", source="spark_cli_set"))

    assert calls["memory_mode"] == "standard"
    assert calls["guidance_style"] == "balanced"
    assert calls["source"] == "spark_cli_set"


def test_cmd_advisory_off_forces_memory_mode_off(monkeypatch):
    calls = {}

    def _fake_apply(memory_mode=None, guidance_style=None, source=""):
        calls["memory_mode"] = memory_mode
        calls["guidance_style"] = guidance_style
        calls["source"] = source
        return {
            "memory_mode": memory_mode,
            "guidance_style": guidance_style,
            "effective": {"replay_enabled": False},
        }

    monkeypatch.setattr(spark_cli, "apply_advisory_preferences", _fake_apply)

    spark_cli.cmd_advisory(
        _args(advisory_cmd="off", guidance_style="coach", source="spark_cli_off")
    )

    assert calls["memory_mode"] == "off"
    assert calls["guidance_style"] == "coach"
    assert calls["source"] == "spark_cli_off"


def test_print_advisory_preferences_uses_runtime_for_true_on_state(capsys):
    spark_cli._print_advisory_preferences(
        {
            "memory_mode": "standard",
            "guidance_style": "balanced",
            "effective": {"replay_enabled": True},
            "runtime": {
                "available": True,
                "engine_enabled": False,
                "emitter_enabled": True,
                "synth_tier": "Programmatic",
            },
        }
    )
    out = capsys.readouterr().out

    assert "advisory_on: no" in out
    assert "advisory_runtime: down" in out
    assert "replay_advisory: on" in out
