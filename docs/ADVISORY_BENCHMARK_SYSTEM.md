# Advisory Benchmark System

## Purpose

Create a dedicated benchmark loop for advisory quality so Spark can improve:
- when advice appears,
- how actionable it is,
- how well it uses memory,
- and how consistently it stays trace-bound.

This benchmark is separate from Forge/Depth and focused only on
`retrieval -> advisory -> actionability`.

## Artifacts

- Runner: `benchmarks/advisory_quality_ab.py`
- Realism runner: `benchmarks/advisory_realism_bench.py`
- Seed scenarios: `benchmarks/data/advisory_quality_eval_seed.json`
- Extended scenarios: `benchmarks/data/advisory_quality_eval_extended.json`
- Realism scenarios: `benchmarks/data/advisory_realism_eval_v1.json`
- Multidomain realism scenarios: `benchmarks/data/advisory_realism_eval_multidomain_v1.json`
- Theory catalog: `benchmarks/data/advisory_theory_catalog_v1.json`
- Theory seeder: `benchmarks/seed_advisory_theories.py`
- Real-case template: `benchmarks/data/advisory_quality_eval_real_user_template.json`
- Log-to-cases generator: `benchmarks/build_advisory_cases_from_logs.py`
- Profile sweeper: `benchmarks/advisory_profile_sweeper.py`
- Contract runner: `scripts/run_advisory_realism_contract.py`
- Domain matrix runner: `scripts/run_advisory_realism_domain_matrix.py`
- Chip experiment runner: `scripts/run_advisory_chip_experiments.py`
- Chip plan: `benchmarks/data/advisory_chip_experiment_plan_v1.json`
- Chip profiles: `benchmarks/data/advisory_chip_profile_*.json`
- Output JSON: `benchmarks/out/advisory_quality_ab_report.json`
- Output Markdown: `benchmarks/out/advisory_quality_ab_report.md`

## Core Metrics

Per-case score uses weighted components:
- `emit_correct` (35%): did emit/no-emit match case expectation
- `expected_hit_rate` (20%): required signal fragments present
- `forbidden_clean_rate` (15%): noisy/irrelevant fragments absent
- `actionability` (10%): concrete next command/check present
- `trace_bound` (10%): decision event linked to the case trace
- `memory_utilized` (10%): memory sources actually contributed

Profile-level score:
- mean case score, then repetition penalty adjustment.

## Profile Comparison

Default benchmark profiles:
- `baseline`
- `balanced`
- `strict`

Each profile controls:
- `advisory_engine.*` cooldown policy
- `advisory_gate.*` suppression policy
- `advisor.max_items` / `advisor.min_rank_score` quality threshold

Run example:

```bash
python benchmarks/advisory_quality_ab.py \
  --cases benchmarks/data/advisory_quality_eval_seed.json \
  --profiles baseline,balanced,strict \
  --repeats 1 \
  --force-live
```

`--force-live` is important when comparing advisory quality itself, because
packet paths can mask live retrieval/gating behavior.

## No-Emit Optimization Loop

`advisory_quality_ab` now records no-emit reason histograms (`error_code`) per profile.
Use those as the primary tuning signal:

1. Run benchmark on candidate profiles.
2. Inspect `no_emit_error_codes` for each profile.
3. Tune based on dominant reason:
   - `AE_DUPLICATE_SUPPRESSED`: reduce repeat cooldown or improve text diversity.
   - `AE_GATE_SUPPRESSED`: adjust gate thresholds or increase relevance quality.
   - `AE_FALLBACK_RATE_LIMIT`: tune fallback guard policy.
4. Re-run benchmark and compare objective score + no-emit distribution shift.

## Auto Sweeper

Use bounded candidate search to choose winner profile without manual guesswork:

```bash
python benchmarks/advisory_profile_sweeper.py \
  --cases benchmarks/data/advisory_quality_eval_extended.json \
  --repeats 1 \
  --force-live \
  --max-candidates 12
```

The sweeper produces:
- ranked candidate report
- objective score per candidate
- winner profile JSON ready to apply/merge

## Realism Layer (Cross-System + Theories)

Use realism benchmark when the goal is production-grade advisory quality beyond coding-only tasks.

Run:

```bash
python benchmarks/advisory_realism_bench.py \
  --cases benchmarks/data/advisory_realism_eval_v1.json \
  --profiles baseline,balanced,strict \
  --repeats 1 \
  --force-live
```

Realism metrics add:
- `high_value_rate`: advice that is emitted, actionable, trace-bound, memory-backed, and source-aligned
- `harmful_emit_rate`: advice emitted when case expects suppression
- `unsolicited_emit_rate`: emitted on suppression cases even when no forbidden content leaks
- `critical_miss_rate`: missed emits on high/critical cases
- `source_alignment_rate`: expected source families (`semantic`, `mind`, `outcomes`, etc.) actually used
- `theory_discrimination_rate`: good theories surfaced correctly, bad theories suppressed
- depth/domain splits (`D1`/`D2`/`D3`, domain score averages)

