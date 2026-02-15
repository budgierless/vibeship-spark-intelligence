# Spark Carmack Optimization Implementation

Date: 2026-02-12
Owner: Spark Intelligence
Status: Implemented (phase checkpoint)

## Why We Are Doing This

Spark was producing value, but too much optional complexity was creating noise:
- optional sync adapters failing repeatedly without helping core flow
- advisory fallback emissions inflating low-signal output
- memory bundles including operational error artifacts
- chip merge spending cycles on duplicate churn

The Carmack rule we are applying:
- keep only what improves the critical path
- degrade everything else to optional
- make defaults lightweight and deterministic

Critical path:
`retrieval -> advisory -> action -> outcome`

## What We Changed

1. Sync path defaulted to core adapters only:
- default mode: `openclaw`, `exports`
- optional adapters (`claude_code`, `cursor`, `windsurf`, `clawdbot`) are opt-in

2. Advisory fallback emission is now opt-in:
- packet no-emit fallback is disabled by default
- this reduces synthetic/noisy fallback emissions

3. Memory evidence hygiene tightened:
- tool-error style telemetry and primitive operational text are filtered from advisory memory fusion
- duplicate memory evidence is deduped before ranking

4. Advisory hot path trimmed:
- pre-tool advisory no longer builds the multi-source memory bundle on the critical path
- packet lineage is inferred from emitted advice source labels

5. Chip merge duplicate churn throttling:
- when merge cycles are mostly duplicates with no new merges, merge enters cooldown
- throttle thresholds are tuneable

## Runtime Controls

Environment:
- `SPARK_SYNC_MODE=core|all`
- `SPARK_SYNC_TARGETS=openclaw,exports,...`
- `SPARK_SYNC_DISABLE_TARGETS=cursor,...`
- `SPARK_ADVISORY_PACKET_FALLBACK_EMIT=0|1`
- `SPARK_ADVISORY_FALLBACK_RATE_GUARD=0|1`
- `SPARK_ADVISORY_FALLBACK_RATE_MAX_RATIO=0.0..1.0`
- `SPARK_ADVISORY_FALLBACK_RATE_WINDOW=10..500`

Tuneables (`~/.spark/tuneables.json`):
- `sync.mode`
- `sync.adapters_enabled`
- `sync.adapters_disabled`
- `advisory_engine.packet_fallback_emit_enabled`
- `advisory_engine.fallback_rate_guard_enabled`
- `advisory_engine.fallback_rate_max_ratio`
- `advisory_engine.fallback_rate_window`
- `chip_merge.duplicate_churn_ratio`
- `chip_merge.duplicate_churn_min_processed`
- `chip_merge.duplicate_churn_cooldown_s`

## Documentation Integration

When these defaults change, update these docs in the same PR:
1. `docs/SPARK_LIGHTWEIGHT_OPERATING_MODE.md`
2. `Intelligence_Flow_Map.md`
3. `Intelligence_Flow.md`
4. `TUNEABLES.md`
5. `docs/DOCS_INDEX.md`
6. `docs/OPENCLAW_RESEARCH_AND_UPDATES.md` (decision log)

## Success Criteria

- optional adapter errors no longer dominate sync health narrative
- fallback advisory ratio trends down
- memory evidence quality improves (less tool-error contamination)
- chip merge cycles show lower duplicate-only processing
