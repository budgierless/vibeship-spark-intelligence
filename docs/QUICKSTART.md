# Spark Quick Start Guide

Get Spark running in 5 minutes.

For the full active documentation map, see `docs/DOCS_INDEX.md`.
For term-based navigation, see `docs/GLOSSARY.md`.

## Prerequisites

- Python 3.10+
- pip

## Installation

### Option 1: Quick Install

```bash
cd /path/to/Spark
./scripts/install.sh
```

### Option 2: Manual Install

```bash
# Install dependencies
pip install -e .

# Install Spark (from repo)
pip install -e .[services]

# Optional: Enable embeddings (fastembed)
pip install -e .[embeddings]

# Test it works
python3 -m spark.cli health
```

## Basic Usage

### Check Status

```bash
python3 -m spark.cli status
```

### Start Background Services (Recommended)

These keep the bridge worker running and the dashboard live.

```bash
python3 -m spark.cli up
# or: spark up
```
Lightweight mode (core services only: sparkd + bridge_worker):
```bash
python3 -m spark.cli up --lite
```

Repo shortcuts:
```bash
./scripts/run_local.sh
```

Windows (repo):
```bat
start_spark.bat
```
This also starts Mind on `SPARK_MIND_PORT` (default `8080`) if `mind.exe` is available.  
Set `SPARK_NO_MIND=1` to skip Mind startup.
Set `SPARK_LITE=1` to skip dashboards/pulse/watchdog (core services only).
Spark auto-detects sibling `../vibeship-spark-pulse` first, then falls back to `~/Desktop/vibeship-spark-pulse`.
Set `SPARK_PULSE_DIR` to override both.
For this setup, use:
```bat
set SPARK_PULSE_DIR=C:\Users\USER\Desktop\vibeship-spark-pulse
```
If Mind CLI is installed but unstable, force Spark's built-in Mind server:
```bat
set SPARK_FORCE_BUILTIN_MIND=1
start_spark.bat
```

Check status:
```bash
python3 -m spark.cli services
# or: spark services
```

### Opportunity Scanner Runtime Checks

Verify scanner status and recent self-Socratic prompts:

```bash
python -c "from lib.opportunity_scanner import get_scanner_status, get_recent_self_opportunities; import json; print(json.dumps(get_scanner_status(), indent=2)); print(json.dumps(get_recent_self_opportunities(limit=5), indent=2))"
```

Inbox workflow (accept/dismiss):
```bash
python -m spark.cli opportunities list --limit 20
python -m spark.cli opportunities accept <id-prefix>
python -m spark.cli opportunities dismiss <id-prefix>
```

Enable Minimax-backed scanner synthesis (optional):

```bash
set SPARK_OPPORTUNITY_LLM_ENABLED=1
set SPARK_OPPORTUNITY_LLM_PROVIDER=minimax
set MINIMAX_API_KEY=your_key_here
set SPARK_MINIMAX_MODEL=MiniMax-M2.5

# Recommended cadence: one LLM "deep scan" at most every 15 minutes per session while you're actively working.
# (Scanner already skips LLM calls when context is insufficient.)
set SPARK_OPPORTUNITY_LLM_COOLDOWN_S=900
```

After setting env vars, restart services (`spark down` then `spark up`) and check scanner heartbeat `llm` fields (`used`, `provider`, `error`).

Verify scanner stats are present in bridge heartbeat:

```bash
python -c "import json; from pathlib import Path; p=Path.home()/'.spark'/'bridge_worker_heartbeat.json'; d=json.loads(p.read_text(encoding='utf-8')); print(json.dumps((d.get('stats') or {}).get('opportunity_scanner') or {}, indent=2))"
```

Inspect persisted scanner artifacts:

```bash
# self-opportunities
python -c "from pathlib import Path; p=Path.home()/'.spark'/'opportunity_scanner'/'self_opportunities.jsonl'; print(p, 'exists=', p.exists())"

# acted outcomes + promotion candidates
python -c "from pathlib import Path; base=Path.home()/'.spark'/'opportunity_scanner'; print((base/'outcomes.jsonl').exists(), (base/'promoted_opportunities.jsonl').exists())"
```

