# Spark Intelligence: Comprehensive Production Readiness Analysis

**Date:** 2026-02-05
**Analyst:** Claude Opus 4.6
**Scope:** Full codebase audit - 100+ Python modules, 20 test files, 11 chips, 10+ documentation files

---

## Executive Summary

Spark Intelligence is a **remarkably ambitious and well-architected self-evolving AI learning system**. After analyzing every module, every tunable, every test, and every documentation file, here is the verdict:

**Production Readiness: 7.5/10** - Strong foundation, specific gaps to close.

The system successfully implements what most AI learning frameworks only theorize: mandatory outcome tracking, enforced memory binding, multi-layer noise filtering (74+ patterns), and domain-specific intelligence chips. The core pipeline works. The architecture is sound. What remains is fine-tuning, test coverage for newer subsystems, and closing a few integration gaps.

---

## 0. Verification Update (2026-02-06, Codex Pass #1)

This section supersedes stale point-in-time numbers below. The original analysis remains useful, but several metrics and a few recommendations are now outdated.

### Evidence Sources Used

- Code validation: `lib/*.py` (focus on `lib/eidos/models.py`, `lib/queue.py`, `lib/pipeline.py`, `lib/advisor.py`)
- Runtime state: `~/.spark/*` (`eidos.db`, `meta_ralph/*`, `advisor/effectiveness.json`, `chip_insights/*.jsonl`)
- Test status: `python -m pytest -q`
- Integration check: `python -m lib.integration_status`

### Corrected Live Snapshot (2026-02-06)

| Metric | Previous in doc | Verified now | Status |
|--------|------------------|--------------|--------|
| Quality Rate (Meta-Ralph) | 47.1% | 23.95% (40/167) | LOWER than target band |
| Total Insights Roasted | 399 | 167 | Lower active sample |
| Quality Passed (>=4/10) | 188 | 40 | Consistent with 23.95% pass |
| Primitive Rejected | 76 | 24 | Filtering active |
| Cognitive Insights Stored | 1,564 | 385 keys (`cognitive_insights.json`) | Structure changed (dict map) |
| Chip Insights Generated | 765,997 | 1,261,045 JSONL rows (~977 MB) | VERY HIGH volume |
| EIDOS Distillations | 7 | 2 (`eidos.db`) | CRITICAL low distillation |
| Outcomes Tracked | 355 | 500 (rolling records in Meta-Ralph) | Active loop exists |
| Outcomes Acted On | 5 | 417 (`meta_ralph.get_stats()`) | Action link exists, but quality low |
| Integration Tests | 8/8 passing | 103 passed, 27 warnings | Strong pass, warning debt |

### What Is Outdated and Corrected

1. `Budget.from_dict` mismatch (max_file_touches 2 vs 3) is already fixed in `lib/eidos/models.py`.
2. "Create tuneables.json" is no longer needed. `~/.spark/tuneables.json` exists and is wired.
3. Queue event handling improved: overflow sidecar prevents lock-contention drops in `lib/queue.py`.
4. Pipeline "double sort redundancy" claim is stale: one pass classifies counts, one pass builds processing order.
5. Outcome-to-action is no longer "missing"; the bigger issue is **outcome quality/effectiveness**, not acted-on rate.

### New Critical Findings (Not Captured in Original Draft)

1. **Advisor effectiveness counters are logically invalid**: `total_followed` is greater than `total_advice_given` in `~/.spark/advisor/effectiveness.json`. This breaks trust in advice ROI metrics.
2. **Integration health is degraded** (`python -m lib.integration_status`): Pre/Post hook coverage was partial in the latest window (`pre=0`, `post=1`).
3. **EIDOS compounding is far below target**: north star compounding rate is 2.0% vs 40% target (`lib.eidos.metrics`).
4. **Distillation output is minimal**: only 2 distillations, and currently 0% helped effectiveness.

### Updated Priority Queue (Current Reality)

#### P0 - Data Integrity and Learning Signal Trust

1. Fix advisor effectiveness accounting so `total_followed <= total_advice_given` is always invariant.
2. Add invariant checks + repair script for corrupted historical effectiveness counters.
3. Add Meta-Ralph dashboard guardrails to flag impossible counters immediately.

#### P1 - Learning Loop Effectiveness

4. Increase distillation yield (still critical) and verify with weekly EIDOS metrics trend.
5. Tighten chip capture volume at source (especially `bench_core`) before further promotion tuning.
6. Raise quality pass rate back into target range (40-55%) by reducing primitive noise at ingest.

#### P2 - Reliability and Test Hygiene

7. Resolve pytest warnings (`PytestReturnNotNoneWarning`) in legacy tests.
8. Add integration test coverage for pre/post hook symmetry.
9. Keep this document as a living analysis with dated verification blocks per iteration.

### Implementation Update (2026-02-05, Codex Pass #2)

This pass implemented and validated the current 9-point optimization set focused on runtime throughput and queue/store reliability without feature removal:

