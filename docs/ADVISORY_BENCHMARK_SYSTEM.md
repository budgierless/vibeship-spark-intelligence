# Advisory Benchmark System

## Purpose

Create a dedicated benchmark loop for advisory quality so Spark can improve:
- when advice appears,
- how actionable it is,
- how well it uses memory,
- and how consistently it stays trace-bound.

This benchmark is separate from Forge/Depth and focused only on
`retrieval -> advisory -> actionability`.

## Artifacts

- Runner: `benchmarks/advisory_quality_ab.py`
- Seed scenarios: `benchmarks/data/advisory_quality_eval_seed.json`
- Output JSON: `benchmarks/out/advisory_quality_ab_report.json`
- Output Markdown: `benchmarks/out/advisory_quality_ab_report.md`

## Core Metrics

Per-case score uses weighted components:
- `emit_correct` (35%): did emit/no-emit match case expectation
- `expected_hit_rate` (20%): required signal fragments present
- `forbidden_clean_rate` (15%): noisy/irrelevant fragments absent
- `actionability` (10%): concrete next command/check present
- `trace_bound` (10%): decision event linked to the case trace
- `memory_utilized` (10%): memory sources actually contributed

Profile-level score:
- mean case score, then repetition penalty adjustment.

## Profile Comparison

Default benchmark profiles:
- `baseline`
- `balanced`
- `strict`

Each profile controls:
- `advisory_engine.*` cooldown policy
- `advisory_gate.*` suppression policy
- `advisor.max_items` / `advisor.min_rank_score` quality threshold

Run example:

```bash
python benchmarks/advisory_quality_ab.py \
  --cases benchmarks/data/advisory_quality_eval_seed.json \
  --profiles baseline,balanced,strict \
  --repeats 1 \
  --force-live
```

`--force-live` is important when comparing advisory quality itself, because
packet paths can mask live retrieval/gating behavior.

## Iteration Loop (Recommended)

1. Run benchmark on current live profile (baseline snapshot).
2. Run benchmark on candidate profiles.
3. Promote winner only if:
   - score improves,
   - no-emit rate does not regress materially,
   - repetition penalty does not worsen.
4. Keep winner live for a real workload window.
5. Run `scripts/advisory_self_review.py` for 12h/24h reality check.
6. Update scenario set with new failure modes.

## Anti-Gaming Guardrails

- Keep `forbidden_contains` current with known noisy phrases.
- Maintain both emit-expected and suppression-expected scenarios.
- Include mixed tools (`Read`, `Edit`, `Task`, `WebFetch`) each cycle.
- Require trace-bound checks in every benchmark run.

## Expansion Backlog

- Add explicit no-emit reason histogram (`error_code`) to benchmark report ranking.
- Add scenario tags by intent-plane and compute per-plane scores.
- Add auto profile sweeper for bounded grid search, then publish top-N candidates.
