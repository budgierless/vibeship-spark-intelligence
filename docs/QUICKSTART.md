# Spark Quick Start Guide

Get Spark running in 5 minutes.

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
pip install requests

# Install Spark (from repo)
pip install -e .

# Optional: Enable embeddings (fastembed)
pip install fastembed

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

Check status:
```bash
python3 -m spark.cli services
# or: spark services
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
- Spark Lab (overview + orchestration): http://localhost:${SPARK_DASHBOARD_PORT:-8585}
- Dashboards Index: http://localhost:${SPARK_DASHBOARD_PORT:-8585}/dashboards
- Spark Pulse (chips + tuneables rail): http://localhost:${SPARK_PULSE_PORT:-8765}
- Meta-Ralph Quality Analyzer: http://localhost:${SPARK_META_RALPH_PORT:-8586}

Port overrides:
- `SPARKD_PORT`
- `SPARK_DASHBOARD_PORT`
- `SPARK_PULSE_PORT`
- `SPARK_META_RALPH_PORT`
- `SPARK_MIND_PORT`

Tip: `spark up` starts Spark Lab + Spark Pulse + Meta-Ralph by default. Use `--no-pulse` or `--no-meta-ralph` to skip.
Tip: `spark up --lite` skips all dashboards/pulse/watchdog to reduce background load.

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

# Sync Spark learnings to Mind
python3 -m spark.cli sync
```

## Claude Code Integration

Add to `.claude/settings.json`:

```json
{
  "hooks": {
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
`post_tool`, `post_tool_failure`, `user_prompt`.

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
