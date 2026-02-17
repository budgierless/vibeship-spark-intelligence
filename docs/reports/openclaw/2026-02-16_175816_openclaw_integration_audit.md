# OpenClaw Integration Audit

- Generated: `2026-02-16T13:58:16.486704+00:00`
- OpenClaw version: `2026.2.15`

## Checks

| Check | Status |
|---|---|
| Subagent depth=2 enabled | `no` |
| maxChildrenPerAgent set | `no` |
| cron webhook configured | `no` |
| cron webhook token configured | `no` |
| llm_input/llm_output hooks configured | `yes` |
| spark-health-alert-watch present | `yes` |
| health job has --confirm-seconds | `yes` |
| health job has --auto-remediate-core | `yes` |

## Sensitive field scan (redacted)

- Total sensitive-key fields: `0`
- Secret-like values: `0`

## Next actions

1. Apply missing config from `docs/openclaw/OPENCLAW_CONFIG_SNIPPETS.md`.
2. Rotate any secret-like values found in local config.
3. Re-run this audit after each OpenClaw config change and commit the report.
