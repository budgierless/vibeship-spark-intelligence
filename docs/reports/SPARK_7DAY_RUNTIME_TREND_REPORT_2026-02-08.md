# Spark 7-Day Runtime Trend Report (UTC)

**Generated:** 2026-02-08  
**Scope:** live telemetry from `~/.spark` + current gate checks

## Executive Summary

Spark is operationally healthy and actively learning, but the prediction/outcome loop still has attribution inefficiency despite drift improvements in the newer testing approach.

- Runtime health: strong (gates passing, no active watchdog failures, healthy backpressure)
- Learning throughput: high (620 new cognitive insights in last 7 days)
- Prediction loop quality: mixed (very high prediction volume, low recent outcome yield, low coverage)
- FORGE dual scoring: active and useful, early-stage sample size

## Current Health

- `python -m spark.cli health`: all core checks passed.
- `python scripts/production_loop_report.py`: `READY (13/13 passed)`.
- Core metrics snapshot:
  - `stored=730`, `retrieved=500`, `actionable=63`, `acted_on=25`
  - `retrieval_rate=68.5%`
  - `acted_on_rate=39.7%`
  - `strict_trace_coverage=64.0%`
  - `quality_rate=42.5%`

## 7-Day Activity Trend

### Daily volume (UTC)

| Date | Predictions | Outcomes | DEPTH Sessions | FORGE Sessions |
|---|---:|---:|---:|---:|
| 2026-02-02 | 0 | 165 | 0 | 0 |
| 2026-02-03 | 0 | 1198 | 0 | 0 |
| 2026-02-04 | 0 | 24 | 0 | 0 |
| 2026-02-05 | 3635 | 83 | 0 | 0 |
| 2026-02-06 | 820 | 116 | 0 | 0 |
| 2026-02-07 | 321 | 10 | 98 | 0 |
| 2026-02-08 | 205 | 1 | 29 | 5 |

### Interpreted trend

- Prediction volume spike on 2026-02-05 appears test-influenced and is materially higher than subsequent days.
- DEPTH/ FORGE became active on 2026-02-07 and 2026-02-08.
- Outcomes dropped sharply by 2026-02-07/08, which weakens attribution feedback density.

## Prediction/Outcome Loop Audit

### What improved

- `prediction_state.matched_ids` is populated (`500` retained), indicating matching has occurred historically.
- Strict gate checks still pass (`strict_acted_on_rate`, `strict_trace_coverage`, `strict_effectiveness`).

### What is still weak

- Recent cycle stats are zeroed:
  - `prediction_state.last_stats`: `matched=0`, `validated=0`, `contradicted=0`
  - `validation_state.last_stats`: `processed=2`, `validated=0`, `contradicted=0`
- Coverage is low:
  - `insights_with_outcomes=57 / 732`
  - `outcome_coverage=0.078` (7.8%)
- Unlinked outcomes remain high:
  - `total_outcomes=2135`
  - `total_links=365`
  - `unlinked=899`

### Mix analysis (7 days)

- Prediction sources:
  - `chip_merge`: 3926
  - `spark_inject`: 532
  - `sync_context`: 430
- Prediction types:
  - `principle`: 2840
  - `general`: 1907
  - `preference`: 256
- Outcome polarity:
  - `neg`: 1416
  - `pos`: 181

### Root-cause hypothesis (current)

1. Volume imbalance: predictions are over-produced relative to outcomes.
2. Outcome skew: negatives dominate, so many positive expectations cannot validate quickly.
3. Linking gap: too many outcomes stay unlinked, reducing validation throughput.
4. Matcher recency window is tight for low-frequency outcomes (`match_predictions` default `max_age_s=6h`), likely missing slower feedback loops.
5. Outcome collector currently only emits outcomes from `user_prompt` and `post_tool_failure`, while other meaningful outcome events (for example `skill_result`) are not ingested into the same loop.

## FORGE and DEPTH Signal Quality

### DEPTH

- Last 7d sessions: `127`
- Valid pct average (0-100 only): `73.6`
- Data anomaly: 3 sessions with pct >100 (`118`, `460`, `501`), indicating score normalization/logging inconsistency in some records.

### FORGE dual-scored sessions

- Last 24h sessions: `5`
- Average overall step score: `6.5 / 10`
- Dimension averages:
  - `correctness`: `7.0`
  - `code_quality`: `7.25`
  - `domain_expertise`: `6.75`
  - `accessibility_safety`: `7.25`
  - `performance`: `6.75`
  - `process`: `5.75` (lowest)
  - `completeness`: `6.75`

## Recommendations (Prediction/Outcome Loop)

### Priority 1 (high impact, low risk)

1. Add source budgets for prediction generation.
   - Cap `chip_merge`-origin predictions per cycle/day.
   - Keep higher priority for `project_profile` and explicit user-facing signals.
2. Enable scheduled auto-linking for unlinked outcomes.
   - Run `auto_link_outcomes` with conservative threshold (e.g. 0.25-0.35) as a periodic job.
   - Record confidence and avoid hard-linking low-similarity candidates.
3. Expand outcome ingestion set.
   - Include high-signal positive outcomes (e.g. `skill_result`) in `collect_outcomes()`.

### Priority 2 (improve attribution quality)

1. Use adaptive match windows by prediction type.
   - Keep short window for tool-failure patterns.
   - Use longer window for project/milestone and strategic predictions.
2. Prefer hard links before semantic similarity.
   - `trace_id` / `session_id` / `entity_id` exact-link path first.
3. Introduce test/prod namespace in prediction records.
   - Exclude test-generated predictions from reliability updates and KPI rollups.

### Priority 3 (measurement hygiene)

1. Add a loop KPI panel:
   - `prediction_to_outcome_ratio`
   - `unlinked_outcomes`
   - `coverage_7d`
   - `validated_per_100_predictions`
2. Fix DEPTH pct normalization anomalies at write time.
3. Keep a rolling 7-day baseline file for drift detection after test-heavy periods.

## Evidence Sources

- `~/.spark/pipeline_metrics.json`
- `~/.spark/predictions.jsonl`
- `~/.spark/outcomes.jsonl`
- `~/.spark/prediction_state.json`
- `~/.spark/validation_state.json`
- `~/.spark/bridge_worker_heartbeat.json`
- `~/.spark/watchdog_state.json`
- `~/.spark/eidos.db`
- `~/.spark/forge_dual_sessions.jsonl`
- `~/.spark/depth_training.jsonl`

