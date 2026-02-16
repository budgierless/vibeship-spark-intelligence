# Retrieval Quality Improvement Plan

**Date**: 2026-02-17
**Goal**: Raise advisory precision from ~60% to >85% (Precision@5)
**Approach**: SOTA-grounded, incremental, measurable at every step

---

## Problem Statement

Spark advisory delivers ~40% noise: research tweets, DEPTH training logs, user quotes, and generic placeholders surface as tool advice because the insight pool (256 items) is flat — no metadata filtering by tool type, no actionability scoring, no memory tiering. Semantic similarity alone can't distinguish "actionable directive" from "interesting observation."

**Top noise offenders** (from 1246 delivered advisories):
- "ClaudeCraft integrating OpenClaw..." delivered 164 times (26.1% of all noise)
- "Security holes in agent ecosystems..." delivered 139 times
- "Use packet guidance." delivered 28 times
- Confidence-merging code snippets delivered 25 times

---

## What We Have (Good)

| Capability | Location | Status |
|------------|----------|--------|
| Local embeddings | `lib/embeddings.py` (BAAI/bge-small-en-v1.5 via FastEmbed) | Working |
| Hybrid semantic+BM25 | `lib/semantic_retriever.py:retrieve()` L417 | Working |
| Domain detection | `lib/advisor.py` (10 domains via keyword markers) | Working |
| Agentic escalation | `lib/advisor.py:_get_semantic_cognitive_advice()` L1904 | Working |
| Prefiltering | `lib/advisor.py:_prefilter_insights_for_retrieval()` L1616 | Working |
| MMR configured | `lib/semantic_retriever.py` (mmr_lambda=0.5) | Working |
| Source boost tiers | `lib/advisor.py:_SOURCE_BOOST` L3535 (15 tiers) | Working |
| Actionability scoring | `lib/advisor.py:_score_actionability()` L3443 | Weak (keyword-only) |
| Intent taxonomy | `lib/advisory_intent_taxonomy.py` (11 families) | Built but NOT wired |
| Tool-intent hints | `lib/advisory_intent_taxonomy.py:TOOL_INTENT_HINTS` L79 | Built but NOT wired |

---

## 3 Biggest Gaps (SOTA-Grounded)

### Gap 1: No Tool-Action Routing (Pre-Retrieval Filtering)

**SOTA reference**: Anthropic Contextual Retrieval, Manus Context Engineering
**Problem**: All 256 insights go into the same retrieval pool regardless of what tool is being called. An `Edit` on a Python file shouldn't see X engagement insights.
**Solution**: Tag each insight with `action_domains` metadata at ingestion time. Filter the pool *before* embedding search based on `tool_name` → `intent_family` mapping (already built in `advisory_intent_taxonomy.py` but not wired).

### Gap 2: No Actionability Gate (Post-Retrieval Relevance)

**SOTA reference**: Self-RAG ISREL gate, CRAG three-tier gating
**Problem**: Current `_score_actionability()` uses 12 keyword patterns with a ±0.3 swing — too weak to separate "always verify auth tokens before deployment" (directive) from "RT @user: interesting thread about auth" (observation).
**Solution**: Replace with a structured actionability classifier that scores on 4 dimensions: has_verb_directive, has_condition, has_specificity, is_observation_only. Gate at threshold — don't just demote, drop.

### Gap 3: Flat Memory Pool (No Tiering)

**SOTA reference**: MemGPT/Letta tiered memory, Mem0 dedup
**Problem**: 256 insights stored equally. A validated EIDOS distillation with 22 validations sits in the same pool as a single-observation research tweet quote.
**Solution**: Three tiers: **pinned** (3-5 highest-value, always included), **active** (50-80 validated insights, normal retrieval), **archive** (170+ low-value, only retrieved on escalation). Tier assignment based on validation count, reliability score, and recency.

---

## Implementation Phases

### Phase 1: Metadata + Actionability Gate (Target: 60% → ~80%)

**Estimated scope**: 4 files modified, ~200 lines changed
**Commit strategy**: One commit per sub-task

#### Task 1.1: Add `action_domain` field to CognitiveInsight

