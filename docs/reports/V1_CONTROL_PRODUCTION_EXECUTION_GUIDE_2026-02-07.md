# V1 Control Production Execution Guide (Detailed)

Date: 2026-02-07  
Purpose: turn Spark into a reliable, high-utility **controlled V1 production robot** with a repeatable tuning loop.

## 1) Executive Verdict (Current)

Current state is strong on correctness and attribution integrity, but not yet strong enough on advisory latency predictability and user-visible usefulness consistency.

Estimated control-readiness score right now: **8.2 / 10**.

Why not 9.5 yet:

1. latency tail still spikes on live advisory path;
2. packet-route exists but live-route is still too high in recent windows;
3. emission usefulness loop is not explicit in UI (no direct user feedback controls yet);
4. several important tuneable families are still not first-class in Pulse tune UX/runtime apply.

## 2) Baseline Snapshot (Measured 2026-02-07)

## A) Production loop gates

`python scripts/production_loop_report.py`

- status: `READY (13/13 passed)`
- actionable_retrieved: `9`
- acted_on: `9`
- strict_with_outcome: `9`
- strict_trace_coverage: `100%`

## B) Advisory API (Pulse)

`GET /api/advisory`

- insufficient_samples: `false`
- actionable_retrieved: `14`
- acted_on: `14`
- strict_with_outcome: `13`
- strict_trace_coverage: `92.86%`
- warnings: `[]`

## C) Engine timing + route split (recent log windows)

`~/.spark/advisory_engine.jsonl` analysis:

- last 50 events: p50 `114.4ms`, p95 `8251.1ms`, avg `2500.3ms`
- last 50 route split: `live=19`, `packet=31` (about 38% live)
- last 50 emit rate: `38%`

Interpretation:

1. most packet-path events are fast;
2. live path still creates extreme p95 spikes;
3. usefulness exposure is still low-to-moderate due high `no_emit` share.

## D) Runtime tune apply status

`GET /api/tuneables/status` currently showed:

- `apply_available=true`
- `apply_attempted=false`

Meaning: tuneables exist on disk, but current Pulse process has not yet applied a save in this runtime session.

## 3) Review of `V1_CONTROL_PRODUCTION_READINESS_GUIDE_2026-02-06.md`

What is correct:

1. A3 (prefetch worker) and packet effectiveness reranking are still top leverage.
2. Controlled rollout and strict go/no-go gates are the right operating model.
3. One-change-per-window tuning discipline is correct.

What needs tightening:

1. add explicit **runtime apply verification** step each morning (`/api/tuneables/status`);
2. add explicit **latency-tail metric capture** from engine logs, not only gate metrics;
3. add explicit **user feedback capture feature** (helpful/not helpful/too noisy), otherwise usefulness loop is slow;
4. include a concrete **Tuneables coverage gap list** (what is tuneable in docs but not in Pulse tune UX).

## 4) Tomorrow Morning Checklist (Step-by-Step)

## 0. Session setup (10 min)

1. Start Spark components and Pulse.
2. Open Pulse tabs: `System`, `Tune`, `Advisory`.
3. Confirm `GET /api/advisory` is healthy (no warnings).

## 1. Baseline capture (15 min)

Run:

1. `python scripts/production_loop_report.py`
2. advisory log stats script for p50/p95/route split (last 50 and 100)
3. `python scripts/strict_attribution_smoke.py`

Record values in a daily runbook row:

1. gate pass count
2. p50/p95 advisory latency
3. packet/live route split
4. emit rate
5. strict sample count

## 2. Force runtime tune apply verification (5 min)

1. In Pulse Tune tab, click `Save` once (even if no value changed).
2. Verify `/api/tuneables/status`:
   - `apply_attempted=true`
   - `applied` list non-empty
   - `warnings` empty
3. If scheduler settings changed, confirm `restart_required` includes `scheduler`.

## 3. Control profile for latency safety (15 min)

Set/confirm:

1. `synthesizer.mode=programmatic`
2. `synthesizer.ai_timeout_s=1.5` (or lower)
3. `advisor.max_items=6` (reduce overload/noise during control phase)
4. keep `meta_ralph.strict_attribution_require_trace=true`

Why:

1. current p95 spikes are mostly live/AI-route related;
2. control V1 should prioritize predictability over richness first.

## 4. Run fixed scenario pack (30-45 min)

Run the same scenarios every day:

1. auth/security
2. test/debug
3. deploy/ops
4. orchestration/task

For each scenario record:

1. first advisory latency
2. route type (`packet_exact`, `packet_relaxed`, `live`)
3. emitted or no_emit
4. operator judgment (`helpful`/`not helpful`/`too noisy`)

## 5. One-change tuning window (30 min)

Only change one parameter family:

1. route coverage knobs, or
2. latency knobs, or
3. usefulness knobs.

Never change all three in one window.

## 6. End-of-day decision (10 min)

