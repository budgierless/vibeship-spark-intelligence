# Spark Improvement Plans (KISS Index)

Purpose: one lightweight, connected view of all improvement plans and where each
idea lives. This is the "index" that ties the docs together and keeps us in the
light-to-medium zone (KISS).

## Doc Map (Source of Truth)

- docs/IMPLEMENTATION_ROADMAP.md - execution status and phases.
- docs/INTEGRATION-PLAN.md - skills/advisor/orchestration loop plan.
- docs/SPARK_GAPS_AND_SOLUTIONS.md - full gap analysis and long-range vision.
- docs/VIBE_CODING_INTELLIGENCE_ROADMAP.md - day-to-day vibe-coding priorities.

## KISS Principles (Light-Medium Only)

- Prefer filtering and surfacing over new subsystems.
- Ship small changes that are observable in SPARK_CONTEXT.md.
- No new servers or heavy dependencies.
- Degrade gracefully when any subsystem is off.
- If we cannot measure it, we avoid it.

## Improvement Plans (Grouped by Weight)

### Light (Config / Selection / Docs)

Goal: improve what we surface without adding new moving parts.

| Item | Status | Notes | File Focus |
|---|---|---|---|
| Context selection upgrades (actionable insights) | DONE | Actionability boost + low-value filter | `lib/context_sync.py` |
| High-validation override | DONE | High-validated insights can surface despite lower reliability | `lib/context_sync.py` |
| Self-awareness boost | DONE | SELF_AWARENESS weighted higher | `lib/context_sync.py` |
| "Warnings" section in SPARK_CONTEXT.md | DONE | Warnings block added with top failure fixes | `lib/bridge.py` |
| Documentation clarity | DONE | Workers + watchdog documented | `docs/QUICKSTART.md`, `README.md` |

### Medium (Small Code, Big Impact)

Goal: fix the quality loop with minimal code additions.

| Item | Status | Notes | File Focus |
|---|---|---|---|
| Dedupe "struggle" variants | DONE | Recovered % variants merged on load | `lib/cognitive_learner.py` |
| Reliability backfill | DONE | Missing confidence/validation fields coerced on load | `lib/cognitive_learner.py` |
| Context diagnostics | NOT BUILT | No include/exclude reason output | `spark/cli.py` |
| Bridge status robustness | DONE | Handles dict vs object shapes | `lib/bridge.py` |

### Heavy (Deferred)

Goal: keep these in view without building them now.

- Full prediction -> outcome validation loop (Phase 6)
- Active learning questions and goal inference
- Team/shared memory + knowledge graph

## Mapping to Existing Plans

| Improvement | Primary Doc | Secondary Doc |
|---|---|---|
| Context selection upgrades | docs/IMPLEMENTATION_ROADMAP.md | docs/SPARK_GAPS_AND_SOLUTIONS.md |
| High-validation override | docs/VIBE_CODING_INTELLIGENCE_ROADMAP.md | docs/SPARK_GAPS_AND_SOLUTIONS.md |
| Warnings section | docs/INTEGRATION-PLAN.md | docs/IMPLEMENTATION_ROADMAP.md |
| Dedupe + reliability backfill | docs/SPARK_GAPS_AND_SOLUTIONS.md | docs/IMPLEMENTATION_ROADMAP.md |
| Validation loop expansion | docs/IMPLEMENTATION_ROADMAP.md | docs/VIBE_CODING_INTELLIGENCE_ROADMAP.md |

## KISS Acceptance Criteria

- Each change is a small, testable patch.
- SPARK_CONTEXT.md becomes more actionable within one session.
- No new daemons or external services required.
- Measurable impact: fewer repeats, fewer tool failures, better adherence.
