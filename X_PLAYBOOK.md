# Spark X Playbook

Everything you need to use Spark's X/Twitter intelligence. Six tools, one system.

## The Six Tools

```
                YOU POST A TWEET
                      |
              +-------v--------+
              |   X Voice      |  Picks tone, sounds human
              |   + Humanizer  |  Strips AI tells
              +-------+--------+
                      |
              +-------v--------+
              |   Pulse        |  Tracks how it performs
              |   (Engagement) |  Predicts likes/replies
              +-------+--------+
                      |
     SOMEONE MENTIONS YOU ON X
                      |
              +-------v--------+
              |   Multiplier   |  Scores the mention (0-10)
              |   (Scoring)    |  Decides: reward / engage / ignore
              +-------+--------+
                      |
              +-------v--------+
              |   ConvoIQ      |  Learns what replies work
              |   (Reply Intel)|  Recommends best hook
              +-------+--------+
                      |
              +-------v--------+
              |   NicheNet     |  Maps relationships
              |   (Network)    |  Finds opportunities
              +-------+--------+
                      |
              +-------v--------+
              |   Scheduler    |  Runs it all automatically
              |   (Daemon)     |  Every 10min-24hr
              +----------------+
```

---

## 1. X Voice -- Your Personality

Makes everything you post sound human and consistent.

### Use It

```python
from lib.x_voice import get_x_voice
from lib.x_humanizer import get_humanizer

voice = get_x_voice()
humanizer = get_humanizer()

# Pick the right tone for a reply
tone = voice.select_tone(context_type="reply", user_handle="@alice", topic="AI")
# Returns: "witty", "technical", "conversational", or "provocative"

# Render a tweet with personality
tweet = voice.render_tweet(
    "Spark's chip system learns domain patterns automatically",
    style="witty",
    reply_to_handle="@alice"
)

# Make any text sound human (strips AI tells)
clean = humanizer.humanize_tweet("It is important to note that this framework is delightful")
# Returns: "this framework's genuinely delightful"

# Check how human something sounds (0-1)
score = humanizer.score_humanness("Furthermore, I would like to point out...")
# Returns: ~0.3 (bad)

# Check relationship warmth with someone
warmth = voice.get_user_warmth("@alice")
# Returns: "cold", "cool", "warm", "hot", or "ally"

# Should we engage with this tweet?
engage, reason = voice.should_engage(
    "Has anyone tried Spark for trading bots?",
    author_handle="@curious_dev"
)
```

### Ask Claude

- "Write a reply to this tweet in Spark's voice: [tweet]"
- "What tone should I use with @alice?"
- "Make this sound more human: [text]"
- "Should we engage with this tweet: [tweet]"

### Four Tones

| Tone | When | Example |
|------|------|---------|
| **Witty** | Fun topics, warm relationships | "chip system goes brrr" |
| **Technical** | Dev questions, cold relationships | "the pipeline processes events through..." |
| **Conversational** | General, getting-to-know | "yeah we built that because..." |
| **Provocative** | Hot takes, debates | "hot take: RAG is dead for agent memory" |

### Warmth Levels

```
cold --> cool --> warm --> hot --> ally
  (stranger)  (acquaintance)  (friend)  (collaborator)
```

Warmer = more casual tone, higher engagement priority.

**State:** `~/.spark/x_voice/profiles.json`

---

## 2. Multiplier -- Scoring Mentions

Scores every @mention across 6 dimensions, decides what to do.

### Use It

```python
# Score a single tweet
from src.scorer import TweetQualityScorer

scorer = TweetQualityScorer()
score = scorer.score_tweet(
    tweet_id="123",
    author="builder_alice",
    text="I built a trading bot using Spark's chip system and the learning loop is impressive"
)
print(f"Score: {score.total_score:.1f}/10")
print(f"Tier: {score.tier}")      # "reward", "engage", or "ignore"
print(f"Why: {score.reasoning}")

# Full pipeline with decisions
from src.mention_monitor import MentionMonitor
from src.models import MentionEvent

monitor = MentionMonitor()
mention = MentionEvent(
    tweet_id="456",
    author="curious_dev",
    text="How does Spark's cognitive learner compare to standard RAG?",
    likes=15, retweets=3,
    author_followers=200,
    author_account_age_days=365,
)

decisions = monitor.process_mentions([mention])
for d in decisions:
    print(f"Action: {d.action}")       # "reward", "engage", or "ignore"
    print(f"Reply: {d.reply_text}")
    if d.multiplier:
        print(f"Tier: {d.multiplier.multiplier_tier} ({d.multiplier.multiplier_value}x)")
```

### Ask Claude

- "Check recent @Spark mentions and run them through the Multiplier"
- "Score this tweet: [text]"
- "Show me the Multiplier leaderboard"
- "Show me pending draft replies"

### The 6 Scoring Dimensions

