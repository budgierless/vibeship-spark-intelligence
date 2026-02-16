# Cognitive Retrieval Uplift Report (v2)

Date: 2026-02-16
Scope: Improve cognitive advisory retrieval quality (not telemetry-driven noise), verify with benchmark variants, and lock safer default behavior.

## What Changed

### Runtime retrieval (lib/advisor.py)
- Added strict low-signal candidate filtering in retrieval prefilter path:
  - drops telemetry-like struggle artifacts (`*_error`, `fails with other`, transcript/meta fragments)
  - controlled by `retrieval.prefilter_drop_low_signal` (default: `true`)
- Added intent/support/reliability rerank features and policy knobs:
  - `intent_coverage_weight`
  - `support_boost_weight`
  - `reliability_weight`
  - `semantic_intent_min`
- Added per-route observability fields in `~/.spark/advisor/retrieval_router.jsonl` for those new knobs and support-count behavior.
- Defaulted new rerank weights to conservative values for levels 1/2 (off by default) after live benchmark comparison.

### Benchmark harness (benchmarks/memory_retrieval_ab.py)
- Added strict cognitive candidate filter to benchmark path for parity with runtime logic.
- Added benchmark controls for cognitive rerank dimensions:
  - `--intent-coverage-weight`
  - `--support-boost-weight`
  - `--reliability-weight`
  - `--semantic-intent-min`
  - `--disable-strict-filter`
- Added stronger hybrid retrieval ranking internals with cross-query support counting.

### Benchmark tuner (benchmarks/tune_memory_retrieval_ab.py)
- Extended grid search to include new cognitive rerank knobs and strict-filter toggle.

### Tests
- Added/updated tests for:
  - low-signal filtering in prefilter/retrieval paths
  - support-boost behavior across multi-query retrieval
  - benchmark-level strict filter behavior
- Key passing suites:
  - `tests/test_advisor_retrieval_routing.py`
  - `tests/test_memory_retrieval_ab.py`
  - `tests/test_advisory_quality_ab.py -k retrieval_overrides`
  - `tests/test_advisor_tool_specific_matching.py`

## Benchmark Runs and Results

## 1) Real-user 20-case set (current defaults)
Command output artifact:
- `benchmarks/out/memory_retrieval_ab_cognitive_default_real20_v2_report.json`

Results:
- `embeddings_only`: MRR `0.06`, P@K `0.05`, Recall@K `0.0625`, Top1 `0.0`, p95 `32ms`
- `hybrid`: MRR `0.1183`, P@K `0.07`, Recall@K `0.0875`, Top1 `0.05`, p95 `29ms`
- `hybrid_agentic`: MRR `0.3183`, P@K `0.15`, Recall@K `0.1875`, Top1 `0.15`, p95 `92ms`

Winner: `hybrid_agentic`

## 2) Live 24-case set (current defaults)
Command output artifact:
- `benchmarks/out/memory_retrieval_ab_cognitive_default_live24_v2_report.json`

Results:
- `embeddings_only`: MRR `0.0521`, P@K `0.025`, Recall@K `0.125`, Top1 `0.0`, p95 `33ms`
- `hybrid`: MRR `0.1597`, P@K `0.05`, Recall@K `0.25`, Top1 `0.0833`, p95 `26ms`
- `hybrid_agentic`: MRR `0.3438`, P@K `0.1`, Recall@K `0.5`, Top1 `0.2917`, p95 `82ms`

Winner: `hybrid_agentic`

## 3) Historical comparison signal
Prior artifact (same 24-case file, older retrieval behavior):
- `benchmarks/out/memory_retrieval_ab_live_2026_02_12_report.json`

Prior summary:
- All systems had `MRR = 0.0`, `P@K = 0.0`, `Top1 = 0.0`.

Current v2 defaults on same 24-case input now produce non-zero retrieval quality with clear system separation and strong `hybrid_agentic` lead.

## 4) Variant sweep highlights (20-case)
Artifacts:
- `benchmarks/out/memory_retrieval_ab_cognitive_controlA_report.json`
- `benchmarks/out/memory_retrieval_ab_cognitive_variantB_report.json`
- `benchmarks/out/memory_retrieval_ab_cognitive_variantC_report.json`
- `benchmarks/out/memory_retrieval_ab_cognitive_real20_variantD_strictOnly_report.json`

Decision:
- Best stable profile was conservative strict filtering with extra rerank boosts disabled by default (`variantD / current defaults`).
- Extra rerank boosts are kept as tuneable knobs for future dataset-specific tuning.

## Real-Time Advisory Check

Artifact:
- `docs/reports/2026-02-16_1705_advisory_controlled_delta_cognitive_v2.json`

Engine summary:
- rounds: `12`
- trace coverage: `100%`
- events: `emitted=3`, `no_emit=3`, `no_advice=6`
- route: `live` only
- emitted latency: p50 `311.8ms`, p95 `599.1ms`

Interpretation:
- Advisory loop remained responsive while cognitive retrieval changes were integrated.

## Final Assessment

Working now:
- Cognitive retrieval quality is materially better on live benchmark sets.
- Low-signal telemetry-like memories are filtered from retrieval candidates.
- `hybrid_agentic` remains the strongest strategy with improved absolute metrics.
- New rerank levers are available for controlled tuning without forcing risky defaults.

Still to improve next:
1. Expand labeled cognitive benchmark cases with stricter key-based labels (reduce loose `contains` matching noise).
2. Run scheduled sweeps per domain (coding/advisory/product) and set per-domain retrieval profiles.
3. Add an online retrieval-quality monitor in self-review output (top1/mrr trend over rolling windows).
