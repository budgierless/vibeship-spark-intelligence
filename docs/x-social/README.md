# Spark X Social Intelligence System

Everything about how Spark learns, communicates, evolves, and grows on X/Twitter.

## Documentation Map

| Doc | What It Covers |
|-----|---------------|
| [ARCHITECTURE.md](ARCHITECTURE.md) | Full system architecture, data flows, module connections |
| [EVOLUTION.md](EVOLUTION.md) | How Spark self-evolves from X interactions and research |
| [VOICE.md](VOICE.md) | Voice/personality system, tone selection, humanization |
| [RESEARCH.md](RESEARCH.md) | Autonomous research engine, topics, LLM analysis |
| [DASHBOARD.md](DASHBOARD.md) | Social intelligence dashboard (localhost:8770) |
| [PATTERNS.md](../social_psychology_patterns.md) | 33 psychological engagement patterns |
| [OPERATIONS.md](OPERATIONS.md) | How to post, reply, like, run research, check outcomes |

## Quick Start

```bash
# Post a tweet
python mcp-servers/x-twitter-mcp/tweet.py "your text here"

# Reply to someone
python mcp-servers/x-twitter-mcp/tweet.py "reply text" --reply-to TWEET_ID

# Like a tweet
python mcp-servers/x-twitter-mcp/tweet.py --like TWEET_ID

# Run research
python scripts/run_research.py --quick

# Run evolution cycle (learn from outcomes)
python -c "from lib.x_evolution import run_evolution_cycle; run_evolution_cycle()"

# Run evolution with gap diagnosis
python -c "from lib.x_evolution import run_evolution_cycle; r = run_evolution_cycle(include_diagnosis=True); print(r['gaps']['overall_health'])"

# Start dashboard
python dashboard/social_intel/app.py
# Visit http://localhost:8770
```

## System Status

- **Account**: [@Spark_coded](https://x.com/Spark_coded)
- **Dashboard**: http://localhost:8770
- **Chips Active**: social-convo, engagement-pulse, x_social
- **Evolution**: Live (14+ events from 88 research insights)
- **Core Integration**: CognitiveLearner + MetaRalph + Advisor + EIDOS
- **Research**: 12 sessions completed, 4,500+ tweets analyzed
- **Gap Diagnosis**: Real-time system health monitoring
- **Tests**: 32 tests in `tests/test_x_voice.py`

## File Map

```
lib/
  x_voice.py              Voice engine (tone, warmth, rendering, research intel)
  x_voice_config.json      Voice config (cultural rules, identity, learned_playbook)
  x_humanizer.py           AI tell removal, em dash removal, lowercase mode
  spark_voice.py           Core personality (opinions, growth)
  x_research.py            5-phase autonomous research engine (noise-guarded)
  x_evolution.py           Self-evolution + core integration + gap diagnosis
  x_client.py              Twitter API wrapper

chips/
  social-convo.chip.yaml   Conversation intelligence chip
  engagement-pulse.chip.yaml  Engagement tracking chip
  x-social.chip.yaml       Social relationships + trends chip

scripts/
  run_research.py          CLI for research sessions

dashboard/social_intel/
  app.py                   FastAPI backend (10 endpoints, port 8770)
  index.html               Single-page dashboard frontend

tests/
  test_x_voice.py          32 tests for voice/humanizer/evolution

mcp-servers/x-twitter-mcp/
  tweet.py                 Direct posting/liking/deleting (OAuth 1.0a)
  .env                     Credentials (not in repo)
```

## Data Locations

All state lives in `~/.spark/`:

| File | What |
|------|------|
| `chip_insights/engagement-pulse.jsonl` | High-performer tweet analysis |
| `chip_insights/x_social.jsonl` | Relationships, trends, topics |
| `chip_insights/social-convo.jsonl` | Conversation patterns |
| `x_research_state.json` | Research sessions, topics, intents |
| `x_watchlist.json` | Tracked accounts |
| `x_evolution_state.json` | Evolution weights, tracked replies |
| `x_evolution_log.jsonl` | Every evolution event (dashboard reads this) |
| `x_voice/profiles.json` | Per-user tone/warmth profiles |
| `voice.json` | Opinions, growth moments |
