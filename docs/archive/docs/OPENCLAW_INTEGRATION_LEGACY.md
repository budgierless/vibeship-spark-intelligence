# OpenClaw Integration

## Overview

Spark Intelligence integrates with OpenClaw to create a self-evolving AI agent that learns from its own conversations and produces actionable intelligence in real-time.

## Architecture

```
User ↔ OpenClaw (agent) ↔ Spark Intelligence ↔ Spark Pulse Dashboard
         │                      │                       │
         │ session JSONL        │ patterns/insights      │ visualization
         ▼                      ▼                       ▼
    openclaw_tailer ──→ sparkd ──→ bridge_cycle ──→ SPARK_CONTEXT.md
                       (HTTP)     (processing)      SPARK_ADVISORY.md
                                      │              SPARK_NOTIFICATIONS.md
                                      ▼
                                 Claude CLI (LLM)
                                      │
                                      ▼
                                 Advisory synthesis
                                 EIDOS distillation
```

## Components

### 1. Event Capture — `adapters/openclaw_tailer.py`

Tails OpenClaw session JSONL files and sends events to sparkd.

```bash
python adapters/openclaw_tailer.py --include-subagents
```

- Watches `~/.openclaw/agents/main/sessions/*.jsonl`
- With `--include-subagents`, also watches subagent sessions
- Sends events to sparkd at `http://localhost:8787/event`
- Handles session boundaries (start/end events)

### 2. Context Output — `lib/output_adapters/openclaw.py`

Writes Spark's learnings to OpenClaw workspace files:

| File | Content |
|------|---------|
| `SPARK_CONTEXT.md` | Curated insights, cognitive state, chip activity |
| `SPARK_ADVISORY.md` | LLM-generated actionable recommendations |
| `SPARK_NOTIFICATIONS.md` | Recent bridge cycle findings (last 5) |

### 3. Context Sync — `lib/context_sync.py`

Selects and promotes insights across all output targets (Claude Code, Cursor, Windsurf, OpenClaw, etc.).

### 4. Live Notifications — `lib/openclaw_notify.py`

Pushes findings to the OpenClaw agent in real-time:

- **`notify_agent()`** — writes to `SPARK_NOTIFICATIONS.md`
- **`wake_agent()`** — POSTs to OpenClaw's cron wake endpoint, triggering the agent to read fresh context
- **5-minute cooldown** between notifications (prevents spam)
- **Cron job** (`spark-context-refresh`): fires every 10 minutes to ensure baseline context refresh

### 5. Self-Report — `lib/self_report.py`

Protocol for the agent to report structured feedback back to Spark (e.g., "this advice was useful", "I tried X and it failed").

## Running Services

| Service | Port | Command | Notes |
|---------|------|---------|-------|
| sparkd | 8787 | `python sparkd.py` | HTTP event ingestion |
| bridge_worker | — | `python bridge_worker.py` | **Must set `SPARK_EMBEDDINGS=0`** |
| openclaw_tailer | — | `python adapters/openclaw_tailer.py --include-subagents` | Session event capture |
| Spark Pulse | 8765 | `python -m uvicorn app:app --host 127.0.0.1 --port 8765` | Dashboard (in vibeship-spark-pulse repo) |

### Start All Services

```powershell
$repo = "C:\Users\USER\Desktop\vibeship-spark-intelligence"
$env:SPARK_EMBEDDINGS = "0"

Start-Process python -ArgumentList "$repo\sparkd.py" -WorkingDirectory $repo -WindowStyle Hidden
Start-Process python -ArgumentList "$repo\bridge_worker.py" -WorkingDirectory $repo -WindowStyle Hidden
Start-Process python -ArgumentList "$repo\adapters\openclaw_tailer.py","--include-subagents" -WorkingDirectory $repo -WindowStyle Hidden
Start-Process python -ArgumentList "-m","uvicorn","app:app","--host","127.0.0.1","--port","8765" -WorkingDirectory "C:\Users\USER\Desktop\vibeship-spark-pulse" -WindowStyle Hidden
```

### Verify

```powershell
# sparkd health
Invoke-RestMethod http://127.0.0.1:8787/health

# Pulse dashboard
curl.exe -s -o NUL -w "%{http_code}" http://127.0.0.1:8765/

# Bridge heartbeat
Get-Content "$env:USERPROFILE\.spark\bridge_worker_heartbeat.json" | ConvertFrom-Json
```

### Advisory Delivery Status (Pulse + Spark Lab)

```powershell
# Spark Lab status (dashboard.py source of truth)
$lab = Invoke-RestMethod http://127.0.0.1:8585/api/status
$lab.advisory.delivery_badge

# Pulse status projection
$pulse = Invoke-RestMethod http://127.0.0.1:8765/api/status
$pulse.advisory.delivery_badge

# Pulse advisory board
$adv = Invoke-RestMethod http://127.0.0.1:8765/api/advisory
$adv.delivery_badge
```

Expected `delivery_badge.state` values:
- `live`: recent live advisory emit path
- `fallback`: packet/fallback advisory path active
- `blocked`: advisory path unavailable/disabled
- `stale`: last advisory event older than stale threshold

## OpenClaw Configuration

### Cron Job

The `spark-context-refresh` cron job fires every 10 minutes:
- Type: `systemEvent` in main session
- Text: Tells the agent to read SPARK_CONTEXT.md and SPARK_NOTIFICATIONS.md

### Workspace Files

All Spark output files live in `~/.openclaw/workspace/`:
- `SPARK_CONTEXT.md` — cognitive insights and system state
- `SPARK_ADVISORY.md` — LLM-generated recommendations
- `SPARK_NOTIFICATIONS.md` — recent bridge cycle events

## Data Flow

1. **Capture**: Agent conversation → session JSONL → openclaw_tailer → sparkd
2. **Process**: sparkd queue → bridge_cycle → pattern detection → chip system → cognitive learner
3. **Synthesize**: bridge_cycle → Claude CLI → advisory synthesis → SPARK_ADVISORY.md
4. **Deliver**: Cron/wake event → agent reads SPARK_CONTEXT.md + SPARK_ADVISORY.md
5. **Act**: Agent applies recommendations in next interactions

## Critical Notes

- **Never run bridge_worker without `SPARK_EMBEDDINGS=0`** — fastembed ONNX model causes 8GB+ memory leak
- **Spark Pulse must use `-m uvicorn`** — running `python app.py` hits blocking `startup_services()`
- **Only one bridge_worker at a time** — duplicate instances compound the memory issue
- **Claude CLI must be authenticated** — run `claude` → `/login` once before LLM features work
