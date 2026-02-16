# OpenClaw Verification Log

Purpose: keep an auditable history of end-to-end Spark x OpenClaw operational verification runs.

## 2026-02-16

### Run A (user-reported live verification)

- Source: operator run in OpenClaw session.
- Result summary:
  - PASS: core services and fresh bridge/scheduler heartbeat.
  - PASS: hook spool has `llm_input` and `llm_output`.
  - PASS: hook events ingested to Spark queue.
  - FAIL: advisory emitted count in sampled 90-minute slice.
  - PASS: `schema_version=2` request coverage (`trace_id`, `run_id`, `advisory_group_key`) at 100%.
  - PASS: canary turns and workspace advisory surfaces.
- Diagnosis:
  - advisory check was over-strict in dedupe-heavy windows and could report false warnings.

### Run B (benchmark rerun)

- Command:
  - `python scripts/openclaw_realtime_e2e_benchmark.py --window-minutes 90 --run-canary --canary-agent spark-speed --canary-timeout-s 45 --settle-seconds 6`
- Report:
  - `docs/reports/openclaw/2026-02-16_190008_openclaw_realtime_e2e_benchmark.md`
- Key signals:
  - `global_dedupe_suppressed=63`
  - `emitted=0`
  - advisory surfaces were fresh
- Action taken:
  - updated benchmark logic to classify dedupe-suppressed + fresh advisory delivery as healthy signal instead of outage.

### Guardrail added

- Script:
  - `scripts/openclaw_realtime_e2e_benchmark.py`
- Regression tests:
  - `tests/test_openclaw_realtime_e2e_benchmark.py`

### Run C (post-fix rerun)

- Command:
  - `python scripts/openclaw_realtime_e2e_benchmark.py --window-minutes 90 --run-canary --canary-agent spark-speed --canary-timeout-s 45 --settle-seconds 6`
- Report:
  - `docs/reports/openclaw/2026-02-16_190252_openclaw_realtime_e2e_benchmark.md`
- Result:
  - status `pass`
  - advisory check mode `dedupe_suppressed_recent_delivery`
