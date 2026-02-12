# OpenClaw Memory + Advisory: Concrete Plan and Live Baseline
Date: 2026-02-12
Owner: Spark + Meta
Scope: memory retrieval reliability, advisory quality, and cross-cutting taxonomy clarity

## 1) Why this plan exists
This plan combines:
- user-reported pain points from real usage,
- live runtime evidence from this environment,
- existing Spark/OpenClaw architecture and benchmark outputs.

Primary objective:
- move from "vague failure + noisy advisory" to "explicit failure kind + actionable next step + stable retrieval behavior".

---

## 2) Unified complaint taxonomy (severity + owner)

| ID | Area | Complaint | Severity | Primary owner |
|---|---|---|---|---|
| M1 | Memory | "Auth blocked" over-reported and vague | P0 | Runtime / memory API |
| M2 | Memory | Inconsistent recall on repeated prompt | P0 | Retrieval pipeline |
| M3 | Memory | Scope/session mismatch (private vs shared) | P0 | Session/scope contract |
| M4 | Memory | Stale retrieval after recent writes | P1 | Indexing/refresh |
| M5 | Memory | Low explainability (why selected/rejected) | P1 | Retrieval diagnostics |
| A1 | Advisory | Repetitive advisory loops | P0 | Advisory gate/packet |
| A2 | Advisory | Noisy/generic advisories | P0 | Advisory ranking/synthesis |
| A3 | Advisory | Weak proof grounding | P0 | Advisory payload contract |
| A4 | Advisory | Context mismatch (global vs local task) | P1 | Intent/task-plane router |
| A5 | Advisory | Low actionability ("warn only") | P1 | Advisory formatter |
| X1 | Cross-cutting | Failure taxonomy too fuzzy | P0 | Shared error contract |

---

## 3) Live baseline (executed now)

Timestamp window: last 48h + live command runs on 2026-02-12.

### Runtime health
- `sparkd`: healthy
- `bridge_worker`: healthy
- `scheduler`: healthy
- `pulse`: mixed in live checks (observed running earlier, stopped in latest check)
- queue: 0

### Sync health
- success: `openclaw`, `exports`
- error: `claude_code`, `cursor`, `windsurf`, `clawdbot`
- current total syncs: 7155

Core/optional split (after health-contract patch):
- core: `openclaw`, `exports` -> healthy
- optional: `claude_code`, `cursor`, `windsurf`, `clawdbot` -> error
- interpretation: optional failures should not downgrade core health state.

### Advisory behavior (last 48h)
- advisory engine events: 481
- `fallback_emit`: 312
- `emitted`: 149
- `no_emit`: 18
- `synth_empty`: 2
- advisory emits: 149
- unique advisory texts: 120
- duplicate rate: 0.19
- feedback entries: 4

Interpretation:
- advisory path still fallback-heavy with low feedback closure.

### Memory retrieval A/B (live run on real-user set)

Strict gates (default behavior):
- winner: `embeddings_only`
- `embeddings_only`: non-empty 1.0, MRR 0.0917, p95 88ms
- `hybrid`: non-empty 0.0, MRR 0.0
- `hybrid_agentic`: non-empty 0.0, MRR 0.0

Relaxed gates (comparison mode):
- winner: `hybrid_agentic`
- `embeddings_only`: MRR 0.0917
- `hybrid`: MRR 0.1017
- `hybrid_agentic`: MRR 0.285, top1 0.15, p95 353ms

Interpretation:
- quality upside exists for `hybrid_agentic`,
- current strict gating is collapsing hybrid outputs to empty.

### Memory retrieval A/B (post-fix rerun, same dataset)

Strict/default rerun after empty-result rescue patch:
- winner: `hybrid_agentic`
- `embeddings_only`: non-empty 1.0, MRR 0.0917, p95 77ms
- `hybrid`: non-empty 1.0, MRR 0.11, p95 34ms
- `hybrid_agentic`: non-empty 1.0, MRR 0.20, p95 103ms

Artifact:
- `benchmarks/out/memory_retrieval_ab_real_user_2026_02_12_default_after_rescue_report.md`

Interpretation:
- strict-gate collapse is removed,
- hybrid paths now return usable results under default gates,
- quality leadership shifts to `hybrid_agentic` with controlled latency.

