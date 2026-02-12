# Spark Intelligence: 2-Day Comprehensive Honest Assessment
Date: 2026-02-12
Scope window: 2026-02-10 to 2026-02-12
Owner: Spark Intelligence

## 1) Scope and evidence used
This assessment is based on:
- live runtime checks executed now (`scripts/status_local.py`, `scripts/status_openclaw_spark.ps1`)
- live memory retrieval A/B runs on real-user set
- targeted test runs executed now (`22 passed`)
- OpenClaw and Spark reports updated during this window
- git activity from 2026-02-10 onward
- AGENTS auto-learnings (DEPTH and system gaps)

## 2) What is working great right now

1. Core runtime stability is strong.
- `sparkd`, dashboard, meta_ralph, bridge_worker, scheduler, watchdog are healthy.
- queue is clear (`0`), no visible backlog pressure.

2. Retrieval architecture direction is correct.
- In relaxed comparison mode, `hybrid_agentic` wins with clear quality lift (MRR 0.285 vs 0.092 embeddings-only).
- This confirms the model/path design has real upside once strict gating is tuned.

3. Advisory engine observability and hardening improved.
- Structured advisory event/error logging was expanded and now includes error taxonomy fields in key paths.
- Fallback failure is now explicit (`fallback_emit_failed`) instead of silent.

4. Testing coverage for the new reliability layer is good.
- Targeted test suite passed: `tests/test_error_taxonomy.py`, `tests/test_memory_retrieval_ab.py`, `tests/test_advisor_effectiveness.py`, `tests/test_advisory_packet_store.py`.
- Result: `22 passed`.

5. Execution discipline improved in the last 2 days.
- Strong reporting cadence in `path-to-AGI/reports/`.
- Rapid iteration with rollback/guardrail thinking is visible in commit stream and run artifacts.

## 3) What is not working (honest)

1. Strict retrieval gate behavior was breaking hybrid paths; rescue patch is now shipped.
- Before fix: strict/default had `hybrid` and `hybrid_agentic` at `non_empty=0.0`.
- After fix: strict/default rerun shows non-empty retrieval and `hybrid_agentic` winner.
- Remaining risk: rescue quality must be monitored so recall gains do not reintroduce low-value noise.

2. Advisory system is still fallback-heavy and somewhat noisy.
- Baseline report shows high `fallback_emit` share and duplicate advisory text rate around `19%`.
- Trust impact: users see repetition and lower signal.

3. Memory reliability is still brittle at provider/auth boundary.
- Multiple reports show auth/provider readiness as a recurring blocker.
- User-visible symptom remains over-broad "blocked" behavior unless explicit taxonomy is fully propagated everywhere.

4. Spark Pulse operational consistency is unstable.
- It has been seen in both states within the same analysis window (running earlier, stopped in latest live check).
- This is an ops consistency issue even if core runtime is healthy.

5. External adapter reliability is uneven.
- Current status snapshots show some adapters consistently erroring while OpenClaw/exports succeed.
- Core quality gets obscured by optional-target failures in shared health views.

6. Spark Porch visibility is missing in this repo.
- No direct `Spark Porch` artifacts found in this codebase search.
- This is either a repo-boundary issue or missing integration telemetry; either way it is a blind spot.

## 4) Systems that need improvement (keep, but fix)

1. Memory retrieval system (highest priority):
- Keep `hybrid_agentic` as target direction.
- Fix strict-gate thresholds and session/scope envelope parity.
- Add freshness/state metadata and rejection reasons.

2. Advisory quality system:
- Add dedupe with evidence-hash cooldown.
- Require proof refs for every non-trivial advisory.
- Enforce one concrete next command/check per advisory.

3. Cross-cutting error contract:
- Continue rollout of shared taxonomy: `policy|auth|timeout|transport|no_hit|stale|unknown`.
- Ensure every retrieval/advisory failure emits `error_kind` + `error_code`.

4. Sync and health status model:
- Split health into `core` vs `optional` targets.
- Keep optional connector failures from degrading primary system trust.

5. DEPTH process quality:
- Keep pipeline; focus targeted training on weak lenses already identified (especially D3/Architect-style weaknesses).

## 5) Systems to clean up or remove for lightweight operation

1. Remove noise-first behavior, not capability:
- Reduce over-activation fan-out and low-value chip writes.
- Minimize no-op tune writes and duplicate exposure events.