**File**: `lib/cognitive_learner.py`
**Line**: 258 (CognitiveInsight dataclass)

Add field:
```python
action_domain: str = ""  # e.g., "code", "x_social", "depth", "general", "system"
```

Add domain classifier method:
```python
def classify_action_domain(insight_text: str, category: str, source: str) -> str:
    """Classify an insight into an action domain for pre-retrieval filtering."""
```

Classification rules:
- Source contains "x_research", "x_social", "engagement", "social-convo" → `"x_social"`
- Source contains "depth" or text starts with `[DEPTH:` → `"depth_training"`
- Category is "user_understanding" and text starts with user quote → `"user_context"`
- Text contains code patterns (def, class, import, {, }) → `"code"`
- Default → `"general"`

Backfill existing 256 insights on load with the classifier.

#### Task 1.2: Wire Intent Taxonomy into Pre-Retrieval Filter

**File**: `lib/advisor.py`
**Line**: 1616 (`_prefilter_insights_for_retrieval`)

Currently filters by keyword overlap and reliability only. Add:

1. Call `map_intent()` from `advisory_intent_taxonomy.py` to get the current intent family
2. Map intent family to allowed action_domains:
   ```python
   INTENT_TO_DOMAINS = {
       "auth_security": ["code", "general"],
       "deployment_ops": ["code", "system", "general"],
       "testing_validation": ["code", "general"],
       "tool_reliability": ["code", "system", "general"],
       "research_decision_support": ["code", "general", "x_social"],
       # ... etc
   }
   ```
3. Filter insights: only include those whose `action_domain` is in the allowed set (or `"general"`)
4. Fallback: if filtering drops below 20 insights, relax to include all

#### Task 1.3: Replace Actionability Scoring with Structured Classifier

**File**: `lib/advisor.py`
**Line**: 3443 (`_score_actionability`)

Replace the 12-keyword approach with a 4-dimension classifier:

```python
def _score_actionability(self, text: str) -> float:
    """Score actionability on 4 dimensions (0.0 to 1.0)."""
    scores = {
        "has_directive": 0.0,     # Contains imperative verb (use, avoid, check, ensure, prefer)
        "has_condition": 0.0,     # Contains when/if/before/after trigger
        "has_specificity": 0.0,   # References concrete tools, files, patterns
        "not_observation": 1.0,   # NOT a passive observation/quote/log
    }
```

**Observation detectors** (new — these are the gap):
- Starts with `RT @` or contains `(eng:` → observation (score 0.0)
- Starts with `[DEPTH:` and contains `Strong ... reasoning:` → training log (score 0.1)
- Starts with `User prefers` or `Now, can we` → user quote (score 0.2)
- Contains only a code snippet (>50% non-alpha chars) → code artifact (score 0.1)
- Is a URL or contains `http://`/`https://` as primary content → reference (score 0.2)

**Gate threshold**: Items scoring below 0.3 are DROPPED, not just demoted.

#### Task 1.4: Raise Similarity Floor

**File**: `lib/semantic_retriever.py`
**Line**: 30-31

Change:
```python
"min_similarity": 0.50 → 0.55
"min_fusion_score": 0.45 → 0.50
```

And in `lib/advisor.py` line 103:
```python
MIN_RANK_SCORE = 0.55 → 0.60
```

Philosophy: return fewer, higher-quality results. Empty is better than noisy.

#### Task 1.5: Build Evaluation Harness

**File**: NEW `tests/test_retrieval_quality.py`

Create 25 test scenarios covering:
- 8 code editing scenarios (Edit/Write on Python/JS files)
- 5 debugging scenarios (Bash with error context)
- 4 research scenarios (WebSearch/WebFetch)
- 4 X/social scenarios (tweet operations)
- 4 general scenarios (Read/Glob on various files)

Each scenario has:
```python
{
    "tool_name": "Edit",
    "tool_input": {"file_path": "lib/advisor.py", "old_string": "...", "new_string": "..."},
    "task_context": "Fixing the actionability scoring",
    "expected_relevant_domains": ["code", "general"],
    "noise_patterns": ["RT @", "[DEPTH:", "User prefers"],  # Should NOT appear
}
```

