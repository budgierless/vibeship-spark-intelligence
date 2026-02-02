# Spark Intelligence Tuneable Parameters

All configurable thresholds, limits, and weights across the system.
Use this to test and optimize learning quality.

---

## 1. Memory Gate (Pattern → EIDOS)

**File:** `lib/pattern_detection/memory_gate.py`

The Memory Gate decides which Steps and Distillations are worth persisting to long-term memory. It prevents noise from polluting the knowledge base by scoring each item against multiple quality signals.

### How It Works

Every Step or Distillation is scored from 0.0 to 1.0+ based on weighted signals. Only items scoring above the `threshold` are persisted.

```
Final Score = Σ(signal_present × signal_weight)
```

### Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `threshold` | **0.5** | **The gate cutoff.** Items scoring below this are discarded. At 0.5, an item needs at least 2-3 positive signals to pass. |
| `WEIGHTS["impact"]` | 0.30 | **Progress signal.** Did this action unblock progress or advance toward the goal? High when a stuck situation was resolved. |
| `WEIGHTS["novelty"]` | 0.20 | **New pattern signal.** Is this something we haven't seen before? Detects first-time tool combinations, new error types, or unique approaches. |
| `WEIGHTS["surprise"]` | 0.30 | **Prediction error signal.** Did the outcome differ from what was predicted? Surprises indicate learning opportunities - the system's model was wrong. |
| `WEIGHTS["recurrence"]` | 0.20 | **Frequency signal.** Has this pattern appeared 3+ times? Recurring patterns are likely stable and worth remembering. |
| `WEIGHTS["irreversible"]` | 0.60 | **Stakes signal.** Is this a high-stakes action (production deploy, security change, data deletion)? Irreversible actions get dominant weight because mistakes are costly. Raised from 0.40. |
| `WEIGHTS["evidence"]` | 0.10 | **Validation signal.** Is there concrete evidence (test pass, user confirmation) supporting this? Evidence-backed items are more trustworthy. |

### Scoring Examples

**High score (passes gate):**
```
Step: "Fixed authentication bug by adding token refresh"
- impact: 0.30 (unblocked login flow)
- surprise: 0.30 (expected different root cause)
- evidence: 0.10 (tests now pass)
Total: 0.70 ✓ PASSES
```

**Low score (rejected):**
```
Step: "Read config file"
- novelty: 0.0 (common action)
- impact: 0.0 (no progress made)
- surprise: 0.0 (expected outcome)
Total: 0.0 ✗ REJECTED
```

### When to Tune

| Scenario | Adjustment |
|----------|------------|
| Too much noise in memory | Raise `threshold` to 0.6-0.7 |
| Missing important learnings | Lower `threshold` to 0.4 |
| Want more emphasis on errors | Raise `surprise` weight |
| Learning too slowly | Lower `recurrence` weight |
| High-stakes project (finance, security) | Weight already at 0.60, raise to 0.7+ if needed |

---

## 2. Pattern Distiller

**File:** `lib/pattern_detection/distiller.py`

The Pattern Distiller analyzes completed Steps to extract reusable rules (Distillations). It looks for patterns in successes, failures, and user behavior to create actionable guidance.

### How It Works

1. Collects completed Steps from the Request Tracker
2. Groups by pattern type (user preferences, tool usage, surprises)
3. Requires minimum evidence before creating a Distillation
4. Passes Distillations through Memory Gate before storage

### Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `min_occurrences` | **2** | **Evidence threshold.** A pattern must appear at least this many times before being distilled into a rule. Lowered from 3 for faster learning. |
| `min_occurrences_critical` | **1** | **Fast-track for CRITICAL tier.** Critical importance items (explicit "remember this", corrections) are learned from a single occurrence. |
| `min_confidence` | **0.6** | **Success rate threshold.** For heuristics (if X then Y), the pattern must have worked at least 60% of the time. Filters out unreliable patterns. |
| `gate_threshold` | **0.5** | **Memory gate threshold** (inherited from Memory Gate). Distillations must score above this to be stored. |

### Distillation Types Created

