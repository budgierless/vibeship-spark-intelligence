# Retrieval Soak + Observer Expansion Run v1

Date: 2026-02-13

## Scope

Executed the next optimization queue without adding features:
1. Retrieval-v2 canary soak validation
2. Observer window expansion + policy refresh
3. Noise/trace check using completed self-review + controlled delta sanity

## 1) Retrieval-v2 Soak Validation

### Commands
- `python scripts/run_advisory_realism_contract.py --primary-prefix advisory_realism_primary_canary_retrieval_v2_soak1 --shadow-prefix advisory_realism_shadow_canary_retrieval_v2_soak1 --run-timeout-s 1200`
- `python benchmarks/memory_retrieval_ab.py --cases benchmarks/data/memory_retrieval_eval_real_user_2026_02_12.json --systems embeddings_only,hybrid,hybrid_agentic --top-k 5 --strict-labels --out-prefix memory_retrieval_ab_canary_retrieval_v2_soak1`
- `python scripts/advisory_self_review.py --window-hours 24`

### Results
- Primary contract: `PASS`
  - file: `benchmarks/out/advisory_realism_primary_canary_retrieval_v2_soak1_report.json`
  - winner: `baseline`
  - objective: `0.7984`
  - high_value: `55.56%`
  - theory_discrimination: `83.33%`
- Shadow contract: `FAIL`
  - file: `benchmarks/out/advisory_realism_shadow_canary_retrieval_v2_soak1_report.json`
  - winner: `baseline`
  - objective: `0.6684`
  - failed gates: `high_value_rate`, `theory_discrimination_rate`
- Memory retrieval:
  - file: `benchmarks/out/memory_retrieval_ab_canary_retrieval_v2_soak1_report.json`
  - winner remains: `hybrid_agentic`
- Self-review:
  - file: `docs/archive/docs/reports_self_review/2026-02-13_124252_advisory_self_review.md`
  - repeated-advice concentration remains high (`~61.21%` top repeated cluster share)
  - engine trace coverage still low (`50.2%`)

## 2) Observer Window Expansion + Policy Refresh

### Commands
- `python scripts/run_chip_learning_diagnostics.py --limit-per-chip 2500 --active-only --project-path "C:\Users\USER\Desktop\vibeship-spark-intelligence" --max-age-days 30 --observer-limit 40 --out-prefix chip_learning_diagnostics_active_observer_expanded_v1`
- `python scripts/run_chip_learning_diagnostics.py --limit-per-chip 2500 --max-age-days 30 --observer-limit 40 --out-prefix chip_learning_diagnostics_observer_expanded_all_v1`
- `python scripts/run_chip_observer_policy.py --report-glob "benchmarks/out/chip_learning_diagnostics*_report.json" --windows 12 --min-windows 3 --min-rows-total 50 --disable-max-schema-statement-rate 0.03 --disable-min-telemetry-rate 0.75 --keep-min-schema-statement-rate 0.20 --keep-min-merge-eligible 1 --out-prefix chip_observer_policy_expanded_v1 --apply`
- `python scripts/prune_chip_observer_rows.py --active-only --project-path "C:\Users\USER\Desktop\vibeship-spark-intelligence" --archive --apply`

### Results
- Expanded all-chip diagnostics:
  - file: `benchmarks/out/chip_learning_diagnostics_observer_expanded_all_v1_report.json`
  - rows analyzed: `11176`
  - telemetry rate: `99.80%`
  - statement yield: `0.15%`
  - merge-eligible: `2`
- Expanded observer policy:
  - file: `benchmarks/out/chip_observer_policy_expanded_v1_report.json`
  - windows analyzed: `12`
  - disable/keep/neutral: `4 / 4 / 22`
  - disabled high-noise observers stayed stable: `x_social/chip_level`, `engagement-pulse/chip_level`, `social-convo/chip_level`, `engagement-pulse/unknown`
- Prune run on active chips:
  - rows `9 -> 9` (no additional rows eligible for pruning in current active files)

## 3) Noise/Trace Check Status

Attempted dedicated live noise/trace matrix and high-round controlled delta, but those runs were too slow/noisy for this interactive pass and were terminated.

Completed fallback sanity:
- `python scripts/advisory_controlled_delta.py --rounds 12 --label canary_retrieval_v2_nonlive_sanity --out docs/reports/advisory_delta_canary_retrieval_v2_nonlive_sanity.json`

Sanity output:
- file: `docs/reports/advisory_delta_canary_retrieval_v2_nonlive_sanity.json`
- rounds: `12`
- emitted returns: `12`
- engine trace coverage: `49.15%`
- fallback share: `0.0%`

## Live Tuneables State After Run

Verified in `C:\Users\USER\.spark\tuneables.json`:
- advisory defaults remain balanced (`7200/120/3600`, `max_items=4`, `min_rank=0.5`)
- retrieval-v2 canary remains active:
  - via `retrieval.overrides.*`
  - `semantic_context_min=0.18`
  - `semantic_lexical_min=0.05`
  - `semantic_strong_override=0.92`
  - `lexical_weight=0.32`

## Decision Snapshot

1. Retrieval-v2 remains promising but not ready for full promotion because shadow contract still fails the same two gates.
2. Observer expansion confirmed the core bottleneck is still telemetry-heavy observer output quality, not advisory gate tuning.
3. Next highest-value benchmark should focus on improving signal richness in observer outputs, then rerun retrieval-v2 contract/shadow.
