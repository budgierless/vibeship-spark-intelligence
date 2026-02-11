# Experiment: Phase 1b — Decision Contract + Causal Follow-up (spark-forge)
Date: 2026-02-11
Owner: Spark

## Hypothesis
If each run logs explicit decisions with expected effects and disconfirming signals, follow-up analysis can evaluate whether decisions were supported or unsupported, improving attribution quality.

## Change
- Added decision-contract construction in `spark_forge/pipeline.py` from preflight output.
- Added `decision_contract` to pipeline report output.
- Extended follow-up prompt to evaluate decision contract causally.
- Added `decision_evaluation` structured output (`supported|unsupported|unclear`).
- Added `decision_evaluation_summary` to learning-loop report.

## Validation plan
- Compile checks: `py_compile` on modified files.
- Real-use: compare unsupported-decision recurrence over repeated runs.

## Result
- Shipped in `spark-forge` commit `592d634`.
- Immediate metrics pending benchmark batch.

## Decision
- Keep and iterate: next step is hard enforcement/reroute when unsupported decisions repeat.
