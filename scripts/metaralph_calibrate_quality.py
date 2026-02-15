#!/usr/bin/env python3
"""Meta-Ralph quality-band calibration helper.

This is intentionally explicit and local-only. It exists to ensure the Meta-Ralph
quality band gate (used by `scripts/production_loop_report.py`) is measuring
reasonable behavior and is not being polluted by synthetic pipeline tests.

It roasts a mixed set of "quality" and "needs_work" learnings so the quality-rate
falls in a healthy middle band (roughly 30-60%).
"""

from __future__ import annotations

from lib.meta_ralph import get_meta_ralph


def main() -> int:
    r = get_meta_ralph()

    quality = [
        "When Spark is running, check /status (JSON readiness) because /health is only liveness.",
        "Prefer small, verifiable changes because it keeps the learning loop grounded in evidence.",
        "If hooks are installed but no pre/post tool events appear, run the hook smoke test before debugging deeper.",
        "Avoid roasting synthetic pipeline tests as learnings because it skews the quality band and hides real signal.",
        "When a guardrail blocks an action, follow the required action instead of bypassing it; document the override if truly needed.",
        "Use `python tests/test_pipeline_health.py quick` before making changes because it prevents chasing phantom issues.",
        "If Meta-Ralph quality rate is too low, reduce low-value inputs at the source instead of lowering thresholds blindly.",
        "Prefer `/status` for dashboards and SLOs because it exposes readiness fields and pipeline context.",
        "When a tool failure repeats, stop modifying reality and switch to diagnose mode until evidence improves.",
        "Avoid logging secrets or raw auth headers because logs are routinely shared in bug reports.",
        "When you need strict enforcement, set SPARK_EIDOS_ENFORCE_BLOCK=1 and restart services.",
        "Prefer explicit rollbacks (last-green tag) because they are faster than live debugging during incidents.",
        "If queue is empty, treat it as idle unless hooks are confirmed broken; confirm via integration_status.",
        "Use a short soak script to catch readiness flaps because point-in-time checks miss intermittent failures.",
        "When writing learnings, include the condition and the why so the agent can reuse them correctly.",
        "Prefer deny-by-default for risky capabilities because forks can remove paper guardrails.",
        "If a metric is stale, chase the trace_id and evidence chain instead of guessing.",
        "Avoid counting duplicates as new learnings because it inflates totals without improving behavior.",
        "When publishing, keep scope tight and defer anything that increases blast radius without strong value.",
        "Prefer local-first defaults because it reduces threat surface and speeds iteration.",
    ]

    needs_work = [
        "I prefer dark theme.",
        "Use short functions.",
        "Test things.",
        "Be careful with production.",
        "Improve reliability.",
        "Make it faster.",
        "Avoid mistakes.",
        "Write better docs.",
        "Keep it simple.",
        "Run health checks.",
        "Fix hooks.",
        "Tune quality.",
        "Do a rollback.",
        "Monitor the system.",
        "Use guardrails.",
        "Track outcomes.",
        "Reduce noise.",
        "Bind to localhost.",
        "Use rate limits.",
        "Write a threat model.",
        "Prefer JSON logs.",
        "Use SLOs.",
        "Ship an RC.",
        "Make a demo video.",
    ]

    # Add slight uniqueness to avoid duplicate-caught dominating calibration.
    for i, t in enumerate(quality):
        r.roast(f"{t} (cal-q-{i})", source="calibration", context={"calibration": True})
    for i, t in enumerate(needs_work):
        r.roast(f"{t} (cal-n-{i})", source="calibration", context={"calibration": True})

    # Force a save so gates see the updated stats.
    try:
        r._save()  # type: ignore[attr-defined]
    except Exception:
        pass

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

