# Spark Research Engine

Autonomous intelligence gathering from X/Twitter. Searches topics, studies accounts, detects trends, and evolves its own research priorities.

## Five-Phase Pipeline

```
Phase 1: SEARCH TOPICS     -> Find high-performing tweets
Phase 2: STUDY ACCOUNTS    -> Analyze watchlist recent activity
Phase 3: ANALYZE PATTERNS  -> Aggregate triggers, strategies, hooks
Phase 4: DETECT TRENDS     -> Compare volumes vs history
Phase 5: SELF-EVOLVE       -> Generate new intents, discover topics
```

## Phase 1: Topic Search

Searches 12+ tiered topics with engagement-filtered queries.

### Topic Tiers

| Tier | Schedule | Topics |
|------|----------|--------|
| 1 (core) | Every session | Vibe Coding, Claude Code, AI Agents, Claude Ecosystem, Agentic Systems |
| 2 (important) | Every 2nd session | AI Coding Tools, Prompt Engineering, Building in Public, AI Code Gen, MCP/Tool Use |
| 3 (frontier) | Every 3rd session | AGI, Frontier AI, Learning in Public, AI Pair Programming |

### Engagement Thresholds

```python
CATEGORY_MIN_LIKES = {
    "core": 50,        # Niche topics - only proven viral
    "technical": 75,   # Broader tech - higher bar
    "frontier": 100,   # Very broad - must be genuinely viral
    "culture": 75,
    "discovered": 50,
}
```

Queries include `min_faves:N` to filter at the API level.

### Adaptive Features

- **Consecutive zero skip**: Topics with 0 results for 3+ sessions are paused
- **Budget gating**: Stops searching when session budget exhausted (800 reads)
- **Since ID tracking**: Only fetches new tweets since last session

## Phase 2: Account Study

Studies watchlist accounts' recent tweets.

- **Priority**: Unstudied accounts first, then by staleness
- **Cap**: 5 accounts per session (was 10)
- **Skip**: Conversation-tier accounts (0-follower reply partners)
- **Analysis**: Compare recent avg_likes vs historical, identify hits/misses
- **LLM deep analysis**: Tweets with 50+ likes get phi4-mini analysis

### Account Relationships

| Tier | Criteria | Purpose |
|------|----------|---------|
| learn_from | 5K+ followers OR exceptional engagement | Follow to learn patterns |
| watch | Discovered via high engagement | Monitor, potential learn_from |
| conversation | Interacted with directly | Relationship tracking |

## Phase 3: Pattern Analysis

Aggregates findings from high performers:

- **Trigger ranking**: Which emotional triggers appear most in viral tweets
- **Strategy ranking**: Which content strategies get most engagement (from LLM)
- **Hook ranking**: Which engagement hooks work (from LLM)
- **Writing patterns**: Structural elements that correlate with performance
- **Questions vs statements**: Engagement comparison
- **Short vs long**: Length effect on engagement

## Phase 4: Trend Detection

Compares current session topic volumes against last 5 sessions:

| Direction | Criteria |
|-----------|----------|
| surging | Current > previous avg x 1.5 |
| rising | Current > previous avg x 1.1 |
| stable | Within 10% of average |
| declining | Current < previous avg x 0.5 |
| new | No previous data |

Surging/new trends trigger research intent generation.

## Phase 5: Self-Evolution

### Research Intents (auto-generated)
- "Deep dive into '{topic}' - volume surging"
- "Study why '{trigger}' trigger appears in {count} tweets"
- "Study @{handle}'s content strategy"
- Capped at 30 intents

### Topic Discovery
- Extracts bigrams from high-performer content
- If a bigram appears in 3+ high performers, creates new discovered topic
- Discovered topics get searched in future sessions

### Tier Adaptation
- Topics with >60% hit rate: promoted (tier 2 -> tier 1)
- Topics with <10% hit rate: demoted (tier 1 -> tier 2)

## LLM Integration (Ollama phi4-mini)

Local LLM analyzes tweets with 50+ likes:

```json
{
  "emotional_triggers": ["curiosity_gap", "surprise"],
  "content_strategy": "hot_take",
  "engagement_hooks": ["bold_claim", "open_loop"],
  "writing_patterns": ["short_sentences", "line_breaks"],
  "why_it_works": "Counter-intuitive claim stops the scroll",
  "replicable_lesson": "Lead with the most surprising stat"
}
```

Falls back to keyword-based trigger detection if Ollama unavailable.

## Noise Elimination

Four `store_insight()` calls in `x_research.py` are guarded to skip empty sessions:

```python
# Only store if we have actual data
if session_data:  # Not empty
    store_insight("engagement-pulse", session_data)
```

This eliminates ~95% of noise from empty research sessions that were previously writing empty insights to chip JSONL files.

## Budget System

```
SESSION_BUDGET:  800 tweet reads per session
MONTHLY_BUDGET:  10,000 reads (Twitter Basic plan)
Auto-reduction:  If monthly < 3x session budget, reduces session budget
```

Monthly usage tracked per YYYY-MM in research state.

## Running Research

```bash
# Full session (all 5 phases)
python scripts/run_research.py

# Quick (skip account study)
python scripts/run_research.py --quick

# Show current state
python scripts/run_research.py --status

# Continuous loop (every 4 hours)
python scripts/run_research.py --loop --interval 4

# Dry run (no API calls)
python scripts/run_research.py --dry-run
```

## MCP Ingestion

Research engine can also ingest tweets gathered via MCP tools (zero bearer_token cost):

```python
researcher = SparkResearcher()
researcher.ingest_mcp_results([
    {"text": "...", "likes": 500, "replies": 30, "user_handle": "@someone", "topic": "AI"},
])
```

## Current State (as of 2026-02-07)

- **Sessions run**: 12
- **Tweets analyzed**: 4,500+
- **Insights stored**: 4,600+
- **Watchlist**: ~20 accounts
- **Discovered topics**: 0 (threshold not met yet)
- **Research intents**: 5 active

## Files

| File | Purpose |
|------|---------|
| `lib/x_research.py` | SparkResearcher class (1,149 lines) |
| `scripts/run_research.py` | CLI runner (197 lines) |
| `~/.spark/x_research_state.json` | Sessions, topics, intents, performance |
| `~/.spark/x_watchlist.json` | Tracked accounts |
| `~/.spark/chip_insights/engagement-pulse.jsonl` | High-performer analysis |
| `~/.spark/chip_insights/x_social.jsonl` | Relationships, trends |
| `~/.spark/chip_insights/social-convo.jsonl` | Conversation patterns |