| Dimension | Weight | High Score |
|-----------|--------|-----------|
| Originality | 25% | Unique thought, personal experience |
| Depth | 20% | Technical detail, explanations |
| Engagement | 20% | Questions, invites discussion |
| Accuracy | 10% | Mentions real Spark features |
| Creativity | 15% | Novel use cases, ideas |
| Effort | 10% | Long-form, proper formatting |

### What Happens at Each Score

| Score | Action | Example |
|-------|--------|---------|
| 7.0+ | **Reward** + reply | Bronze 1.5x / Silver 2x / Gold 3x / Diamond 5x |
| 4.0-6.9 | **Engage** (reply, no reward) | Answer their question helpfully |
| < 4.0 | **Ignore** | Wallet drops, "gm", airdrop begging |

### Anti-Gaming

- Max 2 rewards per author per day
- 6 hour cooldown between rewards
- Account must be 7+ days old with 10+ followers
- 80% duplicate detection blocks copy-paste
- Gaming flags for bad actors

**Location:** `C:\Users\USER\Desktop\spark-multiplier\`
**DB:** `~/.spark/multiplier/scored_mentions.db`

---

## 3. Pulse -- Engagement Tracking

Tracks how tweets perform over time. Predicts engagement, catches surprises.

### Use It

```python
from lib.engagement_tracker import get_engagement_tracker

tracker = get_engagement_tracker()

# Register a tweet you just posted
tracked = tracker.register_tweet(
    tweet_id="789",
    content="Hot take: Spark's approach to learning beats RAG",
    tone="provocative",
    topic="AI"
)

# Get engagement prediction before posting
prediction = tracker.predict_engagement(
    tone="provocative",
    topic="AI",
    is_reply=False
)
print(f"Predicted: {prediction.predicted_likes} likes, {prediction.predicted_replies} replies")

# Take a snapshot (scheduler does this automatically)
tracker.take_snapshot("789", likes=42, replies=15, retweets=8, impressions=2000)

# Check for surprises (viral or flop)
surprise = tracker.detect_surprise("789")
if surprise:
    print(f"Surprise! {surprise['type']}: {surprise['ratio']:.1f}x predicted")

# How accurate are our predictions?
accuracy = tracker.get_prediction_accuracy()
print(f"Prediction accuracy: {accuracy}")
```

### Ask Claude

- "How did my last tweet perform?"
- "Show Pulse stats"
- "What's our prediction accuracy?"
- "Any surprise performers today?"

### Snapshot Schedule

| Time | What |
|------|------|
| 1 hour | Early signal |
| 6 hours | Mid-range performance |
| 24 hours | Final performance |

**Surprise:** actual > 2x predicted = viral moment. actual < 0.3x predicted = flop.

**State:** `~/.spark/engagement_pulse/tracked_tweets.json`

---

## 4. ConvoIQ -- Reply Intelligence

Learns what makes replies land. Extracts "DNA" from successful conversations.

### Use It

```python
from lib.convo_analyzer import get_convo_analyzer

analyzer = get_convo_analyzer()

# Score a reply draft before sending
analysis = analyzer.analyze_reply(
    reply_text="What if we integrated Spark with a trading bot?",
    parent_text="Anyone building AI agents for trading?"
)
print(f"Hook type: {analysis.hook_type}")  # question, observation, challenge, agreement, addition
print(f"Strengths: {analysis.strengths}")
print(f"Suggestions: {analysis.suggestions}")

# Get best hook recommendation for a context
hook = analyzer.get_best_hook(
    parent_text="Spark's learning loop is interesting",
    author_handle="@dev_alice",
    topic="AI"
)
print(f"Use a {hook.hook_type}: {hook.template}")

# Feed a successful reply back for learning
analyzer.extract_dna(
    reply_text="What if we combined this with on-chain data?",
    engagement_score=8.5,
    parent_text="AI agents need better memory",
    topic_tags=["AI", "DeFi"]
)
```

### Ask Claude

- "What's the best way to reply to this: [tweet]"
- "Score this reply draft: [text]"
- "What hook type works best for AI topics?"
- "Show ConvoIQ stats"

### Five Hook Types

| Hook | Example | Best For |
|------|---------|----------|
| **Question** | "What if we combined...?" | Sparking discussion |
| **Observation** | "I noticed that..." | Showing insight |
| **Challenge** | "Actually, have you considered..." | Debates |
| **Agreement** | "Yes, and also..." | Building rapport |
| **Addition** | "Plus there's this angle..." | Adding value |

**State:** `~/.spark/convo_iq/conversation_dna.json`

---

## 5. NicheNet -- Relationship Mapping

Maps the social graph around your niche. Knows who matters, who's warming up.

### Use It

```python
from lib.niche_mapper import get_niche_mapper

mapper = get_niche_mapper()

# Track a new account
mapper.discover_account(
    handle="@interesting_dev",
    topics=["AI", "agents"],
    relevance=0.7,
    discovered_via="daily_research"
)

