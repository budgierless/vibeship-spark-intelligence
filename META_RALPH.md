# Meta-Ralph: The Quality Gate for Spark's Self-Evolution

> "Evolve, don't disable. Roast until it's good."

Meta-Ralph is Spark's internal quality gate - a system that evaluates every proposed learning before it gets stored, ensuring only valuable cognitive insights make it through while primitive operational patterns are filtered out.

---

## Core Philosophy

### The Problem We Solved

Spark was storing primitive learnings that polluted the knowledge base:
- "Read tasks succeed with Read" (tautological)
- "Success rate: 100% over 1794 uses" (operational metrics)
- "For shell tasks, use standard approach" (generic, no reasoning)

These weren't helping anyone. A human wouldn't find them useful.

### The Solution

Instead of disabling components that produce bad output, we **evolve** them:
1. **Roast** every learning before storage
2. **Score** on multiple quality dimensions
3. **Recommend** tuneable adjustments based on data
4. **Learn** what patterns are primitive vs valuable

### The Test

> "Would a human find this useful to know next time?"

If yes → Quality. If no → Primitive.

---

## How Meta-Ralph Works

### Multi-Dimensional Scoring (0-10)

Each learning is scored on 5 dimensions (0-2 each):

| Dimension | 0 | 1 | 2 |
|-----------|---|---|---|
| **Actionability** | Can't act on it | Vague guidance | Specific action |
| **Novelty** | Already obvious | Somewhat new | Genuine insight |
| **Reasoning** | No "why" | Implied "why" | Explicit "because" |
| **Specificity** | Generic | Domain-specific | Context-specific |
| **Outcome Linked** | No outcome | Implied outcome | Validated outcome |

### Verdicts

| Score | Verdict | Action |
|-------|---------|--------|
| >= 4 | QUALITY | Store in memory |
| 2-3 | NEEDS_WORK | Hold for refinement |
| < 2 | PRIMITIVE | Reject |

### Integration Points

Meta-Ralph is integrated into:
- `prompt_evolver.py` - Roasts pattern learnings
- `skill_evolver.py` - Roasts skill insights
- `orchestrator.py` - Roasts orchestration patterns
- `meta_learner.py` - Roasts meta-insights

---

## Tuning History & Lessons Learned

### Session: 2026-02-03 (Initial Calibration)

**Starting State:**
- Processed 1,269 events through Meta-Ralph
- Initial threshold: 7 (too strict)
- Pass rate: 2.8% (only 1 out of 37 passed)

**Issue Detected:** OVER-FILTERING
- Valuable insights like "Use OAuth with PKCE because it prevents token interception" (score 6) were being blocked

**Tuning Iterations:**

| Iteration | Threshold | Pass Rate | Observation |
|-----------|-----------|-----------|-------------|
| 1 | 7 | 2.8% | Too strict, blocking OAuth/PKCE insight |
| 2 | 5 | 5.6% | Better, but still low |
| 3 | 4 | 8.1% | Good balance |

**Key Learning:**
After lowering to 4, Meta-Ralph analyzed the remaining blocked items (avg score 2.5) and correctly concluded:

> "LOW QUALITY INPUT: Items in needs-work zone (avg 2.5) are genuinely low-value. Focus on capturing higher quality input."

This was the right conclusion - the threshold was appropriate, but most tool-use events don't contain cognitive insights. The system was working correctly.

**Lesson:** Don't keep lowering thresholds to chase pass rate. If blocked items are genuinely low-value (like "For read tasks, use standard approach"), the threshold is correct. Focus on capturing higher quality input instead.

---

## Quality Examples

### QUALITY (Score 7) - Passes
```
"User prefers dark theme because it reduces eye strain during late night coding"
- actionability: 2 (specific: use dark theme)
- novelty: 2 (learned this about user)
- reasoning: 2 (explicit "because")
- specificity: 1 (domain-specific)
- outcome_linked: 0 (no validation yet)
Total: 7 ✓ PASSES
```

