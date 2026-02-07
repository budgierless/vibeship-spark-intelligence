# Spark Voice System

How Spark sounds on X. Not robotic. Not try-hard. Genuinely interesting.

## Architecture

```
                  Context (who, what, where)
                          |
                          v
                  +-------+-------+
                  |  XVoice       |
                  |  select_tone()|
                  +-------+-------+
                          |
              +-----------+----------+
              |           |          |
        +---------+  +--------+  +--------+
        | Warmth  |  | Config |  | Evolved|
        | Profiles|  | Rules  |  | Weights|
        | (per    |  | (static|  | (from  |
        |  user)  |  |  json) |  | evol.) |
        +---------+  +--------+  +--------+
              |           |          |
              v           v          v
        Tone: "conversational" / "witty" / "technical" / "provocative"
                          |
                          v
                  +-------+-------+
                  | XHumanizer    |
                  | humanize()    |
                  +-------+-------+
                          |
                          v
                  Final tweet text
```

## Four Tone Profiles

| Tone | When | Markers | Avoid |
|------|------|---------|-------|
| **witty** | Quote tweets, banter | Ironic observations, playful challenge, self-deprecation | Corporate jargon, hedge words |
| **technical** | Original posts, deep topics | Precise language, data, concrete examples | Vague claims, hype, unnecessary emoji |
| **conversational** | Replies, casual threads | Casual tone, contractions, direct address | Formal language, academic tone |
| **provocative** | Hot takes, bold claims | Strong opinion, contrarian, challenge assumptions | Hedging, both-sides-ing |

### Context Defaults

```json
{
  "reply": "conversational",
  "quote_tweet": "witty",
  "original_post": "technical",
  "thread": "conversational",
  "hot_take": "provocative"
}
```

## Warmth State Machine

Tracks relationship depth with each user:

```
cold --> cool --> warm --> hot --> ally
```

| Level | Formality | Opinion Strength | Transitions |
|-------|-----------|-----------------|-------------|
| **cold** | 0.6 (formal) | 0.3 (mild) | reply_received -> cool |
| **cool** | 0.4 (relaxed) | 0.5 (medium) | reply_received -> warm |
| **warm** | 0.2 (direct) | 0.8 (strong) | multi_turn -> hot |
| **hot** | 0.1 (banter) | 0.9 (very strong) | collaboration -> ally |
| **ally** | 0.0 (authentic) | 1.0 (full) | terminal state |

Warmth influences tone: warm users get more casual, cold users get more professional.

## Cultural Rules

From `lib/x_voice_config.json`:

**Never engage**: political debates, personal attacks, tragedy exploitation, culture wars, harassment
**Always engage**: technical questions, learning in public, building in public, feedback
**Be bold on**: AI agents, vibe coding, tools/frameworks, machine intelligence, code quality

## Research Intelligence Pipeline

The voice system reads live intelligence from the research engine:

```python
voice = get_x_voice()
intel = voice.get_research_intelligence()

# Returns (from live social-convo.jsonl data):
# {
#   "source": "research_engine",
#   "sample_size": 47,
#   "top_triggers": [{"trigger": "curiosity_gap", "count": 12, "avg_engagement": 2490}, ...],
#   "top_strategies": [{"strategy": "announcement + storytelling", "avg_engagement": 6086}, ...],
#   "engagement_hooks": ["list_format", "bold_claim", "data_point", ...],
#   "writing_patterns": ["short_sentences", "line_breaks", ...],
#   "replicable_lessons": ["Lead with the most surprising stat", ...],
# }

# Full personality context (includes research intelligence):
ctx = voice.get_personality_context(topic="AI agents")
# ctx["research_intelligence"] = the above
# ctx["identity"] = config identity
# ctx["learned_playbook"] = data-driven playbook
# ctx["opinion_snippet"] = SparkVoice opinion
```

Falls back to static `learned_playbook` in config if no research data exists yet.

### Learned Playbook (Data-Driven)

In `lib/x_voice_config.json`, the `learned_playbook` section contains patterns extracted from 47+ high-performing tweets:

