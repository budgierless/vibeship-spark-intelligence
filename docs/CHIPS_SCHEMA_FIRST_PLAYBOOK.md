# Chips Schema-First Playbook

Date: 2026-02-13
Navigation hub: `docs/GLOSSARY.md`

## Why This Exists

Chips now perform best as **evidence infrastructure**:
- capture domain signals,
- convert signals into schema-valid payloads,
- feed distillation/memory,
- improve advisory quality indirectly.

This playbook defines how chips should be authored and evaluated so they match that role.

Spark OSS default keeps chip runtime disabled. Set `SPARK_CHIPS_ENABLED=1`
before using these runbooks in premium environments.

## Core Position

Chips are not primarily free-form advice generators.

Chips are:
1. signal extractors
2. evidence normalizers
3. distillation inputs

Target flow:
`chips -> schema payload -> distilled learning -> memory retrieval -> advisory decision`

## Schema-First Principles

1. Evidence-first over text-first.
2. Observer contracts over implicit behavior.
3. Field-level quality over aggregate confidence only.
4. Coverage + quality together (no low-volume gaming).
5. Telemetry separation (operational telemetry never treated as learning evidence).
6. Freshness and contradiction awareness in learning promotion.

## Observer Contract (Recommended v2)

Each observer should define a contract block:

```yaml
observer_contract:
  schema_version: v2
  type: signal_observer
  min_evidence_items: 2
  required_semantic_fields: [topic, outcome_type]
  outcome_fields: [likes, replies]
  forbidden_telemetry_fields: [tool_name, cwd, event_type, file_path]
  evidence_priority_order: [topic, outcome_type, likes, replies]
  decision_template: "Prefer {pattern} for {topic} when {outcome_type}."
  rationale_template: "Because {evidence_summary}."
  expected_outcome_template: "Increase {target_metric}."
```

Contract intent:
- make schema validity predictable,
- make merge quality auditable,
- reduce fallback/chip-level noise.

## Observer Types

Use explicit observer classes in chip design:

1. `signal_observer`
- eligible for schema payloads and merge.
- must produce semantic evidence.

2. `session_observer`
- summarizes activity, lower priority.
- not a primary source for durable learnings.

3. `telemetry_observer`
- operational only.
- never eligible for learning merge.

## Chip Authoring Rules

1. Avoid broad triggers without context:
- avoid plain `"tweet"` or `"reply"` alone.
- require event+tool+pattern overlap where possible.

2. Prefer extractable required fields:
- required fields must be observable from real event payloads.
- avoid required fields that rely on manual interpretation only.

3. Keep optional fields meaningful:
- prioritize domain semantics (`topic`, `outcome_type`, `trend_category`) over metadata.

4. Include extraction rules for required fields:
- keyword extraction and regex extraction should exist for each critical field.

5. Define evidence priority:
- specify which fields matter most for schema payloads.

## Runtime and Merge Alignment

Runtime should enforce:
- schema requirement gate on by default,
- minimum evidence item count,
- telemetry field suppression.

Merge should enforce:
- payload-based distillation priority,
- quality thresholds,
- duplicate/low-quality cooldown,
- observer-level diagnostics.

## Evaluation Standard

Chip changes should be evaluated on both:

1. Capture coverage:
- `insights_emitted / events_requested`

2. Quality:
- `schema_payload_rate`
- `schema_statement_rate`
- `merge_eligible_rate`
- downstream advisory quality impact

Promotion rule:
- do not promote stricter profiles if quality rises but coverage collapses.

## Benchmarking Pattern

Use A/B/C/D schema experiments from:
- `scripts/run_chip_schema_experiments.py`
- `scripts/run_chip_schema_multiseed.py` (for robust random-seed validation)
- `benchmarks/data/chip_schema_experiment_plan_v1.json`

Keep objective coverage-weighted to prevent over-strict low-volume winners.

Promotion gate (required):
- candidate `B` must beat baseline `A` on both:
  - objective
  - capture coverage

Example:

```bash
python scripts/run_chip_schema_experiments.py \
  --plan benchmarks/data/chip_schema_experiment_plan_v1.json \
  --chips spark-core,marketing,game-dev \
  --events-per-chip 24 \
  --promotion-baseline-id A_schema_baseline \
  --promotion-candidate-id B_schema_evidence2 \
  --min-candidate-non-telemetry 0.95 \
  --min-candidate-schema-statement 0.90 \
  --min-candidate-merge-eligible 0.05 \
  --out-prefix chip_schema_experiments_latest
```

Mode variation matrix:
- `benchmarks/data/chip_schema_mode_variations_v1.json`
- `benchmarks/data/chip_schema_merge_activation_plan_v1.json` (merge-activation pass)