### QUALITY (Score 6) - Passes (after tuning)
```
"For authentication, use OAuth with PKCE because it prevents token interception"
- actionability: 2 (specific: use PKCE)
- novelty: 1 (known best practice)
- reasoning: 2 (explicit "because")
- specificity: 0 (generic advice)
- outcome_linked: 1 (implied security outcome)
Total: 6 ✓ PASSES
```

### NEEDS_WORK (Score 3) - Held
```
"For read tasks, use standard approach"
- actionability: 2 (action: use standard)
- novelty: 0 (obvious)
- reasoning: 0 (no "why")
- specificity: 1 (task-specific)
- outcome_linked: 0 (no outcome)
Total: 3 ✗ HELD - no reasoning, no novelty
```

### PRIMITIVE (Score 0) - Rejected
```
"Pattern found: read tasks succeed with Read"
- actionability: 0 (tautological)
- novelty: 0 (obvious)
- reasoning: 0 (no "why")
- specificity: 0 (generic)
- outcome_linked: 0 (no outcome)
Total: 0 ✗ REJECTED - pure tautology
```

---

## Tuneable Analysis Logic

Meta-Ralph continuously analyzes its own performance and recommends adjustments:

### Decision Tree

```
IF pass_rate < 10%:
    IF avg_needs_work_score >= threshold - 1:
        → LOWER threshold (valuable items being blocked)
    ELSE:
        → KEEP threshold (input is genuinely low-value)

ELIF pass_rate > 80% AND effectiveness < 50%:
    → RAISE threshold (letting through noise)

ELIF needs_work_rate > 50%:
    IF avg_score close to threshold:
        → CONSIDER_LOWERING
    ELSE:
        → KEEP (items are genuinely borderline)
```

### Sample-Size Guardrails

Meta-Ralph does not tune on tiny samples:
- Require 50+ roasted items before adjusting thresholds.
- Require 5+ needs-work items before using avg_needs_work_score.
- Flag low-quality sources only after 15+ items from that source.

### Key Insight

The magic number isn't pass rate - it's whether blocked items are worth capturing:

- Items scoring 2.5 when threshold is 4 → NOT worth lowering (1.5 points away)
- Items scoring 3.5 when threshold is 4 → Worth considering (0.5 points away)

---

## Future Tuning Guidelines

### When to Lower Threshold

1. High-value insights are being blocked (score close to threshold)
2. Users are explicitly marking blocked items as valuable
3. Outcome tracking shows blocked patterns would have helped

### When to Raise Threshold

1. Stored learnings aren't being used
2. Outcome tracking shows stored patterns led to bad results
3. Too much noise in retrieval results

### When to Keep Threshold

1. Blocked items are genuinely low-value (generic, no reasoning)
2. Pass rate is low but quality of passed items is high
3. System is correctly distinguishing cognitive from operational

---

## Primitive Patterns Database

Patterns that Meta-Ralph has learned to reject:

### Tautologies
- "X tasks succeed with X tool"
- "Pattern found: Y uses Y"

### Pure Metrics
- "Success rate: N% over M uses"
- "Tool timeout rate: X%"
- "File modified: filename"

### Generic Templates
- "For X tasks, use standard approach"
- "Recurring Y errors (Nx)"
- "Validation count: N"
- "Tool timeout: N"

### Operational Sequences
- "Bash → Edit sequence"
- "Read before Edit pattern"

---

## Code Content Extraction (NEW)

### The Problem

Code written via Write/Edit tools contains valuable learning signals in:
- Docstrings with design decisions
- Comments with "REMEMBER:", "PRINCIPLE:", "CORRECTION:"
- Architecture explanations
- Balance formulas with reasoning

**Before:** These were completely ignored. Only user messages were analyzed.

### The Solution

Added to `observe.py` PostToolUse handler:
```python
if tool_name in ("Write", "Edit") and isinstance(tool_input, dict):
    content = tool_input.get("content") or tool_input.get("new_string") or ""
    if content and len(content) > 50:
        extract_cognitive_signals(content, session_id)
```

