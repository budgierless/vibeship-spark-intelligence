# Semantic Advisor Design

**Goal:** Surface the RIGHT learning at the RIGHT time through semantic understanding, not keyword matching.
Navigation hub: `docs/GLOSSARY.md`

---

## Implementation Status (2026-02-05)

Already implemented in this repo:
- `lib/semantic_retriever.py` with trigger rules, MMR diversity, fusion scoring, and intent extraction
- `lib/advisor.py` semantic-first advice with keyword fallback
- `lib/cognitive_learner.py` indexes embeddings on write
- `scripts/semantic_reindex.py` for full reindex
- `TUNEABLES.md` + `~/.spark/trigger_rules.yaml` for configuration

Ops notes:
- Enable via `semantic.enabled=true` and `triggers.enabled=true` in `~/.spark/tuneables.json`
- Rebuild index with `python scripts/semantic_reindex.py`
- Use `spark up --lite` when you want only core services (no dashboards/pulse/watchdog)

---

## Consolidated Proposal Decisions

This design is now the canonical semantic advisor doc and absorbs the archived proposal:
- `docs/archive/root/SEMANTIC_INTELLIGENCE_PROPOSAL.md`

Decisions carried forward:
1. Hybrid retrieval is canonical:
   - triggers + semantic similarity + outcome/reliability weighting.
2. Diversity constraints are required:
   - dedupe and MMR-style controls prevent near-duplicate advice bundles.
3. Intent-aware retrieval is preferred over raw-context embeddings:
   - extract intent first, then rank candidates.
4. Safety defaults are conservative:
   - better to surface fewer high-confidence items than many weak ones.
5. Outcome attribution is the long-term optimization signal:
   - ranking quality improves only when advice usefulness is measured and fed back.

---

## Current State

```
User Action → Advisor → Keyword Matching → Top 8 returned
                              ↓
                      "user" matches "user_understanding:..."
                      "edit" matches "I struggle with Edit..."
```

**Problem:** "user authentication" doesn't match "login security" even though semantically related.

---

## Proposed Architecture

```
User Action → Semantic Advisor
                    ↓
    ┌───────────────┴───────────────┐
    ↓                               ↓
[Trigger Rules]              [Semantic Search]
"If editing auth/* →         Embed query, find
 always surface               similar insights
 security checklist"          by cosine distance
    ↓                               ↓
    └───────────────┬───────────────┘
                    ↓
              [Fusion + Ranking]
              Combine scores with:
              - Semantic similarity (0-1)
              - Trigger match bonus (+0.3)
              - Outcome effectiveness
              - Recency boost
                    ↓
              [Threshold Filter]
              Only surface if score > min_relevance
                    ↓
              [Priority Tiers]
              T1: Critical (interrupt if enabled)
              T2: High (always show)
              T3: Normal (show if space)
              T4: Background (store, don't show)
```

---

## Key Components

### 1. Semantic Index
Store embeddings for all cognitive insights in SQLite (already have `memories_vec` table).

```python
# On insight creation/update
embedding = embed_text(insight.insight + " " + insight.context)
store_embedding(insight_key, embedding)

# On retrieval
query_embedding = embed_text(context)
similar = find_by_cosine(query_embedding, threshold=MIN_SIMILARITY)
```

### 2. Trigger Rules
Explicit rules for high-stakes paths:

```yaml
triggers:
  - pattern: "edit.*auth|security|password|token"
    surface: ["security_checklist", "auth_best_practices"]
    priority: critical

  - pattern: "rm -rf|delete.*prod|drop table"
    surface: ["danger_warnings"]
    priority: critical
    interrupt: true

  - pattern: "deploy|release|push.*main"
    surface: ["pre_deploy_checklist"]
    priority: high
```

### 3. Tuneable Parameters (in TUNEABLES.md)

