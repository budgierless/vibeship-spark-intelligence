# OpenClaw Realtime E2E Benchmark

- Generated: `2026-02-16T14:17:26.766259+00:00`
- Window minutes: `90`
- Status: `pass`

## Checks

| Check | Status | Detail |
|---|---|---|
| core_services_running | `pass` | `{'sparkd': True, 'bridge_worker': True, 'scheduler': True, 'watchdog': True}` |
| hook_spool_llm_input_output | `pass` | `{'llm_input_window': 14, 'llm_output_window': 14}` |
| hook_ingested_to_queue | `pass` | `{'hook_rows_window': 26}` |
| advisory_engine_activity | `pass` | `{'rows_window': 500, 'events': {'user_prompt_prefetch': 250, 'synth_empty': 250}}` |
| workspace_context_delivery | `pass` | `{'existing_workspaces': 3, 'any_context': True}` |
| advisory_delivery_surface | `pass` | `{'any_workspace_advisory': True, 'fallback_advisory_exists': True}` |
| schema_v2_feedback_requests | `pass` | `{'requests_schema_v2_window': 13, 'trace_coverage_pct': 100.0}` |
| strict_outcome_signal | `pass` | `{'strict_with_outcome_window': 7, 'strict_effectiveness_window': 1.0}` |
| production_gates_ready | `pass` | `{'ready': True, 'failed_checks': []}` |
| openclaw_canary_turns | `pass` | `{'agent': 'spark-speed', 'turns_ok': [True, True]}` |

## Live Signal Snapshot

- Hook spool (window): input=14 output=14
- Hook ingest queue rows (window): 26
- Advisory engine rows (window): 500 events={'user_prompt_prefetch': 250, 'synth_empty': 250}
- Strict outcomes (window): 7 effectiveness=1.0
- Feedback requests schema_v2 (window): 13 trace_coverage=100.0
