"""Centralized port configuration for Spark services."""

from __future__ import annotations

import os


def _env_int(name: str, default: int) -> int:
    raw = os.environ.get(name)
    if raw is None or raw == "":
        return default
    try:
        return int(raw)
    except Exception:
        return default


SPARKD_PORT = _env_int("SPARKD_PORT", 8787)
DASHBOARD_PORT = _env_int("SPARK_DASHBOARD_PORT", 8585)
PULSE_PORT = _env_int("SPARK_PULSE_PORT", 8765)
META_RALPH_PORT = _env_int("SPARK_META_RALPH_PORT", 8586)
MIND_PORT = _env_int("SPARK_MIND_PORT", 8080)


def _host(host: str | None) -> str:
    return host or "127.0.0.1"


def build_url(port: int, host: str | None = None) -> str:
    return f"http://{_host(host)}:{port}"


SPARKD_URL = build_url(SPARKD_PORT)
DASHBOARD_URL = build_url(DASHBOARD_PORT)
PULSE_URL = build_url(PULSE_PORT)
META_RALPH_URL = build_url(META_RALPH_PORT)
MIND_URL = build_url(MIND_PORT)

SPARKD_HEALTH_URL = f"{SPARKD_URL}/health"
DASHBOARD_STATUS_URL = f"{DASHBOARD_URL}/health"
PULSE_STATUS_URL = f"{PULSE_URL}/api/status"
META_RALPH_HEALTH_URL = f"{META_RALPH_URL}/health"
MIND_HEALTH_URL = f"{MIND_URL}/health"
