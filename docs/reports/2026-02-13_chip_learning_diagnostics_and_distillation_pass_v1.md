# Chip Learning Diagnostics + Distillation Pass v1

## Objective

Improve chips on the indirect path:

`chips -> distillation/learning -> cognitive memory -> advisory quality`

instead of forcing direct chip advisory usage.

## What Was Implemented

### 1) Distillation-first chip merge

File: `lib/chip_merger.py`

- Added telemetry/operational suppression before merge:
  - chip blocklist: `spark-core`, `bench_core`, `bench-core`
  - markers: `post_tool`, `pre_tool`, `tool_name:`, `event_type:`, `command:`, etc.
- Added learning statement distillation:
  - distill from `content` when meaningful
  - fallback distillation from structured `captured_data.fields`
- Added learning-quality gates beyond total score:
  - `min_cognitive_value`
  - `min_actionability`
  - `min_transferability`
  - `min_statement_len`
- Merged insights now use distilled source tag:
  - `source="chip:<chip_id>:distilled"`
- Added distillation audit log:
  - `~/.spark/chip_learning_distillations.jsonl`
- Added richer merge stats:
  - `merged_distilled`
  - `skipped_non_learning`
  - `learning_distillation_count` in `get_merge_stats()`

### 2) Chip learning diagnostics runner

File: `scripts/run_chip_learning_diagnostics.py`

Outputs:
- `benchmarks/out/chip_learning_diagnostics_v1_report.json`
- `benchmarks/out/chip_learning_diagnostics_v1_report.md`

Metrics include:
- telemetry rate
- learning statement yield
- learning-quality pass rate
- merge-eligible candidate count
- per-chip breakdown and sample statements

## Validation

Tests:

```bash
python -m pytest -q \
  tests/test_chip_merger.py \
  tests/test_run_chip_learning_diagnostics.py \
  tests/test_chips_quality_integration.py \
  tests/test_advisor_retrieval_routing.py \
  tests/test_advisory_memory_fusion.py \
  tests/test_run_advisory_chip_experiments.py
```

Result: `39 passed`

## Diagnostics Snapshot

Run command:

```bash
python scripts/run_chip_learning_diagnostics.py \
  --limit-per-chip 400 \
  --out-prefix chip_learning_diagnostics_v1
```

Observed summary from `benchmarks/out/chip_learning_diagnostics_v1_report.json`:

- rows analyzed: `4715`
- merge-eligible candidates: `2`
- telemetry rate: `99.75%`
- statement yield: `5.98%`

Top learnable chip (current dataset):
- `social-convo`: `2` merge-eligible candidates

## Honest Assessment

1. The new merge path is now correctly filtering telemetry noise from entering cognitive memory.
2. Current chip corpus is still overwhelmingly operational/telemetry in practice.
3. Bottleneck is now explicit and measurable: chip generation quality, not advisory routing.
4. This is the right failure mode: better to reject non-learning chip rows than pollute cognitive memory.

## Next Required Upgrades

1. Improve chip runtime output templates so observers emit distilled, action-oriented statements by default.
2. Reduce raw tool-event observer outputs in chips (especially runtime metadata-heavy observers).
3. Add chip-domain writer constraints:
   - each insight must include rationale and expected use case
   - avoid commands/log snippets unless transformed into lessons
4. Re-run diagnostics and require:
   - telemetry rate down materially
   - merge-eligible count up materially
   - no adverse increase in advisory harmful/noise metrics.
