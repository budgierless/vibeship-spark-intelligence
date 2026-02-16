#!/usr/bin/env python3
"""Generate a redacted Spark x OpenClaw integration audit report."""

from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List


SENSITIVE_KEY_TOKENS = ("token", "apikey", "api_key", "secret", "password", "auth")
SECRET_LIKE_PATTERNS = (
    re.compile(r"^sk_[A-Za-z0-9]{16,}$"),
    re.compile(r"^AIza[0-9A-Za-z\-_]{16,}$"),
    re.compile(r"^\d{6,}:[A-Za-z0-9_\-]{16,}$"),
)


def _load_json(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8-sig"))
    except Exception:
        return {}
    return data if isinstance(data, dict) else {}


def _bool(value: Any) -> bool:
    return bool(value)


def _secret_like(value: str) -> bool:
    text = str(value or "").strip()
    if len(text) < 12:
        return False
    if text.startswith("${") and text.endswith("}"):
        return False
    for pat in SECRET_LIKE_PATTERNS:
        if pat.match(text):
            return True
    # Generic fallback for long opaque values.
    if len(text) >= 24 and " " not in text:
        return True
    return False


def _mask(value: str) -> str:
    text = str(value or "")
    if len(text) <= 6:
        return "*" * len(text)
    return f"{text[:3]}...{text[-3:]}"


def _scan_sensitive_fields(node: Any, prefix: str = "") -> List[Dict[str, str]]:
    out: List[Dict[str, str]] = []
    if isinstance(node, dict):
        for key, value in node.items():
            path = f"{prefix}.{key}" if prefix else str(key)
            key_l = str(key).lower()
            if isinstance(value, str) and any(tok in key_l for tok in SENSITIVE_KEY_TOKENS):
                if value.strip():
                    out.append(
                        {
                            "path": path,
                            "masked_value": _mask(value),
                            "secret_like": str(_secret_like(value)).lower(),
                        }
                    )
            out.extend(_scan_sensitive_fields(value, path))
        return out
    if isinstance(node, list):
        for i, value in enumerate(node):
            path = f"{prefix}[{i}]"
            out.extend(_scan_sensitive_fields(value, path))
    return out


def _openclaw_version(pkg: Dict[str, Any]) -> str:
    return str(pkg.get("version") or "unknown")


def _has_llm_hooks(cfg: Dict[str, Any]) -> bool:
    hooks = cfg.get("hooks") or {}
    if not isinstance(hooks, dict):
        hooks = {}
    raw = json.dumps(hooks).lower()
    if "llm_input" in raw and "llm_output" in raw:
        return True

    plugins = cfg.get("plugins") or {}
    if not isinstance(plugins, dict):
        return False
    entries = plugins.get("entries") or {}
    if not isinstance(entries, dict):
        return False
    telemetry_raw = entries.get("spark-telemetry-hooks")
    if not isinstance(telemetry_raw, dict):
        return False
    if telemetry_raw.get("enabled") is False:
        return False
    cfg = telemetry_raw.get("config") or {}
    if isinstance(cfg, dict) and str(cfg.get("spoolFile") or "").strip():
        return True
    # Allow explicit enabled=true even when config is inherited externally.
    return telemetry_raw.get("enabled") is True


def build_report(
    *,
    openclaw_config: Path,
    cron_jobs: Path,
    openclaw_package: Path,
) -> Dict[str, Any]:
    cfg = _load_json(openclaw_config)
    jobs = _load_json(cron_jobs)
    pkg = _load_json(openclaw_package)

    defaults = (((cfg.get("agents") or {}).get("defaults") or {}))
    subagents = (defaults.get("subagents") or {}) if isinstance(defaults, dict) else {}
    cron_cfg = (cfg.get("cron") or {}) if isinstance(cfg, dict) else {}

    job_rows = list((jobs.get("jobs") or [])) if isinstance(jobs, dict) else []
    health_job = None
    for row in job_rows:
        if str(row.get("name") or "").strip() == "spark-health-alert-watch":
            health_job = row
            break

    health_payload = ((health_job or {}).get("payload") or {})
    health_cmd = str(health_payload.get("message") or "")

    sensitive = _scan_sensitive_fields(cfg)
    secret_like = [row for row in sensitive if row.get("secret_like") == "true"]

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "paths": {
            "openclaw_config": str(openclaw_config),
            "cron_jobs": str(cron_jobs),
            "openclaw_package": str(openclaw_package),
        },
        "openclaw": {
            "version": _openclaw_version(pkg),
            "subagents": {
                "maxConcurrent": subagents.get("maxConcurrent"),
                "maxSpawnDepth": subagents.get("maxSpawnDepth"),
                "maxChildrenPerAgent": subagents.get("maxChildrenPerAgent"),
                "depth2_enabled": int(subagents.get("maxSpawnDepth") or 1) >= 2,
            },
            "cron": {
                "webhook_configured": _bool(cron_cfg.get("webhook")),
                "webhook_token_configured": _bool(cron_cfg.get("webhookToken")),
            },
            "hooks": {
                "llm_input_output_configured": _has_llm_hooks(cfg),
            },
        },
        "spark_health_job": {
            "present": health_job is not None,
            "command_has_alert_json": "--alert-json" in health_cmd,
            "command_has_confirm": "--confirm-seconds" in health_cmd,
            "command_has_auto_remediate": "--auto-remediate-core" in health_cmd,
            "command_has_fail_on_breach": "--fail-on-breach" in health_cmd,
        },
        "sensitive_fields": {
            "count": len(sensitive),
            "secret_like_count": len(secret_like),
            "fields": sensitive,
        },
    }


