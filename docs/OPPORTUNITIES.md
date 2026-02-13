# Opportunity Scanner Methodology

Spark's Opportunity Scanner generates self-improvement opportunities while you work.
The goal is not to "log ideas", but to convert them into verified improvements.

## Scopes

Each self-opportunity can be tagged and later filtered by scope:

- `project`: applies to the current repo/task
- `operation`: applies to a reusable mode of work (e.g. marketing, cinematic, vibe_coding)
- `spark_global`: improves Spark itself across all work

By default, opportunities are scoped as `project` when a project id can be inferred.

## Tagging (How To Control Scope)

Add explicit tags in your prompt or edit text:

- `scope:project`
- `scope:operation op:marketing`
- `scope:global`

Operation names should be lowercase with `a-z0-9_-`, for example:

- `op:vibe_coding`
- `op:cinematic_creation`
- `op:marketing`

## Cadence

Spark runs:

- a cheap heuristic scan every bridge cycle
- an LLM deep scan (MiniMax) at most once per cooldown window (recommended: 15 minutes)

The deep scan cooldown is keyed by scope (so work in one project or operation doesn't spam other contexts).

## Using Opportunities (Inbox Workflow)

1. List opportunities:

```bash
python -m spark.cli opportunities list --limit 20
```

2. Accept one (creates a task file in `docs/opportunities/accepted/` and records the decision):

```bash
python -m spark.cli opportunities accept <id-prefix> --note "why we accept this"
```

3. Dismiss one (reduces repeats for dismissed questions for a TTL window):

```bash
python -m spark.cli opportunities dismiss <id-prefix> --note "why we dismiss this"
```

## Definition Of Done

An opportunity is "done" when:

- a concrete change was made, and
- a measurable verification step exists (test/command/manual check), and
- a rollback path exists if it regresses, and
- the reusable learning is promoted (chip/playbook/rule) when appropriate.

