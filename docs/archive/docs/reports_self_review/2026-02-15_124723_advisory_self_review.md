# Advisory Self-Review (2026-02-15T12:47:23.089518+00:00)

## Window
- Hours analyzed: 12
- State: unclear

## Core Metrics
- Advisory rows: 11
- Advisory trace coverage: 0/11 (0.0%)
- Advice items emitted: 25
- Engine events: 13
- Engine trace coverage: 3/13 (23.08%)
- Fallback share (delivered): 0.0%
- Strict action rate: 0.6667
- Strict effectiveness rate: 0.75
- Trace mismatch count: 0

## Honest Answers
### Did learnings help make better decisions?
- Yes, but unevenly. Trace-bound clusters show good outcomes, mostly from cognitive/self-awareness sources.
- Mind usage exists but is still low-share in retrieval mix.

### Examples with trace IDs
- No trace-bound advisory rows found in this window.

### Were there misses despite memory existing?
- Mixed. Fallback was not dominant in this window; evaluate misses via trace coverage and repeated-noise patterns.
- Engine trace coverage is low; evidence linkage is incomplete in the engine path.

### Were unnecessary advisories/memories triggered?
- Yes. Top repeated advisories account for ~92.0% of all advice items in this window.

## Top Repeated Advice (Noise Candidates)
- 6x (24.0%) When using Bash, remember: Do it, and is this system fully connected to spark intelligence flow right now, for spark to e
- 6x (24.0%) lets push gitthub, and then clean up the whole system except this spark, and at some point we were thinking to bring the council of 50, as the agents can you se
- 3x (12.0%) Consider skill [Team Communications]: Your team can't execute what they don't understand. And they won't buy in to what they don't feel part of. Internal comm
- 3x (12.0%) Constraint: in **exactly one state** at all times
- 3x (12.0%) [openclaw_moltbook] RT @iancr: We built Agent Payments with @Ledger for the @circle @USDC Hackathon — agents propose, humans sign, your Ledger enforces.

🎬 Dem…
- 2x (8.0%) Always Read a file before Edit to verify current content

## Bad Outcome Records
- trace `2d9e3d427699ddf6` | source `opportunity_scanner` | insight `opportunity:compounding_learning` | opp:34eb0962e4de61df

## Optimization (No New Features)
- Increase advisory repeat cooldowns and tool cooldowns to reduce duplicate cautions.
- Keep `include_mind=true` with stale gating and minimum salience to improve cross-session quality without flooding.
- Prefer fewer higher-rank items (`advisor.max_items` and `advisor.min_rank_score`) to improve signal density.
- Improve strict trace discipline in advisory engine events before trusting aggregate success counters.

## Questions To Ask Every Review
1. Which advisories changed a concrete decision, with trace IDs?
2. Which advisories repeated without adding new actionability?
3. Where did fallback dominate and why?
4. Which sources had strict-good outcomes vs non-strict optimism?
5. What is one simplification we can do before adding anything new?