## Operating Contract (Locked)

Active benchmark contract:
- Primary cases: `benchmarks/data/advisory_realism_eval_v2.json`
- Shadow cases: `benchmarks/data/advisory_realism_eval_v1.json`
- Contract file: `benchmarks/data/advisory_realism_operating_contract_v1.json`

Rationale:
- `v2` is the corrective-advisory contract for real-world anti-pattern prompts.
- `v1` remains a strict-suppress historical shadow set.

Execution policy:
1. Run primary (`v2`) and require all gates to pass.
2. Run shadow (`v1`) as non-blocking sanity telemetry.
3. If primary passes and shadow regresses, do not auto-rollback unless trace/source gates regress materially.

Single-command contract run:

```bash
python scripts/run_advisory_realism_contract.py
```

Optional timeout override per run:

```bash
python scripts/run_advisory_realism_contract.py --run-timeout-s 1200
```

Multi-domain matrix run (10+ domain benches in one pass):

```bash
python scripts/run_advisory_realism_domain_matrix.py \
  --cases benchmarks/data/advisory_realism_eval_multidomain_v1.json \
  --force-live \
  --save-domain-reports
```

Preview domains without executing benchmarks:

```bash
python scripts/run_advisory_realism_domain_matrix.py \
  --cases benchmarks/data/advisory_realism_eval_multidomain_v1.json \
  --dry-run
```

Profile overlays can now tune deeper advisor behavior in benchmark runs:
- Retrieval routing thresholds (unified schema for benchmark overlays + live tuneables): `retrieval.overrides.{semantic_context_min, semantic_lexical_min, semantic_strong_override, lexical_weight}`
- `chip_advice_limit`, `chip_advice_min_score`, `chip_advice_max_files`, `chip_advice_file_tail`
- `chip_source_boost`

Chip strategy matrix (A/B/C/D patterns: off, on, targeted segments):

```bash
python scripts/run_advisory_chip_experiments.py \
  --plan benchmarks/data/advisory_chip_experiment_plan_v1.json \
  --profiles baseline \
  --repeats 1 \
  --no-force-live \
  --chip-ablation \
  --random-seed 20260213 \
  --sample-ratio 0.5 \
  --out-prefix advisory_chip_experiments_v2
```

Chip matrix outputs:
- `benchmarks/out/advisory_chip_experiments_v2_report.json`
- `benchmarks/out/advisory_chip_experiments_v2_report.md`

Anti-gaming safeguards in chip runner:
- randomized case order (`--random-seed`)
- randomized subset stress runs (`--sample-ratio`)
- chips-disabled ablation pass (`--chip-ablation`)

Promotion rule:
- do not treat chip tuning as successful unless `chip_lift_objective > 0`
  and safety metrics (`harmful_emit_rate`, `critical_miss_rate`) do not regress.

## Chip Learning Diagnostics (Indirect Path)

Direct chip advisory hit-rate can stay low even when chips are helping through:
`chips -> distillation -> cognitive memory -> advisory quality`.

Run baseline diagnostics:

```bash
python scripts/run_chip_learning_diagnostics.py \
  --limit-per-chip 400 \
  --active-only \
  --project-path "<REPO_ROOT>" \
  --max-age-days 14 \
  --observer-limit 20 \
  --out-prefix chip_learning_diagnostics_v1
```

Run threshold sensitivity diagnostics to test tuneable bottlenecks:

```bash
python scripts/run_chip_learning_diagnostics.py \
  --limit-per-chip 400 \
  --min-total-score 0.45 \
  --min-cognitive-value 0.25 \
  --min-actionability 0.15 \
  --min-transferability 0.15 \
  --min-statement-len 20 \
  --out-prefix chip_learning_diagnostics_relaxed_v1
```

Compare:
- `merge_eligible`
- `statement_yield_rate`
- `learning_quality_pass_rate`
- `schema_payload_rate`
- `schema_statement_rate`
- `telemetry_observer_rate`
- `missing_confidence_rate`
- `missing_quality_rate`
- observer-level schema KPIs (`Observer KPIs` table)

If these barely move under relaxed gates, the blocker is chip content quality (telemetry/noise), not tuneable strictness.

## Schema Capture A/B/C/D Matrix

Use schema-focused experiment arms to choose the best observer runtime profile:

- `A_schema_baseline`
- `B_schema_evidence2`
- `C_schema_strict_runtime`
- `D_schema_strict_runtime_merge`

Plan file:
- `benchmarks/data/chip_schema_experiment_plan_v1.json`

Runner:

```bash
python scripts/run_chip_schema_experiments.py \
  --plan benchmarks/data/chip_schema_experiment_plan_v1.json \
  --chips social-convo,engagement-pulse,x_social \
  --events-per-chip 20 \
  --promotion-baseline-id A_schema_baseline \
  --promotion-candidate-id B_schema_evidence2 \
  --out-prefix chip_schema_experiments_v1
```

