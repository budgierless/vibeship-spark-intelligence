#!/usr/bin/env python3
"""Run production loop gates against live Spark state."""

from lib.production_gates import evaluate_gates, format_gate_report, load_live_metrics


def main() -> int:
    metrics = load_live_metrics()
    result = evaluate_gates(metrics)
    print(format_gate_report(metrics, result))
    return 0 if result.get("ready") else 1


if __name__ == "__main__":
    raise SystemExit(main())

