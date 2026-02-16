# OpenClaw Integration Backlog

Last updated: 2026-02-16
Owner: Spark Intelligence
Status: Active

## Objective

Maintain an auditable backlog for Spark x OpenClaw integration changes, with:

- explicit gap statements,
- clear implementation tasks,
- validation criteria,
- deployment order.

## Current priorities

1. P0: Operational hardening
- [ ] Move OpenClaw credentials from plain `openclaw.json` values to environment/secret-store resolution.
- [ ] Configure `cron.webhook` + dedicated `cron.webhookToken` for finished-run notifications.
- [ ] Enable subagent nesting policy explicitly (`maxSpawnDepth=2`, conservative `maxChildrenPerAgent`).
- [ ] Wire `llm_input`/`llm_output` hook ingestion path to Spark telemetry.

2. P1: Reliability and observability
- [ ] Make KPI auto-remediation resilient in all invocation contexts (module/script execution modes).
- [ ] Add schema-transition dashboards for advisory feedback (`legacy` vs `schema_version=2`).
- [ ] Add weekly "strict quality" rollup report with source/tool/session lineage slices.

3. P2: Governance and lifecycle
- [ ] Add formal advisory promotion/decay policy doc with exploration budget.
- [ ] Add stale advisory re-test cadence and suppression expiry policy.
- [ ] Add monthly config audit with signed changelog entry.

## Validation gates

1. Security
- [ ] No raw secrets in committed files.
- [ ] Ingestion artifacts contain redacted tokens and safe allowlisted fields.

2. Attribution quality
- [ ] New advisory request records include `schema_version`, `trace_id`, `run_id`, `advisory_group_key`.
- [ ] Strict attribution metrics are computed from trace-bound outcome joins only.

3. Runtime health
- [ ] `spark-health-alert-watch` cron runs cleanly every hour.
- [ ] Breach alert includes concise summary and sampled failure snapshot.
- [ ] Auto-remediation only escalates after confirm delay.

## Tracking

- Primary changelog: `docs/openclaw/INTEGRATION_CHANGELOG.md`
- Path/sensitivity map: `docs/OPENCLAW_PATHS_AND_DATA_BOUNDARIES.md`
- Config snippets: `docs/openclaw/OPENCLAW_CONFIG_SNIPPETS.md`