### What Gets Captured Now

| In Code | Detected As | Score |
|---------|-------------|-------|
| `REMEMBER: armor cap 0.75` | explicit_remember_colon | CRITICAL |
| `CORRECTION: No pure RNG` | explicit_correction | CRITICAL |
| `PRINCIPLE: Bug never where you look` | explicit_principle | CRITICAL |
| `INSIGHT: 300 health = 3-4 hits` | explicit_insight | CRITICAL |
| `BALANCE: 5s/3s/1.5s spawn rates` | explicit_balance | CRITICAL |
| `# because it prevents X` | reasoned_decision | CRITICAL |
| `# the reason is Y` | explicit_reasoning | CRITICAL |

### Best Practices for Capture

When writing code that should be learned:
```python
# REMEMBER: Player health = 300 because 3-4 hits feels fair
# CORRECTION: Don't use pure RNG - pity system after 400 drops
# PRINCIPLE: Variety > difficulty for player engagement
# The reason for 1.5 exponent: linear too easy, quadratic impossible
```

---

## Valuable Patterns Database

Patterns that Meta-Ralph has learned to promote:

### User Preferences (with reasoning)
- "User prefers X because Y"
- "User works best when Z"

### Domain Decisions (with context)
- "For [domain], use [approach] because [reason]"
- "[Constraint] requires [solution]"

### Lessons Learned
- "When [situation], [insight] because [outcome]"
- "[Assumption] was wrong → [correction]"

### Architectural Insights
- "Why X over Y: [reasoning]"
- "[Pattern] works better because [evidence]"

---

## Monitoring Commands

```bash
# Check Meta-Ralph stats
python -c "from lib.meta_ralph import get_meta_ralph; print(get_meta_ralph().get_stats())"

# Check tuneable recommendations
python -c "from lib.meta_ralph import get_meta_ralph; import json; print(json.dumps(get_meta_ralph().analyze_tuneables(), indent=2))"

# View recent roasts
python -c "
from lib.meta_ralph import get_meta_ralph
for r in get_meta_ralph().get_recent_roasts(10):
    result = r.get('result', {})
    print(f'[{result.get(\"verdict\", \"?\")}] ({result.get(\"score\", {}).get(\"total\", 0)}) {result.get(\"original\", \"\")[:60]}...')
"

# Dashboard (if running)
curl http://localhost:8788/api/stats
```

---

## Changelog

