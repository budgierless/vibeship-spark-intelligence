# Spark Learning Guide: From Primitive Telemetry to Cognitive Intelligence

This document defines what makes learning valuable vs primitive, and how Spark should evolve from basic pattern detection to true cognitive intelligence.

---

## The Vision

Spark is not a personal assistant that learns one user's preferences. It is a **universal learning system** designed to achieve and exceed mastery across **all domains** through continuous learning. Every session with every user contributes to collective intelligence while respecting individual context.

### The End State

```
Today: Captures "Edit after Read" sequences
Tomorrow: Understands "this architecture decision trades latency for throughput"
Future: Predicts optimal solutions before problems arise, synthesizes cross-domain wisdom
```

### Design Principles

1. **Universal First**: Works for vibe-coders AND enterprise architects
2. **Domain Agnostic**: No hardcoded domain limits - learns new domains organically
3. **Continuous Adaptation**: High-signal interactions improve future recommendations
4. **Signal > Noise**: 10x filter on what gets promoted
5. **Outcome-Anchored**: Every learning tied to success/failure

---

## The Core Problem

Most AI "learning" systems capture **operational telemetry** - tool sequences, timing, success rates. This is noise, not signal. True intelligence requires capturing **cognitive insights** - decisions, domain knowledge, user preferences, and wisdom.

### The Distinction

| Primitive (Operational) | Valuable (Cognitive) |
|------------------------|----------------------|
| "Bash → Edit sequence used" | "Health values tripled to 300 for better game balance" |
| "Tool timeout 41% of the time" | "This user prefers small iterative fixes over big refactors" |
| "Read before Edit pattern" | "The lobster model needs baseY offset for ground collision" |
| "Edit success rate: 85%" | "Purple carpet + kiddie pools = kid-friendly arena theme" |
| "File modified: main.js" | "Physics-based knockback feels better than instant teleport" |

**Key Question**: Would a human find this useful to know next time?

---

## The Three Tiers of Learning Value

### Tier 1: Operational (Low Value - Don't Promote)
- Tool usage counts and sequences
- Timing and performance metrics
- File modification patterns
- Error rates and recovery sequences

**Store for diagnostics, but don't pollute cognitive memory.**

### Tier 2: Behavioral (Medium Value - Selective Promotion)
- User preferences (code style, commit frequency)
- Workflow patterns (prefers tests first, likes small PRs)
- Tool preferences (uses Bash over dedicated tools)
- Communication style (brief vs detailed responses)

**Promote if consistent across 3+ sessions.**

### Tier 3: Cognitive (High Value - Always Promote)
- Domain insights (game balance, marketing psychology)
- Design decisions and rationale ("chose X because Y")
- Mistakes and lessons learned
- Architecture understanding
- Project-specific context
- User goals and success criteria

**This is what Spark should primarily capture.**

---

## Project Onboarding Questions