| Type | What It Captures | Example |
|------|------------------|---------|
| `HEURISTIC` | "When X, do Y" patterns | "When file not found, check path case sensitivity first" |
| `ANTI_PATTERN` | "Don't do X because Y" | "Don't use sed on Windows - syntax differs" |
| `SHARP_EDGE` | Gotchas and pitfalls | "Python venv activation differs between shells" |
| `PLAYBOOK` | Multi-step procedures | "To debug imports: 1. Check PYTHONPATH, 2. Verify __init__.py" |
| `POLICY` | User-defined rules | "Always run tests before committing" |

### When to Tune

| Scenario | Adjustment |
|----------|------------|
| Learning too slowly | Lower `min_occurrences` to 1 |
| Distillations are unreliable | Raise `min_occurrences` to 4-5 |
| Too many weak heuristics | Raise `min_confidence` to 0.7-0.8 |
| Missing edge case patterns | Lower `min_confidence` to 0.5 |
| Want more one-shot learning | Lower `min_occurrences_critical` (already at 1) |

---

## 3. Request Tracker

**File:** `lib/pattern_detection/request_tracker.py`

The Request Tracker wraps every user request in an EIDOS Step envelope, tracking the full lifecycle from intent → action → outcome. This creates the structured data needed for learning.

### How It Works

```
User Message → Step Created (with intent, hypothesis, prediction)
     ↓
Action Taken → Step Updated (with decision, tool used)
     ↓
Outcome Observed → Step Completed (with result, evaluation, lesson)
```

### Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `max_pending` | **50** | **Concurrent request limit.** Maximum unresolved requests being tracked. Prevents memory bloat from abandoned requests. When exceeded, oldest pending requests are dropped. |
| `max_completed` | **200** | **Completed history limit.** How many completed Steps to retain for distillation analysis. Older completed Steps are pruned. |
| `max_age_seconds` | **3600** | **Timeout (1 hour).** Pending requests older than this are auto-closed as "timed_out". Prevents zombie requests from lingering forever. |

### When to Tune

| Scenario | Adjustment |
|----------|------------|
| Long-running sessions with many requests | Raise `max_pending` to 100 |
| Memory-constrained environment | Lower both limits |
| Want more history for distillation | Raise `max_completed` to 500 |
| Requests timing out too quickly | Raise `max_age_seconds` to 7200 (2 hours) |

---

## 4. Pattern Aggregator

**File:** `lib/pattern_detection/aggregator.py`

The Pattern Aggregator coordinates all pattern detectors (correction, sentiment, repetition, semantic, why) and routes detected patterns to the learning system. It's the central hub for pattern detection.

### How It Works

```
Event → All Detectors Run → Patterns Collected → Corroboration Check → Learning Triggered
                                    ↓
                         (Every N events) → Distillation Run
```

### Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `CONFIDENCE_THRESHOLD` | **0.6** | **Learning trigger threshold.** Patterns must have at least 60% confidence to trigger learning. Lowered from 0.7 to let importance scorer do quality filtering. |
| `DEDUPE_TTL_SECONDS` | **600** | **Deduplication window (10 min).** The same pattern won't be processed twice within this window. Prevents spammy patterns from flooding the system. |
| `DISTILLATION_INTERVAL` | **20** | **Batch size for distillation.** After every 20 events processed, the distiller runs to analyze completed Steps. Lower = more frequent distillation. |

### Corroboration Boost

When multiple detectors agree, confidence is boosted:
- Correction + Frustration detected together → +15% confidence
- Repetition + Frustration detected together → +10% confidence

### When to Tune

| Scenario | Adjustment |
|----------|------------|
| Missing subtle patterns | Lower `CONFIDENCE_THRESHOLD` to 0.6 |
| Too many false positives | Raise `CONFIDENCE_THRESHOLD` to 0.8 |
| Same insight appearing repeatedly | Raise `DEDUPE_TTL_SECONDS` to 1800 (30 min) |
| Want faster learning cycles | Lower `DISTILLATION_INTERVAL` to 10 |
| System too slow | Raise `DISTILLATION_INTERVAL` to 50 |

