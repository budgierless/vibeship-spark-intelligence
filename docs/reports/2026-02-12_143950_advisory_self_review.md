# Advisory Self-Review (2026-02-12T14:39:50.301142+00:00)

## Window
- Hours analyzed: 12
- State: unclear

## Core Metrics
- Advisory rows: 211
- Advisory trace coverage: 0/211 (0.0%)
- Advice items emitted: 1648
- Engine events: 1
- Engine trace coverage: 0/1 (0.0%)
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
- Yes. Top repeated advisories account for ~55.99% of all advice items in this window.

## Top Repeated Advice (Noise Candidates)
- 210x (12.74%) [Caution] I struggle with WebFetch fails with other tasks
- 210x (12.74%) [Caution] I struggle with WebFetch fails with other (recovered) tasks
- 167x (10.13%) [Caution] I struggle with WebFetch_error tasks
- 121x (7.34%) [Caution] I struggle with Glob_error tasks
- 110x (6.67%) Mac Mini + AI agent setup trending as "money printer" but requires TAO subnet participation for actual returns - not just local inference
- 105x (6.37%) "formatting": "ALWAYS put 'multiplier granted' on its own line with a line break before it. This makes it scannable when people scroll replies and creates

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