Promotion rule:
- Prefer the arm with highest objective only when it also improves:
  - `capture_coverage`
  - `schema_statement_rate`
  - `merge_eligible_rate`
  - `payload_valid_emission_rate`
- Reject any arm that regresses safety proxy (`telemetry_rate` increase).

Coverage note:
- The schema matrix objective includes `capture_coverage` (`insights_emitted / events_requested`) so over-strict, low-volume profiles cannot tie with stable profiles.

Randomized robustness pass (anti-overfit):

```bash
python scripts/run_chip_schema_multiseed.py \
  --plan benchmarks/data/chip_schema_mode_variations_v1.json \
  --chips social-convo,engagement-pulse,x_social \
  --events-per-chip 24 \
  --seed-start 20260213 \
  --seed-count 7 \
  --promotion-baseline-id M0_baseline_schema_safe \
  --promotion-candidate-id M1_two_evidence_balanced \
  --min-candidate-non-telemetry 0.95 \
  --min-candidate-schema-statement 0.90 \
  --min-candidate-merge-eligible 0.05 \
  --out-prefix chip_schema_mode_variations_multiseed_v1
```

Promotion should use multi-seed pass rate, not single-seed outcome.

Deterministic check (required):
1. Run the same multi-seed command twice with different `--out-prefix` values.
2. Compare both JSON reports ignoring `generated_at`.
3. Treat results as valid only when leader, pass-rate, and aggregate metrics are identical.

Mode variation matrix:

```bash
python scripts/run_chip_schema_experiments.py \
  --plan benchmarks/data/chip_schema_mode_variations_v1.json \
  --chips social-convo,engagement-pulse,x_social \
  --events-per-chip 24 \
  --promotion-baseline-id M0_baseline_schema_safe \
  --promotion-candidate-id M1_two_evidence_balanced \
  --out-prefix chip_schema_mode_variations_v1
```

This run tests multiple schema modes and still enforces the same promotion gate rule.

Merge-activation matrix (for distillation readiness):

```bash
python scripts/run_chip_schema_experiments.py \
  --plan benchmarks/data/chip_schema_merge_activation_plan_v1.json \
  --chips social-convo,engagement-pulse,x_social \
  --events-per-chip 24 \
  --promotion-baseline-id R0_baseline_safe \
  --promotion-candidate-id R3_two_evidence_relaxed_merge \
  --min-candidate-non-telemetry 0.95 \
  --min-candidate-schema-statement 0.90 \
  --min-candidate-merge-eligible 0.05 \
  --out-prefix chip_schema_merge_activation_v1
```

Current lock (2026-02-13 close):
- Primary: `R3_two_evidence_relaxed_merge`
- Fallback: `R2_relaxed_runtime_merge`
- Both pass promotion against `R0`; `R3` remains slightly stronger on objective.

Observer policy from KPI trends (2-3 windows):

```bash
python scripts/run_chip_observer_policy.py \
  --report-glob "benchmarks/out/chip_learning_diagnostics_active_observer_v*_report.json" \
  --windows 3 \
  --min-windows 2 \
  --min-rows-total 50 \
  --apply
```

Then restart runtime services to load `~/.spark/chip_observer_policy.json`.

## Theory Seeding for Controlled Memory Tests

Seed known-good theories into cognitive memory to validate retrieval behavior:

```bash
python benchmarks/seed_advisory_theories.py \
  --catalog benchmarks/data/advisory_theory_catalog_v1.json \
  --quality good
```

Dry-run preview without writes:

```bash
python benchmarks/seed_advisory_theories.py \
  --catalog benchmarks/data/advisory_theory_catalog_v1.json \
  --quality all \
  --dry-run
```

This enables concrete checks for:
1. whether relevant theories are retrieved at the right time,
2. whether source alignment is correct (memory vs semantic vs mind),
3. whether anti-pattern theories remain suppressed.

## Iteration Loop (Recommended)

1. Run benchmark on current live profile (baseline snapshot).
2. Run benchmark on candidate profiles.
3. Promote winner only if:
   - score improves,
   - no-emit rate does not regress materially,
   - repetition penalty does not worsen.
4. Keep winner live for a real workload window.
5. Run `scripts/advisory_self_review.py` for 12h/24h reality check.
6. Update scenario set with new failure modes (or generate from logs and curate).

## Anti-Gaming Guardrails

- Keep `forbidden_contains` current with known noisy phrases.
- Maintain both emit-expected and suppression-expected scenarios.
- Include mixed tools (`Read`, `Edit`, `Task`, `WebFetch`) each cycle.
- Require trace-bound checks in every benchmark run.

## Expansion Backlog

- Add optional automatic tuneable apply/rollback workflow after winner validation window.

