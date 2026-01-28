# Spark Implementation Roadmap

## Priority Matrix by ROI

| Priority | Gap | Impact | Effort | Why This Order |
|----------|-----|--------|--------|----------------|
| **P0** | Session Bootstrap + Multi-Platform Output | CRITICAL | Medium | Nothing works without it |
| **P1** | Pattern Detection Layer | HIGH | Medium | Foundation for all inference |
| **P2** | Validation Loop | HIGH | Medium | Without validation, confidence is meaningless |
| **P3** | Temporal Decay | MEDIUM | **Low** | Quick win - prevents stale data |
| **P3** | Conflict Resolution | MEDIUM | **Low** | Quick win - handles contradictions |
| **P4** | Semantic Matching | HIGH | High | Better detection quality |
| **P4** | Project Context | HIGH | Medium | Relevance filtering by project type |
| **P5** | Agent Context Injection | HIGH | Medium | Spawned agents get Spark context |

---

## Phase 1: Make Learnings Useful (COMPLETED ✓)

### Session Bootstrap + Multi-Platform Output Adapters

```
┌─────────────────────────────────────────────────────────────────┐
│  SESSION BOOTSTRAP SYSTEM                                       │
│                                                                 │
│  Components:                                                    │
│  1. spark-sync command - reads learnings, writes to platforms   │
│  2. Output adapters for each platform:                          │
│     ├─> CLAUDE.md (Claude Code) - auto-write                    │
│     ├─> .cursorrules (Cursor) - auto-write                      │
│     ├─> .windsurfrules (Windsurf) - auto-write                  │
│     ├─> Bot config (Clawdbot) - auto-write                      │
│     ├─> gpt_instructions.md (OpenAI) - export for paste         │
│     └─> gemini_system.md (Gemini) - export for paste            │
│  3. Wrapper launchers: spark-claude, spark-cursor               │
│  4. No daemon needed - on-demand sync before session start      │
│                                                                 │
│  WHY FIRST: Learnings are captured but never loaded.            │
│  Without bootstrap, the entire system is pointless.             │
└─────────────────────────────────────────────────────────────────┘
```

### Trigger Mechanisms (No Daemon Required)
- **Pre-launch hook**: `spark-sync` runs before AI tool launches
- **Git hook**: post-checkout updates context files
- **Optional file watcher** on `~/.spark/` as backup
- **Scheduled task** (cron/Task Scheduler) for periodic sync

### Platform Adapter Strategy

| Platform | Context File | Method | Notes |
|----------|-------------|--------|-------|
| Claude Code | `CLAUDE.md` | Auto-write | Fenced markers preserve user edits |
| Cursor | `.cursorrules` | Auto-write | Project root |
| Windsurf | `.windsurfrules` | Auto-write | Project root |
| Clawdbot | Bot config | Auto-write | `~/.clawdbot/agents/*/config.json` |
| OpenAI GPT | `gpt_instructions.md` | Export | Manual paste to custom instructions |
| Gemini | `gemini_system.md` | Export | Manual paste to system prompt |

---

## Phase 2: Learn Better (COMPLETED ✓)

**Implemented 2026-01-28:**
- `lib/pattern_detection/` - Complete pattern detection layer
- CorrectionDetector - Detects "no, I meant..." signals (95% confidence)
- SentimentDetector - Detects satisfaction/frustration signals
- RepetitionDetector - Detects 3+ similar requests
- SequenceDetector - Detects tool success/failure patterns
- PatternAggregator - Combines detectors, triggers learning
- Integrated into `hooks/observe.py`
- All tests passing (12/12)

### Pattern Detection Layer

```
┌─────────────────────────────────────────────────────────────────┐
│  PATTERN DETECTION LAYER (Highest Impact After Bootstrap)       │
│                                                                 │
│  Build these detectors:                                         │
│  1. CorrectionDetector - "no, I meant..." signals (HIGH value)  │
│  2. SentimentDetector - satisfaction/frustration detection      │
│  3. RepetitionDetector - user asks same thing 3+ times          │
│  4. SequenceDetector - successful tool sequence patterns        │
│  5. StyleDetector - working style from behavior patterns        │
│                                                                 │
│  Current state:  Raw Events → Store → (nothing learned)         │
│  Target state:   Raw Events → Detect → Infer → Synthesize       │
│                                                                 │
│  WHY SECOND: Without patterns, we only store raw events.        │
│  With patterns, every interaction teaches something.            │
└─────────────────────────────────────────────────────────────────┘
```

### Detectors to Build

| Detector | Signals | Value |
|----------|---------|-------|
| **CorrectionDetector** | "no, I meant", "not that", "actually", "wrong" | HIGH - direct preference learning |
| **SentimentDetector** | "perfect", "great" vs "ugh", "still not working" | HIGH - satisfaction tracking |
| **RepetitionDetector** | Same request 3+ times | MEDIUM - strong preference signal |
| **SequenceDetector** | Read→Edit→Test patterns that succeed | MEDIUM - approach learning |
| **StyleDetector** | Response timing, explanation skipping | LOW - working style |

