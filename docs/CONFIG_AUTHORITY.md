# Config Authority

Canonical config resolution model for Spark runtime behavior.

## Purpose
- Eliminate config drift from multiple competing sources.
- Make precedence deterministic and observable.
- Keep auto-tuner scoped and safe.

## Precedence (highest wins last)
1. `schema defaults` from `lib/tuneables_schema.py`
2. `versioned baseline` from `config/tuneables.json`
3. `runtime overrides` from `~/.spark/tuneables.json`
4. `explicit env overrides` (allowlisted per key, per module)

Notes:
- Env overrides are opt-in and explicit, not implicit global shadowing.
- Invalid env values are ignored with warnings.

## Current Adoption
- `lib/bridge_cycle.py` (`bridge_worker.*`)
- `lib/advisory_engine.py` (`advisory_engine.*`)
- `lib/advisory_emitter.py` (`advisory_engine.emit_*`)
- `lib/advisor.py` (`advisor.*`, `auto_tuner.*`, `retrieval.*`, `memory_emotion.*`, `values.advice_cache_ttl`)
- `lib/advisory_gate.py` (`advisory_gate.*`, including agreement gate knobs)
- `lib/advisory_state.py` (`advisory_gate.shown_advice_ttl_s`)
- `lib/meta_ralph.py` (`meta_ralph.*`)
- `lib/pipeline.py` (`values.queue_batch_size`, `pipeline.*`)
- `lib/advisory_synthesizer.py` (`synthesizer.*`)
- `lib/semantic_retriever.py` (`semantic.*`, `triggers.*`)
- `lib/memory_store.py` (`memory_emotion.*`, `memory_learning.*`, `memory_retrieval_guard.*`)
- `lib/promoter.py` / `lib/auto_promote.py` (`promotion.*`)
- `lib/eidos/models.py` (`eidos.*`, inherited `values.*` budget keys)
- `lib/advisory_packet_store.py` (`advisory_packet_store.*`)
- `lib/advisory_prefetch_worker.py` (`advisory_prefetch.*`)
- `lib/queue.py` (`queue.*`)
- `lib/context_sync.py` (`sync.*`)
- `lib/production_gates.py` (`production_gates.*`)
- `lib/chip_merger.py` (`chip_merge.*`)
- `lib/memory_capture.py` (`memory_capture.*`)
- `lib/memory_banks.py` (`memory_emotion.write_capture_enabled`)
- `lib/pattern_detection/request_tracker.py` (`request_tracker.*`)
- `lib/advisory_preferences.py` (read path for `advisor.*`)
- `lib/observatory/config.py` (`observatory.*`)
- `lib/feature_flags.py` (`feature_flags.*`)
- `lib/cognitive_learner.py` (via `feature_flags`)
- `lib/chips/runtime.py` (via `feature_flags`)
- `lib/opportunity_scanner.py` (`opportunity_scanner.*`)
- `lib/prediction_loop.py` (`prediction.*`)

Resolver implementation:
- `lib/config_authority.py`

## Operational Rules
- All tuneables writes must be lock-protected and schema-validated.
- Auto-tuner cross-section writes are disabled by default.
- Queue limits are first-class tuneables (`queue.*`) in schema + config.
- Observatory analytics readers that intentionally compare runtime vs baseline
  (for drift/reporting) may read both files directly; runtime behavior modules
  should still resolve through `ConfigAuthority`.

## Hot-Reload Coverage

All modules register via `register_reload()` in `lib/tuneables_reload.py`. When
`~/.spark/tuneables.json` is modified, `check_and_reload()` (called on bridge
cycles) dispatches callbacks for changed sections.

