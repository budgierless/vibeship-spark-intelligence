# Chip Benchmarking

Run methodology benchmarks against a saved event log.

## Quick Start

```bash
python benchmarks/run_benchmarks.py --limit 500
```

Optional:

```bash
python benchmarks/run_benchmarks.py --chips vibecoding,game_dev --limit 1000
```

Synthetic data:

```bash
python benchmarks/generate_synthetic.py --vibe 50 --game 50
python benchmarks/run_benchmarks.py --log benchmarks/synthetic_events.jsonl --chips vibecoding,game_dev
```

Scenario-based live runs:

```bash
# 1) Record a live session while building artifacts
python benchmarks/record_session.py --scenario benchmarks/scenarios/marketing/scenario.yaml --out benchmarks/logs/marketing_run.jsonl --session marketing-001

# 2) Run benchmarks + scenario scoring
python benchmarks/run_benchmarks.py --log benchmarks/logs/marketing_run.jsonl --chips marketing --scenario benchmarks/scenarios/marketing/scenario.yaml
```

Scenario weights:

- `outcome_signals` and `expected_artifacts` accept weighted entries:
  - `- signal: "kpi defined"\n    weight: 1.0`
  - `- path: "benchmarks/projects/marketing/brief.md"\n    weight: 1.0`

Heuristic enrichment (fills missing fields for domain chips):

```bash
python benchmarks/run_benchmarks.py --chips vibecoding,game_dev --enrich --limit 2000
```

Outputs:
- `benchmarks/out/report.json`
- `benchmarks/out/report.md`
Logs:
- `benchmarks/logs/*.jsonl` (live runs)

## Memory Retrieval A/B

Compare retrieval systems on the same query set:

```bash
python benchmarks/memory_retrieval_ab.py --cases benchmarks/data/memory_retrieval_eval_seed.json
```

Strict labeled run:

```bash
python benchmarks/memory_retrieval_ab.py \
  --cases benchmarks/data/memory_retrieval_eval_seed.json \
  --systems embeddings_only,hybrid,hybrid_agentic \
  --top-k 5 \
  --strict-labels
```

If strict semantic gates produce mostly empty results in your environment,
run with relaxed gates for comparison-only analysis:

```bash
python benchmarks/memory_retrieval_ab.py \
  --cases benchmarks/data/memory_retrieval_eval_seed.json \
  --systems embeddings_only,hybrid,hybrid_agentic \
  --top-k 5 \
  --strict-labels \
  --min-similarity 0.0 \
  --min-fusion-score 0.0
```

Outputs:
- `benchmarks/out/memory_retrieval_ab_report.json`
- `benchmarks/out/memory_retrieval_ab_report.md`

## Advisory Quality A/B

Benchmark advisory usefulness directly (not just retrieval quality):

```bash
python benchmarks/advisory_quality_ab.py \
  --cases benchmarks/data/advisory_quality_eval_seed.json \
  --profiles baseline,balanced,strict \
  --repeats 1 \
  --force-live \
  --out-prefix advisory_quality_ab
```

This writes:
- `benchmarks/out/advisory_quality_ab_report.json`
- `benchmarks/out/advisory_quality_ab_report.md`

Scoring dimensions:
- emit correctness (`should_emit` vs actual emit)
- expected/forbidden content checks
- actionability (`Next check` / command-level guidance)
- trace-bound decision coverage
- memory-source utilization
- repetition penalty across emitted texts

Use `--profile-file` to test custom profile variants layered over defaults.

Extended scenario set:

```bash
python benchmarks/advisory_quality_ab.py \
  --cases benchmarks/data/advisory_quality_eval_extended.json \
  --profiles baseline,balanced,strict \
  --repeats 1 \
  --force-live \
  --out-prefix advisory_quality_extended
```

Auto profile sweeper (bounded search over tuneable grids):

```bash
python benchmarks/advisory_profile_sweeper.py \
  --cases benchmarks/data/advisory_quality_eval_extended.json \
  --repeats 1 \
  --force-live \
  --max-candidates 12 \
  --out-prefix advisory_profile_sweeper
```

Outputs:
- `benchmarks/out/advisory_profile_sweeper_report.json`
- `benchmarks/out/advisory_profile_sweeper_report.md`
- `benchmarks/out/advisory_profile_sweeper_winner_profile.json`

Generate draft real-world advisory cases from recent runtime logs:

```bash
python benchmarks/build_advisory_cases_from_logs.py \
  --lookback-hours 24 \
  --limit 20 \
  --out benchmarks/data/advisory_quality_eval_from_logs.json
```

Seed theory examples into cognitive memory for controlled retrieval tests:

```bash
python benchmarks/seed_advisory_theories.py \
  --catalog benchmarks/data/advisory_theory_catalog_v1.json \
  --quality good
```

Dry-run preview:

```bash
python benchmarks/seed_advisory_theories.py \
  --catalog benchmarks/data/advisory_theory_catalog_v1.json \
  --quality all \
  --dry-run
```

Run realism-grade advisory benchmark (depth tiers + cross-system + theory discrimination):

```bash
python benchmarks/advisory_realism_bench.py \
  --cases benchmarks/data/advisory_realism_eval_v1.json \
  --profiles baseline,balanced,strict \
  --repeats 1 \
  --force-live \
  --out-prefix advisory_realism_bench
```

Realism outputs:
- `benchmarks/out/advisory_realism_bench_report.json`
- `benchmarks/out/advisory_realism_bench_report.md`

Run multi-domain realism matrix (coding/strategy/marketing/ui/social/conversation/prompting/research/memory):

