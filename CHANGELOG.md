# Changelog

All notable changes to Spark Intelligence are documented here.

---

## [Phase 3 Complete] - 2026-02-02

### Theme: EIDOS - Self-Evolving Intelligence System

**Goal**: Force learning through decision packets, prediction loops, and mandatory memory binding.

### The Core Problem

Intelligence wasn't compounding because:
1. **Thrashing**: Fix loops and rabbit holes without learning
2. **Forgetting to write**: Stopped storing after initial phase
3. **Not reading**: Retrieval wasn't binding
4. **No enforcement**: LLM decided everything, no guardrails

### The Solution: EIDOS Architecture

**EIDOS** = Explicit Intelligence with Durable Outcomes & Semantics

The system now enforces a **vertical loop**:
```
Action → Prediction → Outcome → Evaluation → Policy Update → Distillation → Mandatory Reuse
```

### The Five Layers

| Layer | Purpose |
|-------|---------|
| **Canonical Memory** | SQLite - source of truth for episodes, steps, distillations, policies |
| **Semantic Index** | Embeddings for retrieval (never as truth) |
| **Control Plane** | Deterministic enforcement - watchers, budgets, phase control |
| **Reasoning Engine** | LLM - constrained by Control Plane |
| **Distillation Engine** | Post-episode rule extraction |

### Core Primitives

| Primitive | Purpose |
|-----------|---------|
| **Episode** | Bounded learning unit with goal, success criteria, budget |
| **Step** | Decision packet - intent, prediction, result, evaluation, lesson |
| **Distillation** | Extracted rules - heuristics, sharp edges, anti-patterns, playbooks |
| **Policy** | Operating constraints - what must be respected |

### Watchers (Hard Gates)

| Watcher | Trigger | Action |
|---------|---------|--------|
| **Repeat Error** | Same error 2x | Diagnostic phase + new hypothesis |
| **No-New-Info** | 5 steps without evidence | Stop; data-gather plan |
| **Diff Thrash** | Same file modified 3x | Freeze file, focus elsewhere |
| **Confidence Stagnation** | Delta < 0.05 for 3 steps | Force alternative or escalate |
| **Memory Bypass** | Action without citing memory | Block action |

### Memory Gate

Not everything becomes durable memory. Steps must earn persistence:

| Signal | Weight |
|--------|--------|
| High impact (unblocked progress) | +0.3 |
| Novelty (new pattern) | +0.2 |
| Surprise (prediction ≠ outcome) | +0.3 |
| Recurrence (3+ times) | +0.2 |
| Irreversible (security, prod) | +0.4 |

**Score > 0.5 → durable memory**

### Files Added

- `lib/eidos/__init__.py` - Package initialization
- `lib/eidos/models.py` - Core data models (Episode, Step, Distillation, Policy)
- `lib/eidos/control_plane.py` - Watchers, budget enforcement, phase control
- `lib/eidos/memory_gate.py` - Importance scoring for step persistence
- `lib/eidos/distillation_engine.py` - Post-episode reflection and rule extraction
- `lib/eidos/store.py` - SQLite persistence layer
- `EIDOS_ARCHITECTURE.md` - Full architecture documentation

### CLI Commands

```bash
# EIDOS overview
spark eidos

# Statistics
spark eidos --stats

# List episodes
spark eidos --episodes

# List distillations (extracted rules)
spark eidos --distillations
spark eidos --distillations --type heuristic

# List policies
spark eidos --policies

# List decision packets
spark eidos --steps
spark eidos --steps --episode <episode_id>
```

### Success Metrics

| Metric | What It Measures | Target |
|--------|------------------|--------|
| **Reuse Rate** | Episodes using prior distillations | >40% |
| **Outcome Improvement** | Time-to-success decrease | -20%/month |
| **Loop Suppression** | Fix-loop depth | <3 retries |
| **Distillation Quality** | Rules useful when reused | >60% |

### The Fundamental Shift

```
OLD: "How do we store more?"
NEW: "How do we force learning?"
```

Intelligence = compression + reuse + behavior change. Not storage. Not retrieval. **Enforcement.**

---

## [Phase 3.1 Complete] - 2026-02-02

### Theme: EIDOS Architecture Additions

Implemented the full EIDOS specification from EIDOS_ARCHITECTURE_ADDITIONS.md.

### New Components

| Component | File | Purpose |
|-----------|------|---------|
| **Guardrails** | `lib/eidos/guardrails.py` | Evidence Before Modification guard, Phase violation checks |
| **Evidence Store** | `lib/eidos/evidence_store.py` | Ephemeral audit trail with retention policies |
| **Escalation** | `lib/eidos/escalation.py` | Structured escalation output with attempts, evidence, options |
| **Validation** | `lib/eidos/validation.py` | Validation methods and deferred validation tracking |
| **Metrics** | `lib/eidos/metrics.py` | Compounding rate and intelligence metrics |
| **Migration** | `lib/eidos/migration.py` | Data migration from old Spark to EIDOS |

### Guardrail 6: Evidence Before Modification

After 2 failed edit attempts, agent is FORBIDDEN to edit until:
- Reproducing reliably
- Narrowing scope
- Identifying discriminating signal
- Creating minimal reproduction

### Layer 0: Ephemeral Evidence Store

Tool logs stored separately with retention policies:
- Tool output: 72 hours
- Test/build results: 7 days
- Deploy artifacts: 30 days
- Security events: 90 days
- User-flagged: Permanent

### Escalation Structure

Complete escalation reports with:
- Summary (goal, progress, blocker)
- Attempts history
- Evidence gathered
- Current hypothesis
- Minimal reproduction
- Request type (INFO/DECISION/HELP/REVIEW)
- Suggested options

### Validation Methods

Standard codes: `test:passed`, `build:success`, `lint:clean`, `output:expected`, etc.

Deferred validation with max wait times:
- `deferred:needs_deploy` (24h)
- `deferred:needs_data` (48h)
- `deferred:needs_human` (72h)
- `deferred:async_process` (4h)

### Metrics SQL

Compounding Rate query and supporting metrics:
- Reuse Rate: % steps citing memory
- Memory Effectiveness: Win rate with/without memory
- Loop Suppression: Average retries
- Distillation Quality: Rules useful when reused
- Weekly Intelligence Report

### CLI Commands

```bash
# Intelligence metrics
spark eidos --metrics

# Evidence store stats
spark eidos --evidence

# Deferred validations
spark eidos --deferred

# Migration (dry-run first!)
spark eidos --migrate --dry-run
spark eidos --migrate

# Validate migration
spark eidos --validate-migration
```

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
