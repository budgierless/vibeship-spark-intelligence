# Advisory Realism Contract Decision (2026-02-12)

## Decision

Lock advisory realism operations to:
- Primary (blocking): `benchmarks/data/advisory_realism_eval_v2.json`
- Shadow (non-blocking): `benchmarks/data/advisory_realism_eval_v1.json`

Contract artifact:
- `benchmarks/data/advisory_realism_operating_contract_v1.json`

## Evidence

Primary report:
- `benchmarks/out/advisory_realism_baseline_v2labels_v5_report.json`

Shadow report:
- `benchmarks/out/advisory_realism_shadow_v1_postfix_report.json`

Winner profile in both runs: `baseline`

Primary minus shadow delta:
- objective: `+0.1125`
- score: `+0.0708`
- high_value_rate: `+0.1667`
- harmful_emit_rate: `-0.2778`
- critical_miss_rate: `-0.0102`
- source_alignment_rate: `+0.0000`
- theory_discrimination_rate: `+0.2222`
- trace_bound_rate: `+0.0000`

## Gate Outcome

Primary (`v2`) gate status:
- high_value_rate: PASS
- harmful_emit_rate: PASS
- critical_miss_rate: PASS
- source_alignment_rate: PASS
- theory_discrimination_rate: PASS
- trace_bound_rate: PASS

Shadow (`v1`) gate status:
- high_value_rate: FAIL
- harmful_emit_rate: FAIL
- critical_miss_rate: PASS
- source_alignment_rate: PASS
- theory_discrimination_rate: FAIL
- trace_bound_rate: PASS

## Policy

1. Use primary (`v2`) pass/fail as deployment gate.
2. Keep shadow (`v1`) telemetry for drift detection only.
3. Investigate if both primary and shadow regress simultaneously, or if source/trace gates degrade.
