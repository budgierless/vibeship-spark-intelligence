# Spark Intelligence: Semantic Retrieval Proposal

## Multi-LLM Review Complete ✅

**Date:** 2026-02-05
**Status:** Design REFINED after multi-LLM feedback - ready for implementation
**Goal:** Build a self-evolving intelligence system that surfaces the RIGHT knowledge at the RIGHT time

## Implementation Status (2026-02-05)

What is already in the repo now:
- `lib/semantic_retriever.py` (hybrid triggers + semantic + outcomes, MMR, fusion, intent extraction)
- `lib/advisor.py` integration (semantic-first with keyword fallback)
- `lib/cognitive_learner.py` indexing on write
- `scripts/semantic_reindex.py` for full index rebuilds
- `TUNEABLES.md` and `~/.spark/trigger_rules.yaml` for tuneables + triggers

Operational notes:
- Enable with `semantic.enabled=true` and `triggers.enabled=true` in `~/.spark/tuneables.json`
- Build/refresh index: `python scripts/semantic_reindex.py`
- To reduce background load during quickstart, use `spark up --lite` (or `SPARK_LITE=1` in launch scripts)

---

## LLM Feedback Summary (3 Reviewers)

### Unanimous Validation
All reviewers agreed the architecture is fundamentally sound:
- ✅ **Hybrid retrieval** (triggers + semantic + outcomes) is the right approach
- ✅ **Outcome-weighted ranking** is the "killer feature" that makes this self-evolving
- ✅ **Problem diagnosis** is "razor sharp" - storage-retrieval gap identified correctly
- ✅ **Meta-Ralph quality gate** prevents garbage embeddings from polluting retrieval

### Critical Bugs Identified

| Bug | Problem | Fix |
|-----|---------|-----|
| **Threshold logic inverted** | Ranking by fused score then filtering by raw similarity drops high-ranked items | Two thresholds: `min_similarity` (gate) + `min_fusion_score` (decision) |
| **Similarity overloaded** | Triggers use `similarity=1.0`, conflating trigger confidence with semantic similarity | Separate `trigger_conf` from `semantic_sim` |
| **No diversity** | Pure nearest-neighbor returns 8 near-duplicates | Add MMR (Max Marginal Relevance) or cap per category |
| **Arbitrary fusion weights** | 0.5/0.2/0.3 are guesses | Learn optimal weights from outcome data |
| **Muddy query embeddings** | Embedding full context produces poor vectors | Extract intent first, then embed |
| **No cold-start strategy** | New users get garbage semantic results | Ship default insight pack + use EIDOS as prior |

### Consensus on Open Questions

| Question | Answer | Rationale |
|----------|--------|-----------|
| Lazy vs eager embedding? | **Eager** (on write) | Reads 100x more than writes; retrieval must be <50ms |
| Trigger rules format? | **YAML first** | Human-editable, predictable; learned triggers need review/shadow mode |
| Cold start? | **Seed pack + EIDOS prior** | Ship universal best practices, let personalization take over |
| Interrupts opt-in? | **Yes, 100%** | High friction; default off, earn trust first |
| Embedding model? | **bge-small OK for insights** | For raw code, consider voyage-code-2 |
| Minimum similarity threshold? | **Conservative (0.7+)** | Better no advice than bad advice |

### Recommended Implementation Order

1. **Phase 1:** Semantic index + retrieval + baseline measurement + dedup/MMR
2. **Phase 2:** Fusion ranking with outcome weighting (the compounding magic)
3. **Phase 3:** Minimal trigger rules (security + destructive + deploy only)
4. **Phase 4:** Learned triggers (with shadow mode safeguards)
5. **Phase 5:** Interrupt system (only if users request it)

### North Star Metric
> **"% of sessions where at least 1 cognitive insight is surfaced AND later attributed as helpful"**

This is the compounding lever that proves the system works.

---

## Table of Contents

