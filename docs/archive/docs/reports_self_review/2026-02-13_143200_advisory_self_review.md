# Advisory Self-Review (2026-02-13T14:32:00.450579+00:00)

## Window
- Hours analyzed: 12
- State: improving

## Core Metrics
- Advisory rows: 1228
- Advisory trace coverage: 1186/1228 (96.58%)
- Advice items emitted: 2641
- Engine events: 499
- Engine trace coverage: 304/499 (60.92%)
- Fallback share (delivered): 0.0%
- Strict action rate: 0.888
- Strict effectiveness rate: 0.9459
- Trace mismatch count: 35

## Honest Answers
### Did learnings help make better decisions?
- Yes, but unevenly. Trace-bound clusters show good outcomes, mostly from cognitive/self-awareness sources.
- Mind usage exists but is still low-share in retrieval mix.

### Examples with trace IDs
- `delta-metric_fix_smoke-20260213_143000-0039` | tool `WebFetch` | source `self_awareness` | [Caution] I struggle with WebFetch fails with other tasks
- `delta-metric_fix_smoke-20260213_143000-0038` | tool `Edit` | source `cognitive` | Always Read a file before Edit to verify current content
- `delta-metric_fix_smoke-20260213_143000-0037` | tool `Task` | source `cognitive` | lets push gitthub, and then clean up the whole system except this spark, and at some point we were thinking to bring the council of 50, as the agents can you se
- `delta-metric_fix_smoke-20260213_143000-0036` | tool `Read` | source `cognitive` | lets push gitthub, and then clean up the whole system except this spark, and at some point we were thinking to bring the council of 50, as the agents can you se
- `delta-metric_fix_smoke-20260213_143000-0035` | tool `WebFetch` | source `self_awareness` | [Caution] I struggle with WebFetch fails with other tasks
- `delta-metric_fix_smoke-20260213_143000-0034` | tool `Task` | source `cognitive` | lets push gitthub, and then clean up the whole system except this spark, and at some point we were thinking to bring the council of 50, as the agents can you se
- `delta-metric_fix_smoke-20260213_143000-0033` | tool `Edit` | source `cognitive` | Always Read a file before Edit to verify current content
- `delta-metric_fix_smoke-20260213_143000-0032` | tool `Read` | source `cognitive` | Always Read a file before Edit to verify current content

### Were there misses despite memory existing?
- Mixed. Fallback was not dominant in this window; evaluate misses via trace coverage and repeated-noise patterns.
- Engine trace coverage is healthy enough for stronger attribution confidence.

### Were unnecessary advisories/memories triggered?
- Yes. Top repeated advisories account for ~81.83% of all advice items in this window.

## Top Repeated Advice (Noise Candidates)
- 868x (32.87%) Constraint: in **exactly one state** at all times
- 413x (15.64%) lets push gitthub, and then clean up the whole system except this spark, and at some point we were thinking to bring the council of 50, as the agents can you se
- 295x (11.17%) Always Read a file before Edit to verify current content
- 198x (7.5%) [Caution] I struggle with WebFetch fails with other tasks
- 195x (7.38%) [Caution] I struggle with WebFetch fails with other (recovered) tasks
- 192x (7.27%) [Caution] I struggle with WebFetch_error tasks

## Bad Outcome Records
- trace `delta-metric_fix_smoke-20260213_143000-0003` | source `auto_created` | insight `None` | 3d1cc64fce39
- trace `04f3aacb14322957` | source `cognitive` | insight `user_understanding:lets_push_gitthub,_and_then_clean_up_the` | 8325d90244c7
- trace `04f3aacb14322957` | source `self_awareness` | insight `tool:WebFetch` | b8f877bec7e7
- trace `c91c7f6f47080c28` | source `cognitive` | insight `user_understanding:lets_push_gitthub,_and_then_clean_up_the` | bd2024a8f2aa
- trace `d1488b413637f82f` | source `auto_created` | insight `None` | tool:Bash
- trace `None` | source `cognitive` | insight `context:constraint:_in_**exactly_one_state**_at_` | b6594dbd3100
- trace `None` | source `cognitive` | insight `wisdom:principle:_embedded_into_agents` | 3459727f7b26
- trace `None` | source `cognitive` | insight `user_understanding:lets_push_gitthub,_and_then_clean_up_the` | c263fa23ff57
- trace `delta-noise_winner_B_verify-20260213_141947-0018` | source `auto_created` | insight `None` | 238d67c63d7f
- trace `delta-noise_winner_B_verify-20260213_141947-0003` | source `auto_created` | insight `None` | e58740728b5e

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
