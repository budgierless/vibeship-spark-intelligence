# Experiment: Phase 1c — Strategy Pivot Trigger on Repeated Unsupported Decisions
Date: 2026-02-11
Owner: Spark

## Hypothesis
If unsupported decisions repeat, forcing a strategy pivot in the next run should reduce looped failure patterns.

## Change
- Added `_get_strategy_pivot(previous_report)` in `spark_forge/pipeline.py`.
- Trigger condition: `unsupported >= 2` in previous run decision evaluation summary.
- On trigger, inject hard constraints requiring an alternative approach class.
- Surface pivot activation in preflight diagnostics (`strategy_pivot_active`).

## Validation
- Compile check passed (`py_compile pipeline.py`).
- Real-use metric pending: recurrence rate after pivot vs before pivot.

## Result
- Shipped in `spark-forge` commit `54f61a2`.

## Decision
- Keep and monitor.