2. De-prioritize unstable optional adapters until healthy:
- Downgrade optional failing targets from "active error spam" to "suppressed/degraded" state.
- Re-enable only after explicit re-auth/health criteria.

3. Keep one primary operator surface:
- Treat Pulse as primary.
- Keep legacy/secondary surfaces opt-in for debugging only.

4. Stop carrying duplicate patches for shared concerns:
- Apply taxonomy, envelope, dedupe, and KPI contracts once in core and consume everywhere.

## 6) Main gaps right now

1. Gap A (P1): strict retrieval collapse fixed; now requires quality monitoring and threshold tuning cleanup.
2. Gap B (P0): advisory dedupe and grounding are insufficient.
3. Gap C (P0): full end-to-end diagnostics trace is not yet user-visible.
4. Gap D (P1): provider/auth readiness remains too fragile operationally.
5. Gap E (P1): optional connector instability pollutes perceived health.
6. Gap F (P1): moderate-quality plateau in broader training loop still appears.
7. Gap G (P2): Spark Porch visibility gap in this repo boundary.

## 7) End-to-end system assessment (current)

Pipeline: ingest -> classify/learn -> retrieve -> advise -> emit -> feedback -> tune

1. Ingest/classify:
- Working and active; queue is healthy.
- Remaining issue is signal/noise ratio, not basic throughput.

2. Retrieve:
- Architecturally strong; strict-collapse rescue is in place.
- Remaining work is calibration of rescue thresholds to keep quality high as recall increases.

3. Advise:
- Engine works, emits guidance, and now has better structured events.
- Still too much fallback and repetition for high trust.

4. Emit/UI:
- Pulse availability inconsistency reduces operator confidence.

5. Feedback/tuning:
- Loop exists and has improved, but evidence/actionability enforcement is still incomplete.

Net: the loop is operational and improving, but quality reliability is constrained by three bottlenecks:
- rescue-path quality calibration (post strict-collapse fix),
- advisory trust quality,
- operator-facing transparency.

## 8) Deduped integrated execution plan (OpenClaw + broader Spark)

## Track A (OpenClaw first, direct user pain)
1. A1: Shared error taxonomy rollout (in progress)
2. A2: Strict retrieval gate fix + rerun strict A/B
3. A3: Session/scope envelope parity across direct/bridge
4. A4: Advisory dedupe + evidence-first payload contract
5. A5: Live/fallback/blocked/stale status visibility in operator surface

## Track B (Broader Spark cleanup/lightweighting)
1. B1: Noise suppression in chip/exposure flow (done)
2. B2: Optional adapter downgrade policy and clearer health split (done)
3. B3: Artifact hygiene and compaction cadence (done)
4. B4: DEPTH weak-lens targeted uplift (done)

## Shared items (run once)
1. `core.error_taxonomy`
2. `core.diagnostics_envelope`
3. `advisory.dedupe_core`
4. `ops.health_contract`
5. `ops.kpi_template`

## 9) What was already executed in this session

1. Added shared taxonomy module:
- `lib/error_taxonomy.py`

2. Fixed strict retrieval collapse with bounded empty-result rescue:
- `lib/semantic_retriever.py`
- strict/default real-user rerun winner changed to `hybrid_agentic` (no hybrid empty collapse).

3. Wired retrieval benchmark to shared classifier:
- `benchmarks/memory_retrieval_ab.py`

4. Wired advisory engine events to taxonomy/error fields:
- `lib/advisory_engine.py`

5. Added advisory text-fingerprint dedupe cooldown in engine/state:
- `lib/advisory_engine.py`
- `lib/advisory_state.py`

6. Added evidence-first advisory payload fields:
- `lib/advisory_engine.py` now writes `proof_refs` + `evidence_hash` into packet `advice_items`.

7. Added sync health contract split for core vs optional adapters:
- `lib/sync_tracker.py` now emits `core_ok/core_error/optional_error/core_healthy`.

8. Added diagnostics envelope fields for end-to-end advisory tracing:
- `lib/advisory_engine.py` now emits `session_id`, `trace_id`, `session_context_key`, `scope`, `provider_path`, `source_counts`, `missing_sources` in engine events.

9. Added operator-facing delivery badge state in advisory status:
- `lib/advisory_engine.py` now derives and exposes `live|fallback|blocked|stale` from recent events.

10. Added actionability enforcement for emitted advisories:
- if advisory text lacks a concrete command/check, engine appends `Next check: \`<command>\``.

