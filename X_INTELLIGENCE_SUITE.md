# Spark X Intelligence Suite

A complete X/Twitter intelligence system built into Spark. Four modules that work together to understand conversations, track relationships, predict engagement, and maintain a genuine personality on X.

## How It All Connects

```
                    +-----------------+
                    |   Daily Trend   |
                    |   Research      |
                    +--------+--------+
                             |
              searches X, feeds insights to:
                             |
         +-------------------+-------------------+
         |                   |                   |
    +----v----+        +-----v-----+       +-----v-----+
    | ConvoIQ |        |   Pulse   |       |  NicheNet |
    | (reply  |        | (engage-  |       | (relation-|
    | intel)  |        |  ment     |       |  ship     |
    +----+----+        |  tracking)|       |  mapping) |
         |             +-----+-----+       +-----+-----+
         |                   |                   |
         +-------------------+-------------------+
                             |
                      +------v------+
                      |   Advisor   |  <-- pre-tool advice engine
                      | (10 sources)|
                      +------+------+
                             |
                      +------v------+
                      |   X Voice   |  <-- personality & humanization
                      |  (tone,     |
                      |   warmth)   |
                      +-------------+
```

## The Four Modules

### 1. X Voice (`lib/x_voice.py`, `lib/x_humanizer.py`)

**What it does:** Gives Spark a personality on X. Every reply sounds human, never robotic.

**Core ideas:**
- **Tone selection**: 4 modes (witty, technical, conversational, provocative) chosen based on context
- **Per-user adaptation**: Tracks what tone resonates with each person and adjusts
- **Warmth state machine**: `cold -> cool -> warm -> hot -> ally` tracks relationship depth
- **AI tell removal**: 25+ regex patterns strip "Furthermore", "It's important to note", "delve into" and other robotic phrases
- **Humanness scoring**: Rates output 0-1 for how human it sounds

**Key classes:**
- `XVoice` - Main engine: `select_tone()`, `render_tweet()`, `render_thread()`, `should_engage()`, `update_warmth()`
- `XHumanizer` - AI tell removal, contraction injection, humanness scoring
- `XVoiceProfile` - Per-tone settings (emoji frequency, hashtag strategy, formality)
- `UserToneProfile` - Per-user resonance tracking

**State:** `~/.spark/x_voice/profiles.json`

**Example flow:**
```
Input: "It's important to note that this is a delightful framework"
  -> XHumanizer strips AI tells
  -> XVoice selects tone based on recipient's warmth level
Output: "this framework's genuinely delightful"
```

---

### 2. ConvoIQ (`lib/convo_analyzer.py`, `lib/convo_events.py`)

**What it does:** Learns what makes conversations land. Extracts "DNA" from successful interactions.

**Core ideas:**
- **Hook classification**: Every reply opener is one of 5 types: question, observation, challenge, agreement, addition
- **Conversation DNA**: Extracts patterns from high-engagement replies (hook + tone + structure = what worked)
- **Reply scoring**: Scores draft replies before sending (0-10 based on learned DNA)
- **Best hook recommendation**: Given context (topic, audience warmth), recommends the hook type most likely to land

**Key classes:**
- `ConvoAnalyzer` - Main engine: `analyze_reply()`, `extract_dna()`, `get_best_hook()`, `score_reply_draft()`, `study_reply()`
- `ConversationDNA` - Extracted pattern: hook_type, tone, structure, engagement_score, examples
- `ReplyAnalysis` - Analysis result for a single reply

**State:** `~/.spark/convo_iq/conversation_dna.json`, `~/.spark/convo_iq/reply_log.jsonl`

**Chip:** `chips/social-convo.chip.yaml` - Observers track reply effectiveness, learners correlate style with engagement

---

### 3. Pulse (`lib/engagement_tracker.py`)

**What it does:** Tracks how tweets perform over time. Predicts engagement, detects surprises.

**Core ideas:**
- **Register and track**: Every posted tweet gets registered with a baseline prediction
- **Temporal snapshots**: Checks engagement at 1h, 6h, and 24h intervals
- **Prediction vs actual**: Compares predicted likes/replies/retweets against actual
- **Surprise detection**: Flags viral moments (actual > 2x predicted) and flops (actual < 0.3x predicted)
- **Accuracy tracking**: Measures how good our predictions are getting over time

**Key classes:**
- `EngagementTracker` - Main engine: `register_tweet()`, `predict_engagement()`, `take_snapshot()`, `detect_surprise()`
- `TrackedTweet` - Tweet with snapshots array and prediction
- `EngagementPrediction` - Predicted likes/replies/retweets with confidence
- `EngagementSurpriseDetector` - PatternDetector that emits `ENGAGEMENT_SURPRISE` patterns

**State:** `~/.spark/engagement_pulse/tracked_tweets.json`

**Chip:** `chips/engagement-pulse.chip.yaml` - Learns engagement prediction from topic+style+timing

**Integration:** Bridge cycle polls pending snapshots every cycle via `_poll_engagement_pulse()`

---

### 4. NicheNet (`lib/niche_mapper.py`)

**What it does:** Maps the social graph around Spark's niche. Knows who matters, who's warming up, where the action is.

