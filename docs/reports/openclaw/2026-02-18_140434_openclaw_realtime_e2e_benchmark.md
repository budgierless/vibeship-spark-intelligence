# OpenClaw Realtime E2E Benchmark

- Generated: `2026-02-18T10:04:34.408481+00:00`
- Window minutes: `60`
- Status: `fail`

## Checks

| Check | Status | Detail |
|---|---|---|
| core_services_running | `pass` | `{'sparkd': True, 'bridge_worker': True, 'scheduler': True, 'watchdog': True}` |
| hook_spool_llm_input_output | `pass` | `{'llm_input_window': 30, 'llm_output_window': 29}` |
| hook_ingested_to_queue | `pass` | `{'hook_rows_window': 63}` |
| advisory_engine_activity | `pass` | `{'rows_window': 63, 'events': {'user_prompt_prefetch': 1, 'no_advice': 9, 'emitted': 3, 'no_emit': 19, 'global_dedupe_suppressed': 31}}` |
| advisory_engine_emitted_nonzero | `pass` | `{'ok': True, 'mode': 'emitted', 'emitted': 3, 'global_dedupe_suppressed': 31, 'recent_workspace_advisory': True, 'recent_fallback_advisory': True}` |
| workspace_context_delivery | `pass` | `{'existing_workspaces': 3, 'any_context': True}` |
| advisory_delivery_surface | `pass` | `{'any_workspace_advisory': True, 'fallback_advisory_exists': True}` |
| schema_v2_feedback_requests | `pass` | `{'requests_schema_v2_window': 3, 'trace_coverage_pct': 100.0}` |
| strict_outcome_signal | `warn` | `{'strict_with_outcome_window': 0, 'strict_effectiveness_window': None}` |
| production_gates_ready | `fail` | `{'ready': False, 'failed_checks': ['meta_ralph_quality_band']}` |
| openclaw_canary_turns | `warn` | `{'agent': 'spark-speed', 'turns_ok': [False, False]}` |

## Live Signal Snapshot

- Hook spool (window): input=30 output=29
- Hook ingest queue rows (window): 63
- Advisory engine rows (window): 63 events={'user_prompt_prefetch': 1, 'no_advice': 9, 'emitted': 3, 'no_emit': 19, 'global_dedupe_suppressed': 31}
- Strict outcomes (window): 0 effectiveness=None
- Feedback requests schema_v2 (window): 3 trace_coverage=100.0
