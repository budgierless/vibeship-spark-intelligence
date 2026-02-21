# Pipeline Audit: Real Data, Real Gaps, Real Fixes

**Date**: 2026-02-21
**Method**: 3000-memory E2E benchmark through REAL production pipeline
**Input**: 1000 useful memories (11 domains) + 2000 garbage memories (8 types)

---

## The Funnel (Real Numbers)

```
Stage                    Useful    Garbage    % Useful Passed    % Garbage Blocked
-----                    ------    -------    ---------------    -----------------
Input                    1000      2000       100%               -
importance_score(>=0.65) 382       74         38.2%              96.3%
Meta-Ralph (QUALITY)     479       87         47.9%              95.7%
Cognitive (not noise)    479       78         47.9%              96.1%
Advisory retrieval       4         0          0.4%               100%
Gate emission            1         0          0.1%               100%
```

**Bottom line**: Of 1000 useful memories, only 1 reaches the user as advice (0.1%).

---

## 5 Root Causes (Benchmark-Backed)

### Root Cause 1: Cognitive Store is 62% Operational Noise

**Data**: 143 insights in production cognitive store. 89 (62.2%) are "Cycle summary:" entries.

**Examples of noise that dominate retrieval**:
- `meta_learning:cycle_summary:_edit_used_7_times` -> "Cycle summary: Edit used 7 times (100% success)"
- `meta_learning:cycle_summary:_bash_had_77%_success` -> "Cycle summary: Bash had 77% success across 13 uses"
- `meta_learning:cycle_summary:_read_had_75%_success` -> "Cycle summary: Read had 75% success across 8 uses"

**Why it matters**: These entries contain generic tool names ("Edit", "Bash", "Read"). The matching logic in `get_insights_for_context()` checks if any of the first 8 words of the insight text appear in the query. Since virtually every advisory query mentions a tool name, these 89 noise entries match EVERY query.

**Real test**: Searched for "adding rate limiting to login endpoint". Got 53 matches. The relevant test insight "Always hash passwords with bcrypt" was at position 23. Positions 1-15 were dominated by cycle summaries.

**Fix**: Clean cycle summaries from production store + prevent future accumulation.

---

### Root Cause 2: Retrieval Word-Matching is Too Broad

**Data**: `get_insights_for_context()` at `lib/cognitive_learner.py:1386-1404`

**Matching logic**:
```python
hit = (
    (ic and ic in context_lower) or                          # context field match
    (context_lower and context_lower in ic) or               # reverse context match
    any(word in context_lower for word in ii.split()[:8])    # ANY of first 8 words
)
```

**Problem**: The third condition matches if ANY single word from the insight's first 8 words appears in the query. For "Cycle summary: Edit used 7 times (100% success)", the first 8 words are: `["cycle", "summary:", "edit", "used", "7", "times", "(100%", "success)"]`.

The word "edit" matches any Edit tool query. The word "used" matches almost any English sentence.

**Fix**: Require minimum 2-word overlap, skip words < 4 chars, exclude common stopwords.

---

### Root Cause 3: Noise Filter Runs AFTER Limit Truncation

**Data**: `lib/advisor.py:2696-2742`

The advisor calls:
1. `cognitive.get_insights_for_context(context, limit=10)` -> returns top 10 by match_score
2. Then loops through results and calls `is_noise_insight()` to filter

**Problem**: limit=10 is applied BEFORE noise filtering. If 8 of the top 10 are noise, after filtering only 2 useful results remain. But 20+ useful results at positions 11-30 were never fetched.

**Fix**: Increase fetch limit to 30, filter after.

---

### Root Cause 4: importance_score() is Keyword-Only

**Data**: `lib/memory_capture.py:126-160`

Scores memories using three keyword lists:
- HARD_TRIGGERS: "remember this" (1.0), "always" (0.65), "never" (0.65)
- SOFT_TRIGGERS: "i prefer" (0.55), "must" (0.4), "should" (0.25)
- DECISION_MARKERS: "let's do it" (0.25), "ship it" (0.25)

AUTO_SAVE_THRESHOLD = 0.65

**Problem**: Useful insights without trigger phrases score 0.0. Example: "Memory leaks in React often come from useEffect cleanup functions not being implemented" scores 0.0.

**Result**: 618/1000 (61.8%) useful memories blocked.

**Fix**: Add semantic signals (technical terms, causal language, quantitative evidence).

---

### Root Cause 5: Meta-Ralph Garbage Leakage (4.3%)

**Breakdown**:
| Type | Leaked | Total | Rate |
|------|--------|-------|------|
| tool_sequence | 23 | 400 | 5.8% |
| duplicate | 17 | 200 | 8.5% |
| platitude | 14 | 300 | 4.7% |
| system_noise | 12 | 200 | 6.0% |
| timing_metrics | 9 | 300 | 3.0% |
| transcript | 8 | 200 | 4.0% |
| code_snippet | 4 | 200 | 2.0% |
| reaction_noise | 0 | 200 | 0.0% |

**Fix**: Add explicit negative scoring for tool sequences, platitudes, and system noise in `_score_learning()`.

