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

Scenario-based live runs:

```bash
# 1) Record a live session while building artifacts
python benchmarks/record_session.py --scenario benchmarks/scenarios/marketing/scenario.yaml --out benchmarks/logs/marketing_run.jsonl --session marketing-001

# 2) Run benchmarks + scenario scoring
python benchmarks/run_benchmarks.py --log benchmarks/logs/marketing_run.jsonl --chips marketing --scenario benchmarks/scenarios/marketing/scenario.yaml
```

Scenario weights:

- `outcome_signals` and `expected_artifacts` accept weighted entries:
  - `- signal: "kpi defined"\n    weight: 1.0`
  - `- path: "benchmarks/projects/marketing/brief.md"\n    weight: 1.0`

Heuristic enrichment (fills missing fields for domain chips):

```bash
python benchmarks/run_benchmarks.py --chips vibecoding,game_dev --enrich --limit 2000
```

Outputs:
- `benchmarks/out/report.json`
- `benchmarks/out/report.md`
Logs:
- `benchmarks/logs/*.jsonl` (live runs)

## Local Model Stress Suite (Ollama)

Stress-test local models across multiple methodologies (advisory, retrieval conflict resolution,
chip routing, control-plane budgeting, noisy context, structured JSON output).

Default models include:
- `llama3.2:3b`
- `phi4-mini`
- `qwen2.5-coder:3b`

Run:

```bash
python scripts/local_ai_stress_suite.py --repeats 3 --budget-ms 3000 --soft-budget-ms 3500
```

Include live pipeline replay contexts from your local Spark queue:

```bash
python scripts/local_ai_stress_suite.py --repeats 5 --live-scenarios 12 --budget-ms 3000 --soft-budget-ms 3500
```

Custom models:

```bash
python scripts/local_ai_stress_suite.py --models "llama3.2:3b,phi4-mini,qwen2.5-coder:3b"
```

Output:
- `benchmarks/out/local_model_stress_report.json`

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