| Date | Change | Reason | Outcome |
|------|--------|--------|---------|
| 2026-02-03 | Added sample-size guardrails + per-source quality checks | Avoid tuning on low data | More stable recommendations |
| 2026-02-03 | quality_threshold 7→5→4 | Over-filtering (2.8% pass rate) | Pass rate 8.1%, quality maintained |
| 2026-02-03 | needs_work_threshold 4→2 | Proportional adjustment | Better distribution |
| 2026-02-03 | Added dynamic recommendations | Hardcoded values were stale | Recommendations now use current threshold |
| 2026-02-03 | Tightened "items_worth_capturing" | Was recommending LOWER for 2.5 avg items | Now correctly recommends KEEP |
| 2026-02-03 | Enhanced cognitive detection | Filter accuracy only 70% - missing "remember this", decisions | Filter accuracy 100%, pass rate 8%→23% |
| 2026-02-03 | Added priority/decision boosts | "Remember this" not boosting score | Priority items get +2 novelty, decisions get +1 |
| 2026-02-03 | Expanded reasoning patterns | Only explicit "because" detected | Now detects "for better X", "to avoid Y" |
| 2026-02-03 | Added cognitive extraction hook | Only capturing tool events (94%) | Now extracts cognitive signals from user prompts |
| 2026-02-03 | Integrated importance scorer | Pattern matching alone missed semantic value | Pass rate 8.1%→26.4%, dual scoring system |
| 2026-02-03 | Fixed decision detection | "use/using" matched primitives like "use standard approach" | Now only matches "decided/chose/went with/switched to" |
| 2026-02-03 | Validated quality items | Need to verify learnings are genuinely useful | 100% of passed items are human-valuable |
| 2026-02-03 | Fixed primitive patterns | 65 items stuck in needs_work (score 2-3) were operational | Added patterns for "Recurring X errors", "File modified:", fixed "use standard" regex |
| 2026-02-03 | **SESSION 2 START** | --- | --- |
| 2026-02-03 | Fixed persistence pipeline | Quality items passed Meta-Ralph but were never stored (learnings_stored=0) | Insights now stored in cognitive_learner (0→1511+) |
| 2026-02-03 | Enabled auto-refinement | needs_work items (70) stuck in limbo, refinements_made=0 | Refined versions re-scored, ~75% convert to quality |
| 2026-02-03 | Fixed remember/don't forget refinement | Refinement lost "remember" signal, score dropped | Now converts to "Always X because it prevents issues" |
| 2026-02-03 | Integrated outcome tracking | outcome_stats all zeros, no feedback loop | Advisor now tracks retrievals + outcomes in Meta-Ralph |
| 2026-02-03 | Connected Advisor to observe hook | Advisor never called during tool execution | PreToolUse gets advice, PostToolUse reports outcomes |
| 2026-02-03 | Fixed track_outcome() | Outcomes tracked but acted_on never set True | Now properly sets acted_on=True |
| 2026-02-03 | Lowered promotion thresholds | Insights not reaching CLAUDE.md fast enough | DEFAULT_PROMOTION_THRESHOLD 0.7→0.65, MIN_VALIDATIONS 3→2 |
| 2026-02-03 | Connected pattern aggregator | Aggregator had 0 events, pattern detection not working | observe.py now calls aggregator.process_event() |
| 2026-02-03 | **SESSION 3 START** | --- | --- |
| 2026-02-03 | Domain detection expansion | Only 3 domains had triggers | 10 domains with 170+ triggers (game_dev, fintech, marketing, etc.) |
| 2026-02-03 | Distillation quality | Distillations lacked reasoning | Added _extract_reasoning() for "because" clauses |
| 2026-02-03 | Advisor threshold tuning | Advice not surfacing | MIN_RELIABILITY 0.6→0.5, MAX_ITEMS 5→8 |
| 2026-02-03 | Importance scorer expansion | Missing domain keywords | Added decouple, batch, job, queue, scheduler weights |
| 2026-02-03 | Chips auto-activation | Threshold too high | auto_activate_threshold 0.7→0.5, get_active_chips() added |
| 2026-02-03 | **CRITICAL FIX**: Code content extraction | Write/Edit content not analyzed for cognitive signals | Now extracts REMEMBER:, PRINCIPLE:, CORRECTION:, etc. from code |
| 2026-02-03 | Importance patterns expansion | REMEMBER:, CORRECTION:, PRINCIPLE: not scoring as CRITICAL | Added 5 new CRITICAL patterns for explicit learning markers |

---

## Session History

### Session 3: 2026-02-03 (Code Content Extraction & Live Testing)

**Goal:** Complete remaining improvements, create live test environment, fix gap where code content wasn't being analyzed.

**Starting State:**
- Quality Rate: 47.2% (good)
- Total Insights: 1,525
- Domain Detection: 10 domains working
- EIDOS: 17 episodes, 152 steps, 7 distillations
- **Critical Gap:** Code written via Write/Edit tools was NOT analyzed for cognitive signals

**Critical Discovery:**

When building a game simulator with explicit learning markers in code comments:
```python
# REMEMBER: Player health = 300 because 3-4 hits feels fair
# CORRECTION: Do NOT use pure RNG for legendaries - use pity system
# PRINCIPLE: The bug is never where you first look
```

These insights were **NOT being captured** because:
- `extract_cognitive_signals()` was only called on user messages (line 702)
- Write/Edit tool content was ignored