def _status(flag: bool) -> str:
    return "yes" if flag else "no"


def render_markdown(report: Dict[str, Any]) -> str:
    oc = report.get("openclaw") or {}
    sub = oc.get("subagents") or {}
    cron = oc.get("cron") or {}
    hooks = oc.get("hooks") or {}
    health = report.get("spark_health_job") or {}
    sens = report.get("sensitive_fields") or {}

    lines = [
        "# OpenClaw Integration Audit",
        "",
        f"- Generated: `{report.get('generated_at')}`",
        f"- OpenClaw version: `{oc.get('version')}`",
        "",
        "## Checks",
        "",
        "| Check | Status |",
        "|---|---|",
        f"| Subagent depth=2 enabled | `{_status(bool(sub.get('depth2_enabled')))}` |",
        f"| maxChildrenPerAgent set | `{_status(sub.get('maxChildrenPerAgent') is not None)}` |",
        f"| cron webhook configured | `{_status(bool(cron.get('webhook_configured')))}` |",
        f"| cron webhook token configured | `{_status(bool(cron.get('webhook_token_configured')))}` |",
        f"| llm_input/llm_output hooks configured | `{_status(bool(hooks.get('llm_input_output_configured')))}` |",
        f"| spark-health-alert-watch present | `{_status(bool(health.get('present')))}` |",
        f"| health job has --confirm-seconds | `{_status(bool(health.get('command_has_confirm')))}` |",
        f"| health job has --auto-remediate-core | `{_status(bool(health.get('command_has_auto_remediate')))}` |",
        "",
        "## Sensitive field scan (redacted)",
        "",
        f"- Total sensitive-key fields: `{sens.get('count', 0)}`",
        f"- Secret-like values: `{sens.get('secret_like_count', 0)}`",
        "",
        "## Next actions",
        "",
        "1. Apply missing config from `docs/openclaw/OPENCLAW_CONFIG_SNIPPETS.md`.",
        "2. Rotate any secret-like values found in local config.",
        "3. Re-run this audit after each OpenClaw config change and commit the report.",
        "",
    ]
    return "\n".join(lines)


def main() -> int:
    home = Path.home()
    ap = argparse.ArgumentParser(description="Audit Spark x OpenClaw integration state.")
    ap.add_argument(
        "--openclaw-config",
        type=Path,
        default=home / ".openclaw" / "openclaw.json",
    )
    ap.add_argument(
        "--cron-jobs",
        type=Path,
        default=home / ".openclaw" / "cron" / "jobs.json",
    )
    ap.add_argument(
        "--openclaw-package",
        type=Path,
        default=home / ".npm-global" / "node_modules" / "openclaw" / "package.json",
    )
    ap.add_argument(
        "--out-dir",
        type=Path,
        default=Path("docs") / "reports" / "openclaw",
    )
    args = ap.parse_args()

    report = build_report(
        openclaw_config=args.openclaw_config,
        cron_jobs=args.cron_jobs,
        openclaw_package=args.openclaw_package,
    )

    ts = datetime.now().strftime("%Y-%m-%d_%H%M%S")
    out_dir = args.out_dir
    out_dir.mkdir(parents=True, exist_ok=True)
    json_path = out_dir / f"{ts}_openclaw_integration_audit.json"
    md_path = out_dir / f"{ts}_openclaw_integration_audit.md"

    json_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    md_path.write_text(render_markdown(report), encoding="utf-8")

    print(str(json_path))
    print(str(md_path))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
