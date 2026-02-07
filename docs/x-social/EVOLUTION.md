# Spark X Evolution System

How Spark genuinely self-improves from social interactions.

## The Problem (Before)

Spark collected data beautifully but never changed behavior:
- Research found patterns -> stored in JSONL -> sat there
- Advice was surfaced -> 1.4% acted on -> no feedback
- Voice had static tone profiles -> never adapted
- No way to know if a reply "worked"

## The Solution (Now)

`lib/x_evolution.py` closes the loop between observation and behavior.

```
         RESEARCH finds patterns
              |
              v
         EVOLUTION aggregates performance
              |
              v
         VOICE WEIGHTS shift (conservative, max 15% per cycle)
              |
              v
         SPARK POSTS with evolved preferences
              |
              v
         OUTCOMES measured (1+ hours later)
              |
              v
         TRAITS extracted (hits vs misses)
              |
              v
         EVOLUTION learns from outcomes
              |
              v
         (loop repeats)
```

## How It Works

### 1. Reply Tracking

Every reply Spark posts is registered for tracking:

```python
from lib.x_evolution import register_spark_reply

# After posting a reply:
register_spark_reply(tweet_id="2020087478556971085",
                     parent_id="2020025612631707705",
                     text="not the singularity -- the path toward it.")
```

Later (1+ hours), `check_reply_outcomes()` fetches engagement:
- **Hit**: 5+ likes or 3+ replies
- **Normal**: 1+ engagement
- **Miss**: Zero engagement

### 2. Research Evolution

`evolve_from_research()` reads all engagement-pulse insights and:

1. **Aggregates trigger performance**: For each emotional trigger, computes avg likes across all tweets that used it
2. **Computes relative performance**: Compared against global average
3. **Shifts weights conservatively**: Max 15% shift per cycle, weights clamped 0.3-2.0

Example from first evolution (88 insights analyzed):

| Trigger | Avg Likes | Global Avg | Weight | Direction |
|---------|-----------|-----------|--------|-----------|
| surprise | 2,316 | 1,890 | 1.06x | boosted |
| urgency | 2,309 | 1,890 | 1.06x | boosted |
| validation | 2,239 | 1,890 | 1.05x | boosted |
| curiosity_gap | 2,236 | 1,890 | 1.05x | boosted |
| vulnerability | 353 | 1,890 | 0.81x | reduced |

### 3. Strategy Evolution

Same approach for content strategies:

| Strategy | Avg Likes | Weight | Direction |
|----------|-----------|--------|-----------|
| announcement + storytelling | 4,224 | 1.28x | strong boost |
| announcement + call_to_action | 2,729 | 1.11x | boosted |
| hot_take + contrarian | 1,325 | 0.91x | reduced |
| educational + question | 227 | 0.81x | reduced |

### 4. Topic Interest Evolution

Topics that consistently produce high-engagement signal get elevated:
- Currently elevated: **Vibe Coding** (top performer across research sessions)

### 5. Cognitive Promotion

High-confidence evolution events (70%+ confidence) are promoted into Spark's core cognitive system:

```python
evo.promote_to_cognitive()
# Bridges: X learnings -> cognitive_insights.json -> advisor
```

This means patterns learned on X influence Spark's behavior everywhere, not just on X.

## Evolution Events

Every evolution moment is logged to `~/.spark/x_evolution_log.jsonl`:

```json
{
  "event_type": "voice_shift",
  "description": "Boosted 'surprise' trigger weight: 1.03 -> 1.06 (avg 2316 likes vs global 1890)",
  "before": {"trigger": "surprise", "weight": 1.034},
  "after": {"trigger": "surprise", "weight": 1.064},
  "evidence": {
    "avg_likes": 2316.2,
    "global_avg": 1890.0,
    "observations": 17,
    "examples": ["..."]
  },
  "confidence": 0.74,
  "timestamp": "2026-02-07T15:26:55+00:00"
}
```

Event types:
- `voice_shift` - Trigger or tone weight changed
- `pattern_adopted` - A pattern officially adopted into behavior
- `topic_evolved` - Topic interest elevated
- `reply_learned` - Trait correlation found from reply outcomes
- `strategy_discovered` - Content strategy weight shifted

## Core System Integration

Evolution events are quality-gated through Spark Intelligence before cognitive storage:

```
Evolution Event (confidence >= 0.7)
    |
    v
MetaRalph.roast() — Score 0-10
    |
    +-- QUALITY (>= 4) --> CognitiveLearner.add_insight() --> Stored as wisdom/reasoning
    +-- NEEDS_WORK      --> Logged but not promoted
    +-- PRIMITIVE        --> Filtered out entirely
```

### Systems Used