Example:

```bash
python scripts/run_chip_schema_experiments.py \
  --plan benchmarks/data/chip_schema_mode_variations_v1.json \
  --chips spark-core,marketing,game-dev \
  --events-per-chip 24 \
  --promotion-baseline-id M0_baseline_schema_safe \
  --promotion-candidate-id M1_two_evidence_balanced \
  --out-prefix chip_schema_mode_variations_latest
```

Merge-activation pass (recommended after trigger tightening):

```bash
python scripts/run_chip_schema_experiments.py \
  --plan benchmarks/data/chip_schema_merge_activation_plan_v1.json \
  --chips spark-core,marketing,game-dev \
  --events-per-chip 24 \
  --promotion-baseline-id R0_baseline_safe \
  --promotion-candidate-id R3_two_evidence_relaxed_merge \
  --min-candidate-non-telemetry 0.95 \
  --min-candidate-schema-statement 0.90 \
  --min-candidate-merge-eligible 0.05 \
  --out-prefix chip_schema_merge_activation_latest
```

Multi-seed robustness pass (recommended before promotion):

```bash
python scripts/run_chip_schema_multiseed.py \
  --plan benchmarks/data/chip_schema_mode_variations_v1.json \
  --chips spark-core,marketing,game-dev \
  --events-per-chip 24 \
  --seed-start 20260213 \
  --seed-count 7 \
  --promotion-baseline-id M0_baseline_schema_safe \
  --promotion-candidate-id M1_two_evidence_balanced \
  --min-candidate-non-telemetry 0.95 \
  --min-candidate-schema-statement 0.90 \
  --min-candidate-merge-eligible 0.05 \
  --out-prefix chip_schema_mode_variations_multiseed_latest
```

Deterministic verification (required after benchmark runner changes):

1. Run the same command twice with different output prefixes.
2. Compare reports while ignoring `generated_at`.
3. Promote only if both runs match on leader and aggregate metrics.

## Operational Diagnostics

Use fresh, active-chip windows:

```bash
python scripts/run_chip_learning_diagnostics.py \
  --limit-per-chip 400 \
  --active-only \
  --project-path "<REPO_ROOT>" \
  --max-age-days 14 \
  --observer-limit 20 \
  --out-prefix chip_learning_diagnostics_active_window
```

Use observer KPI table to:
- identify weak observers,
- prune low-yield observers,
- guide extraction upgrades.

Observer keep/disable policy (2-3 window trend):

```bash
python scripts/run_chip_observer_policy.py \
  --report-glob "benchmarks/out/chip_learning_diagnostics_active_observer_v*_report.json" \
  --windows 3 \
  --min-windows 2 \
  --min-rows-total 50 \
  --apply
```

Policy file:
- `~/.spark/chip_observer_policy.json`

After apply:
- restart `sparkd` and `bridge_worker` so runtime loads updated observer blocklist.

## Migration Plan

1. Promoted runtime profile (`R3` controlled rollout):
- `SPARK_CHIP_REQUIRE_LEARNING_SCHEMA=1`
- `SPARK_CHIP_OBSERVER_ONLY=1`
- `SPARK_CHIP_MIN_LEARNING_EVIDENCE=2`
- `SPARK_CHIP_MIN_CONFIDENCE=0.65`
- `SPARK_CHIP_MIN_SCORE=0.25`
- `SPARK_CHIP_MERGE_MIN_CONFIDENCE=0.65`
- `SPARK_CHIP_MERGE_MIN_QUALITY=0.62`
2. Merge tuneables for rollout window:
- `chip_merge.min_cognitive_value=0.25`
- `chip_merge.min_actionability=0.15`
- `chip_merge.min_transferability=0.15`
- `chip_merge.min_statement_len=20`
3. Apply tuneables helper:
- `python scripts/apply_chip_profile_r3.py`
4. Keep observer policy trend gate active and re-check every 24h.

## Current Lock (2026-02-13 Close)

- `R3_two_evidence_relaxed_merge` is primary runtime profile.
- `R2_relaxed_runtime_merge` is approved fallback profile.
- `R3` vs `R0` promotion gate pass rate remains `100%` in deterministic rechecks.
- `A_schema_baseline` remains winner in the base A/B/C/D plan.
- `M2_two_evidence_low_conf` remains winner in mode variations, while `M1` still fails promotion against `M0`.

## What Good Looks Like

A healthy chip system has:
- high signal observer rows,
- low chip-level fallback share,
- stable schema payload/statement rates,
- measurable advisory quality lift without noise inflation.


