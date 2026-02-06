# V1 Controlled Production Readiness Guide

Date: 2026-02-06  
Start date for this plan: 2026-02-07 (Saturday)

## 1) Honest Current State

What is strong right now:

1. Runtime and tests are stable:
   - local test suite: 334 passed.
2. Advisory foundation is wired in live hooks:
   - `PreToolUse` -> `on_pre_tool`
   - `PostToolUse`/`PostToolUseFailure` -> `on_post_tool`
   - `UserPromptSubmit` -> `on_user_prompt`
3. Pre-v1 foundation shipped:
   - packet store,
   - dual-path advisory routing,
   - deterministic intent taxonomy,
   - memory fusion bundle.

What is not production-strong yet:

1. Latency tail is still high whenever route falls back to live AI hot path.
2. Predictive path has foundation but not full async refinement worker.
3. Packet hit behavior exists, but packet usefulness/emission quality is inconsistent.
4. Limited operator observability for rapid tuning loops.

## 2) Production Goal Definition (Target = 9.5/10 Controlled)

Controlled production means:

1. Limited cohort only.
2. Strict SLO enforcement.
3. Fast rollback path.
4. Daily tuning loop with metrics.

Scorecard target for 9.5/10 controlled readiness:

1. SLO and reliability (35%)
   - advisory hook p95 <= 1200ms in cohort.
   - advisory hook p99 <= 1800ms.
   - error rate < 0.5%.
2. User-facing usefulness (25%)
   - advisory shown on applicable moments >= 70%.
   - acted-on or explicitly-helpful >= 50%.
3. Predictive value (20%)
   - packet-route usage >= 70%.
   - first-tool packet availability >= 60%.
4. Safety and determinism (10%)
   - deterministic fallback success = 100%.
   - no safety regressions from advisory path.
5. Ops readiness (10%)
   - dashboard/telemetry enough to detect and fix regressions same day.

## 3) Two Features You Should Build Next (High Leverage)

Feature 1 (mandatory): Background prefetch worker (A3).

1. Queue is already being filled from `on_user_prompt`.
2. Without a worker, predictive packet coverage stalls.
3. Outcome:
   - higher packet hit rate,
   - fewer live hot-path AI calls,
   - lower latency tails.

Feature 2 (mandatory): Packet effectiveness scoring and rerank.

1. Add per-packet `effectiveness_score` and `usage_count`.
2. Update in `on_post_tool` using outcome polarity.
3. Use score in relaxed lookup ranking.
4. Outcome:
   - better advisory quality over time,
   - less stale/noisy packet selection.

## 4) Day-by-Day Execution Plan

## Day 1 (2026-02-07): Stabilize hot path and telemetry

Checklist:

1. Verify hook wiring includes `PreToolUse`.
2. Set controlled-production defaults (see section 5).
3. Run baseline measurement for 100 advisory events.
4. Confirm route split and p95 from fresh logs.
5. Confirm fallback path still emits with AI disabled.

Exit criteria:

1. p95 <= 2500ms on baseline controlled profile.
2. packet-route >= 40%.
3. no crash/regression in hooks.

## Day 2-3: Build/enable Feature 1 (prefetch worker)

Checklist:

1. Implement worker skeleton with bounded concurrency and pause on load.
2. Consume `prefetch_queue.jsonl` and generate tool-specific packets.
3. Generate deterministic packet first, optional AI refine second.
4. Add worker health/status metrics.
5. Add tests for planner + worker + pause/resume behavior.

Exit criteria:

1. packet-route >= 60%.
2. live-route <= 20%.
3. p95 <= 1800ms.

## Day 4-5: Build/enable Feature 2 (effectiveness rerank)

Checklist:

1. Add packet scoring fields and update path from outcomes.
2. Downrank packets linked to negative outcomes.
3. Boost packets linked to successful outcomes.
4. Add stale-toxic packet invalidation rule for major edits/writes.
5. Add tests for score update and ranking behavior.

Exit criteria:

1. useful-advice rate improves by >= 15% from Day 1 baseline.
2. no_emit rate drops on applicable events.
3. packet reuse quality improves in replay scenarios.

## Day 6-7: Controlled cohort rollout

Checklist:

