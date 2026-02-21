import json
from pathlib import Path

from scripts.openclaw_integration_audit import build_report, render_markdown


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _write_json_bom(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8-sig")


def test_build_report_detects_missing_config(tmp_path):
    cfg = tmp_path / "openclaw.json"
    jobs = tmp_path / "jobs.json"
    pkg = tmp_path / "package.json"

    _write_json(
        cfg,
        {
            "agents": {"defaults": {"subagents": {"maxConcurrent": 8}}},
            "hooks": {"internal": {"enabled": True, "entries": {"command-logger": {"enabled": True}}}},
        },
    )
    _write_json(jobs, {"jobs": []})
    _write_json(pkg, {"version": "2026.2.15"})

    report = build_report(openclaw_config=cfg, cron_jobs=jobs, openclaw_package=pkg)
    assert report["openclaw"]["subagents"]["depth2_enabled"] is False
    assert report["openclaw"]["cron"]["webhook_configured"] is False
    assert report["spark_health_job"]["present"] is False


def test_build_report_detects_health_job_flags(tmp_path):
    cfg = tmp_path / "openclaw.json"
    jobs = tmp_path / "jobs.json"
    pkg = tmp_path / "package.json"

    _write_json(
        cfg,
        {
            "agents": {
                "defaults": {
                    "subagents": {
                        "maxConcurrent": 8,
                        "maxSpawnDepth": 2,
                        "maxChildrenPerAgent": 3,
                    }
                }
            },
            "cron": {"webhook": "https://x", "webhookToken": "${OPENCLAW_CRON_WEBHOOK_TOKEN}"},
            "hooks": {"internal": {"entries": {"llm_input": {}, "llm_output": {}}}},
        },
    )
    _write_json(
        jobs,
        {
            "jobs": [
                {
                    "name": "spark-health-alert-watch",
                    "payload": {
                        "message": "python scripts\\carmack_kpi_scorecard.py --alert-json --confirm-seconds 60 --auto-remediate-core --fail-on-breach"
                    },
                }
            ]
        },
    )
    _write_json(pkg, {"version": "2026.2.15"})

    report = build_report(openclaw_config=cfg, cron_jobs=jobs, openclaw_package=pkg)
    assert report["openclaw"]["subagents"]["depth2_enabled"] is True
    assert report["openclaw"]["cron"]["webhook_configured"] is True
    assert report["spark_health_job"]["command_has_auto_remediate"] is True
    assert report["openclaw"]["hooks"]["llm_input_output_configured"] is True


def test_build_report_redacts_sensitive_fields(tmp_path):
    cfg = tmp_path / "openclaw.json"
    jobs = tmp_path / "jobs.json"
    pkg = tmp_path / "package.json"
    _write_json(
        cfg,
        {
            "channels": {"telegram": {"botToken": "000000:REDACTED_TOKEN"}},
            "gateway": {"auth": {"token": "pulse-local-bridge-token"}},
        },
    )
    _write_json(jobs, {"jobs": []})
    _write_json(pkg, {"version": "2026.2.15"})

    report = build_report(openclaw_config=cfg, cron_jobs=jobs, openclaw_package=pkg)
    sens = report["sensitive_fields"]
    assert sens["count"] >= 2
    assert sens["secret_like_count"] >= 1
    fields = sens["fields"]
    assert any("..." in row["masked_value"] for row in fields)

    md = render_markdown(report)
    assert "OpenClaw Integration Audit" in md


def test_build_report_detects_plugin_based_llm_hooks(tmp_path):
    cfg = tmp_path / "openclaw.json"
    jobs = tmp_path / "jobs.json"
    pkg = tmp_path / "package.json"
    _write_json(
        cfg,
        {
            "plugins": {
                "entries": {
                    "spark-telemetry-hooks": {
                        "enabled": True,
                        "config": {
                            "spoolFile": "<USER_HOME>\\.spark\\openclaw_hook_events.jsonl",
                        },
                    }
                }
            }
        },
    )
    _write_json(jobs, {"jobs": []})
    _write_json(pkg, {"version": "2026.2.15"})

    report = build_report(openclaw_config=cfg, cron_jobs=jobs, openclaw_package=pkg)
    assert report["openclaw"]["hooks"]["llm_input_output_configured"] is True


def test_build_report_handles_utf8_bom_config(tmp_path):
    cfg = tmp_path / "openclaw.json"
    jobs = tmp_path / "jobs.json"
    pkg = tmp_path / "package.json"
    _write_json_bom(
        cfg,
        {
            "agents": {
                "defaults": {
                    "subagents": {
                        "maxSpawnDepth": 2,
                        "maxChildrenPerAgent": 3,
                    }
                }
            },
            "cron": {"webhook": "${OPENCLAW_CRON_WEBHOOK_URL}", "webhookToken": "${OPENCLAW_CRON_WEBHOOK_TOKEN}"},
        },
    )
    _write_json(jobs, {"jobs": []})
    _write_json(pkg, {"version": "2026.2.15"})

    report = build_report(openclaw_config=cfg, cron_jobs=jobs, openclaw_package=pkg)
    assert report["openclaw"]["subagents"]["depth2_enabled"] is True
    assert report["openclaw"]["subagents"]["maxChildrenPerAgent"] == 3
    assert report["openclaw"]["cron"]["webhook_configured"] is True


def test_build_report_does_not_false_positive_empty_hook_entry(tmp_path):
    cfg = tmp_path / "openclaw.json"
    jobs = tmp_path / "jobs.json"
    pkg = tmp_path / "package.json"
    _write_json(
        cfg,
        {
            "plugins": {
                "entries": {
                    "spark-telemetry-hooks": {},
                }
            }
        },
    )
    _write_json(jobs, {"jobs": []})
    _write_json(pkg, {"version": "2026.2.15"})

    report = build_report(openclaw_config=cfg, cron_jobs=jobs, openclaw_package=pkg)
    assert report["openclaw"]["hooks"]["llm_input_output_configured"] is False


def test_build_report_does_not_flag_env_placeholders_as_secret_like(tmp_path):
    cfg = tmp_path / "openclaw.json"
    jobs = tmp_path / "jobs.json"
    pkg = tmp_path / "package.json"
    _write_json(
        cfg,
        {
            "gateway": {"auth": {"token": "${OPENCLAW_GATEWAY_TOKEN}"}},
            "cron": {"webhookToken": "${OPENCLAW_CRON_WEBHOOK_TOKEN}"},
        },
    )
    _write_json(jobs, {"jobs": []})
    _write_json(pkg, {"version": "2026.2.15"})

    report = build_report(openclaw_config=cfg, cron_jobs=jobs, openclaw_package=pkg)
    assert report["sensitive_fields"]["count"] >= 1
    assert report["sensitive_fields"]["secret_like_count"] == 0