### Test pass (live)
- `tests/test_error_taxonomy.py`
- `tests/test_memory_retrieval_ab.py`
- `tests/test_advisory_packet_store.py`
- `tests/test_advisor_effectiveness.py`
- Result: 22 passed

---

## 4) Concrete fix plan (with "run now" steps)

## Phase 0 (today): Make failures explicit and debuggable
Goal: remove vague "blocked/unavailable" responses.

1. Enforce one shared failure enum in memory/advisory responses:
   - `auth`, `timeout`, `policy`, `no_hit`, `stale`, `transport`, `unknown`
2. Add `error_kind` and `error_code` to every failed retrieval/advisory event.
3. Add deterministic classification order:
   - `policy -> auth -> timeout -> transport -> no_hit -> stale -> unknown`

Run now:
- add unit tests for classifier mapping coverage.
- verify no generic fallback error strings remain in new code paths.

Acceptance:
- 100% of retrieval failures include non-empty `error_kind`.

Owner:
- Runtime/memory API + advisory engine maintainers.

## Phase 1 (24h): Retrieval consistency and session/scope correctness
Goal: same prompt + same context gives stable memory behavior.

1. Standardize retrieval identity envelope:
   - `session_id`, `actor_id`, `scope`, `memory_tier`, `provider_path`
2. Force identical envelope across direct and bridge paths.
3. Patch strict gate thresholds causing hybrid empty collapse.
4. Add staleness metadata:
   - `retrieved_at`, `indexed_at`, `age_ms`, `freshness_state`.

Run now:
- rerun real-user A/B with strict gates after threshold patch.
- compare non-empty rate and MRR deltas.

Acceptance:
- hybrid/hybrid_agentic non-empty rate > 0.9 on real-user set.
- no session/scope ambiguity in diagnostics output.

Owner:
- Retrieval pipeline + bridge maintainers.

## Phase 2 (48h): Advisory trust rebuild
Goal: less noise, more grounded action.

1. Add advisory dedupe suppression:
   - suppress repeats unless evidence hash changes materially.
2. Make evidence mandatory in advisory payload:
   - proof refs (trace/request/packet ids), source, confidence.
3. Add actionability formatter:
   - every warning includes one concrete next command/check.
4. Tighten context routing:
   - prefer local task-plane evidence before global cognitive context.

Run now:
- measure duplicate advisory rate before/after dedupe.
- sample 50 advisories for evidence-field completeness.

Acceptance:
- duplicate advisory rate < 8%.
- >= 90% advisories include concrete action + proof refs.

Owner:
- Advisory engine + packet store + formatter maintainers.

Status update (executed now):
- advisory text-fingerprint cooldown suppression shipped in engine/state.
- packet advice rows now include `proof_refs` + `evidence_hash` fields for grounded payloads.
- emitted advisories now enforce actionability:
  - if no concrete command/check is present, engine appends `Next check: \`<command>\``.

## Phase 3 (72h): UI transparency (what users asked for)
Goal: user can instantly see live/fallback/blocked state.

1. Add retrieval trace panel:
   - source, scope, session, top candidates, rejection reasons.
2. Add persistent status badge:
   - `live`, `fallback`, `blocked`, `stale`.
3. Add one-click "copy diagnostics" bundle for support/debug.

Run now:
- smoke test with 5 real prompts and verify badge correctness.

Acceptance:
- user can identify failure type + next fix within one screen.

Owner:
- Pulse/OpenClaw UI + API integration maintainers.

Status update (executed now):
- advisory engine events now include diagnostics envelope fields:
  - `session_id`, `trace_id`, `session_context_key`, `scope`, `provider_path`, `source_counts`, `missing_sources`
- `on_user_prompt` now logs `user_prompt_prefetch` with envelope metadata.
- engine status now exposes a delivery badge:
  - `live | fallback | blocked | stale` (derived from recent engine events with staleness window).
- dashboard/operator surfaces now expose advisory delivery status:
  - mission and ops API payloads include compact advisory status + `delivery_badge`.
  - mission and ops UI cards now render badge state, reason, age, and queue/prefetch context.