| Parameter | Default | Description |
|-----------|---------|-------------|
| `semantic.min_similarity` | 0.6 | Min cosine similarity to surface (0-1) |
| `semantic.weight_similarity` | 0.5 | Weight of semantic score in fusion |
| `semantic.weight_recency` | 0.2 | Weight of recency in fusion |
| `semantic.weight_outcome` | 0.3 | Weight of past effectiveness |
| `retrieval.precision_mode` | "high_recall" | "high_precision" or "high_recall" or "adaptive" |
| `decay.enabled` | false | Whether to decay unused insights |
| `decay.half_life_days` | 30 | Days until unused insight loses half reliability |
| `interrupt.enabled` | false | Allow active interrupts |
| `interrupt.min_confidence` | 0.9 | Min confidence to interrupt |
| `interrupt.stakes_threshold` | "critical" | Stakes level to interrupt |

### 4. Interrupt System (Optional)

When `interrupt.enabled = true`:

```
PreToolUse hook:
  1. Get semantic advice
  2. If any advice has:
     - priority == "critical"
     - confidence >= interrupt.min_confidence
     - stakes >= interrupt.stakes_threshold
  3. Then BLOCK tool execution with warning:

     ⚠️ SPARK WARNING
     Pattern: "rm -rf on project directory"
     Past outcome: Lost uncommitted work (2026-01-15)

     Advice: Always run 'git status' first

     Continue anyway? [y/N]
```

---

## Implementation Plan

### Phase 1: Semantic Index (Core)
1. Add embedding generation on insight creation
2. Store embeddings in `memories_vec` table
3. Add `get_insights_semantic()` method to cognitive_learner
4. Wire into Advisor

### Phase 2: Trigger Rules
1. Add `~/.spark/trigger_rules.yaml`
2. Parse rules on advisor init
3. Check triggers before semantic search
4. Merge trigger matches with semantic results

### Phase 3: Tuneables
1. Add semantic tuneables to TUNEABLES.md
2. Load in advisor from `~/.spark/tuneables.json`
3. Expose in Spark Pulse dashboard

### Phase 4: Interrupt System (Optional)
1. Add interrupt check in observe.py PreToolUse
2. Add hook response for blocking
3. Track interrupt outcomes for learning

---

## Example Flow

**User runs:** `Edit src/auth/login.py`

**Old system:**
- Keyword match on "Edit" → tool struggles
- Keyword match on "auth" → nothing (no exact match)
- Returns generic tool warnings

**New system:**
1. **Trigger check:** "auth" pattern → surfaces "security_checklist" (priority: high)
2. **Semantic search:** "editing authentication login" →
   - 0.87 similarity: "Always validate tokens server-side"
   - 0.82 similarity: "User prefers JWT over sessions"
   - 0.79 similarity: "Never log passwords, even hashed"
3. **Fusion:** Combine trigger + semantic, rank by score
4. **Return:** Top 8, security checklist first

---

## Questions for Validation

1. Should semantic embeddings be computed lazily (on first retrieval) or eagerly (on insight creation)?
2. Should trigger rules live in YAML (human-editable) or be learned from patterns?
3. What's the cold-start strategy for new users with no insights?
4. Should interrupt require explicit user opt-in?

---

## Next Steps

1. Validate this design with user
2. Check if fastembed is installed/working
3. Implement Phase 1 (semantic index)
4. Test on real retrieval scenarios
5. Iterate based on outcomes

---

## DETAILED SPECIFICATIONS

### A. Code Integration Points

#### File: `lib/semantic_retriever.py` (NEW)

