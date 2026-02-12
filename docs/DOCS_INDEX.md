# Documentation Index

This index is the canonical map of active Spark documentation.
Primary navigation hub: `docs/GLOSSARY.md`.

## Start Here

- `README.md`: project entry point
- `docs/QUICKSTART.md`: setup and daily operations
- `Intelligence_Flow.md`: runtime flow, data stores, tuneables
- `Intelligence_Flow_Map.md`: high-level system map

## Integrations

- `docs/OPENCLAW_OPERATIONS.md`: **Start here** — session startup, how Spark works in OpenClaw, services, troubleshooting
- `docs/OPENCLAW_INTEGRATION.md`: Technical integration details (capture, context sync, notifications)
- `docs/LLM_INTEGRATION.md`: Claude CLI LLM integration (advisory synthesis, EIDOS distillation, PowerShell bridge)

## Operator Runbooks

- `TUNEABLES.md`: tuneable parameters and thresholds
- `docs/SPARK_LIGHTWEIGHT_OPERATING_MODE.md`: lightweight optimization policy (why, KPI gate, delete-pass rules, docs integration checklist)
- `docs/RETRIEVAL_LEVELS.md`: 3-level memory retrieval operating model (local-free, balanced, quality-max) + auto-router controls
- `docs/OPENCLAW_RESEARCH_AND_UPDATES.md`: experiment log for OpenClaw tuning changes, outcomes, and keep/rollback decisions
- `docs/reports/2026-02-12_openclaw_memory_advisory_concrete_plan_and_live_baseline.md`: concrete memory/advisory fix plan + live baseline + execution updates
- `docs/reports/2026-02-12_spark_intelligence_2day_comprehensive_honest_assessment.md`: two-day system scorecard and integrated closure plan
- `docs/adapters.md`: event adapters and schema boundaries
- `docs/claude_code.md`: Claude Code integration
- `docs/cursor.md`: Cursor and VS Code integration
- `docs/CHIPS.md`: chips usage and authoring
- `docs/CHIP_WORKFLOW.md`: fast chip creation workflow
- `STUCK_STATE_PLAYBOOK.md`: recovery playbook

## Core Systems

- `EIDOS_GUIDE.md`: EIDOS architecture and enforcement loop
- `EIDOS_QUICKSTART.md`: EIDOS operational quickstart
- `META_RALPH.md`: quality gate and feedback loop
- `SEMANTIC_ADVISOR_DESIGN.md`: semantic retrieval and advisor behavior
- `docs/PROJECT_INTELLIGENCE.md`: project-level learning loop
- `docs/architecture/PREDICTION_OUTCOME_LOOP.md`: prediction/outcome architecture, data contract, and integration plumbing

## Current Program Docs

- `docs/PROGRAM_STATUS.md`: consolidated implementation status and priorities
- `docs/memory-retrieval-status.md`: memory retrieval stabilization + A/B execution spec
- `docs/reports/2026-02-12_memory_retrieval_tuned_two_system_scorecard.md`: tuned best-vs-best comparison (`embeddings_only` vs `hybrid_agentic`)
- `PRODUCTION_READINESS.md`: production-hardening status and open blockers
- `docs/VISION.md`: long-range architecture vision
- `CHANGELOG.md`: chronological change log

## Important Strategic Docs Kept Active

- `MoE_Plan.md`
- `Path to AGI.md`
- `EVOLUTION_CHIPS_RESEARCH.md`
- `path-to-AGI/index.md` (living glossary/reports/experiments corpus)

## Archived and Historical

- `docs/archive/`: superseded plans, roadmaps, and one-off deep dives
- `docs/reports/`: point-in-time audits and analysis reports

Archive convention:
- Keep active docs focused on current runtime behavior.
- Move stale plans, snapshots, and superseded design proposals to archive.
