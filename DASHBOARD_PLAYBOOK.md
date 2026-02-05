# Spark Intelligence Dashboard Playbook

Purpose: keep the control layer visible, enforceable, and traceable.

Dashboard change rule: if something should appear on a dashboard, add it to
`DASHBOARD_TODOS.md` first. Ship dashboard updates in batches, not as drive-by edits.

## Core rule
Every metric must drill down to `trace_id` -> steps -> evidence -> validation.

**Start Services**
Recommended (all services + dashboards):
1. `python -m spark.cli up`
2. Or `spark up`

Repo shortcuts:
1. `./scripts/run_local.sh`
2. Windows: `start_spark.bat`

Dashboard only (no background workers):
1. `python dashboard.py`

Stop services:
1. `python -m spark.cli down`
2. Or `spark down`

Ports (defaults; override via env, see `lib/ports.py`):
1. Spark Lab dashboard: `http://localhost:${SPARK_DASHBOARD_PORT:-8585}`
2. Spark Pulse (chips/tuneables): `http://localhost:${SPARK_PULSE_PORT:-8765}`
3. Meta-Ralph Quality Analyzer: `http://localhost:${SPARK_META_RALPH_PORT:-8586}`
4. sparkd health: `http://127.0.0.1:${SPARKD_PORT:-8787}/health`
5. Mind server health (if running): `http://127.0.0.1:${SPARK_MIND_PORT:-8080}/health`

Port overrides (env):
1. `SPARKD_PORT`
2. `SPARK_DASHBOARD_PORT`
3. `SPARK_PULSE_PORT`
4. `SPARK_META_RALPH_PORT`
5. `SPARK_MIND_PORT`
6. Adapters can also set `SPARKD_URL` directly.

**Dashboards (Spark Lab)**
Mission Control (default):
1. `/` or `/mission`
2. Health, queues, watchers, run KPIs, trace/run drilldowns.

Learning Factory:
1. `/learning`
2. Funnel metrics and distillation lifecycle.

Rabbit Hole Recovery:
1. `/rabbit`
2. Repeat failures, thrash, and recovery signals.

Acceptance & Validation Board:
1. `/acceptance`
2. Acceptance plans, deferrals, validation gaps, evidence stats.

Ops Console:
1. `/ops`
2. Skills, orchestration, and operational stats.

Dashboards Index:
1. `/dashboards`
2. Links + start commands + data sources.

**Dashboards (Separate Apps)**
1. Meta-Ralph Quality Analyzer: `http://localhost:${SPARK_META_RALPH_PORT:-8586}`
2. Spark Pulse (chips/tuneables): `http://localhost:${SPARK_PULSE_PORT:-8765}`

**CLI Dashboards (No Server)**
1. EIDOS quick health: `python scripts/eidos_dashboard.py`
2. Spark Intelligence CLI: `python scripts/spark_dashboard.py`

**Daily operator loop (10 minutes)**
1. Open Mission Control and confirm green status for services, queue, and EIDOS activity.
2. Scan Watchers feed for new red/yellow alerts and click into the triggering episode.
3. Check Learning Factory funnel. If retrieved >> used or helped drops, investigate top ignored items.
4. Check Acceptance Board for pending critical tests or expired deferrals.
5. Open Meta-Ralph Quality Analyzer and confirm pass rate and outcome tracking are non-zero.
6. If Meta-Ralph outcome stats are flat, verify `track_retrieval()` and `track_outcome()` wiring.

**Cross-dashboard iteration loop (15 minutes)**
1. Mission Control: pick a weak KPI or alert and open its `trace_id`.
2. Learning Factory: find the top offending pattern and its distillation source.
3. Meta-Ralph: inspect verdict mix and the weakest score dimension.
4. Acceptance Board: confirm evidence exists for the change, or log a validation gap.
5. Rabbit Hole: check for repeated failures of the same signature.
6. Apply a small fix, then re-check Mission Control + Meta-Ralph for movement.

