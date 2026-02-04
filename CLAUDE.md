# CLAUDE

---

## THE SPARK INTELLIGENCE CONSTITUTION

### GOVERNING DOCUMENT - READ FIRST, FOLLOW ALWAYS

**This Constitution is the PRIMARY rule set for ALL Spark Intelligence work.**

Before making ANY change, fix, improvement, or tuning to Spark:
1. Read this Constitution
2. Follow all 15 rules
3. No exceptions

**Violations of these rules produce hallucinated progress - changes that look good but don't actually improve Spark.**

---

### The 15 Non-Negotiable Rules

These rules govern ALL work on Spark Intelligence. They exist to ensure every improvement is real, grounded in architecture, and produces actual learning - not hallucinated progress.

> **"Perfect scoring with broken pipeline = zero learning"**

---

### CATEGORY A: REALITY GROUNDING (Rules 1-5)

#### Rule 1: Data from Storage, Not Terminal

> **Always retrieve test results from persistent storage - NEVER rely on terminal output.**

Terminal output is ephemeral. The truth lives in:
- `~/.spark/cognitive_insights.json` (cognitive learnings)
- `~/.spark/eidos.db` (EIDOS distillations)
- `~/.mind/lite/memories.db` (Mind memories)

#### Rule 2: Pipeline Health Before Everything

> **Run `python tests/test_pipeline_health.py` FIRST before any tuning or improvement.**

If this fails, STOP. Fix the pipeline before proceeding. Scoring improvements mean nothing if the pipeline isn't running.

#### Rule 3: Anti-Hallucination Verification

> **Every claimed improvement must have storage evidence.**

Never accept:
- "I saw X in terminal" (ephemeral)
- "The code looks correct" (may not be in data path)
- "Scoring improved" (scoring ≠ storage)

Always verify:
```bash
python -c "from pathlib import Path; import json; print(len(json.loads((Path.home()/'.spark'/'cognitive_insights.json').read_text()).get('insights',[])))"
```

#### Rule 4: End-to-End Flow Verification

> **After any change, verify events flow through the complete pipeline.**

```bash
python tests/test_pipeline_health.py flow
```

A change that isn't in the active data path does nothing.

#### Rule 5: Utilization Over Storage

> **Stored learnings that never get used provide zero value.**

Track the full loop: `Learn → Store → Retrieve → Use → Outcome → Validate`

```bash
python tests/test_learning_utilization.py
```

---

### CATEGORY B: ARCHITECTURE AWARENESS (Rules 6-10)

#### Rule 6: Consult the Architecture Before Changing

> **Read Intelligence_Flow.md and Intelligence_Flow_Map.md before ANY improvement.**

These files are the source of truth for how data flows through Spark.

#### Rule 7: Know the Real Data Flow

> **Memorize this flow - it's the backbone of everything:**

```
Sources (observe.py, sparkd.py, adapters/*)
    → Queue (~/.spark/queue/events.jsonl) [+trace_id]
    → bridge_worker.py (runs every 60s)
    → bridge_cycle.run_bridge_cycle
    ├── memory_capture → cognitive_learner → cognitive_insights.json
    ├── pattern_detection (aggregator → distiller → memory_gate) → eidos_store
    ├── chips_router → chips_runtime → chip_insights/
    └── context_sync → output_adapters → CLAUDE.md/AGENTS.md

Advisor Feedback Loop (parallel path):
    observe.py (PreToolUse) → advisor.get_advice() → advice given
    observe.py (PostToolUse) → advisor.report_outcome() → meta_ralph.track_outcome()
    meta_ralph → cognitive_learner (reliability updates)
```

#### Rule 8: Verify Component Connectivity

> **Before modifying a component, verify it's being called.**

Check:
- What calls this component? (trace upstream)
- What does this component call? (trace downstream)
- Is it in the active data path?

Session 2 lesson: `observe.py` wasn't calling `aggregator.process_event()` - pattern detection had 0 events.

#### Rule 9: Bridge Worker is Critical

> **If bridge_worker isn't running, NOTHING gets processed.**