---

## 5. EIDOS Budget (Episode Limits)

**File:** `lib/eidos/models.py` → `Budget` class

The EIDOS Budget enforces hard limits on episodes to prevent rabbit holes. When any limit is exceeded, the episode transitions to DIAGNOSE or HALT phase.

### How It Works

These are **circuit breakers** - when tripped, they force the system to stop and reassess rather than continuing blindly.

### Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `max_steps` | **25** | **Step limit per episode.** After 25 actions without completing the goal, force DIAGNOSE phase. Prevents endless looping. |
| `max_time_seconds` | **720** | **Time limit (12 minutes).** Episodes taking longer than this are force-stopped. Protects against infinite loops and runaway processes. |
| `max_retries_per_error` | **2** | **Error retry limit.** After failing the same way twice, stop retrying and diagnose. Prevents "try harder" loops. |
| `max_file_touches` | **3** | **File modification limit.** Can only modify the same file three times per episode. Fourth touch triggers DIAGNOSE. Raised from 2 to allow legitimate iteration. |
| `no_evidence_limit` | **5** | **Evidence requirement.** After 5 steps without gathering new evidence (file reads, test runs, etc.), force DIAGNOSE. Prevents blind flailing. |

### What Happens When Limits Hit

| Limit Exceeded | Transition | Behavior |
|----------------|------------|----------|
| `max_steps` | → HALT | Episode ends, escalate to user |
| `max_time_seconds` | → HALT | Episode ends, escalate to user |
| `max_retries_per_error` | → DIAGNOSE | Stop modifying, only observe |
| `max_file_touches` | → DIAGNOSE | File frozen, must find another approach |
| `no_evidence_limit` | → DIAGNOSE | Must gather evidence before acting |

### When to Tune

| Scenario | Adjustment |
|----------|------------|
| Complex tasks need more steps | Raise `max_steps` to 40 |
| Want faster failure detection | Lower `max_steps` to 15 |
| Legitimate long-running tasks | Raise `max_time_seconds` to 1800 (30 min) |
| Frequent file thrashing | Lower `max_file_touches` to 1 |
| Tasks require iteration | Raise `max_file_touches` to 3 |

---

## 6. EIDOS Watchers

**File:** `lib/eidos/control_plane.py`

Watchers are real-time monitors that detect specific stuck patterns. When triggered, they force phase transitions to break out of unproductive loops.

### How It Works

Each watcher monitors a specific metric. When the threshold is exceeded, it fires an alert that triggers a phase transition (usually to DIAGNOSE).

### Watchers

| Watcher | Threshold | What It Detects | Response |
|---------|-----------|-----------------|----------|
| **Repeat Error** | **2** | Same error signature appearing twice. | → DIAGNOSE. Stop modifying, investigate root cause. |
| **No New Info** | **5** | Five consecutive steps without gathering new evidence. | → DIAGNOSE. Must read/test before acting. |
| **Diff Thrash** | **4** | Same file modified four times (after max_file_touches=3). | → SIMPLIFY. Freeze file, find alternative. |
| **Confidence Stagnation** | **0.05 × 3** | Confidence delta < 5% for three steps. | → PLAN. Step back, reconsider approach. |
| **Memory Bypass** | **1** | Action taken without citing retrieved memory. | BLOCK. Must acknowledge memory or declare absent. |
| **Budget Half No Progress** | **50%** | Budget >50% consumed with no progress. | → SIMPLIFY. Reduce scope, focus on core. |
| **Scope Creep** | varies | Plan grows but progress doesn't. | → PLAN. Re-scope to original goal. |
| **Validation Gap** | **2** | More than 2 steps without validation. | → VALIDATE. Must test before continuing. |

### When to Tune

| Scenario | Adjustment |
|----------|------------|
| False positives on error detection | Raise repeat error threshold to 3 |
| Missing repeated mistakes | Lower repeat error threshold to 1 |
| Tasks legitimately require file iteration | Raise diff thrash to 4-5 |
| Want stricter evidence requirements | Lower no new info to 3 |

---

## 7. Cognitive Learner (Decay)

