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

### Operational Sequences
- "Bash → Edit sequence"
- "Read before Edit pattern"

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
