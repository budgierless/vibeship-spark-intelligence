# Chip R3 Runtime Rollout v1

Date: 2026-02-13
Scope: apply promoted chip runtime profile (`R3`) to live Spark startup/runtime and verify with post-change benchmarks.

## What Changed

1. Runtime startup defaults now include promoted chip profile gates:
- `SPARK_CHIP_REQUIRE_LEARNING_SCHEMA=1`
- `SPARK_CHIP_OBSERVER_ONLY=1`
- `SPARK_CHIP_MIN_LEARNING_EVIDENCE=2`
- `SPARK_CHIP_MIN_CONFIDENCE=0.65`
- `SPARK_CHIP_MIN_SCORE=0.25`
- `SPARK_CHIP_MERGE_MIN_CONFIDENCE=0.65`
- `SPARK_CHIP_MERGE_MIN_QUALITY=0.62`

Files:
- `start_spark.bat`
- `scripts/start_openclaw_spark.ps1`

2. Bridge merge gate now supports env-controlled thresholds:
- `lib/bridge_cycle.py`

3. Added helper to apply R3 merge tuneables to user config:
- `scripts/apply_chip_profile_r3.py`
- writes to `~/.spark/tuneables.json` (`chip_merge.*`)

4. Fixed benchmark reproducibility issue:
- `scripts/run_chip_schema_experiments.py` replaced process-randomized `hash()` seeding with stable hash-based seeding.
- `tests/test_run_chip_schema_experiments.py` includes deterministic seed test.

## Live Apply + Runtime State

Applied:
- `python scripts/apply_chip_profile_r3.py`

Services restarted with R3 env:
- `sparkd`, `bridge_worker`, `openclaw_tailer`
- `sparkd /health = ok`

## Validation

Tests:
- `python -m pytest -q tests/test_apply_chip_profile_r3.py tests/test_run_chip_schema_experiments.py tests/test_run_chip_schema_multiseed.py tests/test_run_chip_observer_policy.py tests/test_chips_runtime_filters.py tests/test_chip_merger.py tests/test_run_chip_learning_diagnostics.py tests/test_compact_chip_insights.py`
- Result: `29 passed`

## Post-Rollout Metrics

Diagnostics:
- `chip_learning_diagnostics_active_observer_v7`: `rows=513`, `merge_eligible=2`, `telemetry_rate=97.86%`
- `chip_learning_diagnostics_active_observer_r3_v1` (R3-aligned thresholds): `rows=513`, `merge_eligible=5`

Observer policy refresh:
- `chip_observer_policy_v4` applied.
- Disabled observers remain focused on noisy telemetry-heavy paths:
  - `engagement-pulse/chip_level`
  - `engagement-pulse/unknown`
  - `social-convo/chip_level`
  - `x-social/chip_level`

Schema multiseed (stable-seed runner):
- `chip_schema_merge_activation_multiseed_v4`
- Leader: `R3_two_evidence_relaxed_merge`
- Promotion pass (`R3` vs `R0`): `100%`
- Aggregated:
  - `R3`: objective mean `0.9286`, coverage `100%`, merge-eligible mean `0.6429`
  - `R2`: objective mean `0.9266`, coverage `100%`, merge-eligible mean `0.6329`

## Honest Assessment

1. Rollout is technically successful: runtime profile and tuneables are now aligned with promoted benchmark profile.
2. Benchmark confidence is higher after stable-seed fix; prior run-to-run winner drift was partly benchmark-seeding noise.
3. Telemetry share in historical windows is still high; observer policy is still required as hard guardrail.
4. `R3` is currently the preferred profile, with `R2` a close fallback.

