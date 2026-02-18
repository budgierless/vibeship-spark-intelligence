# Advisory Self-Review (2026-02-13T14:28:42.694042+00:00)

## Window
- Hours analyzed: 12
- State: improving

## Core Metrics
- Advisory rows: 1185
- Advisory trace coverage: 1146/1185 (96.71%)
- Advice items emitted: 2542
- Engine events: 499
- Engine trace coverage: 302/499 (60.52%)
- Fallback share (delivered): 0.0%
- Strict action rate: 0.89
- Strict effectiveness rate: 0.9483
- Trace mismatch count: 35

## Honest Answers
### Did learnings help make better decisions?
- Yes, but unevenly. Trace-bound clusters show good outcomes, mostly from cognitive/self-awareness sources.
- Mind usage exists but is still low-share in retrieval mix.

### Examples with trace IDs
- `3ecb82150523f58a` | tool `Read` | source `cognitive` | lets push gitthub, and then clean up the whole system except this spark, and at some point we were thinking to bring the council of 50, as the agents can you se
- `40bc7542b68a50ea` | tool `Read` | source `cognitive` | lets push gitthub, and then clean up the whole system except this spark, and at some point we were thinking to bring the council of 50, as the agents can you se
- `e5cf841cdd65d7a3` | tool `Bash` | source `cognitive` | lets push gitthub, and then clean up the whole system except this spark, and at some point we were thinking to bring the council of 50, as the agents can you se
- `76a7ee72620050bb` | tool `WebFetch` | source `self_awareness` | [Caution] I struggle with WebFetch fails with other tasks
- `bf918392e032dcee` | tool `Read` | source `cognitive` | lets push gitthub, and then clean up the whole system except this spark, and at some point we were thinking to bring the council of 50, as the agents can you se
- `2d8599ecf3922073` | tool `Read` | source `cognitive` | lets push gitthub, and then clean up the whole system except this spark, and at some point we were thinking to bring the council of 50, as the agents can you se
- `361dcdc37f0c216e` | tool `Read` | source `cognitive` | lets push gitthub, and then clean up the whole system except this spark, and at some point we were thinking to bring the council of 50, as the agents can you se
- `12b1feccd816c9f6` | tool `Bash` | source `trigger` | Before deploy: run tests, verify migrations, and confirm env vars.

### Were there misses despite memory existing?
- Mixed. Fallback was not dominant in this window; evaluate misses via trace coverage and repeated-noise patterns.
- Engine trace coverage is healthy enough for stronger attribution confidence.

### Were unnecessary advisories/memories triggered?
- Yes. Top repeated advisories account for ~81.52% of all advice items in this window.

## Top Repeated Advice (Noise Candidates)
- 867x (34.11%) Constraint: in **exactly one state** at all times
- 372x (14.63%) lets push gitthub, and then clean up the whole system except this spark, and at some point we were thinking to bring the council of 50, as the agents can you se
- 278x (10.94%) Always Read a file before Edit to verify current content
- 188x (7.4%) [Caution] I struggle with WebFetch fails with other tasks
- 185x (7.28%) [Caution] I struggle with WebFetch fails with other (recovered) tasks
- 182x (7.16%) [Caution] I struggle with WebFetch_error tasks

## Bad Outcome Records
- trace `04f3aacb14322957` | source `cognitive` | insight `user_understanding:lets_push_gitthub,_and_then_clean_up_the` | 8325d90244c7
- trace `04f3aacb14322957` | source `self_awareness` | insight `tool:WebFetch` | b8f877bec7e7
- trace `c91c7f6f47080c28` | source `cognitive` | insight `user_understanding:lets_push_gitthub,_and_then_clean_up_the` | bd2024a8f2aa
- trace `d1488b413637f82f` | source `auto_created` | insight `None` | tool:Bash
- trace `None` | source `cognitive` | insight `context:constraint:_in_**exactly_one_state**_at_` | b6594dbd3100
- trace `None` | source `cognitive` | insight `wisdom:principle:_embedded_into_agents` | 3459727f7b26
- trace `None` | source `cognitive` | insight `user_understanding:lets_push_gitthub,_and_then_clean_up_the` | c263fa23ff57
- trace `delta-noise_winner_B_verify-20260213_141947-0018` | source `auto_created` | insight `None` | 238d67c63d7f
- trace `delta-noise_winner_B_verify-20260213_141947-0003` | source `auto_created` | insight `None` | e58740728b5e
- trace `delta-noise_D_mixed_light-20260213_141650-0003` | source `auto_created` | insight `None` | 82f5678d836e

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