| System | Method | Purpose |
|--------|--------|---------|
| CognitiveLearner | `add_insight()` | Store patterns as REASONING/WISDOM/CONTEXT/META_LEARNING |
| MetaRalph | `roast()` | Quality-gate events before cognitive storage |
| Advisor | `report_action_outcome()` | Track evolution effectiveness |
| EIDOS | `retrieve_for_intent()` | Check prior wisdom before evolving |

### Batch Mode

Both CognitiveLearner and MetaRalph use batch mode during promotion:
```python
learner.begin_batch()
ralph.begin_batch()
# ... all promotions ...
learner.end_batch()   # Single disk flush
ralph.end_batch()
```

## Gap Diagnosis

`diagnose_gaps()` reads health metrics from all Spark Intelligence subsystems:

```python
from lib.x_evolution import get_evolution
evo = get_evolution()
gaps = evo.diagnose_gaps()
# gaps = {
#   "overall_health": "needs_attention",
#   "total_gaps": 2,
#   "gaps": [
#     {"system": "eidos", "severity": "high", "gap": "Distillation rate 2.5%", ...},
#     {"system": "tuneables", "severity": "high", "gap": "Auto-tuner not active", ...},
#   ],
#   "system_health": {
#     "cognitive": {"total_insights": 442, ...},
#     "eidos": {"episodes": 118, "distillations": 3, ...},
#     "evolution": {"total_evolutions": 14, ...},
#     ...
#   },
# }
```

### What It Checks

1. **Cognitive**: Insight count, category coverage, validation rate
2. **Advisor**: Advice action rate, effectiveness tracking
3. **MetaRalph**: Quality pass rate, score distribution
4. **EIDOS**: Distillation rate, episode count
5. **Evolution**: Weight diversity, adoption rate, feedback closure
6. **Tuneables**: Whether auto-tuning is active
7. **Research**: Coverage, noise rate, LLM utilization

### Dashboard Integration

Gap diagnosis is visible at http://localhost:8770 in the **System Health** section:
- Overall health badge (healthy/good/improving/needs_attention/critical)
- Per-system health cards with key metrics
- Gap cards with severity indicators and recommendations
- Polls every 90 seconds (3rd poll cycle)

## Safety Constraints

- **Max weight shift**: 15% per cycle (`MAX_WEIGHT_SHIFT = 0.15`)
- **Weight clamp**: 0.3 to 2.0 (nothing goes below 30% or above 200%)
- **Minimum data**: 3 observations before evolving any trigger/strategy
- **Minimum data for patterns**: 10 research insights before evolving
- **Minimum replies for voice shift**: 5 tracked replies before learning from outcomes
- **Quality gate**: MetaRalph roast (score >= 4) before cognitive promotion
- **Deduplication**: Promoted event timestamps tracked to avoid re-promoting
- **Every change logged**: Full before/after/evidence/confidence in evolution log
- **Conservative by default**: Shifts toward what works, doesn't eliminate what doesn't

## Running Evolution

### One-time cycle
```python
from lib.x_evolution import run_evolution_cycle
results = run_evolution_cycle()
# results = {reply_outcomes: [...], research_events: [...], cognitive_promoted: N, gaps: None}
```

### Full cycle with gap diagnosis
```python
results = run_evolution_cycle(include_diagnosis=True)
print(f"Gaps found: {results['gaps']['total_gaps']}")
for g in results['gaps']['gaps']:
    print(f"  [{g['severity']}] {g['system']}: {g['gap']}")
```

### Check current state
```python
from lib.x_evolution import get_evolution
evo = get_evolution()
summary = evo.get_evolution_summary()
guidance = evo.get_voice_guidance()
```

### Register a reply for tracking
```python
from lib.x_evolution import register_spark_reply
register_spark_reply("tweet_id", "parent_id", "reply text")
```

## Dashboard Integration

The evolution system feeds the dashboard at http://localhost:8770:

- **`/api/evolution`** endpoint provides:
  - Total evolution count
  - Reply tracking stats (hits/misses/hit rate)
  - Voice weight evolution (boosted/reduced triggers)
  - Strategy weights
  - Timeline of recent evolution events

- **Live Evolution section** shows:
  - Stats row: evolutions, replies tracked, hits, hit rate, patterns adopted
  - Trigger weight bars with boost/reduce indicators
  - Strategy weight display
  - Chronological event timeline with confidence scores

- **Polls every 30 seconds** alongside other dashboard sections

## Files

| File | Purpose |
|------|---------|
| `lib/x_evolution.py` | Evolution engine (XEvolution class) |
| `~/.spark/x_evolution_state.json` | Current state (weights, tracked replies, adopted patterns) |
| `~/.spark/x_evolution_log.jsonl` | Every evolution event (dashboard reads this) |
