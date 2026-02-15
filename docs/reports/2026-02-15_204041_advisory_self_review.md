# Advisory Self-Review (2026-02-15T20:40:41.652733+00:00)

## Window
- Hours analyzed: 1
- State: unclear

## Core Metrics
- Advisory rows: 651
- Advisory trace coverage: 651/651 (100.0%)
- Advice items emitted: 1487
- Non-benchmark advisory rows: 367 (excluded 284)
- Engine events: 500
- Engine trace coverage: 500/500 (100.0%)
- Fallback share (delivered): 0.0%
- Strict action rate: 0.5342
- Strict effectiveness rate: 0.8953
- Trace mismatch count: 75

## Honest Answers
### Did learnings help make better decisions?
- Yes, but unevenly. Trace-bound clusters show good outcomes, mostly from cognitive/self-awareness sources.
- Mind usage exists but is still low-share in retrieval mix.

### Examples with trace IDs
- `trace-low-a` | tool `Task` | source `cognitive` | Constraint: in **exactly one state** at all times
- `advisory-bench-strict-20260215203701-cb1967-0018` | tool `Task` | source `trigger` | Validate authentication inputs server-side and avoid trusting client checks.
- `advisory-bench-strict-20260215203701-cb1967-0017` | tool `Bash` | source `cognitive` | Constraint: in **exactly one state** at all times
- `advisory-bench-strict-20260215203701-cb1967-0016` | tool `Task` | source `cognitive` | Constraint: in **exactly one state** at all times
- `advisory-bench-strict-20260215203701-cb1967-0015` | tool `Task` | source `cognitive` | Constraint: in **exactly one state** at all times
- `advisory-bench-strict-20260215203701-cb1967-0013` | tool `Read` | source `cognitive` | Constraint: in **exactly one state** at all times
- `advisory-bench-strict-20260215203701-cb1967-0012` | tool `Task` | source `cognitive` | Constraint: in **exactly one state** at all times
- `advisory-bench-strict-20260215203701-cb1967-0011` | tool `Task` | source `cognitive` | Constraint: in **exactly one state** at all times

### Were there misses despite memory existing?
- Mixed. Fallback was not dominant in this window; evaluate misses via trace coverage and repeated-noise patterns.
- Engine trace coverage is healthy enough for stronger attribution confidence.

### Were unnecessary advisories/memories triggered?
- Yes. Top repeated advisories account for ~88.64% of all advice items in this window.

## Top Repeated Advice (Noise Candidates)
- 310x (20.85%) When using Bash, remember: Do it, and is this system fully connected to spark intelligence flow right now, for spark to e
- 309x (20.78%) Constraint: in **exactly one state** at all times
- 307x (20.65%) lets push gitthub, and then clean up the whole system except this spark, and at some point we were thinking to bring the council of 50, as the agents can you se
- 196x (13.18%) Always Read a file before Edit to verify current content
- 104x (6.99%) [Caution] I struggle with WebFetch fails with other tasks
- 92x (6.19%) [Caution] I struggle with WebFetch fails with other (recovered) tasks

## Top Repeated Advice (Non-Benchmark Window)
- 270x (24.84%) lets push gitthub, and then clean up the whole system except this spark, and at some point we were thinking to bring the council of 50, as the agents can you se
- 270x (24.84%) When using Bash, remember: Do it, and is this system fully connected to spark intelligence flow right now, for spark to e
- 180x (16.56%) Always Read a file before Edit to verify current content
- 93x (8.56%) Constraint: in **exactly one state** at all times
- 90x (8.28%) [Caution] I struggle with WebFetch fails with other tasks
- 90x (8.28%) [Caution] I struggle with WebFetch fails with other (recovered) tasks

## Bad Outcome Records
- trace `delta-variantB_post_bomfix-20260215_195701-0021` | source `auto_created` | insight `None` | 539a804371ba
- trace `delta-variantB_post_bomfix-20260215_195701-0018` | source `auto_created` | insight `None` | b7ebfd1f4b57
- trace `delta-variantB_post_bomfix-20260215_195701-0003` | source `auto_created` | insight `None` | 357187b902ca
- trace `delta-variantB_post-20260215_195142-0021` | source `auto_created` | insight `None` | 7e6b6f2f77c8
- trace `delta-variantB_post-20260215_195142-0018` | source `auto_created` | insight `None` | e9198ff05294
- trace `delta-variantB_post-20260215_195142-0003` | source `auto_created` | insight `None` | 6296a96b34ab
- trace `delta-variantB_pre-20260215_194731-0021` | source `auto_created` | insight `None` | 48c4e0225830
- trace `delta-variantB_pre-20260215_194731-0018` | source `auto_created` | insight `None` | 670d3b74b591
- trace `delta-variantB_pre-20260215_194731-0003` | source `auto_created` | insight `None` | 2b1f880bcdf5

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