Always check:
```bash
python -c "import json; from pathlib import Path; print(json.loads((Path.home()/'.spark'/'bridge_worker_heartbeat.json').read_text()))"
```

Heartbeat should be < 120 seconds old.

#### Rule 10: Layer-Aware Changes

> **Identify which layer you're modifying before making changes.**

| Layer | Components | Purpose |
|-------|------------|---------|
| Sources | observe.py, sparkd.py, adapters | Event capture |
| Queue | lib/queue.py | Event buffering |
| Bridge | bridge_worker.py, bridge_cycle.py | Processing orchestration |
| Processing | cognitive_learner, pattern_detection, eidos, chips | Learning extraction |
| Storage | cognitive_insights.json, eidos.db, chip_insights/ | Persistence |
| Output | promoter, context_sync, output_adapters | Promotion to docs |

---

### Operator Dashboards (Use Playbook)

Use `DASHBOARD_PLAYBOOK.md` for full setup and usage (start commands, pages, drilldowns, and APIs).

Quick start:
1. `python -m spark.cli up`
2. Or `python dashboard.py` (Spark Lab only)
3. Pulse: `python spark_pulse.py` (port 8765)
4. **Meta-Ralph Quality Analyzer:** `python meta_ralph_dashboard.py` (port 8586)

`spark up` starts Spark Lab + Pulse + Meta-Ralph by default (use `--no-pulse` / `--no-meta-ralph` to skip).

Key pages:
1. `http://localhost:8585/mission` - Mission Control
2. `http://localhost:8585/learning` - Learning Factory
3. `http://localhost:8585/rabbit` - Rabbit Hole Recovery
4. `http://localhost:8585/acceptance` - Acceptance Board
5. `http://localhost:8585/ops` - Ops Overview
6. `http://localhost:8585/dashboards` - Dashboards Index
7. **`http://localhost:8765`** - Spark Pulse (chips + tuneables)
8. **`http://localhost:8586`** - Meta-Ralph Quality Analyzer (advice quality metrics)

---

### CATEGORY C: QUALITY & ITERATION (Rules 11-15)

#### Rule 11: Baseline Before Tuning

> **Always capture baseline metrics FROM STORAGE before making changes.**

```bash
python tests/test_cognitive_capture.py baseline
```

#### Rule 12: Compare Against Baseline with Evidence

> **After changes, compare to baseline with storage evidence.**

```bash
python tests/test_cognitive_capture.py compare
```

Show: Before count → After count, with file paths.

#### Rule 13: Document with Evidence (Sync META_RALPH.md)

> **Every improvement claim must include:**

- Pipeline health check: PASSED
- Storage before: X insights
- Storage after: Y insights
- Delta: +Z insights
- Utilization: N retrievals, M outcomes

> **CRITICAL: Update META_RALPH.md changelog after EVERY session that modifies Spark.**

META_RALPH.md is the living record of all Spark improvements. After any fix, tune, or enhancement:
1. Add entry to Session History section
2. Document what was changed and why
3. Include evidence (metrics, file paths, counts)

This ensures future sessions understand what was done and why.

#### Rule 14: Evolve, Don't Disable

> **Never disable a component that produces bad output. Improve it.**

Meta-Ralph's philosophy: "Roast until it's good."

#### Rule 15: The Human Test

> **Would a human find this useful to know next time?**

If yes → Quality learning. If no → Primitive (reject).

This is the ultimate filter for what Spark should learn.

---

### CATEGORY D: MULTI-DOMAIN EVOLUTION (Rules 16-20)

#### Rule 16: Spark Evolves Across All Domains

> **Spark is not just for coding - it learns across vibe coding, marketing, UI/UX, trends, business, and more.**

Active domain chips in `~/.spark/chip_insights/`:
- `game_dev` - Game balance, physics, feel
- `marketing` - Audience, campaigns, metrics
- `vibecoding` - Flow state, iteration patterns
- `market-intel` - Trends, competitors, opportunities
- `biz-ops` - Operations, processes, decisions
- `spark-core` - Self-improvement learnings

