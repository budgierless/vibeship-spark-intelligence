# OpenClaw System Brief: Trend Intelligence → Automated Build Flow

Purpose:
Use this as the operational, project-wide reference for OpenClaw context.

- What exists now
- What remains to implement
- What to monitor and tune
- Env/config that controls behavior

---

## A) Current implemented state

### 1) Trend discovery (data engine)
- Location: `spark-x-builder/scripts/daily_trend_research.py`
- Responsibility:
  - Searches X for configured trend topics
  - Extracts engagement-weighted insights
  - Builds trend profiles
  - Generates candidate groups: `skills`, `mcps`, `startup_ideas`
  - Emits JSON run result
- Implemented quality/cost controls (defaults):
  - `TREND_DAILY_ROW_BUDGET=180`
  - `TREND_MAX_TOPIC_ROWS=36`
  - `TREND_QUERY_LIMIT_HIGH=24`, `...MEDIUM=18`, `...LOW=12`
  - `TREND_MIN_ENGAGEMENT_SCORE=45.0`
  - `TREND_MIN_LIKES=4`, `TREND_MIN_RETWEETS=1`, `TREND_MIN_REPLIES=1`
  - `TREND_MAX_FRESHNESS_HOURS=96`
  - `TREND_MIN_CANDIDATE_BUCKET_SCORE=20`
  - Viral filter:
    - `TREND_VIRAL_MIN_SCORE=0.72`
    - `TREND_VIRAL_MIN_EVIDENCE=12`
    - `TREND_VIRAL_TOP_QUANTILE=0.10`
    - `TREND_VIRAL_MOMENTUM_MIN=1.40`
    - `TREND_VIRAL_ABSOLUTE_NEW=0.78`

### 2) Scheduler integration
- Location: `spark_scheduler.py` (`task_daily_research`)
- Responsibility:
  - Runs `spark-x-builder` script via subprocess
  - Parses JSON result
  - Writes handoff file
  - Builds queue manifest for OpenClaw consumption
  - Notifies optional webhooks
- Implemented queue gates:
  - `TREND_BUILD_QUEUE_MIN_CONFIDENCE=0.62`
  - `TREND_BUILD_QUEUE_MIN_TREND_SCORE=0.72`
  - `TREND_BUILD_QUEUE_MIN_EVIDENCE=10`
  - `TREND_MAX_QUEUED_ITEMS=24`
- Routes engine by:
  - candidate `assigned_engine` then fallbacks:
    - `default_agent` / `target_engine` / `build_plan.target_engine`
    - bucket defaults (`TREND_BUILD_TARGET_SKILL`, `...MCP`, `...STARTUP`)
  - canonicalized names: `claude->codex`, `gpt->opus`

### 3) Existing documentation added
- `TREND_FLOW_SCHEMA.md`  
  Full schemas for builder output, handoff, manifest, env defaults.
- `OPENCLAW_TREND_FLOW_BRIEF.md`
  Consumption instructions and implementation skeleton for OpenClaw.

### 4) Written artifact locations
- `~/.spark/claw_integration/latest_trend_handoff.json`
- `~/.openclaw/workspace/spark_build_queue/latest_build_queue.json`
- `~/.openclaw/workspace/spark_build_queue/trend_build_queue_<RUN_ID>.json`
- `~/.spark/claw_integration/build_dispatch_log.jsonl`

---

## B) Remaining OpenClaw-side work (priority)

### P0 — Required before full handoff automation
1. Build queue consumer worker
   - Poll latest queue manifest
   - De-duplicate by `job_id` + `run_id`
   - Route by `assigned_engine`
   - Write per-job execution status
2. Engine runner adapters
   - `codex` runner
   - `minimax` runner
   - `opus` runner
3. Job idempotency + retry policy
   - prevent duplicate execution on same manifest reruns
   - backoff retries and dead-letter on repeated failure

### P1 — Robustness / operations
4. State/telemetry store
   - Persist queue snapshot version, job state, completion timestamps, errors
