# Experiment: Phase 1 — Preflight Similarity Gate (spark-forge)
Date: 2026-02-11
Owner: Spark

## Hypothesis
If each run explicitly retrieves similar prior failures/successes before generation and converts top failure patterns into hard constraints, repeated failure signatures should decrease.

## Constraints
- No breaking changes to existing forge pipeline output.
- Keep phase-1 implementation non-blocking and lightweight.
- Preserve current generation/scoring/follow-up flow.

## Change
- Added preflight stage in `spark-forge/src/spark_forge/pipeline.py`.
- Retrieves prior advice via `retrieve_forge_advice(...)`.
- Structures preflight output into:
  - similar_failures
  - similar_successes
  - imported_risks
  - approach_choice
  - rejected_approaches
- Injects imported risks into generation constraints:
  - `Avoid known failure pattern: ...`
- Exposes `preflight` block in final pipeline report.
- Adds `preflight_summary` inside `learning_loop` diagnostics.

## Validation plan
- Real-use scenario:
  - Run repeated task-family batches in spark-forge and compare recurrence patterns.
- Synthetic checks:
  - `python -m py_compile src/spark_forge/pipeline.py src/spark_forge/config.py`
- Success metrics:
  - Recurrence count for same failure signature decreases.
  - First-pass score stability improves on repeated domains.

## Result
- Outcome: Implemented and pushed (`spark-forge` commit `3e158eb`).
- Metrics delta: pending real-run batch comparison.

## Decision
- Keep / iterate

## Notes
This is a phase-1 gate scaffold. Next step is stricter decision-contract enforcement tied to explicit causal checkpoints.