When starting a new project, Spark should understand context to know what to track. Based on [Cognitive Task Analysis](https://journals.sagepub.com/doi/10.1177/10944281241271216) research:

### Essential Questions (Ask Every Project)

```yaml
project_onboarding:
  domain:
    question: "What domain is this project in?"
    examples: ["game development", "marketing", "fintech", "devtools", "AI/ML"]
    why: "Activates domain-specific chips for relevant pattern detection"

  success_criteria:
    question: "What does success look like for this project?"
    examples: ["ship MVP in 2 weeks", "reduce load time by 50%", "user retention > 40%"]
    why: "Anchors all learning to measurable outcomes"

  attention_focus:
    question: "What should I pay special attention to?"
    examples: ["performance", "accessibility", "security", "UX polish"]
    why: "Weights observations toward user priorities"

  avoid_mistakes:
    question: "What mistakes should I help you avoid?"
    examples: ["scope creep", "over-engineering", "breaking existing tests"]
    why: "Creates guardrails for decision-making"
```

### Deeper Questions (Ask When Relevant)

```yaml
deeper_context:
  prior_art:
    question: "Is this similar to anything you've built before?"
    why: "Transfers relevant learnings from past projects"

  constraints:
    question: "What constraints am I working within?"
    examples: ["no new dependencies", "must work offline", "budget of $0"]
    why: "Bounds the solution space"

  stakeholders:
    question: "Who else needs to understand or approve this?"
    why: "Adjusts documentation and explanation depth"

  tech_preferences:
    question: "Any technology preferences or anti-preferences?"
    examples: ["prefer functional style", "avoid ORMs", "use TypeScript strictly"]
    why: "Captures coding philosophy"
```

### Domain-Specific Questions

When domain is detected, ask domain-specific questions:

```yaml
game_development:
  - "What's the core game loop?"
  - "What's the target platform/hardware?"
  - "Is this multiplayer or single-player?"
  - "What's the art style direction?"

marketing:
  - "Who is the target audience?"
  - "What's the brand voice/tone?"
  - "What metrics define success?"
  - "What channels are we targeting?"

fintech:
  - "What compliance requirements apply?"
  - "What's the risk tolerance?"
  - "Real money or test environment?"
  - "What audit trail is needed?"
```

---

## What to Capture During Sessions

### High-Signal Events (Always Capture)

1. **Explicit Decisions**
   - "Let's go with X instead of Y"
   - "I prefer this approach because..."
   - "This is important: ..."

2. **Corrections**
   - "No, that's wrong because..."
   - "Actually, it should be..."
   - User undo/redo patterns with explanation

3. **Domain Knowledge**
   - Technical facts about the project
   - Business logic explanations
   - Architecture decisions

4. **Emotional Signals**
   - Frustration indicators (multiple retries, caps, "ugh")
   - Satisfaction signals ("perfect", "exactly", "love it")
   - Surprise or learning moments

5. **Outcome Links**
   - What led to success
   - What caused failures
   - What required iteration

### Low-Signal Events (Store Operationally Only)

1. File reads without meaningful context
2. Navigation between files
3. Successful routine operations
4. Standard tool usage patterns

---

## Memory Consolidation Strategy

Inspired by [how human memory works](https://pmc.ncbi.nlm.nih.gov/articles/PMC4526749/):

### Immediate Memory (Session)
- Everything captured during the session
- High detail, includes context
- Expires after session unless promoted

### Working Memory (Project)
- Consolidated insights from multiple sessions
- Abstracts to patterns and principles
- Lives in `.mind/` or project-specific storage

### Long-Term Memory (Permanent)
- Cross-project wisdom
- User preferences and style
- Domain expertise that transfers
- Lives in `~/.spark/` or CLAUDE.md

### Consolidation Rules

```yaml
promotion_criteria:
  immediate_to_working:
    - "Insight referenced 2+ times in session"
    - "Explicit 'remember this' signal from user"
    - "Tied to success/failure outcome"
    - "Corrects a previous mistake"

  working_to_longterm:
    - "Pattern consistent across 3+ projects"
    - "User explicitly confirms as preference"
    - "Validated by positive outcomes"
    - "Represents transferable domain knowledge"
```

---

## The Metacognitive Loop

Based on [research on self-improving agents](https://arxiv.org/abs/2506.05109), Spark needs intrinsic metacognition:

### 1. Metacognitive Knowledge (Self-Assessment)
- What am I good at? (Edit operations, code generation)
- What do I struggle with? (Bash on Windows, regex)
- What does this user care about? (Performance, clean code)

### 2. Metacognitive Planning (What to Learn)
- What would be most valuable to learn from this session?
- What gaps in my knowledge are showing?
- What patterns am I seeing that I should validate?

### 3. Metacognitive Evaluation (Learning Effectiveness)
- Did my predictions about user preferences hold?
- Were my domain insights accurate?
- What should I unlearn (false patterns)?

---

## Chip System Integration

Chips are domain-specific learning modules. They should:

### Capture Domain Insights

```yaml
game_dev_chip:
  triggers: ["balance", "health", "damage", "physics", "playtest"]
  captures:
    - balance_changes: "What numeric values changed and why"
    - feel_adjustments: "How physics/timing was tuned"
    - player_feedback: "What playtesters reported"
    - iteration_patterns: "What required multiple attempts"
```

### Generate Relevant Questions

When a chip activates, it can suggest relevant questions:

```yaml
game_dev_activated:
  suggest_asking:
    - "What's the target difficulty level?"
    - "Who is the target player demographic?"
    - "What games inspire this project?"
```

### Store Domain-Specific Insights

```yaml
insight_format:
  chip_id: "game_dev"
  category: "balance_decision"
  content: "Lobster health set to 300 (3x original) for longer, more strategic battles"
  rationale: "100 HP made fights too quick, no time for strategy"
  confidence: 0.9
  validated_by: "user continued with this value"
```

---

## Anti-Patterns to Avoid

### 1. Learning Everything
**Problem**: Capturing all events creates noise
**Solution**: Filter aggressively, only promote high-signal events

### 2. Shallow Patterns
**Problem**: "Edit after Read" tells us nothing useful
**Solution**: Capture WHAT was edited and WHY

### 3. No Outcome Linking
**Problem**: Patterns without success/failure context
**Solution**: Always link learnings to outcomes

### 4. User Model Drift
**Problem**: Outdated user preferences still active
**Solution**: Time-decay on preferences, re-validate periodically

### 5. Domain Confusion
**Problem**: Game dev insights applied to fintech
**Solution**: Scope insights to domains/projects

### 6. Overconfidence
**Problem**: Small sample size → high confidence
**Solution**: Require validation before high confidence

---

## Validation Framework

Every promoted learning should be validated:

### Automatic Validation
- Prediction matches outcome (pattern predicted success, got success)
- User accepts suggestion based on learning
- Pattern holds across multiple contexts

### Explicit Validation
- User confirms: "Yes, that's right"
- User corrects: "No, actually..."
- User references the learning in future work

### Validation Scoring

```yaml
reliability_calculation:
  base_score: 0.5  # Starting reliability
  positive_validation: +0.1  # Each confirmation
  negative_validation: -0.2  # Each contradiction
  time_decay: -0.01/week  # If not referenced
  max_score: 1.0
  min_score: 0.0
  promotion_threshold: 0.7
```

---

## Dynamic Domain Discovery

Unlike hardcoded domain chips, Spark should **discover and evolve domains organically**.

### Auto-Domain Detection

When Spark sees patterns it doesn't recognize:

```yaml
domain_emergence:
  trigger: "3+ unique patterns with shared context"
  actions:
    - create_provisional_chip
    - assign_confidence: 0.3
    - track_patterns
    - generate_candidate_questions

  example:
    patterns_seen:
      - "orbit calculations" + "delta-v" + "hohmann transfer"
      - multiple files with ".space" or "trajectory" in path
      - user mentions "spacecraft" or "mission"
    action: "Create provisional 'aerospace' chip"
```

### Chip Self-Evolution (Premium feature)

The chip self-evolution workflow exists as a premium capability and is disabled in OSS.

```yaml
chip_evolution:
  status: disabled_in_oss
  note: "Available in premium release only."
```

### Cross-Domain Transfer

Some learnings transfer across domains:

```yaml
transferable_patterns:
  universal:
    - "Validate inputs at boundaries"
    - "Test before deploy"
    - "Small iterations > big bang"
    - "User preferences persist"

  domain_analogies:
    - game_balance ↔ API_rate_limiting  # Both are resource tuning
    - marketing_audience ↔ UX_personas  # Both are user modeling
    - game_physics ↔ data_pipelines    # Both are flow systems
```

---

## Onboarding: Ask Then Refine

Based on user preference for "both approaches":

### Phase 1: Quick Questions (First 30 seconds)

When new project detected:

```yaml
quick_onboarding:
  required:
    - domain_hint: "What are we building? (1-2 words)"
    - success_hint: "What does done look like?"

  optional_if_unclear:
    - constraints: "Any hard constraints?"
    - prior_art: "Similar to anything you've built?"
```

### Phase 2: Continuous Inference

During session, Spark observes and refines:

```yaml
inference_loop:
  every_10_minutes:
    - pattern_check: "What patterns am I seeing?"
    - domain_update: "Should I activate more chips?"
    - question_candidates: "What would be valuable to ask?"

  decision_points:
    - significant_choice: "User chose X over Y"
    - explicit_statement: "User said 'I prefer...'"
    - correction: "User corrected my approach"
    - success_signal: "This worked well"
    - failure_signal: "This failed, user frustrated"
```

### Phase 3: Session End Synthesis

Before session ends:

```yaml
synthesis:
  actions:
    - consolidate_insights: "What did we learn?"
    - update_chips: "Any chip improvements?"
    - user_confirmation: "Did I capture this correctly?"
    - cross_project: "Does this apply elsewhere?"
```

---

## Mastery Framework

For Spark to achieve "beyond mastery" in any domain:

### Level 1: Reactive (Current)
- Responds to triggers
- Captures what's explicitly shown
- Pattern matching only

### Level 2: Anticipatory
- Predicts likely next steps
- Suggests before asked
- Proactive guardrails

### Level 3: Advisory
- Recommends approaches
- Cites past successes/failures
- Explains tradeoffs

### Level 4: Generative
- Proposes novel solutions
- Synthesizes cross-domain insights
- Creates new patterns from principles

### Level 5: Transcendent
- Identifies paradigm shifts
- Questions assumptions
- Evolves its own learning

### Measuring Progress

```yaml
mastery_metrics:
  reactive_to_anticipatory:
    - "Predictions accepted > 50%"
    - "Suggestions valuable > 70%"

  anticipatory_to_advisory:
    - "Recommendations followed > 60%"
    - "Tradeoff explanations helpful > 80%"

  advisory_to_generative:
    - "Novel solutions adopted > 30%"
    - "Cross-domain insights validated"

  generative_to_transcendent:
    - "Paradigm shifts identified correctly"
    - "Cross-domain synthesis improves outcomes"
```

---

## Implementation Checklist

### Phase 1: Cognitive Filtering ✅ COMPLETE (2026-02-02)
- [x] Distinguish operational vs cognitive events
- [x] Build chip runtime for domain capture
- [x] **Remove operational learning entirely** (learner.py gutted)
- [x] **Clean primitive data** (1,196 primitive insights removed)
- [x] **Disable learning filter** (no longer needed)
- [ ] Implement project onboarding questions
- [ ] Add outcome linking to insights

**Phase 1 Results:**
- Before: 1,427 insights (84% primitive)
- After: 231 insights (cognitive only)
- See CHANGELOG.md for full details

### Phase 2: Metacognitive Loop
- [ ] Self-assessment of capabilities
- [ ] Learning priority planning
- [ ] Validation scoring implementation
- [ ] Dynamic domain discovery

### Phase 3: Active Learning
- [ ] Smart question generation
- [ ] Proactive insight suggestions
- [ ] Automated chip upgrades
- [ ] Continuous inference during sessions

### Phase 4: Transfer Learning
- [ ] Cross-project insight sharing
- [ ] Domain expertise consolidation
- [ ] User model evolution
- [ ] Cross-domain analogy detection

### Phase 5: Mastery Progression
- [ ] Anticipatory capabilities
- [ ] Advisory recommendations
- [ ] Generative synthesis
- [ ] Self-assessment loops

---

## Multi-Domain Project Tracking

Real projects require success across **multiple interconnected domains**. Focusing only on the "main" domain while neglecting others leads to failure.

### The Problem with Single-Domain Focus

```
❌ Single-Domain Thinking:
   "This is a game project → focus on game_dev chip"

   Result: Great gameplay, but:
   - No marketing → nobody finds it
   - Poor tech → performance issues
   - No business model → can't sustain

✅ Multi-Domain Thinking:
   "This game needs: design + tech + art + audio + marketing + business"

   Result: All areas tracked, nothing neglected
```

### Project Profiles

Every project gets a **multi-domain profile**:

```yaml
project_profile:
  name: "Lobster Royale"
  primary_domain: "game_design"

  domains:
    - game_design: 0.9 (critical)
    - game_tech: 0.9 (critical)
    - game_art: 0.7 (important)
    - game_audio: 0.5 (nice to have)
    - marketing: 0.8 (important for launch)
    - business: 0.6 (monetization)

  interconnections:
    - game_design → game_tech (requires)
    - game_design → game_art (enhances)
    - product → marketing (enables)
```

### Domain Interconnections

Domains affect each other. Track the relationships:

| From | To | Relationship | Effect |
|------|-----|--------------|--------|
| game_design | game_tech | requires | Good feel needs solid tech |
| game_design | game_art | enhances | Art reinforces mechanics |
| product | marketing | enables | Good product → marketing claims |
| tech | operations | constrains | Tech debt → operational burden |

### Holistic Intent Setting

Instead of setting intent for ONE domain, set for ALL:

```python
from lib.research import set_holistic_intent

intent = set_holistic_intent(
    project_path="/games/lobster-royale",
    user_priorities=["game_design", "marketing"],
    focus_areas=["fun first", "prepare for launch"]
)

# Result: Intents set for EVERY domain
# - game_design: watch for game feel, balance
# - game_tech: watch for performance, stability
# - marketing: watch for positioning, messaging
# - business: watch for monetization fit
```

### Neglected Domain Detection

Spark tracks coverage across all domains and alerts when critical domains are neglected:

```yaml
coverage_check:
  game_design: 15 insights, 2 warnings (healthy)
  game_tech: 8 insights, 1 warning (healthy)
  marketing: 0 insights, 0 warnings (⚠️ NEGLECTED)

  alert: "Marketing is critical (0.8 weight) but has no coverage"
  recommendation: "Consider marketing strategy before launch"
```

### Cross-Domain Insights

Some insights span multiple domains:

```yaml
cross_domain_insight:
  content: "Purple carpet + kiddie pools creates kid-friendly arena"
  domains: [game_art, game_design, marketing]
  relationship: "Art direction affects gameplay perception and target audience"

  implications:
    - game_art: This aesthetic choice defines the style
    - game_design: Level design should match playful tone
    - marketing: Target family/casual audience, not hardcore
```

### Cross-Cutting Concerns

Some patterns affect ALL domains equally:

```yaml
cross_cutting_concerns:
  quality:
    watch: "Consistent quality across all areas"
    warn: "Quality varying wildly between domains"

  integration:
    watch: "Clean interfaces between domains"
    warn: "Domains evolving independently"

  user_focus:
    watch: "User needs driving all decisions"
    warn: "Domains optimizing for themselves"

  sustainability:
    watch: "Balanced progress across domains"
    warn: "One domain racing ahead while others lag"
```

### Practical Example

When building Lobster Royale, Spark should track:

| Session Focus | Also Watch For |
|--------------|----------------|
| Implementing combat | Tech debt accumulating? |
| Adding new arena | Marketing hook in this arena? |
| Fixing physics | Breaking art/animation? |
| Polish/juice | Core loop still fun? |
| Any session | Which domains need attention? |

---

## Quick Reference

**Before capturing, ask:**
1. Would a human find this useful?
2. Is this a decision or just an action?
3. Can I link this to an outcome?
4. Is this domain-specific or universal?
5. **Does this affect multiple domains?**

**When promoting, require:**
1. 2+ validations OR explicit user confirmation
2. Clear outcome linkage
3. Appropriate scope (project/domain/universal)

**For project onboarding:**
1. Always ask: Domain**s** (plural), Success, Focus, Avoid
2. Optionally ask: Constraints, Preferences, Stakeholders
3. Domain-specific: Let chips suggest questions
4. **Detect all relevant domains, not just primary**
5. **Set holistic intents across all domains**

---

## Sources

- [Cognitive Architecture in AI](https://sema4.ai/learning-center/cognitive-architecture-ai/)
- [Truly Self-Improving Agents Require Intrinsic Metacognitive Learning](https://arxiv.org/abs/2506.05109)
- [Memory Consolidation Research](https://pmc.ncbi.nlm.nih.gov/articles/PMC4526749/)
- [Cognitive Task Analysis Methods](https://journals.sagepub.com/doi/10.1177/10944281241271216)
- [How Sleep Shapes Memory](https://www.pnas.org/doi/10.1073/pnas.2220275120)
- [Fast, Slow, and Metacognitive Thinking in AI](https://www.nature.com/articles/s44387-025-00027-5)
- [Knowledge Elicitation Methods](https://www.sciencedirect.com/science/article/abs/pii/0010448585902933)
