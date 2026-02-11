# Report: Proposal-Quality Scoring System Added
Date: 2026-02-11
Owner: Spark

## Context
Need a structured way to evaluate the quality of self-improvement proposals themselves.

## What was added
In `spark-forge`:
- `src/spark_forge/proposal_quality.py`
  - Weighted scoring function:
    - empirical impact (35%)
    - novelty (20%)
    - depth/root-cause alignment (20%)
    - sophistication floor (15%)
    - composability (10%)
  - Penalties for non-measurable/undefined acceptance/no execution path.
  - Baseline scoring helper for current Phase-2 proposals.
- `docs/PROPOSAL_QUALITY_SCORING.md`

## Validation
- `py_compile` passed.
- Baseline scoring output generated successfully:
  - preflight gate: 69.7
  - decision contract: 74.6
  - two-layer gate: 67.6

## Commit
- `spark-forge` commit: `48e2e72`

## Decision
Keep. Use this rubric before adopting future self-mod proposals.