5. Wake/hot path integration
   - Confirm wake behavior and poll frequency
   - Ensure manifest read is atomic or retry-safe
6. Post-run eventing
   - Emit completion event back to Spark or OpenClaw dashboard

### P2 — Cost/quality upgrades
7. Per-engine budget controls
   - max jobs/hour and max cost per cycle
8. Fail-fast candidate guardrails
   - optionally require higher confidence if evidence weak
9. Optional external moderation filters
   - block unsafe/low-quality candidate outputs before execution

### P3 — Expansion modules (next)
10. Trend scoring feedback loop
   - mark queue entries that shipped vs. failed
   - feed back to scheduler thresholds
11. Repo creation policy
   - enforce path uniqueness and collision strategy
12. Multi-repo target routing
   - route startup ideas into dedicated infra repo if needed

---

## C) OpenClaw worker contract (required behavior)

Input: `latest_build_queue.json`

For each job:
1. Validate required keys:
   - `job_id`, `run_id`, `assigned_engine`, `build_type`, `target_path`, `source_payload`
2. Resolve engine:
   - `codex` -> skill workflow runner
   - `minimax` -> MCP/automation workflow
   - `opus` -> startup/launch workflow
3. Execute with manifest context:
   - prefer `one_shot_spawn` if present
   - include trend context + confidence + `source_payload` for reproducibility
4. Emit status:
   - `queued`, `running`, `done`, `failed`
   - include error message and timestamp for failures
5. Persist completion:
   - mark in local state (SQLite/JSONL ok)
   - support at-least-once semantics safely

---

## D) Repo boundaries and why this split

- Keep trend intelligence in Spark/intelligence + spark-x-builder:
  - API calls, scoring, candidate quality logic
- Keep execution/orchestration in OpenClaw:
  - job execution, retries, failure handling, repository side effects

This avoids entangling expensive discovery logic with heavy build orchestration and is easier to scale.

---

## E) “Can OpenClaw understand the full system?” setup recommendations

OpenClaw should be fed these files first in this order:
1. `OPENCLAW_FULL_SYSTEM_BRIEF.md` (this file)
2. `OPENCLAW_TREND_FLOW_BRIEF.md`
3. `TREND_FLOW_SCHEMA.md`
4. `SCHEDULER.md` and `X_PLAYBOOK.md` (existing)

---

## F) Environment checklist (single source)

- Trend builder:
  - `SPARK_X_BUILDER_PATH`
  - all `TREND_*` config vars from section A1
- Scheduler:
  - `TREND_BUILD_TARGET_SKILL` / `TREND_BUILD_TARGET_MCP` / `TREND_BUILD_TARGET_STARTUP`
  - `TREND_BUILD_QUEUE_MIN_CONFIDENCE`
  - `TREND_BUILD_QUEUE_MIN_TREND_SCORE`
  - `TREND_BUILD_QUEUE_MIN_EVIDENCE`
  - `TREND_MAX_QUEUED_ITEMS`
  - `OPENCLAW_WEBHOOK_URL`
  - `CLAWDBOT_WEBHOOK_URL`
  - `TREND_NOTIFY_OPENCLAW` (default 1)
  - `TREND_WAKE_OPENCLAW` (default 0)

---

## G) Suggested OpenClaw bootstrap command sequence

1. Confirm scheduler writes manifest:
   - `python spark_scheduler.py --task daily_research --force`
2. Validate files:
   - `~/.openclaw/workspace/spark_build_queue/latest_build_queue.json`
3. Start worker:
   - (new worker to be implemented) reads manifest and executes jobs
4. Confirm status persistence and completion events.

---

## H) Open decisions / assumptions

- High engagement thresholds are intentionally strict to reduce API spend.
- Queue is quality-gated first (confidence/trend score/evidence) before any execution.
- Engine assignment currently follows configured defaults + overrides from candidates.
- OpenClaw remains the execution brain; scheduler remains the trend brain.

