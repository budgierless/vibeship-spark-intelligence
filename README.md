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
- **Skill extraction** — converts patterns into reusable skills

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

Clawdbot path override (optional):
```bash
SPARK_CLAWDBOT_CONTEXT_PATH=~/.clawdbot/agents/main/SPARK_CONTEXT.md
```

Clawdbot workspace override (recommended). By default Spark writes to `USER.md`:
```bash
SPARK_CLAWDBOT_WORKSPACE=~/clawd
```

Clawdbot target override (optional):
```bash
# Comma-separated filenames in the workspace
SPARK_CLAWDBOT_TARGETS=USER.md,TOOLS.md
```

Default targets are `USER.md` and `SPARK_CONTEXT.md`.

Optional: set a scheduled task to run `python -m spark.cli sync-context` every
10–30 minutes for sessions started outside wrappers (see `docs/QUICKSTART.md`).

Local dev alternative (from repo root):

```bash
python cli.py status
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
# from your cloned Spark repo
./scripts/run_local.sh
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
- `AGENTS.md` — Workflow patterns
- `TOOLS.md` — Tool-specific insights
- `SOUL.md` — Behavioral patterns

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
# Check status
python -m spark.cli status

# Sync learnings to Mind
python -m spark.cli sync

# Process offline queue
python -m spark.cli queue

# View recent learnings
python -m spark.cli learnings

# Run promotion check
python -m spark.cli promote

# Extract skills from patterns
python -m spark.cli extract-skills
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

## License

MIT

---

*the spark that learns*
