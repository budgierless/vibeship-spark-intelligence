# Tomorrow Continuation Prompt (Chip + Advisory)

Use this prompt at the start of tomorrow's session:

---

Continue from the current Spark chip/advisory optimization state in `vibeship-spark-intelligence`.

Context lock:
- Runtime profile: `R3_two_evidence_relaxed_merge` (primary), `R2_relaxed_runtime_merge` (fallback).
- Deterministic benchmark seeding is already fixed.
- Promotion gate must require objective + coverage + quality floors.
- Observer policy is active; telemetry-heavy observers remain disabled by policy.

Non-negotiables:
1. Do not optimize for vanity telemetry.
2. Keep chips as evidence infrastructure: `chips -> schema -> distill -> memory -> advisory`.
3. Every promotion decision must be reproducible (same command twice, same metrics except `generated_at`).
4. Commit and push in clean checkpoints.

Start with these exact steps:
1. Verify runtime and policy:
   - `python scripts/apply_chip_profile_r3.py`
   - run service status/health and confirm `sparkd` healthy.
2. Run fresh diagnostics windows:
   - `python scripts/run_chip_learning_diagnostics.py --limit-per-chip 220 --active-only --project-path "." --max-age-days 14 --observer-limit 25 --out-prefix chip_learning_diagnostics_active_observer_tomorrow_v1`
   - `python scripts/run_chip_observer_policy.py --report-glob "benchmarks/out/chip_learning_diagnostics_active_observer_v*_report.json" --windows 3 --min-windows 2 --min-rows-total 50 --disable-max-schema-statement-rate 0.02 --disable-min-telemetry-rate 0.80 --keep-min-schema-statement-rate 0.20 --keep-min-merge-eligible 1 --out-prefix chip_observer_policy_tomorrow_v1 --apply`
3. Run reproducible benchmark pair (twice, different prefixes):
   - `python scripts/run_chip_schema_multiseed.py --plan benchmarks/data/chip_schema_merge_activation_plan_v1.json --chips social-convo,engagement-pulse,x_social --events-per-chip 24 --seed-start 20260217 --seed-count 7 --promotion-baseline-id R0_baseline_safe --promotion-candidate-id R3_two_evidence_relaxed_merge --min-candidate-non-telemetry 0.95 --min-candidate-schema-statement 0.90 --min-candidate-merge-eligible 0.05 --out-prefix chip_schema_merge_activation_multiseed_tomorrow_v1`
   - run same command with `..._v2`.
4. Compare both reports ignoring `generated_at`; confirm deterministic match.
5. If deterministic and KPIs hold, keep R3. If coverage or advisory quality regresses materially, switch to R2 fallback and re-run the same verification cycle.

Deliverables for tomorrow:
1. One report in `docs/reports/` with:
   - KPI deltas vs previous day,
   - promotion/fallback decision,
   - deterministic proof summary.
2. Updated docs if any operating rule changed.
3. Commits pushed to `main`.

---

