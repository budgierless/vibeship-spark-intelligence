# OpenClaw Realtime E2E Benchmark

- Generated: `2026-02-16T14:48:55.757474+00:00`
- Window minutes: `90`
- Status: `pass`

## Checks

| Check | Status | Detail |
|---|---|---|
| core_services_running | `pass` | `{'sparkd': True, 'bridge_worker': True, 'scheduler': True, 'watchdog': True}` |
| hook_spool_llm_input_output | `pass` | `{'llm_input_window': 61, 'llm_output_window': 60}` |
| hook_ingested_to_queue | `pass` | `{'hook_rows_window': 115}` |
| advisory_engine_activity | `pass` | `{'rows_window': 500, 'events': {'user_prompt_prefetch': 250, 'no_emit': 217, 'no_advice': 28, 'emitted': 5}}` |
| advisory_engine_emitted_nonzero | `pass` | `{'emitted': 5}` |
| workspace_context_delivery | `pass` | `{'existing_workspaces': 3, 'any_context': True}` |
| advisory_delivery_surface | `pass` | `{'any_workspace_advisory': True, 'fallback_advisory_exists': True}` |
| schema_v2_feedback_requests | `pass` | `{'requests_schema_v2_window': 17, 'trace_coverage_pct': 100.0}` |
| strict_outcome_signal | `pass` | `{'strict_with_outcome_window': 2, 'strict_effectiveness_window': 0.0}` |
| production_gates_ready | `pass` | `{'ready': True, 'failed_checks': []}` |
| openclaw_canary_turns | `pass` | `{'agent': 'spark-speed', 'turns_ok': [True, True]}` |

## Live Signal Snapshot

- Hook spool (window): input=61 output=60
- Hook ingest queue rows (window): 115
- Advisory engine rows (window): 500 events={'user_prompt_prefetch': 250, 'no_emit': 217, 'no_advice': 28, 'emitted': 5}
- Strict outcomes (window): 2 effectiveness=0.0
- Feedback requests schema_v2 (window): 17 trace_coverage=100.0
