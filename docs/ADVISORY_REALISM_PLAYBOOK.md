# Advisory Realism Playbook

## Why This Exists

Spark advisory quality can look good in narrow coding benchmarks while failing in real operations.

We need a loop that verifies:
- advice is high-value, not just frequent,
- cross-system context is actually used,
- memory retrieval (semantic, cognitive, mind, outcomes) is source-aligned,
- anti-pattern theories are suppressed,
- critical cases are not missed.

This playbook turns advisory tuning into a measurable operating cycle.

## What We Added

- `benchmarks/advisory_realism_bench.py`
- `benchmarks/data/advisory_realism_eval_v1.json`
- `benchmarks/data/advisory_theory_catalog_v1.json`
- `benchmarks/seed_advisory_theories.py`

Supporting extension:
- `benchmarks/advisory_quality_ab.py` now includes per-case `source_counts` in output.

## Realism Model

Three depth tiers:
- `D1`: real-time tactical guidance (immediate next checks)
- `D2`: workflow/policy tuning across systems
- `D3`: strategic architecture and cross-session learning

Cross-system coverage examples:
- `spark_pulse + advisory`
- `spark_porch + spark_depth + orchestration`
- `mind + semantic_memory + advisory`
- `sparkd + bridge_worker + openclaw_bridge`

Theory quality labels:
- `good`: should be surfaced with evidence and actionability
- `bad`: should be suppressed or rejected

## Metrics That Matter

Realism runner produces:
- `high_value_rate`
- `harmful_emit_rate`
- `critical_miss_rate`
- `source_alignment_rate`
- `theory_discrimination_rate`
- depth/domain score splits

Readiness gates (defaults):
- high value >= 55%
- harmful emit <= 10%
- critical miss <= 10%
- source alignment >= 55%
- theory discrimination >= 70%
- trace bound >= 85%

## End-to-End Runbook

1. Seed good theories into memory:
```bash
python benchmarks/seed_advisory_theories.py \
  --catalog benchmarks/data/advisory_theory_catalog_v1.json \
  --quality good
```

2. Run realism benchmark:
```bash
python benchmarks/advisory_realism_bench.py \
  --cases benchmarks/data/advisory_realism_eval_v1.json \
  --profiles baseline,balanced,strict \
  --repeats 1 \
  --force-live \
  --out-prefix advisory_realism_bench
```

Primary + shadow cadence:
- Primary contract run: `benchmarks/data/advisory_realism_eval_v2.json` (blocking)
- Shadow run: `benchmarks/data/advisory_realism_eval_v1.json` (non-blocking)
- Contract reference: `benchmarks/data/advisory_realism_operating_contract_v1.json`

3. Tune profile candidates with sweeper if needed:
```bash
python benchmarks/advisory_profile_sweeper.py \
  --cases benchmarks/data/advisory_quality_eval_extended.json \
  --repeats 1 \
  --force-live \
  --max-candidates 12
```

4. Re-run realism benchmark and compare deltas.

5. Validate with runtime review:
```bash
python scripts/advisory_self_review.py --hours 24
```

## How This Enters Ongoing Documentation

When updating `Intelligence_Flow.md` / `Intelligence_Flow_Map.md`, include:
- advisory objective metric = high-value advice rate (not raw advice count),
- memory objective metric = source alignment rate,
- reliability objective metric = harmful emit and critical miss rates,
- learning objective metric = theory discrimination over time.

This keeps Spark optimization tied to outcomes, not feature volume.

## Daily/Per-Shift Cadence

- Run realism bench at least once per day.
- If major tuneables changed, run before and after.
- Log winner profile + gate pass/fail into `docs/reports/`.
- Reject profile changes that improve base score but regress harmful emit or critical miss.
