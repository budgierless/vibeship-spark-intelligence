# Intelligent Learning Architecture

**Goal**: Make Spark not just filter out noise, but actively identify, capture, and evolve from truly important information.

The current system is reactive (score what comes in). We need **proactive intelligence** that:
1. Knows what it doesn't know
2. Actively seeks valuable information
3. Connects learnings across contexts
4. Abstracts principles from specifics
5. Validates and evolves its beliefs

---

## The Seven Intelligence Systems

### 1. Curiosity Engine
**Problem**: We only learn from what happens to pass by.
**Solution**: Actively identify knowledge gaps and seek to fill them.

```
What I Know          What I Don't Know         What I Should Ask
     ↓                      ↓                        ↓
[User prefers X]    [Why does user prefer X?]  → "What drives this preference?"
[Tool Y fails]      [When does Y succeed?]     → Track success conditions
[Domain is games]   [What game patterns?]      → "What makes a good game feel?"
```

**Implementation**:
- Track "unknown edges" - things referenced but not understood
- Generate questions from partial knowledge
- Surface curiosity prompts during relevant contexts
- Reward question-asking that leads to valuable answers

### 2. Wisdom Distillation Engine
**Problem**: We store specific learnings but don't abstract principles.
**Solution**: Automatically extract general wisdom from multiple specific learnings.

```
Specific Learnings:
  - "Health=300 works for game balance"
  - "Timeout=5000ms works for API calls"
  - "Margin=16px works for spacing"
           ↓
Abstracted Wisdom:
  - "Start with sensible defaults, then tune based on feel"
  - "Numbers that 'feel right' often have underlying principles"
```

**Implementation**:
- Cluster similar learnings by semantic similarity
- Look for common patterns across clusters
- Generate candidate principles
- Validate principles against new situations
- Promote validated principles to WISDOM tier

### 3. Contradiction Detector
**Problem**: New information may contradict existing beliefs, but we don't notice.
**Solution**: Actively check new learnings against existing knowledge.

```
Existing: "User prefers verbose explanations"
New: "User said 'just give me the code'"
         ↓
Contradiction detected!
         ↓
Resolution options:
  - Context-dependent (verbose for concepts, terse for code)
  - Belief update (user preference changed)
  - Clarification needed (ask user)
```

**Implementation**:
- Before storing new insight, semantic search existing insights
- Flag high-similarity but opposite-sentiment matches
- Track contradiction resolution patterns
- Learn when beliefs should be context-qualified vs updated

### 4. Transfer Learning Engine
**Problem**: Learnings in one domain don't transfer to related domains.
**Solution**: Identify cross-domain applicability of insights.

```
Game Dev Learning: "Feedback loops keep players engaged"
         ↓
Transfer Analysis:
  - Marketing: "Feedback loops keep users engaged with campaigns"
  - Product: "Feedback loops drive feature adoption"
  - Code: "Fast feedback loops improve dev velocity"
```

**Implementation**:
- Identify domain-agnostic core of each learning
- Map to analogous concepts in other domains
- Track transfer success/failure
- Build cross-domain principle library

### 5. Hypothesis Tracker
**Problem**: We learn from outcomes but don't make predictions to test.
**Solution**: Generate hypotheses and track their validation.

```
Observation: "User corrected my approach twice"
         ↓
Hypothesis: "User prefers approach X over approach Y"
         ↓
Prediction: "Next time, I should try X first"
         ↓
Track: Did X work? Was user satisfied?
         ↓
Update: Confidence in hypothesis
```

**Implementation**:
- Generate hypotheses from patterns (2+ similar events)
- Make explicit predictions
- Track prediction outcomes
- Promote validated hypotheses to beliefs
- Demote invalidated hypotheses

### 6. Deep User Model
**Problem**: User understanding is shallow (preferences) not deep (motivations).
**Solution**: Build multi-layer user model that explains WHY, not just WHAT.

```
Layer 1 - Behaviors: "User uses dark mode"
Layer 2 - Preferences: "User prefers low-contrast interfaces"
Layer 3 - Values: "User values eye comfort over aesthetics"
Layer 4 - Motivations: "User works long hours, eye strain is real"
Layer 5 - Identity: "User is a serious developer who optimizes environment"
```

**Implementation**:
- Track behavior patterns
- Infer preferences from behaviors
- Infer values from preferences
- Infer motivations from values
- Build coherent user identity model
- Use deeper layers to predict new preferences

### 7. Calibration System
**Problem**: We don't know when we're confident vs uncertain.
**Solution**: Track confidence calibration and express appropriate uncertainty.

```
Situation: Code review task
         ↓
Check calibration:
  - Past accuracy on code review: 73%
  - This domain familiarity: Low
  - Similar past tasks: 2 (both had issues)
         ↓
Calibrated response:
  "I'll review this, but I'm less confident in [specific area] -
   you may want to double-check that part."
```