Metric: Precision@5 = (relevant items in top 5) / 5

---

### Phase 2: Cross-Encoder Reranking + RRF (Target: ~80% → ~90%)

**Estimated scope**: 2 new files, 3 files modified, ~300 lines
**Depends on**: Phase 1 complete and measured

#### Task 2.1: Add Cross-Encoder Reranker

**File**: NEW `lib/cross_encoder_reranker.py`

Use `cross-encoder/ms-marco-MiniLM-L-6-v2` (22M params, fully local, ~200ms on CPU):

```python
class CrossEncoderReranker:
    def __init__(self, model_name="cross-encoder/ms-marco-MiniLM-L-6-v2"):
        from sentence_transformers import CrossEncoder
        self.model = CrossEncoder(model_name)

    def rerank(self, query: str, candidates: List[str], top_k: int = 8) -> List[Tuple[int, float]]:
        """Rerank candidates by cross-encoder relevance score."""
        pairs = [(query, c) for c in candidates]
        scores = self.model.predict(pairs)
        ranked = sorted(enumerate(scores), key=lambda x: x[1], reverse=True)
        return ranked[:top_k]
```

Lazy-load on first use. Cache the model instance.

#### Task 2.2: Wire Cross-Encoder into Advisory Pipeline

**File**: `lib/advisor.py`
**Location**: Between `_rank_advice()` (L3589) and `MIN_RANK_SCORE` filter (L1850)

After initial ranking produces top-16 candidates, run cross-encoder rerank on the top-16 to get the final top-8. This is a second-pass filter that uses the full query-document pair for relevance scoring (not just embedding distance).

```python
# After _rank_advice(), before MIN_RANK_SCORE filter:
if len(advice_list) > 8 and self._cross_encoder_available():
    advice_list = self._cross_encoder_rerank(semantic_context, advice_list, top_k=MAX_ADVICE_ITEMS)
```

#### Task 2.3: Implement Reciprocal Rank Fusion (RRF)

**File**: `lib/semantic_retriever.py`
**Location**: New method in `SemanticRetriever`

Currently, semantic score and BM25 score are combined with a linear weight (`bm25_mix`). Replace with RRF:

```python
def _rrf_score(self, semantic_rank: int, bm25_rank: int, k: int = 60) -> float:
    """Reciprocal Rank Fusion — combines rankings without score normalization."""
    return 1.0 / (k + semantic_rank) + 1.0 / (k + bm25_rank)
```

This is more robust than linear interpolation because it doesn't require score normalization between semantic similarity (0-1) and BM25 (unbounded).

#### Task 2.4: Tune MMR for Better Diversity

**File**: `lib/semantic_retriever.py`

Current: `mmr_lambda=0.5`. This is a reasonable default but we should measure the impact of diversity vs relevance at different values. Add this as a tunable:

```python
# In tuneables.json semantic section:
"mmr_lambda": 0.6  # Slightly prefer relevance over diversity
```

---

### Phase 3: Memory Tiering + Contextual Enrichment (Target: ~90% → ~95%)

**Estimated scope**: 2 files modified, 1 new file, ~250 lines
**Depends on**: Phase 2 complete and measured

#### Task 3.1: Implement Three-Tier Memory System

**File**: `lib/cognitive_learner.py`
**New method**: `tier_insights()`

Tier assignment rules:
```
PINNED (3-5 items):
  - times_validated >= 15 AND reliability >= 0.95
  - OR: promoted == True AND source == "eidos"

ACTIVE (50-80 items):
  - times_validated >= 3 AND reliability >= 0.70
  - OR: created_at within last 7 days
  - OR: category in ("self_awareness", "wisdom") AND confidence >= 0.8

ARCHIVE (everything else):
  - Only retrieved during agentic escalation
  - Candidates for eviction after 90 days with 0 validations
```

#### Task 3.2: Wire Tiering into Retrieval

**File**: `lib/advisor.py`

Modify `_prefilter_insights_for_retrieval()`:
1. Always include PINNED items (bypass all filtering)
2. Search ACTIVE tier for normal queries
3. Include ARCHIVE tier only during agentic escalation (`should_escalate == True`)

