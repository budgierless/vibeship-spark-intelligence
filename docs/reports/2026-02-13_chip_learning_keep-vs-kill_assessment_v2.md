# Chip Learning Keep-vs-Kill Assessment v2

Date: 2026-02-13  
Scope: indirect chip path (`chips -> distillation -> cognitive memory -> advisory`)

## Executive Decision

Do **not** fully kill chips yet.  
Kill the current telemetry-heavy chip runtime path and keep only a narrow learning pilot.

Current state is not acceptable for broad chip usage, but there is still measurable value in a small subset.

## Evidence (Deep Diagnostics)

Source: `benchmarks/out/chip_learning_diagnostics_deep_v2_report.json`

- rows analyzed: `13455`
- telemetry rate: `99.81%`
- telemetry observer rate: `91.06%`
- statement yield rate: `7.89%`
- learning-quality pass rate: `89.86%`
- merge-eligible learnings: `2`
- missing confidence rate: `7.78%`
- missing quality-score rate: `7.78%`

Relaxed threshold sensitivity (`chip_learning_diagnostics_deep_relaxed_v2_report.json`):
- merge-eligible: `2 -> 4`
- telemetry and statement yield unchanged

Interpretation:
1. Tuneables are not the primary blocker.
2. Primary blocker is runtime emission quality (telemetry and generic chip-level rows).
3. Secondary blocker is schema inconsistency (missing confidence/quality in a notable subset).

## What Was Changed (Shipped)

Runtime and merger hardening:
- `lib/chips/runtime.py`
  - observer-only mode default on (`SPARK_CHIP_OBSERVER_ONLY`, default true)
  - telemetry observer suppression (pre/post tool, user_prompt_signal, etc.)
  - optional chip-id runtime blocklist (`SPARK_CHIP_BLOCKED_IDS`)
  - runtime active-chip filtering before routing
- `lib/chip_merger.py`
  - telemetry observer blocklist in distillation
  - telemetry observer rows are rejected before learning statement distillation
- `scripts/run_chip_learning_diagnostics.py`
  - added observer telemetry rate
  - added missing confidence/quality rates
  - reports schema-quality diagnostics per chip

Validation:
- targeted tests passed (`36 passed`)

## Operational Activation Decision

For `C:\Users\USER\Desktop\vibeship-spark-intelligence`:
- keep active: `social-convo`, `x_social`, `engagement-pulse`
- set global active chips to empty

Rationale:
- these are the only chips with current evidence of potentially learnable domain signals
- generic/core benchmark chips were dominating telemetry with near-zero mergeable learning output

## Keep / Off Matrix (Now)

Keep (pilot):
- `social-convo`
- `x_social`
- `engagement-pulse`

Off (until redesigned):
- `spark-core`
- `bench_core`
- `api-design`
- `quantum`
- `vibecoding`
- `market-intel`
- `marketing`
- `game_dev`
- `moltbook`
- `biz-ops`

## Redesign Requirements Before Re-Enable

1. Observer outputs must carry explicit learning schema:
- `decision`
- `rationale`
- `evidence`
- `expected_outcome`

2. Remove generic telemetry observer pathways from production chips:
- `pre_tool_*`
- `post_tool_*`
- `user_prompt_signal`
- generic `tool_*` observers

3. Enforce confidence/quality-score presence in runtime writes.

4. Re-enable chips only if they pass this gate over a fresh window:
- telemetry rate < 80%
- telemetry observer rate < 50%
- merge-eligible >= 20 per 2k rows
- no advisory harmful/noise regression

## Honest Bottom Line

Chips are currently a noisy collector, not a reliable learning engine.  
With the runtime hardening now in place, chips can still be useful as a narrow distillation sensor layer, but only under strict activation control and schema discipline.
