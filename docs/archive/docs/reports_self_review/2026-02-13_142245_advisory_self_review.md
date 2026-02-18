# Advisory Self-Review (2026-02-13T14:22:45.639405+00:00)

## Window
- Hours analyzed: 2
- State: improving

## Core Metrics
- Advisory rows: 760
- Advisory trace coverage: 736/760 (96.84%)
- Advice items emitted: 1686
- Engine events: 500
- Engine trace coverage: 266/500 (53.2%)
- Fallback share (delivered): 0.0%
- Strict action rate: 0.9183
- Strict effectiveness rate: 0.9485
- Trace mismatch count: 24

## Honest Answers
### Did learnings help make better decisions?
- Yes, but unevenly. Trace-bound clusters show good outcomes, mostly from cognitive/self-awareness sources.
- Mind usage exists but is still low-share in retrieval mix.

### Examples with trace IDs
- `d5894510d10706bf` | tool `mcp__h70-skills__h70_load_skill` | source `cognitive` | lets push gitthub, and then clean up the whole system except this spark, and at some point we were thinking to bring the council of 50, as the agents can you se
- `c916976daacb75ce` | tool `Bash` | source `cognitive` | lets push gitthub, and then clean up the whole system except this spark, and at some point we were thinking to bring the council of 50, as the agents can you se
- `7cf9fdc5edf100e3` | tool `Read` | source `cognitive` | Always Read a file before Edit to verify current content
- `bad3b2f0a4426c06` | tool `mcp__exa__web_search_exa` | source `cognitive` | Constraint: in **exactly one state** at all times
- `delta-noise_winner_B_verify-20260213_141947-0079` | tool `WebFetch` | source `self_awareness` | [Caution] I struggle with WebFetch fails with other tasks
- `delta-noise_winner_B_verify-20260213_141947-0078` | tool `Edit` | source `cognitive` | Always Read a file before Edit to verify current content
- `delta-noise_winner_B_verify-20260213_141947-0077` | tool `Task` | source `cognitive` | lets push gitthub, and then clean up the whole system except this spark, and at some point we were thinking to bring the council of 50, as the agents can you se
- `delta-noise_winner_B_verify-20260213_141947-0076` | tool `Read` | source `cognitive` | lets push gitthub, and then clean up the whole system except this spark, and at some point we were thinking to bring the council of 50, as the agents can you se

### Were there misses despite memory existing?
- Mixed. Fallback was not dominant in this window; evaluate misses via trace coverage and repeated-noise patterns.
- Engine trace coverage is low; evidence linkage is incomplete in the engine path.

### Were unnecessary advisories/memories triggered?
- Yes. Top repeated advisories account for ~85.13% of all advice items in this window.

## Top Repeated Advice (Noise Candidates)
- 574x (34.05%) Constraint: in **exactly one state** at all times
- 278x (16.49%) lets push gitthub, and then clean up the whole system except this spark, and at some point we were thinking to bring the council of 50, as the agents can you se
- 220x (13.05%) Always Read a file before Edit to verify current content
- 123x (7.3%) [Caution] I struggle with WebFetch fails with other tasks
- 120x (7.12%) [Caution] I struggle with WebFetch fails with other (recovered) tasks
- 120x (7.12%) [Caution] I struggle with WebFetch_error tasks

## Bad Outcome Records
- trace `delta-noise_winner_B_verify-20260213_141947-0018` | source `auto_created` | insight `None` | 238d67c63d7f
- trace `delta-noise_winner_B_verify-20260213_141947-0003` | source `auto_created` | insight `None` | e58740728b5e
- trace `delta-noise_D_mixed_light-20260213_141650-0003` | source `auto_created` | insight `None` | 82f5678d836e
- trace `delta-noise_C_rank_tight-20260213_141542-0003` | source `auto_created` | insight `None` | 78aa7795fdcd
- trace `delta-noise_C_rank_tight-20260213_141244-0003` | source `auto_created` | insight `None` | 2f4ad1135e8b
- trace `delta-noise_B_cooldowns_up-20260213_141042-0021` | source `auto_created` | insight `None` | f408477d6895
- trace `delta-noise_B_cooldowns_up-20260213_141042-0018` | source `auto_created` | insight `None` | 6549575f1067
- trace `delta-noise_B_cooldowns_up-20260213_141042-0003` | source `auto_created` | insight `None` | 66a4a1839213
- trace `delta-noise_A_control-20260213_140714-0051` | source `auto_created` | insight `None` | 863b72704c5b
- trace `delta-noise_A_control-20260213_140714-0021` | source `auto_created` | insight `None` | 4df5b022014f

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
