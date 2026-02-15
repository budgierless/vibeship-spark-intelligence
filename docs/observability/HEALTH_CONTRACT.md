# Health Contract

Spark Intelligence exposes two different concepts:

- Liveness: "process is up"
- Readiness: "system is usable and loops are healthy"

## sparkd

- `GET /health`
  - Purpose: liveness
  - Expected: HTTP 200 with plain body `ok`

- `GET /status`
  - Purpose: readiness + pipeline signal
  - Expected: HTTP 200 JSON with:
    - `ok: true`
    - `now` (unix seconds)
    - `port`
    - `bridge_worker.last_heartbeat`
    - `bridge_worker.pattern_backlog`
    - `bridge_worker.validation_backlog`
    - `pipeline` (when available)

## Dashboards

See `DASHBOARD_PLAYBOOK.md` for URLs and SSE endpoints.