The watchdog auto-restarts workers and warns when the queue grows. Set
`SPARK_NO_WATCHDOG=1` to disable it when using the launch scripts.

Stop services:
```bash
python3 -m spark.cli down
# or: spark down
```

### Dashboards

Defaults (override via env; see `lib/ports.py`):
- Spark Pulse (primary unified dashboard): http://localhost:${SPARK_PULSE_PORT:-8765}
  - Tabs/surfaces include Mission, Learning, Rabbit, Acceptance, Ops, Chips, Tuneables, Tools, and Trace/Run drilldowns.
- Spark Lab (auxiliary/legacy web views): http://localhost:${SPARK_DASHBOARD_PORT:-8585}
- Dashboards Index (Spark Lab): http://localhost:${SPARK_DASHBOARD_PORT:-8585}/dashboards
- Meta-Ralph Quality Analyzer: http://localhost:${SPARK_META_RALPH_PORT:-8586}

Port overrides:
- `SPARKD_PORT`
- `SPARK_DASHBOARD_PORT`
- `SPARK_PULSE_PORT`
- `SPARK_META_RALPH_PORT`
- `SPARK_MIND_PORT`

Tip: `spark up` starts Spark Lab + Spark Pulse + Meta-Ralph by default. Pulse (`8765`) is the primary operator surface; Spark Lab (`8585`) is legacy/auxiliary.
Tip: Use `--no-pulse` or `--no-meta-ralph` only for debugging or reduced startup modes.
Tip: `spark up --lite` skips all dashboards/pulse/watchdog to reduce background load.
Tip: Pulse does not require Spark Lab (`8585`) by default; set `SPARK_DASHBOARD_FALLBACK=1` only if you want HTTP fallback behavior.

### Production Hardening Defaults

- `sparkd` auth: when `SPARKD_TOKEN` is set, all mutating `POST` endpoints require `Authorization: Bearer <token>`.
- Queue safety: queue rotation and processed-event consumption both use temp-file + atomic replace.
- Validation loop: bridge cycle runs both prompt validation and outcome-linked validation each cycle.
- Dashboard exposure: Meta-Ralph dashboard binds to `127.0.0.1` by default.
- Service startup: if Spark Pulse app is unavailable, core services still start and pulse is reported unavailable.

Test gates before push:
```bash
python -m ruff check . --select E9,F63,F7,F82
python -m pytest -q
```

### Automated Always-On (Quick Start)

Keep Spark running at login so hooks never miss events.

#### Windows (Task Scheduler)
Manual setup:
1) Open Task Scheduler -> Create Task
2) Trigger: At log on
3) Action: Start a program
   - Program/script: `spark` (or full `python.exe`)
   - Add arguments: `up --sync-context --project "C:\path\to\your\project"`
   - Start in: `C:\path\to\your\project`

Helper script (creates the task automatically):
```powershell
./scripts/install_autostart_windows.ps1
```

Remove the task:
```powershell
./scripts/remove_autostart_windows.ps1
```

If you get "Access is denied", run PowerShell as Administrator.

#### macOS (launchd)
Create `~/Library/LaunchAgents/co.vibeship.spark.plist`:
```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
  <dict>
    <key>Label</key><string>co.vibeship.spark</string>
    <key>ProgramArguments</key>
    <array>
      <string>/usr/bin/python3</string>
      <string>-m</string>
      <string>spark.cli</string>
      <string>up</string>
      <string>--sync-context</string>
      <string>--project</string>
      <string>/path/to/your/project</string>
    </array>
    <key>RunAtLoad</key><true/>
    <key>KeepAlive</key><true/>
    <key>StandardOutPath</key><string>$HOME/.spark/logs/launchd.out</string>
    <key>StandardErrorPath</key><string>$HOME/.spark/logs/launchd.err</string>
  </dict>
</plist>
```