**Implementation**:
- Track prediction accuracy by task type
- Track accuracy by domain/context
- Compute calibrated confidence intervals
- Express uncertainty appropriately
- Learn from calibration errors

---

## Integration Architecture

```
                    ┌─────────────────────────────────────┐
                    │         INCOMING INFORMATION        │
                    └─────────────────┬───────────────────┘
                                      │
                    ┌─────────────────▼───────────────────┐
                    │       IMPORTANCE SCORER             │
                    │  (Rule-based + Semantic + Feedback) │
                    └─────────────────┬───────────────────┘
                                      │
           ┌──────────────────────────┼──────────────────────────┐
           │                          │                          │
           ▼                          ▼                          ▼
┌──────────────────┐      ┌──────────────────┐      ┌──────────────────┐
│ CONTRADICTION    │      │    HYPOTHESIS    │      │    CURIOSITY     │
│   DETECTOR       │      │     TRACKER      │      │     ENGINE       │
│                  │      │                  │      │                  │
│ Does this        │      │ Does this        │      │ Does this        │
│ contradict       │      │ validate/        │      │ answer an        │
│ existing belief? │      │ invalidate a     │      │ open question?   │
│                  │      │ hypothesis?      │      │                  │
└────────┬─────────┘      └────────┬─────────┘      └────────┬─────────┘
         │                         │                         │
         └─────────────────────────┼─────────────────────────┘
                                   │
                    ┌──────────────▼──────────────┐
                    │      COGNITIVE LEARNER      │
                    │   (Store with full context) │
                    └──────────────┬──────────────┘
                                   │
           ┌───────────────────────┼───────────────────────┐
           │                       │                       │
           ▼                       ▼                       ▼
┌──────────────────┐    ┌──────────────────┐    ┌──────────────────┐
│     WISDOM       │    │    TRANSFER      │    │   DEEP USER      │
│   DISTILLATION   │    │    LEARNING      │    │     MODEL        │
│                  │    │                  │    │                  │
│ Can we abstract  │    │ Does this apply  │    │ Does this reveal │
│ a principle?     │    │ to other domains?│    │ deeper motivation│
└────────┬─────────┘    └────────┬─────────┘    └────────┬─────────┘
         │                       │                       │
         └───────────────────────┼───────────────────────┘
                                 │
                    ┌────────────▼────────────┐
                    │    CALIBRATION SYSTEM   │
                    │  (Track prediction      │
                    │   accuracy over time)   │
                    └────────────┬────────────┘
                                 │
                    ┌────────────▼────────────┐
                    │   PROMOTION ENGINE      │
                    │  (CLAUDE.md, AGENTS.md) │
                    └─────────────────────────┘
```

---

## Implementation Priority

### Phase 1: Foundation (Current)
- [x] Importance Scorer with semantic intelligence
- [x] Rule-based signal detection
- [x] Outcome feedback loop
- [ ] Basic contradiction detection

### Phase 2: Active Intelligence
- [ ] Curiosity Engine (knowledge gap tracking)
- [ ] Hypothesis Tracker (prediction → validation)
- [ ] Basic calibration (confidence tracking)

### Phase 3: Deep Learning
- [ ] Wisdom Distillation (principle extraction)
- [ ] Transfer Learning (cross-domain application)
- [ ] Deep User Model (motivation inference)

### Phase 4: Self-Evolution
- [ ] Meta-learning (learning how to learn)
- [ ] Architecture self-modification
- [ ] Autonomous knowledge seeking

---

## Success Metrics

| System | Metric | Target |
|--------|--------|--------|
| Importance Scorer | Prediction accuracy | >85% |
| Curiosity Engine | Questions that lead to insights | >50% |
| Wisdom Distillation | Principles validated | >70% |
| Contradiction Detector | Conflicts resolved correctly | >80% |
| Transfer Learning | Cross-domain insights used | >30% |
| Hypothesis Tracker | Predictions validated | >60% |
| Deep User Model | Preference predictions | >75% |
| Calibration | Confidence vs accuracy match | <10% error |

---

## The Vision

```
Today:  Reactive filtering - "Is this worth learning?"
        ↓
Next:   Active seeking - "What should I be learning?"
        ↓
Future: Self-evolving - "How should I be learning?"
```

Spark becomes not just a learning system, but a **learning-to-learn** system that:
1. Knows what it knows (and doesn't know)
2. Actively fills knowledge gaps
3. Abstracts wisdom from experience
4. Transfers knowledge across domains
5. Predicts and validates
6. Calibrates its confidence
7. Evolves its own learning strategies

---

*The goal is not to store more - it's to understand deeper.*
