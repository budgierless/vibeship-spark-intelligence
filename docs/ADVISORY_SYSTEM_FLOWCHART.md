# Spark Advisory System — Complete Flowchart

## Main Pipeline (The [SPARK] Path)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        CLAUDE CODE SESSION                                  │
│                                                                             │
│   User types prompt ──► Claude picks tool ──► PreToolUse hook fires         │
└──────────────────────────────────┬──────────────────────────────────────────┘
                                   │
                                   ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  hooks/observe.py  (line 562)                                               │
│                                                                             │
│  event_type == PRE_TOOL                                                     │
│                                                                             │
│  ┌──────────────┐    ┌──────────────────┐    ┌──────────────────────┐       │
│  │ make_         │    │ advisory_engine  │    │ EIDOS               │       │
│  │ prediction()  │    │ .on_pre_tool()   │    │ create_step_before  │       │
│  │              │    │  ▼ THE MAIN PATH │    │ _action()           │       │
│  └──────────────┘    └────────┬─────────┘    └──────────────────────┘       │
│                               │                                             │
│           ┌───────────────────┤ (if engine crashes)                         │
│           │                   ▼                                             │
│           │    ┌──────────────────────────┐                                 │
│           │    │ LEGACY FALLBACK          │                                 │
│           │    │ advisor.advise_on_tool() │                                 │
│           │    │ ⚠ NO STDOUT EMISSION     │                                 │
│           │    │ Just logs to JSONL       │                                 │
│           │    └──────────────────────────┘                                 │
│           │                                                                 │
└───────────┼─────────────────────────────────────────────────────────────────┘
            │
            ▼
