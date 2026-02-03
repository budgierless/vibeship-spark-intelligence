# CLAUDE

## Core Vision Documents (MUST READ)

These documents define the evolution from primitive telemetry to superintelligent cognition:

1. **CORE.md** - Master vision + 8-phase roadmap (Instrumentation → Superintelligence)
2. **CORE_GAPS.md** - Gap map: what exists, what transforms, what's new, what to clean
3. **CORE_GAPS_PLAN.md** - How to fill each gap (workflows, architecture, code targets)
4. **CORE_IMPLEMENTATION_PLAN.md** - Buildable execution plan with sequencing

### 🚀 New Project Activation

**[SPARK_ACTIVATION_PROMPT.md](./SPARK_ACTIVATION_PROMPT.md)** - Copy-paste prompt for new projects

Use this when starting any new project to properly activate:
- Spark Intelligence (learning layer)
- EIDOS (enforcement layer)
- Chips (domain-specific knowledge)
- Proper learning protocols

### 📋 Pattern → EIDOS Integration ✅ IMPLEMENTED

**[PATTERN_TO_EIDOS_PLAN.md](./PATTERN_TO_EIDOS_PLAN.md)** - Connect pattern detection to EIDOS

**Status:** Implemented 2026-02-02

Components:
- **RequestTracker** (`lib/pattern_detection/request_tracker.py`) - Wraps user requests in Step envelopes
- **PatternDistiller** (`lib/pattern_detection/distiller.py`) - Converts patterns to Distillations
- **MemoryGate** (`lib/pattern_detection/memory_gate.py`) - Scores items before persistence
- **StructuralRetriever** (`lib/eidos/retriever.py`) - Retrieves by structure, not text

### 🔧 Tuneable Parameters

**[TUNEABLES.md](./TUNEABLES.md)** - All configurable thresholds and weights

Key tuneables to test:
- `memory_gate.threshold` = 0.5 (persistence threshold)
- `distiller.min_occurrences` = 3 (pattern frequency)
- `distiller.min_confidence` = 0.6 (success rate threshold)
- `aggregator.DISTILLATION_INTERVAL` = 20 (events between distillation)

### 🎯 Meta-Ralph: Quality Gate Methodology

**[META_RALPH.md](./META_RALPH.md)** - The iterative improvement system for Spark's learning quality

**Core Philosophy:** "Evolve, don't disable. Roast until it's good."

**The Test:** Would a human find this useful to know next time? If yes → Quality. If no → Primitive.

#### Scoring Dimensions (0-2 each, total 0-10)

| Dimension | What It Measures |
|-----------|------------------|
| **Actionability** | Can you act on this insight? |
| **Novelty** | Is this new information? |
| **Reasoning** | Does it explain "why"? |
| **Specificity** | Is it context-specific? |
| **Outcome Linked** | Is there validated evidence? |

#### Verdicts

| Score | Verdict | Action |
|-------|---------|--------|
| >= 4 | QUALITY | Store in memory |
| 2-3 | NEEDS_WORK | Hold for refinement |
| < 2 | PRIMITIVE | Reject |

#### Iteration Methodology

1. **Measure** - Run `test_cognitive_capture.py baseline` to save current metrics
2. **Analyze** - Check what's passing vs blocked, verify quality
3. **Tune** - Adjust thresholds or detection patterns
4. **Test** - Run `test_cognitive_capture.py test` to verify filter accuracy
5. **Compare** - Run `test_cognitive_capture.py compare` to measure improvement
6. **Validate** - Manually verify passed items are genuinely useful
7. **Document** - Update META_RALPH.md changelog

#### Test Suite Commands

```bash
# Save baseline before tuning
python tests/test_cognitive_capture.py baseline

# After tuning, compare to baseline
python tests/test_cognitive_capture.py compare

# Test filter accuracy (cognitive vs operational)
python tests/test_cognitive_capture.py test

# Run deep analysis
python tests/test_cognitive_capture.py deep

# Run Meta-Ralph unit tests
python tests/test_meta_ralph.py
```

