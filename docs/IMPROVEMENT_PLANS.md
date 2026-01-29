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

1) Context selection upgrades (focus on actionable insights)
   - Prefer insights with "Fix:", "Do:", "Avoid:", or explicit instructions.
   - Downrank or exclude "Heavy X usage" signals in context outputs.
   - File focus: `lib/context_sync.py`

2) High-validation override
   - Surface insights with very high validation counts even if reliability < threshold.
   - File focus: `lib/context_sync.py`

3) Self-awareness boost
   - Prefer SELF_AWARENESS patterns that reduce tool failures (path, timeout, syntax).
   - File focus: `lib/context_sync.py`

4) "Warnings" section in SPARK_CONTEXT.md
   - Show top 3 failure patterns with short fixes.
   - File focus: `lib/bridge.py` or `lib/context_sync.py`

5) Documentation clarity
   - State which workers must be running and how to start them.
   - Link to `start_spark.bat` and `spark status` for checks.
   - File focus: `docs/QUICKSTART.md`, `README.md`

### Medium (Small Code, Big Impact)

Goal: fix the quality loop with minimal code additions.

1) Dedupe "struggle" variants
   - Normalize "recovered X%" variants into a single insight.
   - File focus: `lib/cognitive_learner.py`

2) Reliability backfill
   - If reliability is missing in stored insights, compute on load.
   - File focus: `lib/cognitive_learner.py`

3) Context diagnostics
   - Expose why an insight was included or excluded (short summary).
   - File focus: `spark/cli.py` or `lib/context_sync.py`

4) Bridge status robustness
   - Ensure status reporting handles dict vs object shapes safely.
   - File focus: `lib/bridge.py`

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
