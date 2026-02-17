# OpenClaw Realtime E2E Benchmark

- Generated: `2026-02-16T15:06:24.169103+00:00`
- Window minutes: `90`
- Status: `pass`

## Checks

| Check | Status | Detail |
|---|---|---|
| core_services_running | `pass` | `{'sparkd': True, 'bridge_worker': True, 'scheduler': True, 'watchdog': True}` |
| hook_spool_llm_input_output | `pass` | `{'llm_input_window': 72, 'llm_output_window': 71}` |
| hook_ingested_to_queue | `pass` | `{'hook_rows_window': 143}` |
| advisory_engine_activity | `pass` | `{'rows_window': 500, 'events': {'no_emit': 68, 'user_prompt_prefetch': 250, 'global_dedupe_suppressed': 101, 'no_advice': 25, 'synth_empty': 56}}` |
| advisory_engine_emitted_nonzero | `pass` | `{'ok': True, 'mode': 'dedupe_suppressed_recent_delivery', 'emitted': 0, 'global_dedupe_suppressed': 101, 'recent_workspace_advisory': True, 'recent_fallback_advisory': True}` |
| workspace_context_delivery | `pass` | `{'existing_workspaces': 3, 'any_context': True}` |
| advisory_delivery_surface | `pass` | `{'any_workspace_advisory': True, 'fallback_advisory_exists': True}` |
| schema_v2_feedback_requests | `pass` | `{'requests_schema_v2_window': 18, 'trace_coverage_pct': 100.0}` |
| strict_outcome_signal | `pass` | `{'strict_with_outcome_window': 2, 'strict_effectiveness_window': 0.0}` |
| production_gates_ready | `pass` | `{'ready': True, 'failed_checks': []}` |
| openclaw_canary_turns | `pass` | `{'agent': 'spark-speed', 'turns_ok': [True, True]}` |

## Live Signal Snapshot

- Hook spool (window): input=72 output=71
- Hook ingest queue rows (window): 143
- Advisory engine rows (window): 500 events={'no_emit': 68, 'user_prompt_prefetch': 250, 'global_dedupe_suppressed': 101, 'no_advice': 25, 'synth_empty': 56}
- Strict outcomes (window): 2 effectiveness=0.0
- Feedback requests schema_v2 (window): 18 trace_coverage=100.0
