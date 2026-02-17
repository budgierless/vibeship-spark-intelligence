# OpenClaw Realtime E2E Benchmark

- Generated: `2026-02-16T15:00:08.081108+00:00`
- Window minutes: `90`
- Status: `warn`

## Checks

| Check | Status | Detail |
|---|---|---|
| core_services_running | `pass` | `{'sparkd': True, 'bridge_worker': True, 'scheduler': True, 'watchdog': True}` |
| hook_spool_llm_input_output | `pass` | `{'llm_input_window': 66, 'llm_output_window': 65}` |
| hook_ingested_to_queue | `pass` | `{'hook_rows_window': 131}` |
| advisory_engine_activity | `pass` | `{'rows_window': 500, 'events': {'global_dedupe_suppressed': 63, 'user_prompt_prefetch': 250, 'no_emit': 162, 'no_advice': 25}}` |
| advisory_engine_emitted_nonzero | `warn` | `{'emitted': 0}` |
| workspace_context_delivery | `pass` | `{'existing_workspaces': 3, 'any_context': True}` |
| advisory_delivery_surface | `pass` | `{'any_workspace_advisory': True, 'fallback_advisory_exists': True}` |
| schema_v2_feedback_requests | `pass` | `{'requests_schema_v2_window': 18, 'trace_coverage_pct': 100.0}` |
| strict_outcome_signal | `pass` | `{'strict_with_outcome_window': 2, 'strict_effectiveness_window': 0.0}` |
| production_gates_ready | `pass` | `{'ready': True, 'failed_checks': []}` |
| openclaw_canary_turns | `pass` | `{'agent': 'spark-speed', 'turns_ok': [True, True]}` |

## Live Signal Snapshot

- Hook spool (window): input=66 output=65
- Hook ingest queue rows (window): 131
- Advisory engine rows (window): 500 events={'global_dedupe_suppressed': 63, 'user_prompt_prefetch': 250, 'no_emit': 162, 'no_advice': 25}
- Strict outcomes (window): 2 effectiveness=0.0
- Feedback requests schema_v2 (window): 18 trace_coverage=100.0