#### Key Learnings

- Don't chase pass rate - chase quality of passed items
- "use/using" is too broad for decision detection (use "decided/chose/switched to")
- Importance scorer + pattern matching = better than either alone
- Blocked items scoring 1.5+ below threshold are genuinely low-value
- Filter accuracy should be 90%+ before trusting pass rate metrics
- Quality items must be STORED, not just logged (critical bug fixed 2026-02-03)
- Auto-refinement must RE-SCORE the refined version to change verdict
- Outcome tracking requires both retrieval tracking AND outcome reporting

#### Session History

**Session 2 (2026-02-03): 10 Improvements Initiative**

Completed 5 critical fixes:

| Fix | Problem | Solution | Commit |
|-----|---------|----------|--------|
| Persistence | Quality items logged but not stored | Added `cognitive.add_insight()` call | 546c965 |
| Auto-refinement | Refined versions not re-scored | Re-score refined, use if QUALITY | db56747 |
| Outcome tracking | track_retrieval/track_outcome never called | Integrated with Advisor | ea43727 |
| Promotion speed | Threshold 0.7/3 too strict | Lowered to 0.65/2 | 2b830c3 |
| Pattern aggregator | 0 events reaching pattern detection | Added aggregator call in observe.py | 8b3993d |

**Session 1 (2026-02-03): Meta-Ralph Calibration**

Tuned Meta-Ralph thresholds and detection patterns:
- quality_threshold: 7 → 5 → 4
- Filter accuracy: 70% → 100%
- Pass rate: 2.8% → 39.4%

See META_RALPH.md for full changelog.

### 📊 MONITORING: Distillation Quality (ACTIVE WATCHER)

**CRITICAL:** Monitor distillation quality in real sessions.

#### Quick Checks (Run Periodically)

```bash
# Check EIDOS store stats
python -c "from lib.eidos import get_store; import json; print(json.dumps(get_store().get_stats(), indent=2))"

# Check memory gate pass rate
python -c "from lib.pattern_detection import get_memory_gate; print(get_memory_gate().get_stats())"

# Check aggregator + distillation stats
python -c "from lib.pattern_detection import get_aggregator; import json; print(json.dumps(get_aggregator().get_stats(), indent=2))"

# View recent distillations
python -c "
from lib.eidos import get_store
for d in get_store().get_all_distillations(limit=10):
    print(f'[{d.type.value}] {d.statement[:80]}... (conf: {d.confidence:.2f})')
"
```

#### What to Watch For

| Signal | Good | Bad | Action |
|--------|------|-----|--------|
| Distillation count | Growing over sessions | Stagnant | Lower min_occurrences |
| Gate pass rate | 30-70% | <10% or >90% | Adjust threshold |
| Distillation quality | Actionable rules | Generic statements | Improve lesson extraction |
| Statement length | 30-200 chars | Too short/long | Tune synthesis |

#### Session End Checklist

Before ending a session, check:
- [ ] How many new distillations were created?
- [ ] What's the gate pass rate?
- [ ] Are distillation statements actionable?
- [ ] Any unexpected patterns in the data?

### Current Phase: Phase 3 - EIDOS ✅ COMPLETE

**Completed:** 2026-02-02

EIDOS = **E**xplicit **I**ntelligence with **D**urable **O**utcomes & **S**emantics

**The Core Problem (Solved):**
Intelligence wasn't compounding because: thrashing without learning, forgetting to write, not reading retrieved memories, no enforcement of rules.

**The Solution:**
> "Intelligence = compression + reuse + behavior change. Not storage. Not retrieval. **Enforcement.**"

**Full Documentation:** [EIDOS_GUIDE.md](./EIDOS_GUIDE.md)

---

## EIDOS Principles (CRITICAL)

### The Vertical Loop

Every action MUST go through:

```
Action → Prediction → Outcome → Evaluation → Policy Update → Distillation → Mandatory Reuse
```

### Six Layers

