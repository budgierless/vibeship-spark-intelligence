# OpenClaw Paths And Data Boundaries

Last reviewed: 2026-02-16

## Canonical local paths

- `C:\Users\USER\.openclaw\`: primary OpenClaw home directory
- `C:\Users\USER\.openclaw\openclaw.json`: runtime config (agents/channels/gateway/plugins)
- `C:\Users\USER\.openclaw\workspace\`: OpenClaw workspace files (memory/reports/skills artifacts)
- `C:\Users\USER\.openclaw\agents\`: agent session artifacts and transcripts
- `C:\Users\USER\.npm-global\node_modules\openclaw\`: installed OpenClaw package code/docs/skills
- `C:\tmp\openclaw\`: runtime gateway logs
- `C:\Users\USER\.spark\`: Spark Intelligence runtime state (telemetry/outcomes/advisory logs)

## Data-sensitivity map

High sensitivity (do not commit or share raw):

- `C:\Users\USER\.openclaw\openclaw.json`
- `C:\Users\USER\.openclaw\credentials\`
- `C:\Users\USER\.openclaw\identity\`
- `C:\Users\USER\.openclaw\agents\` (can include prompts/tool outputs)
- `C:\tmp\openclaw\` logs (may include operational secrets/errors)
- `C:\Users\USER\.spark\` raw telemetry and outcome stores

Lower sensitivity (safer for summaries, still review before sharing):

- `C:\Users\USER\.npm-global\node_modules\openclaw\docs\`
- `C:\Users\USER\.npm-global\node_modules\openclaw\skills\`
- project-level reports that are already redacted

## Operational notes

- If OpenClaw package version changes, re-check `C:\Users\USER\.npm-global\node_modules\openclaw\package.json`.
- For cron health checks, source of truth is `C:\Users\USER\.openclaw\cron\jobs.json` plus `C:\Users\USER\.openclaw\cron\runs\`.
- For Spark advisory telemetry quality checks, start with:
  - `C:\Users\USER\.spark\advice_feedback_requests.jsonl`
  - `C:\Users\USER\.spark\advice_feedback.jsonl`
  - `C:\Users\USER\.spark\advisory_engine.jsonl`
  - `C:\Users\USER\.spark\bridge_worker_heartbeat.json`
