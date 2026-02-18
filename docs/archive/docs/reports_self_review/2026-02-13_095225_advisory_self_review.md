# Advisory Self-Review (2026-02-13T09:52:25.939811+00:00)

## Window
- Hours analyzed: 12
- State: unclear

## Core Metrics
- Advisory rows: 77
- Advisory trace coverage: 0/77 (0.0%)
- Advice items emitted: 455
- Engine events: 0
- Engine trace coverage: 0/0 (0.0%)
- Fallback share (delivered): 0.0%
- Strict action rate: None
- Strict effectiveness rate: None
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
- Yes. Top repeated advisories account for ~48.12% of all advice items in this window.

## Top Repeated Advice (Noise Candidates)
- 47x (10.33%) [Caution] I struggle with WebFetch fails with other tasks
- 47x (10.33%) [Caution] I struggle with WebFetch fails with other (recovered) tasks
- 35x (7.69%) [Caution] I struggle with WebFetch_error tasks
- 32x (7.03%) instead of this being a question let's make it better and say a collection evolution network with guardrails or should we say the guardrails?
- 30x (6.59%) Overall: **good direction, partially stable**.

- ✅ **Phase‑1 plugin baseline works** (send path is live, commits pushed).
- ✅ We shipped **latency tuning + ins
- 28x (6.15%) [Thu 2026-02-12 18:54 GMT+4] For some reason the second message that came here on the Pulse chat was again the previous message let's build the number one mod e

## Bad Outcome Records
- None in this window.

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
