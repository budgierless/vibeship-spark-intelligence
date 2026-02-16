# Replay Counterfactual Advisory (Shipped 2026-02-16)

## Why this exists

Advisory quality improves when Spark can say:

- what happened in similar past cases,
- which pattern underperformed,
- which alternative won under strict attribution,
- and whether the evidence is strong enough to justify intervention.

This feature adds that behavior directly into `advisor.advise()` as a first-class source (`source="replay"`).

## What shipped

### Runtime behavior

Spark now attempts to synthesize one replay advisory per tool call:

- Finds past acted-on outcomes for the same tool.
- Keeps only explicit outcomes (`good`/`bad`).
- Uses strict attribution requirements for replay confidence:
  - retrieval trace matches outcome trace,
  - bounded outcome latency window.
- Builds per-pattern buckets (grouped by `insight_key` fallback `learning_id`).
- Compares strongest strict-success pattern against baseline pattern.
- Emits replay advisory only if improvement delta is meaningful.

### Output style

Advisory text format:

`[Replay] Similar <tool> pattern: '<baseline>' worked X% (n strict cases). Alternative '<best>' worked Y% (n). Try the alternative?`

Reason line includes:

- strict replay provenance,
- last-seen date,
- estimated uplift delta.

### Integration points

- `lib/advisor.py`
  - `advise()` now calls `_get_replay_counterfactual_advice(...)`
  - new helper methods:
    - `_replay_extract_tool`
    - `_replay_outcome_ts`
    - `_is_replay_strict`
    - `_replay_preview_text`
    - `_get_replay_counterfactual_advice`
- source weight includes:
  - `_SOURCE_BOOST["replay"] = 1.22`

### Safety gates for emission

Replay advisory returns nothing unless all gates are met:

1. Replay enabled.
2. At least two candidate patterns for the same tool.
3. Candidate strict sample floor met.
4. Improvement delta meets threshold.
5. Context relevance floor met for at least one side.

## Tuneables / controls

Current controls are environment-backed:

- `SPARK_ADVISORY_REPLAY_ENABLED` (default `1`)
- `SPARK_ADVISORY_REPLAY_MIN_STRICT` (default `4`)
- `SPARK_ADVISORY_REPLAY_MIN_DELTA` (default `0.20`)
- `SPARK_ADVISORY_REPLAY_MAX_RECORDS` (default `3500`)
- `SPARK_ADVISORY_REPLAY_MAX_AGE_S` (default `21 days`)
- `SPARK_ADVISORY_REPLAY_STRICT_WINDOW_S` (default `1200`)
- `SPARK_ADVISORY_REPLAY_MIN_CONTEXT` (default `0.12`)

## Validation in this patch

Tests added:

- `tests/test_advisor_replay.py`
  - surfaces better strict alternative with strong delta,
  - blocks replay when delta is too small,
  - blocks replay when outcomes are non-strict.

Regression coverage also run during patch:

- advisor-related suites,
- auto-tuner suite,
- gate/quality suites,
- production loop report still `READY (13/13)`.

## Suggested productization next (immediate follow-up)

1. Add explicit user controls (`off|standard|replay`) via tuneables/API.
2. Add feedback endpoint for replay advice:
   - accepted alternative,
   - skipped,
   - not relevant.
3. Track replay-specific KPIs:
   - `replay_emit_count`,
   - `replay_accept_rate`,
   - `replay_delta_realized` (post-advice strict success uplift).
4. Add advisory UI badge:
   - `Replay` + confidence + strict sample count + last seen date.

## Operator notes

If replay appears too often:

- increase `SPARK_ADVISORY_REPLAY_MIN_STRICT`,
- increase `SPARK_ADVISORY_REPLAY_MIN_DELTA`,
- reduce `SPARK_ADVISORY_REPLAY_MAX_AGE_S`.

If replay appears too rarely:

- lower strict sample floor slightly,
- lower delta floor moderately,
- widen max age window only if outcomes are still representative.

Prepared: **2026-02-16**