**File:** `lib/cognitive_learner.py`

The Cognitive Learner stores insights with time-based decay. Older insights gradually lose reliability, ensuring the system stays current and doesn't over-rely on stale knowledge.

### How It Works

```
Effective Reliability = Base Reliability × 2^(-age_days / half_life)
```

After one half-life period, reliability drops to 50%. After two half-lives, 25%, etc.

### Half-Life by Category

| Category | Half-Life | Rationale |
|----------|-----------|-----------|
| `WISDOM` | **180 days** | Principles and wisdom are timeless, decay slowly. "Ship fast, iterate faster" stays true. |
| `META_LEARNING` | **120 days** | How to learn itself changes slowly. Learning strategies remain valid. |
| `USER_UNDERSTANDING` | **90 days** | User preferences are fairly stable but can evolve. |
| `COMMUNICATION` | **90 days** | Communication style preferences are sticky but not permanent. |
| `SELF_AWARENESS` | **60 days** | Blind spots need regular reassessment. What I struggled with before may not apply now. |
| `REASONING` | **60 days** | Assumptions and reasoning patterns should be questioned regularly. |
| `CREATIVITY` | **60 days** | Novel approaches may become stale as tech evolves. |
| `CONTEXT` | **45 days** | Environment-specific context changes frequently. Project structure, team practices, etc. |

### Pruning Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `max_age_days` | **365** | **Maximum age.** Insights older than 1 year are pruned regardless of reliability. |
| `min_effective` | **0.2** | **Minimum effective reliability.** When decay brings reliability below 20%, the insight is pruned. |

### When to Tune

| Scenario | Adjustment |
|----------|------------|
| Fast-changing project | Lower CONTEXT half-life to 30 days |
| Stable long-term project | Raise half-lives across the board |
| Want insights to last longer | Raise `max_age_days` to 730 (2 years) |
| Memory getting cluttered | Lower `min_effective` to 0.3 |

---

## 8. Structural Retriever

**File:** `lib/eidos/retriever.py`

The Structural Retriever fetches relevant Distillations before actions. Unlike text similarity search, it prioritizes by EIDOS structure (policies > playbooks > sharp edges > heuristics).

### How It Works

```
Intent/Error → Keyword Extraction → Match Against Distillations → Sort by Type Priority → Return Top N
```

### Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `max_results` | **10** | **Result limit.** Maximum Distillations returned per query. More results = more context but also more noise. |
| `min_overlap` | **2** | **Keyword threshold.** Minimum number of keywords that must overlap between query and Distillation. Filters out weak matches. |

### Type Priority Order

1. **POLICY** (highest) - User-defined rules always come first
2. **PLAYBOOK** - Multi-step procedures for known situations
3. **SHARP_EDGE** - Gotchas and pitfalls to avoid
4. **HEURISTIC** - General "if X then Y" patterns
5. **ANTI_PATTERN** (lowest) - What not to do

### When to Tune

| Scenario | Adjustment |
|----------|------------|
| Retrieval returning irrelevant results | Raise `min_overlap` to 3 |
| Missing relevant Distillations | Lower `min_overlap` to 1 |
| Too much context overwhelming decisions | Lower `max_results` to 5 |
| Complex tasks need more guidance | Raise `max_results` to 15-20 |

---

## 9. Importance Scorer (Signal Detection)

**File:** `lib/importance_scorer.py`

The Importance Scorer evaluates incoming text at **ingestion time** (not promotion time) to determine what's worth learning. This ensures critical one-time insights are captured even if they never repeat.

### How It Works

Text is analyzed for signal patterns that indicate importance:
1. Check for CRITICAL signals (explicit requests, corrections)
2. Check for HIGH signals (preferences, principles)
3. Check for MEDIUM signals (observations, context)
4. Check for LOW signals (noise indicators)
5. Apply domain relevance boost
6. Apply first-mention elevation

### Importance Tiers