| Section | Module(s) | Reload Label |
|---------|-----------|-------------|
| `advisor` | advisor.py, advisory_preferences.py | `advisor.reload_from`, `advisory_preferences.reload` |
| `advisory_engine` | advisory_engine.py, advisory_emitter.py | `advisory_engine.apply_config`, `advisory_emitter.reload` |
| `advisory_gate` | advisory_gate.py, advisory_state.py | `advisory_gate.reload_from`, `advisory_state.reload_gate_from` |
| `advisory_quality` | advisory_preferences.py | `advisory_preferences.reload.quality` |
| `auto_tuner` | advisor.py | `advisor.reload_from.auto_tuner` |
| `bridge_worker` | bridge_cycle.py | `bridge_worker.reload_from` |
| `chip_merge` | chip_merger.py | `chip_merger.reload` |
| `eidos` | eidos/models.py | `eidos.models.reload_from` |
| `memory_capture` | memory_capture.py | `memory_capture.reload_from` |
| `memory_emotion` | memory_banks.py, memory_store.py | `memory_banks.reload`, `memory_store.reload.emotion` |
| `memory_learning` | memory_store.py | `memory_store.reload.learning` |
| `memory_retrieval_guard` | memory_store.py | `memory_store.reload.guard` |
| `meta_ralph` | meta_ralph.py | `meta_ralph.reload_from` |
| `pipeline` | pipeline.py | `pipeline.reload_from_section` |
| `promotion` | promoter.py, auto_promote.py | `promoter.reload`, `auto_promote.reload` |
| `queue` | queue.py | `queue.apply_config` |
| `request_tracker` | request_tracker.py | `request_tracker.reload_from` |
| `semantic` | semantic_retriever.py | `semantic_retriever.reload` |
| `sync` | context_sync.py | `context_sync.reload` |
| `synthesizer` | advisory_synthesizer.py | `advisory_synthesizer.reload` |
| `triggers` | semantic_retriever.py | `semantic_retriever.reload.triggers` |
| `feature_flags` | feature_flags.py | `feature_flags.reload` |
| `opportunity_scanner` | opportunity_scanner.py | `opportunity_scanner` |
| `values` | eidos/models.py, pipeline.py | `eidos.models.reload_from_values`, `pipeline.reload_from` |

## Migration Standard
- New modules should load runtime knobs via `resolve_section(...)`.
- Env overrides should use explicit mappings (`env_bool/env_int/env_float/env_str`).
- Reload callbacks should re-resolve through `ConfigAuthority` rather than raw section payloads.

## Environment Variable Override Reference

Only keys with explicit `env_overrides` mappings respond to env vars. All others require file edits.

### Advisory Engine (`advisory_engine`)
| Env Var | Key | Type |
|---------|-----|------|
| `SPARK_ADVISORY_ENGINE` | `enabled` | bool |
| `SPARK_ADVISORY_MAX_MS` | `max_ms` | float |
| `SPARK_ADVISORY_INCLUDE_MIND` | `include_mind` | bool |
| `SPARK_ADVISORY_PREFETCH_QUEUE` | `prefetch_queue_enabled` | bool |
| `SPARK_ADVISORY_PREFETCH_INLINE` | `prefetch_inline_enabled` | bool |
| `SPARK_ADVISORY_PACKET_FALLBACK_EMIT` | `packet_fallback_emit_enabled` | bool |
| `SPARK_ADVISORY_FALLBACK_RATE_GUARD` | `fallback_rate_guard_enabled` | bool |
| `SPARK_ADVISORY_FALLBACK_RATE_MAX_RATIO` | `fallback_rate_max_ratio` | float |
| `SPARK_ADVISORY_FALLBACK_RATE_WINDOW` | `fallback_rate_window` | int |
| `SPARK_ADVISORY_FALLBACK_BUDGET_CAP` | `fallback_budget_cap` | int |
| `SPARK_ADVISORY_FALLBACK_BUDGET_WINDOW` | `fallback_budget_window` | int |
| `SPARK_ADVISORY_PREFETCH_INLINE_MAX_JOBS` | `prefetch_inline_max_jobs` | int |
| `SPARK_ADVISORY_REQUIRE_ACTION` | `actionability_enforce` | bool |
| `SPARK_ADVISORY_FORCE_PROGRAMMATIC_SYNTH` | `force_programmatic_synth` | bool |
| `SPARK_ADVISORY_SELECTIVE_AI_SYNTH` | `selective_ai_synth_enabled` | bool |
| `SPARK_ADVISORY_SELECTIVE_AI_MIN_REMAINING_MS` | `selective_ai_min_remaining_ms` | float |
| `SPARK_ADVISORY_SELECTIVE_AI_MIN_AUTHORITY` | `selective_ai_min_authority` | str |
| `SPARK_ADVISORY_SESSION_KEY_INCLUDE_RECENT_TOOLS` | `session_key_include_recent_tools` | bool |
| `SPARK_ADVISORY_STALE_S` | `delivery_stale_s` | float |
| `SPARK_ADVISORY_TEXT_REPEAT_COOLDOWN_S` | `advisory_text_repeat_cooldown_s` | float |
| `SPARK_ADVISORY_GLOBAL_DEDUPE_COOLDOWN_S` | `global_dedupe_cooldown_s` | float |