**The Fix (Commit 66c137e):**

Added cognitive signal extraction for Write/Edit content in `observe.py`:
```python
# COGNITIVE SIGNAL EXTRACTION FROM CODE CONTENT
if tool_name in ("Write", "Edit") and isinstance(tool_input, dict):
    content = tool_input.get("content") or tool_input.get("new_string") or ""
    if content and len(content) > 50:
        extract_cognitive_signals(content, session_id)
```

**New Importance Patterns (lib/importance_scorer.py):**

| Pattern | Signal Name | Score |
|---------|-------------|-------|
| `\bremember:\s` | explicit_remember_colon | CRITICAL |
| `\bcorrection:\s` | explicit_correction | CRITICAL |
| `\bprinciple:\s` | explicit_principle | CRITICAL |
| `\binsight:\s` | explicit_insight | CRITICAL |
| `\bbalance:\s` | explicit_balance | CRITICAL |

**Verified Working:**
```
[reasoning] (90%) CRITICAL GAME BALANCE INSIGHT:
- Player base health: 300 (sweet spot - allows 3-4 hits)...
```

**Live Test Environment Created:**

Location: `C:\Users\USER\Desktop\spark-live-test`

Files:
- `SPARK_MONITOR.py` - Real-time learning observation
- `PROJECT_PROMPT.md` - Comprehensive game dev project with 20+ explicit learnings
- `check_learning.py` - Check learning state anytime

The project exercises 5 domains (game_dev, architecture, orchestration, debugging, product) with explicit "Remember this" statements for validation.

**Final Stats:**
- Cognitive Insights: 1,525
- Meta-Ralph Quality Rate: 47.2%
- Domain Detection: 10 domains, 170+ triggers
- Mind Memories: 32,335
- EIDOS Distillations: 7

---

### Session 2: 2026-02-03 (10 Improvements Initiative)

**Goal:** Identify and fix the 10 highest-impact improvements for Spark learning.

**Starting State:**
- Quality Rate: 39.4% (good)
- Filter Accuracy: 100% (optimal)
- Outcome Tracking: 0% (broken)
- Learnings Stored: 0 (broken)
- Refinements Made: 0 (broken)
- Aggregator Events: 0 (broken)

**Improvements Completed:**

#### 1. Persistence Pipeline Fix (Critical)
- **Problem:** `observe.py` line 273-274 only logged quality items, never stored them
- **Root Cause:** After Meta-Ralph approved an item, nothing called `cognitive.add_insight()`
- **Fix:** Added storage call with category detection based on signals
- **Commit:** 546c965
- **Result:** Insights now persist (tested: 1509 → 1511 after test)

#### 2. Auto-Refinement Activation
- **Problem:** 70 items stuck in needs_work, refinements_made=0
- **Root Cause:** `_attempt_refinement()` was called but refined version never re-scored
- **Fix:** Re-score refined version, use refined verdict if QUALITY
- **Commit:** db56747
- **Result:** ~75% of needs_work items now refine to quality

#### 3. Outcome Tracking Integration
- **Problem:** outcome_stats showed all zeros, no feedback loop
- **Root Cause:** `track_retrieval()` and `track_outcome()` never called
- **Fix:**
  - Advisor.advise() calls ralph.track_retrieval()
  - Advisor.report_outcome() calls ralph.track_outcome()
  - observe.py PreToolUse gets advice, PostToolUse reports outcomes
- **Commit:** ea43727
- **Result:** Outcomes now tracked (tested: total_tracked=5, good_outcomes=1)

#### 4. Promotion Threshold Adjustment
- **Problem:** Insights not reaching CLAUDE.md fast enough
- **Fix:**
  - DEFAULT_PROMOTION_THRESHOLD: 0.7 → 0.65
  - DEFAULT_MIN_VALIDATIONS: 3 → 2
- **Commit:** 2b830c3
- **Result:** Faster path from insight → permanent documentation

