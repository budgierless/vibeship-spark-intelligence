# Troubleshooting KB (Public Alpha)

## 1) Services Won't Start

Checklist:
- Confirm Python 3.10+
- Run:
  - `python -m spark.cli health`
  - `python -m spark.cli services`
- Prefer starting services with:
  - Windows: `start_spark.bat`
  - Mac/Linux: `spark up`

## 2) Ports Already In Use

Symptoms:
- Service fails to bind, health checks fail.

Fix:
- Override ports with env vars (see `lib/ports.py` and `docs/QUICKSTART.md`).

## 3) Dashboards Not Loading

Checklist:
- Confirm services are running: `spark services`
- Pulse default: `http://127.0.0.1:8765`
- If running lite mode, dashboards may be disabled.

## 4) Queue Shows 0 Events

This is often normal if you have not generated tool interactions yet in the current session.
If you expect events:
- confirm hooks installed (Claude Code / Cursor docs)
- confirm tailer is running
- re-run: `python tests/test_pipeline_health.py quick`

## 5) Guardrails Blocking Actions

If you see `[EIDOS] BLOCKED: ...`:
- read the message and required action
- do not bypass for production contexts
- if you intentionally need to allow a class of actions, use explicit overrides and document them

Security issues: see `SECURITY.md`.

