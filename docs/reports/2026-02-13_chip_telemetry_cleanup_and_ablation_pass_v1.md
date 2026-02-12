# Chip Telemetry Cleanup + Ablation Pass v1

## What Changed

Implemented three upgrades focused on honest chip contribution measurement:

1. Telemetry-chip blocking in advisory path
- Blocked telemetry-heavy chips (`spark-core`, `bench_core`) from advisory retrieval.
- Added telemetry marker filtering (`post_tool`, `pre_tool`, `event_type:`, `file_path:`, etc.).

2. Intent-aware chip filtering in memory fusion
- Chip evidence retrieval now uses intent-aware/domain-aware gating.
- Added hard suppression for telemetry-like chip rows and cross-domain weak matches.
- Added env kill switch: `SPARK_ADVISORY_DISABLE_CHIPS=1`.

3. True chip ablation KPIs in benchmark runner
- `scripts/run_advisory_chip_experiments.py` now supports:
  - randomized order (`--random-seed`)
  - random subset sampling (`--sample-ratio`)
  - chips-disabled ablation (`--chip-ablation`)
- Reports now include:
  - `ablation_objective`
  - `chip_lift_objective`
  - `chip_lift_high_value_rate`
  - `chip_lift_harmful_emit_rate`

## Validation

Tests:
- `python -m pytest -q tests/test_advisor_retrieval_routing.py tests/test_advisory_memory_fusion.py tests/test_run_advisory_chip_experiments.py tests/test_run_advisory_realism_domain_matrix.py`
- Result: `29 passed`

## Benchmark Snapshot (bounded randomized run)

Command:

```bash
python scripts/run_advisory_chip_experiments.py \
  --plan benchmarks/data/advisory_chip_experiment_plan_v1.json \
  --profiles baseline \
  --experiments A_chip_off_global,C_chip_targeted_business_social \
  --repeats 1 \
  --no-force-live \
  --random-seed 20260213 \
  --sample-ratio 0.35 \
  --chip-ablation \
  --out-prefix advisory_chip_experiments_v3_ablation_random
```

Output:
- `benchmarks/out/advisory_chip_experiments_v3_ablation_random_report.json`
- `benchmarks/out/advisory_chip_experiments_v3_ablation_random_report.md`

Result:
- `A_chip_off_global`: objective `0.6397`, ablation `0.6397`, chip lift `+0.0000`
- `C_chip_targeted_business_social`: objective `0.6142`, ablation `0.6142`, chip lift `+0.0000`
- `chip_advice_hit_case_rate`: `0.00%`
- `chip_evidence_case_rate`: `0.00%`

## Honest Assessment

- The cleanup successfully removed telemetry noise from chips.
- Current chip corpus does not yet contain enough advisory-grade/actionable content to survive the stricter filters.
- Net: chips currently add no measurable value in advisory outcomes under honest ablation (`chip_lift=0`).

## Next Required Step (not optional)

Upgrade chip generation quality, not chip retrieval tuneables:

1. Distill chip outputs into actionable guidance format.
2. Suppress raw event-log style entries at write-time.
3. Require outcome-linked confidence calibration for chip rows.
4. Re-run randomized ablation matrix and only promote chip configs when `chip_lift_objective > 0`.
