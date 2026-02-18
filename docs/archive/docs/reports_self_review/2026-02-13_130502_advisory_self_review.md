# Advisory Self-Review (2026-02-13T13:05:02.419530+00:00)

## Window
- Hours analyzed: 24
- State: improving

## Core Metrics
- Advisory rows: 1369
- Advisory trace coverage: 1163/1369 (84.95%)
- Advice items emitted: 5073
- Engine events: 500
- Engine trace coverage: 250/500 (50.0%)
- Fallback share (delivered): 0.0%
- Strict action rate: 0.762
- Strict effectiveness rate: 0.9528
- Trace mismatch count: 119

## Honest Answers
### Did learnings help make better decisions?
- Yes, but unevenly. Trace-bound clusters show good outcomes, mostly from cognitive/self-awareness sources.
- Mind usage exists but is still low-share in retrieval mix.

### Examples with trace IDs
- `delta-canary_retrieval_v2_nonlive_sanity-20260213_125145-0007` | tool `WebFetch` | source `self_awareness` | [Caution] I struggle with WebFetch fails with other tasks
- `delta-canary_retrieval_v2_soak1_fast-20260213_125049-0011` | tool `WebFetch` | source `self_awareness` | [Caution] I struggle with WebFetch fails with other tasks
- `advisory-bench-baseline-20260213125050-2c884e-0009` | tool `Task` | source `cognitive` | Constraint: in **exactly one state** at all times
- `delta-canary_retrieval_v2_soak1_fast-20260213_125049-0010` | tool `Task` | source `cognitive` | Constraint: in **exactly one state** at all times
- `advisory-bench-baseline-20260213125050-2c884e-0008` | tool `Read` | source `cognitive` | Constraint: in **exactly one state** at all times
- `delta-canary_retrieval_v2_soak1_fast-20260213_125049-0009` | tool `Edit` | source `cognitive` | Constraint: in **exactly one state** at all times
- `advisory-bench-baseline-20260213125050-2c884e-0007` | tool `Task` | source `cognitive` | Constraint: in **exactly one state** at all times
- `delta-canary_retrieval_v2_soak1_fast-20260213_125049-0008` | tool `Read` | source `cognitive` | Constraint: in **exactly one state** at all times

### Were there misses despite memory existing?
- Mixed. Fallback was not dominant in this window; evaluate misses via trace coverage and repeated-noise patterns.
- Engine trace coverage is low; evidence linkage is incomplete in the engine path.

### Were unnecessary advisories/memories triggered?
- Yes. Top repeated advisories account for ~61.37% of all advice items in this window.

## Top Repeated Advice (Noise Candidates)
- 746x (14.71%) Constraint: in **exactly one state** at all times
- 575x (11.33%) instead of this being a question let's make it better and say a collection evolution network with guardrails or should we say the guardrails?
- 566x (11.16%) lets push gitthub, and then clean up the whole system except this spark, and at some point we were thinking to bring the council of 50, as the agents can you se
- 467x (9.21%) When using Bash, remember: Do it, and is this system fully connected to spark intelligence flow right now, for spark to e
- 453x (8.93%) "formatting": "ALWAYS put 'multiplier granted' on its own line with a line break before it. This makes it scannable when people scroll replies and creates
- 306x (6.03%) Mac Mini + AI agent setup trending as "money printer" but requires TAO subnet participation for actual returns - not just local inference

## Bad Outcome Records
- trace `delta-canary_retrieval_v2_soak1_fast-20260213_125049-0003` | source `auto_created` | insight `None` | 894d8164cb58
- trace `delta-canary_retrieval_v2_soak1_quick-20260213_124944-0003` | source `auto_created` | insight `None` | 48df277afc9e
- trace `delta-canary_retrieval_v2_soak1-20260213_124252-0093` | source `auto_created` | insight `None` | 7bfffd71d856
- trace `delta-canary_retrieval_v2_soak1-20260213_124252-0075` | source `auto_created` | insight `None` | 2d0d4161a4d4
- trace `delta-canary_retrieval_v2_soak1-20260213_124252-0066` | source `auto_created` | insight `None` | 9dbf19ff885e
- trace `delta-canary_retrieval_v2_soak1-20260213_124252-0045` | source `auto_created` | insight `None` | 486efdb391fc
- trace `delta-canary_retrieval_v2_soak1-20260213_124252-0039` | source `auto_created` | insight `None` | f9d9f84b4902
- trace `delta-canary_retrieval_v2_soak1-20260213_124252-0003` | source `auto_created` | insight `None` | 2527bac46fb4
- trace `d61f269db84aa0a3b24e` | source `opportunity_scanner` | insight `opportunity:assumption_audit` | opp:8913f4fddbc566d6
- trace `d61f269db84aa0a3b24e` | source `opportunity_scanner` | insight `opportunity:assumption_audit` | opp:087d1a5858873e58

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