1. Queue logical-head consume path (`~/.spark/queue/state.json`) with periodic compaction to avoid full-file rewrites on every consume.
2. Queue active-size counting + short TTL count cache + forced uncached count on rotation decisions.
3. Queue-aware tail reads with optional start offset for active-window operations.
4. Bridge-cycle batch/deferred persistence for `lib/cognitive_learner.py` and `lib/meta_ralph.py`.
5. Bridge-cycle single-pass event classification reused across tastebank, content learning, chips, and cognitive signals.
6. Advisor cache-key hardening (hash of tool/context/task/input hints) + tail-based recent-advice reads.
7. Memory bank JSONL reads switched to bounded tail scanning instead of full-file loads.
8. Mind bridge health/backoff/timeouts tuned for non-blocking behavior under Mind outage.
9. Chip runtime/store size-based JSONL rotation to cap unbounded growth.

Additional consistency fix included in the same sweep:
- `lib/eidos/models.py` `Budget.from_dict(max_file_touches)` aligned to `3`.

Validation run summary:
- `python -m py_compile` on modified runtime modules: PASS
- `python -m pytest -q tests/test_queue.py tests/test_queue_concurrency.py tests/test_bridge_starvation.py tests/test_10_improvements.py`: PASS (22 passed)
- `python -m pytest -q tests/test_meta_ralph.py tests/test_learning_utilization.py tests/test_pipeline_health.py`: PASS (7 passed)
- `python -m pytest -q tests/test_skills_registry.py tests/test_orchestration.py`: PASS (4 passed)

---

## Table of Contents