**Core ideas:**
- **Account discovery**: Tracks up to 500 accounts in the niche with relevance scoring
- **Relationship tracking**: Every interaction updates warmth (delegated to XVoice state machine)
- **Hub identification**: Detects conversation hubs (topic clusters, key threads, influential accounts)
- **Engagement opportunities**: Generates strategic opportunities with urgency (1-5), expiry, suggested tone
- **Network stats**: Reciprocity rate, warmth distribution, top topics, interaction counts

**Key classes:**
- `NicheMapper` - Main engine: `discover_account()`, `update_relationship()`, `identify_hub()`, `generate_opportunity()`
- `TrackedAccount` - Handle, topics, relevance, warmth, interaction counts
- `ConversationHub` - Hub type (topic/account/thread), engagement level, key accounts
- `EngagementOpportunity` - Target, reason, urgency, suggested tone, expiry

**State:** `~/.spark/niche_intel/` (tracked_accounts.json, hubs.json, opportunities.json)

**Chip:** `chips/niche-intel.chip.yaml` - Learns which interaction types warm up relationships

---

## How They Integrate Into Spark

### Advisor Sources (lib/advisor.py)

The advisor now has 10 sources that provide pre-tool advice. Three are from the X Intelligence Suite:

| Source | Boost | What it provides |
|--------|-------|-----------------|
| `convo` | 1.2x | DNA patterns and hook recommendations for X reply tools |
| `engagement` | 1.15x | Prediction accuracy stats and tracked tweet warnings |
| `niche` | 1.1x | Active opportunities and relationship context for mentioned users |

### Bridge Cycle (lib/bridge_cycle.py)

Engagement Pulse hooks into the bridge cycle to poll pending snapshots. Every cycle:
1. Gets list of tweets pending their next snapshot
2. Cleans up tweets older than 7 days
3. Reports stats in cycle output

### Pattern Detection (lib/pattern_detection/)

New pattern type: `ENGAGEMENT_SURPRISE` - emitted when a tweet dramatically over- or under-performs its prediction. Fed into the cognitive learner as `REASONING` category insights.

### Daily Trend Research (scripts/daily_trend_research.py)

Two new functions plug into the daily research loop:
- `study_reply_patterns()` - Feeds high-engagement replies through ConvoIQ analyzer
- `scan_niche_accounts()` - Discovers accounts from trend research for NicheNet tracking

---

## Tests

```
pytest tests/test_x_voice.py          # 32 tests - XVoice + XHumanizer
pytest tests/test_convo_iq.py         # 37 tests - ConvoIQ + events
pytest tests/test_engagement_pulse.py # 33 tests - Pulse + surprise detector
pytest tests/test_niche_net.py        # 30 tests - NicheNet + dataclasses
```

Run all: `pytest tests/test_x_voice.py tests/test_convo_iq.py tests/test_engagement_pulse.py tests/test_niche_net.py -v`

**132 tests, all passing.**

---

## File Manifest

### Created (16 files)

| File | Module | Lines |
|------|--------|-------|
| `lib/x_voice.py` | X Voice | 530 |
| `lib/x_humanizer.py` | X Voice | 243 |
| `lib/x_voice_config.json` | X Voice | 87 |
| `tests/test_x_voice.py` | X Voice | 358 |
| `lib/convo_analyzer.py` | ConvoIQ | 597 |
| `lib/convo_events.py` | ConvoIQ | 268 |
| `chips/social-convo.chip.yaml` | ConvoIQ | 380 |
| `tests/test_convo_iq.py` | ConvoIQ | 432 |
| `lib/engagement_tracker.py` | Pulse | 466 |
| `lib/pattern_detection/engagement_surprise.py` | Pulse | 129 |
| `chips/engagement-pulse.chip.yaml` | Pulse | 279 |
| `tests/test_engagement_pulse.py` | Pulse | 416 |
| `lib/niche_mapper.py` | NicheNet | 493 |
| `chips/niche-intel.chip.yaml` | NicheNet | 298 |
| `tests/test_niche_net.py` | NicheNet | 383 |

### Modified (8 files)

| File | Change |
|------|--------|
| `lib/spark_voice.py` | Added `get_personality_snippet(topic)` |
| `lib/resonance.py` | Added `calculate_user_resonance()` |
| `lib/advisor.py` | 3 new advice sources + `_SOURCE_BOOST` entries |
| `lib/bridge_cycle.py` | Added `_poll_engagement_pulse()` step |
| `lib/pattern_detection/base.py` | Added `ENGAGEMENT_SURPRISE` to PatternType enum |
| `lib/pattern_detection/__init__.py` | Export EngagementSurpriseDetector |
| `lib/pattern_detection/aggregator.py` | Register new detector + category mapping |
| `scripts/daily_trend_research.py` | Reply study + niche scanning functions |

---

## Warmth State Machine (Shared by XVoice + NicheNet)

```
cold ──[reply/like]──> cool ──[reply+mention]──> warm ──[multi-turn]──> hot ──[collab]──> ally
```

Every interaction type maps to a warmth event:
- `reply` -> `we_reply`
- `reply_received` -> `reply_received`
- `like` -> `mutual_like`
- `mention` -> `they_mention_us`
- `multi_turn` -> `multi_turn_convo`
- `share` -> `they_share_our_content`
- `collab` -> `collaboration`

Warmth affects tone selection (warmer = more casual), engagement priority, and opportunity urgency.
