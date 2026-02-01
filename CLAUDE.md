# CLAUDE

## Core Vision Documents (MUST READ)

These documents define the evolution from primitive telemetry to superintelligent cognition:

1. **CORE.md** - Master vision + 8-phase roadmap (Instrumentation → Superintelligence)
2. **CORE_GAPS.md** - Gap map: what exists, what transforms, what's new, what to clean
3. **CORE_GAPS_PLAN.md** - How to fill each gap (workflows, architecture, code targets)
4. **CORE_IMPLEMENTATION_PLAN.md** - Buildable execution plan with sequencing

### Current Phase: Phase 2 - Importance Scoring ✅ COMPLETE

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