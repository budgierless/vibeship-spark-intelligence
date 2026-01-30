# Spark Plus (Docker-only) Architecture

Status: documentation only. No implementation has started.

## Purpose
Spark Plus is the self-hosted, Docker-only stack for heavier connectors,
evaluation, and replay workflows. It extends Spark core without bloating it.

## Goals
- Docker-only deployment (local or on a server).
- Isolate heavy connectors and data stores from Spark core.
- Provide replay and evaluation tooling for chips.
- Keep data local and user-controlled.

## Non-goals
- No hosted SaaS.
- No mandatory external cloud services.
- No changes to Spark core behavior unless explicitly enabled.

## Components (proposed)
1) Connectors
- MCP adapters (VibeShip + other MCP profiles).
- Repo/CI/deploy/observability/product/support/design connectors.

2) Event router
- Normalizes all inputs to SparkEventV1.
- Enforces schema validation before write.

3) Storage
- Event log (JSONL or SQLite).
- Optional vector store (local).

4) Evaluation and replay
- Replays event logs through chips.
- Produces evaluation reports per chip.

5) Dashboard (optional)
- Surface health, throughput, and evaluation results.

## Integration with Spark core
- Spark core consumes SparkEventV1 events produced by Spark Plus.
- Chips runtime lives in the `vibeship-spark-chips` repo.
- Spark Plus can run chips offline for evaluation and replay.

## Data flow (concept)
Connectors -> Event Router -> Event Log -> Chip Replay/Eval -> Reports
                     \-> (optional) Sync to Spark core queue

## Security and privacy
- All data stored locally by default.
- Explicit opt-in per connector scope.
- Clear audit logs for data access.

## Assessment plan (before implementation)
This is the checklist we will run to understand the system and risks.

1) Connector audit
- List candidate MCPs and non-MCP sources.
- Identify auth requirements and data scopes.

2) Data volume and throughput
- Measure expected event volume per connector.
- Define retention and compression strategy.

3) Schema and validation
- Confirm SparkEventV1 compliance for all sources.
- Define required fields for replay and evaluation.

4) Evaluation targets
- Decide which chips must show ROI in v1.
- Define metrics: precision, recall, outcome coverage.

5) Operational constraints
- Docker compose layout, volumes, and port allocations.
- Resource ceilings for local machines.

## Open questions
- Which connectors are first priority for Spark Plus?
- Preferred storage format: JSONL, SQLite, or both?
- What is the evaluation report format and destination?
- Should Spark Plus push events into Spark core automatically or on demand?
