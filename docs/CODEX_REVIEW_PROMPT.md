# Codex Review Task: Spark Intelligence Flow Evolution

## Your Role
You are reviewing a comprehensive analysis and redesign proposal for the Spark Intelligence system — a self-evolving AI learning pipeline that observes Claude Code tool usage, extracts insights, filters noise, and emits pre-tool advisory advice. The system has grown organically over months and accumulated significant redundancy, bypass paths, and architectural debt.

## What You're Reviewing

Read these files in order:

1. **`docs/INTELLIGENCE_FLOW_EVOLUTION.md`** — The main analysis document containing:
   - Current system architecture (write path + read path)
   - Meta-Ralph vs EIDOS comparison (two quality gate systems)
   - Full redundancy audit (noise filters, storage, feedback, retrieval, config)
   - Tuneable audit (127 keys → proposed 80, kill list, merge list)
   - 15 identified bypass paths where stages get skipped
   - 8 sequence issues in the advisory emission path
   - The proposed "Carmack Design" — optimal write path, read path, and effectiveness loop
   - 6 implementation batches with risk ratings

2. **`docs/ADVISORY_SYSTEM_FLOWCHART.md`** — Existing detailed flowchart of the advisory pipeline (packet store, gate, synthesis, emission)

3. **`lib/advisory_engine.py`** — The main advisory engine (~2500 lines). Focus on:
   - `on_pre_tool()` method (~lines 1435-2464) — the read path being redesigned
   - `apply_engine_config()` — hot-reload registration
   - Global dedupe, text repeat, budget exhaustion, fallback emit paths

4. **`lib/bridge_cycle.py`** — The bridge cycle (~1200 lines). Focus on:
   - `run_bridge_cycle()` — the write path being redesigned
   - How Meta-Ralph, cognitive learner, EIDOS, and chips are invoked
   - Which stages are try/except (fail-open) vs mandatory

5. **`lib/advisory_gate.py`** — The gate evaluation (~400 lines). Focus on:
   - `evaluate()` and `_evaluate_single()` — the 10-step filter sequence
   - Shown TTL, tool cooldown, budget cap, source TTL multipliers
   - How this overlaps with global_dedupe in advisory_engine.py

6. **`lib/meta_ralph.py`** — Quality gate for cognitive learnings (~1500 lines). Focus on:
   - `roast()` method — 7-dimension scoring
   - Primitive pattern detection, deduplication, auto-refinement
   - How it differs from EIDOS distillation validation

7. **`lib/advisor.py`** — Advisory retrieval engine (~5000 lines). Focus on:
   - `advise()` method — 12+ source retrieval
   - `_rank_score()` — 3-factor ranking (relevance x readiness x effectiveness)
   - `_get_cognitive_advice()`, `_get_semantic_cognitive_advice()`, `_get_cognitive_advice_keyword()` — 3 methods reading same data store

8. **`lib/cognitive_learner.py`** — Noise filtering + insight storage (~1100 lines). Focus on:
   - `_is_noise_insight()` — 41 noise patterns
   - How these overlap with Meta-Ralph's primitive patterns and primitive_filter.py

9. **`config/tuneables.json`** — Version-controlled defaults
10. **`lib/tuneables_schema.py`** — Schema definitions for all tuneable sections

## What I Want You To Do

### Part 1: Validate or Challenge the Analysis

For each section of `INTELLIGENCE_FLOW_EVOLUTION.md`, tell me:

- **Is the diagnosis correct?** Did we identify the real problems, or are we solving phantom issues?
- **Are there redundancies we MISSED?** Read the actual code — are there more overlaps not captured?
- **Are any "redundancies" actually intentional and correct?** Sometimes two systems look similar but serve genuinely different purposes. Call these out.
- **Is the Meta-Ralph vs EIDOS conclusion right?** We concluded they're complementary, not redundant. Do you agree after reading the actual code?

### Part 2: Challenge the Proposed Design

For the "Carmack Design" (Section 7):

- **Will the reorder of on_pre_tool() actually work?** Trace through the code — are there dependencies between steps that prevent reordering?
- **Is removing fallback emits safe?** The fallbacks exist for a reason. What happens when Meta-Ralph is down or cognitive learner errors out? Will the system emit ZERO advice indefinitely?
- **Is the retry queue (for fail-closed gates) worth the complexity?** Or is fail-open with good telemetry actually better for a learning system that should degrade gracefully?
- **Will merging 4 cooldown mechanisms into 2 break anything?** The current 4 serve subtly different purposes (text-level vs ID-level vs state-level vs cross-session). Can they truly be unified?
- **Is the tuneable kill list safe?** For each item we propose removing, verify it's actually dead code by grepping the codebase.
- **Does the source ranking consolidation (multiplicative to additive) lose anything?** The compound effect was maybe intentional — penalizing unreliable sources harder.

### Part 3: Find What We Missed

Read the full codebase (especially `lib/` directory) and identify:

- **More bypass paths** beyond the 15 we found
- **More dead code** beyond what we identified
- **More file redundancy** in the storage layer beyond the 38 files we cataloged
- **Any circular dependencies** between modules
- **Any race conditions** in the feedback/tracking systems (multiple writers to same files)
- **Any performance bottlenecks** we should address while redesigning

### Part 4: Propose Your Own Improvements

Based on your full review, tell me:

- **What would YOU change about our 6-batch implementation plan?** Different ordering? Different grouping? Missing batches?
- **What's the single highest-impact change** we should make first?
- **What should we explicitly NOT change** (working well, leave alone)?
- **Are there simpler alternatives** to any of our proposed changes?
- **What tests should exist** before we start modifying anything? (Safety net)

### Part 5: Risk Assessment

For each of the 6 implementation batches:
- What could go wrong?
- What's the blast radius if it breaks?
- What's the rollback story?
- What monitoring should be in place before shipping?

## Key Context

- This is a LIVE system running as Claude Code hooks — bad changes affect every coding session
- The system processes thousands of events per session through the bridge cycle
- Advisory emission happens on EVERY tool call (Read, Edit, Bash, etc.) — latency matters
- The auto-tuner modifies tuneables autonomously every 12 hours
- All changes should be behind tuneable rollback switches
- The codebase is ~100+ Python modules, ~59% test coverage
- Current advisory metrics: ~18% emit rate, ~97% follow rate, ~4194 ledger rows/24h
- Meta-Ralph quality threshold: 4.5/12 (tuneable)
- Advisory gate thresholds: WARNING 0.68, NOTE 0.36, WHISPER 0.34
- 97 environment variables currently shadow tuneables silently
- 4 cooldown mechanisms overlap: text_repeat (420s), advice_repeat (420s), shown_ttl (420s), global_dedupe (240s)
- Auto-tuner uses multiplicative source boosts (0.3x-1.6x) that compound with additive gates (min_rank_score 0.45)

## Output Format

Structure your review as:

```
## Part 1: Analysis Validation
### Correct
- ...
### Challenged
- ...
### Missed
- ...

## Part 2: Design Challenges
### Safe Changes
- ...
### Risky Changes (with alternatives)
- ...

## Part 3: Additional Findings
- ...

## Part 4: Recommendations
- ...

## Part 5: Risk Matrix
| Batch | Risk | Blast Radius | Rollback | Pre-ship Monitoring |
```

Be direct. Challenge everything. If the analysis is wrong somewhere, say so. If a proposed change will break things, explain exactly why and what to do instead. No hand-waving — cite specific files, line numbers, and function names. If you disagree with our conclusions, show the code that proves your point.
