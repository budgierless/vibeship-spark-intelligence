# Chip Strategy Experiment Matrix v2

## Scope

Objective: run a real chip strategy matrix beyond simple chip off/on using segmented C/D plans, then score impact on advisory quality.

Plan + runner:
- `benchmarks/data/advisory_chip_experiment_plan_v1.json`
- `scripts/run_advisory_chip_experiments.py`

Run command:

```bash
python scripts/run_advisory_chip_experiments.py \
  --plan benchmarks/data/advisory_chip_experiment_plan_v1.json \
  --profiles baseline \
  --repeats 1 \
  --no-force-live \
  --out-prefix advisory_chip_experiments_v2
```

## Result Snapshot

Source: `benchmarks/out/advisory_chip_experiments_v2_report.json`

| Rank | Experiment | Objective | High-Value | Harmful | Unsolicited | Chip Advice Hit | Chip Evidence Hit | Delta Objective vs Control |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| 1 | `C_chip_targeted_business_social` | 0.7361 | 43.48% | 0.00% | 4.35% | 0.00% | 100.00% | +0.0075 |
| 2 | `D_chip_memory_research_focus` | 0.7336 | 43.48% | 0.00% | 4.35% | 0.00% | 100.00% | +0.0050 |
| 3 | `A_chip_off_global` | 0.7286 | 43.48% | 0.00% | 4.35% | 0.00% | 100.00% | +0.0000 |
| 4 | `B_chip_on_global` | 0.7286 | 43.48% | 0.00% | 4.35% | 0.00% | 100.00% | +0.0000 |

## Honest Assessment

1. Segmented strategies (C/D) improved weighted objective slightly vs control, but the gain is small.
2. `chip_advice_hit` stayed at `0.00%` in every arm. Chips are being retrieved (`chip_evidence_hit=100%`) but not selected into emitted advice.
3. Practical implication: chip tuning is currently affecting retrieval pool composition, not final advisory decisions.
4. This means chip profiles alone are insufficient for stronger real advisory impact under current gating/ranking behavior.

## Measurement Correction Applied

Earlier chip hit-rate telemetry could overcount by mixing retrieval evidence with emitted advice.  
The runner now separates:
- `chip_hit_case_rate` (advice emission),
- `chip_evidence_case_rate` (retrieval evidence presence),
with equivalent mind/semantic splits.

File updated:
- `scripts/run_advisory_chip_experiments.py`

## Next Optimization Targets

1. Increase chip selection probability in emitted advice for matched domains without increasing harmful or unsolicited rates.
2. Add a dedicated promotion criterion: chip strategy is only "working" if `chip_advice_hit` rises materially while objective and safety metrics do not regress.
3. Keep C as current working winner for now, but treat it as interim until chip advice-hit is non-zero in production-like runs.