11. Added taxonomy + dedupe/retrieval/evidence/ops tests:
- `tests/test_error_taxonomy.py`
- `tests/test_semantic_retriever.py`
- `tests/test_advisory_engine_dedupe.py`
- `tests/test_advisory_engine_evidence.py`
- `tests/test_sync_tracker_tiers.py`
- `tests/test_advisory_dual_path_router.py`

12. Validation runs:
- `python -m pytest tests/test_semantic_retriever.py tests/test_memory_retrieval_ab.py -q`
- `python -m pytest tests/test_advisory_engine_dedupe.py tests/test_advisor_effectiveness.py tests/test_advisory_packet_store.py tests/test_error_taxonomy.py tests/test_memory_retrieval_ab.py tests/test_semantic_retriever.py -q`
- `python -m pytest tests/test_advisory_engine_evidence.py tests/test_advisory_engine_dedupe.py tests/test_advisory_packet_store.py tests/test_advisor_effectiveness.py -q`
- `python -m pytest tests/test_sync_tracker_tiers.py tests/test_advisory_engine_evidence.py tests/test_advisory_engine_dedupe.py tests/test_semantic_retriever.py -q`
- `python -m pytest tests/test_error_taxonomy.py tests/test_memory_retrieval_ab.py tests/test_semantic_retriever.py tests/test_advisory_engine_dedupe.py tests/test_advisory_engine_evidence.py tests/test_advisory_dual_path_router.py tests/test_advisory_packet_store.py tests/test_advisor_effectiveness.py tests/test_sync_tracker_tiers.py -q`
- Result: all listed targeted runs passed (known Windows pytest atexit temp-permission warning remains after success).

13. Live retrieval rerun artifacts:
- `benchmarks/out/memory_retrieval_ab_real_user_2026_02_12_default_live_refresh_report.md`
- `benchmarks/out/memory_retrieval_ab_real_user_2026_02_12_relaxed_live_refresh_report.md`
- `benchmarks/out/memory_retrieval_ab_real_user_2026_02_12_default_after_rescue_report.md`

14. Wired advisory delivery visibility into operator surfaces:
- `dashboard.py` mission and ops payloads now include compact advisory status with `delivery_badge`.
- mission and ops UI now render explicit advisory delivery state, reason, age, and queue/prefetch context.

15. Added dashboard advisory status tests:
- `tests/test_dashboard_advisory_status.py`

16. Extended delivery badge visibility into Pulse/OpenClaw surfaces:
- external `vibeship-spark-pulse` now normalizes and exposes advisory delivery in `/api/status` and `/api/advisory`.
- Pulse advisory UI now renders delivery state (`live|fallback|blocked|stale`) with reason/age/event/mode.

17. Added auto-tuner no-op churn cleanup:
- `lib/auto_tuner.py` now skips recommendation and boost writes when values do not change.

18. Added exposure write-volume reduction for sync-heavy paths:
- `lib/exposure_tracker.py` now dedupes/caps `sync_context`, `sync_context:project`, and `chip_merge` writes.

19. Tightened chip merge relevance and skip-noise suppression:
- `lib/chip_merger.py` now uses timestamp-independent content hashes and low-quality cooldown suppression.
- `lib/bridge_cycle.py` now runs stricter chip merge confidence/quality thresholds and surfaces cooldown skip stats.

20. Added runtime artifact hygiene in bridge cycle:
- new `lib/runtime_hygiene.py` removes stale heartbeat files, stale PID state, and stale temp artifacts.
- bridge cycle now runs this hygiene step each loop.

21. Added DEPTH weak-lens targeting upgrades:
- `lib/depth_trainer.py` now tracks ordered weak lens IDs and generates targeted drill topics for weak slices.

22. Added validation tests for Track B upgrades:
- `tests/test_exposure_tracker.py`
- `tests/test_chip_merger.py`
- `tests/test_runtime_hygiene.py`
- `tests/test_depth_topic_discovery.py`

## 10) Decision summary

1. Keep and invest:
- hybrid-agentic retrieval direction,
- advisory engine core,
- current structured iteration/reporting cadence.

2. Fix immediately:
- full evidence-first payload/actionability requirements,
- full taxonomy propagation and trace visibility.

3. Clean up/lightweight:
- optional failing adapter noise,
- low-value chip/exposure churn,
- duplicate system surfaces/processes that are not contributing measurable value.