1. Keep or rollback change based on measurable delta.
2. Update daily baseline table.
3. Queue next day’s single hypothesis.

## 5) Parameter Iteration Plan (Exact Order)

## Phase A: Route coverage first

Goal: reduce live-route share.

Primary controls:

1. implement A3 worker (mandatory);
2. keep prefetch enabled (`SPARK_ADVISORY_PREFETCH_QUEUE=1`);
3. ensure packet TTL not too short for active sessions.

Target:

1. packet-route >= 75%
2. live-route <= 15%

## Phase B: Latency tail second

Goal: p95/p99 stability.

Primary controls:

1. `synthesizer.mode=programmatic` for control baseline;
2. `synthesizer.ai_timeout_s` low ceiling;
3. only allow `auto` after route coverage improves.

Target:

1. p95 <= 1800ms
2. p99 <= 2500ms

## Phase C: Usefulness and noise third

Goal: users actually feel value.

Primary controls:

1. `advisor.max_items`, `advisor.min_rank_score`, `advisor.min_reliability`
2. advisory gate tuning (requires new tuneable surface, see section 7)
3. packet effectiveness rerank (Feature 2)

Target:

1. emit rate 45-70% (context dependent)
2. helpful/acted_on >= 55%
3. too-noisy feedback < 10%

## 6) Two Features to Build Next (for Real User Value)

## Feature 1: Advisory Feedback Controls in Pulse (Immediate)

Add per-advice actions in Advisory tab:

1. `Helpful`
2. `Not Helpful`
3. `Too Noisy`

Store feedback and connect it to:

1. packet ranking,
2. source attribution quality,
3. gate suppression logic.

Why this is high leverage:

1. creates fast usefulness signal loops;
2. gives users visible agency immediately;
3. makes tuning objective, not guesswork.

## Feature 2: A3 Prefetch Worker + Packet Effectiveness Rerank

Implement from backlog:

1. `lib/advisory_prefetch_planner.py`
2. `lib/advisory_prefetch_worker.py`
3. packet score fields (`effectiveness_score`, `usage_count`) in packet metadata

Why this is high leverage:

1. increases packet-hit and lowers live latency;
2. improves advisory quality over time;
3. creates real predictive behavior users can feel.

## 7) Tuneables Coverage Gaps (Add These Sections)

Current Pulse Tune covers many sections, but these high-impact areas are still missing or partial.

## A) `advisory_engine` section (new)

Add:

1. `max_ms`
2. `include_mind_in_memory`
3. `enable_prefetch_queue`
4. `emit_enabled`
5. `emit_max_chars`
6. `emit_format`

## B) `advisory_gate` section (new)

Add:

1. `max_emit_per_call`
2. `tool_cooldown_s`
3. `advice_repeat_cooldown_s`
4. authority thresholds (`warning`, `note`, `whisper`)
5. phase relevance multipliers

Why: current no_emit share is high and gate behavior is not tunable from Pulse.

## C) `advisory_packet_store` section (new)

Add:

1. `packet_ttl_s`
2. `max_index_packets`
3. relaxed lookup score weights (tool match, intent match, plane match, recency)

Why: route quality and freshness are central to predictive feel.

## D) `memory_gate` full weight surface (complete)

Current Pulse tunes only subset. Add:

1. `weight_recurrence`
2. `weight_evidence`

Why: this directly controls memory quality/noise balance.

## E) `request_tracker` section (new)

Add:

1. `max_pending`
2. `max_completed`
3. `max_age_seconds`

Why: affects learning backlog health and stale-request behavior.

## F) `memory_capture` section (new)

Add:

1. `auto_save_threshold`
2. `suggest_threshold`
3. `max_capture_chars`

Why: this is core to user memory quality and currently not operator-tunable from Pulse.

## G) `queue` section (new)

Add:

1. `max_events`
2. `tail_chunk_bytes`

Why: directly impacts throughput/backpressure and historical observability.

## 8) Plug-In Correctness Checklist (When Tuning)

Use this every time a setting changes:

1. Save in Pulse Tune.
2. Check `/api/tuneables/status`.
3. Confirm key appears in `applied`.
4. Confirm no warnings.
5. If key is scheduler-related, restart scheduler.
6. Re-run:
   - `python scripts/production_loop_report.py`
   - advisory latency/route snapshot
7. Keep/rollback based on measured delta only.

## 9) Go/No-Go for 9.5 Controlled Score

Ship at 9.5 only if all hold for 3 consecutive days:

1. production gates remain `13/13`.
2. p95 advisory latency <= 1200ms, p99 <= 1800ms.
3. packet-route >= 75%, live-route <= 10-15%.
4. helpful/acted_on >= 55%.
5. no critical incidents or safety regressions.

If any fail:

1. rollback last change,
2. hold rollout scope,
3. rerun fixed scenario pack,
4. resume with one-parameter iteration.