| Tier | Score Range | Behavior | Examples |
|------|-------------|----------|----------|
| **CRITICAL** | 0.9+ | Learn immediately, bypass normal thresholds | "Remember this", corrections, "never do X" |
| **HIGH** | 0.7-0.9 | Should learn, prioritize | Preferences, principles, reasoned explanations |
| **MEDIUM** | 0.5-0.7 | Consider learning | Observations, context, weak preferences |
| **LOW** | 0.3-0.5 | Store but don't promote | Acknowledgments, trivial statements |
| **IGNORE** | <0.3 | Don't store | Tool sequences, metrics, operational noise |

### Critical Signals (Immediate Learning)

| Pattern | Signal Type | Why It's Critical |
|---------|-------------|-------------------|
| "remember this" | explicit_remember | User explicitly requesting persistence |
| "always do it this way" | explicit_preference | Strong user directive |
| "never do this" | explicit_prohibition | Important constraint |
| "no, I meant..." | correction | User correcting misunderstanding |
| "because this works" | reasoned_decision | Outcome with explanation |

### High Signals

| Pattern | Signal Type |
|---------|-------------|
| "I prefer" | preference |
| "let's go with" | preference |
| "the key is" | principle |
| "the pattern here is" | pattern_recognition |
| "in general" | generalization |

### Low Signals (Noise)

| Pattern | Signal Type |
|---------|-------------|
| "Bash → Edit" | tool_sequence |
| "45% success" | metric |
| "timeout" | operational |
| "okay", "got it" | acknowledgment |

### When to Tune

Add domain-specific patterns to `DOMAIN_WEIGHTS` for your use case. See Section 15 for domain weight configuration.

---

## 10. Context Sync Defaults

**File:** `lib/context_sync.py`

Context Sync synchronizes high-value insights to Mind (persistent memory) for cross-session retrieval.

### Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `DEFAULT_MIN_RELIABILITY` | **0.7** | **Quality threshold.** Only sync insights with 70%+ reliability to Mind. |
| `DEFAULT_MIN_VALIDATIONS` | **3** | **Evidence threshold.** Insights must be validated 3+ times before syncing. |
| `DEFAULT_MAX_ITEMS` | **12** | **Batch limit.** Maximum items to sync per operation. |
| `DEFAULT_MAX_PROMOTED` | **6** | **Promotion limit.** Maximum items to mark as "promoted" per sync. |

### When to Tune

| Scenario | Adjustment |
|----------|------------|
| Mind getting cluttered | Raise thresholds |
| Missing important context | Lower `DEFAULT_MIN_VALIDATIONS` to 2 |
| Want more cross-session memory | Raise `DEFAULT_MAX_ITEMS` to 20 |

---

## 11. Advisor (Action Guidance)

**File:** `lib/advisor.py`

The Advisor queries relevant insights **before** actions are taken, making stored knowledge actionable. It bridges the gap between learning and decision-making.

### How It Works

```
Tool + Context → Query Memory Banks + Cognitive Insights + Mind → Rank by Relevance → Return Advice
```

### Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `MIN_RELIABILITY_FOR_ADVICE` | **0.6** | **Quality filter.** Only include insights with 60%+ reliability in advice. Lower than promotion threshold because advice is just suggestions. |
| `MIN_VALIDATIONS_FOR_STRONG_ADVICE` | **2** | **Strong advice threshold.** Insights validated 2+ times are marked as "strong" advice. |
| `MAX_ADVICE_ITEMS` | **5** | **Advice limit.** Maximum advice items returned per query. More advice = more context but slower decisions. |
| `ADVICE_CACHE_TTL_SECONDS` | **120** | **Cache duration (2 min).** Same query within 2 minutes returns cached advice. Lowered from 5 min for fresher context. |

### Advice Sources

| Source | What It Provides |
|--------|------------------|
| `cognitive` | Insights from cognitive_learner (preferences, self-awareness) |
| `mind` | Memories from Mind persistent storage |
| `bank` | Project/global memory banks |
| `self_awareness` | Cautions about known struggles |
| `surprise` | Warnings from past unexpected failures |
| `skill` | Relevant skill recommendations |

### When to Tune