### Advisory Gate (`advisory_gate`)
| Env Var | Key | Type |
|---------|-----|------|
| `SPARK_ADVISORY_AGREEMENT_GATE` | `agreement_gate_enabled` | bool |
| `SPARK_ADVISORY_AGREEMENT_MIN_SOURCES` | `agreement_min_sources` | int |
| `SPARK_ADVISORY_EMIT_WHISPERS` | `emit_whispers` | bool |
| `SPARK_ADVISORY_SHOWN_TTL_S` | `shown_advice_ttl_s` | int |

### Synthesizer (`synthesizer`)
| Env Var | Key | Type |
|---------|-----|------|
| `SPARK_SYNTH_MODE` | `mode` | str |
| `SPARK_SYNTH_TIMEOUT` | `ai_timeout_s` | float |
| `SPARK_SYNTH_PREFERRED_PROVIDER` | `preferred_provider` | str |
| `SPARK_MINIMAX_MODEL` | `minimax_model` | str |

### Bridge Worker (`bridge_worker`)
| Env Var | Key | Type |
|---------|-----|------|
| `SPARK_BRIDGE_MIND_SYNC_ENABLED` | `mind_sync_enabled` | bool |
| `SPARK_BRIDGE_MIND_SYNC_LIMIT` | `mind_sync_limit` | int |
| `SPARK_BRIDGE_MIND_SYNC_MIN_READINESS` | `mind_sync_min_readiness` | float |
| `SPARK_BRIDGE_MIND_SYNC_MIN_RELIABILITY` | `mind_sync_min_reliability` | float |
| `SPARK_BRIDGE_MIND_SYNC_MAX_AGE_S` | `mind_sync_max_age_s` | int |
| `SPARK_BRIDGE_MIND_SYNC_DRAIN_QUEUE` | `mind_sync_drain_queue` | bool |
| `SPARK_BRIDGE_MIND_SYNC_QUEUE_BUDGET` | `mind_sync_queue_budget` | int |

### Context Sync (`sync`)
| Env Var | Key | Type |
|---------|-----|------|
| `SPARK_SYNC_MODE` | `mode` | str |
| `SPARK_SYNC_MIND_LIMIT` | `mind_limit` | int |

### Advisory Prefetch (`advisory_prefetch`)
| Env Var | Key | Type |
|---------|-----|------|
| `SPARK_ADVISORY_PREFETCH_WORKER` | `worker_enabled` | bool |

### Memory (`memory_emotion`)
| Env Var | Key | Type |
|---------|-----|------|
| `SPARK_MEMORY_EMOTION_WRITE_CAPTURE` | `write_capture_enabled` | bool |
| `SPARK_ADVISORY_MEMORY_EMOTION_ENABLED` | `enabled` | bool |
| `SPARK_ADVISORY_MEMORY_EMOTION_WEIGHT` | `retrieval_state_match_weight` | float |
| `SPARK_ADVISORY_MEMORY_EMOTION_MIN_SIM` | `retrieval_min_state_similarity` | float |

### Feature Flags (`feature_flags`)
| Env Var | Key | Type |
|---------|-----|------|
| `SPARK_PREMIUM_TOOLS` | `premium_tools` | bool |
| `SPARK_CHIPS_ENABLED` | `chips_enabled` | bool |
| `SPARK_ADVISORY_DISABLE_CHIPS` | `advisory_disable_chips` | bool |

### Advisor (`advisor`)
| Env Var | Key | Type |
|---------|-----|------|
| `SPARK_ADVISORY_REPLAY_ENABLED` | `replay_enabled` | bool |
| `SPARK_ADVISORY_REPLAY_MIN_STRICT` | `replay_min_strict` | int |
| `SPARK_ADVISORY_REPLAY_MIN_DELTA` | `replay_min_delta` | float |
| `SPARK_ADVISORY_REPLAY_MAX_RECORDS` | `replay_max_records` | int |
| `SPARK_ADVISORY_REPLAY_MAX_AGE_S` | `replay_max_age_s` | int |
| `SPARK_ADVISORY_REPLAY_STRICT_WINDOW_S` | `replay_strict_window_s` | int |
| `SPARK_ADVISORY_REPLAY_MIN_CONTEXT` | `replay_min_context` | float |
| `SPARK_ADVISOR_MIND_MAX_STALE_S` | `mind_max_stale_s` | float |
| `SPARK_ADVISOR_MIND_STALE_ALLOW_IF_EMPTY` | `mind_stale_allow_if_empty` | bool |
| `SPARK_ADVISOR_MIND_MIN_SALIENCE` | `mind_min_salience` | float |
| `SPARK_ADVISOR_MIND_RESERVE_SLOTS` | `mind_reserve_slots` | int |
| `SPARK_ADVISOR_MIND_RESERVE_MIN_RANK` | `mind_reserve_min_rank` | float |

