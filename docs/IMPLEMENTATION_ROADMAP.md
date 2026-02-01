# Spark Implementation Roadmap

Related docs:
- docs/IMPROVEMENT_PLANS.md (KISS index and lightweight plan)
- docs/INTEGRATION-PLAN.md
- docs/SPARK_GAPS_AND_SOLUTIONS.md
- docs/VIBE_CODING_INTELLIGENCE_ROADMAP.md

## Priority Matrix by ROI

| Priority | Gap | Impact | Effort | Status |
|----------|-----|--------|--------|--------|
| **P0** | Session Bootstrap + Multi-Platform Output | CRITICAL | Medium | ✅ DONE |
| **P1** | Pattern Detection Layer | HIGH | Medium | ✅ DONE |
| **P2** | Temporal Decay + Conflict Resolution | MEDIUM | Low | ✅ DONE |
| **P3** | Project Context + Semantic Matching | HIGH | Medium | ✅ DONE |
| **P4** | Agent Context Injection | HIGH | Medium | ✅ DONE |
| **P5** | Worker Health Monitoring | HIGH | Medium | ✅ DONE |
| **P6** | Validation Loop (Predictions) | MEDIUM | Medium | 🟡 IN PROGRESS |
| **P7** | Content Learning | HIGH | Medium | ✅ DONE |

---

## Phase 1: Make Learnings Useful (COMPLETED ✓)

