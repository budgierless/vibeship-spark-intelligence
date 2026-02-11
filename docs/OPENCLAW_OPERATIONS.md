# OpenClaw Operations — Running Spark the Seer

## Session Startup Checklist

Every time you start a new OpenClaw session, do this:

### 1. Start Spark Services

```powershell
$repo = "C:\Users\USER\Desktop\vibeship-spark-intelligence"
$env:SPARK_EMBEDDINGS = "0"

# Core services
$sparkd = Start-Process python -ArgumentList "$repo\sparkd.py" -WorkingDirectory $repo -WindowStyle Hidden -PassThru
$bridge = Start-Process python -ArgumentList "$repo\bridge_worker.py" -WorkingDirectory $repo -WindowStyle Hidden -PassThru
$tailer = Start-Process python -ArgumentList "$repo\adapters\openclaw_tailer.py","--include-subagents" -WorkingDirectory $repo -WindowStyle Hidden -PassThru

# Dashboard
$pulse = Start-Process python -ArgumentList "-m","uvicorn","app:app","--host","127.0.0.1","--port","8765" -WorkingDirectory "C:\Users\USER\Desktop\vibeship-spark-pulse" -WindowStyle Hidden -PassThru

Write-Host "sparkd=$($sparkd.Id) bridge=$($bridge.Id) tailer=$($tailer.Id) pulse=$($pulse.Id)"
```

### 2. Verify Everything is Running

```powershell
# Quick health check
Invoke-RestMethod http://127.0.0.1:8787/health                    # sparkd
curl.exe -s -o NUL -w "%{http_code}" http://127.0.0.1:8765/       # pulse
Get-Process python | Select-Object Id,@{N='MB';E={[math]::Round($_.WorkingSet64/1MB)}}
```

### 3. Verify Claude CLI Auth

```powershell
claude -p "say OK"
```

If it says "Invalid API key", run `claude` and type `/login`.

---

## How Spark Works Inside OpenClaw

### Data Flow

```
You type a message
        │
        ▼
OpenClaw processes it (tools, responses, etc.)
        │
        ▼
Session JSONL written to ~/.openclaw/agents/main/sessions/
        │
        ▼
openclaw_tailer reads new events, sends to sparkd (:8787)
        │
        ▼
sparkd queues events in ~/.spark/queue/events.jsonl
        │
        ▼
bridge_worker processes queue every ~30 seconds:
  ├─ Pattern detection (coding patterns, errors, workflows)
  ├─ Chip system (domain-specific insights across 7+ domains)
  ├─ Cognitive learner (builds validated knowledge base)
  ├─ Feedback ingestion (reads agent self-reports)
  ├─ Prediction/validation loop
  ├─ Context sync (writes to all IDE targets)
  ├─ Auto-tuner (optimizes its own parameters)
  └─ LLM Advisory (calls Claude when enough patterns found)
        │
        ▼
Outputs written to OpenClaw workspace:
  ├─ SPARK_CONTEXT.md    (curated insights)
  ├─ SPARK_ADVISORY.md   (Claude-generated recommendations)
  └─ SPARK_NOTIFICATIONS.md (recent events)
        │
        ▼
Cron job (every 10 min) tells agent to read + act on advisories
        │
        ▼
Agent evaluates, acts, reports feedback to spark_reports/
        │
        ▼
bridge_worker ingests feedback → updates confidence → loop repeats
```

### The Self-Evolution Loop

```
         ┌──────────────────────────────────────────────┐
         │                                              │
         ▼                                              │
    Conversation ──→ Capture ──→ Patterns ──→ Claude   │
                                Advisory               │
                                    │                   │
                                    ▼                   │
                             Agent evaluates            │
                              ├─ Act → Report outcome ──┘
                              └─ Skip → Report reason ──┘
```

The `advice_action_rate` metric tracks what % of advice gets acted on. Target: >50%.

---

## Services Reference

| Service | Port | Process | Critical Notes |
|---------|------|---------|----------------|
| sparkd | 8787 | `python sparkd.py` | HTTP event ingestion endpoint |
| bridge_worker | — | `python bridge_worker.py` | **MUST set `SPARK_EMBEDDINGS=0`** or 8GB+ RAM leak |
| openclaw_tailer | — | `python adapters/openclaw_tailer.py --include-subagents` | Tails session JSONL files |
| Spark Pulse | 8765 | `python -m uvicorn app:app` | **MUST use `-m uvicorn`** not `python app.py` |

### RAM Budget

| Service | Expected | Alert |
|---------|----------|-------|
| sparkd | 30-40MB | >100MB |
| bridge_worker | 60-80MB | >200MB |
| tailer | 20-30MB | >50MB |
| Spark Pulse | 120-170MB | >300MB |
| **Total** | **~350MB** | **>500MB** |