| Layer | Purpose |
|-------|---------|
| **0. Evidence** | Ephemeral audit trail (72h-90d retention) |
| **1. Canonical** | SQLite - source of truth |
| **2. Semantic** | Embeddings for retrieval (never authoritative) |
| **3. Control** | Watchers, budgets, phases (enforcement) |
| **4. Reasoning** | LLM, constrained by Control Plane |
| **5. Distillation** | Post-episode rule extraction |

### Guardrails (HARD GATES - Non-negotiable)

| Guardrail | What It Enforces |
|-----------|------------------|
| **Progress Contract** | Every action must advance toward goal |
| **Memory Binding** | Retrieved memories MUST be cited |
| **Outcome Enforcement** | Predictions MUST be compared to outcomes |
| **Loop Watchers** | Same error 2x = diagnostic phase |
| **Phase Control** | Actions restricted by phase |
| **Evidence Before Modification** | 2 failed edits = forced diagnostic |

### Decision Packets (Not Logs)

Every action is a decision packet with:
- **BEFORE**: Intent, decision, alternatives, assumptions, prediction, confidence
- **ACTION**: Tool, parameters
- **AFTER**: Result, evaluation, surprise level, lesson, new confidence

### Memory Gate

Steps must **earn** persistence:

| Signal | Weight |
|--------|--------|
| Impact (unblocked progress) | +0.3 |
| Novelty (new pattern) | +0.2 |
| Surprise (prediction ≠ outcome) | +0.3 |
| Recurrence (3+ times) | +0.2 |
| Irreversible (security/prod) | +0.4 |

**Score > 0.5 = durable memory**

### CLI Commands

```bash
spark eidos              # Overview
spark eidos --stats      # Statistics
spark eidos --metrics    # Compounding rate
spark eidos --episodes   # List episodes
spark eidos --steps      # List decision packets
spark eidos --distillations  # Extracted rules
```

### Quick Checklist

Before action:
- [ ] Prediction made with confidence?
- [ ] Memory retrieved and cited?
- [ ] Phase appropriate for action?

After action:
- [ ] Outcome recorded?
- [ ] Prediction evaluated?
- [ ] Lesson extracted?

---

## Elevated Control Layer (CRITICAL)

**Full Documentation:** [STUCK_STATE_PLAYBOOK.md](./STUCK_STATE_PLAYBOOK.md)

### The Mantra

> **"If progress is unclear, stop acting and change the question."**

### Invariant Rules (Never Break)

1. **No action without falsifiable hypothesis**
2. **Two failures = STOP modifying reality** (only observe)
3. **Progress must be observable** (every step changes something)
4. **Budgets are capped** (25 steps, 12 min, 2 retries per error)
5. **Memory must be consulted** (cite or declare absent)

### Watchers (Automatic Rabbit-Hole Detection)

| Watcher | Trigger | Action |
|---------|---------|--------|
| **Repeat Failure** | Same error 2x | → DIAGNOSE |
| **No New Evidence** | 5 steps without | → DIAGNOSE |
| **Diff Thrash** | Same file 3x | → SIMPLIFY (freeze file) |
| **Confidence Stagnation** | Delta < 0.05 × 3 | → PLAN |
| **Memory Bypass** | No citation | BLOCK |
| **Budget Half No Progress** | >50%, no progress | → SIMPLIFY |

### Escape Protocol

When stuck (watcher triggers 2x or budget > 80%):

1. **FREEZE** - No more edits
2. **SUMMARIZE** - What we know/tried/observed
3. **ISOLATE** - Smallest failing unit
4. **FLIP** - "What must be true for this to be impossible?"
5. **HYPOTHESES** - Generate 3 max
6. **TEST** - Pick 1 discriminating test
7. **ARTIFACT** - Produce learning (rabbit holes pay rent)

### Operating States

```
EXPLORE → PLAN → EXECUTE → VALIDATE → CONSOLIDATE
   ↑                     ↓
   └────── DIAGNOSE ←────┘
            ↓
         SIMPLIFY
            ↓
         ESCALATE/HALT
```

---

## Final Hardening (v1 Complete)

### Truth Ledger (Prevents Hallucinated Learning)

