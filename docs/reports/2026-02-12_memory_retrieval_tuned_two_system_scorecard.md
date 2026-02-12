# Memory Retrieval Tuned Scorecard (Embeddings vs Hybrid-Agentic)
Date: 2026-02-12  
Dataset: `benchmarks/data/memory_retrieval_eval_real_user_2026_02_12.json`  
Cases: 20 (train=14, dev=6 split for tuning)

## Scope
- Tune `embeddings_only` and `hybrid_agentic` independently.
- Compare best-vs-best configurations.
- Backends tested: `tfidf`, `fastembed`.

## Commands

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

## Best Params

### TF-IDF backend
- `embeddings_only`: `candidate_k=40`
- `hybrid_agentic`: `candidate_k=40`, `lexical_weight=0.5`, `min_similarity=0.0`, `min_fusion_score=0.0`

### Fastembed backend
- `embeddings_only`: `candidate_k=40`
- `hybrid_agentic`: `candidate_k=40`, `lexical_weight=0.3`, `min_similarity=0.25`, `min_fusion_score=0.25`

## Results (Full 20-case set)

### TF-IDF (winner: `hybrid_agentic`)
| System | P@5 | Recall@5 | MRR | Top1 Hit | p95 (ms) | Error Rate |
|---|---:|---:|---:|---:|---:|---:|
| embeddings_only | 0.040 | 0.050 | 0.0917 | 0.050 | 85 | 0.000 |
| hybrid_agentic | 0.110 | 0.1375 | 0.3250 | 0.200 | 545 | 0.000 |

### Fastembed (winner: `embeddings_only`)
| System | P@5 | Recall@5 | MRR | Top1 Hit | p95 (ms) | Error Rate |
|---|---:|---:|---:|---:|---:|---:|
| embeddings_only | 0.450 | 0.6125 | 0.6350 | 0.550 | 147 | 0.000 |
| hybrid_agentic | 0.220 | 0.2750 | 0.5417 | 0.500 | 913 | 0.000 |

## Decision
- If objective is absolute retrieval quality + latency on this dataset: use `fastembed + embeddings_only`.
- If objective is to maximize hybrid-agentic relative lift in low-quality embedding environments: `tfidf + tuned hybrid_agentic` wins.

## Artifacts
- `benchmarks/out/memory_retrieval_ab_tuning_tfidf.json`
- `benchmarks/out/memory_retrieval_ab_tuning_fastembed_quick.json`