#### Task 3.3: Contextual Enrichment at Ingestion

**File**: `lib/cognitive_learner.py`
**Method**: `add_insight()`

Before embedding, prepend usage context (Anthropic Contextual Retrieval technique):

```python
enriched_text = f"[{category}] [domain:{action_domain}] {insight_text}"
```

This gives the embedding model domain and category signal, improving retrieval accuracy by ~67% per Anthropic's research.

Re-embed existing insights with enriched text (one-time migration).

#### Task 3.4: Adaptive Retrieval Gate

**File**: `lib/advisor.py`
**Method**: `advise()`

Skip retrieval entirely for trivial operations:
```python
SKIP_RETRIEVAL_TOOLS = {"Read", "Glob", "Grep"}  # Read-only tools
SKIP_CONTEXTS = {"listing files", "reading file", "searching for"}

if tool_name in SKIP_RETRIEVAL_TOOLS and not task_context:
    return []  # No advice needed for simple reads
```

This reduces unnecessary retrieval calls and prevents noise from accumulating in cache.

---

## Evaluation Framework

### Primary Metric: Precision@5

```
Precision@5 = (number of relevant items in top 5) / 5
```

### Test Scenarios (25 total)

| Category | Count | Example |
|----------|-------|---------|
| Code editing | 8 | Edit Python file with auth context |
| Debugging | 5 | Bash with pytest failure |
| Research | 4 | WebSearch for API docs |
| X/Social | 4 | Tweet composition |
| General | 4 | Read config file |

### Measurement Protocol

1. **Before each phase**: Run all 25 scenarios, record Precision@5
2. **After each phase**: Re-run, compute delta
3. **Noise audit**: Count instances of known noise patterns in results
4. **Latency check**: Ensure retrieval stays under 500ms p95

### Target Metrics

| Phase | Precision@5 | Noise Rate | Latency p95 |
|-------|-------------|------------|-------------|
| Current | ~0.60 | ~40% | ~300ms |
| Phase 1 | >0.80 | <20% | ~300ms |
| Phase 2 | >0.88 | <12% | ~500ms |
| Phase 3 | >0.93 | <7% | ~400ms |

---

## Risk Mitigations

| Risk | Mitigation |
|------|------------|
| Cross-encoder adds latency | Only rerank top-16 (not full pool). Budget: 200ms |
| Over-filtering drops good advice | Fallback: if <3 results after filtering, relax thresholds |
| Tier migration corrupts data | Keep backup of cognitive_insights.json before migration |
| Domain classifier wrong | "general" domain is always included as fallback |
| sentence-transformers dependency | Lazy-load, graceful fallback to current ranking if unavailable |

---

## Files Changed Per Phase

### Phase 1
- `lib/cognitive_learner.py` — Add `action_domain` field + classifier
- `lib/advisor.py` — Wire intent filtering, replace actionability scorer
- `lib/semantic_retriever.py` — Raise similarity floor
- `tests/test_retrieval_quality.py` — NEW evaluation harness

### Phase 2
- `lib/cross_encoder_reranker.py` — NEW cross-encoder wrapper
- `lib/advisor.py` — Wire cross-encoder reranking
- `lib/semantic_retriever.py` — RRF fusion, MMR tuning

### Phase 3
- `lib/cognitive_learner.py` — Tiering system + contextual enrichment
- `lib/advisor.py` — Wire tiering into retrieval gate

---

## Decision Log

| Decision | Rationale |
|----------|-----------|
| Local cross-encoder over API call | Zero latency cost, no API key needed, 22M params runs fine on CPU |
| RRF over linear interpolation | Rank-based fusion doesn't need score normalization |
| 3 tiers (not 5) | Simple is better. 3 tiers cover the real use cases |
| Gate at 0.3 actionability | Below 0.3 = clearly observation/quote/log. Safe to drop |
| Keep "general" domain as fallback | Prevents over-filtering on unknown intents |
| Phase 1 first (no reranker) | Metadata filtering before retrieval > reranking after retrieval. Fix input, not output |
| Evaluation harness before any code changes | Can't improve what you can't measure |
