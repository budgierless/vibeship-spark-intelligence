# Observability + On-Call (mission-1771186081212)

Date: 2026-02-16

## Artifacts Added

- `docs/observability/HEALTH_CONTRACT.md`
- `docs/observability/SLOS.md`
- `docs/observability/ONCALL_AND_INCIDENTS.md`
- `scripts/soak_health.ps1`

## Verification

- `GET http://127.0.0.1:8787/health` returns plain `ok` (liveness)
- `GET http://127.0.0.1:8787/status` returns JSON (readiness)
- 1-minute soak run succeeded and wrote:
  - `reports/launch-readiness/mission-1771186081212/soak_health.log`

Notes:
- /health is intentionally plain text; /status is the structured readiness endpoint.