---

## 5) Mapping complaints to exact fixes

| Complaint | Fix lever |
|---|---|
| "Auth blocked too often" | taxonomy split + classifier + explicit `error_kind` |
| Inconsistent recall | session envelope unification + path parity |
| Wrong scope leaks/misses | scope diagnostics + envelope validation |
| Stale retrieval | freshness metadata + index timing trace |
| Low explainability | retrieval trace panel + rejection reasons |
| Repetitive advisories | dedupe/cooldown by evidence hash |
| Noisy advisories | ranking thresholds + local-task-first routing |
| Weak grounding | mandatory proof refs in payload |
| No actionability | mandatory "next command/check" field |
| Fuzzy errors | shared cross-cutting failure enum |

---

## 6) KPI dashboard for this plan

Track each checkpoint:
- memory failure classification coverage (% with non-empty kind)
- retrieval non-empty rate by mode
- MRR by mode
- stale retrieval rate
- advisory duplicate rate
- advisory evidence completeness rate
- advisory actionability rate
- fallback ratio (`fallback_emit` / all advisory events)
- sync target reliability per adapter

Initial baseline (current):
- fallback ratio: 312 / 481 = 64.9%
- advisory duplicate rate: 19%
- strict hybrid non-empty: 0.0

Target:
- fallback ratio < 30%
- duplicate rate < 8%
- strict hybrid_agentic non-empty > 90%

---

## 7) Immediate execution queue (start now)

1. Implement failure classifier + tests.
2. Patch strict retrieval gates and rerun strict A/B.
3. Add advisory evidence hash dedupe and metric logging.
4. Ship minimal trace payload fields (`session_id`, `scope`, `provider_path`, `error_kind`, `freshness_state`).
5. Run 5-prompt smoke sequence and capture before/after KPI snapshot.

---

## 8) Two-track execution (deduped)

You requested OpenClaw-first plus broader system improvements. This is the split:

## Track A (OpenClaw-first, P0/P1)
- A1: Shared failure taxonomy contract (`policy|auth|timeout|transport|no_hit|stale|unknown`)
- A2: Retrieval strict-gate fix for hybrid/hybrid_agentic collapse
- A3: Session/scope envelope parity (`session_id`, `actor_id`, `scope`, `memory_tier`, `provider_path`)
- A4: Advisory dedupe + evidence-first payload enforcement
- A5: Live/fallback/blocked/stale visibility in Pulse/OpenClaw surface

Primary KPI targets:
- strict hybrid_agentic non-empty > 90%
- advisory fallback ratio < 30%
- advisory duplicate rate < 8%

## Track B (Broader Spark cleanup + lightweighting)
- B1: Auto-tuner no-op churn cleanup (only write when values actually change)
- B2: Exposure stream volume reduction (sampling/dedup for sync-heavy noise)
- B3: Chip activation relevance tightening (reduce low-quality merge skip churn)
- B4: Sync target downgrade policy (optional target failures should not degrade core signal)
- B5: Artifact hygiene and stale operational state cleanup
- B6: DEPTH process-quality uplift (focus on process weakness in recent slices)

Primary KPI targets:
- no-op tune writes near zero
- lower exposures/minute with no recall regression
- lower `skipped_low_quality` rate in chip merge cycles
- optional adapter failures isolated from core health status

## Dedup matrix (shared work applied once)

| Shared item | Applies to Track A | Applies to Track B | Run once as |
|---|---|---|---|
| Failure taxonomy contract | Yes | Yes (diagnostics clarity) | `core.error_taxonomy` |
| Envelope/trace fields | Yes | Yes (cross-system observability) | `core.diagnostics_envelope` |
| Advisory dedupe machinery | Yes | Yes (noise reduction globally) | `advisory.dedupe_core` |
| Health status normalization | Yes | Yes | `ops.health_contract` |
| KPI checkpoint format | Yes | Yes | `ops.kpi_template` |

Execution rule:
- implement shared item once in core,
- consume in both tracks,
- avoid duplicate one-off patches.

---

## 9) Notes

- This is grounded in live runs and local runtime telemetry from this environment.
- For public-facing complaint links, build a separate complaint index with external issue URLs and quoted evidence.
