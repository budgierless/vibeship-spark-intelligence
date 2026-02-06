from pathlib import Path

import lib.service_control as service_control
import spark_pulse


def test_start_services_uses_pulse_repo_as_cwd(monkeypatch, tmp_path):
    pulse_dir = tmp_path / "vibeship-spark-pulse"
    pulse_dir.mkdir(parents=True, exist_ok=True)
    pulse_app = pulse_dir / "app.py"
    pulse_app.write_text("print('pulse')\n", encoding="utf-8")

    monkeypatch.setattr(service_control, "SPARK_PULSE_DIR", pulse_dir)
    monkeypatch.setattr(
        service_control,
        "service_status",
        lambda bridge_stale_s=90: {
            "sparkd": {"running": True},
            "bridge_worker": {"running": True},
            "pulse": {"running": False},
        },
    )
    monkeypatch.setattr(
        service_control,
        "_service_cmds",
        lambda **kwargs: {"pulse": ["python", str(pulse_app)]},
    )

    captured = {}

    def _fake_start_process(name, args, cwd=None):
        captured["name"] = name
        captured["args"] = args
        captured["cwd"] = cwd
        return 12345

    monkeypatch.setattr(service_control, "_start_process", _fake_start_process)
    monkeypatch.setattr(service_control, "_wait_for_service_ready", lambda *a, **k: True)

    result = service_control.start_services(
        include_dashboard=False,
        include_meta_ralph=False,
        include_watchdog=False,
    )

    assert result["pulse"] == "started:12345"
    assert captured["name"] == "pulse"
    assert captured["cwd"] == pulse_dir
    assert captured["args"] == ["python", str(pulse_app)]


def test_redirector_launches_external_pulse_with_repo_cwd(monkeypatch, tmp_path):
    pulse_dir = tmp_path / "vibeship-spark-pulse"
    pulse_dir.mkdir(parents=True, exist_ok=True)
    pulse_app = pulse_dir / "app.py"
    pulse_app.write_text("print('pulse')\n", encoding="utf-8")

    monkeypatch.setattr(service_control, "SPARK_PULSE_DIR", pulse_dir)

    called = {}

    def _fake_call(args, cwd=None):
        called["args"] = args
        called["cwd"] = cwd
        return 0

    monkeypatch.setattr(spark_pulse.subprocess, "call", _fake_call)

    try:
        spark_pulse.main()
    except SystemExit as exc:
        assert exc.code == 0
    else:
        raise AssertionError("Expected SystemExit from spark_pulse.main()")

    assert called["args"][0] == spark_pulse.sys.executable
    assert called["args"][1] == str(pulse_app)
    assert called["cwd"] == str(pulse_dir)


def test_pulse_health_requires_api_and_ui(monkeypatch):
    calls = []

    def _fake_http_ok(url, timeout=1.5):
        calls.append(url)
        # Simulate docs healthy but UI broken.
        return "docs" in url

    monkeypatch.setattr(service_control, "_http_ok", _fake_http_ok)

    assert service_control._pulse_ok() is False
    assert service_control.PULSE_DOCS_URL in calls
    assert service_control.PULSE_UI_URL in calls


def test_resolve_pulse_dir_prefers_sibling(monkeypatch, tmp_path):
    root = tmp_path / "vibeship-spark-intelligence"
    root.mkdir(parents=True, exist_ok=True)
    sibling_pulse = tmp_path / "vibeship-spark-pulse"
    sibling_pulse.mkdir(parents=True, exist_ok=True)
    (sibling_pulse / "app.py").write_text("print('pulse')\n", encoding="utf-8")

    monkeypatch.delenv("SPARK_PULSE_DIR", raising=False)
    monkeypatch.setattr(service_control, "ROOT_DIR", root)

    resolved = service_control._resolve_pulse_dir()
    assert resolved == sibling_pulse


def test_service_status_detects_pulse_using_absolute_app_path(monkeypatch, tmp_path):
    pulse_dir = tmp_path / "custom-pulse-dir"
    pulse_dir.mkdir(parents=True, exist_ok=True)
    pulse_app = pulse_dir / "app.py"
    pulse_app.write_text("print('pulse')\n", encoding="utf-8")

    monkeypatch.setattr(service_control, "SPARK_PULSE_DIR", pulse_dir)
    monkeypatch.setattr(service_control, "_pulse_ok", lambda: False)
    monkeypatch.setattr(service_control, "_bridge_heartbeat_age", lambda: None)
    monkeypatch.setattr(service_control, "_read_pid", lambda name: None)
    monkeypatch.setattr(
        service_control,
        "_process_snapshot",
        lambda: [(32123, f'python "{pulse_app}"')],
    )

    status = service_control.service_status()
    assert status["pulse"]["running"] is True
    assert status["pulse"]["healthy"] is False
