# Ralph Iteration Optimization Audit

Date: 2026-02-07  
Scope: live system audit with bounded CPU/memory loops

## 1) What was run (bounded loops, no heavy leak risk)

All loops were intentionally low-cost:

1. `python scripts/production_loop_report.py`
2. `python scripts/status_local.py`
3. Meta-Ralph stats/tuneables/deep analysis via in-process one-shot scripts.
4. Advisory latency/route parsing from `~/.spark/advisory_engine.jsonl` (tail analytics).
5. One bounded model stress pass:
   - `python scripts/local_ai_stress_suite.py --repeats 1 --live-scenarios 2 ...`
6. Storage hygiene dry-run only:
   - `python scripts/compact_chip_insights.py --keep-lines 2000`

No continuous loops or unbounded scans were executed.

## 2) Current state snapshot

## 2.1 Core production loop status

- Gate status: READY (13/13 passed)
- retrieval_rate: 113.1%
- acted_on_rate: 55.4%
- strict_trace_coverage: 70.3%
- strict_effectiveness_rate: 94.3%
- quality_rate: 44.5%
- queue_depth: 0

Interpretation:

1. Core self-learning loop is healthy.
2. This is a strong base for controlled production.

## 2.2 Service/runtime health

All main services were healthy and running:

1. sparkd
2. dashboard
3. pulse
4. meta_ralph
5. bridge_worker
6. scheduler
7. watchdog

Queue and validation backlogs were low.

## 2.3 Meta-Ralph loop health

- total_roasted: 737
- pass_rate/quality_rate: 44.5%
- reject_rate: 3.5%
- outcome effectiveness: 96.0%
- tuneables analysis: no threshold issue detected.

Interpretation:

1. Ralph loop is not the current bottleneck.
2. Quality gating is in a good band.

## 2.4 Advisory path bottleneck (critical)

From route-tagged advisory events:

1. `live + emitted`:
   - median ~7130.6ms
   - p95 ~10073.5ms
2. `packet_* + no_emit`:
   - median ~102.7ms
   - p95 ~479.2ms
3. packet route share: ~61%

Interpretation:

1. Packet path is fast.
2. Live emitted path is still too slow for V1 UX.
3. Current usefulness score is latency-capped.

## 2.5 Model stress quick pass (bounded)

Quick run (`9 scenarios x 3 models x 1 repeat`):

1. `phi4-mini`:
   - intelligence avg: 84.78
   - usefulness avg: 81.89
   - p95 latency: 4109.98ms
2. `qwen2.5-coder:3b`:
   - intelligence avg: 66.56
   - usefulness avg: 66.78
   - p95 latency: 5751.64ms
3. `llama3.2:3b`:
   - unstable in this run (errors/timeouts),
   - poor strict pass in this configuration.

Interpretation:

1. `phi4-mini` remains best quality profile.
2. Hot-path AI must still be constrained by routing and budgets.

## 2.6 Storage/bloat findings (leak risk)

Top bloat zones:

1. `~/.spark/logs`: ~35.1MB
2. `~/.spark/chip_insights`: ~34.8MB
3. `~/.spark/exposures.jsonl`: ~16.6MB
4. `~/.spark/advisor`: ~15.8MB

Compaction dry-run impact:

- chip insights lines: `38993 -> 18769` (about 52% reduction possible)

## 3) Usefulness score (primary metric)

Audit usefulness score (0-10): **6.2 / 10**

Why not higher:

1. Core learning quality is good.
2. Advisory latency tail drags user-perceived value down.
3. Packet route exists but emits too little useful guidance in many events.

## 4) Biggest gaps (ranked by impact)

## Gap 1: Live advisory emit latency tail

Impact: very high  
Current symptom: `live+emitted` p95 ~10s.

Use current system first:

1. Set synthesizer hot path to deterministic-first during controlled rollout:
   - `synthesizer.mode = programmatic`
2. Only enable AI synthesis in bounded windows for measured cohorts.

Expected usefulness gain: +1.8 to +2.8 points.

## Gap 2: Packet route often no-emits

Impact: very high  
Current symptom: high `packet_* + no_emit`.

Root cause observed in gating math:

1. Example packet advice with `confidence=0.6` and `context_match=0.8` gives score `0.48`.
2. Gate threshold for `note` is `0.50`.
3. Result becomes `whisper` (not emitted).

Use current system first:

1. Raise packet default confidence floor to >=0.70 for baseline packet rows.
2. Ensure baseline packets are not created with low confidence that guarantees suppression.
3. If packet path no-emits, perform bounded fallback to live deterministic synth (not AI-first).

Expected usefulness gain: +1.0 to +1.8 points.

## Gap 3: Over-reliance on old mixed advisory log stats

Impact: medium-high  
Current symptom: raw 500-event history blends pre-foundation and foundation paths.

Use current system first:

1. Track and report route-segmented SLOs:
   - `live+emitted`
   - `packet_exact+emitted`
   - `packet_relaxed+emitted`
2. Use segment SLOs for tuning decisions, not aggregate only.

Expected usefulness gain: +0.4 to +0.8 points.

## Gap 4: Telemetry bloat risk over long sessions

Impact: medium  
Current symptom: logs/chip insights growth can degrade long-term stability.

Use current system first:

1. Schedule chip insight compaction.
2. Add/verify log rotation for dashboard/pulse/semantic logs.
3. Keep heavy scans out of hooks.

Expected usefulness gain: +0.2 to +0.5 points (indirect, but stabilizes long runs).

## 5) Tuning plan using existing components first

## Step A: Hot-path latency hardening (no new feature)

1. Set:
   - `synthesizer.mode = programmatic`
   - keep `ai_timeout_s <= 1.8` for controlled optional windows.
2. Validate p95 over next 100 advisory events.
3. Keep this stable for one day before next knob.

## Step B: Packet usefulness lift (small code tuning, existing path)

1. Packet confidence floor and baseline confidence calibration.
2. Packet no-emit fallback to bounded deterministic live guidance.
3. Re-measure:
   - packet emitted rate,
   - no_emit rate,
   - acted_on rate.

## Step C: Route-aware tuning loop

1. Tune by route segment, not aggregate.
2. Only one change per window.
3. Keep rollback rule: revert if p95 or usefulness regresses.

## Step D: Memory and log hygiene

1. Run chip compact weekly (or daily in high-volume periods).
2. Rotate large logs.
3. Monitor top file growth weekly.

## 6) Only two “new” additions if needed

Use only if existing tuning above plateaus.

1. Background prefetch worker (consume already-queued jobs).
2. Packet effectiveness rerank (downrank low-value packets over time).

These two are the minimum feature adds with high ROI.

## 7) Target score progression

Realistic progression if executed cleanly:

1. Current: 6.2 / 10
2. After Step A: 7.8 to 8.6 / 10
3. After Step B: 8.8 to 9.3 / 10
4. After prefetch + packet rerank: 9.3 to 9.6 / 10 (controlled production target)

## 8) What to do next (tomorrow morning)

1. Apply Step A config.
2. Run 100-event route-segmented advisory measurement.
3. Apply Step B packet confidence/no-emit tuning.
4. Re-run advisory tests + production loop report.
5. Freeze config for 24h and compare usefulness deltas.