0. [Verification Update (2026-02-06, Codex Pass #1)](#0-verification-update-2026-02-06-codex-pass-1)
0.1 [Implementation Update (2026-02-05, Codex Pass #2)](#implementation-update-2026-02-05-codex-pass-2)
1. [System Health Snapshot](#1-system-health-snapshot)
2. [Architecture Assessment](#2-architecture-assessment)
3. [Tunable Parameter Optimization](#3-tunable-parameter-optimization)
4. [Code Cleanup Targets](#4-code-cleanup-targets)
5. [Pipeline Gap Analysis](#5-pipeline-gap-analysis)
6. [Chip System Review & Recommendations](#6-chip-system-review--recommendations)
7. [Test Coverage & Quality](#7-test-coverage--quality)
8. [Critical Bug Risks](#8-critical-bug-risks)
9. [Production Hardening Checklist](#9-production-hardening-checklist)
10. [Recommended Tunable Changes](#10-recommended-tunable-changes)
11. [Priority Action Items](#11-priority-action-items)

---

## 1. System Health Snapshot

### Current Metrics (Live Data)

| Metric | Value | Health |
|--------|-------|--------|
| Quality Rate (Meta-Ralph) | 47.1% | GOOD - Sweet spot between permissive and strict |
| Total Insights Roasted | 399 | Active system |
| Quality Passed (>=4/10) | 188 | ~47% pass rate |
| Primitive Rejected | 76 | Noise filter working |
| Cognitive Insights Stored | 1,564 | Healthy accumulation |
| Chip Insights Generated | 765,997 | Prolific (see concerns below) |
| EIDOS Distillations | 7 | LOW - needs attention |
| Mind Memories | 32,335 | Rich knowledge base |
| Outcomes Tracked | 355 | Good feedback loop |
| Outcomes Acted On | 5 | LOW - gap in action loop |
| Integration Tests | 8/8 passing | ALL GREEN |

### Key Ratios

| Ratio | Value | Assessment |
|-------|-------|------------|
| Signal-to-Noise | 1:5.2 (raw) -> 5x filtered | Excellent filtering |
| Insight-to-Action | 5/355 = 1.4% | CRITICAL GAP - insights not driving actions |
| Distillation-to-Insight | 7/1,564 = 0.4% | LOW - distillation engine underperforming |
| Chip-to-Cognitive Ratio | 765K:1.5K = 500:1 | TOO HIGH - chips generating noise volume |

---

## 2. Architecture Assessment

### What's Working Well (Strengths)

**1. Multi-Layer Quality Control (10/10)**
The 3-tier noise filtering is exceptional:
- Layer 1: Meta-Ralph quality gate (5 dimensions, score >= 4/10)
- Layer 2: Cognitive learner noise filter (41 hardcoded patterns)
- Layer 3: Promoter operational filter (33 patterns)
- Combined: 74+ distinct noise patterns

This is genuinely world-class for an intelligence system. Most systems have one filter; you have three independent layers.

**2. EIDOS Vertical Loop (9/10)**
The mandatory `Action -> Prediction -> Outcome -> Evaluation -> Distillation -> Reuse` loop is the right design. The Step Envelope requiring intent, prediction, and evaluation before/after every action is exactly what makes learning real rather than decorative.

**3. Tuneable Architecture (9/10)**
Everything flows through `~/.spark/tuneables.json` with sensible fallback defaults in code. This is production-grade configuration management.

**4. Event Queue Design (8/10)**
Append-only JSONL with rotation, overflow sidecar, and priority classification is solid. The <10ms capture target respects the hook's performance constraints.

**5. Chip System Design (8/10)**
The YAML chip specification is elegant. Triggers -> Observers -> Learners -> Outcomes -> Insights is a clean pipeline. The domain-specific intelligence concept is the right way to scale learning across verticals.

### Architecture Concerns

**1. Distillation Engine Underperforming**
Only 7 distillations from 1,564 cognitive insights = 0.4% conversion. The distillation engine should be generating 10-50x more reusable rules. This is the biggest gap in the learning loop.

**2. Outcome-to-Action Gap**
5 outcomes acted on out of 355 tracked = 1.4%. Insights are being stored but not changing behavior. The advisor retrieval loop needs strengthening.

**3. Chip Insight Volume**
765,997 chip insights is extreme. Most of these are likely low-value telemetry from the spark-core chip. Need aggressive filtering at the chip level, not just at promotion time.

**4. File-Based Concurrency**
Using file locks for the event queue works at current scale but is a bottleneck for high-throughput scenarios. The 50ms lock timeout causes silent event drops.

---

## 3. Tunable Parameter Optimization

### Parameters I Recommend Changing

Based on analyzing the full pipeline, current metrics, and the gap between insight storage and insight utilization:

#### 3.1 EIDOS Budget (models.py defaults)

| Parameter | Current | Recommended | Rationale |
|-----------|---------|-------------|-----------|
| `max_steps` | 25 | 30 | 25 is slightly restrictive for complex debugging tasks |
| `max_time_seconds` | 720 (12m) | 900 (15m) | 12 min cuts off complex multi-file tasks |
| `max_retries_per_error` | 2 | 2 | Keep - forces diagnostic mode appropriately |
| `max_file_touches` | 3 | 3 | Keep - prevents thrashing |
| `no_evidence_limit` | 5 | 4 | Lower to force DIAGNOSE phase sooner - prevents drift |

**Rationale:** The budget system is well-calibrated overall. The `no_evidence_limit` reduction from 5 to 4 is the key change - forcing earlier diagnostic reflection when the system is spinning without learning.

#### 3.2 Meta-Ralph Quality Gate

| Parameter | Current | Recommended | Rationale |
|-----------|---------|-------------|-----------|
| `QUALITY_THRESHOLD` | 4 | 4 | Keep - 47% pass rate is ideal sweet spot |
| `NEEDS_WORK_THRESHOLD` | 2 | 2 | Keep - appropriate |
| `MIN_OUTCOME_SAMPLES` | 5 | 3 | Lower to start quality feedback sooner |
| `MIN_TUNEABLE_SAMPLES` | 50 | 30 | Lower to enable auto-tuning faster |
| `MIN_SOURCE_SAMPLES` | 15 | 10 | Enable per-source quality analysis earlier |

**Rationale:** The quality threshold at 4/10 produces a 47% pass rate which is a healthy balance. The statistical minimums are too conservative - the system has been running long enough that lowering these will unlock earlier feedback loops.

#### 3.3 Advisor System

| Parameter | Current | Recommended | Rationale |
|-----------|---------|-------------|-----------|
| `MIN_RELIABILITY_FOR_ADVICE` | 0.5 | 0.45 | Slightly more inclusive to surface more advice |
| `MAX_ADVICE_ITEMS` | 8 | 6 | Reduce advice volume for focus |
| `ADVICE_CACHE_TTL_SECONDS` | 120 | 180 | Longer cache reduces computation |
| `MIN_RANK_SCORE` | 0.35 | 0.40 | Higher threshold drops low-quality advice |

**Rationale:** The advisor is the bridge between insights and actions. The 1.4% action rate suggests it's either not surfacing enough advice or the advice isn't actionable enough. Lowering the reliability floor while raising the rank score floor will surface more candidates but only keep the best ones.

#### 3.4 Semantic Retrieval

| Parameter | Current | Recommended | Rationale |
|-----------|---------|-------------|-----------|
| `min_similarity` | 0.58 | 0.55 | Slightly broader recall |
| `weight_outcome` | 0.35 | 0.40 | Weight successful insights more heavily |
| `weight_recency` | 0.1 | 0.15 | Slightly favor recent context |
| `mmr_lambda` | 0.5 | 0.6 | Favor relevance slightly over diversity |
| `category_caps.meta_learning` | 1 | 2 | Allow 2 meta-learning insights |

**Rationale:** The semantic retrieval system needs to surface more relevant, successful insights. Increasing outcome weight from 0.35 to 0.40 will better prioritize insights that have proven useful. The `meta_learning` cap of 1 is too restrictive - meta-insights about how the system learns are valuable.

#### 3.5 Pattern Detection

| Parameter | Current | Recommended | Rationale |
|-----------|---------|-------------|-----------|
| `CONFIDENCE_THRESHOLD` | 0.60 | 0.55 | Catch more early-stage patterns |
| `DISTILLATION_INTERVAL` | 20 | 15 | Run distillation more frequently |
| `DEDUPE_TTL_SECONDS` | 600 | 600 | Keep - 10 min window is appropriate |

**Rationale:** Only 7 distillations is far too few. Lowering the confidence threshold and running distillation more frequently should increase the rate of rule extraction.

#### 3.6 Promotion Thresholds

| Parameter | Current | Recommended | Rationale |
|-----------|---------|-------------|-----------|
| `DEFAULT_PROMOTION_THRESHOLD` | 0.65 | 0.60 | Slightly lower to increase learning velocity |
| `DEFAULT_MIN_VALIDATIONS` | 2 | 2 | Keep - minimum 2 validations is right |
| `DEFAULT_CONFIDENCE_FLOOR` | 0.90 | 0.88 | Very slight reduction for fast-track |
| `DEFAULT_MIN_AGE_HOURS` | 2.0 | 1.5 | Reduce settling period |
| `CLAUDE.md budget` | 40 | 50 | Increase budget for richer context |
| `TOOLS.md budget` | 25 | 35 | More tool-specific insights |

**Rationale:** The promotion pipeline is slightly too conservative. The system has strong noise filters, so we can afford to lower the reliability threshold slightly and increase the doc budgets.

---

## 4. Code Cleanup Targets

### 4.1 Safe to Remove / Simplify

**1. `lib/eidos/models.py` line 127 - Budget.from_dict default mismatch**
```python
# Current: max_file_touches defaults to 2 in from_dict
max_file_touches=data.get("max_file_touches", 2),
# But the class default is 3
max_file_touches: int = 3
```
**Fix:** Change from_dict default from 2 to 3 to match class default.

**2. `lib/pipeline.py` - Double sorting of processing order**
Lines ~598-614 sort events twice. The second sort is redundant.

**3. `lib/queue.py` - Silent event drops in quick_capture()**
Line ~137 silently swallows failures. At minimum, should increment a dropped counter for observability.

**4. `lib/advisor.py` - Dead source boost entries**
The source boost multipliers include entries for sources that may not be active. Clean up unused source entries.

**5. `hooks/observe.py` - Hardcoded tool baselines**
Lines 223-249 hardcode success baselines per tool. These should be loaded from tuneables.json or learned from data.

### 4.2 Unnecessary Code Patterns

**1. Repeated tool name string matching**
Throughout `pipeline.py`, `observe.py`, and `cognitive_learner.py`, tool names like "Edit", "Read", "Bash", "Glob", "Grep" are matched as string literals. Should be centralized as a constant set.

**2. Multiple JSON file writes for outcome tracking**
`meta_ralph.py` uses `_atomic_write_json()` which creates many temp files. Consider consolidating outcome storage.

**3. Redundant cognitive signal extraction**
`bridge_cycle.py` line ~162 extracts cognitive signals from already-processed events. This duplicates work that the pipeline already does.

### 4.3 Do NOT Remove (Looks Unnecessary But Isn't)

- `lib/primitive_filter.py` - Separate from cognitive_learner noise filter, used in different contexts
- `lib/resonance.py` + `lib/spark_voice.py` - Internal state calibration, part of self-evolution design
- `lib/eidos/minimal_mode.py` - Fallback when EIDOS is disabled, needed for robustness
- `build/` directory artifacts - Excluded from runtime, can be ignored

---

## 5. Pipeline Gap Analysis

### GAP 1: Distillation Rate (CRITICAL)

**Problem:** 7 distillations from 1,564 insights = 0.4% conversion rate.
**Target:** 5-10% conversion rate (78-156 distillations).
**Root Cause:** Distillation only runs every 20 events AND requires completed episodes. If episodes aren't completing properly, distillation never fires.
**Fix:**
1. Lower DISTILLATION_INTERVAL from 20 to 15
2. Add standalone distillation that doesn't require episode completion
3. Run periodic batch distillation over accumulated insights

### GAP 2: Outcome-to-Action Loop (CRITICAL)

**Problem:** 5 of 355 outcomes actually changed behavior = 1.4%.
**Target:** >20% of outcomes should influence next actions.
**Root Cause:** Outcomes are tracked but the advisor doesn't weight them strongly enough when generating advice.
**Fix:**
1. Increase `weight_outcome` in semantic retrieval from 0.35 to 0.40
2. Add "hot outcomes" - recent outcomes get temporary priority boost in advisor
3. Track whether advice was followed and correlate with outcomes

### GAP 3: Chip Insight Volume Control (HIGH)

**Problem:** 765,997 chip insights is 500x the cognitive insight count.
**Root Cause:** spark-core chip triggers on nearly every tool event, generating massive volumes of low-value telemetry.
**Fix:**
1. Add chip-level noise filter BEFORE storing to chip_insights/
2. Raise chip merger min_confidence from 0.7 to 0.8
3. Add chip insight rotation (keep last N per chip, not unlimited)
4. Add chip-level DISTILLATION_INTERVAL similar to pattern detection

### GAP 4: EIDOS Episode Completion Rate (HIGH)

**Problem:** Only 7 distillations implies very few episodes completing the full lifecycle.
**Root Cause:** STALE_EPISODE_THRESHOLD_S at 1800 (30 min) means many episodes are abandoned before reaching CONSOLIDATE phase.
**Fix:**
1. Track episode completion rate as a metric
2. Auto-consolidate stale episodes instead of just abandoning them
3. Extract partial distillations from incomplete episodes

### GAP 5: Semantic Deduplication (MEDIUM)

**Problem:** No semantic deduplication for similar insights. Only hash-based exact dedup exists.
**Root Cause:** Semantic similarity comparison not integrated at storage time.
**Fix:**
1. Use the existing embedding infrastructure to check similarity before storing
2. Merge similar insights instead of storing duplicates
3. Threshold at 0.92 cosine similarity (already configured but not enforced at write)

### GAP 6: Error Path Resilience (MEDIUM)

**Problem:** No handling for corrupted JSON files, stale locks, or database corruption.
**Root Cause:** Happy-path development focus.
**Fix:**
1. Add JSON parse error recovery (skip corrupted lines, log warning)
2. Add stale lock detection (lock older than 5 seconds = force release)
3. Add database integrity check on startup

### GAP 7: Trace Context Enforcement (LOW)

**Problem:** trace_id propagation is optional (SPARK_TRACE_STRICT=1 not enabled by default).
**Root Cause:** Design choice for flexibility, but weakens learning attribution.
**Fix:** Consider enabling SPARK_TRACE_STRICT=1 for production to ensure all learning can be traced back to actions.

---

## 6. Chip System Review & Recommendations

### Current State

**11 chips defined, ~3 activated:**
| Chip | Status | Domain | Assessment |
|------|--------|--------|------------|
| spark-core | AUTO, Active | coding | GOOD but too noisy - generates bulk of 765K insights |
| vibecoding | opt-in | velocity | GOOD design, useful for engineering delivery |
| game-dev | opt-in | games | GOOD for game projects |
| marketing | opt-in | campaigns | GOOD for marketing work |
| market-intel | opt-in | market research | GOOD for competitive analysis |
| moltbook | opt-in | moltbook | Platform-specific, useful when relevant |
| biz-ops | opt-in | business | GOOD for business operations |
| bench-core | opt-in | benchmarking | USEFUL for tool performance tracking |
| examples/marketing-growth | opt-in | growth | Template/example - good reference |
| examples/product-development | opt-in | product | Template/example - good reference |
| examples/sales-intelligence | opt-in | sales | Template/example - good reference |

### Chip Effectiveness Assessment

**spark-core chip (PRIMARY CONCERN):**
- Triggers on almost every tool event ("worked because", "failed because", etc.)
- Generates the vast majority of chip insights
- Most of these are LOW VALUE operational telemetry
- **Recommendation:** Add tighter trigger patterns. Instead of "worked because" (matches everything), use "worked because of the" or "this worked because" with minimum 50 character context requirement.

**Domain chips (game-dev, marketing, biz-ops):**
- Well-designed with specific triggers
- Should be activated more proactively based on project context
- **Recommendation:** Auto-activate domain chips when project_context detects the domain, instead of requiring manual opt-in.

**bench-core chip:**
- Useful but generates timing telemetry
- **Recommendation:** Add explicit noise filter for timing metrics within the chip itself.

### Chip System Improvement Recommendations

**1. Per-Chip Noise Filtering (HIGH PRIORITY)**
Add a `noise_patterns` section to chip YAML spec:
```yaml
noise_patterns:
  - "status=success"
  - "tool_name="
  - "triggered by 'post_tool"
```
Filter BEFORE storing to chip_insights, not after.

**2. Chip Insight Rotation (HIGH PRIORITY)**
Implement per-chip JSONL rotation at 10,000 lines (not unlimited growth).
Current: spark-core.jsonl is likely hundreds of MB.
Target: Each chip insight file stays under 5MB.

**3. Auto-Activation Based on Domain Detection (MEDIUM)**
When `lib/cognitive_signals.py` detects a domain (game_dev, fintech, marketing), automatically activate the corresponding chip. Currently requires manual `spark chips activate`.

**4. Chip Quality Scoring Dashboard (MEDIUM)**
Track per-chip:
- Insights generated per hour
- Insights promoted (passed all filters)
- Insights acted on (influenced behavior)
- Cost ratio: generated / promoted

**5. Provisional Chip Discovery (LOW)**
The `~/.spark/provisional_chips/` directory is for auto-generating chips from frequent patterns. This is a great concept but needs a minimum evidence threshold before creating a provisional chip (suggest: 50+ pattern occurrences across 3+ sessions).

**6. Chip Evolution Tuning (LOW)**
The evolution config should deprecate trigger patterns that have `matches >= 10 AND value_ratio < 0.2`. Verify this is actually running.

---

## 7. Test Coverage & Quality

### Coverage Summary

| Category | Modules | Tests | Coverage | Risk |
|----------|---------|-------|----------|------|
| Meta-Ralph | 1 | 6 | 100% | LOW |
| Queue | 1 | 11 | 100% | LOW |
| Pattern Detection | 5+ | 12 | 100% | LOW |
| Content Learning | 1 | 23 | 100% | LOW |
| Events | 1 | 8 | 100% | LOW |
| Bridge/Pipeline | 3 | 8 | 67% | MEDIUM |
| Cognitive Learning | 2 | 8 | 50% | MEDIUM |
| EIDOS Store | 14 | 1 | 7% | HIGH |
| Chips System | 8 | 1 | 12% | HIGH |
| Advisor | 1 | 1 | 10% | HIGH |
| Scoring Modules | 4 | 0 | 0% | CRITICAL |
| Hooks | 2 | 0 | 0% | HIGH |
| Promoter | 1 | 0 | 0% | HIGH |
| **Overall** | **~100** | **75+** | **~59%** | **MODERATE** |

### Critical Test Gaps for Production

**1. Scoring modules have ZERO tests:**
- `importance_scorer.py` - Drives all importance decisions
- `contradiction_detector.py` - Detects conflicting insights
- `novelty_detector.py` - Determines if insights are new
- `curiosity_engine.py` - Generates exploration questions

**2. EIDOS subsystem at 7% coverage:**
- 14 Python files in `lib/eidos/`
- Only tested through integration tests
- No unit tests for distillation, control plane, guardrails, validation

**3. Chips system at 12% coverage:**
- 8 Python files in `lib/chips/`
- No tests for loader, evolution, runtime, scoring

**4. 4 test files are scripts (not pytest-discoverable):**
- test_10_improvements.py
- test_cognitive_capture.py
- test_learning_utilization.py
- test_pipeline_health.py

### What's Excellent

- **Concurrency testing (10/10)** - Queue concurrent reads/writes thoroughly tested
- **Test isolation (10/10)** - All tests properly monkeypatch paths, no ~/.spark pollution
- **Pattern detection coverage (9/10)** - All 5 detector types covered
- **Integration testing (9/10)** - End-to-end pipeline validation with 8 test areas

---

## 8. Critical Bug Risks

### Risk 1: Queue Event Loss Under Concurrency (MEDIUM-HIGH)

**Location:** `lib/queue.py` line ~120
**Issue:** Lock timeout of 50ms. If the queue is busy, events are silently dropped via the overflow sidecar. But if both main queue and overflow are being written simultaneously, there's a race condition.
**Impact:** Lost learning events during high-activity periods.
**Fix:** Increase lock timeout to 200ms and add a dropped-event counter.

### Risk 2: Budget.from_dict Default Mismatch (LOW but annoying)

**Location:** `lib/eidos/models.py` line 127
**Issue:** `from_dict` defaults `max_file_touches` to 2, but class default is 3. Any episode deserialized from JSON without explicit `max_file_touches` will be more restrictive than intended.
**Fix:** Change `from_dict` default to 3.

### Risk 3: Stale Episode Accumulation (MEDIUM)

**Location:** `lib/eidos/integration.py` line 52
**Issue:** STALE_EPISODE_THRESHOLD_S = 1800 (30 min). Stale episodes are abandoned but not cleaned up or distilled from.
**Impact:** Wasted learning opportunity from incomplete episodes.
**Fix:** Auto-distill from stale episodes before abandoning them.

### Risk 4: Concurrent JSON Writes in Meta-Ralph (LOW)

**Location:** `lib/meta_ralph.py`
**Issue:** Outcome tracking writes to JSON files. Under concurrent access, could corrupt state.
**Impact:** Lost outcome data, incorrect quality scores.
**Fix:** Use SQLite for outcome tracking (already available in the stack) or add file locking.

---

## 9. Production Hardening Checklist

### Must Do (Before Production)

- [ ] **Fix Budget.from_dict default mismatch** (5 min fix)
- [ ] **Add dropped-event counter to queue** (30 min)
- [ ] **Create tuneables.json with recommended values** (see Section 10)
- [ ] **Add chip insight rotation** (prevent unbounded growth)
- [ ] **Add JSON parse error recovery in queue reader** (handle corrupted lines)
- [ ] **Lower DISTILLATION_INTERVAL to 15** (increase distillation rate)
- [ ] **Track episode completion rate as metric**

### Should Do (Production Quality)

- [ ] **Add tests for importance_scorer.py** (highest risk untested module)
- [ ] **Add tests for EIDOS core** (distillation, episodes, steps)
- [ ] **Convert 4 script-based tests to pytest** (CI/CD compatibility)
- [ ] **Create conftest.py** with shared fixtures
- [ ] **Add per-chip noise filtering before storage**
- [ ] **Auto-distill from stale episodes**
- [ ] **Enable SPARK_TRACE_STRICT=1**

### Nice to Have (Excellence)

- [ ] Add semantic deduplication at storage time
- [ ] Implement "hot outcomes" priority boost in advisor
- [ ] Add auto-activation of domain chips
- [ ] Add chip quality scoring dashboard
- [ ] Move from file locks to SQLite for queue (eliminates concurrency issues)
- [ ] Add error path tests (corrupted files, timeouts, network failures)

---

## 10. Recommended Tunable Changes

Here is the complete recommended `~/.spark/tuneables.json`:

```json
{
  "preset": "production_v2",
  "updated": "2026-02-05",
  "values": {
    "min_occurrences": 1,
    "min_occurrences_critical": 1,
    "confidence_threshold": 0.55,
    "gate_threshold": 0.45,
    "max_retries_per_error": 2,
    "max_file_touches": 3,
    "no_evidence_steps": 4,
    "min_confidence_delta": 0.08,
    "weight_impact": 0.25,
    "weight_novelty": 0.25,
    "weight_surprise": 0.35,
    "weight_irreversible": 0.45,
    "max_steps": 30,
    "episode_timeout_minutes": 15,
    "advice_cache_ttl": 180,
    "queue_batch_size": 100,
    "distillation_interval": 15
  },
  "semantic": {
    "enabled": true,
    "min_similarity": 0.55,
    "min_fusion_score": 0.5,
    "weight_recency": 0.15,
    "weight_outcome": 0.40,
    "mmr_lambda": 0.6,
    "index_on_write": true,
    "index_on_read": true,
    "index_backfill_limit": 500,
    "index_cache_ttl_seconds": 120,
    "category_caps": {
      "cognitive": 3,
      "trigger": 2,
      "default": 2,
      "user_understanding": 2,
      "context": 2,
      "self_awareness": 2,
      "meta_learning": 2,
      "wisdom": 2,
      "reasoning": 2
    }
  },
  "promotion": {
    "reliability_threshold": 0.60,
    "min_validations": 2,
    "confidence_floor": 0.88,
    "min_age_hours": 1.5,
    "adapter_budgets": {
      "CLAUDE.md": 50,
      "AGENTS.md": 30,
      "TOOLS.md": 35,
      "SOUL.md": 25,
      ".cursorrules": 40,
      ".windsurfrules": 40
    }
  },
  "advisor": {
    "min_reliability": 0.45,
    "min_validations_strong": 2,
    "max_items": 6,
    "cache_ttl": 180,
    "min_rank_score": 0.40
  },
  "meta_ralph": {
    "quality_threshold": 4,
    "needs_work_threshold": 2,
    "needs_work_close_delta": 0.5,
    "min_outcome_samples": 3,
    "min_tuneable_samples": 30,
    "min_needs_work_samples": 3,
    "min_source_samples": 10
  },
  "eidos": {
    "max_steps": 30,
    "max_time_seconds": 900,
    "max_retries_per_error": 2,
    "max_file_touches": 3,
    "no_evidence_limit": 4
  }
}
```

### Key Changes from Current Defaults (Summary)

| Parameter | Old | New | Why |
|-----------|-----|-----|-----|
| `confidence_threshold` | 0.60 | 0.55 | Catch more early patterns |
| `no_evidence_steps` | 5 | 4 | Force reflection sooner |
| `max_steps` | 25 | 30 | Allow more complex tasks |
| `episode_timeout` | 12min | 15min | Prevent premature timeout |
| `distillation_interval` | 20 | 15 | Generate more distillations |
| `weight_outcome` | 0.35 | 0.40 | Prioritize proven insights |
| `weight_recency` | 0.10 | 0.15 | Favor recent context |
| `mmr_lambda` | 0.50 | 0.60 | Favor relevance over diversity |
| `meta_learning cap` | 1 | 2 | Allow more meta-insights |
| `promotion reliability` | 0.65 | 0.60 | Increase learning velocity |
| `confidence_floor` | 0.90 | 0.88 | Slightly easier fast-track |
| `min_age_hours` | 2.0 | 1.5 | Faster settling |
| `CLAUDE.md budget` | 40 | 50 | More project context |
| `TOOLS.md budget` | 25 | 35 | More tool insights |
| `advisor min_reliability` | 0.50 | 0.45 | Surface more candidates |
| `advisor max_items` | 8 | 6 | Focus on best advice |
| `advisor min_rank_score` | 0.35 | 0.40 | Higher quality threshold |
| `min_outcome_samples` | 5 | 3 | Earlier feedback loops |
| `min_tuneable_samples` | 50 | 30 | Faster auto-tuning |
| `eidos no_evidence_limit` | 5 | 4 | Faster diagnostic triggers |
| `eidos max_time` | 720 | 900 | More time for complex tasks |

---

## 11. Priority Action Items

### Tier 1: Do Today (Critical Path to Production)

1. **Create tuneables.json** with the recommended values above
2. **Fix Budget.from_dict** default mismatch (max_file_touches: 2 -> 3)
3. **Add chip insight rotation** - prevent spark-core.jsonl from growing unbounded
4. **Lower DISTILLATION_INTERVAL** in aggregator.py from 20 to 15

### Tier 2: Do This Week (Production Hardening)

5. **Add dropped-event counter** to queue.py for observability
6. **Add JSON parse error recovery** in queue reader (skip bad lines)
7. **Tighten spark-core chip triggers** - add minimum context length
8. **Auto-distill from stale episodes** before abandoning them
9. **Add tests for importance_scorer.py** (highest risk untested module)
10. **Track episode completion rate** as a dashboard metric

### Tier 3: Do This Month (Excellence)

11. Add EIDOS core unit tests (distillation, episodes, steps)
12. Add chips system unit tests (loader, runtime, scoring)
13. Convert script-based tests to pytest
14. Implement "hot outcomes" boost in advisor
15. Add auto-activation of domain chips based on project context
16. Consider SQLite for queue (eliminate file-based concurrency)

---

## Appendix A: Module Inventory (100+ files)

### Core Pipeline (6 files)
- `hooks/observe.py` - Event capture hook
- `lib/queue.py` - Event queue management
- `lib/pipeline.py` - Processing pipeline
- `lib/bridge_cycle.py` - Bridge worker orchestration
- `lib/bridge.py` - Context sync bridge
- `spark_watchdog.py` - Service monitoring

### Intelligence Engine (12 files)
- `lib/meta_ralph.py` - Quality gate
- `lib/cognitive_signals.py` - Signal extraction
- `lib/cognitive_learner.py` - Insight storage (with 41 noise patterns)
- `lib/advisor.py` - Advice generation
- `lib/importance_scorer.py` - Importance scoring
- `lib/contradiction_detector.py` - Contradiction detection
- `lib/novelty_detector.py` - Novelty detection
- `lib/curiosity_engine.py` - Curiosity engine
- `lib/hypothesis_tracker.py` - Hypothesis tracking
- `lib/prediction_loop.py` - Prediction management
- `lib/validation_loop.py` - Validation management
- `lib/content_learner.py` - Code pattern learning

### EIDOS System (14 files)
- `lib/eidos/models.py` - Core data models
- `lib/eidos/control_plane.py` - Budget enforcement
- `lib/eidos/integration.py` - Hook integration
- `lib/eidos/distillation_engine.py` - Rule extraction
- `lib/eidos/memory_gate.py` - Importance scoring
- `lib/eidos/guardrails.py` - Safety enforcement
- `lib/eidos/evidence_store.py` - Audit trail
- `lib/eidos/escalation.py` - Help requests
- `lib/eidos/validation.py` - Validation methods
- `lib/eidos/metrics.py` - Intelligence metrics
- `lib/eidos/migration.py` - Data migration
- `lib/eidos/minimal_mode.py` - Fallback mode
- `lib/eidos/truth_ledger.py` - Truth records
- `lib/eidos/acceptance_compiler.py` - Criteria compilation

### Chips System (10 files)
- `lib/chips/router.py` - Chip routing
- `lib/chips/runtime.py` - Chip execution
- `lib/chips/loader.py` - Chip discovery/loading
- `lib/chips/registry.py` - Chip registry
- `lib/chips/scoring.py` - Chip quality scoring
- `lib/chips/evolution.py` - Self-improvement
- `lib/chips/store.py` - Chip storage
- `lib/chips/policy.py` - Chip policies
- `lib/chips/schema.py` - YAML schema validation
- `lib/chip_merger.py` - Insight merging

### Pattern Detection (8 files)
- `lib/pattern_detection/aggregator.py` - Pattern aggregation
- `lib/pattern_detection/distiller.py` - Pattern distillation
- `lib/pattern_detection/correction.py` - Correction detection
- `lib/pattern_detection/sentiment.py` - Sentiment detection
- `lib/pattern_detection/repetition.py` - Repetition detection
- `lib/pattern_detection/semantic.py` - Semantic intent detection
- `lib/pattern_detection/why.py` - Why/reasoning detection
- `lib/pattern_detection/memory_gate.py` - Memory gate filter

### Memory & Storage (8 files)
- `lib/memory_store.py` - Hybrid storage
- `lib/memory_banks.py` - Per-project memory
- `lib/memory_capture.py` - Memory capture
- `lib/embeddings.py` - Embedding generation
- `lib/context_sync.py` - Context synchronization
- `lib/promoter.py` - Learning promotion
- `lib/primitive_filter.py` - Primitive detection
- `lib/memory_migrate.py` - Migration utilities

### Output Adapters (5 files)
- `lib/output_adapters/claude_code.py`
- `lib/output_adapters/cursor.py`
- `lib/output_adapters/windsurf.py`
- `lib/output_adapters/clawdbot.py`
- `lib/output_adapters/exports.py`

### Support Systems (20+ files)
- Skills: `skills_registry.py`, `skills_router.py`
- Outcomes: `outcomes/tracker.py`, `outcomes/linker.py`, `outcomes/signals.py`
- Metalearning: `metalearning/strategist.py`, `metalearning/evaluator.py`, `metalearning/reporter.py`
- Research: `research/spark_research.py`, `research/web_research.py`, and more
- Onboarding: `onboarding/detector.py`, `onboarding/questions.py`, `onboarding/context.py`
- Others: `tastebank.py`, `resonance.py`, `spark_voice.py`, `growth_tracker.py`, etc.

---

## Appendix B: Chip System Usage Guide

### How to Use Chips Effectively

**For a new project:**
1. Start a session and let domain detection identify your domain
2. Activate the relevant domain chip: `spark chips activate game-dev`
3. Answer the chip's onboarding questions: `spark chips questions game-dev`
4. Work normally - the chip captures domain-specific insights automatically
5. Review chip insights: `spark chips insights game-dev`

**For ongoing projects:**
1. Chips auto-trigger on relevant events (no manual action needed)
2. Review chip insights periodically to see what it's learning
3. Validate useful insights: `spark validate --search "insight text"`
4. Deactivate if a chip is generating too much noise: `spark chips deactivate bench-core`

**Chip activation recommendations by project type:**

| Project Type | Activate | Why |
|-------------|----------|-----|
| Game development | spark-core + game-dev | Balance tuning, player feedback, perf |
| Web app | spark-core + vibecoding | Delivery velocity, code quality |
| Marketing site | spark-core + marketing | Campaign metrics, CTR, conversion |
| Business project | spark-core + biz-ops | Operations, pricing, strategy |
| Market research | spark-core + market-intel | Competition, pricing, trends |
| Benchmarking | spark-core + bench-core | Tool performance, timing |
| Multi-domain | spark-core + 2-3 domain chips | Cross-domain synthesis |

**Best practices:**
- Only activate 2-3 chips simultaneously (avoids insight overload)
- spark-core should always be active (it's auto-activated)
- Deactivate chips for domains you're not currently working in
- Review chip insights weekly to validate quality

---

## Appendix C: North Star Metrics to Track

| Metric | Current | Target | How to Improve |
|--------|---------|--------|----------------|
| **Compounding Rate** | Unknown | >40% | Track steps citing memory that succeeded |
| **Distillation Conversion** | 0.4% | 5-10% | Lower interval, auto-distill stale episodes |
| **Outcome Action Rate** | 1.4% | >20% | Strengthen advisor, add hot outcomes |
| **Quality Pass Rate** | 47% | 40-55% | Keep current threshold (4/10) |
| **Promotion Rate** | Unknown | >10%/week | Lower reliability threshold to 0.60 |
| **Chip S/N Ratio** | ~500:1 | <50:1 | Per-chip noise filter, tighter triggers |
| **Episode Completion** | Unknown | >60% | Auto-consolidate stale, increase timeout |
| **Memory Effectiveness** | Unknown | >10% | Track success rate with vs without memory |

---

*This analysis was generated from reading every Python module, every test file, every documentation file, every chip definition, and every configuration in the Spark Intelligence codebase. The recommendations are specific, actionable, and prioritized for production readiness.*