| Scenario | Adjustment |
|----------|------------|
| Getting too much advice | Lower `MAX_ADVICE_ITEMS` to 3 |
| Missing relevant warnings | Lower `MIN_RELIABILITY_FOR_ADVICE` to 0.5 |
| Advice is stale | Lower `ADVICE_CACHE_TTL_SECONDS` to 60 (already lowered to 120) |
| Performance issues | Raise cache TTL to 600 (10 min) |

---

## 12. Memory Capture

**File:** `lib/memory_capture.py`

Memory Capture scans user messages for statements worth persisting. It uses keyword triggers and heuristics to identify preferences, rules, and decisions.

### How It Works

```
User Message → Score Against Triggers → Above Auto-Save? → Save Automatically
                                     → Above Suggest? → Queue for Review
                                     → Below Suggest? → Ignore
```

### Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `AUTO_SAVE_THRESHOLD` | **0.82** | **Auto-save cutoff.** Statements scoring 82%+ are saved without confirmation. High threshold ensures only clear signals auto-save. |
| `SUGGEST_THRESHOLD` | **0.55** | **Suggestion cutoff.** Statements scoring 55-82% are queued for user review. Below 55% is ignored. |
| `MAX_CAPTURE_CHARS` | **2000** | **Length limit.** Maximum characters to capture. Longer statements are truncated. |

### Hard Triggers (Explicit Signals)

These keywords trigger high scores immediately:

| Trigger Phrase | Score | Why |
|----------------|-------|-----|
| "remember this" | 1.0 | Explicit persistence request |
| "don't forget" | 0.95 | Strong persistence signal |
| "lock this in" | 0.95 | Commitment language |
| "non-negotiable" | 0.95 | Boundary/constraint |
| "hard rule" | 0.95 | Explicit rule definition |
| "hard boundary" | 0.95 | Constraint definition |
| "from now on" | 0.85 | Future-oriented preference |
| "always" | 0.65 | Generalization signal |
| "never" | 0.65 | Prohibition signal |

### Soft Triggers (Implicit Signals)

| Trigger | Score | Interpretation |
|---------|-------|----------------|
| "I prefer" | 0.55 | Preference |
| "I hate" | 0.75 | Strong negative preference |
| "I need" | 0.50 | Requirement |
| "design constraint" | 0.65 | Technical constraint |
| "for this project" | 0.65 | Project-specific context |

### When to Tune

| Scenario | Adjustment |
|----------|------------|
| Too many auto-saves | Raise `AUTO_SAVE_THRESHOLD` to 0.90 |
| Missing important preferences | Lower `AUTO_SAVE_THRESHOLD` to 0.75 |
| Too many suggestions to review | Raise `SUGGEST_THRESHOLD` to 0.65 |
| Long statements getting cut off | Raise `MAX_CAPTURE_CHARS` to 3000 |

---

## 13. Event Queue

**File:** `lib/queue.py`

The Event Queue captures all Spark events (tool calls, user prompts, errors) with < 10ms latency. Background processing handles the heavy lifting.

### How It Works

```
Event → Quick Capture (< 10ms) → Append to JSONL File → Background Processing
                                           ↓
                              Rotate when MAX_EVENTS exceeded
```

### Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `MAX_EVENTS` | **10000** | **Rotation threshold.** When queue exceeds 10,000 events, oldest half is discarded. Balances history retention vs file size. |
| `TAIL_CHUNK_BYTES` | **65536** | **Read chunk size (64KB).** When reading recent events, reads this much at a time. Larger = faster for big files, more memory. |

### Queue Location

```
~/.spark/queue/events.jsonl
```

### When to Tune

| Scenario | Adjustment |
|----------|------------|
| Need more history | Raise `MAX_EVENTS` to 50000 |
| Disk space constrained | Lower `MAX_EVENTS` to 5000 |
| Large events (long outputs) | Raise `TAIL_CHUNK_BYTES` to 131072 (128KB) |
| Memory constrained | Lower `TAIL_CHUNK_BYTES` to 32768 (32KB) |

---

## 14. Promoter (Insight → CLAUDE.md)

**File:** `lib/promoter.py`