| Status | Meaning | Can Use For |
|--------|---------|-------------|
| **CLAIM** | Unverified | Low-impact only |
| **FACT** | Validated with evidence | All actions |
| **RULE** | Generalized from facts | High-impact actions |

**Rule:** Only FACTS/RULES with strong evidence for high-impact decisions.

### Acceptance Compiler (Definition of Done)

**Rule:** No EXECUTE without acceptance tests.
- Goal → compiled to explicit tests
- Must have critical (must-pass) tests defined
- Stay in EXPLORE/PLAN until validation plan exists

### Policy Patches (Learning → Behavior)

Distillations create patches:
```
"When condition X, force behavior Y"
```

Default patches:
- Two failures → DIAGNOSE + freeze edits
- File touched 3x → block file
- Budget 50% → require validation

### Minimal Mode (Fallback)

When stuck, enter minimal mode:
- ✅ Read, Glob, Grep, tests
- ❌ Edit, Write, refactor

Exit requires: new evidence + new hypothesis

### 8 Watchers

| # | Watcher | Trigger |
|---|---------|---------|
| 1 | Repeat Failure | Same error 2x |
| 2 | No New Evidence | 5 steps without |
| 3 | Diff Thrash | Same file 3x |
| 4 | Confidence Stagnation | Delta < 0.05 × 3 |
| 5 | Memory Bypass | No citation |
| 6 | Budget Half No Progress | >50%, no progress |
| 7 | **Scope Creep** | Plan grows, progress doesn't |
| 8 | **Validation Gap** | >2 steps without validation |

---

### Phase 2 - Importance Scoring ✅ COMPLETE

**Completed:** 2026-02-02

**The Core Problem (Solved):**
Spark was deciding importance at PROMOTION time, not INGESTION time. Critical one-time insights were lost because they didn't repeat.

**What We Built:**
- `lib/importance_scorer.py` - Semantic importance scoring at ingestion
- Integrated into `lib/pattern_detection/aggregator.py`
- CLI command: `spark importance --text "..."` for testing

**How It Works:**
| Tier | Score | Examples |
|------|-------|----------|
| CRITICAL | 0.9+ | "Remember this", corrections, explicit decisions |
| HIGH | 0.7-0.9 | Preferences, principles, reasoned explanations |
| MEDIUM | 0.5-0.7 | Observations, context, weak preferences |
| LOW | 0.3-0.5 | Acknowledgments, trivial statements |
| IGNORE | <0.3 | Tool sequences, metrics, operational noise |

**Key Principle:** Importance != Frequency. Critical insights on first mention get learned immediately.

### Phase 1 - Cognitive Filtering ✅ COMPLETE

**Completed:** 2026-02-02

**What We Did:**
- Removed ALL operational learning from `learner.py` (1,156 → 113 lines)
- Disabled `learning_filter.py` (no longer needed)
- Cleaned 1,196 primitive learnings from `cognitive_insights.json`
- Kept 231 truly cognitive insights

See **CHANGELOG.md** for full details.

---

## Spark Learning Guide (CRITICAL)

**Full Documentation:** [SPARK_LEARNING_GUIDE.md](./SPARK_LEARNING_GUIDE.md)

### The Core Distinction

| Primitive (Operational) | Valuable (Cognitive) |
|------------------------|---------------------|
| "Bash → Edit sequence" | "Health=300 for better game balance" |
| "Tool timeout rate: 41%" | "User prefers iterative small fixes" |
| "File modified: main.js" | "baseY offset fixes ground collision" |
| "Read before Edit pattern" | "Purple carpet = kid-friendly theme" |

**The Test:** Would a human find this useful to know next time?

### Project Onboarding Questions

**Always ask at project start:**

1. **Domain**: "What domain is this?" → Activates relevant chips
2. **Success**: "What does success look like?" → Anchors learning to outcomes
3. **Focus**: "What should I pay attention to?" → Weights observations
4. **Avoid**: "What mistakes should I help avoid?" → Creates guardrails

**Ask when relevant:**