---

## Key Files

### OpenClaw Workspace (`~/.openclaw/workspace/`)

| File | Purpose | Who writes | Who reads |
|------|---------|-----------|-----------|
| `SPARK_CONTEXT.md` | Curated insights | bridge_worker | Agent (cron) |
| `SPARK_ADVISORY.md` | LLM recommendations | bridge_worker | Agent (cron) |
| `SPARK_NOTIFICATIONS.md` | Recent events | bridge_worker | Agent (cron) |
| `spark_reports/*.json` | Agent feedback | Agent | bridge_worker |
| `MEMORY.md` | Long-term memory | Agent | Agent |
| `HEARTBEAT.md` | Heartbeat tasks | Agent | Agent |

### Spark Data (`~/.spark/`)

| File | Purpose |
|------|---------|
| `queue/events.jsonl` | Event queue (FIFO) |
| `cognitive_insights.json` | Validated knowledge base |
| `bridge_worker_heartbeat.json` | Bridge cycle status |
| `feedback_state.json` | Feedback loop metrics |
| `feedback_log.jsonl` | All feedback history |
| `llm_calls.json` | Rate limit tracking (30/hr) |
| `llm_advisory.md` | Latest advisory (backup) |
| `eidos_distillations.jsonl` | Self-model updates |
| `eidos_llm_counter.txt` | Distillation cycle counter |
| `chip_insights/*.jsonl` | Per-chip observations (2MB rotation) |

---

## Cron Jobs

| Job | Schedule | Purpose |
|-----|----------|---------|
| `spark-context-refresh` | Every 30 min | Checkpoint-style reminder: read Spark files, act only on relevant items, log acted/skipped outcomes |

## Config Lifecycle (Hot-apply vs Restart)

Use this to avoid guessing whether a change is live.

| Config area | Hot-apply | Operator action |
|-------------|-----------|-----------------|
| Advisory runtime (`advisory_engine`, `advisory_gate`, `advisory_packet_store`, `advisory_prefetch`) | Yes | Apply and verify logs/status |
| Synthesizer (`synthesizer` section) | Yes | Apply and verify `get_synth_status` |
| Env vars (`SPARK_*`) | No | Restart affected process |
| Legacy/import-time configs (many modules) | Usually no | Restart affected process |

Verification loop after any config change:
1. Check service health (`sparkd`, `bridge_worker` heartbeat, Mind health)
2. Confirm behavior in a real active cycle (not synthetic-only)
3. Log result in `docs/OPENCLAW_RESEARCH_AND_UPDATES.md`

---

## Troubleshooting

### bridge_worker using too much RAM
- Check `SPARK_EMBEDDINGS` is `0`
- Check for duplicate bridge_worker processes: `Get-WmiObject Win32_Process -Filter "Name='python.exe'" | Where-Object {$_.CommandLine -like "*bridge_worker*"}`
- Kill all and restart one

### Pulse not responding
- Check it's running: `netstat -ano | findstr 8765`
- If port in use, kill old process first
- Always use `-m uvicorn app:app`, never `python app.py`

### LLM advisory not generating
- Check Claude auth: `claude -p "say OK"` (needs PTY)
- Check rate limit: `Get-Content ~/.spark/llm_calls.json`
- Check bridge heartbeat: `llm_advisory` should be `True`
- Need ≥5 patterns or ≥2 merged insights to trigger

### No events in queue
- Verify tailer is running and watching the right session
- Check sparkd is accepting: `Invoke-RestMethod http://127.0.0.1:8787/health`

---

## Agent Behavior (Spark the Seer)

### On Cron Refresh (every 10 min)
1. Read `SPARK_ADVISORY.md`
2. For each recommendation: act, defer, or skip
3. Report feedback via `lib/agent_feedback.py`:
   ```python
   import sys; sys.path.insert(0, r"C:\Users\USER\Desktop\vibeship-spark-intelligence")
   from lib.agent_feedback import advisory_acted, advisory_skipped, learned_something
   ```
4. Read `SPARK_CONTEXT.md` and `SPARK_NOTIFICATIONS.md`

### On Heartbeat
- Check Spark services health
- Review advisories if not recently reviewed
- Monitor RAM usage

### When Learning Something
Always write it down:
```python
from lib.agent_feedback import learned_something
learned_something("what you learned", "context", confidence=0.9)
```

---

## Git Workflow

- Repo: `vibeforge1111/vibeship-spark-intelligence` (PRIVATE)
- Push after every logical chunk
- Today's commits: 14 (Phase 1-2, UTF-8 fixes, live advice, memory leak fix, LLM integration, feedback loop, docs)
