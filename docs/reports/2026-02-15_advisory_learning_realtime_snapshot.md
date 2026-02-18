# Advisory + Learning Real-Time Snapshot (2026-02-15)

This is a point-in-time run using the live Spark Intelligence environment on this machine.

## Commands Run

```bash
python scripts/status_local.py
python tests/test_pipeline_health.py quick
python tests/test_learning_utilization.py quick

python benchmarks/advisory_quality_ab.py \
  --cases benchmarks/data/advisory_quality_eval_seed.json \
  --profiles baseline,balanced,strict \
  --repeats 1 \
  --force-live \
  --out-prefix advisory_quality_ab_live_now

python scripts/run_advisory_realism_contract.py --run-timeout-s 900

python scripts/advisory_self_review.py --window-hours 24

python benchmarks/memory_retrieval_ab.py \
  --cases benchmarks/data/memory_retrieval_eval_seed.json \
  --systems embeddings_only,hybrid_agentic \
  --top-k 5 \
  --strict-labels \
  --out-prefix memory_retrieval_ab_live_now
```

## Runtime Health

From `python scripts/status_local.py`:
- services: sparkd/dashboard/pulse/meta_ralph/bridge_worker/scheduler/watchdog all RUNNING (bridge_worker last ~48s ago)
- queue: 0 events (pattern backlog 0, validation backlog 0)

From `python tests/test_pipeline_health.py quick`:
- PASS: bridge worker heartbeat (fresh)
- WARN: queue has events (0 total, 0 recent 1h)
- PASS: Meta-Ralph receiving events (total roasted 17458, quality rate 5.8%)
- PASS: cognitive insights storage (total 452, recent 24h: 0)

## Learning Utilization (Loop Closure)

From `python tests/test_learning_utilization.py quick`:
- stored: 452
- retrieved: 500
- acted on: 500
- effectiveness: 83.4%
- grade: A

## Advisory Quality A/B (Seed Set)

Report: `benchmarks/out/advisory_quality_ab_live_now_report.md`
- cases: 10
- winner: balanced (score 0.9400)
- emit accuracy: 100%
- actionability: 100%
- trace-bound: 100%
- memory utilization: 100%
- repetition penalty: 30% (text duplication still material)

## Advisory Realism Contract (Primary + Shadow)

Primary report: `benchmarks/out/advisory_realism_primary_contract_report.md`
- winner: strict
- objective: 0.6935 (base score 0.7490)
- gates: FAIL
  - high_value_rate: 38.89% (target 55%)
  - source_alignment_rate: 50.93% (target 55%)

Shadow report: `benchmarks/out/advisory_realism_shadow_contract_report.md`
- winner: baseline (all profiles tied)
- objective: 0.5673 (base score 0.6772)
- gates: FAIL
  - high_value_rate: 11.11% (target 55%)
  - source_alignment_rate: 50.93% (target 55%)
  - theory_discrimination_rate: 66.67% (target 70%)

## Memory Retrieval A/B (Seed Set)

Report: `benchmarks/out/memory_retrieval_ab_live_now_report.md`
- cases: 5
- winner: hybrid_agentic
- MRR: 0.133 (vs embeddings_only 0.040)
- error rate: 0 for both
- top1 hit: 0.0 for both (overall retrieval quality is still low on this seed set)

## Advisory Self Review (Last 24h)

Report: `docs/archive/docs/reports_self_review/2026-02-15_200030_advisory_self_review.md`
- advisory trace coverage: 98.68%
- engine trace coverage: 50.0% (engine path evidence linkage incomplete)
- strict effectiveness rate: 0.7935
- noise: top repeated advisories account for ~91.48% of all advice items

## Top-10 Benchmarks Status (This Snapshot)

| # | Benchmark | Status | Evidence |
|---|---|---|---|
| 1 | Trigger precision/recall | strong on seed set | `benchmarks/out/advisory_quality_ab_live_now_report.md` (emit acc 100%) |
| 2 | Advice correctness | mixed | seed set looks strong; realism high-value is below gate |
| 3 | Timing/interruption | not directly measured | needs a timing benchmark; repetition/noise suggests real interruption risk |
| 4 | Learning capture quality (write) | partial | pipeline healthy, but 0 recent insights in 24h window |
| 5 | Retrieval accuracy (read) | weak on seed set | `benchmarks/out/memory_retrieval_ab_live_now_report.md` (low MRR, top1=0) |
| 6 | Scope control | partial | realism suppress sets exist; still failing high-value/source-align suggests gating/sourcing needs work |
| 7 | Conflict/priority | not directly measured | needs explicit conflicting-source fixtures |
| 8 | Recency/expiry/versioning | not measured | needs explicit expiry/version fixtures |
| 9 | Robustness/injection | covered by tests | `pytest` suites passing; not re-run here beyond routing/effectiveness unit tests |
| 10 | Online outcomes | partially supported | utilization grade A + self-review strict effectiveness ~0.79, but heavy repetition indicates degraded UX |

