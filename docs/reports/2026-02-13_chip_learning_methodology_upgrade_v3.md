# Chip Learning Methodology Upgrade v3 (Schema/Routing/Distillation)

Date: 2026-02-13

## Why We Changed This

Primary issue: chip learning stream was dominated by telemetry-like rows, which diluted advisory quality and created low-signal distillation.

Goal for this pass: make chip learning explicitly evidence-first and schema-bound so only actionable rows survive into cognitive learning.

## What Was Implemented

### 1. Observer Learning Schema Enforcement (runtime)

File: `lib/chips/runtime.py`

- Added canonical learning payload generation at capture time:
  - `decision`
  - `rationale`
  - `evidence`
  - `expected_outcome`
- Added payload validity checks and telemetry-field filtering.
- Added runtime gate requirement (enabled by default):
  - `SPARK_CHIP_REQUIRE_LEARNING_SCHEMA=true`
- Added minimum evidence control:
  - `SPARK_CHIP_MIN_LEARNING_EVIDENCE` (default `1`)

Result: observer rows without meaningful schema/evidence are dropped before storage/merge impact.

### 2. Distillation Priority Shift (merger)

File: `lib/chip_merger.py`

- Distillation now prefers `captured_data.learning_payload` when valid.
- Payload evidence is filtered to exclude telemetry keys/signals.
- Raw-content and field-based distillation remain as fallback paths.

Result: stronger alignment between captured observer evidence and final distilled learning statements.

### 3. Diagnostics Upgrade (schema visibility)

File: `scripts/run_chip_learning_diagnostics.py`

Added global/per-chip metrics:
- `schema_payload_rate`
- `schema_statement_rate`

Result: we can now quantify whether chips are producing schema-usable rows, not just any row.

### 4. Test Coverage Added

Files:
- `tests/test_chips_runtime_filters.py`
- `tests/test_chip_merger.py`

New assertions cover:
- runtime schema payload creation
- runtime gate rejection when schema is missing/invalid
- merger preference for schema payload distillation

## Routing and Signal Discipline

Routing behavior remains chip-relevance-first, but this pass effectively hardens routing quality by suppressing low-value observer emissions at runtime gate time.

Practical outcome:
- route may still match, but row is discarded unless schema/evidence quality is present.

## Operational Verification

Run:

```powershell
python -m pytest -q tests/test_chips_runtime_filters.py tests/test_chip_merger.py tests/test_run_chip_learning_diagnostics.py tests/test_advisory_memory_fusion.py tests/test_advisor_retrieval_routing.py
python scripts/run_chip_learning_diagnostics.py --out-prefix chip_learning_diagnostics_schema_v3
```

Interpretation focus:
- `schema_payload_rate` should rise on fresh rows
- `schema_statement_rate` should rise on fresh rows
- telemetry and telemetry-observer rates should continue down as old rows age out

## Keep/Kill Guidance After This Pass

Keep:
- `social-convo`
- `x_social`
- `engagement-pulse`

Kill or block at runtime if still noisy after fresh-window validation:
- any chip with high telemetry/noise and near-zero schema statement yield.

## Decision Rule

A chip should stay active only if it contributes to actionable, schema-valid learning that improves advisory outcomes.