Every session should activate relevant chips and capture domain-specific insights.

#### Rule 17: Data-Grounded Iteration Only

> **ALL metrics, findings, and improvements MUST come from persistent storage.**

```python
# CORRECT: Read from storage
from pathlib import Path
import json
data = json.loads((Path.home() / '.spark' / 'cognitive_insights.json').read_text())

# WRONG: Trust terminal output or in-memory state
print("I saw 100 insights")  # Ephemeral, unverifiable
```

Never claim improvement without storage evidence. Never hallucinate progress.

#### Rule 18: Rolling Window for Active Metrics

> **For rate-based metrics, use rolling windows to avoid historical debt.**

Old records without outcomes dilute current performance. When measuring acted-on rate:
- Prefer last 24h window over all-time
- Document which window is used
- Separate "historical debt" from "current health"

```python
# Good: Rolling window
recent_records = [r for r in records if age(r) < timedelta(hours=24)]
rate = acted_on_recent / len(recent_records)

# Misleading: All-time (includes stale records)
rate = acted_on_total / len(all_records)
```

#### Rule 19: Cross-Domain Learning Synthesis

> **Insights from one domain should inform others when applicable.**

Examples:
- Game balance insights → Product feature prioritization
- Marketing audience patterns → UI/UX decisions
- Vibe coding flow states → Documentation style
- Trend analysis → Feature roadmap

Use chip merger (`lib/chip_merger.py`) to promote cross-domain patterns to cognitive system.

#### Rule 20: Resonance Over Metrics

> **Spark should resonate with user intentions, not just optimize numbers.**

The goal is not perfect metrics. The goal is:
- Useful advice at the right moment
- Learning what actually helps
- Evolving understanding of preferences
- Building genuine intelligence, not gaming scores

Ask: "Does this make Spark more helpful?" not "Does this improve the metric?"

---

### Quick Commands Reference

```bash
# MANDATORY: Pipeline health (run FIRST)
python tests/test_pipeline_health.py

# Quick status
python tests/test_pipeline_health.py quick

# Learning utilization
python tests/test_learning_utilization.py

# Baseline before tuning
python tests/test_cognitive_capture.py baseline

# Compare after tuning
python tests/test_cognitive_capture.py compare
```

```python
# Meta-Ralph quality stats
from lib.meta_ralph import get_meta_ralph
print(get_meta_ralph().get_stats())

# EIDOS distillations
from lib.eidos import get_store
print(get_store().get_stats())

# Pattern aggregator
from lib.pattern_detection import get_aggregator
print(get_aggregator().get_stats())

# Mind stats
import requests
print(requests.get("http://localhost:8080/v1/stats").json())

# Verify storage (not just scoring)
from pathlib import Path
import json
f = Path.home() / '.spark' / 'cognitive_insights.json'
data = json.loads(f.read_text())
print(f'Stored insights: {len(data.get("insights", []))}')
```

---

### Quick Access Commands

```bash
# MANDATORY: Pipeline health check (run FIRST before any tuning)
python tests/test_pipeline_health.py

# Quick status
python tests/test_pipeline_health.py quick
```

```python
# Meta-Ralph quality stats
from lib.meta_ralph import get_meta_ralph
print(get_meta_ralph().get_stats())

# EIDOS distillations
from lib.eidos import get_store
print(get_store().get_stats())

# Pattern aggregator
from lib.pattern_detection import get_aggregator
print(get_aggregator().get_stats())

# Mind stats
import requests
print(requests.get("http://localhost:8080/v1/stats").json())

# Verify storage (not just scoring)
from pathlib import Path
import json
f = Path.home() / '.spark' / 'cognitive_insights.json'
data = json.loads(f.read_text())
print(f'Stored insights: {len(data.get("insights", []))}')
```

### Why This Matters

Terminal output is ephemeral. The intelligence lives in:
- **Spark**: `~/.spark/cognitive_insights.json` (persistent learnings)
- **EIDOS**: SQLite store with episodes, steps, distillations
- **Mind**: `~/.mind/lite/memories.db` (32,335+ memories)

