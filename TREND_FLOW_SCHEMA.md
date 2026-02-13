# Trend Intake → Build Queue Flow (Spark Scheduler + spark-x-builder + OpenClaw)

This file defines the contract for the **daily trend pipeline** after the latest automation changes.

- `spark-x-builder` produces trend intelligence and build candidates.
- `spark_scheduler` converts that output into a routed build queue for OpenClaw/Clawdbot.
- OpenClaw consumes the queue manifest and runs per-job automation by engine (codex/minimax/opus).

---

## 1) Script boundary

- `spark-x-builder/scripts/daily_trend_research.py`
  - Produces a JSON payload (`TrendBuilderResult`) with trending topics + build candidates.
- `spark_scheduler.task_daily_research`
  - Reads the payload from child process output.
  - Persists handoff payload to `~/.spark/claw_integration/latest_trend_handoff.json`.
  - Generates queue manifest to `~/.openclaw/workspace/spark_build_queue/latest_build_queue.json`.

---

## 2) Artifact locations

- **Handoff file:** `~/.spark/claw_integration/latest_trend_handoff.json`
- **Queue manifest:** `~/.openclaw/workspace/spark_build_queue/latest_build_queue.json`
- **Queue snapshots:** `~/.openclaw/workspace/spark_build_queue/trend_build_queue_<RUN_ID>.json`
- **Dispatch log:** `~/.spark/claw_integration/build_dispatch_log.jsonl`

---

## 3) TrendBuilderResult schema (producer output)

### Required/typical fields
```json
{
  "status": "completed",
  "topics_processed": 6,
  "queries_run": 12,
  "search_rows_scanned": 180,
  "insights_extracted": 37,
  "recommendations": 5,
  "trends_evaluated": 6,
  "trends_selected": 2,
  "trends_filtered": 4,
  "trend_profiles": [
    {
      "topic": "vibe_coding",
      "trend_score": 0.81,
      "trend_rank": 1,
      "trend_velocity": 18.4,
      "evidence_count": 14,
      "momentum_vs_prev_day": 1.52,
      "gating_reasons": ["ready"],
      "selected_for_build": true
    }
  ],
  "build_candidates": {
    "skills": [],
    "mcps": [],
    "startup_ideas": []
  },
  "injected_to_spark": 20,
  "report": { "...": "..." }
}
```

### Notes
- `build_candidates` is the only field consumed by the scheduler queue builder.
- Candidate items are expected to include:
  - `name` / `title`
  - `type` (`skill`/`mcps`/`startup`)
  - `source_topic`
  - `confidence` (0–1 float)
  - optional `trend_profile` containing:
    - `trend_score`
    - `trend_rank`
    - `evidence_count`
    - `gating_reasons`
    - `selected_for_build`
  - optional `build_plan` with `target_engine` / `automation_root` / `target_path`

---

## 4) Queue manifest schema (scheduler output)

### Top-level fields
```json
{
  "run_id": "YYYYMMDD_HHMMSS",
  "generated_at": "ISO8601 timestamp",
  "source": "spark_scheduler.daily_research",
  "run_status": "completed",
  "topics_processed": 6,
  "jobs": [
    {
      "job_id": "skill_1718320000_1",
      "source_bucket": "skills",
      "build_type": "skill",
      "build_name": "vibe-coding-trend-assistant",
      "title": "Vibe Coding Trend Assistant",
      "assigned_engine": "codex",
      "source_topic": "vibe_coding",
      "confidence": 0.82,
      "trend_rank": 1,
      "target_path": "~\\/trend-builds/codex/skills/vibe-coding-trend-assistant",
      "priority": "high",
      "why_build_now": "...",
      "launch_pack": { "...": "..." },
      "trend_profile": {
        "trend_score": 0.81,
        "trend_rank": 1,
        "evidence_count": 14
      },
      "build_plan": {
        "target_engine": "codex",
        "target_path": ".../skills/..."
      },
      "one_shot_spawn": { "...": "..." },
      "source_payload": { "...": "..." },
      "run_id": "YYYYMMDD_HHMMSS",
      "scheduled_at": "ISO8601"
    }
  ],
  "stats": {
    "trends_evaluated": 6,
    "trends_selected": 2,
    "queue_count": 3,
    "trends_filtered": 4
  }
}
```

