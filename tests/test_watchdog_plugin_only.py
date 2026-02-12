from pathlib import Path

import spark_watchdog


def test_plugin_only_mode_from_env(monkeypatch, tmp_path):
    sentinel = tmp_path / "plugin_only_mode"
    monkeypatch.setattr(spark_watchdog, "PLUGIN_ONLY_SENTINEL", sentinel)
    monkeypatch.setenv("SPARK_PLUGIN_ONLY", "1")
    assert spark_watchdog._plugin_only_mode_enabled() is True


def test_plugin_only_mode_from_sentinel(monkeypatch, tmp_path):
    sentinel = tmp_path / "plugin_only_mode"
    sentinel.parent.mkdir(parents=True, exist_ok=True)
    sentinel.write_text("1", encoding="utf-8")
    monkeypatch.setattr(spark_watchdog, "PLUGIN_ONLY_SENTINEL", sentinel)
    monkeypatch.delenv("SPARK_PLUGIN_ONLY", raising=False)
    assert spark_watchdog._plugin_only_mode_enabled() is True


def test_restart_allowed_keeps_core_services_in_plugin_only():
    assert spark_watchdog._restart_allowed("sparkd", plugin_only_mode=True) is True
    assert spark_watchdog._restart_allowed("scheduler", plugin_only_mode=True) is True
    assert spark_watchdog._restart_allowed("bridge_worker", plugin_only_mode=True) is False
    assert spark_watchdog._restart_allowed("pulse", plugin_only_mode=True) is False
    assert spark_watchdog._restart_allowed("dashboard", plugin_only_mode=True) is False
    assert spark_watchdog._restart_allowed("meta_ralph", plugin_only_mode=True) is False

