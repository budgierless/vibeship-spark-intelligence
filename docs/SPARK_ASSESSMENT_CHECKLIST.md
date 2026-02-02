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