### Engine routing logic
- Default mappings from env in scheduler:
  - `TREND_BUILD_TARGET_SKILL` (default `codex`)
  - `TREND_BUILD_TARGET_MCP` (default `minimax`)
  - `TREND_BUILD_TARGET_STARTUP` (default `opus`)
- Candidate-level override fields:
  - `assigned_engine`
  - `default_agent`
  - `target_engine`
  - `build_plan.default_engine`
- Canonicalization:
  - `claude` -> `codex`
  - `gpt` -> `opus`

---

## 5) Queue selection gates (must pass to enter manifest)

Inside scheduler (`spark_scheduler.py`) a candidate is queued only if:
- `confidence >= TREND_BUILD_QUEUE_MIN_CONFIDENCE` (default `0.62`)
- `trend_profile.trend_score >= TREND_BUILD_QUEUE_MIN_TREND_SCORE` (default `0.72`)
- `trend_profile.evidence_count >= TREND_BUILD_QUEUE_MIN_EVIDENCE` (default `10`)
- queue size cap: `TREND_MAX_QUEUED_ITEMS` (default `24`)

---

## 6) Upstream trend extraction gates (cost & quality controls)

Inside `spark-x-builder/scripts/daily_trend_research.py`:
- Daily row budget: `TREND_DAILY_ROW_BUDGET` (default `180`)
- Per-topic cap: `TREND_MAX_TOPIC_ROWS` (default `36`)
- Query caps by priority:
  - `TREND_QUERY_LIMIT_HIGH=24`
  - `TREND_QUERY_LIMIT_MEDIUM=18`
  - `TREND_QUERY_LIMIT_LOW=12`
- Engagement filters:
  - `TREND_MIN_LIKES=4`
  - `TREND_MIN_RETWEETS=1`
  - `TREND_MIN_REPLIES=1`
  - `TREND_MIN_ENGAGEMENT_SCORE=45.0`
  - `TREND_MAX_FRESHNESS_HOURS=96`
- Candidate bucket threshold:
  - `TREND_MIN_CANDIDATE_BUCKET_SCORE=20`
- Viral filter:
  - `TREND_VIRAL_MIN_SCORE`
  - `TREND_VIRAL_MIN_EVIDENCE`
  - `TREND_VIRAL_TOP_QUANTILE`
  - `TREND_VIRAL_MOMENTUM_MIN`
  - `TREND_VIRAL_ABSOLUTE_NEW`

---

## 7) OpenClaw integration fields

If handoff delivery webhooks are configured:
- `OPENCLAW_WEBHOOK_URL` gets the `latest_trend_handoff` payload
- `CLAWDBOT_WEBHOOK_URL` also gets the same payload

`latest_trend_handoff.json` contains:
- full trend payload summary
- `runner` metadata (repo/path/command)
- `build_queue_file` path (set to latest queue file)
- optional embedded `build_queue` stats after generation
- optional `deliveries` flags from webhook posts

---

## 8) Minimal handoff contract for OpenClaw/Clawdbot workers

Workers should consume `latest_build_queue.json` and execute each `jobs[]` item:
- Validate `assigned_engine` and dispatch to toolchain
- Use `target_path` for output location
- Use `one_shot_spawn` to create skill/mcp/startup artifact
- Persist result to:
  - `.../spark_build_queue/latest_build_queue.json`
  - optionally emit completion event that references `run_id`

---

## 9) Recommended profiles

- **Strict (viral-only, lower spend):**
  - Increase: `TREND_MIN_ENGAGEMENT_SCORE=65`, `TREND_DAILY_ROW_BUDGET=120`, `TREND_BUILD_QUEUE_MIN_TREND_SCORE=0.82`
  - Decrease: `TREND_MIN_CANDIDATE_BUCKET_SCORE=30`
- **Balanced (current default):**
  - Keep defaults as documented above
- **Aggressive (more volume):**
  - Increase: `TREND_DAILY_ROW_BUDGET=280`, `TREND_QUERY_LIMIT_HIGH=36`, `TREND_QUERY_LIMIT_MEDIUM=24`, `TREND_BUILD_QUEUE_MIN_CONFIDENCE=0.55`