1. [The Vision](#the-vision)
2. [The Problem We're Solving](#the-problem-were-solving)
3. [Current System Architecture](#current-system-architecture)
4. [What We've Built So Far](#what-weve-built-so-far)
5. [The Gap We Identified](#the-gap-we-identified)
6. [Proposed Solution](#proposed-solution)
7. [Alternative Approaches Considered](#alternative-approaches-considered)
8. [The Self-Evolving AGI Angle](#the-self-evolving-agi-angle)
9. [Open Questions for Review](#open-questions-for-review)
10. [Technical Specifications](#technical-specifications)

---

## The Vision

We're building **Spark Intelligence** - a system that allows AI agents (like Claude, GPT, etc.) to:

1. **Learn** from interactions (user preferences, decisions, mistakes, successes)
2. **Remember** across sessions (persistent memory, not just context window)
3. **Evolve** over time (get better at helping this specific user)
4. **Apply** learnings at the right moment (not just store them)

The ultimate goal: **An AI that genuinely knows you and gets smarter the more you work together.**

This isn't about fine-tuning models. It's about building an intelligent retrieval and application layer that sits between the user and the LLM, feeding relevant learned knowledge into every interaction.

---

## The Problem We're Solving

### The Core Issue: LLMs Don't Learn From You

Every time you start a new session with an LLM:
- It doesn't remember your preferences
- It doesn't know your past mistakes
- It doesn't know what worked before
- It treats you like a stranger

### The Storage-Retrieval Gap

Many systems try to solve this with "memory":
- Store everything the user says
- Retrieve "relevant" memories
- Inject into context

**But this creates a new problem:** How do you retrieve the RIGHT memory at the RIGHT time?

Current approaches use **keyword matching**:
- User says "edit authentication code"
- System searches for "authentication" in stored memories
- Finds memories that contain the word "authentication"

**This fails for:**
- Semantic similarity: "login security" doesn't match "authentication" even though related
- Implicit relevance: "always validate server-side" is relevant to auth but doesn't contain the word
- Contextual triggers: "deploying to production" should surface safety checklists but keyword won't find them

### The Utilization Gap

Even when the right memory is retrieved, it often isn't **used**:
- Memory is retrieved but agent ignores it
- Memory is shown but doesn't influence the action
- No feedback loop to learn what advice actually helped

We measured this in our system:
- **374 cognitive insights** stored
- **Only 1%** of advice comes from these insights
- **89.7%** of actions are "effective" but we can't attribute to which insights helped

---

## Current System Architecture

Spark Intelligence consists of several interconnected components:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           SPARK INTELLIGENCE                                 │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐  │
│  │   CAPTURE   │───▶│   PROCESS   │───▶│    STORE    │───▶│   RETRIEVE  │  │
│  │             │    │             │    │             │    │             │  │
│  │ observe.py  │    │ meta_ralph  │    │ cognitive   │    │  advisor    │  │
│  │ (hooks)     │    │ (quality)   │    │ _learner    │    │  (surface)  │  │
│  └─────────────┘    └─────────────┘    └─────────────┘    └─────────────┘  │
│         │                 │                  │                   │          │
│         │                 │                  │                   │          │
│         ▼                 ▼                  ▼                   ▼          │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                         STORAGE LAYER                                │   │
│  │                                                                      │   │
│  │  ~/.spark/cognitive_insights.json  (374 learned insights)           │   │
│  │  ~/.spark/eidos.db                 (distillations, patterns)        │   │
│  │  ~/.spark/memory_store.sqlite      (memories with embeddings)       │   │
│  │  ~/.mind/lite/memories.db          (Mind v5 external memory)        │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Component Descriptions

#### 1. Capture Layer (observe.py)
- Hooks into Claude Code's tool execution
- Captures PreToolUse, PostToolUse, UserPromptSubmit events
- Extracts cognitive signals (preferences, decisions, corrections)
- Routes to processing pipeline

#### 2. Processing Layer (Meta-Ralph)
- Quality gate for all learnings
- Scores on 5 dimensions: Actionability, Novelty, Reasoning, Specificity, Outcome-Linked
- Filters out "primitive" learnings (tool usage stats, timing data)
- Only passes "cognitive" learnings (user insights, decisions, preferences)
- Current pass rate: 46.7%

#### 3. Storage Layer
- **Cognitive Insights**: User preferences, decisions, learned patterns
- **EIDOS Distillations**: Extracted rules from repeated patterns
- **Memory Store**: SQLite with FTS5 + optional embeddings
- **Mind v5**: External persistent memory service

#### 4. Retrieval Layer (Advisor)
- Called before each tool execution
- Queries multiple sources for relevant advice
- Returns top 8 most relevant pieces of advice
- **Currently uses keyword matching** (this is what we want to improve)

### Data Flow

```
User Action (e.g., "Edit auth/login.py")
        │
        ▼
┌───────────────────┐
│   PreToolUse      │
│   Hook Fires      │
└───────────────────┘
        │
        ▼
┌───────────────────┐
│  Advisor.advise() │◀──────────────────────────────────┐
└───────────────────┘                                   │
        │                                               │
        ▼                                               │
┌───────────────────────────────────────────────────┐   │
│           RETRIEVAL (Current: Keyword)            │   │
│                                                   │   │
│  1. cognitive_learner.get_insights_for_context()  │   │
│     └─▶ Keyword match: "auth" in insight text     │   │
│                                                   │   │
│  2. eidos_retriever.retrieve_for_intent()         │   │
│     └─▶ Structural match by distillation type     │   │
│                                                   │   │
│  3. memory_banks.retrieve()                       │   │
│     └─▶ FTS5 search on memory content             │   │
│                                                   │   │
│  4. Tool-specific advice                          │   │
│     └─▶ Direct lookup by tool name                │   │
└───────────────────────────────────────────────────┘   │
        │                                               │
        ▼                                               │
┌───────────────────┐                                   │
│  Rank & Return    │                                   │
│  Top 8 Advice     │                                   │
└───────────────────┘                                   │
        │                                               │
        ▼                                               │
┌───────────────────┐                                   │
│  Tool Executes    │                                   │
└───────────────────┘                                   │
        │                                               │
        ▼                                               │
┌───────────────────┐                                   │
│  PostToolUse      │                                   │
│  Hook Fires       │                                   │
└───────────────────┘                                   │
        │                                               │
        ▼                                               │
┌───────────────────┐                                   │
│ Outcome Tracking  │───────────────────────────────────┘
│ (was advice       │   Feedback loop: which advice
│  helpful?)        │   was followed? did it help?
└───────────────────┘
```

---

## What We've Built So Far

### Working Components

| Component | Status | Description |
|-----------|--------|-------------|
| Event Capture | ✅ Working | Hooks capture all tool events |
| Meta-Ralph Quality Gate | ✅ Working | 46.7% pass rate, filters primitives |
| Cognitive Storage | ✅ Working | 374 insights stored |
| EIDOS Distillations | ✅ Working | Pattern extraction to rules |
| Outcome Tracking | ✅ Working | 89.7% effectiveness rate |
| Advisor | ⚠️ Limited | Works but uses keyword matching |
| Embedding Infrastructure | ✅ Exists | fastembed + SQLite vectors, but unused |

### Key Metrics (Current State)

```
Pipeline Health: HEALTHY
├── Bridge Worker: Running (21s since heartbeat)
├── Queue Events: 50 recent
├── Meta-Ralph: 403 roasted, 188 quality passed
└── Cognitive Insights: 374 stored, 19 recent (24h)

Advisor Effectiveness:
├── Advice Given: 4,025 entries
├── Outcomes Tracked: 40,849
├── Follow Rate: ~100%
├── Helpfulness Rate: 97%
└── Cognitive Source Usage: 1% ← THE GAP

Outcome Attribution:
├── auto_created: 75.4% (no insight linkage)
├── self_awareness: 20.2% (tool failure patterns)
├── eidos: 3.4% (distillations)
└── cognitive: 1.0% (learned user insights) ← THE GAP
```

### The Paradox

We have **374 valuable cognitive insights** about the user:
- User preferences ("prefers dark mode", "likes iterative fixes")
- Past decisions ("chose JWT over sessions")
- Learned patterns ("always validate server-side")
- User style ("learns by building, not reading")

But **only 1% of advice** comes from these insights. The rest comes from:
- Generic tool warnings ("Bash can fail")
- EIDOS rules (extracted patterns)
- Self-awareness (past failure patterns)

**Why?** Because keyword matching can't find semantically relevant insights.

---

## The Gap We Identified

### Keyword Matching Limitations

Current retrieval in `cognitive_learner.get_insights_for_context()`:

```python
def get_insights_for_context(self, context: str, limit: int = 10):
    for key, insight in self.insights.items():
        # Simple keyword matching
        hit = (
            (context in insight.context) or
            (insight.context in context) or
            any(word in context for word in insight.text.split()[:8])
        )
        if hit:
            results.append(insight)
```

**This misses:**

| Query | Should Match | But Doesn't Because |
|-------|--------------|---------------------|
| "edit authentication code" | "validate tokens server-side" | No keyword overlap |
| "login security" | "user prefers JWT" | Different words, same concept |
| "deploying to prod" | "always run tests first" | Semantic relationship, not lexical |
| "fixing game physics" | "user prefers iterative small fixes" | Preference applies but no keywords |

### The Embedding Infrastructure Exists But Is Unused

We already have:

```python
# lib/embeddings.py
def embed_text(text: str) -> List[float]:
    """Returns 384-dim embedding using bge-small-en-v1.5"""
    from fastembed import TextEmbedding
    embedder = TextEmbedding(model_name="BAAI/bge-small-en-v1.5")
    return list(embedder.embed([text]))[0]

# lib/memory_store.py
# SQLite table for vector storage
CREATE TABLE memories_vec (
    memory_id TEXT PRIMARY KEY,
    dim INTEGER,
    vector BLOB
);

# Cosine similarity function
def _cosine(a: List[float], b: List[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    return dot / (norm(a) * norm(b))
```

**But the Advisor doesn't use it.** It still relies on keyword matching.

---

## Proposed Solution

### Semantic Retrieval Architecture

Replace keyword matching with embedding-based semantic similarity:

```
User Action → Semantic Advisor
                    │
    ┌───────────────┴───────────────┐
    ▼                               ▼
[Trigger Rules]              [Semantic Search]
Explicit patterns            Embedding similarity
"If auth file →              "edit auth" ≈ "validate tokens"
 surface security"           cosine similarity = 0.87
    │                               │
    └───────────────┬───────────────┘
                    ▼
              [Fusion Ranking]
              Combine:
              - Semantic similarity (0-1)
              - Trigger match bonus
              - Past effectiveness
              - Recency
                    │
                    ▼
              [Threshold Filter]
              precision_mode: high_recall / high_precision
                    │
                    ▼
              Return top N insights
```

### Key Components

#### 1. Semantic Index
Pre-compute embeddings for all cognitive insights:

```python
# On insight creation
embedding = embed_text(insight.text + " " + insight.context)
store_in_sqlite(insight_key, embedding)

# On retrieval
query_embedding = embed_text("edit authentication code")
similar_insights = find_by_cosine_similarity(query_embedding)
# Returns: "validate tokens" (0.87), "JWT preference" (0.82), ...
```

#### 2. Trigger Rules
Explicit rules for known high-stakes patterns:

```yaml
# ~/.spark/trigger_rules.yaml
triggers:
  - pattern: "auth|security|password|token"
    surface: [security_checklist, auth_best_practices]
    priority: critical

  - pattern: "rm -rf|delete.*prod"
    surface: [danger_warnings]
    priority: critical
    interrupt: true  # Block and warn

  - pattern: "deploy|release"
    surface: [pre_deploy_checklist]
    priority: high
```

#### 3. Fusion Ranking
Combine multiple signals with configurable weights:

```
SCORE = (similarity × W_SIM) + (recency × W_REC) + (effectiveness × W_OUT) + priority_boost

Default weights (tuneable):
- W_SIM = 0.5  (semantic similarity)
- W_REC = 0.2  (recency boost)
- W_OUT = 0.3  (past effectiveness)
```

#### 4. Configurable Embedding Providers
Users choose their embedding backend:

| Provider | Quality | Latency | Cost | Offline |
|----------|---------|---------|------|---------|
| Local (fastembed) | Good | ~10ms | Free | ✅ |
| OpenAI | Better | ~100ms | $0.02/1M | ❌ |
| Cohere | Better | ~80ms | Free tier | ❌ |
| Voyage AI | Best (code) | ~100ms | $0.12/1M | ❌ |

#### 5. Tuneable Parameters
All settings user-configurable in `~/.spark/tuneables.json`:

```json
{
  "semantic": {
    "enabled": true,
    "embedding_provider": "local",
    "min_similarity": 0.6,
    "precision_mode": "high_recall",
    "weight_similarity": 0.5,
    "weight_recency": 0.2,
    "weight_outcome": 0.3
  },
  "triggers": {
    "enabled": true,
    "learn_triggers": true
  },
  "decay": {
    "enabled": false,
    "half_life_days": 30
  }
}
```

---

## Alternative Approaches Considered

### Alternative 1: Fine-tuning the LLM
**Approach:** Fine-tune the base model on user data
**Pros:** Deep integration, model "knows" the user
**Cons:**
- Expensive (compute cost)
- Slow to update (need retraining)
- Privacy concerns (user data in model)
- Provider lock-in (can't fine-tune Claude)

**Verdict:** Not viable for dynamic, per-user learning

### Alternative 2: RAG with Vector Database
**Approach:** Store everything in Pinecone/Weaviate, use standard RAG
**Pros:** Industry standard, well-documented
**Cons:**
- External dependency
- Cost at scale
- No quality filtering (garbage in, garbage out)
- No outcome tracking

**Verdict:** Good foundation but needs quality layer (which we have with Meta-Ralph)

### Alternative 3: Knowledge Graph
**Approach:** Build a graph of entities and relationships
**Pros:** Rich relationships, explainable retrieval
**Cons:**
- Complex to build and maintain
- Requires entity extraction
- Doesn't handle fuzzy/natural language well

**Verdict:** Could be added later as enhancement, but semantic embeddings are simpler start

### Alternative 4: Rule-Based Expert System
**Approach:** Manually define rules for when to surface what
**Pros:** Predictable, explainable, fast
**Cons:**
- Doesn't scale (need rules for everything)
- Misses semantic relationships
- Requires manual maintenance

**Verdict:** Use as supplement (trigger rules) not replacement

### Alternative 5: Hybrid (Our Choice)
**Approach:** Combine semantic search + trigger rules + outcome learning
**Pros:**
- Semantic catches relationships keywords miss
- Triggers ensure critical paths never missed
- Outcome tracking improves over time
- All tuneable by user

**Cons:**
- More complex implementation
- Need to balance multiple signals

**Verdict:** Best of all worlds, worth the complexity

---

## The Self-Evolving AGI Angle

### Why This Matters for AGI

The key insight: **Intelligence isn't just knowledge, it's knowing when to apply knowledge.**

A human expert doesn't just have facts. They have:
1. **Relevance detection** - Know what matters in each situation
2. **Pattern recognition** - See similarities across different contexts
3. **Adaptive learning** - Get better at #1 and #2 over time
4. **Self-correction** - Notice when their approach isn't working

Spark is building these capabilities:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                     SELF-EVOLVING INTELLIGENCE LOOP                         │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│    ┌──────────┐      ┌──────────┐      ┌──────────┐      ┌──────────┐      │
│    │  LEARN   │─────▶│  STORE   │─────▶│ RETRIEVE │─────▶│  APPLY   │      │
│    │          │      │          │      │          │      │          │      │
│    │ Extract  │      │ Quality  │      │ Semantic │      │ Surface  │      │
│    │ insights │      │ filter   │      │ matching │      │ at right │      │
│    │ from     │      │ (Meta-   │      │ (NEW)    │      │ moment   │      │
│    │ actions  │      │ Ralph)   │      │          │      │          │      │
│    └──────────┘      └──────────┘      └──────────┘      └──────────┘      │
│          ▲                                                     │            │
│          │                                                     │            │
│          │           ┌──────────┐      ┌──────────┐            │            │
│          │           │  TRACK   │◀─────│  OUTCOME │◀───────────┘            │
│          │           │          │      │          │                         │
│          └───────────│ Update   │      │ Did it   │                         │
│                      │ insight  │      │ help?    │                         │
│                      │ scores   │      │          │                         │
│                      └──────────┘      └──────────┘                         │
│                                                                             │
│  THE LOOP IMPROVES ITSELF:                                                  │
│  • Insights that help get higher reliability → retrieved more often        │
│  • Insights that don't help decay → retrieved less often                   │
│  • Trigger rules learned from successful retrievals                        │
│  • Weights tuned based on outcome data                                     │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### What Makes This Different From Standard Memory Systems

| Standard Memory | Spark Intelligence |
|-----------------|-------------------|
| Store everything | Store only quality (Meta-Ralph filter) |
| Retrieve by similarity | Retrieve by relevance + triggers + outcomes |
| Static retrieval | Adaptive (outcome-weighted) |
| No feedback | Full outcome tracking |
| One-size-fits-all | User-tuneable |

### The Compounding Effect

Over time, Spark should:

1. **Week 1:** Surface somewhat relevant insights (semantic matching alone)
2. **Month 1:** Surface highly relevant insights (outcome-weighted)
3. **Month 3:** Anticipate needs (learned triggers)
4. **Month 6:** Feel like it "knows" the user

This is the **compounding intelligence** we're aiming for - not just storage, but genuine understanding that improves with every interaction.

### The Missing Pieces for Full AGI

What we're building is one layer of the stack:

```
┌─────────────────────────────────────────────────────────────┐
│                    FULL AGI STACK                           │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  L5: REASONING        │ Claude/GPT provides this           │
│      (inference)      │                                     │
│  ─────────────────────┼─────────────────────────────────── │
│  L4: PLANNING         │ EIDOS provides this                │
│      (goal→steps)     │ (episodes, steps, predictions)     │
│  ─────────────────────┼─────────────────────────────────── │
│  L3: RETRIEVAL ◀──────┼───── WE ARE HERE                   │
│      (right knowledge │ Semantic advisor proposal          │
│       at right time)  │                                     │
│  ─────────────────────┼─────────────────────────────────── │
│  L2: MEMORY           │ Already built                      │
│      (persistent      │ (cognitive_insights, EIDOS,        │
│       storage)        │  memory_store, Mind v5)            │
│  ─────────────────────┼─────────────────────────────────── │
│  L1: PERCEPTION       │ Already built                      │
│      (capture events) │ (observe.py hooks)                 │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

The semantic retrieval proposal fills the **L3 gap** - the intelligence layer between raw memory and reasoning.

---

## Open Questions for Review

We'd appreciate feedback from other LLMs on these questions:

### Architecture Questions

1. **Embedding model choice**: Is `bge-small-en-v1.5` sufficient for code/technical content, or should we default to a code-specialized model?

2. **Fusion formula**: Our proposed `SCORE = (sim × 0.5) + (recency × 0.2) + (outcome × 0.3)` - are these weights reasonable? Should we use learned weights instead?

3. **Trigger vs semantic balance**: Should semantic always run, or should trigger matches short-circuit semantic search?

4. **Cold start**: For new users with no insights, what's the best bootstrap strategy?

### Implementation Questions

5. **Lazy vs eager embedding**: Should we compute embeddings on insight write (eager) or first retrieval (lazy)?

6. **Index structure**: At what scale should we switch from brute-force cosine to approximate nearest neighbor (ANN)?

7. **Cache strategy**: How long should we cache query embeddings? Should we pre-compute embeddings for common queries?

### Learning Questions

8. **Trigger learning**: How should we extract patterns from successful retrievals to create new triggers?

9. **Decay function**: If we enable decay for unused insights, what's the right half-life? Should it vary by category?

10. **Outcome attribution**: When multiple insights are surfaced and the action succeeds, how do we attribute credit?

### Philosophical Questions

11. **Privacy**: Should semantic embeddings be stored locally only, or is it acceptable to use API-based embedding services?

12. **Explainability**: How important is it for users to understand WHY an insight was surfaced?

13. **User control**: What level of control should users have over the retrieval process?

---

## Technical Specifications (REFINED)

### Design Fixes from LLM Review

The following changes address the critical bugs identified:

#### Fix 1: Separate Signal Types (Not Overloaded Similarity)

```python
@dataclass
class SemanticResult:
    insight_key: str
    insight_text: str
    # FIXED: Separate signal types instead of overloading similarity
    semantic_sim: float      # 0-1, embedding cosine similarity
    trigger_conf: float      # 0-1, explicit rule confidence (1.0 if matched)
    source_type: str         # "semantic", "trigger", "both"
    priority: str            # "critical", "high", "normal", "background"
    why: str                 # Explainability: "Trigger: auth_security" or "Semantic: 0.87"
```

#### Fix 2: Two-Stage Thresholding (Gate + Decision)

```python
# WRONG (old): Rank by fused score, then filter by raw similarity
results = self._rank(results)  # Uses fused score
results = [r for r in results if r.similarity >= threshold]  # Filters by raw similarity

# FIXED: Two separate thresholds
min_similarity = 0.4       # Cheap guardrail: "is this remotely relevant?"
min_fusion_score = 0.5     # Real decision: "is this worth surfacing?"

# Stage 1: Gate on minimum semantic similarity (triggers bypass this)
results = [r for r in results
           if r.source_type == "trigger" or r.semantic_sim >= min_similarity]

# Stage 2: Compute fusion score and filter on that
for r in results:
    r.fusion_score = self._compute_fusion(r)
results = [r for r in results if r.fusion_score >= min_fusion_score]
```

#### Fix 3: MMR Diversity (Avoid Near-Duplicates)

```python
def _diversify_mmr(self, results: List[SemanticResult], lambda_: float = 0.5) -> List[SemanticResult]:
    """
    Max Marginal Relevance: balance relevance with diversity.
    lambda_ = 1.0 is pure relevance, 0.0 is pure diversity.
    """
    selected = []
    remaining = list(results)

    while remaining and len(selected) < self.config.get("max_results", 8):
        if not selected:
            # First item: highest score
            best = max(remaining, key=lambda r: r.fusion_score)
        else:
            # Subsequent: balance relevance vs redundancy
            def mmr_score(r):
                relevance = r.fusion_score
                max_sim_to_selected = max(
                    self._text_similarity(r.insight_text, s.insight_text)
                    for s in selected
                )
                return lambda_ * relevance - (1 - lambda_) * max_sim_to_selected

            best = max(remaining, key=mmr_score)

        selected.append(best)
        remaining.remove(best)

    return selected
```

#### Fix 4: Intent Extraction Before Embedding

```python
def _extract_intent(self, context: str) -> str:
    """
    Extract clean intent from context before embedding.
    Muddy context = muddy embeddings.
    """
    # Remove tool metadata noise
    intent = re.sub(r'file_path=.*?(?=\s|$)', '', context)
    intent = re.sub(r'\{.*?\}', '', intent)  # Remove JSON blobs

    # Extract key action words
    action_patterns = [
        r'(edit|create|delete|update|fix|add|remove|change)\s+(\w+)',
        r'working on\s+(.+?)(?:\.|$)',
        r'implementing\s+(.+?)(?:\.|$)',
    ]

    for pattern in action_patterns:
        match = re.search(pattern, context, re.IGNORECASE)
        if match:
            return match.group(0)

    # Fallback: first 100 chars, cleaned
    return ' '.join(context.split()[:20])
```

#### Fix 5: Category Caps (Diversity by Source)

```python
def _cap_by_category(self, results: List[SemanticResult]) -> List[SemanticResult]:
    """
    Prevent single category from dominating.
    Max 3 from each source type.
    """
    caps = self.config.get("category_caps", {
        "cognitive": 3,
        "eidos": 3,
        "trigger": 2,
        "default": 2
    })

    counts = {}
    capped = []

    for r in results:
        cat = self._get_category(r)
        counts[cat] = counts.get(cat, 0) + 1
        if counts[cat] <= caps.get(cat, caps["default"]):
            capped.append(r)

    return capped
```

---

### New File: `lib/semantic_retriever.py` (REVISED)

```python
"""
Semantic retrieval for cognitive insights.

FIXED VERSION addressing LLM review feedback:
1. Separate signal types (not overloaded similarity)
2. Two-stage thresholding (gate + decision)
3. MMR diversity (avoid duplicates)
4. Intent extraction (clean queries)
5. Category caps (balanced sources)
6. Explainability ("why" field)
"""

from typing import List, Dict, Optional
from dataclasses import dataclass, field
from pathlib import Path
import json
import re

@dataclass
class SemanticResult:
    """Single retrieval result with separated signals."""
    insight_key: str
    insight_text: str
    semantic_sim: float = 0.0      # Embedding similarity (0-1)
    trigger_conf: float = 0.0      # Trigger match confidence (0-1)
    recency_score: float = 0.0     # How recent (0-1)
    outcome_score: float = 0.5     # Historical effectiveness (0-1)
    fusion_score: float = 0.0      # Combined score (computed)
    source_type: str = "semantic"  # "semantic", "trigger", "both"
    category: str = "cognitive"    # For category caps
    priority: str = "normal"       # "critical", "high", "normal", "background"
    why: str = ""                  # Explainability string

class SemanticRetriever:
    """
    Hybrid retrieval combining triggers + semantics + outcomes.

    Flow:
    1. Extract intent from context (clean query)
    2. Check explicit trigger rules
    3. Semantic search via embeddings
    4. Merge and deduplicate
    5. Compute fusion scores
    6. Gate on min_similarity (semantic only)
    7. Filter on min_fusion_score
    8. Diversify with MMR + category caps
    9. Return top N with explainability
    """

    def __init__(self, config: Optional[Dict] = None):
        self.config = config or self._load_config()
        self.embedder = self._init_embedder()
        self.trigger_matcher = TriggerMatcher(self.config.get("triggers", {}))
        self.index = SemanticIndex(self.config.get("index_path"))

    def retrieve(
        self,
        context: str,
        insights: Dict,
        limit: int = 8,
    ) -> List[SemanticResult]:
        """Main retrieval with all fixes applied."""

        # 1. Extract clean intent
        query = self._extract_intent(context)

        results = []
        seen_keys = set()

        # 2. Trigger rules (explicit, bypass similarity gate)
        trigger_matches = self.trigger_matcher.match(context)
        for match in trigger_matches:
            if match.insight_key not in seen_keys:
                seen_keys.add(match.insight_key)
                insight = insights.get(match.insight_key)
                if insight:
                    results.append(SemanticResult(
                        insight_key=match.insight_key,
                        insight_text=insight.insight,
                        trigger_conf=1.0,
                        source_type="trigger",
                        category="trigger",
                        priority=match.priority,
                        why=f"Trigger: {match.rule_name}",
                    ))

        # 3. Semantic search
        query_vec = self.embedder.embed(query)
        if query_vec:
            candidates = self.index.search(query_vec, limit=limit * 3)
            for key, sim in candidates:
                if key not in seen_keys:
                    seen_keys.add(key)
                    insight = insights.get(key)
                    if insight:
                        results.append(SemanticResult(
                            insight_key=key,
                            insight_text=insight.insight,
                            semantic_sim=sim,
                            source_type="semantic",
                            category=self._infer_category(insight),
                            priority=self._infer_priority(sim),
                            why=f"Semantic: {sim:.2f} similar",
                        ))

        # 4. Enrich with recency and outcome scores
        for r in results:
            insight = insights.get(r.insight_key)
            if insight:
                r.recency_score = self._compute_recency(insight)
                r.outcome_score = self._get_outcome_effectiveness(r.insight_key)

        # 5. Gate: minimum semantic similarity (triggers bypass)
        min_sim = self.config.get("min_similarity", 0.4)
        results = [r for r in results
                   if r.source_type == "trigger" or r.semantic_sim >= min_sim]

        # 6. Compute fusion scores
        for r in results:
            r.fusion_score = self._compute_fusion(r)

        # 7. Filter on fusion score
        min_fusion = self.config.get("min_fusion_score", 0.5)
        results = [r for r in results if r.fusion_score >= min_fusion]

        # 8. Sort by fusion score
        results.sort(key=lambda r: r.fusion_score, reverse=True)

        # 9. Diversify: MMR + category caps
        results = self._diversify_mmr(results)
        results = self._cap_by_category(results)

        return results[:limit]

    def _compute_fusion(self, r: SemanticResult) -> float:
        """
        Fusion formula (FIXED per LLM feedback):
        - Similarity is a gate, not a dominator
        - Outcome is a booster for relevant items
        - Formula: semantic_sim * (1 + outcome_boost + recency_boost) + trigger_bonus
        """
        w_out = self.config.get("weight_outcome", 0.5)
        w_rec = self.config.get("weight_recency", 0.2)

        if r.source_type == "trigger":
            # Triggers start at 0.9, boosted by outcome
            base = 0.9 + (r.outcome_score - 0.5) * w_out
        else:
            # Semantic: similarity * (1 + boosters)
            boosters = (r.outcome_score - 0.5) * w_out + r.recency_score * w_rec
            base = r.semantic_sim * (1 + boosters)

        # Priority bonus
        priority_bonus = {"critical": 0.2, "high": 0.1, "normal": 0, "background": -0.1}
        base += priority_bonus.get(r.priority, 0)

        return min(1.0, max(0.0, base))

    def _load_config(self) -> Dict:
        """Load from tuneables.json."""
        path = Path.home() / ".spark" / "tuneables.json"
        if path.exists():
            data = json.loads(path.read_text())
            return data.get("semantic", {})
        return {}
```

### Modified: `lib/advisor.py`

```python
# In advise() method, add semantic path:

def advise(self, tool_name: str, tool_input: Dict, task_context: str = "") -> List[Advice]:
    # ... existing code ...

    # NEW: Use semantic retrieval if enabled
    if self._semantic_enabled():
        from .semantic_retriever import get_semantic_retriever
        retriever = get_semantic_retriever()
        semantic_results = retriever.retrieve(
            query=f"{tool_name} {task_context}",
            insights=self.cognitive.insights,
            limit=10,
        )
        advice_list.extend(self._convert_to_advice(semantic_results))
    else:
        # Fallback to keyword matching (existing behavior)
        advice_list.extend(self._get_cognitive_advice(tool_name, context))

    # ... rest of existing code ...
```

### Modified: `lib/cognitive_learner.py`

```python
# In add_insight() method, index embedding:

def add_insight(self, category, insight, context, confidence):
    # ... existing code ...

    # NEW: Index for semantic search
    self._index_embedding(insight_key, insight, context)

def _index_embedding(self, key: str, text: str, context: str):
    """Compute and store embedding for semantic search."""
    try:
        from .semantic_retriever import get_semantic_retriever
        retriever = get_semantic_retriever()
        if retriever.config.get("index_on_write", True):
            retriever.index.add(key, f"{text} {context}")
    except Exception:
        pass  # Don't break writes if indexing fails
```

### New: `~/.spark/trigger_rules.yaml`

```yaml
# Explicit trigger rules for known patterns
version: 1

rules:
  - name: auth_security
    pattern: "auth|login|password|token|session|jwt|oauth"
    surface: [security_checklist, auth_best_practices]
    priority: high

  - name: destructive_commands
    pattern: "rm -rf|delete.*prod|drop table|truncate"
    surface: [danger_warnings]
    priority: critical
    interrupt: true

  - name: deployment
    pattern: "deploy|release|push.*main|merge.*master"
    surface: [pre_deploy_checklist]
    priority: high

# Learned triggers (auto-populated by Spark)
learned: []
```

### Updated: `~/.spark/tuneables.json`

```json
{
  "preset": "aggressive",
  "values": {
    "min_occurrences": 1,
    "confidence_threshold": 0.45,
    "gate_threshold": 0.35
  },
  "semantic": {
    "enabled": true,
    "embedding_provider": "local",
    "embedding_model": "BAAI/bge-small-en-v1.5",
    "min_similarity": 0.6,
    "weight_similarity": 0.5,
    "weight_recency": 0.2,
    "weight_outcome": 0.3,
    "precision_mode": "high_recall",
    "index_on_write": true,
    "cache_ttl_seconds": 300
  },
  "triggers": {
    "enabled": true,
    "learn_triggers": true,
    "rules_file": "~/.spark/trigger_rules.yaml"
  },
  "decay": {
    "enabled": false,
    "half_life_days": 30
  }
}
```

---

## Summary

### What We Have
- Working capture, processing, and storage pipeline
- 374 cognitive insights about the user
- Quality gate (Meta-Ralph) with 46.7% pass rate
- Outcome tracking with 89.7% effectiveness
- Embedding infrastructure (unused)

### What's Missing
- Semantic retrieval (currently keyword matching)
- Trigger rules for critical paths
- Outcome-weighted ranking
- User-tuneable retrieval parameters

### What We're Proposing
1. Add semantic embedding-based retrieval
2. Add explicit trigger rules (YAML + learned)
3. Add fusion ranking with outcome weighting
4. Make everything tuneable

### The Goal
Transform from "memory system that stores stuff" to "intelligence system that knows when to surface what" - a critical step toward self-evolving AGI that genuinely understands and helps each user.

---

## Multi-LLM Review: COMPLETE ✅

### Feedback Received From
- LLM 1: Architecture validation + 5 critical implementation gotchas
- LLM 2: "Phenomenal design" + specific code fixes
- LLM 3: "Razor sharp problem diagnosis" + implementation sequencing

### Key Takeaways

**What's Validated:**
- Hybrid approach (semantic + triggers + outcomes) is correct
- Outcome-weighted ranking is the differentiator
- Meta-Ralph quality gate is "load-bearing infrastructure"
- The compounding loop makes this genuinely self-evolving

**What's Fixed:**
- Threshold logic (two-stage: gate + decision)
- Signal separation (trigger_conf ≠ semantic_sim)
- Diversity (MMR + category caps)
- Query quality (intent extraction)
- Cold start (seed pack + EIDOS prior)

**Implementation Order (Consensus):**
1. Semantic index + baseline measurement
2. Fusion ranking with outcome weighting
3. Minimal trigger rules (3-4 critical paths)
4. Learned triggers (with shadow mode)
5. Interrupt system (opt-in only)

---

## Ready for Implementation

### Phase 1 Scope (First Deliverable)

**Build:**
1. `lib/semantic_retriever.py` with fixes from LLM review
2. Embedding index for all 374 cognitive insights (eager, on write)
3. Integration into `advisor.py` behind feature flag
4. Baseline measurement script

**Ship With:**
- Default seed pack (20-30 universal best practices)
- Conservative thresholds (min_similarity=0.7)
- MMR diversity (lambda=0.5)
- Explainability ("why" field on every result)

**Success Metric:**
> % of sessions where at least 1 cognitive insight is surfaced AND later attributed as helpful

**Timeline:** Measure baseline → implement → re-measure → iterate

---

## Appendix: Cold Start Seed Pack (Draft)

```yaml
# ~/.spark/seed_insights.yaml
# Universal best practices for new users
# Tagged as source: system_default (decays as user generates own)

insights:
  - id: security_input_validation
    text: "Always validate user input on the server side, never trust client-side validation alone"
    category: security
    triggers: ["input", "validation", "user data", "form"]

  - id: security_no_secrets
    text: "Never commit secrets, API keys, or credentials to version control"
    category: security
    triggers: ["commit", "env", "api key", "secret", "credential"]

  - id: git_test_before_push
    text: "Run tests before pushing to main/master branch"
    category: git
    triggers: ["push", "main", "master", "merge"]

  - id: destructive_confirm
    text: "Double-check destructive operations (delete, drop, truncate) before executing"
    category: safety
    triggers: ["delete", "drop", "truncate", "rm -rf"]

  - id: deploy_checklist
    text: "Before deploying: run tests, check migrations, verify environment variables"
    category: deployment
    triggers: ["deploy", "release", "production", "prod"]
```

---

## Next Steps

1. **User approves** this refined design
2. **Implement Phase 1** with fixes from LLM review
3. **Measure baseline** before enabling semantic
4. **Enable and iterate** based on north star metric
5. **Phase 2-5** based on outcome data