### Retrieval (`retrieval`)
| Env Var | Key | Type |
|---------|-----|------|
| `SPARK_RETRIEVAL_LEVEL` | `level` | str |
| `SPARK_RETRIEVAL_MODE` | `mode` | str |
| `SPARK_ADVISORY_MINIMAX_FAST_RERANK` | `minimax_fast_rerank` | bool |
| `SPARK_ADVISORY_MINIMAX_TOP_K` | `minimax_fast_rerank_top_k` | int |
| `SPARK_ADVISORY_MINIMAX_MIN_ITEMS` | `minimax_fast_rerank_min_items` | int |
| `SPARK_ADVISORY_MINIMAX_MIN_COMPLEXITY` | `minimax_fast_rerank_min_complexity` | int |
| `SPARK_ADVISORY_MINIMAX_HIGH_VOLUME_ITEMS` | `minimax_fast_rerank_high_volume_min_items` | int |
| `SPARK_ADVISORY_MINIMAX_REQUIRE_AGENTIC` | `minimax_fast_rerank_require_agentic` | bool |
| `SPARK_ADVISORY_MINIMAX_MODEL` | `minimax_fast_rerank_model` | str |
| `SPARK_ADVISORY_MINIMAX_TIMEOUT_S` | `minimax_fast_rerank_timeout_s` | float |
| `SPARK_ADVISORY_MINIMAX_COOLDOWN_S` | `minimax_fast_rerank_cooldown_s` | float |

### Emitter (via `advisory_engine`)
| Env Var | Key | Type |
|---------|-----|------|
| `SPARK_ADVISORY_EMIT` | `emit_enabled` | bool |
| `SPARK_ADVISORY_MAX_CHARS` | `emit_max_chars` | int |
| `SPARK_ADVISORY_FORMAT` | `emit_format` | str |

### Bridge Worker Extended (`bridge_worker`)
| Env Var | Key | Type |
|---------|-----|------|
| `SPARK_OPENCLAW_NOTIFY` | `openclaw_notify` | bool |
| `SPARK_BRIDGE_STEP_TIMEOUT_S` | `step_timeout_s` | float |
| `SPARK_BRIDGE_DISABLE_TIMEOUTS` | `disable_timeouts` | bool |
| `SPARK_BRIDGE_GC_EVERY` | `gc_every` | int |
| `SPARK_BRIDGE_STEP_EXECUTOR_WORKERS` | `step_executor_workers` | int |

### Opportunity Scanner (`opportunity_scanner`)
| Env Var | Key | Type |
|---------|-----|------|
| `SPARK_OPPORTUNITY_SCANNER` | `enabled` | bool |
| `SPARK_OPPORTUNITY_SELF_MAX` | `self_max_items` | int |
| `SPARK_OPPORTUNITY_USER_MAX` | `user_max_items` | int |
| `SPARK_OPPORTUNITY_HISTORY_MAX` | `max_history_lines` | int |
| `SPARK_OPPORTUNITY_SELF_DEDUP_WINDOW_S` | `self_dedup_window_s` | float |
| `SPARK_OPPORTUNITY_SELF_RECENT_LOOKBACK` | `self_recent_lookback` | int |
| `SPARK_OPPORTUNITY_SELF_CATEGORY_CAP` | `self_category_cap` | int |
| `SPARK_OPPORTUNITY_USER_SCAN` | `user_scan_enabled` | bool |
| `SPARK_OPPORTUNITY_SCAN_EVENT_LIMIT` | `scan_event_limit` | int |
| `SPARK_OPPORTUNITY_OUTCOME_WINDOW_S` | `outcome_window_s` | float |
| `SPARK_OPPORTUNITY_OUTCOME_LOOKBACK` | `outcome_lookback` | int |
| `SPARK_OPPORTUNITY_PROMOTION_MIN_SUCCESSES` | `promotion_min_successes` | int |
| `SPARK_OPPORTUNITY_PROMOTION_MIN_EFFECTIVENESS` | `promotion_min_effectiveness` | float |
| `SPARK_OPPORTUNITY_PROMOTION_LOOKBACK` | `promotion_lookback` | int |
| `SPARK_OPPORTUNITY_LLM_ENABLED` | `llm_enabled` | bool |
| `SPARK_OPPORTUNITY_LLM_PROVIDER` | `llm_provider` | str |
| `SPARK_OPPORTUNITY_LLM_TIMEOUT_S` | `llm_timeout_s` | float |
| `SPARK_OPPORTUNITY_LLM_MAX_ITEMS` | `llm_max_items` | int |
| `SPARK_OPPORTUNITY_LLM_MIN_CONTEXT_CHARS` | `llm_min_context_chars` | int |
| `SPARK_OPPORTUNITY_LLM_COOLDOWN_S` | `llm_cooldown_s` | float |
| `SPARK_OPPORTUNITY_DECISION_LOOKBACK` | `decision_lookback` | int |
| `SPARK_OPPORTUNITY_DISMISS_TTL_S` | `dismiss_ttl_s` | float |