The Promoter automatically promotes high-quality insights to project documentation (CLAUDE.md, AGENTS.md, etc.) where they'll be loaded every session.

### How It Works

```
Cognitive Insights → Filter by Reliability/Validations → Filter Operational Noise → Filter Safety → Write to Target File
```

### Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `DEFAULT_PROMOTION_THRESHOLD` | **0.7** | **Reliability requirement.** Insights must have 70%+ reliability to be promoted. |
| `DEFAULT_MIN_VALIDATIONS` | **3** | **Validation requirement.** Insights must be validated 3+ times before promotion. |

### Safety Filters

**Operational patterns blocked** (tool telemetry, not human-useful):
- Tool sequences: `"Bash → Edit"`, `"Read → Write"`
- Usage counts: `"42 calls"`, `"heavy usage"`
- Metrics: `"success rate"`, `"error rate"`

**Safety patterns blocked** (harmful content):
- Deception-related language
- Manipulation-related language
- Harassment-related language

### Promotion Targets

| Target File | Categories | What Goes There |
|-------------|------------|-----------------|
| CLAUDE.md | WISDOM, REASONING, CONTEXT | Project conventions, gotchas, patterns |
| AGENTS.md | META_LEARNING, SELF_AWARENESS | Workflow patterns, blind spots |
| TOOLS.md | CONTEXT | Tool-specific insights |
| SOUL.md | USER_UNDERSTANDING, COMMUNICATION | User preferences, communication style |

### When to Tune

| Scenario | Adjustment |
|----------|------------|
| CLAUDE.md getting cluttered | Raise both thresholds |
| Important insights not promoting | Lower `DEFAULT_MIN_VALIDATIONS` to 2 |
| Want only high-confidence | Raise `DEFAULT_PROMOTION_THRESHOLD` to 0.8 |

---

## 15. Importance Scorer (Weights & Domains)

**File:** `lib/importance_scorer.py`

Extended configuration for domain-specific importance weighting.

### Default Keyword Weights

These keywords boost importance scores across all domains:

```python
DEFAULT_WEIGHTS = {
    "user": 1.3,        # User-related content is important
    "preference": 1.4,  # Explicit preferences highly valued
    "decision": 1.3,    # Decisions should be remembered
    "principle": 1.3,   # Principles guide future actions
    "style": 1.2,       # Style preferences matter
}
```

### Domain-Specific Weights

When a domain is active, these keywords get boosted:

**Game Development (`game_dev`):**
```python
{
    "balance": 1.5,     # Game balance is critical
    "feel": 1.5,        # Game feel is critical
    "gameplay": 1.4,    # Gameplay decisions
    "physics": 1.3,     # Physics tuning
    "collision": 1.2,   # Collision behavior
    "spawn": 1.2,       # Spawn mechanics
    "difficulty": 1.3,  # Difficulty tuning
    "player": 1.3,      # Player experience
}
```

**Finance/Fintech (`fintech`):**
```python
{
    "compliance": 1.5,   # Regulatory requirements
    "security": 1.5,     # Security is paramount
    "transaction": 1.4,  # Transaction handling
    "risk": 1.4,         # Risk management
    "audit": 1.3,        # Audit requirements
    "validation": 1.3,   # Data validation
}
```

**Marketing (`marketing`):**
```python
{
    "audience": 1.5,     # Target audience
    "conversion": 1.5,   # Conversion optimization
    "messaging": 1.4,    # Message crafting
    "channel": 1.3,      # Channel strategy
    "campaign": 1.3,     # Campaign management
    "roi": 1.4,          # ROI considerations
}
```

**Product (`product`):**
```python
{
    "user": 1.5,        # User focus
    "feature": 1.4,     # Feature decisions
    "feedback": 1.4,    # User feedback
    "priority": 1.3,    # Prioritization
    "roadmap": 1.3,     # Roadmap planning
}
```

### Adding New Domains

To add a new domain, add to `DOMAIN_WEIGHTS` dict in `lib/importance_scorer.py`:

```python
DOMAIN_WEIGHTS["healthcare"] = {
    "hipaa": 1.5,
    "patient": 1.5,
    "clinical": 1.4,
    "ehr": 1.3,
}
```

