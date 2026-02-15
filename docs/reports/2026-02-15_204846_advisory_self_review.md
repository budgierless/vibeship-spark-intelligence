# Advisory Self-Review (2026-02-15T20:48:46.271156+00:00)

## Window
- Hours analyzed: 1
- State: improving

## Core Metrics
- Advisory rows: 616
- Advisory trace coverage: 616/616 (100.0%)
- Advice items emitted: 1230
- Non-benchmark advisory rows: 269 (excluded 347)
- Engine events: 500
- Engine trace coverage: 500/500 (100.0%)
- Fallback share (delivered): 0.0%
- Strict action rate: 0.4607
- Strict effectiveness rate: 0.9146
- Trace mismatch count: 96

## Honest Answers
### Did learnings help make better decisions?
- Yes, but unevenly. Trace-bound clusters show good outcomes, mostly from cognitive/self-awareness sources.
- Mind usage exists but is still low-share in retrieval mix.

### Examples with trace IDs
- `delta-variantC-20260215_204832-0011` | tool `WebFetch` | source `self_awareness` | [Caution] I struggle with WebFetch fails with other tasks
- `delta-variantC-20260215_204832-0010` | tool `Task` | source `cognitive` | Constraint: in **exactly one state** at all times
- `delta-variantC-20260215_204832-0008` | tool `Read` | source `cognitive` | Always Read a file before Edit to verify current content
- `delta-variantC-20260215_204832-0007` | tool `WebFetch` | source `self_awareness` | [Caution] I struggle with WebFetch fails with other tasks
- `delta-variantC-20260215_204832-0005` | tool `Task` | source `cognitive` | Constraint: in **exactly one state** at all times
- `delta-variantC-20260215_204832-0004` | tool `Read` | source `cognitive` | Always Read a file before Edit to verify current content
- `delta-variantC-20260215_204832-0003` | tool `WebFetch` | source `self_awareness` | [Caution] I struggle with WebFetch fails with other tasks
- `delta-variantC-20260215_204832-0002` | tool `Task` | source `cognitive` | Constraint: in **exactly one state** at all times

### Were there misses despite memory existing?
- Mixed. Fallback was not dominant in this window; evaluate misses via trace coverage and repeated-noise patterns.
- Engine trace coverage is healthy enough for stronger attribution confidence.

### Were unnecessary advisories/memories triggered?
- Yes. Top repeated advisories account for ~87.39% of all advice items in this window.

## Top Repeated Advice (Noise Candidates)
- 302x (24.55%) Constraint: in **exactly one state** at all times
- 226x (18.37%) When using Bash, remember: Do it, and is this system fully connected to spark intelligence flow right now, for spark to e
- 223x (18.13%) lets push gitthub, and then clean up the whole system except this spark, and at some point we were thinking to bring the council of 50, as the agents can you se
- 161x (13.09%) Always Read a file before Edit to verify current content
- 98x (7.97%) [Caution] I struggle with WebFetch fails with other tasks
- 65x (5.28%) [Caution] I struggle with WebFetch fails with other (recovered) tasks

## Top Repeated Advice (Non-Benchmark Window)
- 186x (24.25%) lets push gitthub, and then clean up the whole system except this spark, and at some point we were thinking to bring the council of 50, as the agents can you se
- 186x (24.25%) When using Bash, remember: Do it, and is this system fully connected to spark intelligence flow right now, for spark to e
- 127x (16.56%) Always Read a file before Edit to verify current content
- 68x (8.87%) Constraint: in **exactly one state** at all times
- 66x (8.6%) [Caution] I struggle with WebFetch fails with other tasks
- 63x (8.21%) [Caution] I struggle with WebFetch fails with other (recovered) tasks

## Bad Outcome Records
- trace `delta-variantC-20260215_204832-0003` | source `auto_created` | insight `None` | 124253e6b102
- trace `delta-variantB_post_bomfix-20260215_195701-0021` | source `auto_created` | insight `None` | 539a804371ba
- trace `delta-variantB_post_bomfix-20260215_195701-0018` | source `auto_created` | insight `None` | b7ebfd1f4b57
- trace `delta-variantB_post_bomfix-20260215_195701-0003` | source `auto_created` | insight `None` | 357187b902ca
- trace `delta-variantB_post-20260215_195142-0021` | source `auto_created` | insight `None` | 7e6b6f2f77c8
- trace `delta-variantB_post-20260215_195142-0018` | source `auto_created` | insight `None` | e9198ff05294
- trace `delta-variantB_post-20260215_195142-0003` | source `auto_created` | insight `None` | 6296a96b34ab

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
