---
name: spark
description: "Self-evolving intelligence layer. Auto-captures learnings from tool usage, stores in Mind, writes to markdown, and promotes high-value insights to CLAUDE.md/AGENTS.md. Use when: (1) Starting a new session to load cognitive context, (2) After errors to learn from failures, (3) When patterns emerge to extract skills, (4) Periodically to sync and promote learnings."
---

# Spark

Self-evolving intelligence layer for AI agents.

## What It Does

Spark automatically:
1. **Observes** every tool call and its outcome
2. **Learns** cognitive patterns (not just what worked, but WHY)
3. **Stores** learnings in Mind for semantic retrieval
4. **Writes** human-readable logs to `.learnings/`
5. **Promotes** proven insights to CLAUDE.md/AGENTS.md
6. **Extracts** recurring patterns into reusable skills

## Quick Reference

| Situation | Action |
|-----------|--------|
| Session start | Spark auto-loads relevant cognitive context |
| Tool fails | Spark captures error pattern, suggests recovery |
| Pattern validated 3+ times | Consider promotion to CLAUDE.md |
| Recurring workflow identified | Extract as skill |
| Mind available | Sync for cross-project learning |

## Cognitive Categories

Spark learns in these categories:

| Category | What It Learns |
|----------|----------------|
| `self_awareness` | Overconfidence, blind spots, struggle areas |
| `user_understanding` | Preferences, expertise, communication style |
| `reasoning` | WHY things work, not just that they work |
| `context` | When patterns apply vs don't apply |
| `wisdom` | General principles across contexts |
| `meta_learning` | How to learn, when to ask vs act |
| `communication` | Explanation styles that work |

## CLI Commands

```bash
# Check system status
python cli.py status

# Sync to Mind
python cli.py sync

# Write learnings to markdown
python cli.py write

# Promote ready insights
python cli.py promote

# Sync bootstrap context to platform files
python cli.py sync-context

# Preview/apply decay-based pruning
python cli.py decay

# View recent learnings
python cli.py learnings --limit 20
```

## Integration

### With Claude Code

Add to `.claude/settings.json`:

```json
{
  "hooks": {
    "PostToolUse": [{
      "matcher": "",
      "hooks": [{
        "type": "command", 
        "command": "python /path/to/Spark/hooks/observe.py"
      }]
    }],
    "PostToolUseFailure": [{
      "matcher": "",
      "hooks": [{
        "type": "command",
        "command": "python /path/to/Spark/hooks/observe.py"
      }]
    }]
  }
}
```

### With Clawdbot

Spark automatically syncs learnings to workspace files:
- `AGENTS.md` — Workflow patterns
- `TOOLS.md` — Tool insights  
- `SOUL.md` — User preferences

### With Mind

When Mind is running (`python -m mind.lite_tier`), Spark syncs learnings for:
- Semantic search across all learnings
- Cross-project pattern transfer
- Decision tracking and outcome attribution

## Output Files

| File | Contents |
|------|----------|
| `.learnings/LEARNINGS.md` | All cognitive insights |
| `.learnings/ERRORS.md` | Error patterns and recoveries |
| `~/.spark/cognitive_insights.json` | Raw insight data |
| `~/.spark/queue/events.jsonl` | Event queue |

## Promotion Criteria

Insights are auto-promoted when:
- Reliability ≥ 70%
- Validated ≥ 3 times
- Not already promoted

Promotion targets:
- `CLAUDE.md` — Wisdom, reasoning, context rules
- `AGENTS.md` — Meta-learning, self-awareness
- `TOOLS.md` — Tool-specific context rules
- `SOUL.md` — User understanding, communication

## API

```python
from lib import (
    get_cognitive_learner,
    sync_all_to_mind,
    write_all_learnings,
    check_and_promote,
)

# Get learner instance
cognitive = get_cognitive_learner()

# Learn something
cognitive.learn_why(
    what_worked="Read before Edit",
    why_it_worked="Prevents content mismatch errors",
    context="File editing workflow"
)

# Sync to Mind
sync_all_to_mind()

# Write to markdown
write_all_learnings()

# Promote proven insights
check_and_promote()
```

## Part of Vibeship

- **Mind** — Persistent memory with semantic search
- **Spark** — Self-evolving intelligence (this)
- **Spawner** — Skill loading and orchestration
- **H70** — 500+ expert skills
