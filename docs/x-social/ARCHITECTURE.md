# X Social Intelligence Architecture

## System Overview

Spark's X intelligence is a closed-loop system: research finds what works, evolution adapts behavior, voice applies the learnings, and outcomes feed back into the next cycle.

```
              RESEARCH (finds patterns)
                    |
        +-----------+-----------+
        |                       |
   EVOLUTION                 CHIPS
   (adapts weights)        (store insights)
        |                       |
        +------->  VOICE  <-----+
                 (applies)
                    |
              POSTS ON X
                    |
              OUTCOMES
                    |
              EVOLUTION
              (learns)
```

## Module Architecture

```
+------------------------------------------------------------------+
|                         X SOCIAL SYSTEM                          |
|                                                                    |
|  +-----------------------+     +---------------------------+     |
|  |   RESEARCH ENGINE     |     |   EVOLUTION ENGINE         |     |
|  |   lib/x_research.py   |     |   lib/x_evolution.py       |     |
|  |                       |     |                           |     |
|  |  Phase 1: Search      |     |  1. Track reply outcomes  |     |
|  |  Phase 2: Study       |---->|  2. Evolve from research  |     |
|  |  Phase 3: Analyze     |     |  3. Shift voice weights   |     |
|  |  Phase 4: Trends      |     |  4. Quality-gate (Ralph)  |     |
|  |  Phase 5: Self-Evolve |     |  5. Promote to cognitive  |     |
|  +-----------+-----------+     |  6. Diagnose system gaps  |     |
|              |                 +---+-------+-------+------+     |
|              v                     |       |       |             |
|  +-----------+-----------+         |       |       |             |
|  |      CHIP INSIGHTS     |         v       v       v             |
|  |  ~/.spark/chip_insights/|    +------+ +------+ +------+       |
|  |                       |    |Ralph | |Cogni-| |EIDOS |       |
|  |  engagement-pulse.jsonl|    |roast | |tive  | |dist- |       |
|  |  x_social.jsonl       |    |gate  | |learn | |illat.|       |
|  |  social-convo.jsonl   |    +------+ +------+ +------+       |
|  +-----------+-----------+     (Spark Intelligence core)         |
|              |                              |                     |
|              v                              v                     |
|  +-----------+-----------+     +------------+--------------+     |
|  |  VOICE SYSTEM          |     |    DASHBOARD (port 8770)  |     |
|  |  lib/x_voice.py        |     |    9 API endpoints        |     |
|  |  lib/x_humanizer.py    |     |                           |     |
|  |  lib/spark_voice.py    |     |  /api/overview   /api/gaps|     |
|  |  lib/x_voice_config.json|     |  /api/topics    /api/evo |     |
|  |                        |     |  /api/patterns  /api/res  |     |
|  |  get_research_intel()  |     |  /api/convo     /api/grow |     |
|  |  learned_playbook      |     |  /api/learning-flow       |     |
|  +-----------+-----------+     +------------+--------------+     |
+------------------------------------------------------------------+
```

## Core System Integration

The X evolution engine is deeply integrated with Spark Intelligence:

| Core System | Integration | Purpose |
|-------------|-------------|---------|
| **CognitiveLearner** | `add_insight()` with proper categories | Store evolved patterns as reasoning/wisdom/context insights |
| **MetaRalph** | `roast()` quality gate (score >= 4) | Filter primitive evolution events before cognitive promotion |
| **Advisor** | `report_action_outcome()` | Track effectiveness of evolution-driven decisions |
| **EIDOS** | `retrieve_for_intent()` | Check prior distillations before evolving (prior wisdom) |

```
Evolution Event -> MetaRalph roast() -> if QUALITY -> CognitiveLearner add_insight()
                                                   -> Advisor track outcome
                                     -> if PRIMITIVE -> filtered (not stored)
```

## Data Flow

### 1. Research -> Chips (One-way, always running)

```
Twitter API (bearer token, read-only)
    |
    v
SparkResearcher.search_topics()
    |
    +-- Finds tweets with 50+ likes
    +-- LLM (phi4-mini) analyzes high performers
    +-- Detects: triggers, strategies, hooks, writing_patterns
    |
    v
store_insight("engagement-pulse", analysis)
    |
    v
~/.spark/chip_insights/engagement-pulse.jsonl
```

### 2. Chips -> Evolution (Periodic, from research data)

```
engagement-pulse.jsonl (88+ insights)
    |
    v
XEvolution.evolve_from_research()
    |
    +-- Aggregates trigger performance across all insights
    +-- Computes avg_likes per trigger vs global average
    +-- Shifts weights: boost high performers, reduce low
    |
    v
x_evolution_state.json  (voice_weights.triggers, voice_weights.strategies)
x_evolution_log.jsonl   (every evolution event logged)
```