### Pattern Aggregator
- Collects patterns from all detectors
- Triggers inference when confidence >= 0.8
- Triggers inference when multiple patterns corroborate

---

## Phase 3: Trust What We Learn (NEXT PRIORITY - QUICK WINS)

### Validation + Decay + Conflict Resolution

```
┌─────────────────────────────────────────────────────────────────┐
│  VALIDATION + DECAY (Low Effort, Medium Impact)                 │
│                                                                 │
│  1. Temporal Decay (~50 lines of code)                          │
│     - Half-life by type:                                        │
│       • preferences: 90 days                                    │
│       • principles: 180 days                                    │
│       • opinions: 60 days                                       │
│       • observations: 30 days                                   │
│     - Auto-prune below 0.3 confidence threshold                 │
│                                                                 │
│  2. Validation Loop                                             │
│     - Create prediction from insight + situation                │
│     - Observe actual outcome                                    │
│     - Boost confidence when correct, decay when wrong           │
│     - Capture surprises as learning opportunities               │
│                                                                 │
│  3. Conflict Resolution                                         │
│     - Group learnings by topic                                  │
│     - Pick best based on: context match + recency + confidence  │
│     - Track contradictions for meta-learning                    │
│                                                                 │
│  WHY: Quick wins that prevent garbage accumulation and          │
│  make confidence scores actually meaningful.                    │
└─────────────────────────────────────────────────────────────────┘
```

### Decay Half-Lives

| Learning Type | Half-Life | Rationale |
|---------------|-----------|-----------|
| Preferences | 90 days | Relatively stable |
| Principles | 180 days | Very stable |
| Opinions | 60 days | Change faster |
| Observations | 30 days | Transient |

---

## Phase 4: Smarter Learning (DEEPER WORK)

### Context Awareness + Semantic Understanding

```
┌─────────────────────────────────────────────────────────────────┐
│  CONTEXT AWARENESS (Medium Effort, High Impact)                 │
│                                                                 │
│  1. Project Context Detection                                   │
│     - Auto-detect from files: package.json, requirements.txt    │
│     - Extract: language, framework, project type                │
│     - Filter learnings by relevance to current project          │
│                                                                 │
│  2. Agent Context Injection                                     │
│     - Intercept Task tool calls                                 │
│     - Inject Spark context into agent prompts                   │
│     - Levels: minimal (top 3), summary, full                    │
│                                                                 │
│  3. Semantic Matching                                           │
│     - Beyond keywords: understand intent clusters               │
│     - Detect polite corrections: "could you instead..."         │
│     - Detect implicit preferences: "let's go with option B"     │
│     - Intent patterns: correction, satisfaction, frustration    │
└─────────────────────────────────────────────────────────────────┘
```

**Phase 4 status (in progress):**
- Added `lib/project_context.py` with top-level detection + cache.
- Sync now filters bootstrap insights by project context.
- Added `SemanticIntentDetector` (polite redirects, implicit preferences) with repetition gating.
- Added opt-in agent context injection via `lib.orchestration.inject_agent_context`.

### Project Context Detection

| File | Detects |
|------|---------|
| `package.json` | JavaScript/TypeScript, React/Vue/Next, dependencies |
| `requirements.txt` / `pyproject.toml` | Python, frameworks |
| `go.mod` | Go |
| `Cargo.toml` | Rust |
| `pom.xml` / `build.gradle` | Java |

---

## Estimated Timeline

| Phase | Components | Effort | Cumulative |
|-------|-----------|--------|------------|
| Phase 1 | Session Bootstrap + Output Adapters | 3-5 days | Week 1 |
| Phase 2 | Pattern Detection Layer | 5-7 days | Week 2 |
| Phase 3 | Decay + Validation + Conflicts | 2-3 days | Week 3 |
| Phase 4 | Context + Semantic | 5-7 days | Week 4 |

---

## Success Metrics

| Phase | Metric | Target |
|-------|--------|--------|
| Phase 1 | Learnings loaded at session start | 100% of sessions |
| Phase 2 | Patterns detected per session | 5+ meaningful patterns |
| Phase 3 | Stale learnings pruned | < 10% over 90 days old |
| Phase 4 | Context-appropriate learnings | 90%+ relevance score |

---

## The Critical Insight

The feedback loop must be complete:

```
Current:  Capture → Store → (nothing)

Target:   Capture → Store → Load → Apply → Validate → Improve
                            ↑                         │
                            └─────────────────────────┘
```

- Without **Load** (Phase 1): learnings are useless
- Without **Detect** (Phase 2): no meaningful patterns
- Without **Validate** (Phase 3): confidence is meaningless
- Without **Context** (Phase 4): learnings apply incorrectly

**Phase 1 (Session Bootstrap) is the #1 blocker. Everything else is useless without it.**
