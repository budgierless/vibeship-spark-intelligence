# X Operations Guide

Practical guide for everything Spark does on X.

## Posting

### Tweet
```bash
python mcp-servers/x-twitter-mcp/tweet.py "your text here"
```

### Reply
```bash
python mcp-servers/x-twitter-mcp/tweet.py "reply text" --reply-to 2020076511085359115
```

### Reply with hashtags
```bash
python mcp-servers/x-twitter-mcp/tweet.py "text" --reply-to ID --tags AI Spark
```

### Like
```bash
python mcp-servers/x-twitter-mcp/tweet.py --like 2020076511085359115
```

### Delete
```bash
python mcp-servers/x-twitter-mcp/tweet.py --delete 2020076511085359115
```

### Post with media
```bash
python mcp-servers/x-twitter-mcp/tweet.py "check this out" --media path/to/image.png
```

### Test credentials
```bash
python mcp-servers/x-twitter-mcp/tweet.py --test
```

## Reading (MCP Tools)

MCP tools work for all read operations. Use these in Claude Code:

```
# Search tweets
mcp__x-twitter__search_twitter(query="vibe coding", count=20)

# Get tweet details
mcp__x-twitter__get_tweet_details(tweet_id="2020076511085359115")

# Get user profile
mcp__x-twitter__get_user_by_screen_name(screen_name="Spark_coded")

# Get mentions
mcp__x-twitter__get_user_mentions(user_id="USER_ID")

# Get timeline
mcp__x-twitter__get_latest_timeline(count=20)

# Get trending
mcp__x-twitter__get_trends()
```

## Reply Style Guide

Spark's voice on X follows these rules:
- **All lowercase** (no capital letters in replies)
- **No em dashes** (use " - " or restructure)
- **1-3 sentences** max for replies
- **No emojis** unless the conversation calls for it
- **No hashtags** in replies
- **Research the post first** before replying (read the context)
- **Like the post** when you reply

## Research

### Run a full session
```bash
python scripts/run_research.py
```

### Quick mode (topics only, no account study)
```bash
python scripts/run_research.py --quick
```

### Check status
```bash
python scripts/run_research.py --status
```

### Continuous loop
```bash
python scripts/run_research.py --loop --interval 4
```

### Dry run (see queries without API calls)
```bash
python scripts/run_research.py --dry-run
```

## Evolution

### Run evolution cycle
```python
from lib.x_evolution import run_evolution_cycle
results = run_evolution_cycle()
print(f"Reply outcomes: {len(results['reply_outcomes'])}")
print(f"Research events: {len(results['research_events'])}")
print(f"Cognitive promoted: {results['cognitive_promoted']}")
```

### Register reply for tracking
```python
from lib.x_evolution import register_spark_reply
register_spark_reply("new_tweet_id", "parent_tweet_id", "reply text here")
```

### Check evolution status
```python
from lib.x_evolution import get_evolution
evo = get_evolution()
summary = evo.get_evolution_summary()
print(f"Total evolutions: {summary['total_evolutions']}")
print(f"Hit rate: {summary['reply_outcomes']['hit_rate']}")
```

### Diagnose system gaps
```python
from lib.x_evolution import get_evolution
evo = get_evolution()
gaps = evo.diagnose_gaps()
print(f"Overall health: {gaps['overall_health']}")
for g in gaps['gaps']:
    print(f"  [{g['severity']}] {g['system']}: {g['gap'][:80]}")
```

### Full evolution cycle with diagnosis
```python
from lib.x_evolution import run_evolution_cycle
results = run_evolution_cycle(include_diagnosis=True)
print(f"Events: {len(results['research_events'])}")
print(f"Promoted: {results['cognitive_promoted']}")
print(f"Gaps: {results['gaps']['total_gaps']}")
```

### Get voice guidance (what to emphasize)
```python
from lib.x_evolution import get_evolution
evo = get_evolution()
guidance = evo.get_voice_guidance()
print(f"Prefer triggers: {guidance['preferred_triggers']}")
print(f"Prefer strategies: {guidance['preferred_strategies']}")
```

## Dashboard

### Start
```bash
python dashboard/social_intel/app.py
# Visit http://localhost:8770
```

### API endpoints (for debugging)
```bash
curl http://localhost:8770/api/status
curl http://localhost:8770/api/overview
curl http://localhost:8770/api/evolution
curl http://localhost:8770/api/gaps
curl http://localhost:8770/api/research
curl http://localhost:8770/api/topics
curl http://localhost:8770/api/social-patterns
curl http://localhost:8770/api/conversations
curl http://localhost:8770/api/growth
```

## Workflow: Posting + Tracking

When replying to tweets:

1. **Read the tweet** (MCP `get_tweet_details`)
2. **Craft a reply** (follow voice style guide)
3. **Post it** (`tweet.py "text" --reply-to ID`)
4. **Like the parent** (`tweet.py --like ID`)
5. **Register for tracking** (`register_spark_reply(new_id, parent_id, text)`)
6. **Check later** (evolution engine checks outcomes after 1+ hours)

## Workflow: Research + Evolution

1. **Run research** (`python scripts/run_research.py`)
2. **Run evolution** (from Python: `run_evolution_cycle()`)
3. **Check dashboard** (http://localhost:8770 - evolution section)
4. **Review voice guidance** (see what triggers/strategies evolved)
5. **Apply in next posts** (use preferred triggers, avoid weak ones)

## Monitoring

### Check what's running
```bash
# Dashboard
curl -s http://localhost:8770/api/status

# Spark MCP
curl -s http://localhost:8787/status 2>/dev/null || echo "Not running"
```

### Check evolution state
```bash
python -c "
import json
from pathlib import Path
state = json.loads((Path.home()/'.spark'/'x_evolution_state.json').read_text())
triggers = state.get('voice_weights',{}).get('triggers',{})
for t,w in sorted(triggers.items(), key=lambda x: -x[1]):
    print(f'  {t}: {w:.3f}')
"
```

### Check research state
```bash
python scripts/run_research.py --status
```

## Troubleshooting

| Problem | Solution |
|---------|----------|
| `tweet.py` 403 error | Check `.env` credentials, run `tweet.py --test` |
| MCP post_tweet 403 | Normal - MCP uses bearer token (read-only). Use `tweet.py` instead |
| Research 402 error | Twitter API credits exhausted. Wait for monthly reset |
| Dashboard won't start | Check if port 8770 is in use: `netstat -ano | findstr 8770` |
| Ollama not available | Research falls back to keyword detection. Start Ollama: `ollama serve` |
| Evolution shows 0 events | Run `evolve_from_research()` after research completes |
