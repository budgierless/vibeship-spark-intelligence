# OpenClaw Integration Audit

- Generated: `2026-02-16T14:05:23.734603+00:00`
- OpenClaw version: `2026.2.15`

## Checks

| Check | Status |
|---|---|
| Subagent depth=2 enabled | `yes` |
| maxChildrenPerAgent set | `yes` |
| cron webhook configured | `yes` |
| cron webhook token configured | `yes` |
| llm_input/llm_output hooks configured | `yes` |
| spark-health-alert-watch present | `yes` |
| health job has --confirm-seconds | `yes` |
| health job has --auto-remediate-core | `yes` |

## Sensitive field scan (redacted)

- Total sensitive-key fields: `5`
- Secret-like values: `4`

## Next actions

1. Apply missing config from `docs/openclaw/OPENCLAW_CONFIG_SNIPPETS.md`.
2. Rotate any secret-like values found in local config.
3. Re-run this audit after each OpenClaw config change and commit the report.