5. **Prior Art**: "Similar to anything you've built before?"
6. **Constraints**: "What constraints am I working within?"
7. **Tech Preferences**: "Any technology preferences?"

### Memory Consolidation Tiers

```
Immediate (Session) → Working (Project) → Long-Term (Permanent)
     ↓                      ↓                    ↓
  High detail          Patterns &           Cross-project
  Expires fast         principles           wisdom
```

**Promotion Rules:**
- Immediate→Working: Referenced 2+ times, tied to outcome, or explicit "remember this"
- Working→Long-term: Consistent across 3+ projects, validated by outcomes

### Chip Integration

When domain detected, chips should:
1. Auto-activate based on triggers
2. Capture domain-specific insights
3. Suggest relevant questions
4. Store structured knowledge

---

## Spark Learnings

*Cognitive insights from `~/.spark/cognitive_insights.json` (231 total)*

<!-- SPARK_LEARNINGS_START -->
<!--
  Phase 1 Complete (2026-02-02): Removed 1,196 primitive learnings
  Only human-useful cognitive insights remain.
-->

### User Understanding (171 insights)
- User prefers Vibeship style - dark theme, monospace fonts, clean grids
- User hates gradients - use solid colors, flat design
- User prefers clean and thorough code - quality over speed
- User works best late night - quiet, no interruptions, flow state
- Main frustration with AI: not remembering context

### Self-Awareness (14 insights)
- I struggle with Bash errors (449 validations)
- I tend to be overconfident about Bash tasks (187v)
- I struggle with Edit errors (46v)
- Blind spot: File permissions before operation

### Wisdom (17 insights)
- Ship fast, iterate faster
- Never fail silently - always surface errors clearly
- Maintainable > clever
- Security is non-negotiable
- Lightweight solutions - avoid bloat

### Context (23 insights)
- Windows Unicode crash - cp1252 can't encode emojis
- Two Spark directories - old vibeship-spark vs new vibeship-spark-intelligence
- Bash vs cmd syntax mismatch on Windows

### Reasoning (6 insights)
- Assumption 'File exists at expected path' often wrong → Use Glob first

<!-- SPARK_LEARNINGS_END -->

---

## Tools & Capabilities

### Playwright (Browser Automation)
When WebFetch fails or content requires JavaScript rendering (e.g., X/Twitter articles, SPAs):

```javascript
// Use Playwright to fetch dynamic content
const { chromium } = require('playwright');
const browser = await chromium.launch({ headless: true });
const page = await browser.newPage();
await page.goto(url, { waitUntil: 'domcontentloaded' });
await page.waitForTimeout(3000); // Wait for JS to render
const content = await page.evaluate(() => document.body.innerText);
await browser.close();
```

**When to use Playwright over WebFetch:**
- X/Twitter articles and threads
- Single Page Applications (SPAs)
- Content behind JavaScript rendering
- Pages that block simple HTTP requests

**Installation:** `npm install playwright && npx playwright install chromium`

---

## Spark Autonomy (24/7 Self-Evolving Builder)

**Full Documentation:** [SPARK_AUTONOMY.md](./SPARK_AUTONOMY.md)

Spark orchestrates the VibeShip ecosystem to build autonomously while you're away:

```
IdeaRalph (Ideation) → Spark (Executor) → Spark (Learner) → feedback loop
```

### Key Components

| Tool | Role |
|------|------|
| **IdeaRalph** | Source of ideas, specs, risk tags |
| **Mind** | Persistent memory, context retrieval |
| **Spawner** | Route tasks to agents/skills |
| **Scanner** | Security scan before shipping |

### Install VibeShip Tools

```bash
npx github:vibeforge1111/vibeship-idearalph install
```

### The Vision

Spark doesn't just learn - it **builds**:
- Queries IdeaRalph for next actionable idea
- Gets agent recommendation from Spawner
- Executes in sandbox using existing orchestration
- Learns from outcome via pattern detection
- Feeds insights back to IdeaRalph

See SPARK_AUTONOMY.md for full implementation details.