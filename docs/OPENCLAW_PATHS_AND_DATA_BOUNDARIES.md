# OpenClaw Paths And Data Boundaries

Last reviewed: 2026-02-16

## Canonical local paths

- `<OPENCLAW_HOME>\`: primary OpenClaw home directory
- `<OPENCLAW_HOME>\openclaw.json`: runtime config (agents/channels/gateway/plugins)
- `<OPENCLAW_HOME>\workspace\`: OpenClaw workspace files (memory/reports/skills artifacts)
- `<OPENCLAW_HOME>\agents\`: agent session artifacts and transcripts
- `<NPM_GLOBAL>\node_modules\openclaw\`: installed OpenClaw package code/docs/skills
- `C:\tmp\openclaw\`: runtime gateway logs
- `<SPARK_HOME>\`: Spark Intelligence runtime state (telemetry/outcomes/advisory logs)

## Data-sensitivity map

High sensitivity (do not commit or share raw):

- `<OPENCLAW_HOME>\openclaw.json`
- `<OPENCLAW_HOME>\credentials\`
- `<OPENCLAW_HOME>\identity\`
- `<OPENCLAW_HOME>\agents\` (can include prompts/tool outputs)
- `C:\tmp\openclaw\` logs (may include operational secrets/errors)
- `<SPARK_HOME>\` raw telemetry and outcome stores

Lower sensitivity (safer for summaries, still review before sharing):

- `<NPM_GLOBAL>\node_modules\openclaw\docs\`
- `<NPM_GLOBAL>\node_modules\openclaw\skills\`
- project-level reports that are already redacted

## Operational notes

- If OpenClaw package version changes, re-check `<NPM_GLOBAL>\node_modules\openclaw\package.json`.
- For cron health checks, source of truth is `<OPENCLAW_HOME>\cron\jobs.json` plus `<OPENCLAW_HOME>\cron\runs\`.
- For Spark advisory telemetry quality checks, start with:
  - `<SPARK_HOME>\advice_feedback_requests.jsonl`
  - `<SPARK_HOME>\advice_feedback.jsonl`
  - `<SPARK_HOME>\advisory_engine.jsonl`
  - `<SPARK_HOME>\bridge_worker_heartbeat.json`