```python
"""
Semantic retrieval for cognitive insights.

Configurable embedding providers:
- local: fastembed (default, free, offline)
- openai: text-embedding-3-small/large
- cohere: embed-english-v3
- voyage: voyage-large-2 (best for code)
"""

from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
from pathlib import Path
import json

@dataclass
class SemanticResult:
    insight_key: str
    insight_text: str
    similarity: float
    source: str  # "semantic", "trigger", "hybrid"
    priority: str  # "critical", "high", "normal", "background"

class SemanticRetriever:
    def __init__(self, config: Optional[Dict] = None):
        self.config = config or self._load_config()
        self.embedder = self._init_embedder()
        self.trigger_matcher = TriggerMatcher()

    def _load_config(self) -> Dict:
        """Load from ~/.spark/tuneables.json"""
        tuneables_file = Path.home() / ".spark" / "tuneables.json"
        defaults = {
            "embedding_provider": "local",  # local, openai, cohere, voyage
            "embedding_model": "BAAI/bge-small-en-v1.5",
            "min_similarity": 0.6,
            "weight_similarity": 0.5,
            "weight_recency": 0.2,
            "weight_outcome": 0.3,
            "precision_mode": "high_recall",  # high_recall, high_precision, adaptive
        }
        if tuneables_file.exists():
            data = json.loads(tuneables_file.read_text())
            semantic = data.get("semantic", {})
            defaults.update(semantic)
        return defaults

    def _init_embedder(self):
        """Initialize embedding provider based on config."""
        provider = self.config.get("embedding_provider", "local")

        if provider == "local":
            from lib.embeddings import embed_text
            return LocalEmbedder()
        elif provider == "openai":
            return OpenAIEmbedder(model=self.config.get("embedding_model"))
        elif provider == "cohere":
            return CohereEmbedder()
        elif provider == "voyage":
            return VoyageEmbedder()
        else:
            return LocalEmbedder()  # fallback

    def retrieve(
        self,
        query: str,
        insights: Dict,  # insight_key -> CognitiveInsight
        limit: int = 10,
    ) -> List[SemanticResult]:
        """
        Main retrieval method combining triggers + semantic search.

        1. Check trigger rules (explicit patterns)
        2. Semantic search (embedding similarity)
        3. Fuse and rank results
        """
        results = []

        # 1. Trigger rules (fast, explicit)
        trigger_matches = self.trigger_matcher.match(query)
        for match in trigger_matches:
            if match.insight_key in insights:
                results.append(SemanticResult(
                    insight_key=match.insight_key,
                    insight_text=insights[match.insight_key].insight,
                    similarity=1.0,  # Trigger = perfect match
                    source="trigger",
                    priority=match.priority,
                ))

        # 2. Semantic search (slower, learned)
        query_embedding = self.embedder.embed(query)
        if query_embedding:
            semantic_matches = self._semantic_search(
                query_embedding, insights, limit=limit * 2
            )
            for key, similarity in semantic_matches:
                # Skip if already from trigger
                if any(r.insight_key == key for r in results):
                    continue
                results.append(SemanticResult(
                    insight_key=key,
                    insight_text=insights[key].insight,
                    similarity=similarity,
                    source="semantic",
                    priority=self._infer_priority(similarity),
                ))

        # 3. Fuse and rank
        ranked = self._rank_results(results, insights)

        # 4. Filter by threshold
        threshold = self._get_threshold()
        filtered = [r for r in ranked if r.similarity >= threshold]

        return filtered[:limit]

    def _semantic_search(
        self,
        query_vec: List[float],
        insights: Dict,
        limit: int,
    ) -> List[Tuple[str, float]]:
        """Find insights by embedding similarity."""
        # Load pre-computed embeddings from index
        index = self._load_index()

        scores = []
        for key in insights:
            if key in index:
                insight_vec = index[key]
                sim = self._cosine_similarity(query_vec, insight_vec)
                scores.append((key, sim))

        # Sort by similarity descending
        scores.sort(key=lambda x: -x[1])
        return scores[:limit]

    def _rank_results(
        self,
        results: List[SemanticResult],
        insights: Dict,
    ) -> List[SemanticResult]:
        """Apply fusion ranking with configurable weights."""
        w_sim = self.config.get("weight_similarity", 0.5)
        w_rec = self.config.get("weight_recency", 0.2)
        w_out = self.config.get("weight_outcome", 0.3)

        def score(r: SemanticResult) -> float:
            base = r.similarity * w_sim

            # Recency boost
            insight = insights.get(r.insight_key)
            if insight and hasattr(insight, 'last_seen'):
                recency = self._recency_score(insight.last_seen)
                base += recency * w_rec

            # Outcome effectiveness boost
            if insight and hasattr(insight, 'reliability'):
                base += insight.reliability * w_out

            # Priority boost
            priority_boost = {
                "critical": 0.3,
                "high": 0.2,
                "normal": 0.0,
                "background": -0.1,
            }
            base += priority_boost.get(r.priority, 0.0)

            return base

        results.sort(key=score, reverse=True)
        return results

    def _get_threshold(self) -> float:
        """Get similarity threshold based on precision mode."""
        mode = self.config.get("precision_mode", "high_recall")
        base = self.config.get("min_similarity", 0.6)

        if mode == "high_precision":
            return base + 0.15  # Stricter
        elif mode == "high_recall":
            return base - 0.15  # More permissive
        else:  # adaptive
            return base
```

