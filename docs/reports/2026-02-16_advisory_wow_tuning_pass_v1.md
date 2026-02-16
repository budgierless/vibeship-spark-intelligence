# Advisory Wow Tuning Pass v1 (2026-02-16)

## Objective
- Improve advisory and cognitive retrieval quality using live benchmark variation runs.
- Convert winning benchmark settings into runtime-safe defaults plus a one-command tuneables apply path.

## Benchmarks Run

### 1) Advisory quality baseline
```bash
python benchmarks/advisory_quality_ab.py \
  --cases benchmarks/data/advisory_quality_eval_extended.json \
  --profiles baseline,balanced,strict \
  --repeats 1 \
  --force-live \
  --out-prefix advisory_quality_live_baseline_2026_02_16
```

Result:
- Winner: `baseline`
- Score: `0.7176`
- Emit accuracy: `70.83%`

### 2) Advisory profile sweep (fast live)
```bash
python benchmarks/advisory_profile_sweeper.py \
  --cases benchmarks/data/advisory_quality_eval_extended.json \
  --repeats 1 \
  --force-live \
  --max-candidates 6 \
  --cooldown-grid 1800,7200 \
  --tool-cooldown-grid 90,120 \
  --advice-repeat-grid 1800,3600,7200 \
  --min-rank-grid 0.45,0.5,0.55 \
  --max-items-grid 4,5 \
  --out-prefix advisory_profile_sweeper_live_fast_2026_02_16
```

Result:
- Winner: `sweep_0002`
- Objective: `0.9564`
- Score: `0.8689`
- No-emit: `0.00%`

### 3) Memory retrieval variant sweep (live learning dataset)
Cases:
- `benchmarks/data/memory_retrieval_eval_live_2026_02_12.json`

Top `hybrid_agentic` variants:
- `vA_baseline`: MRR `0.3438`, Top1 `0.2917`, P95 `68ms`
- `vB_recall_balanced`: MRR `0.5104`, Top1 `0.4583`, P95 `192ms`
- `vC_quality_strict`: MRR `0.5347`, Top1 `0.5000`, P95 `213ms`  ← winner
- `vD_aggressive_recall`: MRR `0.3556`, Top1 `0.2083`, P95 `427ms`
- `vE_support_heavy`: MRR `0.4132`, Top1 `0.3333`, P95 `224ms`

### 4) Domain matrix gate check with winner variant
```bash
python benchmarks/memory_retrieval_domain_matrix.py \
  --cases benchmarks/data/memory_retrieval_eval_live_2026_02_12.json \
  --systems embeddings_only,hybrid,hybrid_agentic \
  --min-cases-per-domain 2 \
  --candidate-k 40 \
  --lexical-weight 0.40 \
  --intent-coverage-weight 0.1 \
  --support-boost-weight 0.1 \
  --reliability-weight 0.05 \
  --semantic-intent-min 0.03 \
  --min-similarity 0.5 \
  --min-fusion-score 0.45 \
  --out-prefix memory_retrieval_domain_matrix_variantC_2026_02_16
```

Result:
- Weighted MRR: `0.535`
- Top1: `0.500`
- Non-empty: `1.000`
- Domain gate pass rate: `100%` (up from `0%` baseline)

## Code Changes in This Pass
- `lib/advisor.py`
  - Stronger domain-aware retrieval defaults for levels `1/2/3`.
  - Domain profiles tuned for `memory`, `coding`, and `x_social`.
- `lib/semantic_retriever.py`
  - Lowered default `min_similarity` from `0.55` to `0.50` to recover recall while preserving fusion gating.
- `scripts/apply_advisory_wow_tuneables.py`
  - Adds dry-run/write utility to apply benchmark-backed tuneables into `~/.spark/tuneables.json`.

## Operational Command
Dry run:
```bash
python scripts/apply_advisory_wow_tuneables.py
```

Apply:
```bash
python scripts/apply_advisory_wow_tuneables.py --write
```

## Expected User-Visible Impact
- Better retrieval hit quality for memory/cognitive advisory loops.
- Higher chance of surfacing past successful learnings for similar contexts.
- Domain-aware advisory feels more relevant and less generic across memory/coding/social tasks.
