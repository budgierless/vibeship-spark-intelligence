# On-Call + Incident Response (Local-First)

This is a lightweight incident playbook for Spark Intelligence.
For broader ops, see the `team` repo runbooks.

## Severity

- SEV-0: secrets leaked, guardrails bypassed by default, remote-exposed endpoints, data loss
- SEV-1: crash-loop, queue corruption, repeated watchdog restarts, pipeline health fails
- SEV-2: degraded learning (retrieval/utilization collapses), dashboards unusable, partial outages

## First 5 Minutes (Triage)

1. Confirm status:
   - `spark status`
   - `spark services`
2. Run quick gate:
   - `python tests/test_pipeline_health.py quick`
3. Check logs:
   - `C:\\Users\\<you>\\.spark\\logs\\` (see `DASHBOARD_PLAYBOOK.md`)
4. If unsafe behavior suspected:
   - set `SPARK_EIDOS_ENFORCE_BLOCK=1`
   - restart services

## Containment

- Reduce surface area:
  - `spark down`
  - `spark up --lite` (core services only)
- Disable optional integrations and dashboards if they are the fault domain.

## Recovery

- Identify the first failing component (sparkd / bridge_worker / Mind / dashboards).
- Fix the smallest thing that restores the SLOs.
- Re-run:
  - `python tests/test_pipeline_health.py`

## Postmortem (48h)

- What was the trigger?
- What was the blast radius?
- What guardrail/test/runbook change prevents recurrence?
- Link evidence (logs, trace IDs, test outputs) in a short report under `docs/reports/`.