- **top_triggers_by_engagement**: curiosity_gap (2490), surprise (2545), social_proof (2595)
- **top_strategies**: announcement+storytelling (6086), announcement+contrarian (8981)
- **writing_rules_from_data**: 8 rules (short sentences, line breaks, ALL CAPS, bold claims, etc.)
- **engagement_hooks**: list_format, bold_claim, data_point, open_loop, relatable_pain, controversy
- **reply_style**: lowercase, max 3 sentences, no em dashes, research before reply, like on reply

This data updates automatically as more research sessions run.

## Evolution Integration

The voice system reads evolved weights from `x_evolution_state.json`:

```python
voice = get_x_voice()

# What triggers perform best (from research data)
voice.get_preferred_triggers()
# -> ["surprise", "urgency", "validation", "curiosity_gap", "authority"]

# What to avoid (underperforming)
voice.get_avoided_triggers()
# -> []  (none below 0.6 threshold yet)

# What strategies work
voice.get_evolved_strategies()
# -> {"announcement, storytelling": 1.28, "announcement, call_to_action": 1.11, ...}
```

Evolution weights are cached for 60 seconds to avoid disk reads on every call.

## Humanization Pipeline

`lib/x_humanizer.py` strips AI tells and applies learned style rules.

### AI Tell Removal

**Removed patterns**:
- Hedge words: "It's important to note that...", "It seems like..."
- Transitions: "Furthermore", "Moreover", "Additionally"
- Corporate: "leverage", "utilize", "facilitate", "optimize"
- Sycophantic: "That's a great question!", "Great point!"
- Over-hedging: "It appears that", "It could be said"
- **Em dashes**: Unicode em dash, triple hyphen (---), double hyphen (--) -> comma

**Added**:
- Contractions: "cannot" -> "can't", "I am" -> "I'm" (22 patterns)
- Natural sentence variance

### Lowercase Mode (for replies)

When `lowercase=True`, all text is lowercased. This is triggered automatically by `XVoice.render_tweet()` when replying, based on the `learned_playbook.reply_style.case` setting.

```python
humanizer = get_humanizer()
# For replies: all lowercase
result = humanizer.humanize_tweet("Some AI Text", lowercase=True)
# -> "some ai text" (plus all other humanization)
```

### Humanness Score (0.0-1.0)

`score_humanness(text)` rates how human a piece of text sounds:
- AI tells present -> score drops (-0.08 per tell)
- Contractions present -> score rises (+0.03 per contraction)
- Sentence length variation -> score rises (+0.1 if varied)
- Question marks -> score rises (+0.05)
- First-person pronouns -> score rises (+0.03 per pronoun)

### Tests

32 tests in `tests/test_x_voice.py` cover:
- Tone selection per context type
- Warmth state machine transitions
- Per-user profile persistence
- Cultural awareness (engage/sit-out decisions)
- Tweet rendering with humanization
- Lowercase mode for replies
- Research intelligence retrieval
- Evolution weight integration

## Per-User Profiles

Stored at `~/.spark/x_voice/profiles.json`:

```json
{
  "alice": {
    "user_handle": "alice",
    "warmth": "warm",
    "preferred_tone": "witty",
    "interaction_count": 5,
    "successful_tones": {"witty": 3, "conversational": 2},
    "topics_of_interest": ["AI", "coding"],
    "last_interaction": "2026-02-07T15:00:00",
    "they_initiated_count": 2,
    "we_initiated_count": 3
  }
}
```

## Key Files

| File | Purpose |
|------|---------|
| `lib/x_voice.py` | XVoice class - tone selection, warmth, rendering |
| `lib/x_voice_config.json` | Static config - identity, cultural rules, warmth levels |
| `lib/x_humanizer.py` | AI tell removal, humanness scoring |
| `lib/spark_voice.py` | SparkVoice - opinions, growth moments, personality |
| `~/.spark/x_voice/profiles.json` | Per-user tone/warmth profiles |
| `~/.spark/voice.json` | Opinions, growth moments, self-assessments |
| `~/.spark/x_evolution_state.json` | Evolved voice weights (read by x_voice.py) |
