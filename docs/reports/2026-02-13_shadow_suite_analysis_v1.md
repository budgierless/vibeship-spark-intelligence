# Shadow Suite Analysis v1 (Why It Fails, What To Do)

Date: 2026-02-13

## Executive Summary

The advisory contract runs two suites:
- **PRIMARY** = v2 scoring surface (current target)
- **SHADOW** = v1 scoring surface (historical strict-suppress sentinel)

Primary consistently passes gates. Shadow consistently fails **two gates**:
- `high_value_rate`
- `theory_discrimination_rate`

This is largely explained by **label drift**: five cases are labeled `should_emit=false` in v1 but `should_emit=true` in v2. When we emit on those cases, v1 counts them as **unsolicited**, dragging shadow high-value and theory-discrimination metrics.

## 1) What "Shadow" Means In This Repo

From `benchmarks/data/advisory_realism_operating_contract_v1.json`:
- PRIMARY cases: `benchmarks/data/advisory_realism_eval_v2.json`
- SHADOW cases: `benchmarks/data/advisory_realism_eval_v1.json`

This is not production shadow traffic. It is a second benchmark suite intended to detect regressions against an older scoring regime.

Contract policy note (important):
- `shadow_regression_allowed: true`
- "v1 remains a historical strict-suppress sanity set and should not block v2 corrective-advisory policy"

## 2) The Concrete Driver: "Unsolicited" In Shadow

Using the latest force-live full contract:
- Shadow unsolicited emits: `5/18` (27.78%)

Those five cases are:
- `r3_uncertain_signal_suppress`
- `r6_theory_without_proof`
- `r9_shiny_feature_detour`
- `r12_fake_confidence_push`
- `r16_over_generalized_global_fix`

In the shadow report, each has `should_emit=false` and `emitted=true`.

In the primary report, the **same cases** have `should_emit=true`, so the exact same "emit" behavior is no longer counted as unsolicited.

Interpretation:
- Shadow is acting as a "be quieter / suppress theory-ish output" suite.
- Primary is acting as a "be helpful / corrective / proactive" suite.

## 3) What This Means For Decisions

If your product direction is "more proactive advisory", then:
- prioritize PRIMARY gates
- track SHADOW failures as a *sentinel* (don't optimize to it by default)

If your product direction is "strict suppress / only speak when extremely confident", then:
- you can tune advisory gating upward, but be careful: prior strict canary runs increased critical misses and reduced helpful emission.

## 4) Options (Recommended Order)

1. Keep shadow as-is and treat it as non-blocking.
   - Best when v2 is the truth surface and v1 is legacy.

2. Split shadow into two suites:
   - `shadow_strict_suppress` (keep current v1 semantics)
   - `shadow_alignment` (update v1 `should_emit` labels to match v2)
   This preserves a strict sentinel while also giving you a comparable regression check.

3. If you truly want SHADOW to pass, you must reduce emits on those 5 cases.
   - This will likely reduce helpfulness on PRIMARY unless the gating can be made conditional on stronger evidence signals.

