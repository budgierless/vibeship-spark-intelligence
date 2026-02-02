# Spark Intelligence Activation Prompt

**Copy-paste this to new projects to properly activate Spark, EIDOS, and Chips.**

---

## STEP 1: Verify Spark Status

Before starting work, check Spark is running:
- Spark Dashboard: http://localhost:8585
- Spark Pulse: http://localhost:8765
- Mind API: http://localhost:8080

If not running, start with: `python -m spark.cli up` from vibeship-spark-intelligence

---

## STEP 2: Project Onboarding (ANSWER THESE)

**Domain**: [What domain is this project? e.g., game_dev, marketing, fintech, SaaS, web3]
**Success**: [What does success look like for this project?]
**Focus**: [What should I pay attention to and learn from?]
**Avoid**: [What mistakes should I help avoid?]
**Constraints**: [Any tech/time/scope constraints?]

---

## STEP 3: Activate Relevant Chips

Available chips (activate based on domain):

| Chip | Domain | Use When |
|------|--------|----------|
| `spark-core` | Core | Always active - Spark patterns |
| `vibecoding` | Development | Coding standards and patterns |
| `game_dev` | Gaming | Game development, physics, balance |
| `marketing` | Marketing | Content, campaigns, audience |
| `market-intel` | Research | Market research, competitive analysis |
| `biz-ops` | Operations | Business operations, workflows |
| `moltbook` | Predictions | Prediction markets, betting mechanics |
| `bench_core` | Performance | Benchmarking, optimization |

---

## STEP 4: EIDOS Protocol (ENFORCE THIS)

### The Vertical Loop (Every Action)

```
1. ACTION     → What am I doing?
2. PREDICTION → What do I expect? (confidence 0-1)
3. OUTCOME    → What actually happened?
4. EVALUATION → Did prediction match?
5. LESSON     → What's the reusable insight?
```

### Hard Gates (Never Break)

| # | Rule | Consequence |
|---|------|-------------|
| 1 | No action without falsifiable hypothesis | Must state what would prove you wrong |
| 2 | Two failures = STOP modifying | Only observe/diagnose after 2 fails |
| 3 | Progress must be observable | Every step changes something measurable |
| 4 | Budgets are capped | 25 steps, 12 min, 2 retries per error |
| 5 | Memory must be consulted | Cite retrieved memory or declare absent |

### Watchers (Auto-triggers)

| Watcher | Trigger | Action |
|---------|---------|--------|
| **Repeat Failure** | Same error 2x | → DIAGNOSE |
| **No New Evidence** | 5 steps without | → DIAGNOSE |
| **Diff Thrash** | Same file 3x | → SIMPLIFY (freeze file) |
| **Confidence Stagnation** | Delta < 0.05 × 3 | → PLAN |
| **Memory Bypass** | No citation | BLOCK |
| **Budget Half** | >50%, no progress | → SIMPLIFY |
| **Scope Creep** | Plan grows, progress doesn't | → SIMPLIFY |
| **Validation Gap** | >2 steps without validation | → VALIDATE |

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

### When Stuck (Escape Protocol)

1. **FREEZE** - No more edits
2. **SUMMARIZE** - What we know/tried/observed
3. **ISOLATE** - Smallest failing unit
4. **FLIP** - "What must be true for this to be impossible?"
5. **HYPOTHESES** - Generate 3 max
6. **TEST** - Pick 1 discriminating test
7. **ARTIFACT** - Produce learning (rabbit holes pay rent)

---

## STEP 5: Learning Protocol

### What to Learn (Cognitive - Human-Useful)

✅ Domain decisions ("health=300 for better game balance")
✅ User preferences ("prefers iterative small fixes")
✅ Architecture insights ("why X over Y")
✅ Lessons from mistakes (mistake → fix → insight)
✅ Corrections ("actually, we use X not Y")
✅ Explicit requests ("remember this for next time")

### What NOT to Learn (Primitive - Operational Noise)

❌ Tool sequences (Bash → Edit)
❌ Timing metrics
❌ File modification counts
❌ Error rates
❌ Generic acknowledgments

**The Test**: Would a human find this useful to know next time?

### Importance Scoring (At Ingestion)

| Tier | Score | Signals |
|------|-------|---------|
| CRITICAL | 0.9+ | "Remember this", corrections, explicit decisions |
| HIGH | 0.7-0.9 | Preferences, principles, reasoned explanations |
| MEDIUM | 0.5-0.7 | Observations, context, weak preferences |
| LOW | 0.3-0.5 | Acknowledgments, trivial statements |
| IGNORE | <0.3 | Tool sequences, metrics, operational noise |

---

## STEP 6: Session End Protocol

Before ending any session:

1. **Report what was learned** (not just what was done)
2. **Note any surprises** (prediction ≠ outcome)
3. **Flag insights for promotion** (salience > 0.7)
4. **Update project context** if domain/phase changed
5. **Complete EIDOS episode** if goal achieved or abandoned

---

## User Preferences (From Spark Memory)

These are learned preferences - apply them:

| Preference | Value |
|------------|-------|
| **Code Quality** | Clean, thorough, quality over speed |
| **Design** | Dark theme, monospace fonts, no gradients, solid colors |
| **Communication** | Adaptive - brief when clear, detailed when complex |
| **Workflow** | Action-oriented, try quick fixes before deep analysis |
| **Core Value** | Context memory is critical - always leverage Spark/Mind |
| **Testing** | Always suggest tests, user values full coverage |
| **Explanations** | Show working code first, explain after |

---

## Session Template

Copy this to start a session:

```
## Current Session

**Project**: [PROJECT NAME]
**Domain**: [DOMAIN from Step 2]
**Goal**: [WHAT WE'RE BUILDING/FIXING]
**Phase**: [discovery | planning | execution | validation | consolidation]
**Chips**: [Which chips are relevant]

### Pre-flight Checklist
- [ ] Spark services running?
- [ ] Relevant chips activated?
- [ ] EIDOS vertical loop understood?
- [ ] Previous learnings consulted?

### Context from Previous Sessions
[Any relevant memories or learnings to cite]

---

Ready to begin. What would you like to build?
```

---

## Quick Reference

### CLI Commands

```bash
# Start everything
python -m spark.cli up

# Check status
python -m spark.cli status
python -m spark.cli services

# EIDOS commands
spark eidos              # Overview
spark eidos --stats      # Statistics
spark eidos --metrics    # Compounding rate

# Process queue
spark process

# Check learnings
spark learnings --query "topic"
```

### Dashboards

| Dashboard | URL | Purpose |
|-----------|-----|---------|
| Spark Lab | http://localhost:8585 | Main dashboard, insights, queue |
| Spark Pulse | http://localhost:8765 | Neural visualization + chips rail |
| Mind API | http://localhost:8080/docs | Memory API docs |

---

*Generated from vibeship-spark-intelligence. See EIDOS_GUIDE.md for full documentation.*
