# OpenClaw Realtime E2E Benchmark Prompt

Use this prompt in OpenClaw when you want an honest live benchmark of Spark Intelligence (learning -> advisory -> action/outcome), not just unit tests.

## Prompt (paste as-is)

```text
Run a real-time end-to-end Spark Intelligence benchmark in this environment.

Rules:
1) Use live runtime signals and real OpenClaw turns, not unit-test-only evidence.
2) Run this command first and use its JSON/MD outputs as the base evidence:
   python scripts/openclaw_realtime_e2e_benchmark.py --window-minutes 90 --run-canary --canary-agent spark-speed --settle-seconds 12
3) Then validate these points explicitly from files/metrics:
   - Hook telemetry is live (`llm_input` and `llm_output`) and ingested to Spark queue.
   - Advisory engine has recent activity.
   - Feedback requests are schema_version=2 with trace/run/group correlation coverage.
   - Strict trace-bound outcomes exist in-window and show effectiveness.
   - Spark context/advisory files are present in active OpenClaw workspace(s).
4) If anything fails, provide root cause and exact fix commands.
5) Output format:
   - PASS/WARN/FAIL per check
   - short evidence for each check (file + key metric)
   - final verdict: "production-safe now" or "not yet", with top 3 blockers.
```

## Expected Evidence Artifacts

- `docs/reports/openclaw/*_openclaw_realtime_e2e_benchmark.json`
- `docs/reports/openclaw/*_openclaw_realtime_e2e_benchmark.md`
