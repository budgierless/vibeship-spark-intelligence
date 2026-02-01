# Spark

*The self-evolving intelligence layer for AI agents*

```
     _____ ____  ___    ____  __ __
    / ___// __ \/   |  / __ \/ //_/
    \__ \/ /_/ / /| | / /_/ / ,<   
   ___/ / ____/ ___ |/ _, _/ /| |  
  /____/_/   /_/  |_/_/ |_/_/ |_|  
```

---

## What is Spark?

Spark is the intelligence layer that makes AI agents **learn from experience**.

```
OBSERVE → LEARN → STORE → PROMOTE → IMPROVE
    ↑                                    │
    └────────────────────────────────────┘
```

It combines:
- **Automatic observation** — captures every action without manual logging
- **Cognitive learning** — learns HOW to think, not just what to do
- **Persistent memory** — stores learnings in Mind for semantic retrieval
- **Human-readable output** — writes to `.learnings/` markdown files
- **Auto-promotion** — elevates high-value insights to CLAUDE.md/AGENTS.md
- **Context-aware bootstrap** — filters learnings by project stack
- **Semantic intent detection** — catches polite redirects and implicit preferences
- **Skill extraction** — converts patterns into reusable skills
- **Outcome logging** — records skill/orchestration/project decision outcomes
- **Prediction loop** — validates insights against outcomes (beyond tool success/failure)

---

## Current Status: Phase 1 Complete ✅

**As of 2026-02-02**, Spark has completed Phase 1: Cognitive Filtering.

### What Changed

| Before | After |
|--------|-------|
| Captured ALL tool events | Only captures cognitive insights |
| 1,427 stored "learnings" | 231 truly useful insights |
| 84% primitive data | 0% primitive data |
| Tool sequences, timing, error rates | User preferences, wisdom, context |

### Philosophy

```
OLD: Capture everything → Filter → Still noisy
NEW: Only capture what a human would find useful
```

### Current Cognitive Insights (231 total)

- **User Understanding** (171): Preferences, styles, frustrations
- **Context** (23): Windows issues, setup gotchas
- **Wisdom** (17): Principles like "Ship fast, iterate faster"
- **Self-Awareness** (14): What Spark struggles with
- **Reasoning** (6): Domain-specific knowledge

See `CHANGELOG.md` for full details on the Phase 1 refactor.

---

## Core Documents (Start Here)

- `CORE.md` — Vision and phase roadmap from primitive telemetry to superintelligence
- `CORE_GAPS.md` — What exists vs what must be built or cleaned
- `CORE_GAPS_PLAN.md` — How each gap gets filled with workflows and architecture
- `CORE_IMPLEMENTATION_PLAN.md` — Context-rich build plan with sequencing and metrics

---

## Quick Start

### 1. Install

```bash
pip install vibeship-spark
```

Or clone and install:

```bash
git clone https://github.com/vibeforge1111/vibeship-spark-intelligence.git
cd vibeship-spark-intelligence
pip install -e .
```

### 2. Start Mind (Optional but recommended)

```bash
pip install vibeship-mind
python -m mind.lite_tier
```

Mind provides persistent semantic memory. Without it, Spark still works but learnings are local only.

### 3. Run Spark

```bash
python -m spark.cli status
# or: spark status
```

If you want the background services (sparkd + bridge_worker + dashboard) running
continuously, start them via the launcher:

```bash
python -m spark.cli up
# or: spark up
```

Windows:
```bat
start_spark.bat
```

The watchdog auto-restarts workers and warns on queue growth. Set
`SPARK_NO_WATCHDOG=1` to disable it.

Check daemon status:
```bash
python -m spark.cli services
# or: spark services
```

Auto-start at login (recommended):
```bash
spark up --sync-context
```

Windows helper:
```powershell
./scripts/install_autostart_windows.ps1
```

macOS (launchd):
```bash
launchctl load -w ~/Library/LaunchAgents/co.vibeship.spark.plist
```