┌═══════════════════════════════════════════════════════════════════════════════┐
║                                                                             ║
║   advisory_engine.py :: on_pre_tool()   (2,874 lines)                       ║
║                                                                             ║
║   ┌─────────────────────────────────────────────────────────┐               ║
║   │ 0. SAFETY CHECK                                         │               ║
║   │    - Abort early if tool is in safety bypass list       │               ║
║   └─────────────────────┬───────────────────────────────────┘               ║
║                         │                                                   ║
║                         ▼                                                   ║
║   ┌─────────────────────────────────────────────────────────┐               ║
║   │ 1. LOAD STATE                                           │               ║
║   │    advisory_state.py (427 lines)                        │               ║
║   │    - Session history, intent, cooldowns                 │               ║
║   │    - Recent tool calls, shown advice                    │               ║
║   └─────────────────────┬───────────────────────────────────┘               ║
║                         │                                                   ║
║                         ▼                                                   ║
║   ┌─────────────────────────────────────────────────────────┐               ║
║   │ 1.5 CHEAP CHECKS (before retrieval)                     │               ║
║   │    - Text repeat guard (same context recently emitted?) │               ║
║   │    - Emission budget check (budget already exhausted?)  │               ║
║   │    - ⚡ Skips retrieval entirely if either fires         │               ║
║   └─────────────────────┬───────────────────────────────────┘               ║
║                         │                                                   ║
║                         ▼                                                   ║
║   ┌─────────────────────────────────────────────────────────┐               ║
║   │ 2. PACKET LOOKUP (Fast Path)                            │               ║
║   │    advisory_packet_store.py (~3,286 lines)              │               ║
║   │                                                         │               ║
║   │    Exact match: session + tool + intent + plane         │               ║
║   │    Relaxed match: weighted scoring across dimensions    │               ║
║   │    TTL: 900s (15 min)                                   │               ║
║   │                                                         │               ║
║   │    HIT ──► skip to step 4 (gate)                        │               ║
║   │    MISS ──► continue to step 3                          │               ║
║   └─────────────┬───────────────────┬───────────────────────┘               ║
║                 │                   │                                        ║
║           (packet hit)        (packet miss)                                  ║
║                 │                   │                                        ║
║                 │                   ▼                                        ║
║                 │   ┌───────────────────────────────────────────────────┐    ║
║                 │   │ 3. LIVE RETRIEVAL                                │    ║
║                 │   │    advisor.py :: advise_on_tool() (5,816 lines)  │    ║
║                 │   │                                                  │    ║
║                 │   │    Queries 7 sources in parallel:                │    ║
║                 │   │                                                  │    ║
║                 │   │    ┌─────────────────────┐ quality: 0.50        │    ║
║                 │   │    │ ① Cognitive Insights │─────────────┐        │    ║
║                 │   │    │   cognitive_learner  │             │        │    ║
║                 │   │    └─────────────────────┘             │        │    ║
║                 │   │    ┌─────────────────────┐ quality: 0.90        │    ║
║                 │   │    │ ② EIDOS Distillation│─────────────┤        │    ║
║                 │   │    │   eidos/store.py     │             │        │    ║
║                 │   │    └─────────────────────┘             │        │    ║
║                 │   │    ┌─────────────────────┐ quality: 0.65        │    ║
║                 │   │    │ ③ Mind Memories     │─────────────┤        │    ║
║                 │   │    │   mind_bridge.py     │             │        │    ║
║                 │   │    └─────────────────────┘             │        │    ║
║                 │   │    ┌─────────────────────┐ quality: 0.65        │    ║
║                 │   │    │ ④ Domain Chips      │─────────────┤        │    ║
║                 │   │    │   chip_insights/     │             │        │    ║
║                 │   │    └─────────────────────┘             │        │    ║
║                 │   │    ┌─────────────────────┐ quality: 0.75        │    ║
║                 │   │    │ ⑤ Trigger Rules     │─────────────┤        │    ║
║                 │   │    │   (if/then per tool) │             │        │    ║
║                 │   │    └─────────────────────┘             │        │    ║
║                 │   │    ┌─────────────────────┐ quality: 0.85        │    ║
║                 │   │    │ ⑥ Replay History    │─────────────┤        │    ║
║                 │   │    │   (past patterns)    │             │        │    ║
║                 │   │    └─────────────────────┘             │        │    ║
║                 │   │    ┌─────────────────────┐ quality: 0.40        │    ║
║                 │   │    │ ⑦ Memory Banks      │─────────────┤        │    ║
║                 │   │    │   memory_banks.py    │             │        │    ║
║                 │   │    └─────────────────────┘             │        │    ║
║                 │   │                                        │        │    ║
║                 │   │    3-Factor Ranking:                    │        │    ║
║                 │   │    score = 0.50*relevance               │        │    ║
║                 │   │          + 0.25*quality                 │        │    ║
║                 │   │          + 0.25*trust                   │        │    ║
║                 │   │                                        │        │    ║
║                 │   │    Returns top 8 items ◄───────────────┘        │    ║
║                 │   └───────────────────────────────┬─────────────────┘    ║
║                 │                                   │                      ║
║                 └──────────────┬─────────────────────┘                      ║
║                                │                                            ║
║                                ▼                                            ║
║   ┌─────────────────────────────────────────────────────────┐               ║
║   │ 4. QUALITY GATE                                         │               ║
║   │    advisory_gate.py (757 lines)                         │               ║
║   │                                                         │               ║
║   │    For each advice item, assigns authority:              │               ║
║   │    ≥ 0.95  →  BLOCK   (EIDOS blocks action)            │               ║
║   │    ≥ 0.80  →  WARNING  [SPARK ADVISORY]                │               ║
║   │    ≥ 0.48  →  NOTE     [SPARK]          ◄── most common│               ║
║   │    ≥ 0.27  →  WHISPER  (spark: ...)                    │               ║
║   │    < 0.27  →  SILENT   (suppressed)                    │               ║
║   │                                                         │               ║
║   │    Filters:                                             │               ║
║   │    ✗ Already shown (TTL per-source: 210-420s)          │               ║
║   │    ✗ Tool cooldown (per-tool: 7-18s)                   │               ║
║   │    ✗ Budget cap (dynamic: 2-4 per call)                │               ║
║   │    ✗ Obvious from context                               │               ║
║   │                                                         │               ║
║   │    Output: 0-4 items that pass all filters              │               ║
║   └─────────────────────┬───────────────────────────────────┘               ║
║                         │                                                   ║
║              ┌──────────┴──────────┐                                        ║
║              │                     │                                        ║
║         (0 items)            (1-2 items)                                    ║
║              │                     │                                        ║
║              ▼                     ▼                                        ║
║     return None           ┌─────────────────────────────────┐               ║
║     (no output)           │ 5. SYNTHESIS                    │               ║
║                           │    advisory_synthesizer.py      │               ║
║                           │    (954 lines)                  │               ║
║                           │                                 │               ║
║                           │  Tier 1 (Default, <5ms):        │               ║
║                           │  Template: "When {X}: {Y}"      │               ║
║                           │                                 │               ║
║                           │  Tier 2 (Selective, 2-8s):      │               ║
║                           │  Ollama phi4-mini rewrite       │               ║
║                           │  (only when budget allows)      │               ║
║                           └──────────────┬──────────────────┘               ║
║                                          │                                  ║
║                                          ▼                                  ║
║   ┌─────────────────────────────────────────────────────────┐               ║
║   │ 6. EMISSION                                             │               ║
║   │    advisory_emitter.py (307 lines)                      │               ║
║   │                                                         │               ║
║   │    Format by authority:                                 │               ║
║   │      WARNING → "[SPARK ADVISORY] text"                  │               ║
║   │      NOTE    → "[SPARK] text"                           │               ║
║   │      WHISPER → "(spark: text)"                          │               ║
║   │                                                         │               ║
║   │    Budget: max 500 chars                                │               ║
║   │    Fallback budget: cap=1 per window=5 calls           │               ║
║   │                                                         │               ║
║   │    ══════════════════════════════════                    │               ║
║   │    ║  sys.stdout.write(text + "\n") ║  ◄── THE OUTPUT   │               ║
║   │    ║  sys.stdout.flush()            ║                   │               ║
║   │    ══════════════════════════════════                    │               ║
║   │                                                         │               ║
║   │    Claude Code reads this as hook feedback              │               ║
║   └─────────────────────┬───────────────────────────────────┘               ║
║                         │                                                   ║
║                         ▼                                                   ║
║   ┌─────────────────────────────────────────────────────────┐               ║
║   │ 7. POST-EMISSION TRACKING                               │               ║
║   │                                                         │               ║
║   │    • Mark shown in advisory_state.py                    │               ║
║   │    • Save packet to packet_store.py                     │               ║
║   │    • Log to advisory_emit.jsonl                         │               ║
║   │    • Log to advisory_decision_ledger.jsonl              │               ║
║   └─────────────────────────────────────────────────────────┘               ║
║                                                                             ║
╚═══════════════════════════════════════════════════════════════════════════════╝
```

## Supporting Systems (Not On The Hot Path)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  SUPPORTING MODULES                                                         │
│                                                                             │
│  ┌──────────────────────────────┐   ┌──────────────────────────────┐        │
│  │ advisory_memory_fusion.py    │   │ advisory_intent_taxonomy.py  │        │
│  │ (804 lines)                  │   │ (211 lines)                  │        │
│  │                              │   │                              │        │
│  │ Combines cognitive + chips   │   │ Classifies intent family     │        │
│  │ into unified retrieval       │   │ for packet keying            │        │
│  │ Used by: advisor.py          │   │ Used by: advisory_engine.py  │        │
│  └──────────────────────────────┘   └──────────────────────────────┘        │
│                                                                             │
│  ┌──────────────────────────────┐   ┌──────────────────────────────┐        │
│  │ advisory_preferences.py      │   │ advisory_quarantine.py       │        │
│  │ (452 lines)                  │   │ (130 lines)                  │        │
│  │                              │   │                              │        │
│  │ User pref storage            │   │ Noise blacklist              │        │
│  │ CLI: spark advisory prefs    │   │ Records suppressed items     │        │
│  │ Used by: advisor.py          │   │ Used by: advisor.py          │        │
│  └──────────────────────────────┘   └──────────────────────────────┘        │
│                                                                             │
│  ┌──────────────────────────────┐   ┌──────────────────────────────┐        │
│  │ advisory_parser.py           │   │ distillation_transformer.py  │        │
│  │ (196 lines)                  │   │ (544 lines)                  │        │
│  │                              │   │                              │        │
│  │ Text parsing utilities       │   │ EIDOS → advisory quality     │        │
│  │ Used by: synthesizer         │   │ bridge (suppression rules)   │        │
│  └──────────────────────────────┘   │ Used by: advisor.py (L3895)  │        │
│                                     │ Used by: bridge_cycle.py     │        │
│  ┌──────────────────────────────┐   │ Used by: cognitive_learner   │        │
│  │ exposure_tracker.py          │   └──────────────────────────────┘        │
│  │ (290 lines)                  │                                           │
│  │                              │                                           │
│  │ Records what was shown       │                                           │
│  │ trace_id resolution          │                                           │
│  │ Used by: 8+ files            │                                           │
│  └──────────────────────────────┘                                           │
│  ┌──────────────────────────────┐   ┌──────────────────────────────┐        │
│  │ validate_and_store.py       │   │ noise_patterns.py            │        │
│  │ (unified write gate)        │   │ (shared noise patterns)      │        │
│  │                              │   │                              │        │
│  │ Routes ALL cognitive writes  │   │ Consolidated noise regex     │        │
│  │ through Meta-Ralph first     │   │ used by 5+ modules           │        │
│  │ Fail-open quarantine on err │   │ Used by: validate_and_store  │        │
│  │ Used by: bridge, hyp, agg   │   │ Used by: cognitive, meta_r   │        │
│  └──────────────────────────────┘   └──────────────────────────────┘        │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Prefetch System (Dormant Background)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  PREFETCH (enabled by default, fires on UserPromptSubmit)                   │
│                                                                             │
│  UserPromptSubmit event                                                     │
│        │                                                                    │
│        ▼                                                                    │
│  advisory_engine.py :: on_user_prompt()                                     │
│        │                                                                    │
│        ├──► advisory_prefetch_planner.py (95 lines)                         │
│        │    Predicts which tools user will call next                         │
│        │    Maps intent → likely tool set                                    │
│        │                                                                    │
│        └──► advisory_prefetch_worker.py (305 lines)                         │
│             Pre-generates packets for predicted tools                        │
│             Stores in packet_store for fast lookup                           │
│                                                                             │
│  Status: ENABLED (env SPARK_ADVISORY_PREFETCH_INLINE=1)                     │
│  Impact: Unclear — depends on intent prediction accuracy                    │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Write-Only Feedback Loops (OPEN — Data Goes In, Nothing Reads It Back)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  FEEDBACK SYSTEMS — DATA FLOWS ONE WAY                                      │
│                                                                             │
│                                                                             │
│  ┌─────────────────────────┐        ┌──────────────────────────────┐        │
│  │ implicit_outcome_        │        │ ~/.spark/advisor/             │        │
│  │ tracker.py (114 lines)   │───────►│ implicit_feedback.jsonl       │        │
│  │                          │ write  │                              │        │
│  │ Records:                 │        │ Read by:                     │        │
│  │ • advice given before    │        │ • packet_store (trace report)│        │
│  │   tool call              │        │ • observatory (display)      │        │
│  │ • tool success/failure   │        │                              │        │
│  │                          │        │ NOT read by:                 │        │
│  │ Called from:             │        │ ✗ advisory_gate.py           │        │
│  │ • observe.py (pre+post)  │        │ ✗ advisor.py _rank_score()  │        │
│  │                          │        │ ✗ advisory_engine.py         │        │
│  └─────────────────────────┘        └──────────────────────────────┘        │
│                                                                             │
│                                          ▲                                  │
│                                          │ NO FEEDBACK LOOP                 │
│                                          │ Data accumulates                 │
│                                          │ but never influences             │
│                                          │ future advice quality            │
│                                          ▼                                  │
│                                                                             │
│  ┌─────────────────────────┐        ┌──────────────────────────────┐        │
│  │ advice_feedback.py       │        │ ~/.spark/                    │        │
│  │ (386 lines)              │───────►│ advice_feedback.jsonl         │        │
│  │                          │ write  │ advice_feedback_requests.jsonl│        │
│  │ Records:                 │        │ advice_feedback_summary.json  │        │
│  │ • explicit user feedback │        │                              │        │
│  │ • feedback requests      │        │ Read by:                     │        │
│  │                          │        │ • packet_store (trace report)│        │
│  │ Called from:             │        │ • CLI (spark advice-feedback) │        │
│  │ • observe.py (legacy)    │        │                              │        │
│  │ • advisory_engine.py     │        │ NOT read by:                 │        │
│  │ • advisor.py             │        │ ✗ advisory_gate.py           │        │
│  │                          │        │ ✗ _rank_score()              │        │
│  └─────────────────────────┘        └──────────────────────────────┘        │
│                                                                             │
│  SESSION END (observe.py line 942-951):                                     │
│  ┌──────────────────────────────────────────────────────────┐               │
│  │ stderr: "[SPARK] Outcome check-in: run `spark outcome`"  │               │
│  │ stderr: "[SPARK] Advice feedback pending..."             │               │
│  │                                                          │               │
│  │ These prompt the USER to manually give feedback.         │               │
│  │ Gated by env vars (off by default).                      │               │
│  └──────────────────────────────────────────────────────────┘               │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Dead Code

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  DEAD CODE                                                                  │
│                                                                             │
│  ┌─────────────────────────────────────────────┐                            │
│  │ curiosity_engine.py (407 lines)              │                            │
│  │                                              │                            │
│  │ Tracks knowledge gaps (WHY/WHEN/HOW/WHAT)    │                            │
│  │                                              │                            │
│  │ Imported by: spark/cli.py ONLY               │                            │
│  │ Called by hot path: NEVER                     │                            │
│  │ Emits output: NEVER                          │                            │
│  │ Last meaningful use: UNKNOWN                  │                            │
│  │                                              │                            │
│  │ Verdict: DELETE or wire into opportunity      │                            │
│  │          scanner                              │                            │
│  └─────────────────────────────────────────────┘                            │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Separate System (Not Advisory)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  OPPORTUNITY SCANNER — Separate self-improvement system                     │
│                                                                             │
│  ┌──────────────────────────────┐   ┌──────────────────────────────┐        │
│  │ opportunity_scanner.py        │   │ opportunity_inbox.py          │        │
│  │ (1,562 lines)                │   │ (229 lines)                  │        │
│  │                              │   │                              │        │
│  │ Generates Socratic self-     │   │ CLI for accept/dismiss       │        │
│  │ improvement suggestions      │   │ decisions                    │        │
│  │                              │   │                              │        │
│  │ Called by: bridge_cycle.py   │   │ Called by: spark/cli.py      │        │
│  │ Also: advisor.py (source ⑧) │   │                              │        │
│  │                              │   │                              │        │
│  │ Emits to stdout: NEVER      │   │ Emits to stdout: NEVER       │        │
│  │ Stores: JSONL only           │   │                              │        │
│  └──────────────────────────────┘   └──────────────────────────────┘        │
│                                                                             │
│  NOT conflicting with [SPARK] advisory. Separate concern.                   │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Line Count Summary

```
ESSENTIAL (hot path):
  advisory_engine.py ............  2,874  ██████████████
  advisory_packet_store.py ......  3,286  ████████████████
  advisor.py ....................  5,816  █████████████████████████████
  advisory_gate.py ..............    757  ███
  advisory_emitter.py ...........    307  █
  advisory_state.py .............    427  ██
                                 ──────
                          TOTAL: 13,467 lines (~66%)

