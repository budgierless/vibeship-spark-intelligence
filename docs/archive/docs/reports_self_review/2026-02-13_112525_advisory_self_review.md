# Advisory Self-Review (2026-02-13T11:25:25.247724+00:00)

## Window
- Hours analyzed: 24
- State: improving

## Core Metrics
- Advisory rows: 915
- Advisory trace coverage: 643/915 (70.27%)
- Advice items emitted: 4767
- Engine events: 500
- Engine trace coverage: 250/500 (50.0%)
- Fallback share (delivered): 0.0%
- Strict action rate: 0.718
- Strict effectiveness rate: 0.9972
- Trace mismatch count: 141

## Honest Answers
### Did learnings help make better decisions?
- Yes, but unevenly. Trace-bound clusters show good outcomes, mostly from cognitive/self-awareness sources.
- Mind usage exists but is still low-share in retrieval mix.

### Examples with trace IDs
- `advisory-bench-balanced-20260213112414-b0ade5-0016` | tool `Task` | source `cognitive` | Constraint: in **exactly one state** at all times
- `advisory-bench-balanced-20260213112414-b0ade5-0015` | tool `Task` | source `cognitive` | Constraint: in **exactly one state** at all times
- `advisory-bench-balanced-20260213112414-b0ade5-0012` | tool `Task` | source `cognitive` | Constraint: in **exactly one state** at all times
- `advisory-bench-balanced-20260213112414-b0ade5-0010` | tool `Bash` | source `cognitive` | Constraint: in **exactly one state** at all times
- `advisory-bench-balanced-20260213112414-b0ade5-0009` | tool `Task` | source `cognitive` | Constraint: in **exactly one state** at all times
- `advisory-bench-balanced-20260213112414-b0ade5-0007` | tool `Task` | source `cognitive` | Constraint: in **exactly one state** at all times
- `advisory-bench-balanced-20260213112414-b0ade5-0006` | tool `Task` | source `cognitive` | Constraint: in **exactly one state** at all times
- `advisory-bench-balanced-20260213112414-b0ade5-0005` | tool `Task` | source `cognitive` | Constraint: in **exactly one state** at all times

### Were there misses despite memory existing?
- Mixed. Fallback was not dominant in this window; evaluate misses via trace coverage and repeated-noise patterns.
- Engine trace coverage is low; evidence linkage is incomplete in the engine path.

### Were unnecessary advisories/memories triggered?
- Yes. Top repeated advisories account for ~56.52% of all advice items in this window.

## Top Repeated Advice (Noise Candidates)
- 585x (12.27%) instead of this being a question let's make it better and say a collection evolution network with guardrails or should we say the guardrails?
- 547x (11.47%) lets push gitthub, and then clean up the whole system except this spark, and at some point we were thinking to bring the council of 50, as the agents can you se
- 483x (10.13%) "formatting": "ALWAYS put 'multiplier granted' on its own line with a line break before it. This makes it scannable when people scroll replies and creates
- 460x (9.65%) When using Bash, remember: Do it, and is this system fully connected to spark intelligence flow right now, for spark to e
- 320x (6.71%) Mac Mini + AI agent setup trending as "money printer" but requires TAO subnet participation for actual returns - not just local inference
- 300x (6.29%) Constraint: in **exactly one state** at all times

## Bad Outcome Records
- trace `delta-strict_canary_v1-20260213_112150-0003` | source `auto_created` | insight `None` | 35e33431fcd9

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