Linux (systemd user service):
```bash
systemctl --user enable --now spark-up.service
```

Full Windows/macOS/Linux examples are in `docs/QUICKSTART.md`.

Per-project ensure (optional):
```bash
spark ensure --sync-context --project .
```

### 4. Session Bootstrap (Recommended)

Run a lightweight sync before launching your agent to load learnings into
platform context files.

```bash
# One-shot
python -m spark.cli sync-context

# Wrapper launchers (sync then launch)
./scripts/spark-claude.sh
./scripts/spark-cursor.sh
./scripts/spark-windsurf.sh
./scripts/spark-clawdbot.sh
```

Windows (PowerShell / CMD):
```bat
scripts\spark-claude.bat
scripts\spark-cursor.bat
scripts\spark-windsurf.bat
scripts\spark-clawdbot.bat
```

Clawdbot workspace override (recommended). By default Spark writes to `USER.md` and `SPARK_CONTEXT.md`:
```bash
SPARK_CLAWDBOT_WORKSPACE=~/clawd
```

Clawdbot target override (optional):
```bash
# Comma-separated filenames in the workspace
SPARK_CLAWDBOT_TARGETS=USER.md,TOOLS.md
```

Clawdbot path override (advanced):
```bash
SPARK_CLAWDBOT_CONTEXT_PATH=~/clawd/SPARK_CONTEXT.md
```

Default targets are `USER.md` and `SPARK_CONTEXT.md`.

Optional: set a scheduled task to run `spark sync-context` every
10–30 minutes for sessions started outside wrappers (see `docs/QUICKSTART.md`).

Local dev alternative (from repo root):

```bash
python -m spark.cli status
```

Drain the processing backlog (pattern detection + capture):
```bash
python -m spark.cli process --drain
```

If `python -m spark.cli` fails because the package isn't installed, run:

```bash
pip install -e .
```

---

## Configuration

Spark keeps defaults minimal. Set these env vars to opt in:

- `SPARK_DEBUG=1` to emit internal debug logs to stderr.
- `SPARK_WORKSPACE=/path/to/workspace` to override the default `~/clawd` used by the bridge.
- `SPARK_LOG_DIR=~/.spark/logs` to override where logs are written.
- `SPARK_LOG_TEE=0` to disable teeing stdout/stderr into log files.
- `SPARK_NO_WATCHDOG=1` to skip the watchdog when using launch scripts.

Tip: leave `SPARK_DEBUG` off for normal use. Enable it temporarily when troubleshooting to avoid extra log noise.

---

## How It Works

### The Learning Loop

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   OBSERVE   │────▶│    LEARN    │────▶│    STORE    │
│   (hooks)   │     │ (cognitive) │     │   (mind)    │
└─────────────┘     └─────────────┘     └──────┬──────┘
                                               │