**Completed 2026-01-27**

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
└─────────────────────────────────────────────────────────────────┘
```

### Implementation Files
- `lib/output_adapters/claude_code.py` - CLAUDE.md writer
- `lib/output_adapters/cursor.py` - .cursorrules writer
- `lib/output_adapters/windsurf.py` - .windsurfrules writer
- `lib/output_adapters/clawdbot.py` - Clawdbot config writer
- `lib/output_adapters/common.py` - Shared marked-section logic
- `lib/context_sync.py` - Main sync orchestration

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

**Completed 2026-01-28**

### Pattern Detection Layer

```
┌─────────────────────────────────────────────────────────────────┐
│  PATTERN DETECTION LAYER                                         │
│                                                                 │
│  Detectors built:                                               │
│  ✅ CorrectionDetector - "no, I meant..." signals               │
│  ✅ SentimentDetector - satisfaction/frustration detection      │
│  ✅ RepetitionDetector - user asks same thing 3+ times          │
│  ✅ SemanticIntentDetector - polite redirects, implicit prefs   │
│  ✅ PatternAggregator - combines detectors, triggers learning   │
│                                                                 │
│  All tests passing: 15/15                                       │
└─────────────────────────────────────────────────────────────────┘
```

### Implementation Files
- `lib/pattern_detection/correction.py` - 7KB
- `lib/pattern_detection/sentiment.py` - 9KB
- `lib/pattern_detection/repetition.py` - 7KB
- `lib/pattern_detection/semantic.py` - 5KB
- `lib/pattern_detection/aggregator.py` - 9KB
- `lib/pattern_detection/worker.py` - Queue processing worker

### Detectors Summary

| Detector | Signals | Value |
|----------|---------|-------|
| **CorrectionDetector** | "no, I meant", "not that", "actually", "wrong" | HIGH - direct preference learning |
| **SentimentDetector** | "perfect", "great" vs "ugh", "still not working" | HIGH - satisfaction tracking |
| **RepetitionDetector** | Same request 3+ times | MEDIUM - strong preference signal |
| **SemanticIntentDetector** | "what about", "let's go with", "option B" | MEDIUM - polite redirects |

---

## Phase 3: Trust What We Learn (COMPLETED ✓)

**Completed 2026-01-28**

### Temporal Decay + Conflict Resolution

```
┌─────────────────────────────────────────────────────────────────┐
│  DECAY + CONFLICT RESOLUTION                                     │
│                                                                 │
│  ✅ Temporal Decay                                              │
│     - _half_life_days() - category-specific decay rates         │
│     - effective_reliability() - adjusted confidence with decay  │
│     - prune_stale() - removes insights below threshold          │
│     - CLI: python -m spark.cli decay --apply                    │
│                                                                 │
│  ✅ Conflict Resolution                                         │
│     - resolve_conflicts() - groups by topic, picks best         │
│     - Scoring: effective_reliability + recency + validations    │
│     - Auto-applied during context sync                          │
│                                                                 │
│  Integration:                                                   │
│     - context_sync.py:211 calls prune_stale() during sync       │
│     - context_sync.py:86 passes resolve_conflicts=True          │
│     - context_sync.py:94 sorts by effective_reliability()       │
└─────────────────────────────────────────────────────────────────┘
```

### Implementation Location
All in `lib/cognitive_learner.py`:
- `_half_life_days()` - lines 593-605
- `effective_reliability()` - lines 607-612
- `prune_stale()` - lines 614-628
- `resolve_conflicts()` - lines 671-686

### Decay Half-Lives

| Category | Half-Life | Rationale |
|----------|-----------|-----------|
| USER_UNDERSTANDING | 90 days | Preferences relatively stable |
| COMMUNICATION | 90 days | Communication style stable |
| WISDOM | 180 days | Principles very stable |
| META_LEARNING | 120 days | Learning patterns stable |
| SELF_AWARENESS | 60 days | Self-knowledge evolves |
| REASONING | 60 days | Reasoning patterns evolve |
| CONTEXT | 45 days | Context-specific, transient |
| CREATIVITY | 60 days | Creative patterns evolve |

---

## Phase 4: Smarter Learning (COMPLETED ✓)

**Completed 2026-01-28**

### Context Awareness + Semantic Understanding

```
┌─────────────────────────────────────────────────────────────────┐
│  CONTEXT AWARENESS                                               │
│                                                                 │
│  ✅ Project Context Detection                                   │
│     - lib/project_context.py (8.6KB)                            │
│     - Detects: package.json, pyproject.toml, go.mod, etc.       │
│     - Extracts: language, framework, dependencies               │
│     - Caches results for performance                            │
│                                                                 │
│  ✅ Agent Context Injection                                     │
│     - lib/orchestration.py:inject_agent_context()               │
│     - Opt-in via SPARK_AGENT_INJECT=1                           │
│     - Configurable: SPARK_AGENT_CONTEXT_LIMIT                   │
│     - Configurable: SPARK_AGENT_CONTEXT_MAX_CHARS               │
│                                                                 │
│  ✅ Semantic Matching                                           │
│     - lib/pattern_detection/semantic.py                         │
│     - Detects polite redirects: "what about", "how about"       │
│     - Detects implicit preferences: "let's go with option B"    │
│     - Repetition gating: boosts confidence on repeated signals  │
└─────────────────────────────────────────────────────────────────┘
```

### Implementation Files
- `lib/project_context.py` - Project detection + cache (8.6KB)
- `lib/orchestration.py` - Agent injection + routing (6.9KB)
- `lib/pattern_detection/semantic.py` - Semantic intent detection (5KB)

### Project Context Detection

| File | Detects |
|------|---------|
| `package.json` | JavaScript/TypeScript, React/Vue/Next/Svelte, dependencies |
| `requirements.txt` / `pyproject.toml` | Python, frameworks |
| `go.mod` | Go |
| `Cargo.toml` | Rust |
| `pom.xml` / `build.gradle` | Java |

---

## Phase 5: Operational Reliability (COMPLETED ✓)

**Completed 2026-01-28**

### Worker Health Monitoring

```
┌─────────────────────────────────────────────────────────────────┐
│  WORKER HEALTH MONITORING                                        │
│                                                                 │
│  ✅ Watchdog (scripts/watchdog.py)                              │
│     - Auto-restarts sparkd, dashboard, bridge_worker            │
│     - Checks HTTP health endpoints                              │
│     - Monitors heartbeat age for bridge_worker                  │
│     - Queue pressure warnings (> 500 events for 5+ mins)        │
│     - Logs to ~/.spark/logs/watchdog.log                        │
│                                                                 │
│  ✅ Heartbeat System (lib/bridge_cycle.py)                      │
│     - bridge_worker writes heartbeat every cycle                │
│     - bridge_heartbeat_age_s() checks staleness                 │
│     - File: ~/.spark/bridge_worker_heartbeat.json               │
│                                                                 │
│  ✅ CLI Health Check (spark/cli.py:cmd_health)                  │
│     - python -m spark.cli health                                │
│     - Shows all component status                                │
│                                                                 │
│  ✅ Auto-start in start_spark.bat                               │
│     - Watchdog starts automatically                             │
│     - Opt-out: set SPARK_NO_WATCHDOG=1                          │
└─────────────────────────────────────────────────────────────────┘
```

### Implementation Files
- `scripts/watchdog.py` - Auto-restart + queue alerts
- `lib/bridge_cycle.py` - Heartbeat write/read helpers
- `spark/cli.py:cmd_health` - CLI health check
- `start_spark.bat` - Starts watchdog by default

---

## Phase 6: Validation Loop (IN PROGRESS)

### Prediction → Outcome → Learning

```
┌─────────────────────────────────────────────────────────────────┐
│  VALIDATION LOOP                                                 │
│                                                                 │
│  Current state:                                                 │
│  - Decay exists (time-based confidence reduction)               │
│  - Manual validation via spark_validate MCP tool                │
│  - Prediction registry + outcome matching (prompts/tool errors) │
│  - Outcome logging for skills/orchestration/project decisions   │
│                                                                 │
│  Missing:                                                       │
│  🔴 Explicit outcome check-ins (user confirmation)              │
│  🔴 Auto-boost/decay for non-cognitive predictions              │
│  🔴 Surprise capture for non-cognitive contradictions           │
│  🔴 Broader project outcome signals (launch metrics, etc.)      │
│                                                                 │
│  Example flow:                                                  │
│  1. Insight: "User prefers TypeScript"                          │
│  2. Prediction: "User will request TypeScript for new file"     │
│  3. Observe: User requests JavaScript                           │
│  4. Result: Decay confidence, capture surprise                  │
└─────────────────────────────────────────────────────────────────┘
```

### Implemented (v1)
- `lib/validation_loop.py` - validates user preference/communication insights from prompts
- `lib/bridge_cycle.py` - runs validation each cycle
- `lib/prediction_loop.py` - prediction registry + semantic outcome matching
- `lib/outcome_log.py` - shared outcome log for non-tool domains
- `spark validate` - manual scan command
- `tests/test_validation_loop.py` - matcher unit tests

### Next (recommended)
- Monitor v1 for a day or two to confirm low false positives
- Add explicit outcome check-ins + tighter matching thresholds
- Extend prediction signals to project milestones and agent success KPIs

---

## Phase 7: Content Learning (COMPLETED ✓)

**Completed 2026-01-29**

### Content-Based Pattern Detection

```
┌─────────────────────────────────────────────────────────────────┐
│  CONTENT LEARNING                                                │
│                                                                 │
│  Learns from:                                                   │
│  ✅ Code written via Edit/Write events                         │
│  ✅ Project structure from file listings                        │
│                                                                 │
│  Detects:                                                       │
│  - Python: naming_style, type_hints, error_handling, imports   │
│  - JS/TS: function_style, async_patterns, react_patterns       │
│  - Generic: indentation, comments, formatting                   │
│  - Project: test_organization, source_organization, tooling    │
│                                                                 │
│  Philosophy: Observations, not preferences                      │
│  - Start at 60% confidence (vs 80% for explicit preferences)   │
│  - Build understanding over repeated patterns (3+ occurrences) │
│  - Stored as CONTEXT category insights                          │
│                                                                 │
│  All tests passing: 28/28                                       │
└─────────────────────────────────────────────────────────────────┘
```

### Implementation Files
- `lib/content_learner.py` - Pattern detection from code (296 lines)
- `lib/bridge_cycle.py` - Integrated content learning from Edit/Write events
- `tests/test_content_learner.py` - Comprehensive test suite (28 tests)

### Pattern Categories

| Language | Patterns Detected |
|----------|-------------------|
| **Python** | snake_case, type_hints, f_strings, dataclasses, pathlib, docstrings |
| **JS/TS** | arrow_functions, async_await, react_hooks, exports, semicolons |
| **Generic** | TODO comments, indentation style, line length |
| **Project** | test organization, src directory, TypeScript, ESLint, Prettier |

---

## Summary

| Phase | Status | Key Files |
|-------|--------|-----------|
| Phase 1: Session Bootstrap | ✅ DONE | `lib/output_adapters/`, `lib/context_sync.py` |
| Phase 2: Pattern Detection | ✅ DONE | `lib/pattern_detection/` (15/15 tests) |
| Phase 3: Decay + Conflicts | ✅ DONE | `lib/cognitive_learner.py` |
| Phase 4: Context + Semantic | ✅ DONE | `lib/project_context.py`, `lib/orchestration.py` |
| Phase 5: Worker Health | ✅ DONE | `scripts/watchdog.py`, `lib/bridge_cycle.py` |
| Phase 6: Validation Loop | 🟡 IN PROGRESS | `lib/validation_loop.py`, `lib/bridge_cycle.py`, `lib/prediction_loop.py`, `lib/outcome_log.py` |
| Phase 7: Content Learning | ✅ DONE | `lib/content_learner.py` (28/28 tests) |

---

## Success Metrics

| Phase | Metric | Target | Status |
|-------|--------|--------|--------|
| Phase 1 | Learnings loaded at session start | 100% of sessions | ✅ |
| Phase 2 | Patterns detected per session | 5+ meaningful patterns | ✅ |
| Phase 3 | Stale learnings pruned | < 10% over 90 days old | ✅ |
| Phase 4 | Context-appropriate learnings | 90%+ relevance score | ✅ |
| Phase 5 | Worker uptime | 99%+ | ✅ |
| Phase 6 | Prediction accuracy tracking | Baseline + improvement | 🟡 |
| Phase 7 | Code patterns detected | 3+ unique patterns/project | ✅ |

---

## The Feedback Loop

```
Current state (Phases 1-5 complete):

  Capture → Detect → Store → Load → Apply
      ↑                              │
      └──────────────────────────────┘
              (via sync)

  + Watchdog ensures workers stay alive
  + Heartbeat monitors processing health
  + Queue alerts prevent backlog

Target state (with Phase 6):

  Capture → Detect → Store → Load → Apply → Validate → Improve
      ↑                                                   │
      └───────────────────────────────────────────────────┘
              (continuous learning loop)
```

**Next priority: Phase 6 (Validation Loop)** - automatic prediction→outcome→learning cycle.