### 3. Evolution -> Voice (Automatic, cached 60s)

```
x_evolution_state.json
    |
    v
XVoice._load_evolution_weights()  (cached 60s)
    |
    +-- get_preferred_triggers()  -> ["surprise", "urgency", "validation"]
    +-- get_avoided_triggers()    -> ["vulnerability"]
    +-- get_evolved_strategies()  -> {"announcement+storytelling": 1.28}
    |
    v
Used in tone selection and content guidance
```

### 3b. Research -> Voice (Live intelligence pipeline)

```
social-convo.jsonl (pattern_analysis entries)
    |
    v
XVoice.get_research_intelligence()
    |
    +-- Reads latest pattern_analysis from social-convo chip
    +-- Extracts: top_triggers, top_strategies, hooks, writing_patterns
    +-- Falls back to static learned_playbook in x_voice_config.json
    |
    v
XVoice.get_personality_context()
    |
    +-- Merges: identity + opinions + growth + research_intelligence
    |
    v
Used in content generation prompts
```

### 3c. Humanization Pipeline

```
Raw AI text
    |
    v
XHumanizer.humanize_tweet(text, lowercase=is_reply)
    |
    +-- Remove AI tells (hedge words, transitions, corporate speak)
    +-- Remove em dashes (unicode + triple/double hyphen -> comma)
    +-- Add contractions (cannot -> can't, etc.)
    +-- Clean whitespace
    +-- If reply: convert to lowercase (per learned playbook)
    |
    v
Human-sounding tweet text
```

### 4. Voice -> Posts -> Outcomes (Closed loop)

```
XVoice.select_tone() + render_tweet()
    |
    v
tweet.py posts to X (OAuth 1.0a)
    |
    v
XEvolution.register_reply(tweet_id, parent_id, text)
    |
    v (wait 1+ hours)
    |
XEvolution.check_reply_outcomes()
    |
    +-- Fetches engagement metrics from Twitter API
    +-- Classifies: "hit" (5+ likes or 3+ replies)
    |              "normal" (1+ engagement)
    |              "miss" (zero engagement)
    +-- Extracts traits from hits vs misses
    |
    v
Evolution events logged -> voice weights adjusted
```

## Three Intelligence Chips

### social-convo (HOW to reply)

- **Chip ID**: `social-convo`
- **Focus**: Conversation patterns, hook types, tone effectiveness
- **Observers**: reply_sent, reply_effectiveness, conversation_analysis, hook_extraction
- **Data**: `~/.spark/chip_insights/social-convo.jsonl`
- **Used by**: Advisor pre-tool advice, dashboard patterns section

### engagement-pulse (WHAT performs)

- **Chip ID**: `engagement-pulse`
- **Focus**: Tweet metrics, content strategy effectiveness, engagement predictions
- **Observers**: tweet_posted, engagement_snapshot, engagement_surprise
- **Data**: `~/.spark/chip_insights/engagement-pulse.jsonl` (88+ entries)
- **Used by**: Evolution engine (primary data source), dashboard research section

### x_social (WHO we know + WHAT's trending)

- **Chip ID**: `x_social`
- **Focus**: Relationships, account intelligence, trend tracking
- **Observers**: user_interaction, user_profile_update, trend_observed, influencer_study
- **Data**: `~/.spark/chip_insights/x_social.jsonl` (5,168+ entries)
- **Used by**: Dashboard overview/patterns, watchlist management

## API Flow (Reads vs Writes)

### Reads (MCP tools via bearer token)

MCP tools work for all read operations:
- `search_twitter` - Search tweets
- `get_tweet_details` - Get specific tweet
- `get_user_by_screen_name` - User lookup
- `get_user_followers` / `get_user_following`
- `get_timeline` / `get_latest_timeline`

### Writes (tweet.py via OAuth 1.0a)

MCP `post_tweet` returns 403 (bearer token = read-only). Use `tweet.py`:

```bash
# Post
python mcp-servers/x-twitter-mcp/tweet.py "text"

# Reply
python mcp-servers/x-twitter-mcp/tweet.py "text" --reply-to ID

# Like
python mcp-servers/x-twitter-mcp/tweet.py --like ID

# Delete
python mcp-servers/x-twitter-mcp/tweet.py --delete ID

# With media
python mcp-servers/x-twitter-mcp/tweet.py "text" --media path/to/image.png
```

## Credential Setup

Credentials in `mcp-servers/x-twitter-mcp/.env`:
```
TWITTER_API_KEY=...
TWITTER_API_SECRET=...
TWITTER_ACCESS_TOKEN=...
TWITTER_ACCESS_TOKEN_SECRET=...
TWITTER_BEARER_TOKEN=...
```

- OAuth 1.0a (API key + access token): Used by `tweet.py` for writes
- Bearer token: Used by research engine and MCP tools for reads
