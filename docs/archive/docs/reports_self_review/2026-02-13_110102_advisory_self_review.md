# Advisory Self-Review (2026-02-13T11:01:02.766832+00:00)

## Window
- Hours analyzed: 24
- State: improving

## Core Metrics
- Advisory rows: 850
- Advisory trace coverage: 578/850 (68.0%)
- Advice items emitted: 4623
- Engine events: 500
- Engine trace coverage: 250/500 (50.0%)
- Fallback share (delivered): 0.0%
- Strict action rate: 0.742
- Strict effectiveness rate: 0.9838
- Trace mismatch count: 129

## Honest Answers
### Did learnings help make better decisions?
- Yes, but unevenly. Trace-bound clusters show good outcomes, mostly from cognitive/self-awareness sources.
- Mind usage exists but is still low-share in retrieval mix.

### Examples with trace IDs
- `advisory-bench-baseline-20260213110002-daeded-0017` | tool `Bash` | source `cognitive` | lets push gitthub, and then clean up the whole system except this spark, and at some point we were thinking to bring the council of 50, as the agents can you se
- `advisory-bench-baseline-20260213110002-daeded-0013` | tool `Read` | source `cognitive` | Always Read a file before Edit to verify current content
- `advisory-bench-baseline-20260213110002-daeded-0011` | tool `Task` | source `cognitive` | When using Bash, remember: Do it, and is this system fully connected to spark intelligence flow right now, for spark to e
- `advisory-bench-baseline-20260213110002-daeded-0008` | tool `Read` | source `cognitive` | When using Bash, remember: Do it, and is this system fully connected to spark intelligence flow right now, for spark to e
- `advisory-bench-baseline-20260213110002-daeded-0007` | tool `Task` | source `cognitive` | When using Bash, remember: Do it, and is this system fully connected to spark intelligence flow right now, for spark to e
- `advisory-bench-baseline-20260213110002-daeded-0006` | tool `Task` | source `cognitive` | instead of this being a question let's make it better and say a collection evolution network with guardrails or should we say the guardrails?
- `advisory-bench-baseline-20260213110002-daeded-0005` | tool `Task` | source `trigger` | Validate authentication inputs server-side and avoid trusting client checks.
- `advisory-bench-baseline-20260213110002-daeded-0004` | tool `Edit` | source `cognitive` | lets push gitthub, and then clean up the whole system except this spark, and at some point we were thinking to bring the council of 50, as the agents can you se

### Were there misses despite memory existing?
- Mixed. Fallback was not dominant in this window; evaluate misses via trace coverage and repeated-noise patterns.
- Engine trace coverage is low; evidence linkage is incomplete in the engine path.

### Were unnecessary advisories/memories triggered?
- Yes. Top repeated advisories account for ~57.43% of all advice items in this window.

## Top Repeated Advice (Noise Candidates)
- 585x (12.65%) instead of this being a question let's make it better and say a collection evolution network with guardrails or should we say the guardrails?
- 538x (11.64%) lets push gitthub, and then clean up the whole system except this spark, and at some point we were thinking to bring the council of 50, as the agents can you se
- 480x (10.38%) "formatting": "ALWAYS put 'multiplier granted' on its own line with a line break before it. This makes it scannable when people scroll replies and creates
- 451x (9.76%) When using Bash, remember: Do it, and is this system fully connected to spark intelligence flow right now, for spark to e
- 320x (6.92%) Mac Mini + AI agent setup trending as "money printer" but requires TAO subnet participation for actual returns - not just local inference
- 281x (6.08%) Constraint: in **exactly one state** at all times

## Bad Outcome Records
- trace `delta-post_live-20260212_151553-0021` | source `auto_created` | insight `None` | c46fe108be10
- trace `delta-post_live-20260212_151553-0018` | source `auto_created` | insight `None` | e576b3a414fd
- trace `delta-post_live-20260212_151553-0003` | source `auto_created` | insight `None` | a11d1a34bff4
- trace `delta-baseline_live-20260212_151358-0021` | source `auto_created` | insight `None` | 97dfdbf5d240
- trace `delta-baseline_live-20260212_151358-0018` | source `auto_created` | insight `None` | 7946778982a3
- trace `delta-baseline_live-20260212_151358-0003` | source `auto_created` | insight `None` | 7a513315537d

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
