# Service Level Objectives (Local-First)

These SLOs are designed for a local-first alpha where the "site" is the user's machine.
They are still useful because they define when the system is stable enough to trust.

## SLO-1: sparkd readiness

- Indicator: `GET /status` returns 200 with `ok: true`
- Target: 99% over a 24h window (when services are running)
- Alert: readiness fails for 3 consecutive checks (>= 30s) or returns non-JSON

## SLO-2: bridge worker heartbeat freshness

- Indicator: `bridge_worker` heartbeat age (via CLI `spark services` or `/status`)
- Target: heartbeat age <= 90s
- Alert: heartbeat age > 120s

## SLO-3: queue safety

- Indicator: queue depth and rotation
- Target: queue within configured bounds (see `DASHBOARD_PLAYBOOK.md`)
- Alert: oldest-event age increases continuously for 10 minutes OR queue rotation fails

## SLO-4: dashboards usable

- Indicator: Pulse + dashboards return 200 and streams do not crash loop
- Target: dashboards reachable on localhost when enabled

