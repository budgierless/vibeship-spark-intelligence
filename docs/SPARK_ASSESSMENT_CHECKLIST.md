# Spark Assessment Checklist

Status: documentation only. Use before any implementation changes.

## Spark Core (current repo)
### Inputs
- SparkEventV1 schema compliance across all adapters.
- Event queue growth and drop behavior under load.
- Hook latency and failure modes (PreToolUse/PostToolUse).
- Hook names normalize to runtime event types for chips: post_tool, post_tool_failure, user_prompt.

### Risks
- Schema drift between adapters.
- Queue backlog and watchdog behavior.
- Privacy leaks from overly broad payload capture.

### Metrics
- Ingest latency (p50/p95).
- Queue depth over time.
- Validation error rate (invalid events / total).

## Chips Runtime (future repo)
### Inputs
- Chip spec validation (schema + required fields).
- Trigger coverage across event kinds.
- Extraction reliability (non-regex and regex usage).

### Risks
- False positives from weak triggers.
- Scope overreach by community chips.
- Outcome linking failures (missing entity refs or time windows).

### Metrics
- Precision and recall per chip.
- Outcome coverage (% outcomes explained).
- Prediction accuracy per chip.

## Vibecoding Chip (v1)
### Inputs
- MCP availability and auth for each profile.
- Repo/CI/deploy/observability feed reliability.
- Outcome signals and time windows.

### Risks
- Missing or noisy outcome signals.
- Overfitting to a single repo/workflow.
- Attribution errors (which change caused which outcome).

### Metrics
- Actionable insight rate (insights used / insights emitted).
- Time-to-signal (event -> insight latency).
- False positive rate for regressions.

## Production Loop Gates (new)
Run these in every iteration loop before promotion:

1. `python tests/test_pipeline_health.py quick`
2. `python tests/test_learning_utilization.py quick`
3. `python tests/test_metaralph_integration.py`
4. `python -m lib.integration_status`
5. `python scripts/production_loop_report.py`
6. If counters are invalid: `python scripts/repair_effectiveness_counters.py`

### Required gate targets
- Effectiveness counter integrity: `helpful <= followed <= total`.
- Retrieval rate: `>= 10%`.
- Acted-on rate: `>= 30%` on actionable retrievals (exclude orchestration-only `tool:task` records).
- Effectiveness rate: `>= 50%`.
- Distillation floor: `>= 5`.
- Meta-Ralph quality band: `30%..60%`.
- Chip-to-cognitive ratio: `<= 100`.
- Queue depth: `<= 2000`.

### Future loop test coverage to expand
- Structured JSON logging validation on `sparkd`/bridge/hooks paths.
- EIDOS distillation edge cases (low-sample, contradictory evidence, stale episodes).
- Source-attribution quality tests (advice source -> action -> outcome linkage).
- High-volume chip suppression tests (noise containment under burst traffic).
- Telemetry hygiene tests (counter repair, chip compaction, outcome retention windows).
- Trace-linking continuity tests across `advise -> act -> report_outcome` with concurrent tool runs.
