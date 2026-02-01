# Changelog

All notable changes to Spark Intelligence are documented here.

---

## [Phase 2 Complete] - 2026-02-02

### Theme: Importance Scoring Foundation

**Goal**: Score importance at INGESTION time, not PROMOTION time.

### The Core Problem

Spark was deciding what's important **after** learning, not **during** learning. This meant:
- Critical one-time insights were lost (because they didn't repeat)
- Trivial repeated patterns got elevated (because frequency = confidence)
- The system conflated "frequently occurring" with "important to learn"

### The Solution

New `ImportanceScorer` that assesses semantic importance at ingestion:

| Tier | Score | Examples |
|------|-------|----------|
| **CRITICAL** | 0.9+ | "Remember this", corrections, explicit decisions |
| **HIGH** | 0.7-0.9 | Preferences, principles, reasoned explanations |
| **MEDIUM** | 0.5-0.7 | Observations, context, weak preferences |
| **LOW** | 0.3-0.5 | Acknowledgments, trivial statements |
| **IGNORE** | <0.3 | Tool sequences, metrics, operational noise |

### Key Features

1. **First-Mention Elevation**: Critical insights captured immediately, no repetition needed
2. **Domain-Driven Weighting**: "balance" in game_dev gets 1.5x boost
3. **Question-Guided Capture**: Project onboarding questions define what matters
4. **Signal Detection**: Pattern matching for preference, correction, reasoning signals
5. **Semantic Intelligence**: Compare against known-valuable insights using embeddings
6. **Feedback Loop**: Track importance prediction accuracy and learn from mistakes

### Intelligence Layers

```
Layer 1: Rule-based signals (fast, pattern matching)
         ↓
Layer 2: Semantic similarity (embeddings, compare to validated insights)
         ↓
Layer 3: Outcome feedback (learn from prediction errors)
```

### Seven Intelligence Systems

| System | Purpose | Status |
|--------|---------|--------|
| **Importance Scorer** | Score importance at ingestion | ✅ Complete |
| **Contradiction Detector** | Catch conflicting beliefs | ✅ Complete |
| **Curiosity Engine** | Track knowledge gaps, generate questions | ✅ Complete |
| **Hypothesis Tracker** | Make predictions, validate them | ✅ Complete |
| Wisdom Distillation | Abstract principles from specifics | 🔜 Planned |
| Transfer Learning | Apply learnings across domains | 🔜 Planned |
| Deep User Model | Infer motivations from behaviors | 🔜 Planned |

### Files Added

- `lib/importance_scorer.py` - Core importance scoring engine with semantic intelligence
- `lib/contradiction_detector.py` - Detects conflicts between new and existing beliefs
- `lib/curiosity_engine.py` - Tracks knowledge gaps and generates questions
- `lib/hypothesis_tracker.py` - Makes predictions and validates them over time
- `INTELLIGENT_LEARNING_ARCHITECTURE.md` - Full architecture documentation

### Files Modified

- `lib/pattern_detection/aggregator.py` - Integrated importance scoring at trigger_learning
- `spark/cli.py` - Added `spark importance` command for testing

### CLI Testing

```bash
# Test rule-based importance scoring
spark importance --text "Remember this: always use forward slashes"
spark importance --examples  # See example scorings
spark importance --text "I prefer dark mode" --domain game_dev

# Test with semantic intelligence (compares to known-valuable insights)
spark importance --text "User prefers iterative fixes" --semantic

# View prediction accuracy feedback
spark importance --feedback
```

### Philosophy

```
OLD: Learn if it repeats (frequency = importance)
NEW: Learn if it's important (semantic value at ingestion)
```

---

## [Phase 1 Complete] - 2026-02-02

### 🎯 Theme: Cognitive Filtering

**Goal**: Stop operational telemetry from polluting cognitive memory.

### Summary

Removed ALL primitive/operational learning from Spark. The system now only captures and stores truly cognitive insights that a human would find useful.

### What Was Removed

#### Code Changes

| File | Before | After | Change |
|------|--------|-------|--------|
| `learner.py` | 1,156 lines | 113 lines | Gutted all operational tracking |
| `processor.py` | Operational logging | Minimal | Removed tool effectiveness, sequences, signals |
| `learning_filter.py` | 316 lines | 68 lines | Replaced with deprecated stub |
| `pre_action_reflection.py` | Used LearningFilter | Removed dependency | No longer checks graduated patterns |

#### Data Cleanup

| Storage | Before | After | Removed |
|---------|--------|-------|---------|
| `cognitive_insights.json` | 1,427 insights | 231 insights | 1,196 primitive learnings |
| `graduated_patterns.json` | Tool tracking data | Empty `{}` | All graduated patterns |
| Event queue | 8,300+ events | 0 | All pending operational events |

### What Was Removed (Primitive Patterns)

- **Tool sequences** (1,147): "Read → Edit", "Glob → Glob → Glob"
- **Usage signals** (35): "Heavy Bash usage (42 calls)"
- **Tool errors** (6): "Bash fails with timeout"
- **Frustration patterns** (5): "User frustrated after: Bash, Bash"
- **Tool struggles** (1): "Struggling with Bash"
- **Tool signals** (1): "Heavy tool usage indicates..."
- **Risky patterns** (1): "Pattern 'Edit' risky"

### What Was Kept (Cognitive Insights)

| Category | Count | Examples |
|----------|-------|----------|
| **User Understanding** | 171 | "User prefers Vibeship style", "User hates gradients" |
| **Context** | 23 | "Windows Unicode crash issues", "MCP server configuration" |
| **Wisdom** | 17 | "Ship fast, iterate faster", "Never fail silently" |
| **Self Awareness** | 14 | "I struggle with Bash errors", "Overconfident about Edit" |
| **Reasoning** | 6 | "File existence assumptions often wrong" |

### New Philosophy

```
OLD: Capture everything → Filter operationally → Still noisy
NEW: Only capture what a human would find useful
```

### Files Modified

- `vibeship-spark/lib/learner.py` - Gutted operational tracking
- `vibeship-spark/lib/learning_filter.py` - Replaced with stub
- `vibeship-spark/lib/pre_action_reflection.py` - Removed LearningFilter dependency
- `vibeship-spark/processor.py` - Removed operational logging and cognitive extraction
- `~/.spark/cognitive_insights.json` - Cleaned of primitive data
- `~/.spark/graduated_patterns.json` - Cleared

### Scripts Added

- `scripts/clean_primitive_learnings.py` - Utility to clean primitive insights

### Next Steps (Phase 2)

Now that primitive learning is removed, the next phase focuses on:

1. **User Correction Capture** - Detect when user says "no, do it this way"
2. **Domain Decision Detection** - Capture explicit decisions with rationale
3. **Preference Parsing** - Detect "I prefer X over Y" statements
4. **Project Onboarding Questions** - Ask users what to pay attention to

---

## [Pre-Phase 1] - Before 2026-02-02

### Initial State

- Spark captured ALL tool events (success, failure, timing)
- Learning filter tried to identify "interesting" operational patterns
- 90%+ of stored learnings were primitive tool metrics
- Cognitive insights buried under operational noise

### Known Issues

- "TOOL_EFFECTIVENESS: Bash has 93% success rate" stored as learning
- "Sequence Read → Edit works" promoted as wisdom
- "Heavy Bash usage (42 calls)" marked as cognitive insight
- Thousands of duplicated tool sequence patterns

---

## Version History

| Version | Date | Phase | Key Change |
|---------|------|-------|------------|
| 0.3.0 | 2026-02-02 | Phase 2 Complete | Importance scoring at ingestion |
| 0.2.0 | 2026-02-02 | Phase 1 Complete | Removed operational learning |
| 0.1.x | Pre-2026-02 | Phase 0 | Instrumentation and raw capture |
