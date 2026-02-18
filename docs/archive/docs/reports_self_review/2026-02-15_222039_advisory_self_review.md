# Advisory Self-Review (2026-02-15T22:20:39.652227+00:00)

## Window
- Hours analyzed: 12.0
- State: unclear

## Core Metrics
- Advisory rows: 2001
- Advisory trace coverage: 1983/2001 (99.1%)
- Advice items emitted: 5320
- Non-benchmark advisory rows: 1654 (excluded 347)
- Engine events: 500
- Engine trace coverage: 500/500 (100.0%)
- Fallback share (delivered): 0.0%
- Strict action rate: 0.788
- Strict effectiveness rate: 0.8046
- Trace mismatch count: 105

## Honest Answers
### Did learnings help make better decisions?
- Yes, but unevenly. Trace-bound clusters show good outcomes, mostly from cognitive/self-awareness sources.
- Mind usage exists but is still low-share in retrieval mix.

### Examples with trace IDs
- `direct-trace2-1771193682-1` | tool `Read` | source `cognitive` | Always Read a file before Edit to verify current content
- `direct-trace2-1771193681-0` | tool `Read` | source `cognitive` | Always Read a file before Edit to verify current content
- `direct-trace-1771193623-0` | tool `Read` | source `cognitive` | Always Read a file before Edit to verify current content
- `delta-variantD_agentic_rate_035-20260215_215505-0033` | tool `Edit` | source `cognitive` | Always Read a file before Edit to verify current content
- `delta-variantD_agentic_rate_035-20260215_215505-0024` | tool `Read` | source `cognitive` | Always Read a file before Edit to verify current content
- `delta-variantD_agentic_rate_035-20260215_215505-0011` | tool `WebFetch` | source `self_awareness` | [Caution] I struggle with WebFetch fails with other tasks
- `delta-variantD_agentic_rate_035-20260215_215505-0008` | tool `Read` | source `cognitive` | Always Read a file before Edit to verify current content
- `delta-variantD_agentic_rate_035-20260215_215505-0007` | tool `WebFetch` | source `self_awareness` | [Caution] I struggle with WebFetch fails with other tasks

### Were there misses despite memory existing?
- Mixed. Fallback was not dominant in this window; evaluate misses via trace coverage and repeated-noise patterns.
- Engine trace coverage is healthy enough for stronger attribution confidence.

### Were unnecessary advisories/memories triggered?
- Yes. Top repeated advisories account for ~90.65% of all advice items in this window.

## Top Repeated Advice (Noise Candidates)
- 1254x (23.57%) When using Bash, remember: Do it, and is this system fully connected to spark intelligence flow right now, for spark to e
- 1239x (23.29%) lets push gitthub, and then clean up the whole system except this spark, and at some point we were thinking to bring the council of 50, as the agents can you se
- 848x (15.94%) Always Read a file before Edit to verify current content
- 653x (12.27%) Constraint: in **exactly one state** at all times
- 434x (8.16%) [Caution] I struggle with WebFetch fails with other tasks
- 395x (7.42%) [Caution] I struggle with WebFetch fails with other (recovered) tasks

## Top Repeated Advice (Non-Benchmark Window)
- 1214x (24.99%) When using Bash, remember: Do it, and is this system fully connected to spark intelligence flow right now, for spark to e
- 1202x (24.75%) lets push gitthub, and then clean up the whole system except this spark, and at some point we were thinking to bring the council of 50, as the agents can you se
- 814x (16.76%) Always Read a file before Edit to verify current content
- 419x (8.63%) Constraint: in **exactly one state** at all times
- 402x (8.28%) [Caution] I struggle with WebFetch fails with other tasks
- 393x (8.09%) [Caution] I struggle with WebFetch fails with other (recovered) tasks

## Bad Outcome Records
- trace `delta-variantD_agentic_rate_035-20260215_215505-0003` | source `auto_created` | insight `None` | 07196b05236b
- trace `delta-variantC_plus-20260215_210227-0003` | source `auto_created` | insight `None` | a219f91f4e62
- trace `delta-variantC-20260215_204832-0003` | source `auto_created` | insight `None` | 124253e6b102
- trace `delta-variantB_post_bomfix-20260215_195701-0021` | source `auto_created` | insight `None` | 539a804371ba
- trace `delta-variantB_post_bomfix-20260215_195701-0018` | source `auto_created` | insight `None` | b7ebfd1f4b57
- trace `delta-variantB_post_bomfix-20260215_195701-0003` | source `auto_created` | insight `None` | 357187b902ca
- trace `delta-variantB_post-20260215_195142-0021` | source `auto_created` | insight `None` | 7e6b6f2f77c8
- trace `delta-variantB_post-20260215_195142-0018` | source `auto_created` | insight `None` | e9198ff05294
- trace `delta-variantB_post-20260215_195142-0003` | source `auto_created` | insight `None` | 6296a96b34ab
- trace `delta-variantB_pre-20260215_194731-0021` | source `auto_created` | insight `None` | 48c4e0225830

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