# Update relationship after interaction
old, new = mapper.update_relationship("@interesting_dev", "we_reply")
print(f"Warmth: {old} -> {new}")

# Get strategic opportunities
opportunities = mapper.generate_opportunities()
for opp in opportunities:
    print(f"[Urgency {opp.urgency}/5] {opp.target}: {opp.reason}")
    print(f"  Suggested tone: {opp.suggested_tone}")

# Find warm accounts to engage with
warm_accounts = mapper.get_accounts_by_warmth("warm")

# Get network overview
stats = mapper.get_network_stats()
print(f"Tracking {stats['tracked_accounts']} accounts")
print(f"Warmth: {stats['warmth_distribution']}")
```

### Ask Claude

- "Show me NicheNet opportunities"
- "Who are our warmest contacts?"
- "What accounts should we engage with today?"
- "Show network stats"

### Relationship Events

| Event | Trigger |
|-------|---------|
| `we_reply` | We reply to them |
| `reply_received` | They reply to us |
| `mutual_like` | We like their tweet |
| `they_mention_us` | They mention us |
| `multi_turn_convo` | Back-and-forth thread |
| `they_share_our_content` | They RT/quote us |
| `collaboration` | Joint project or thread |

**State:** `~/.spark/niche_intel/` (tracked_accounts.json, hubs.json, opportunities.json)

---

## 6. Scheduler -- Runs It All

Background daemon that feeds data to all five tools automatically.

### Start It

```bash
# Start everything (scheduler included)
python -m spark.cli up

# Or run scheduler alone
python spark_scheduler.py
```

### Run Tasks Manually

```bash
python spark_scheduler.py --task mention_poll --force
python spark_scheduler.py --task engagement_snapshots --force
python spark_scheduler.py --task daily_research --force
python spark_scheduler.py --task niche_scan --force
python spark_scheduler.py --once   # all due tasks, then exit
```

### What Runs When

| Task | Every | What |
|------|-------|------|
| Mention poll | 10 min | Fetches @mentions, scores through Multiplier, queues draft replies |
| Engagement snapshots | 30 min | Gets actual metrics for Pulse tracking |
| Daily research | 24 hours | Searches X for your topics, feeds NicheNet + ConvoIQ |
| Niche scan | 6 hours | Updates account map from research |

### Review Draft Replies

Scheduler scores mentions but **never auto-posts**. Drafts go here:

```
~/.spark/multiplier/draft_replies.json
```

Ask Claude: "Show me pending Multiplier replies"

### Change Intervals

Edit `~/.spark/tuneables.json`:

```json
{
  "scheduler": {
    "enabled": true,
    "mention_poll_interval": 600,
    "engagement_snapshot_interval": 1800,
    "daily_research_interval": 86400,
    "niche_scan_interval": 21600
  }
}
```

No restart needed -- picks up changes on next cycle.

**State:** `~/.spark/scheduler/state.json`, `~/.spark/scheduler/heartbeat.json`

---

## All State Files

Everything lives in `~/.spark/`:

```
~/.spark/
  x_voice/profiles.json              # Tone history, warmth levels
  convo_iq/conversation_dna.json     # Learned reply patterns
  convo_iq/reply_log.jsonl           # Reply analysis log
  engagement_pulse/tracked_tweets.json  # Tweet performance tracking
  niche_intel/tracked_accounts.json  # 500 tracked accounts
  niche_intel/hubs.json              # Conversation hubs
  niche_intel/opportunities.json     # Engagement opportunities
  multiplier/scored_mentions.db      # SQLite scoring database
  multiplier/draft_replies.json      # Pending reply queue
  scheduler/state.json               # Task run timestamps
  scheduler/heartbeat.json           # Health signal
  tuneables.json                     # All configuration
```

## Environment Variables Required

```
TWITTER_BEARER_TOKEN
TWITTER_API_KEY
TWITTER_API_SECRET
TWITTER_ACCESS_TOKEN
TWITTER_ACCESS_TOKEN_SECRET
```

## Quick Commands

| What | How |
|------|-----|
| Start everything | `python -m spark.cli up` |
| Check status | `python -m spark.cli status` |
| Stop everything | `python -m spark.cli down` |
| Poll mentions now | `python spark_scheduler.py --task mention_poll --force` |
| Run all due tasks | `python spark_scheduler.py --once` |
| Run tests | `python -m pytest tests/test_x_voice.py tests/test_convo_iq.py tests/test_engagement_pulse.py tests/test_niche_net.py tests/test_x_client.py tests/test_scheduler.py -v` |

## Test Coverage

| Suite | Tests |
|-------|-------|
| X Voice + Humanizer | 32 |
| ConvoIQ | 37 |
| Pulse | 33 |
| NicheNet | 30 |
| X Client | 26 |
| Scheduler | 22 |
| Multiplier (separate repo) | 84 |
| **Total** | **264** |
