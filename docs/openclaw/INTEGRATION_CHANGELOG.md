# OpenClaw Integration Changelog

This log tracks Spark x OpenClaw integration changes that should be easy to audit later.

## 2026-02-16

### Added

- Introduced canonical local path and sensitivity map:
  - `docs/OPENCLAW_PATHS_AND_DATA_BOUNDARIES.md`
- Introduced structured integration backlog:
  - `docs/openclaw/INTEGRATION_BACKLOG.md`
- Added OpenClaw config snippet/runbook reference:
  - `docs/openclaw/OPENCLAW_CONFIG_SNIPPETS.md`

### Observed operational gaps

- OpenClaw `2026.2.15` is installed, but the active config does not explicitly set:
  - `agents.defaults.subagents.maxSpawnDepth`
  - `agents.defaults.subagents.maxChildrenPerAgent`
  - `cron.webhook` / `cron.webhookToken`
  - explicit `llm_input` / `llm_output` integration wiring
- Secrets are still present as plain values in local OpenClaw config and require hardening.

### Next steps

1. Apply config hardening from `docs/openclaw/OPENCLAW_CONFIG_SNIPPETS.md`.
2. Validate telemetry joins and strict attribution rates after config rollout.
3. Keep each change as a separate commit for rollback clarity.