Load it:
```bash
launchctl load -w ~/Library/LaunchAgents/co.vibeship.spark.plist
```

Unload it:
```bash
launchctl unload ~/Library/LaunchAgents/co.vibeship.spark.plist
```

#### Linux (systemd user service)
Create `~/.config/systemd/user/spark-up.service`:
```ini
[Unit]
Description=Spark background services

[Service]
Type=simple
ExecStart=python3 -m spark.cli up --sync-context --project /path/to/your/project
Restart=on-failure

[Install]
WantedBy=default.target
```

Enable and start:
```bash
systemctl --user daemon-reload
systemctl --user enable --now spark-up.service
```

Stop:
```bash
systemctl --user disable --now spark-up.service
```

#### Fallback (cron)
If you prefer cron:
```
@reboot python3 -m spark.cli up --sync-context --project /path/to/your/project >/dev/null 2>&1
```

### Per-Project Ensure (Optional)

If you want each project to guarantee Spark is running, add this to your
project start script or editor task:

```bash
spark ensure --sync-context --project .
# or: python3 -m spark.cli ensure --sync-context --project .
```

Windows helper (run from project root):
```bat
scripts\ensure_spark.bat
```

macOS/Linux helper:
```bash
spark ensure --sync-context --project "$(pwd)"
```

### Create Learnings (Programmatic)

```python
from lib.cognitive_learner import get_cognitive_learner

cognitive = get_cognitive_learner()

# Learn from a failure
cognitive.learn_struggle_area(
    task_type="regex_patterns",
    failure_reason="Edge cases in complex patterns"
)

# Learn a principle
cognitive.learn_principle(
    principle="Always test edge cases",
    examples=["Empty input", "Null values", "Unicode"]
)
```

### Write to Markdown

```bash
python3 -m spark.cli write
# Creates .learnings/LEARNINGS.md
```

### Optional: Agent Context Injection (Opt-in)

If you spawn sub-agents, you can prepend a compact Spark context block to their
prompts. This is off by default.

```bash
SPARK_AGENT_INJECT=1
SPARK_AGENT_CONTEXT_LIMIT=3
SPARK_AGENT_CONTEXT_MAX_CHARS=1200
```

Use `lib.orchestration.inject_agent_context(prompt)` when preparing sub-agent prompts.

## Optional: Scheduled Sync Backup

If you want a safety net (for sessions launched outside wrappers), run sync on a timer.

**Windows Task Scheduler**
- Action: `spark`
- Args: `sync-context`
- Start in: your repo root
- Trigger: every 10–30 minutes

**macOS/Linux (cron)**
```
*/20 * * * * cd /path/to/vibeship-spark-intelligence && spark sync-context >/dev/null 2>&1
```

### Promote High-Value Insights

```bash
# Check what's ready
python3 -m spark.cli promote --dry-run

# Actually promote
python3 -m spark.cli promote
# Creates/updates AGENTS.md, CLAUDE.md, etc.
```

## Mind Integration (Optional)

For persistent semantic memory:

```bash
# Install Mind
pip install vibeship-mind

# Start Mind server
python3 -m mind.lite_tier
# If Mind CLI fails, use Spark's built-in server:
python3 mind_server.py

# Sync Spark learnings to Mind
python3 -m spark.cli sync
```

## Semantic Retrieval (Optional)

Enable semantic matching for cognitive insights:

```bash
# Optional: local embeddings
pip install fastembed

# Enable semantic + triggers
# ~/.spark/tuneables.json
#
# "semantic": { "enabled": true, ... }
# "triggers": { "enabled": true, ... }

# Backfill semantic index
python -m spark.index_embeddings --all
# (legacy) python scripts/semantic_reindex.py
```

Use it during real work:
```python
from lib.advisor import advise_on_tool
advice = advise_on_tool("Edit", {"file_path": "src/auth/login.py"}, "edit auth login flow")
```

