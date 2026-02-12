# Memory Retrieval Execution Spec
Date: 2026-02-12  
Scope window: 2026-02-12 to 2026-02-19  
Status: Active

## Goal
Stabilize memory retrieval reliability and produce a strict A/B decision on retrieval strategy quality (`embeddings_only` vs `hybrid` vs `hybrid_agentic`) under matched conditions.

## Current Snapshot
- Progress system integration: high confidence.
- Memory retrieval reliability: improving (core routing now deterministic and instrumented).
- Main risk: auth/session/transport/policy failures are conflated into generic "auth blocked" messaging.
- Benchmark status: harness executed with tuned runs on 20-case real-user set.

## Implementation Update (2026-02-12)
- Implemented Carmack-style retrieval controls in advisor routing:
  - embeddings-first fast path
  - minimal escalation gate in `auto` mode (weak count, weak top score, high-risk)
  - hard agentic deadline (`agentic_deadline_ms`)
  - windowed agentic rate cap (`agentic_rate_limit`)
  - insight prefilter cap (`prefilter_max_insights`)
  - route log: `~/.spark/advisor/retrieval_router.jsonl`
- Added/validated unit tests for:
  - rate-cap behavior
  - deadline cut-off behavior
  - prefilter cap behavior
- Tuned A/B rerun outputs:
  - `benchmarks/out/memory_retrieval_ab_tuning_fastembed_bm25_2026_02_12.json`
  - `benchmarks/out/memory_retrieval_ab_tuning_tfidf_bm25_2026_02_12.json`
- Observed benchmark highlights:
  - fastembed:
    - embeddings_only: MRR 0.635, top1 0.55, p95 198ms
    - hybrid_agentic: MRR 0.6542, top1 0.60, p95 623ms
  - tfidf:
    - embeddings_only: MRR 0.0917, top1 0.05, p95 75ms
    - hybrid_agentic: MRR 0.3958, top1 0.25, p95 217ms

## Priority Workboard
| Priority | Work Item | Owner | Due Date | Acceptance Criteria |
|---|---|---|---|---|
| P0 | Add diagnostics endpoint contract (`/api/memory/health`, `/api/memory/diag`) | Spark runtime maintainer | 2026-02-13 | Endpoint returns explicit health fields and non-200 failures are classified |
| P0 | Enforce error taxonomy split (`auth`, `timeout`, `policy`, `transport`, `unknown`) | Spark runtime maintainer | 2026-02-13 | No generic auth catch-all in retrieval path logs for classified failures |
| P0 | Standardize retrieval identity envelope (`session_id`, `actor_id`, `scope`, `memory_tier`) | Spark + bridge maintainers | 2026-02-14 | Same envelope present in direct and bridge retrieval paths |
| P0 | Run strict A/B benchmark and publish canonical report | Product owner + Spark | 2026-02-14 | >=20 matched pairs, one report, winner decision recorded |
| P1 | Add replayable retrieval tests for auth/session/policy modes | QA + Spark | 2026-02-15 | All six failure-mode tests pass in CI |
| P1 | Add trace correlation (`trace_id`, `request_id`) to retrieval diagnostics | Spark runtime maintainer | 2026-02-15 | Failures link end-to-end across API, bridge, and retriever logs |

## Diagnostics Contract
Use admin-only endpoints and redact sensitive values.

### `GET /api/memory/health`
Response fields:
- `auth_configured`: boolean
- `auth_valid`: boolean
- `provider_reachable`: boolean
- `session_bound`: boolean
- `latency_ms`: integer
- `last_error_code`: string or null
- `last_error_kind`: `auth|timeout|policy|transport|unknown|null`
- `trace_id`: string
- `request_id`: string

### `GET /api/memory/diag?session_id=...`
Response fields:
- all `health` fields
- `session_id`: string
- `actor_id`: string
- `scope`: `main|shared|...`
- `memory_tier`: `daily|long_term|private|...`
- `provider_path`: `direct|bridge`
- `redacted`: boolean

Access control:
- Authenticated operator/admin only.
- Never expose raw tokens, headers, or credential blobs.
- Redact provider config to booleans and provider names only.

## Error Taxonomy Rules
Classification order must be deterministic:
1. `policy`
2. `auth`
3. `timeout`
4. `transport`
5. `unknown`

Mapping:
- `401/403`, missing/invalid credentials -> `auth`
- deadline exceeded, timeout exceptions -> `timeout`
- guardrail/policy denial -> `policy`
- connectivity/network/bridge failures -> `transport`
- everything else -> `unknown`

## A/B Benchmark Protocol
Harness:
- `benchmarks/memory_retrieval_ab.py`
- seed file: `benchmarks/data/memory_retrieval_eval_seed.json`

Systems:
1. `embeddings_only`
2. `hybrid`
3. `hybrid_agentic`

Required metrics:
- `precision@k`
- `recall@k`
- `MRR`
- `top1_hit_rate`
- `p50/p95 latency`
- `error_rate` + error kind counts

Initial success thresholds:
- Hybrid-agentic quality lift: >=10% MRR over embeddings-only.
- Reliability non-regression: error rate not worse than baseline.
- Latency budget: p95 <= 1800ms.
- Classification coverage: 100% non-empty `error_kind` for failures.

### Run Commands
```bash
python benchmarks/memory_retrieval_ab.py \
  --cases benchmarks/data/memory_retrieval_eval_seed.json \
  --systems embeddings_only,hybrid,hybrid_agentic \
  --top-k 5 \
  --strict-labels \
  --out-prefix memory_retrieval_ab_2026_02_12
```

```bash
python benchmarks/memory_retrieval_ab.py \
  --cases benchmarks/data/memory_retrieval_eval_seed.json \
  --systems embeddings_only,hybrid,hybrid_agentic \
  --top-k 5 \
  --print-case-results
```

Outputs:
- `benchmarks/out/<prefix>_report.json`
- `benchmarks/out/<prefix>_report.md`

## 24h Execution Checklist (2026-02-12 to 2026-02-13)
1. Implement diagnostics endpoint contract and taxonomy mapping.
2. Label at least 20 real query cases in benchmark input.
3. Run strict A/B and publish canonical report.
4. Decide default retrieval mode (`hybrid_agentic` keep/rollback/split-by-class).
5. Open follow-up issues for any threshold misses.

## Go/No-Go Decision Rule
- Go: hybrid-agentic wins on quality threshold, reliability is stable, latency within budget.
- Conditional: split strategy by task class if quality improves but latency breaches budget.
- No-go: rollback default to `hybrid` or `embeddings_only` if quality lift is insufficient or stability regresses.
