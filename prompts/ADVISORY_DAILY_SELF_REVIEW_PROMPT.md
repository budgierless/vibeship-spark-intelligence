# Advisory Daily Self-Review Prompt

Run this at mid-day and end-of-day using the latest advisory self-review report.

Input:
- Latest file in `docs/reports/*_advisory_self_review.md`
- Optional extra telemetry from:
  - `~/.spark/advisory_engine.jsonl`
  - `~/.spark/advisor/recent_advice.jsonl`
  - `~/.spark/meta_ralph/outcome_tracking.json`

Rules:
- No claims without evidence.
- Every claimed success/failure must include at least one trace id if available.
- If trace id is missing, mark `unverified`.
- Prefer simplification/tuning over adding features.

Answer exactly these questions:
1. Did we use learnings while working, with concrete examples?
2. Which trace ids prove advisory influenced better decisions?
3. Where did we fail to pull the right memory at the right time, despite having it?
4. Which advisories/memories were unnecessary or repetitive?
5. What should be tuned immediately to improve advisory signal quality?
6. What should be tuned to improve memory-to-advice conversion quality?
7. What should be removed (not added) to reduce noise and operator load?
8. What are the top 3 risks of self-delusion in this review?

Required output format:

## Evidence Summary
- Window analyzed:
- Advisory rows:
- Advisory trace coverage:
- Engine fallback share:
- Strict action rate:
- Strict effectiveness rate:

## Trace-Backed Wins
- `<trace_id>`: what advisory/memory changed, what action changed, what improved

## Trace-Backed Misses
- `<trace_id or unverified>`: what should have been retrieved, why it likely missed

## Noise Inventory
- repeated advisories with counts + share
- low-value memory/advice classes to suppress

## Keep/Fix/Cut (Tuning Only)
- KEEP:
- FIX:
- CUT:

## Next 3 Tuning Actions
- action, expected metric movement, rollback condition

## Honesty Check
- 3 ways this review might be wrong and what evidence would disprove it
