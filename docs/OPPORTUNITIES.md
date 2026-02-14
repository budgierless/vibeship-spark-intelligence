# Opportunity Scanner

Spark's Opportunity Scanner generates self-improvement opportunities while you work.
The goal is not to log ideas, but to convert them into verified improvements.

Design constraints:
- Cognitive, not telemetry: it filters noise like trace ids, heartbeat logs, status codes, tool_*_error strings.
- Guardrailed: respects Spark consciousness kernel checks (non-harm, service, clarity).
- Provider policy: Opportunity Scanner deep scans never use DeepSeek.

## Scopes

Each opportunity is tagged so it can be reused correctly:
- `project`: applies to the current repo/task (default when a project id can be inferred)
- `operation`: applies to a reusable mode of work (marketing, cinematic creation, vibe coding, research)
- `spark_global`: improves Spark itself across all work

## Tagging (How To Control Scope)

Add explicit tags in your prompt/edit text:
- `scope:project`
- `scope:operation op:marketing`
- `scope:operation op:cinematic_creation`
- `scope:global`

Operation names must be lowercase `a-z0-9_-`.

## Cadence (Heuristic + Deep Scan)

Spark runs:
- a cheap heuristic scan every `bridge_worker` cycle
- an LLM deep scan (MiniMax) at most once per cooldown window

Recommended default while actively building:
- `SPARK_OPPORTUNITY_LLM_COOLDOWN_S=900` (15 minutes)

The cooldown is keyed by scope (`scope_type:scope_id`), so one project/operation does not spam another.

## Where It Runs

- `bridge_worker` calls `lib.opportunity_scanner.scan_runtime_opportunities(...)` each cycle.
- Opportunities are persisted to disk and surfaced via a CLI inbox.

## Where It Writes (Storage)

All artifacts live under `~/.spark/opportunity_scanner/`:
- `self_opportunities.jsonl`: emitted self-opportunities
- `decisions.jsonl`: accept/dismiss decisions (inbox actions)
- `outcomes.jsonl`: (optional) outcome attribution signals
- `promoted_opportunities.jsonl`: promotion candidates

## Record Shape (Self Opportunities)

Each row includes fields like:
- identifiers: `opportunity_id`, `trace_id`, `session_id`, `ts`
- scope: `scope_type`, `scope_id`, `project_id`, `project_label`, `operation`
- content: `category`, `priority`, `confidence`, `question`, `next_step`, `rationale`
- provenance: `source` (`heuristic|llm`), `llm_provider` (when `source=llm`)

## Inbox Workflow (How You Use It)

List recent opportunities:
```bash
python -m spark.cli opportunities list --limit 20
```

Accept one (records the decision and generates a concrete task file):
```bash
python -m spark.cli opportunities accept <id-prefix> --note "why we accept this"
```

Dismiss one (reduces repeats for dismissed question keys for a TTL window):
```bash
python -m spark.cli opportunities dismiss <id-prefix> --note "why we dismiss this"
```

Accepted tasks are written to:
- `docs/opportunities/accepted/`

## Definition Of Done

An accepted opportunity is done when:
- you made a concrete change
- you added verification (test/command/manual check)
- you defined rollback/fallback if it regresses
- you promoted the reusable learning (chip/playbook/rule) when appropriate