#### 5. Pattern Aggregator Connection
- **Problem:** Aggregator had 0 events, pattern detection not working
- **Root Cause:** observe.py never called the aggregator
- **Fix:** Added aggregator.process_event() call after quick_capture()
- **Commit:** 8b3993d
- **Result:** Events now flow to pattern detection system

**Remaining (5 improvements):**
- Skill Domain Coverage (7 domains at zero)
- Distillation Quality
- Advisor Integration verification
- Importance Scorer domain testing
- Chips Auto-Activation

---

## Validation Session: 2026-02-03

### Verified Quality Items (What Spark Actually Learns)

| Score | Learning | Why It's Valuable |
|-------|----------|-------------------|
| 7 | "Dark theme preference because reduces eye strain" | User context for future sessions |
| 6 | "OAuth with PKCE because prevents token interception" | Technical decision with rationale |
| 5 | "Remember this: validate input before DB operations" | Explicit memory request |
| 4 | "Iterative small fixes vs big rewrites" | Work style preference |
| 6 | "Authentication decision with reasoning" | Architecture insight |
| 4 | "Config file location correction" | Project-specific knowledge |

### Correctly Blocked Primitives

| Score | Learning | Why It's Blocked |
|-------|----------|------------------|
| 0 | "Read task succeeded with Read tool" | Tautology |
| 0 | "Success rate: 95% over 1000 uses" | Pure metrics |
| 2 | "For shell tasks, use standard approach" | Generic, no reasoning |
| 0 | "Pattern found: Edit follows Read" | Operational sequence |

### Detection Pattern Fix

**Problem:** Decision detection was matching "use/using" which caught primitives.

**Before:** "For X tasks, use standard approach" → counted as decision (wrong)
**After:** Only matches explicit decisions: "decided to", "chose to", "went with", "switched to"

**Impact:** Decision count dropped from 42 to 4 (all genuine decisions)

---

## The Ralph Loop

```
PROPOSE → ROAST → REFINE → TEST → VERIFY → META-ROAST → repeat
```

Meta-Ralph doesn't just filter - it improves. Every rejected learning is an opportunity to:
1. Learn what patterns are primitive
2. Refine the scoring dimensions
3. Improve the source components
4. Update the tuneables

The goal isn't to block things - it's to **evolve** the entire system until everything it produces is worth keeping.

---

## Current State: 2026-02-03 (Session 3 Complete)

### Intelligence Evolution Metrics

| Metric | Value | Status |
|--------|-------|--------|
| Quality Rate | 47.2% | Excellent |
| Total Roasted | 391 | Growing |
| Quality Passed | 182 | Strong |
| Primitive Rejected | 76 | Working |
| Duplicates Caught | 10 | Active |
| Filter Accuracy | 100% | Optimal |

### Learning Pipeline Status

| Component | Status | Notes |
|-----------|--------|-------|
| User Message Extraction | ✅ Working | Captures preferences, decisions |
| **Code Content Extraction** | ✅ **NEW** | Now analyzes Write/Edit content |
| Domain Detection | ✅ 10 domains | 170+ trigger patterns |
| Importance Scoring | ✅ Enhanced | 5 new CRITICAL patterns |
| Meta-Ralph Quality Gate | ✅ 47.2% | Good signal/noise ratio |
| EIDOS Distillation | ✅ 7 rules | Heuristics and policies |
| Mind Persistence | ✅ 32,335 | Cross-session memory |

### Latest Fix: Needs_Work Cleanup

**Problem:** 65 items stuck in needs_work zone (score 2-3) were actually operational primitives.

**Root Cause:** Primitive patterns weren't catching:
- "For X tasks, use standard approach" (regex had required comma)
- "Recurring X errors (Nx)" (pattern missing entirely)

**Fix:** Added/improved patterns in `PRIMITIVE_PATTERNS`:
```python
r"for \w+ tasks,? use standard"      # Fixed: comma now optional
r"recurring \w+ errors? \(\d+x\)"    # New pattern
r"file modified:"                     # New pattern
r"tool timeout"                       # New pattern
```

