# Advisory Integration Audit (2026-02-06)

## Scope
Audit what predictive advisory components are actually integrated, what is active at runtime, and how to test/observe them.

## What Is Integrated Now

### Core Predictive Advisory Stack
- `lib/advisory_engine.py`
  - Pre-tool route orchestration: live advisor or packet cache route.
  - Gate + synth + emit flow.
  - Packet persistence and prefetch queue enqueue.
- `lib/advisory_gate.py`
  - Authority and emission decisions (`warning/note/whisper/silent`).
- `lib/advisory_synthesizer.py`
  - AI/programmatic advisory synthesis with mode/timeout/cache controls.
- `lib/advisory_emitter.py`
  - Stdout emission bridge into hook feedback context.
- `lib/advisory_packet_store.py`
  - Packet cache, relaxed/exact lookup, prefetch queue, invalidation.
- `lib/advisory_state.py`
  - Session intent/phase/tool history/shown advice tracking across hook processes.
- `lib/advisory_intent_taxonomy.py`
  - Intent family + task plane inference for routing/context keys.
- `lib/advisory_memory_fusion.py`
  - Multi-source retrieval bundle for advisory lineage.

### Hook Wiring (Active)
- `hooks/observe.py`
  - `PreToolUse` calls `advisory_engine.on_pre_tool(...)`.
  - `PostToolUse` and `PostToolUseFailure` call `advisory_engine.on_post_tool(...)`.
  - `UserPromptSubmit` calls `advisory_engine.on_user_prompt(...)`.
  - Legacy advisor fallback remains in place if engine path throws.

## Fixes Applied In This Iteration

### Attribution Integrity
- Removed cross-tool Task fallback as default in recent advice lookup (`lib/advisor.py` tests cover this).
- Added robust post-tool trace recovery path and lookup preference for unresolved pre-tool traces.
- Implicit feedback now links recent advice using trace when available (prevents wrong attribution joins).

### Gate Data Integrity
- Production gate loading now normalizes/repairs invalid advisor effectiveness counters on read.
- Meta-Ralph outcome persistence now merges on-disk + in-memory records to prevent concurrent writer clobbering of actionable/strict attribution samples.

### Regression Coverage Added
- `tests/test_advisor_effectiveness.py`
  - Prevent Task fallback cross-linking by default.
- `tests/test_advisory_state.py`
  - Verify trace recovery logic.
- `tests/test_production_loop_gates.py`
  - Updated to deterministic effectiveness metrics helper.
- `tests/test_meta_ralph.py`
  - Added concurrent writer merge regression to preserve outcome records.

## Current Live Status (Observed)
- Strict attribution pipeline code path is operational (probe passes).
- Queue backpressure is healthy (queue depth currently low).
- Latest production loop snapshot is `READY (13/13 passed)` with strict attribution gates passing (`strict_with_outcome=10`, `strict_trace_coverage=50%`).
- Because these are live counters, readiness can regress if sample quality/volume drops; keep monitoring via report + dashboard.

## How To Test Right Now

### 1) Isolated strict attribution smoke (no live data mutation)
```bash
python scripts/strict_attribution_smoke.py
```

### 2) Live production gates
```bash
python scripts/production_loop_report.py
```

### 3) Pulse Advisory tab/API
- `GET /api/advisory`
- `POST /api/advisory/probe` (runs strict attribution smoke and returns result)

## Notes
- If low-sample gate failures reappear, treat them first as a data-coverage issue (before debugging queue/trace policy).
- Advisory tab exposes sample sufficiency and strict trace metrics so operators can quickly distinguish runtime breakage vs coverage gaps.