---

## 16. Environment Variables

System-wide configuration via environment variables.

| Variable | Default | Description |
|----------|---------|-------------|
| `SPARK_NO_WATCHDOG` | `false` | **Disable watchers.** Set to `true` to turn off all watcher enforcement. Use for debugging only. |
| `SPARK_OUTCOME_AUTO_LINK` | `true` | **Auto-link outcomes.** Automatically link outcomes to their originating Steps. |
| `SPARK_AGENT_CONTEXT_LIMIT` | `8000` | **Agent context tokens.** Maximum tokens for agent context injection. |
| `SPARK_DEBUG` | `false` | **Debug mode.** Enables verbose logging across all components. |
| `SPARK_MIND_URL` | `localhost:8080` | **Mind API endpoint.** URL for Mind persistent memory service. |

### Usage

```bash
# Disable watchers for debugging
export SPARK_NO_WATCHDOG=true

# Enable debug logging
export SPARK_DEBUG=true

# Connect to remote Mind
export SPARK_MIND_URL=https://mind.example.com:8080
```

---

## Monitoring Commands

```bash
# Check distillation stats
spark eidos --stats

# View recent distillations
spark eidos --distillations

# Check memory gate stats
python -c "from lib.pattern_detection import get_memory_gate; print(get_memory_gate().get_stats())"

# Check aggregator stats
python -c "from lib.pattern_detection import get_aggregator; print(get_aggregator().get_stats())"

# View EIDOS store stats
python -c "from lib.eidos import get_store; print(get_store().get_stats())"

# Check importance scorer stats
python -c "from lib.importance_scorer import get_importance_scorer; print(get_importance_scorer().get_feedback_stats())"

# Check advisor effectiveness
python -c "from lib.advisor import get_advisor; print(get_advisor().get_effectiveness_report())"

# Check promoter status
python -c "from lib.promoter import get_promotion_status; print(get_promotion_status())"

# Check queue stats
python -c "from lib.queue import get_queue_stats; print(get_queue_stats())"
```

---

## Quick Parameter Index

### Learning Quality Pipeline

```
User Input → Memory Capture (0.82 auto-save)
         → Pattern Detection (0.7 confidence)
         → Distillation (3 occurrences, 0.6 success rate)
         → Memory Gate (0.5 threshold)
         → Cognitive Storage
         → Promotion (0.7 reliability, 3 validations)
         → CLAUDE.md
```

### Stuck Detection Pipeline

```
Action → Budget Check (25 steps, 12 min)
     → Watcher Check (repeat error 2x, no evidence 5x)
     → Phase Transition → DIAGNOSE/HALT
```

### Memory Decay Pipeline

```
Insight Created → Daily Decay (category half-life)
              → Effective Reliability Drops
              → Below 0.2? → Pruned
              → Over 365 days? → Pruned
```

---

## Testing Recommendations

### 1. Memory Gate Testing
```python
from lib.pattern_detection import get_memory_gate
gate = get_memory_gate()

# Create test step with known quality
# Verify gate.score_step() returns expected score
# Check gate.get_stats() for pass/reject rates
```

### 2. Distillation Quality Testing
```python
from lib.pattern_detection import get_pattern_distiller
distiller = get_pattern_distiller()

# Process known patterns
# Verify distillation statements make sense
# Check confidence scores match expectations
```

### 3. Watcher Testing
```python
from lib.eidos import get_elevated_control_plane
control = get_elevated_control_plane()

# Simulate stuck scenarios
# Verify watchers trigger at thresholds
# Check phase transitions happen correctly
```

### 4. Importance Scorer Testing
```bash
# Test specific text
spark importance --text "Remember this: always use dark theme"

# Should return CRITICAL tier

spark importance --text "okay got it"

# Should return LOW/IGNORE tier
```

### 5. End-to-End Learning Test
1. Send user message with "remember this" trigger
2. Verify auto-save in cognitive_insights.json
3. Validate 3 times
4. Check promotion to CLAUDE.md
5. Verify retrieval in next session