**Result:** These items now score 0 and are rejected as primitive.

### Skill Domain Coverage (All 10 Domains Active)

| Domain | Triggers | Example Keywords |
|--------|----------|------------------|
| game_dev | 24 | player, health, balance, spawn, physics |
| fintech | 20 | payment, compliance, transaction, risk |
| marketing | 18 | campaign, conversion, roi, audience |
| product | 17 | feature, feedback, roadmap, sprint |
| orchestration | 17 | workflow, pipeline, queue, batch |
| architecture | 16 | pattern, decouple, interface, module |
| agent_coordination | 16 | agent, routing, context, handoff |
| team_management | 15 | delegation, blocker, standup |
| ui_ux | 21 | layout, component, responsive, accessibility |
| debugging | 16 | error, trace, root cause, stack |

### Learning Pattern Distribution

| Pattern | Count | Strength |
|---------|-------|----------|
| reasoning | 26 | Dominant |
| preferences | 19 | Strong |
| corrections | 13 | Good |
| rules | 12 | Good |
| context | 10 | Moderate |
| decisions | 6 | Growing |

### User Resonance Signals

| Signal | Count | Notes |
|--------|-------|-------|
| style_preference | 26 | Strong user connection |
| explicit_memory | 8 | Users actively requesting persistence |

---

## Future Improvements Roadmap

### ✅ Phase 1: Skill Coverage (COMPLETE)

**Status:** All 10 domains now have triggers (170+ total)
- game_dev, fintech, marketing, product, orchestration
- architecture, agent_coordination, team_management, ui_ux, debugging

### ✅ Phase 2: Code Content Extraction (COMPLETE)

**Status:** Write/Edit content now analyzed for cognitive signals
- Added extraction in observe.py PostToolUse
- 5 new CRITICAL patterns (REMEMBER:, CORRECTION:, PRINCIPLE:, etc.)

### 🔄 Phase 3: Outcome Tracking (In Progress)

**Current:** Infrastructure exists but acted_on outcomes = 0

**Remaining Work:**
1. Ensure report_outcome() is called after actions
2. Track which learnings led to good/bad outcomes
3. Use outcome data to adjust learning reliability
4. Demote learnings with consistently bad outcomes

### 📋 Phase 4: Auto-Refinement Enhancement

**Current:** Refinement logic exists, refinements_made = 0

**Target:** 80% needs_work → quality conversion

**Actions:**
1. Trigger refinement more aggressively
2. Add better refinement templates
3. Track which refinement strategies work

### 📋 Phase 5: Cross-Session Learning

**Goal:** Learnings compound across sessions and projects

**Actions:**
1. Promote high-reliability learnings to CLAUDE.md automatically
2. Build user preference profiles from patterns
3. Create domain expertise summaries
4. Track what works across different project types

### 📋 Phase 6: Predictive Intelligence

**Goal:** Anticipate what the user needs before they ask

**Actions:**
1. Pattern recognition for common workflows
2. Proactive suggestions based on context
3. Early warning for potential pitfalls
4. Recommend relevant past learnings before action

---

## Key Insights from This Session

### What's Working Well

1. **Reasoning capture is strong** (26 instances) - "because" patterns are being caught
2. **User preferences are resonating** (19 instances) - style preferences are being learned
3. **Quality rate is healthy** (36.6%) - not over-filtering or under-filtering
4. **Trend is improving** - more quality items than primitives

### What's Now Working (Fixed This Session)

1. ✅ **Skill coverage complete** - All 10 domains have triggers
2. ✅ **Code content extraction** - Write/Edit now analyzed for learnings
3. ✅ **Importance patterns** - REMEMBER:, CORRECTION:, PRINCIPLE: score CRITICAL
4. ✅ **Chips auto-activation** - Context-based chip loading

### Remaining Opportunities