**Data Sources (No Hallucinations)**
1. Spark Lab: `~/.spark/queue/events.jsonl`, `~/.spark/bridge_worker_heartbeat.json`, `~/.spark/eidos.db`, `~/.spark/truth_ledger.json`, `~/.spark/acceptance_plans.json`, `~/.spark/evidence.db`, `~/.spark/cognitive_insights.json`, `~/.spark/logs/semantic_retrieval.jsonl`, `~/.spark/advisor/metrics.json`.
2. Meta-Ralph Quality Analyzer: `~/.spark/meta_ralph/roast_history.json`, `~/.spark/meta_ralph/outcome_tracking.json`, `~/.spark/meta_ralph/learnings_store.json`, `~/.spark/advisor/effectiveness.json`, `~/.spark/advisor/recent_advice.jsonl`.
3. EIDOS CLI: `~/.spark/eidos.db`, `~/.spark/truth_ledger.json`, `~/.spark/policy_patches.json`, `~/.spark/minimal_mode_state.json`, `~/.spark/minimal_mode_history.jsonl`.
4. Spark Intelligence CLI: `~/.spark/cognitive_insights.json`, `~/.spark/research_reports/`, `~/.spark/sparknet/collective/`.

**Known Gaps**
1. Legacy Meta-Ralph roast records without `trace_id` won't deep-link; new records include it.

**Logging & Rotation**
Defaults (override via env):
1. Log directory: `SPARK_LOG_DIR` (default `~/.spark/logs`)
2. Rotation size: `SPARK_LOG_MAX_BYTES` (default 10 MB)
3. Backups: `SPARK_LOG_BACKUPS` (default 5)
4. Tee to console: `SPARK_LOG_TEE` (default on)

**Queue Limits**
Defaults (override via env):
1. `SPARK_QUEUE_MAX_EVENTS` (default 10000)
2. `SPARK_QUEUE_MAX_BYTES` (default 10 MB)

**Watchdog Settings**
Key flags:
1. `--fail-threshold` (default 3 consecutive failures before restart)
2. `--bridge-stale-s` (default 90 seconds heartbeat staleness)
3. `--startup-delay` (default 15 seconds grace period)

**Per-change checklist (before and after edits)**
1. Run pipeline health check: `python tests/test_pipeline_health.py`
2. Verify trace_id is present on new steps, evidence, and outcomes.
3. Validate that the dashboard drilldown shows evidence for the change.
4. If validation is missing, add a test or explicit evidence link.

**Trace-first drilldown**
1. Start from a metric or alert.
2. Open the `trace_id` for that event.
3. Review steps in order and confirm evidence exists for each step.
4. If evidence is missing, log a validation gap and block promotion.

URL shortcuts:
1. `/mission?trace_id=<trace_id>`
2. `/mission?episode_id=<episode_id>`

CLI helpers:
1. `python scripts/trace_query.py --trace-id <trace_id>`
2. `python scripts/trace_backfill.py --dry-run`
3. `python scripts/trace_backfill.py --apply`

**Trace binding enforcement**
Default: TRACE_GAP is warning-only.
Strict mode: set `SPARK_TRACE_STRICT=1` to block actions on trace gaps.

**Mission Control usage**
Goal: answer "Are we stable and learning?"
1. If any service is stale or down, fix ops first.
2. If queue oldest event age spikes, inspect bridge cycle health.
3. If EIDOS activity is zero, check EIDOS enabled flag and bridge cycle errors.
4. Use trace_id drilldown to see the latest active episode timeline.

**Rabbit Hole Recovery usage**
Goal: detect and exit loops.
1. Use the repeat failure scoreboard to identify top error signatures.
2. Open the offending trace_id and confirm if evidence is missing.
3. Trigger Escape Protocol if the same signature repeats 2+ times.
4. After escape, ensure a learning artifact was created and linked.

**Learning Factory usage**
Goal: compound intelligence, not just store it.
1. Follow the funnel: retrieved -> cited -> used -> helped -> promoted.
2. If retrieved is high but helped is low, demote or refine the top offenders.
3. If promoted is zero, check validation counts and outcome links.
4. Review contradicted items weekly and schedule revalidation.

**Acceptance and Validation Board usage**
Goal: turn "done" into a contract.
1. Ensure every active episode has an approved acceptance plan.
2. Prioritize P1 tests and close validation gaps before new work.
3. If deferrals are expiring, resolve or explicitly re-defer.

**APIs (JSON)**
1. `/api/mission`
2. `/api/learning`
3. `/api/rabbit`
4. `/api/acceptance`
5. `/api/ops`
6. `/api/trace?trace_id=<trace_id>`
7. `/api/run?episode_id=<episode_id>`
8. `/api/status/stream` (SSE)
9. `/api/ops/stream` (SSE)

**Weekly maintenance**
1. Review top repeated failures and add a distillation or guardrail.
2. Review top contradicted insights and downgrade reliability.
3. Audit evidence store for expiring high-value artifacts and extend retention.