See **META_RALPH.md** for full testing methodology.

---

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
## Spark Bootstrap
Auto-loaded high-confidence learnings from ~/.spark/cognitive_insights.json
Last updated: 2026-02-04T16:05:38

- [user_understanding] ## ðŸš¨ PRIMARY RULES

### Rule 1: Source of Truth for Testing

**CRITICAL:** When testing and iterating on Spark learning quality:

> **Always retrieve test data directly from Mind memory and Spark Intelligence (via MCP tools or Python imports) - NEVER rely on terminal output.**

### Rule 2: Architecture-Grounded Improvements

**CRITICAL:** Before making any improvement or fix:

> **Consult Intelligence_Flow.md and Intelligence_Flow_Map.md to ensure changes align with actual data flow.**

Witho... (100% reliable, 4 validations)
- [self_awareness] I struggle with Bash fails with windows_path -> Fix: Use forward slashes (/) instead of backslas tasks (27% reliable, 1359 validations)
- [self_awareness] I struggle with Bash fails with file_not_found -> Fix: Verify path exists with Read or ls first tasks (25% reliable, 2135 validations)
- [self_awareness] I struggle with Bash fails with syntax_error -> Fix: Check syntax, look for missing quotes or br tasks (24% reliable, 1185 validations)
- [self_awareness] I struggle with Bash fails with command_not_found -> Fix: Check command spelling or install requ tasks (12% reliable, 495 validations)
- [self_awareness] I struggle with Bash fails with windows_encoding -> Fix: Use ASCII characters or set UTF-8 encod tasks (11% reliable, 426 validations)
- [self_awareness] I struggle with Bash fails with connection_error -> Fix: Check if service is running on expected tasks (10% reliable, 421 validations)
- [self_awareness] I struggle with Bash fails with permission_denied -> Fix: Check file permissions or run with ele tasks (10% reliable, 320 validations)
- [self_awareness] I struggle with Bash fails with json_error -> Fix: Verify JSON format is valid (recovered 100%) tasks (10% reliable, 334 validations)
- [self_awareness] I struggle with Bash fails with timeout -> Fix: Reduce scope or increase timeout tasks (24% reliable, 1316 validations)
- [context] **Always verify:** Is bridge_worker running? Is the queue being processed?

### Rule 3: Pipeline Health Before Tuning

**CRITICAL:** Before ANY tuning or iteration session:

> **Run `python tests/test_pipeline_health.py` FIRST. Scoring metrics are meaningless if the pipeline isn't operational.**

Session 2 lesson: Meta-Ralph showed 39.4% quality rate, but `learnings_stored=0`. Perfect scoring, broken pipeline = zero learning.

### Rule 4: Anti-Hallucination

**CRITICAL:** Never claim improvement... (100% reliable, 29 validations)
- [user_understanding] Now, can we actually do this in this way? After we do these upgrades too for the next iteration, can you actually give me a project prompt so that I can run that using Spark and we can see in real-time what is really happening - what is being saved into the memory and what are the gaps? Instead of trying to just do these through these tests, because in real-time, we may be able to achieve even more understanding - not maybe, but even more understanding - about what is working and what is not. If... (99% reliable, 89 validations)

## Project Focus
- Phase: discovery

## Project Questions
- What is the project goal in one sentence?
- How will we know it's complete?
- What could make this fail later?

## Promoted Learnings (Docs)
- User learns by building - figure it out as they go, hands-on *When: Learning style* (100% reliable, 3 validations)
- User prefers Just try it, user will correct if wrong for assumptions *When: When assumptions is relevant* (73% reliable, 8 validations)
- User prefers Try different angles - brute force approaches for unstuck_method *When: When unstuck_method is relevant* (100% reliable, 7 validations)
- User prefers Build something - learn by doing for learning_style *When: When learning_style is relevant* (86% reliable, 6 validations)
- User aversion: when we are using rounded corners for components *When: Chat message: I hate when we are using rounded cor* (100% reliable, 15 validations)
- User wanted: no, I meant...")
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