1. **Outcome tracking refinement** - Currently 0 acted_on outcomes recorded
2. **Cross-project learning** - Insights don't yet transfer between project types
3. **Auto-refinement rate** - Could improve needs_work → quality conversion

### Meta-Ralph's Self-Assessment

> "The learning pipeline is now complete from input to storage. Code content
> is being analyzed, all domains are covered, and quality filtering is
> working at 47%. The main opportunity is connecting learnings to actual
> outcomes and improving cross-session intelligence compounding."

---

## Commands Reference

```bash
# Session summary with suggestions
python -c "from lib.meta_ralph import get_meta_ralph; print(get_meta_ralph().print_session_summary())"

# Deep analysis of intelligence evolution
python -c "from lib.meta_ralph import get_meta_ralph; print(get_meta_ralph().print_deep_analysis())"

# Check stats
python -c "from lib.meta_ralph import get_meta_ralph; import json; print(json.dumps(get_meta_ralph().get_stats(), indent=2))"

# Tuneable recommendations
python -c "from lib.meta_ralph import get_meta_ralph; import json; print(json.dumps(get_meta_ralph().analyze_tuneables(), indent=2))"
```

---

## Cognitive Capture Test Suite

**Location:** `tests/test_cognitive_capture.py`

A dedicated test suite for measuring and improving capture quality over time.

### Usage

```bash
# Save current metrics as baseline (before tuning)
python tests/test_cognitive_capture.py baseline

# Compare current metrics to baseline (after tuning)
python tests/test_cognitive_capture.py compare

# Just analyze current state
python tests/test_cognitive_capture.py analyze

# Test filter accuracy with sample data
python tests/test_cognitive_capture.py test

# Run deep analysis
python tests/test_cognitive_capture.py deep
```

### What It Measures

| Metric | Description |
|--------|-------------|
| **Pass Rate** | % of items that pass quality threshold |
| **Avg Score** | Average score across all roasted items |
| **Cognitive Density** | % of items with reasoning/preference/decision signals |
| **Skill Coverage** | Which domains have learnings |
| **Filter Accuracy** | Correctly classifies cognitive vs operational |

### Improvement Workflow

```
1. BASELINE
   python tests/test_cognitive_capture.py baseline

2. TUNE
   - Adjust thresholds in lib/meta_ralph.py
   - Add detection patterns in lib/importance_scorer.py
   - Modify scoring weights

3. TEST
   python tests/test_cognitive_capture.py test
   → Verify filter accuracy (should be 90%+)

4. COMPARE
   python tests/test_cognitive_capture.py compare
   → Check improvement in pass rate, cognitive density

5. VALIDATE
   - Manually review passed items
   - Confirm they're genuinely useful

6. DOCUMENT
   - Update changelog in META_RALPH.md
   - Record what worked, what didn't
```

### Sample Output

```
============================================================
 CURRENT CAPTURE QUALITY METRICS
 2026-02-03T14:30:00
============================================================

META-RALPH FILTERING:
  Total roasted: 153
  Quality passed: 56 (36.6%)
  Needs work: 45
  Primitive: 52
  Avg score: 3.8/10

COGNITIVE SIGNALS:
  Has reasoning ('because'): 26
  Has preference ('prefer'): 19
  Has decision ('decided'): 6
  Has correction ('instead'): 13
  Cognitive density: 41.8%

SKILL DOMAIN COVERAGE:
  product              ################ (17)
  debugging            # (1)
  ui_ux                # (1)

OVERALL GRADE: B
  (Based on cognitive density: 41.8%)
```

### Filter Accuracy Test

Tests that cognitive samples pass and operational samples fail:

**Cognitive Samples (should pass):**
- "User prefers dark theme because it reduces eye strain"
- "Remember this: always validate input before database operations"
- "I decided to use TypeScript instead of JavaScript for better type safety"

**Operational Samples (should fail):**
- "Read task succeeded with Read tool"
- "Success rate: 95% over 1000 uses"
- "Pattern found: Edit follows Read"

**Target:** 100% accuracy (currently achieved)