---

## Advisory Retrieval Details (26 Real Queries)

Only 3/26 queries matched benchmark data:
- "debugging flaky test CI" -> timezone insight (1 match)
- "fixing memory leak React" -> useEffect cleanup (2 matches)
- "optimizing page load lazy loading" -> lazy loading stats (1 match)

23 other queries: 0 matches. Keyword matching can't bridge semantic gaps.

---

## Score Distribution (Meta-Ralph)

```
Score  Count   Category
  1    1507    Noise/primitive
  2     929    Below threshold
  3      62    Below threshold
  4     117    Near threshold
  5      67    Above threshold
  6      14    Quality
  7      96    Quality
  8     206    Quality
  9       2    High quality
```

Bimodal: peak at 1-2 (noise) and secondary peak at 8 (well-structured useful content).

---

## Previous 20-Issue Audit Fixes (All Implemented 2026-02-21)

| # | Issue | File(s) | Fix | Status |
|---|-------|---------|-----|--------|
| 1 | auto_link interval 300s | prediction_loop.py | 300->60s, limit 80->200 | DONE |
| 2 | Validation triggers narrow | validation_loop.py | +13 POS, +9 NEG words | DONE |
| 3 | Implicit tracker missing | implicit_outcome_tracker.py | CREATE new file + wire | DONE |
| 4 | Meta-Ralph 7.15% pass | tuneables.json | threshold 4.5->3.8 | DONE |
| 5 | Advisory gate harsh defaults | advisory_gate.py | emit 1->2, cool 90->30 | DONE |
| 6 | Mind 0% effective | tuneables.json, advisor.py | Enable, boost 0->0.2 | DONE |
| 7 | Promoter thresholds low | promoter.py, tuneables.json | 0.7->0.80, 3->5 vals | DONE |
| 8 | 0 EIDOS policies | distillation_engine.py | Add _generate_policy() | DONE |
| 9 | Distillation every 10 cycles | bridge_cycle.py | %10->%5 | DONE |
| 10 | Chip cooldown 30min | chip_merger.py | 1800->600s | DONE |
| 11 | Auto-save threshold 0.82 | memory_capture.py | 0.82->0.65 | DONE |
| 12 | Sync targets disabled | tuneables.json | mode core->all | DONE |
| 13 | 67% meta_learning, 2% wisdom | cognitive_learner.py | Add promote_to_wisdom() | DONE |
| 14 | Predictions never expire | prediction_loop.py | Add cleanup function | DONE |
| 15 | Distillation gate strict | distillation_engine.py | min len 30->20 | DONE |
| 16 | Mixed patterns rejected | distiller.py | Add SHARP_EDGE for mixed | DONE |
| 17 | 25 processes / 2.2GB RAM | -- | Audit-only, document | DONE |
| 18 | No demotion of stale promos | bridge_cycle.py | Add demotion pass | DONE |
| 19 | implicit_feedback.jsonl empty | -- | Fixed by Issue 3 | DONE |
| 20 | Prediction budget 180, no dedup | prediction_loop.py | 180->50, add dedup | DONE |

---

## NEW Benchmark-Driven Fixes (Issues 21-25)

| # | Issue | Root Cause | File(s) | Fix | Status |
|---|-------|-----------|---------|-----|--------|
| 21 | 62% cognitive store is noise | Cycle summaries saved as insights | cognitive_learner.py | Clean store + guard add_insight() | DONE |
| 22 | Word-matching too broad | Single common word matches all queries | cognitive_learner.py | Min 2-word match, skip stopwords | DONE |
| 23 | Noise filter after truncation | limit=10 before is_noise_insight() | advisor.py | limit 10->30 | DONE |
| 24 | importance_score keyword-only | No semantic signals | memory_capture.py | Add technical/causal/quant scoring | DONE |
| 25 | Meta-Ralph garbage leakage 4.3% | No negative scoring for noise patterns | meta_ralph.py | Penalize tool sequences, platitudes | DONE |

---

## Before/After: Cognitive Retrieval (Critical Path)

**Benchmark**: 557 test memories injected, 49 real advisory queries run through production `on_pre_tool()`.

| Metric | BEFORE (pre-fix 21-25) | AFTER (post-fix 21-25) | Delta |
|--------|----------------------|----------------------|-------|
| Cognitive source items | 0 | 43 | **0 -> 43 (UNBLOCKED)** |
| Queries with any advice | 49/49 | 45/49 | -4 (expected, noise removed) |
| Bench items in advice | 0/64 | 43/94 | **0% -> 46%** |
| EIDOS items | 49 | 36 | -13 (less dominant now) |
| Trigger items | 15 | 15 | unchanged |
| Cognitive store noise | 89/143 (62%) | 0/55 (0%) | **-62pp** |
| Avg latency | 69ms | 78ms | +9ms (negligible) |

**Key result**: The cognitive retrieval path went from DEAD (0 items) to the DOMINANT advisory source (43 items). Before, ALL advice came from EIDOS distillations and trigger rules because cognitive was drowned by cycle summary noise. Now cognitive is the primary source.
