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
- `docs/SPARK_CARMACK_OPTIMIZATION_IMPLEMENTATION.md`: implemented Carmack optimization changes (core-only sync, advisory fallback policy, memory/chip noise controls)
- `docs/RETRIEVAL_LEVELS.md`: 3-level memory retrieval operating model (local-free, balanced, quality-max) + auto-router controls
- `docs/ADVISORY_BENCHMARK_SYSTEM.md`: advisory-quality benchmark design, scoring model, and iteration loop
- `docs/ADVISORY_REALISM_PLAYBOOK.md`: cross-system advisory realism loop (depth tiers, theory seeding, source-alignment gates)
- `scripts/run_advisory_realism_domain_matrix.py`: multi-domain advisory realism matrix runner (10+ domain slices per run)
- `scripts/run_advisory_chip_experiments.py`: chip strategy experiment runner (A/B/C/D off/on/targeted segment plans)
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
- `docs/reports/2026-02-12_advisory_tuning_delta.md`: advisory tuneables execution report + measured pre/post deltas
- `docs/reports/2026-02-12_advisory_realism_contract_decision.md`: locked primary/shadow advisory realism benchmark contract + gate outcomes
- `docs/reports/2026-02-12_advisory_realism_contract_run.md`: latest contract execution snapshot with primary/shadow metrics and delta
- `docs/reports/2026-02-12_advisory_multidomain_matrix_baseline.md`: multidomain advisory matrix baseline (11 domains, weighted metrics, gap order)
- `docs/reports/2026-02-12_advisory_multidomain_tuning_pass_v2.md`: multidomain tuning pass v2 with baseline/candidate deltas and residual gaps
- `docs/reports/2026-02-12_chips_advisory_memory_benchmark_plan.md`: chip utilization benchmark strategy, A/B plan, and promotion criteria
- `docs/reports/2026-02-13_chip_strategy_experiment_matrix_v2.md`: first full A/B/C/D chip strategy run with corrected advice-hit vs evidence-hit scoring
- `docs/reports/2026-02-13_chip_telemetry_cleanup_and_ablation_pass_v1.md`: telemetry cleanup + intent-gated chip retrieval + randomized ablation outcome snapshot
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
