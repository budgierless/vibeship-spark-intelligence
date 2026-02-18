# Advisory Self-Review (2026-02-13T12:26:39.389121+00:00)

## Window
- Hours analyzed: 24
- State: improving

## Core Metrics
- Advisory rows: 1158
- Advisory trace coverage: 928/1158 (80.14%)
- Advice items emitted: 4884
- Engine events: 500
- Engine trace coverage: 251/500 (50.2%)
- Fallback share (delivered): 0.0%
- Strict action rate: 0.71
- Strict effectiveness rate: 0.9718
- Trace mismatch count: 145

## Honest Answers
### Did learnings help make better decisions?
- Yes, but unevenly. Trace-bound clusters show good outcomes, mostly from cognitive/self-awareness sources.
- Mind usage exists but is still low-share in retrieval mix.

### Examples with trace IDs
- `advisory-bench-C_chip_targeted-20260213121520-66ccc3-0002` | tool `Task` | source `cognitive` | Constraint: in **exactly one state** at all times
- `advisory-bench-C_chip_targeted-20260213121520-e72da8-0002` | tool `Task` | source `cognitive` | Constraint: in **exactly one state** at all times
- `advisory-bench-A_control-20260213121010-b93a2d-0002` | tool `Task` | source `cognitive` | Constraint: in **exactly one state** at all times
- `advisory-bench-A_control-20260213121010-b93a2d-0001` | tool `Edit` | source `cognitive` | lets push gitthub, and then clean up the whole system except this spark, and at some point we were thinking to bring the council of 50, as the agents can you se
- `advisory-bench-A_control-20260213120955-8b2d3e-0002` | tool `Task` | source `cognitive` | Constraint: in **exactly one state** at all times
- `advisory-bench-A_control-20260213120955-8b2d3e-0001` | tool `Task` | source `cognitive` | Constraint: in **exactly one state** at all times
- `advisory-bench-A_control-20260213120942-bc6b18-0001` | tool `Task` | source `cognitive` | Constraint: in **exactly one state** at all times
- `advisory-bench-A_control-20260213120926-5967bb-0002` | tool `Task` | source `cognitive` | Constraint: in **exactly one state** at all times

### Were there misses despite memory existing?
- Mixed. Fallback was not dominant in this window; evaluate misses via trace coverage and repeated-noise patterns.
- Engine trace coverage is low; evidence linkage is incomplete in the engine path.

### Were unnecessary advisories/memories triggered?
- Yes. Top repeated advisories account for ~59.99% of all advice items in this window.

## Top Repeated Advice (Noise Candidates)
- 575x (11.77%) instead of this being a question let's make it better and say a collection evolution network with guardrails or should we say the guardrails?
- 569x (11.65%) lets push gitthub, and then clean up the whole system except this spark, and at some point we were thinking to bring the council of 50, as the agents can you se
- 545x (11.16%) Constraint: in **exactly one state** at all times
- 470x (9.62%) "formatting": "ALWAYS put 'multiplier granted' on its own line with a line break before it. This makes it scannable when people scroll replies and creates
- 462x (9.46%) When using Bash, remember: Do it, and is this system fully connected to spark intelligence flow right now, for spark to e
- 309x (6.33%) Mac Mini + AI agent setup trending as "money printer" but requires TAO subnet participation for actual returns - not just local inference

## Bad Outcome Records
- trace `d61f269db84aa0a3b24e` | source `opportunity_scanner` | insight `opportunity:assumption_audit` | opp:8913f4fddbc566d6
- trace `d61f269db84aa0a3b24e` | source `opportunity_scanner` | insight `opportunity:assumption_audit` | opp:087d1a5858873e58
- trace `d61f269db84aa0a3b24e` | source `opportunity_scanner` | insight `opportunity:assumption_audit` | opp:b51d5a97859ba448
- trace `d61f269db84aa0a3b24e` | source `opportunity_scanner` | insight `opportunity:assumption_audit` | opp:50d5823b6e109006
- trace `delta-2026-02-13_indirect_intelligence_flow_matrix_v1_m1_distillation_D_balanced_tight-20260213_115128-0015` | source `auto_created` | insight `None` | 36a4232cbe86
- trace `delta-2026-02-13_indirect_intelligence_flow_matrix_v1_m1_distillation_A_control-20260213_114458-0003` | source `auto_created` | insight `None` | c6613f5be658
- trace `delta-restored_balanced_v1-20260213_112631-0021` | source `auto_created` | insight `None` | 965033d99c6f
- trace `delta-restored_balanced_v1-20260213_112631-0018` | source `auto_created` | insight `None` | 74ea831e39c5
- trace `delta-restored_balanced_v1-20260213_112631-0003` | source `auto_created` | insight `None` | c3b2786abf35
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