#### File: `lib/advisor.py` (MODIFIED)

```python
# In advise() method, replace:
#   advice_list.extend(self._get_cognitive_advice(tool_name, context))
# With:

    # Use semantic retriever if enabled
    if self._use_semantic_retrieval():
        from .semantic_retriever import get_semantic_retriever
        retriever = get_semantic_retriever()
        semantic_results = retriever.retrieve(
            query=context,
            insights=self.cognitive.insights,
            limit=10,
        )
        advice_list.extend(self._results_to_advice(semantic_results))
    else:
        # Fallback to keyword matching
        advice_list.extend(self._get_cognitive_advice(tool_name, context))
```

#### File: `lib/cognitive_learner.py` (MODIFIED)

```python
# In add_insight() method, add:

def add_insight(self, ...):
    # ... existing code ...

    # Index embedding for semantic search
    self._index_embedding(insight_key, insight_text, insight_context)

def _index_embedding(self, key: str, text: str, context: str):
    """Compute and store embedding for semantic search."""
    try:
        from .semantic_retriever import get_semantic_retriever
        retriever = get_semantic_retriever()
        if retriever.config.get("index_on_write", True):
            combined = f"{text} {context}"
            retriever.index_insight(key, combined)
    except Exception:
        pass  # Don't break writes if indexing fails
```

---

### B. Fusion Algorithm Detail

```
FUSION SCORE = (similarity × W_SIM) + (recency × W_REC) + (effectiveness × W_OUT) + priority_boost

Where:
- similarity: Cosine similarity between query and insight embeddings (0.0 - 1.0)
- recency: Time-decay score (1.0 = just now, 0.5 = half_life days ago, 0.0 = very old)
- effectiveness: Historical outcome rate for this insight (0.0 - 1.0)
- priority_boost: Explicit boost for trigger matches
  - critical: +0.3
  - high: +0.2
  - normal: +0.0
  - background: -0.1

Default weights (tuneable):
- W_SIM = 0.5 (semantic similarity is primary signal)
- W_REC = 0.2 (recent insights are more relevant)
- W_OUT = 0.3 (past effectiveness matters)

Threshold filtering:
- high_precision mode: score >= 0.75 (fewer results, higher confidence)
- high_recall mode: score >= 0.45 (more results, may include some noise)
- adaptive mode: score >= 0.60 (balanced)
```

**Example calculation:**

```
Query: "edit authentication code"
Insight: "Always validate tokens server-side" (reliability: 0.85, last_seen: 2 days ago)

similarity = 0.87 (embedding cosine)
recency = 0.90 (recent)
effectiveness = 0.85 (reliable)
priority = "normal" (no trigger match)

SCORE = (0.87 × 0.5) + (0.90 × 0.2) + (0.85 × 0.3) + 0.0
      = 0.435 + 0.180 + 0.255
      = 0.87

Result: SURFACED (above all thresholds)
```

---

### C. Performance & Scaling Implications

#### Memory Usage

| Insights Count | Embedding Size | Index Memory |
|----------------|----------------|--------------|
| 100 | 384 dims × 4 bytes | ~150 KB |
| 1,000 | 384 dims × 4 bytes | ~1.5 MB |
| 10,000 | 384 dims × 4 bytes | ~15 MB |
| 100,000 | 384 dims × 4 bytes | ~150 MB |

**Mitigation:** Store embeddings in SQLite (disk), load on-demand with LRU cache.

#### Latency

| Operation | Local Embed | OpenAI Embed | Search (1K) | Search (10K) |
|-----------|-------------|--------------|-------------|--------------|
| Embed query | ~10ms | ~100ms | - | - |
| Cosine search | - | - | ~5ms | ~50ms |
| Total | ~15ms | ~105ms | ~15ms | ~55ms |

