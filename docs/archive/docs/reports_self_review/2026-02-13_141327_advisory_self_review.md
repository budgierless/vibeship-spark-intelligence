# Advisory Self-Review (2026-02-13T14:13:27.206822+00:00)

## Window
- Hours analyzed: 12
- State: improving

## Core Metrics
- Advisory rows: 964
- Advisory trace coverage: 937/964 (97.2%)
- Advice items emitted: 2024
- Engine events: 500
- Engine trace coverage: 258/500 (51.6%)
- Fallback share (delivered): 0.0%
- Strict action rate: 0.898
- Strict effectiveness rate: 0.9465
- Trace mismatch count: 47

## Honest Answers
### Did learnings help make better decisions?
- Yes, but unevenly. Trace-bound clusters show good outcomes, mostly from cognitive/self-awareness sources.
- Mind usage exists but is still low-share in retrieval mix.

### Examples with trace IDs
- `delta-noise_C_rank_tight-20260213_141244-0012` | tool `Read` | source `cognitive` | Always Read a file before Edit to verify current content
- `delta-noise_C_rank_tight-20260213_141244-0011` | tool `WebFetch` | source `self_awareness` | [Caution] I struggle with WebFetch fails with other tasks
- `delta-noise_C_rank_tight-20260213_141244-0009` | tool `Edit` | source `cognitive` | Always Read a file before Edit to verify current content
- `delta-noise_C_rank_tight-20260213_141244-0008` | tool `Read` | source `cognitive` | Always Read a file before Edit to verify current content
- `delta-noise_C_rank_tight-20260213_141244-0007` | tool `WebFetch` | source `self_awareness` | [Caution] I struggle with WebFetch fails with other tasks
- `delta-noise_C_rank_tight-20260213_141244-0004` | tool `Read` | source `cognitive` | Always Read a file before Edit to verify current content
- `delta-noise_C_rank_tight-20260213_141244-0003` | tool `WebFetch` | source `self_awareness` | [Caution] I struggle with WebFetch fails with other tasks
- `delta-noise_C_rank_tight-20260213_141244-0001` | tool `Edit` | source `cognitive` | Always Read a file before Edit to verify current content

### Were there misses despite memory existing?
- Mixed. Fallback was not dominant in this window; evaluate misses via trace coverage and repeated-noise patterns.
- Engine trace coverage is low; evidence linkage is incomplete in the engine path.

### Were unnecessary advisories/memories triggered?
- Yes. Top repeated advisories account for ~78.85% of all advice items in this window.

## Top Repeated Advice (Noise Candidates)
- 789x (38.98%) Constraint: in **exactly one state** at all times
- 248x (12.25%) lets push gitthub, and then clean up the whole system except this spark, and at some point we were thinking to bring the council of 50, as the agents can you se
- 172x (8.5%) Always Read a file before Edit to verify current content
- 132x (6.52%) [Caution] I struggle with WebFetch fails with other tasks
- 129x (6.37%) [Caution] I struggle with WebFetch fails with other (recovered) tasks
- 126x (6.23%) [Caution] I struggle with WebFetch_error tasks

## Bad Outcome Records
- trace `delta-noise_C_rank_tight-20260213_141244-0003` | source `auto_created` | insight `None` | 2f4ad1135e8b
- trace `delta-noise_B_cooldowns_up-20260213_141042-0021` | source `auto_created` | insight `None` | f408477d6895
- trace `delta-noise_B_cooldowns_up-20260213_141042-0018` | source `auto_created` | insight `None` | 6549575f1067
- trace `delta-noise_B_cooldowns_up-20260213_141042-0003` | source `auto_created` | insight `None` | 66a4a1839213
- trace `delta-noise_A_control-20260213_140714-0051` | source `auto_created` | insight `None` | 863b72704c5b
- trace `delta-noise_A_control-20260213_140714-0021` | source `auto_created` | insight `None` | 4df5b022014f
- trace `delta-noise_A_control-20260213_140714-0018` | source `auto_created` | insight `None` | d2705fccc1ce
- trace `delta-noise_A_control-20260213_140714-0003` | source `auto_created` | insight `None` | da0be4046910
- trace `d1488b413637f82f` | source `cognitive` | insight `user_understanding:when_using_bash,_remember:_do_it,_and_is` | 976037f9b320
- trace `d1488b413637f82f` | source `cognitive` | insight `user_understanding:lets_push_gitthub,_and_then_clean_up_the` | 76e0e7e6e7cf

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
