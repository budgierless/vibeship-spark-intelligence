# Chip Benchmarking

Run methodology benchmarks against a saved event log.

## Quick Start

```bash
python benchmarks/run_benchmarks.py --limit 500
```

Optional:

```bash
python benchmarks/run_benchmarks.py --chips vibecoding,game_dev --limit 1000
```

Synthetic data:

```bash
python benchmarks/generate_synthetic.py --vibe 50 --game 50
python benchmarks/run_benchmarks.py --log benchmarks/synthetic_events.jsonl --chips vibecoding,game_dev
```

Heuristic enrichment (fills missing fields for domain chips):

```bash
python benchmarks/run_benchmarks.py --chips vibecoding,game_dev --enrich --limit 2000
```

Outputs:
- `benchmarks/out/report.json`
- `benchmarks/out/report.md`

## Notes

- This replays a local event log (`~/.spark/queue/events.jsonl`) by default.
- Results are heuristic and meant to compare methodology variants on the same data.

## Beyond Primitive Benchmarks (Superintelligence Metrics)

Track these in addition to raw accept rates:
- Human-useful ratio (non-operational insights / total).
- Outcome coverage (insights with validated outcomes).
- Preference stability (validated preferences over time).
- Reasoning density (why/principle insights vs sequences).
- Safety compliance (unsafe insights blocked).
- Cross-domain transfer rate (insights reused across chips).
