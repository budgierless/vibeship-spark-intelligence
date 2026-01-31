# Chip Benchmarks: How to Measure Evolved Intelligence

This doc explains how to run chip benchmarks and what to measure beyond
primitive counts. The goal is superintelligent learning, not just volume.

---

## Quick Start

```bash
python benchmarks/run_benchmarks.py --limit 500
```

Domain chips:

```bash
python benchmarks/run_benchmarks.py --chips vibecoding,game_dev --enrich --limit 2000
```

Synthetic events:

```bash
python benchmarks/generate_synthetic.py --vibe 50 --game 50
python benchmarks/run_benchmarks.py --log benchmarks/synthetic_events.jsonl --chips vibecoding,game_dev
```

Outputs:
- `benchmarks/out/report.json`
- `benchmarks/out/report.md`

---

## Methodology Variants

We compare 10 methodology filters (baseline, operational filter, safety filter,
outcome-required, etc.) to see which yields the highest human-useful ratio.

---

## Superintelligence-Oriented Metrics

These metrics matter more than raw counts:

1) Human-useful ratio
   - Percentage of insights that are not operational telemetry.

2) Outcome coverage
   - Percentage of insights with matched outcomes.

3) Reasoning density
   - Ratio of "why" and principle insights vs sequences.

4) Preference stability
   - Preferences validated across time.

5) Safety compliance
   - Unsafe insights blocked before promotion.

6) Cross-domain transfer
   - Insights that generalize across chips.

7) Time-to-useful-insight
   - How quickly the system learns something valuable.

---

## What Good Looks Like

- Human-useful ratio > 80%.
- Outcome coverage > 50%.
- Reasoning density rising over time.
- Safety compliance 100% (no unsafe promotion).
- Preference stability improving across sessions.

---

## Benchmarks vs Reality

Benchmarks are directional, not absolute. Always validate with:
- Real outcomes from projects.
- Human feedback loops.
- Safety audits.

