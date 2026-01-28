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

# Optional: Enable semantic search (requires ~500MB)
pip install sentence-transformers

# Test it works
python3 cli.py health
```

## Basic Usage

### Check Status

```bash
python3 cli.py status
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
python3 cli.py write
# Creates .learnings/LEARNINGS.md
```

## Optional: Scheduled Sync Backup

If you want a safety net (for sessions launched outside wrappers), run sync on a timer.

**Windows Task Scheduler**
- Action: `python`
- Args: `-m spark.cli sync-context`
- Start in: your repo root
- Trigger: every 10–30 minutes

**macOS/Linux (cron)**
```
*/20 * * * * cd /path/to/vibeship-spark-intelligence && python3 -m spark.cli sync-context >/dev/null 2>&1
```

### Promote High-Value Insights

```bash
# Check what's ready
python3 cli.py promote --dry-run

# Actually promote
python3 cli.py promote
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
python3 cli.py sync
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
    }]
  }
}
```

## Directory Structure

After running, Spark creates:

```
~/.spark/                      # Config and data
├── cognitive_insights.json    # Raw learnings
├── mind_sync_state.json       # Sync tracking
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
| `health` | Quick health check |
| `learnings` | List recent cognitive insights |
| `write` | Write insights to markdown |
| `promote` | Auto-promote high-value insights |
| `sync` | Sync to Mind (if running) |
| `queue` | Process offline sync queue |
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

## Next Steps

1. **Integrate with your workflow** — Set up the hooks
2. **Start Mind** — For persistent cross-project learning
3. **Review learnings** — `python3 cli.py learnings`
4. **Promote insights** — `python3 cli.py promote`

---

*Part of the Vibeship Ecosystem*
