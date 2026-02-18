# Advisory Self-Review (2026-02-15T20:00:30.357383+00:00)

## Window
- Hours analyzed: 24
- State: unclear

## Core Metrics
- Advisory rows: 1890
- Advisory trace coverage: 1865/1890 (98.68%)
- Advice items emitted: 5678
- Engine events: 500
- Engine trace coverage: 250/500 (50.0%)
- Fallback share (delivered): 0.0%
- Strict action rate: 0.9787
- Strict effectiveness rate: 0.7935
- Trace mismatch count: 6

## Honest Answers
### Did learnings help make better decisions?
- Yes, but unevenly. Trace-bound clusters show good outcomes, mostly from cognitive/self-awareness sources.
- Mind usage exists but is still low-share in retrieval mix.

### Examples with trace IDs
- `advisory-bench-baseline-20260215195943-a3ef0f-0018` | tool `Task` | source `trigger` | Validate authentication inputs server-side and avoid trusting client checks.
- `advisory-bench-baseline-20260215195943-a3ef0f-0017` | tool `Bash` | source `cognitive` | lets push gitthub, and then clean up the whole system except this spark, and at some point we were thinking to bring the council of 50, as the agents can you se
- `advisory-bench-baseline-20260215195943-a3ef0f-0016` | tool `Task` | source `cognitive` | When using Bash, remember: Do it, and is this system fully connected to spark intelligence flow right now, for spark to e
- `advisory-bench-baseline-20260215195943-a3ef0f-0015` | tool `Task` | source `cognitive` | lets push gitthub, and then clean up the whole system except this spark, and at some point we were thinking to bring the council of 50, as the agents can you se
- `advisory-bench-baseline-20260215195943-a3ef0f-0013` | tool `Read` | source `cognitive` | Always Read a file before Edit to verify current content
- `advisory-bench-baseline-20260215195943-a3ef0f-0012` | tool `Task` | source `cognitive` | lets push gitthub, and then clean up the whole system except this spark, and at some point we were thinking to bring the council of 50, as the agents can you se
- `advisory-bench-baseline-20260215195943-a3ef0f-0011` | tool `Task` | source `cognitive` | When using Bash, remember: Do it, and is this system fully connected to spark intelligence flow right now, for spark to e
- `advisory-bench-baseline-20260215195943-a3ef0f-0010` | tool `Bash` | source `cognitive` | lets push gitthub, and then clean up the whole system except this spark, and at some point we were thinking to bring the council of 50, as the agents can you se

### Were there misses despite memory existing?
- Mixed. Fallback was not dominant in this window; evaluate misses via trace coverage and repeated-noise patterns.
- Engine trace coverage is low; evidence linkage is incomplete in the engine path.

### Were unnecessary advisories/memories triggered?
- Yes. Top repeated advisories account for ~91.48% of all advice items in this window.

## Top Repeated Advice (Noise Candidates)
- 1443x (25.41%) When using Bash, remember: Do it, and is this system fully connected to spark intelligence flow right now, for spark to e
- 1426x (25.11%) lets push gitthub, and then clean up the whole system except this spark, and at some point we were thinking to bring the council of 50, as the agents can you se
- 929x (16.36%) Always Read a file before Edit to verify current content
- 514x (9.05%) Constraint: in **exactly one state** at all times
- 443x (7.8%) [Caution] I struggle with WebFetch fails with other tasks
- 440x (7.75%) [Caution] I struggle with WebFetch fails with other (recovered) tasks

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
- trace `delta-chg-20260215-181949-step4-advisory-outcome-tags-actedblo-20260215_182334-0021` | source `auto_created` | insight `None` | c05631d2f3a7

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
