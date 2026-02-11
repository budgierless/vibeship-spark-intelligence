# Experiment: Phase 3b — Hybrid+Agentic Retrieval in Spark Intelligence Core
Date: 2026-02-11
Owner: Spark

## Hypothesis
Applying hybrid + lightweight agentic retrieval inside Spark Intelligence advisor path (not just spark-forge) should improve relevance of cognitive advice and reduce embeddings-only misses.

## Change
- Updated `lib/advisor.py`:
  - `_get_semantic_cognitive_advice(...)` now runs multi-query retrieval:
    - primary context query
    - 1–3 facet-expanded queries (agentic expansion)
  - merges candidates by best fusion score per insight
  - applies lexical-overlap rerank on top of semantic fusion
  - emits source label `semantic-hybrid` for non-trigger hybrid results
- Added helper methods:
  - `_extract_agentic_queries(...)`
  - `_lexical_overlap_score(...)`

## Validation
- `python -m py_compile lib/advisor.py` passed.

## Result
- Shipped in `vibeship-spark-intelligence` commit `789a9f6`.

## Decision
- Keep and monitor acted-on advisory rate + duplicate failure recurrence.