1. Enable for limited user/project cohort only.
2. Run daily SLO and utility reports.
3. Capture explicit feedback (`helpful`, `not helpful`, `too noisy`).
4. Freeze risky config knobs for 24h intervals to avoid confounded tuning.

Exit criteria:

1. 3 consecutive days meeting SLO + usefulness thresholds.
2. no critical incidents.

## 5) Controlled-Production Configuration Baseline

Apply these defaults for controlled V1:

1. Advisory engine:
   - `SPARK_ADVISORY_ENGINE=1`
   - `SPARK_ADVISORY_MAX_MS=4000`
   - `SPARK_ADVISORY_PREFETCH_QUEUE=1`
   - `SPARK_ADVISORY_INCLUDE_MIND=0`
2. Emission:
   - `SPARK_ADVISORY_EMIT=1`
   - `SPARK_ADVISORY_MAX_CHARS=500`
3. Synthesis mode (initially stability-first):
   - `SPARK_SYNTH_MODE=programmatic` for first baseline window.
4. After worker is live and stable:
   - switch to `SPARK_SYNTH_MODE=auto`,
   - keep tight timeout `SPARK_SYNTH_TIMEOUT=1.5` to `2.0`.

Recommended tuneables additions:

```json
{
  "synthesizer": {
    "mode": "programmatic",
    "preferred_provider": "ollama",
    "ai_timeout_s": 1.8,
    "cache_ttl_s": 120,
    "max_cache_entries": 50
  }
}
```

## 6) Measurement and Tuning Loop (Daily)

Run this loop once in the morning and once end-of-day.

Step A: collect advisory metrics.

1. total events
2. p50/p90/p95 latency
3. route split (`packet_exact`, `packet_relaxed`, `live`)
4. emit rate / no_emit rate
5. packet freshness and queue depth

Step B: decide one controlled adjustment only.

1. Adjust one parameter family per window.
2. Do not change synthesis, gating, and ranking all at once.

Step C: replay fixed scenario set.

1. auth/security scenario
2. testing/debug scenario
3. deployment/ops scenario
4. orchestration/task-management scenario

Step D: compare vs previous window and keep or rollback.

## 7) Parameter Iteration Order (Do In This Order)

1. Route coverage knobs:
   - maximize packet-route share first.
2. Hot-path latency knobs:
   - synthesis mode/timeout.
3. Usefulness knobs:
   - gate thresholds and emission cadence.
4. Quality knobs:
   - packet ranking/effectiveness.

Do not start with model swaps before route coverage is fixed.

## 8) User-Value Validation (What users should feel)

A user should feel:

1. Advice appears quickly and not too often.
2. Advice is specific to what they are doing now.
3. Advice improves after failures and repeated patterns.

Practical acceptance checks:

1. First tool call in a session gets baseline guidance in under 400ms.
2. After one failure, next similar tool action receives more targeted guidance.
3. Repeated noisy advice gets suppressed/downranked within same session.

## 9) Risk Register (Current)

1. Hot-path live fallback can still spike latency if packet miss.
2. No full async refine worker yet means predictive quality plateau.
3. Lack of packet outcome ranking can keep low-value packets active.
4. Hook misconfiguration without `PreToolUse` kills predictive feel.

## 10) Go/No-Go Gates for Controlled V1

Go controlled cohort when all are true:

1. 3-day rolling p95 <= 1200ms.
2. packet-route >= 70%.
3. live-route <= 10%.
4. useful/acted-on >= 50%.
5. no critical regressions from advisory path.

If any fail:

1. remain in controlled mode,
2. rollback last tuning change,
3. re-run fixed replay pack before next change.

## 11) Commands to Use Daily

1. Test suite:
   - `python -m pytest -q`
2. Advisory-focused tests:
   - `python -m pytest -q tests/test_advisory_packet_store.py tests/test_advisory_intent_taxonomy.py tests/test_advisory_memory_fusion.py tests/test_advisory_dual_path_router.py`
3. Local status:
   - `python scripts/status_local.py`
4. Stress scenarios:
   - `python scripts/local_ai_stress_suite.py`

## 12) Final Recommendation

Ship controlled V1 now only after Day 1 baseline + configuration hardening.

To reach 9.5/10 controlled readiness, the fastest path is:

1. implement prefetch worker,
2. implement packet effectiveness rerank,
3. run strict daily measurement loop for one week.