Semantic retrieval logs and metrics:
- `~/.spark/logs/semantic_retrieval.jsonl`
- `~/.spark/advisor/metrics.json`

## Claude Code Integration

Add to `.claude/settings.json`:

```json
{
  "hooks": {
    "PreToolUse": [{
      "matcher": "",
      "hooks": [{
        "type": "command",
        "command": "python3 /path/to/Spark/hooks/observe.py"
      }]
    }],
    "PostToolUse": [{
      "matcher": "",
      "hooks": [{
        "type": "command",
        "command": "python3 /path/to/Spark/hooks/observe.py"
      }]
    }],
    "PostToolUseFailure": [{
      "matcher": "",
      "hooks": [{
        "type": "command",
        "command": "python3 /path/to/Spark/hooks/observe.py"
      }]
    }],
    "UserPromptSubmit": [{
      "matcher": "",
      "hooks": [{
        "type": "command",
        "command": "python3 /path/to/Spark/hooks/observe.py"
      }]
    }]
  }
}
```

Spark maps these hook names to runtime event types used by chips:
`pre_tool`, `post_tool`, `post_tool_failure`, `user_prompt`.

For predictive advisory to work end-to-end, `PreToolUse` must be enabled.

## Directory Structure

After running, Spark creates:

```
~/.spark/                      # Config and data
├── cognitive_insights.json    # Raw learnings
├── mind_sync_state.json       # Sync tracking
├── exposures.jsonl            # Surfaced insights (prediction inputs)
├── predictions.jsonl          # Prediction registry
├── outcomes.jsonl             # Outcomes log (skills/orchestration/project)
├── skills_index.json          # Cached skills index
├── skills_effectiveness.json  # Skill success/fail counters
├── orchestration/
│   ├── agents.json            # Registered agents
│   └── handoffs.jsonl         # Handoff history
└── queue/
    └── events.jsonl           # Event queue

.learnings/                    # In your project
├── LEARNINGS.md              # Human-readable insights
└── ERRORS.md                 # Error patterns

AGENTS.md                      # Promoted workflow patterns
CLAUDE.md                      # Promoted conventions
```

## CLI Commands Reference

| Command | Description |
|---------|-------------|
| `status` | Show full system status |
| `services` | Show daemon/service status |
| `up` | Start background services (`--lite` for core-only) |
| `ensure` | Start missing services if not running |
| `down` | Stop background services |
| `health` | Quick health check |
| `learnings` | List recent cognitive insights |
| `write` | Write insights to markdown |
| `promote` | Auto-promote high-value insights |
| `sync-context` | Sync bootstrap context to platform files |
| `decay` | Preview/apply decay-based pruning |
| `sync` | Sync to Mind (if running) |
| `queue` | Process offline sync queue |
| `process` | Run bridge worker cycle or drain backlog |
| `validate` | Run validation scan on recent events |
| `events` | Show recent captured events |

## Troubleshooting

### "Mind API: Not available"

Mind isn't running. Either:
- Start Mind: `python3 -m mind.lite_tier`
- Or ignore it — Spark works offline and queues for later

### "requests not installed"

```bash
pip install requests
```

### Learnings not appearing

Check that the hook is configured correctly and the path is absolute.

If the queue is large or processing stalled, run:

```bash
python -m spark.cli process --drain
```

### Extra logging (optional)

Enable debug logs temporarily when troubleshooting:

```bash
set SPARK_DEBUG=1
```

Tip: leave it off for normal usage to avoid log noise.

### Validation Loop (v1)

The current validation loop focuses on user preferences + communication insights.
Recommended: let it run for a day or two to confirm low false positives, then
expand scope if needed.

## Next Steps

1. **Integrate with your workflow** — Set up the hooks
2. **Start Mind** — For persistent cross-project learning
3. **Review learnings** — `python3 -m spark.cli learnings`
4. **Promote insights** — `python3 -m spark.cli promote`

---

*Part of the Vibeship Ecosystem*