### Prediction (`prediction`)
| Env Var | Key | Type |
|---------|-----|------|
| `SPARK_PREDICTION_TOTAL_BUDGET` | `total_budget` | int |
| `SPARK_PREDICTION_DEFAULT_SOURCE_BUDGET` | `default_source_budget` | int |
| `SPARK_PREDICTION_SOURCE_BUDGETS` | `source_budgets` | str |
| `SPARK_PREDICTION_AUTO_LINK` | `auto_link_enabled` | bool |
| `SPARK_PREDICTION_AUTO_LINK_INTERVAL_S` | `auto_link_interval_s` | float |
| `SPARK_PREDICTION_AUTO_LINK_LIMIT` | `auto_link_limit` | int |
| `SPARK_PREDICTION_AUTO_LINK_MIN_SIM` | `auto_link_min_sim` | float |

## Hot-Reload Status

Modules with `register_reload()` pick up file changes automatically (1-30s). Others require restart.

| Section | Hot-Reload | Module |
|---------|-----------|--------|
| `advisory_engine` | Yes | `advisory_engine.py`, `advisory_emitter.py` |
| `advisory_gate` | Yes | `advisory_gate.py`, `advisory_state.py` |
| `advisor` | Yes | `advisor.py` |
| `meta_ralph` | Yes | `meta_ralph.py` |
| `pipeline` | Yes | `pipeline.py` |
| `bridge_worker` | Yes | `bridge_cycle.py` |
| `queue` | Yes | `queue.py` |
| `eidos` | Yes | `eidos/models.py` |
| `synthesizer` | Yes | `advisory_synthesizer.py` |
| `advisory_packet_store` | Yes | `advisory_packet_store.py` |
| `advisory_prefetch` | Yes | `advisory_prefetch_worker.py` |
| `memory_capture` | Yes | `memory_capture.py` |
| `request_tracker` | Yes | `request_tracker.py` |
| `flow` | Yes | `validate_and_store.py` |
| `semantic` | Yes | `semantic_retriever.py` |
| `triggers` | Yes | `semantic_retriever.py` |
| `sync` | Yes | `context_sync.py` |
| `feature_flags` | Yes | `feature_flags.py` |
| `opportunity_scanner` | Yes | `opportunity_scanner.py` |

## Verification
- `tests/test_config_authority.py`
- `tests/test_tuneables_alignment.py`
- `tests/test_advisory_engine_evidence.py::test_load_engine_config_env_override_wins`
- `tests/test_advisory_gate_config.py::test_load_gate_config_env_overrides`
- `tests/test_advisory_state.py::test_load_state_gate_config_env_override`
- `tests/test_pipeline_config_authority.py`
- `tests/test_advisory_synthesizer_env.py::test_load_synth_config_respects_env_override`
- `tests/test_semantic_retriever.py::test_load_config_reads_sections_and_env_overrides`
- `tests/test_memory_store_config_authority.py`
- `tests/test_promotion_config_authority.py`
- `tests/test_eidos_config_authority.py`
- `tests/test_packet_prefetch_config_authority.py`
- `tests/test_context_sync_policy.py`
- `tests/test_production_gates_config_authority.py`
- `tests/test_remaining_config_authority.py`
- `tests/test_runtime_tuneable_sections.py`
- `tests/test_pr1_config_authority.py`
- `tests/test_pr2_config_authority.py`