**Mitigation:**
- Pre-compute insight embeddings on write (background)
- Cache query embeddings for repeated queries
- Use approximate nearest neighbor (ANN) for >10K insights

#### Scaling Strategy

```
Insights < 1,000:  Brute-force cosine search (simple, fast enough)
Insights 1K-10K:   SQLite with indexed vectors
Insights > 10K:    Approximate search (HNSW index via faiss or annoy)
```

#### Background Indexing

```python
# bridge_worker.py addition
def run_bridge_cycle():
    # ... existing processing ...

    # Background: Index any unindexed insights
    index_pending_insights(batch_size=50)
```

---

### D. Configurable Embedding Providers

#### Tuneable Configuration (~/.spark/tuneables.json)

```json
{
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
    "half_life_days": 30,
    "min_reliability": 0.1
  }
}
```

#### Provider Implementations

```python
class LocalEmbedder:
    """Free, offline, good quality."""
    def embed(self, text: str) -> List[float]:
        from lib.embeddings import embed_text
        return embed_text(text)

class OpenAIEmbedder:
    """Better quality, requires API key, has cost."""
    def __init__(self, model: str = "text-embedding-3-small"):
        self.model = model
        self.client = openai.OpenAI()  # Uses OPENAI_API_KEY env

    def embed(self, text: str) -> List[float]:
        response = self.client.embeddings.create(
            model=self.model,
            input=text,
        )
        return response.data[0].embedding

class CohereEmbedder:
    """Good quality, has free tier."""
    def __init__(self):
        import cohere
        self.client = cohere.Client()  # Uses COHERE_API_KEY env

    def embed(self, text: str) -> List[float]:
        response = self.client.embed(
            texts=[text],
            model="embed-english-v3.0",
        )
        return response.embeddings[0]
```

---

### E. Trigger Rules (YAML + Learned)

#### Static Rules (~/.spark/trigger_rules.yaml)

```yaml
# User-editable trigger rules
version: 1

rules:
  # Security-related
  - name: auth_security
    pattern: "auth|login|password|token|session|jwt|oauth"
    context_pattern: "edit|write|modify"
    surface:
      - security_checklist
      - auth_best_practices
    priority: high

  # Danger patterns
  - name: destructive_commands
    pattern: "rm -rf|delete.*prod|drop table|truncate"
    surface:
      - danger_confirmation
    priority: critical
    interrupt: true

  # Deployment
  - name: pre_deploy
    pattern: "deploy|release|push.*main|merge.*master"
    surface:
      - deploy_checklist
      - rollback_procedure
    priority: high

# Learned triggers (auto-populated by Spark)
learned:
  - pattern: "phaser|game.*dev|sprite"
    surface:
      - game_dev_patterns
    confidence: 0.82
    learned_from: "session_2026-01-15"
```

#### Trigger Learning

```python
def learn_trigger(context: str, insight_key: str, outcome: str):
    """
    Learn new trigger patterns from successful retrievals.

    If an insight is retrieved semantically AND has a good outcome,
    extract patterns from the context for future explicit triggering.
    """
    if outcome != "good":
        return

    # Extract salient patterns from context
    patterns = extract_patterns(context)  # NLP-based

    # Add to learned triggers if confidence high enough
    learned_triggers.add(
        pattern=patterns,
        surface=[insight_key],
        confidence=0.7,  # Starts low, increases with validation
    )
```

---

## Summary: What Changes

| Component | Change Type | Risk | Effort |
|-----------|-------------|------|--------|
| `lib/semantic_retriever.py` | NEW | Low | Medium |
| `lib/advisor.py` | MODIFY (additive) | Low | Low |
| `lib/cognitive_learner.py` | MODIFY (additive) | Low | Low |
| `lib/embeddings.py` | EXTEND (providers) | Low | Medium |
| `~/.spark/tuneables.json` | EXTEND | None | Low |
| `~/.spark/trigger_rules.yaml` | NEW | None | Low |
| `TUNEABLES.md` | EXTEND | None | Low |

**Backward Compatibility:** 100% - semantic retrieval is opt-in via `semantic.enabled` tuneable. Default behavior unchanged until user enables it.
