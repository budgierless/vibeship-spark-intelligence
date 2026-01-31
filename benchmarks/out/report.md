# Chip Methodology Benchmark Report

Event log: C:\Users\USER\.spark\queue\events.jsonl
Chips: game_dev, vibecoding
Limit: 2000

| Method | Accepted | Accept Rate | Avg Conf | Outcome Hits |
|--------|----------|------------|----------|--------------|
| baseline | 186 | 100.00% | 1.00 | 12 |
| operational_filter | 186 | 100.00% | 1.00 | 12 |
| safety_filter | 186 | 100.00% | 1.00 | 12 |
| outcome_required | 12 | 6.45% | 1.00 | 12 |
| min_fields_2 | 186 | 100.00% | 1.00 | 12 |
| high_conf_0_8 | 186 | 100.00% | 1.00 | 12 |
| correction_first | 178 | 95.70% | 1.00 | 12 |
| why_capture | 122 | 65.59% | 1.00 | 12 |
| preference_only | 178 | 95.70% | 1.00 | 12 |
| balanced | 186 | 100.00% | 1.00 | 12 |

## Notes
- baseline: Accept all insights (no filtering).
- operational_filter: Reject operational telemetry (tool sequences, usage counts).
- safety_filter: Reject unsafe or harmful insight text.
- outcome_required: Only accept insights with matched outcomes.
- min_fields_2: Require at least 2 captured fields.
- high_conf_0_8: Require confidence >= 0.8.
- correction_first: Only accept insights from correction-like user input.
- why_capture: Only accept insights when a causal reason is present.
- preference_only: Only accept preference-related signals.
- balanced: Operational + safety filter + confidence >= 0.7 + evidence or outcome.