┌─────────────┐     ┌─────────────┐            │
│   IMPROVE   │◀────│   PROMOTE   │◀───────────┘
│  (behavior) │     │ (CLAUDE.md) │
└─────────────┘     └─────────────┘
```

### Cognitive Learning Categories

Spark doesn't just learn WHAT works — it learns WHY:

| Category | What It Learns |
|----------|----------------|
| **Self-Awareness** | When am I overconfident? What are my blind spots? |
| **User Understanding** | Preferences, expertise, communication style |
| **Reasoning** | Why did an approach work, not just that it worked |
| **Context** | When does a pattern apply vs not apply? |
| **Wisdom** | General principles that transcend specific tools |
| **Meta-Learning** | How do I learn best? When should I ask vs act? |
| **Communication** | What explanations work well? |

### Output Formats

Spark writes learnings to multiple destinations:

| Destination | Format | Purpose |
|-------------|--------|---------|
| Mind Lite+ | SQLite + semantic | Persistent retrieval |
| `.learnings/*.md` | Markdown | Human-readable audit trail |
| `CLAUDE.md` | Promoted rules | Project conventions |
| `AGENTS.md` | Promoted workflows | Tool usage patterns |
| `skills/*.md` | Extracted skills | Reusable capabilities |

---

## Architecture

```
Spark/
├── lib/
│   ├── cognitive_learner.py   # Core cognitive learning
│   ├── mind_bridge.py         # Mind Lite+ integration
│   ├── markdown_writer.py     # .learnings/ output
│   ├── promoter.py            # Auto-promotion engine
│   ├── skill_extractor.py     # Pattern → skill conversion
│   ├── queue.py               # Fast event queue
│   └── ...
├── hooks/
│   ├── observe.py             # Observation hook (<50ms)
│   ├── session_start.py       # Session initialization
│   └── session_end.py         # Session cleanup
├── scripts/
│   ├── install.sh             # One-command setup
│   └── ...
└── docs/
    └── ...
```

---

## Integration

### With Claude Code (incl. inside Cursor)

1) Start Spark locally:
```bash
spark up
```

Check status:
```bash
spark services
```

2) Add Spark hooks to Claude Code (`.claude/settings.json`):
```json
{
  "hooks": {
    "PreToolUse": [{"matcher":"","hooks":[{"type":"command","command":"python3 /ABS/PATH/TO/SPARK/hooks/observe.py"}]}],
    "PostToolUse": [{"matcher":"","hooks":[{"type":"command","command":"python3 /ABS/PATH/TO/SPARK/hooks/observe.py"}]}],
    "PostToolUseFailure": [{"matcher":"","hooks":[{"type":"command","command":"python3 /ABS/PATH/TO/SPARK/hooks/observe.py"}]}],
    "UserPromptSubmit": [{"matcher":"","hooks":[{"type":"command","command":"python3 /ABS/PATH/TO/SPARK/hooks/observe.py"}]}]
  }
}
```

3) (Recommended in Cursor) Add Cursor tasks for explicit “remember” + TasteBank capture.
See: `docs/cursor.md`

Tip: print absolute hook paths for your machine:
```bash
./scripts/print_paths.sh
```
And install a ready-to-merge hook file:
```bash
./scripts/install_claude_hooks.sh
```

### With Clawdbot

Spark works automatically with Clawdbot's workspace model. Learnings sync to:
- `USER.md` - User preferences and working style
- `SPARK_CONTEXT.md` - Spark bootstrap context (ready for hook injection)

Override targets with `SPARK_CLAWDBOT_TARGETS=USER.md,TOOLS.md` if needed.

### Agent Context Injection (Opt-in)

If you spawn sub-agents, you can prepend a compact Spark context block to their
prompts. This is off by default to prevent bloat.

```bash
SPARK_AGENT_INJECT=1
SPARK_AGENT_CONTEXT_LIMIT=3
SPARK_AGENT_CONTEXT_MAX_CHARS=1200
```

Use `lib.orchestration.inject_agent_context(prompt)` when preparing a sub-agent prompt.

Example:
```python
from lib.orchestration import inject_agent_context

prompt = "Please audit the config loader for edge cases."
prompt = inject_agent_context(prompt)
```


### With Mind

When Mind is running, Spark automatically syncs learnings for semantic retrieval:

```python
from spark.lib.mind_bridge import retrieve_from_mind

# Find relevant learnings for current task
memories = retrieve_from_mind("how to handle API errors", limit=5)
```

---

## CLI Reference

```bash
# Start background services
python -m spark.cli up

# Show daemon/service status
python -m spark.cli services

# Ensure services are running (start missing)
python -m spark.cli ensure --sync-context --project .

# Stop background services
python -m spark.cli down

# Check status
python -m spark.cli status

# Sync learnings to Mind
python -m spark.cli sync

# Process offline queue
python -m spark.cli queue

# Run validation scan
python -m spark.cli validate

# Tip: v1 validates user preferences + communication; monitor before expanding scope

# Record explicit outcome check-in
python -m spark.cli outcome --result yes --text "Worked as expected"

# Show pending outcome check-in requests
python -m spark.cli outcome --pending

# Link outcome to last exposure (improves matching)
python -m spark.cli outcome --result yes --link-latest --text "Worked as expected"

# Auto-link outcomes within a 30-minute window
python -m spark.cli outcome --result yes --auto-link --text "Worked as expected"

# Evaluate predictions vs outcomes (last 7 days)
python -m spark.cli eval --days 7

# Validate recent queue events (ingest hygiene)
python -m spark.cli validate-ingest --limit 200
# This writes ~/.spark/ingest_report.json unless --no-write is set

# Project questioning + capture
python -m spark.cli project init --domain game_dev
python -m spark.cli project questions
python -m spark.cli project answer game_core_loop --text "Core loop feels satisfying when the grab succeeds 60% of the time."
python -m spark.cli project capture --type insight --text "Claw physics: grip strength vs weight balance matters" --impact "player success rate"
python -m spark.cli project capture --type reference --text "Claw machines rely on adjustable claw strength tied to payout" --evidence "arcade teardown video"
python -m spark.cli project capture --type transfer --text "Calibrate difficulty with a target success window, not feature count"

# View recent learnings
python -m spark.cli learnings

# Run promotion check (also updates PROJECT.md)
python -m spark.cli promote

# Sync bootstrap context to platform files
python -m spark.cli sync-context

# Preview/apply decay-based pruning
python -m spark.cli decay
```

---

## Configuration

Create `~/.spark/config.json`:

```json
{
  "mind_url": "http://localhost:8080",
  "user_id": "your-user-id",
  "auto_sync": true,
  "auto_promote": true,
  "markdown_output": true,
  "learnings_dir": ".learnings"
}
```

---

## Part of Vibeship

Spark is part of the **Vibeship Ecosystem**:

- **Mind** — Persistent memory with semantic search
- **Spark** — Self-evolving intelligence layer (this project)
- **Spawner** — Skill loading and orchestration
- **H70** — 500+ expert skills

Together, they create AI agents that continuously improve.

---

## Project Intelligence

Spark now supports project-level questioning and capture. See:
`docs/PROJECT_INTELLIGENCE.md`

---

## Chips - Domain-Specific Intelligence

**Chips teach Spark *what* to learn, not just *how* to learn.**

Chips are YAML specifications that define:
- **Triggers** — When to activate (patterns, events, tools)
- **Observers** — What data to capture
- **Learners** — What patterns to detect
- **Outcomes** — How to measure success
- **Questions** — What context helps learning

```bash
# List installed chips
spark chips list

# Install a chip
spark chips install chips/spark-core.chip.yaml

# Activate it
spark chips activate spark-core

# See what questions it asks
spark chips questions spark-core

# Check its insights
spark chips insights spark-core
```

### Built-in Chips

| Chip | Domains | What It Learns |
|------|---------|----------------|
| `spark-core` | coding, debugging | Tool effectiveness, error patterns, preferences |

### Example Chips

See `chips/examples/` for domain-specific templates:
- `marketing-growth.chip.yaml` — Channel ROI, messaging, audience signals
- `product-development.chip.yaml` — Feature impact, user needs, launch patterns
- `sales-intelligence.chip.yaml` — Win patterns, objection handling, cycle optimization

### Create Your Own

```yaml
chip:
  id: my-domain
  name: My Domain Intelligence
  domains: [my-area]

triggers:
  patterns:
    - "success phrase"
    - "failure phrase"

observers:
  - name: my_observation
    triggers: ["capture this"]
    capture:
      required:
        key_field: What this captures

learners:
  - name: my_learner
    type: correlation
    learn:
      - "What patterns to detect"

outcomes:
  positive:
    - condition: "metric > threshold"
      insight: "This approach works"

questions:
  - id: domain_goal
    question: What is the goal?
    category: goal
    affects_learning: [my_learner]
```

Full documentation: `docs/CHIPS.md`
Workflow guide: `docs/CHIP_WORKFLOW.md`

---

## License

MIT

---

*the spark that learns*