```bash
python scripts/run_advisory_realism_domain_matrix.py \
  --cases benchmarks/data/advisory_realism_eval_multidomain_v1.json \
  --force-live \
  --save-domain-reports
```

Matrix outputs:
- `benchmarks/out/advisory_realism_domain_matrix_report.json`
- `benchmarks/out/advisory_realism_domain_matrix_report.md`
- `benchmarks/out/advisory_realism_domain_matrix_domains/*.json|.md` (when `--save-domain-reports`)

Run chip strategy experiments beyond simple on/off (A/B/C/D segmented plans):

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

Chip experiment outputs:
- `benchmarks/out/advisory_chip_experiments_v2_report.json`
- `benchmarks/out/advisory_chip_experiments_v2_report.md`

Chip experiment report now includes ablation fields:
- `ablation_objective`, `ablation_high_value_rate`, `ablation_harmful_emit_rate`
- `chip_lift_objective`, `chip_lift_high_value_rate`, `chip_lift_harmful_emit_rate`

This prevents false positives by explicitly measuring whether chips improve outcomes vs a chips-disabled pass.

Chip learning diagnostics (indirect path: chips -> distillation -> cognitive memory):

```bash
python scripts/run_chip_learning_diagnostics.py \
  --limit-per-chip 400 \
  --out-prefix chip_learning_diagnostics_v1
```

Threshold sensitivity pass (to test whether tuneables are the bottleneck):

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

Diagnostics outputs:
- `benchmarks/out/chip_learning_diagnostics_v1_report.json`
- `benchmarks/out/chip_learning_diagnostics_v1_report.md`

Key diagnostics to track:
- `telemetry_rate`
- `telemetry_observer_rate`
- `missing_confidence_rate`
- `missing_quality_rate`
- `merge_eligible`

Candidate profile overlay with retrieval/chip tuning:
- `benchmarks/data/advisory_realism_profile_candidates_v2.json`

Operational contract (locked):
- Primary: `benchmarks/data/advisory_realism_eval_v2.json`
- Shadow: `benchmarks/data/advisory_realism_eval_v1.json`
- Contract file: `benchmarks/data/advisory_realism_operating_contract_v1.json`

One-command primary + shadow run with compact pass/fail dashboard:

```bash
python scripts/run_advisory_realism_contract.py
```

With explicit per-run timeout:

```bash
python scripts/run_advisory_realism_contract.py --run-timeout-s 1200
```

Primary run:

```bash
python benchmarks/advisory_realism_bench.py \
  --cases benchmarks/data/advisory_realism_eval_v2.json \
  --profiles baseline,balanced,strict \
  --repeats 1 \
  --force-live \
  --out-prefix advisory_realism_primary
```

Shadow run:

```bash
python benchmarks/advisory_realism_bench.py \
  --cases benchmarks/data/advisory_realism_eval_v1.json \
  --profiles baseline,balanced,strict \
  --repeats 1 \
  --force-live \
  --out-prefix advisory_realism_shadow
```

### Tune for best-vs-best comparison

Use grid-search tuning to optimize each system independently, then compare
their best configurations on train/dev/full splits:

```bash
python benchmarks/tune_memory_retrieval_ab.py \
  --cases benchmarks/data/memory_retrieval_eval_real_user_2026_02_12.json \
  --systems embeddings_only,hybrid_agentic \
  --backend tfidf \
  --candidate-grid 20,40 \
  --lexical-grid 0.1,0.3,0.5 \
  --min-similarity-grid 0.0,0.25,0.5 \
  --min-fusion-grid 0.0,0.25,0.45 \
  --out benchmarks/out/memory_retrieval_ab_tuning_tfidf.json
```

```bash
python benchmarks/tune_memory_retrieval_ab.py \
  --cases benchmarks/data/memory_retrieval_eval_real_user_2026_02_12.json \
  --systems embeddings_only,hybrid_agentic \
  --backend fastembed \
  --candidate-grid 40 \
  --lexical-grid 0.0,0.1,0.3 \
  --min-similarity-grid 0.0,0.25 \
  --min-fusion-grid 0.0,0.25 \
  --out benchmarks/out/memory_retrieval_ab_tuning_fastembed_quick.json
```

Output:
- `benchmarks/out/memory_retrieval_ab_tuning_*.json`

## Local Model Stress Suite (Ollama)

Stress-test local models across multiple methodologies (advisory, retrieval conflict resolution,
chip routing, control-plane budgeting, noisy context, structured JSON output).

Default models include:
- `llama3.2:3b`
- `phi4-mini`
- `qwen2.5-coder:3b`

Run:

```bash
python scripts/local_ai_stress_suite.py --repeats 3 --budget-ms 3000 --soft-budget-ms 3500
```

Include live pipeline replay contexts from your local Spark queue:

```bash
python scripts/local_ai_stress_suite.py --repeats 5 --live-scenarios 12 --budget-ms 3000 --soft-budget-ms 3500
```

Custom models:

```bash
python scripts/local_ai_stress_suite.py --models "llama3.2:3b,phi4-mini,qwen2.5-coder:3b"
```

Output:
- `benchmarks/out/local_model_stress_report.json`

## Notes

- This replays a local event log (`~/.spark/queue/events.jsonl`) by default.
- Results are heuristic and meant to compare methodology variants on the same data.

## Beyond Primitive Benchmarks (Superintelligence Metrics)

Track these in addition to raw accept rates:
- Human-useful ratio (non-operational insights / total).
- Outcome coverage (insights with validated outcomes).
- Preference stability (validated preferences over time).
- Reasoning density (why/principle insights vs sequences).
- Safety compliance (unsafe insights blocked).
- Cross-domain transfer rate (insights reused across chips).
