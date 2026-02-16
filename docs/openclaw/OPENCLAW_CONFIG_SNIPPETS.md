# OpenClaw Config Snippets

Use these snippets in local `C:\Users\USER\.openclaw\openclaw.json` (not in repo).

## 1) Subagent depth policy

```json
{
  "agents": {
    "defaults": {
      "subagents": {
        "maxConcurrent": 8,
        "maxSpawnDepth": 2,
        "maxChildrenPerAgent": 3
      }
    }
  }
}
```

Notes:

- `maxSpawnDepth: 2` enables orchestrator pattern.
- Keep `maxChildrenPerAgent` conservative to avoid fan-out instability.

## 2) Cron finished-run webhook auth

```json
{
  "cron": {
    "webhook": "https://<your-private-endpoint>/openclaw/cron-finished",
    "webhookToken": "${OPENCLAW_CRON_WEBHOOK_TOKEN}"
  }
}
```

Notes:

- Use a dedicated token.
- Do not reuse gateway auth token.

## 3) Hook telemetry enablement (llm_input / llm_output)

Wire OpenClaw hook handlers so Spark receives model-aware telemetry:

- `llm_input`: prompt/input context shape
- `llm_output`: output/usage/route completion context

Implementation options:

1. Hook handlers post to Spark ingest endpoint directly.
2. Hook handlers write structured JSONL consumed by Spark tailer.

Required join fields to emit:

- `trace_id`
- `run_id` (if available)
- `session_id` / `session_key`
- model/provider/route metadata
- tool-call context

## 4) Secret hygiene policy

- Keep secrets in env or secret store, not raw JSON.
- Rotate existing exposed tokens immediately.
- Store only redacted operational artifacts in docs/reports.
