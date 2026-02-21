# Advisory Phase-2 Dedupe Rollout (Observation-First)

Status: `draft`  
Scope: remove duplicate advisory accounting paths safely, without abrupt behavior changes.

## Goal

Reduce duplicate outcome accounting between `advisory_engine` and legacy `advisor` paths while preserving advisory quality and reliability.

## Non-Goals

- No immediate runtime path removal.
- No large refactor in a single release.
- No metric schema reset.

## Why This Needs a Controlled Rollout

Current runtime has overlapping advisory/outcome behaviors in some hook and bridge flows. Turning one path off abruptly can distort:

- advice-helped attribution
- Meta-Ralph outcome linkage
- packet effectiveness counters
- operator-facing delivery health

## Guardrail Principles

1. Measure before mutating.
2. Introduce flags with conservative defaults.
3. Gate each phase on data quality thresholds.
4. Keep rollback to one env var flip.

## Proposed Flags (Phase-2)

- `SPARK_PHASE2_OBSERVE_ONLY=1`
- `SPARK_PHASE2_LOG_DUAL_PATH_DIFF=1`
- `SPARK_PHASE2_DISABLE_LEGACY_OUTCOME=0`
- `SPARK_PHASE2_DISABLE_LEGACY_FALLBACK=0`
- `SPARK_PHASE2_DISABLE_LEGACY_ITEM_FEEDBACK=0`

Note: defaults above are intentionally no-op from behavior perspective.

## Rollout Phases

### Phase 0: Baseline

- Capture 7+ days of current behavior.
- Snapshot:
  - delivery badge distribution (`live|fallback|blocked|stale`)
  - outcome counts by source
  - advice-helped rate
  - packet hit/emit ratio

Exit criteria:
- stable daily volumes (no major incident periods).

### Phase 1: Observation Instrumentation

- Enable only observation flags.
- Log diff records between engine-attributed outcomes and legacy-attributed outcomes.
- Do not disable any path.

Exit criteria:
- dual-path diff report is complete for at least 3 full working days.

### Phase 2: Disable Legacy Item-Level Feedback

- Set `SPARK_PHASE2_DISABLE_LEGACY_ITEM_FEEDBACK=1`.
- Keep fallback and coarse legacy outcome reporting enabled.

Exit criteria:
- no drop in delivery quality metrics beyond agreed band.

### Phase 3: Disable Legacy Coarse Outcome Reporting

- Set `SPARK_PHASE2_DISABLE_LEGACY_OUTCOME=1`.
- Keep legacy fallback retrieval for safety.

Exit criteria:
- engine-only outcome linkage remains stable and actionable.

### Phase 4: Disable Legacy Fallback (Optional)

- Set `SPARK_PHASE2_DISABLE_LEGACY_FALLBACK=1`.
- Use only after confidence window passes and engine reliability is proven.

Exit criteria:
- no increase in blocked/stale states attributable to fallback removal.

## Rollback Plan

If any phase regresses:

1. Revert the latest phase flag to `0`.
2. Keep observation diff logging on.
3. Collect 24h regression evidence.
4. Fix root cause before retrying.

## Validation Metrics (per phase)

- Advisory delivery health:
  - `% live`
  - `% fallback`
  - `% blocked`
  - `% stale`
- Outcome integrity:
  - `outcomes_with_trace_id / total_outcomes`
  - `advice_helped_rate`
- Packet/runtime:
  - packet hit ratio
  - emitted advisory count
  - pre-tool latency budget breaches

## Ownership and Review Cadence

- Daily check-in during active phase.
- Weekly summary with pass/fail decision for advancing phase.
- Required sign-off before each phase progression.
