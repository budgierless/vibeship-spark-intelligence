# Spark Live Operations Snapshot (2026-02-20)

Generated from live checks at approximately `2026-02-20T03:58:15`.
This document captures all currently running Spark-related services and control points.

## 1) Service map (live)

- `http://localhost:8780` (Neural Nexus)
  - Role: Executive learning orchestrator + embedded dashboard for 26 learning systems (plus 3 external inputs).
  - API: `http://localhost:8780/openapi.json`
  - Health: `{"status":"ok","service":"neural-nexus"}`

- `http://localhost:8790/docs` (System 26 Executive Loop API)
  - Role: Live control plane for the autonomous loop and budget.
  - Health: `{"status":"ok","pid":59448}`
  - Endpoints include:
    - `GET /health`
    - `GET /status`
    - `GET /plan`
    - `GET /budget`
    - `GET /history`
    - `POST /mode`
    - `POST /pause`
    - `POST /resume`
    - `POST /kill`
    - `POST /override`

- `http://localhost:8787/health` (Sparkd / MCP daemon)
  - Role: MCP server used by Claude Code and Spark hooks.
  - Health: `ok`

- `http://localhost:8770` (Spark Neural / social intel dashboard)
  - Role: Social research + filter funnel + topic/research/gap visibility.
  - Endpoints:
    - `GET /api/status`
    - `GET /api/learning-flow`
    - `GET /api/gaps`
    - `GET /api/filter-funnel`
    - `GET /api/overview`
    - `GET /api/topics`
    - `GET /api/research`
    - `GET /api/social-patterns`
    - `GET /api/evolution`
    - `GET /api/topics`
  - Health-like state: `{"status":"alive","identity":"Spark"}`

- `http://localhost:8765` (Spark Pulse / living intelligence)
  - Role: Living intelligence runtime, advisory pipeline integration, and trace stream access.
  - Docs: `http://localhost:8765/docs`
  - Health: `ok`, `service":"spark-pulse-channel"`
  - Key endpoint: `GET /api/trace` and `GET /api/trace?limit=N`
  - Service map endpoint: `GET /api/services`

- `http://localhost:8080` (Mind v5 LITE+)
  - Role: Memory and pattern service.
  - Health: `{"status":"healthy","version":"5.0.0"}`

## 2) Current live state snapshot

### Executive loop state (`:8790`)
- Mode: `autonomous`
- Cycles run: `7`
- Budget: `300` total, `61` used, `239` remaining (reset `2026-02-19`)
- Today counters: `evolutions=12`, `merges=0`, `pushes=0`, `agent_spawns=0`
- Kill switch exists and is live via `POST /kill` on this port.
- Plan signals currently:
  - `system_21_hypothesis` (`P2_HIGH`)
  - `system_22_evolution` (`P2_HIGH`) x2

Recent history contains repeated `evolve` attempts with blocking failures:
- `Tests failed on branch`
- `error` field on last actions is non-empty while `status` is not marked success.

### Learning systems state (`:8780`)
- Totals: `28` systems, `7` healthy, `3` warning, `7` critical, `11` not run.
- Layer distribution:
  - `competence` (1-10): `0` healthy, `0` warning, `1` critical, `9` not run
  - `consciousness` (11-15): `4` healthy, `1` warning, `0` critical, `0` not run
  - `growth` (16-19): `1` healthy, `0` warning, `3` critical, `0` not run
  - `evolution` (21-26): `1` healthy, `2` warning, `1` critical, `2` not run
  - `external`: `1` healthy, `0` warning, `2` critical, `0` not run
- Run state at capture time: `{"running":false,"cycle":null,"progress":null}`

### Spark Intelligence / consciousness summary (`:8770`)
- Total insights: `625`
- Cognitive insights: `575`
- Social insights: `37`
- Engagement insights: `13`
- Total pipeline events in learning flow: `575` observations/funnel input
- Research sessions: `15`, tweets analyzed: `4591`
- Gaps endpoint: `total_gaps=0`, `overall_health=healthy`
- Active topics: `6` (`Vibe Coding` active and others)

### Spark Pulse / tracer (`:8765`)
- Adversarial/tracing stream endpoint: `/api/trace` currently returns empty arrays (no active trace payload at snapshot time).
- Advisory signal is in `stale` state due no recent emit.
- Advisory delivery mode at snapshot: `delivery_mode":"none"` from `/api/status`.
- Service map shows `sparkd`, `dashboard`, `bridge_worker`, `watchdog`, `mind` running.
- Mind tier currently: `lite+`, with `2425` total memories and `2` users (`/v1/stats` on `:8080`).

## 3) Best-practice execution loop (what to do now)

Objective from your instruction: analyze, propose, test, measure outcome, keep only improvements, roll back failures, and keep safety guardrails.

Recommended sequence:
1. Baseline capture
   - `curl -s http://localhost:8780/api/status`
   - `curl -s http://localhost:8780/api/layers`
   - `curl -s http://localhost:8790/status`
   - `curl -s http://localhost:8790/budget`
   - `curl -s http://localhost:8765/api/status`
   - `curl -s http://localhost:8765/api/trace?limit=20`

2. Focused growth analysis pass
   - Run full growth/evolution targets first before global full cycle:
     - `curl -X POST http://localhost:8780/api/run/growth`
     - `curl -X POST http://localhost:8780/api/run/evolution`
   - Prefer one pass at a time while budget remains and failure rate is known.

3. Hypothesis / improvement generation and test
   - Let the executive loop propose from current signals: `curl -s http://localhost:8790/plan`
   - If needed, force a bounded run:
     - `curl -X POST http://localhost:8790/override -H "Content-Type: application/json" -d "{\"action\":\"run_once\",\"target\":\"system_22\"}"`
   - Verify outcome:
     - `curl -s http://localhost:8790/history?limit=20`

4. Keep or rollback rule
   - Keep when run outcomes are positive and do not violate budget/safety.
   - Roll back immediately when errors match: `Tests failed on branch`, test failures, or merge/push rejections.
   - If safety or quality signal degrades, pause: `curl -X POST http://localhost:8790/pause`.

5. Safety controls
   - Kill switch: `curl -X POST http://localhost:8790/kill`
   - Resume (if intentionally restarting): `curl -X POST http://localhost:8790/resume`
   - Set explicit mode with reason:
     - `curl -X POST http://localhost:8790/mode -H "Content-Type: application/json" -d "{\"mode\":\"manual\",\"reason\":\"targeted gap repair\"}"`

## 4) Recommended priority to reduce "not_run" quickly

1. `Growth` layer (16-19): 3 critical, currently no advisory coherence output.
2. `Evolution` layer (21-26): 2 not_run, and key growth path blocked by repeated failed branch test cycles.
3. `Competence` layer: 9 systems still not executed end-to-end in this window.
4. Then run `Consciousness` maintenance and full cross-system pass once above layers are no longer clearly failing.

## 5) Useful commands (daily check)

- `curl -s http://localhost:8790/status | jq`
- `curl -s http://localhost:8790/plan | jq`
- `curl -s http://localhost:8790/history?limit=25 | jq`
- `curl -s http://localhost:8780/api/status | jq`
- `curl -s http://localhost:8780/api/layers | jq`
- `curl -s http://localhost:8770/api/overview | jq`
- `curl -s http://localhost:8765/api/services | jq`
- `curl -s http://localhost:8765/api/trace?limit=50 | jq`
- `curl -s http://localhost:8080/v1/stats | jq`