SUPPORTING (used by essential):
  advisory_synthesizer.py .......    954  ████
  advisory_memory_fusion.py .....    804  ████
  advisory_preferences.py .......    452  ██
  distillation_transformer.py ...    544  ██
  advisory_intent_taxonomy.py ...    211  █
  advisory_parser.py ............    196  █
  advisory_quarantine.py ........    130  █
  exposure_tracker.py ...........    290  █
                                 ──────
                          TOTAL:  3,581 lines (18%)

EXTRACTED FROM PACKET STORE (Phase 5 split):
  advisory_packet_llm_reranker.py   249  █
  advisory_packet_feedback.py ...   262  █
  feedback_effectiveness_cache.py   ~200 █
                                 ──────
                          TOTAL:   ~711 lines (3%)

WRITE-ONLY (open feedback loop):
  advice_feedback.py ............    386  ██
  implicit_outcome_tracker.py ...    114  █
                                 ──────
                          TOTAL:    500 lines (2%)

DORMANT (enabled but rarely fires):
  advisory_prefetch_planner.py ..     95
  advisory_prefetch_worker.py ...    305  █
                                 ──────
                          TOTAL:    400 lines (2%)

SEPARATE SYSTEM (not advisory):
  opportunity_scanner.py ........  1,562  ████████
  opportunity_inbox.py ..........    229  █
                                 ──────
                          TOTAL:  1,791 lines (9%)

DEPRECATED:
  curiosity_engine.py ...........    407  ██  (deprecated Phase 4)
                                 ──────
                          TOTAL:    407 lines (2%)

═══════════════════════════════════════
GRAND TOTAL:                   ~21,757 lines across 23 files
```
