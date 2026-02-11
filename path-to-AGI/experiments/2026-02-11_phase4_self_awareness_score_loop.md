# Experiment: Phase 4 — Adversarial Strategy Selection + Self-Awareness Score
Date: 2026-02-11
Owner: Spark

## Hypothesis
If each run explicitly considers 3 approaches, predicts likely failure adversarially, and chooses the hardest-to-trigger failure mode, then failures become more anticipated over time.

## Change
- Updated `spark-forge/src/spark_forge/pipeline.py`:
  - Added pre-execution strategy selector:
    - generates 3 plausible approaches
    - assigns adversarial failure mode per approach
    - selects approach with highest failure trigger difficulty
  - Added self-awareness tracking:
    - compares predicted failure mode vs observed follow-up failure patterns
    - tracks predicted vs unpredicted failures over time
    - persists metrics in `~/.spark/forge_self_awareness.json`
  - Added report fields:
    - `strategy_selection`
    - `self_awareness`

## Validation
- `py_compile` passed for updated pipeline module.

## Result
- Shipped in `spark-forge` commit `11f9718`.

## Decision
- Keep and monitor self-awareness score trend across batches.
