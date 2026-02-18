# Advisory Self-Review (2026-02-16T15:18:10.336772+00:00)

## Window
- Hours analyzed: 1.0
- State: unclear

## Core Metrics
- Advisory rows: 84
- Advisory trace coverage: 84/84 (100.0%)
- Advice items emitted: 84
- Non-benchmark advisory rows: 84 (excluded 0)
- Engine events: 500
- Engine trace coverage: 500/500 (100.0%)
- Fallback share (delivered): 0.0%
- Strict action rate: 0.4
- Strict effectiveness rate: 0.0
- Trace mismatch count: 3

## Honest Answers
### Did learnings help make better decisions?
- Yes, but unevenly. Trace-bound clusters show good outcomes, mostly from cognitive/self-awareness sources.
- Mind usage exists but is still low-share in retrieval mix.

### Examples with trace IDs
- `liveprobe-dedupeoff-note035-20260216_151516-0017` | tool `Edit` | source `cognitive` | Always Read a file before Edit to verify current content
- `liveprobe-dedupeoff-note035-20260216_151516-0009` | tool `Edit` | source `cognitive` | Always Read a file before Edit to verify current content
- `liveprobe-dedupeoff-note035-20260216_151516-0008` | tool `Read` | source `cognitive` | Always Read a file before Edit to verify current content
- `liveprobe-dedupeoff-note035-20260216_151516-0004` | tool `Read` | source `cognitive` | Always Read a file before Edit to verify current content
- `liveprobe-dedupeoff-note035-20260216_151516-0001` | tool `Edit` | source `cognitive` | Always Read a file before Edit to verify current content
- `liveprobe-dedupeoff-note035-20260216_151516-0000` | tool `Read` | source `cognitive` | Always Read a file before Edit to verify current content
- `liveprobe-probe_pass1_note_1400_gate050-20260216_150702-0009` | tool `Edit` | source `cognitive` | Always Read a file before Edit to verify current content
- `spark-auto-s7-read-1771254272328` | tool `Read` | source `advisor` | Note-level guidance.

### Were there misses despite memory existing?
- Mixed. Fallback was not dominant in this window; evaluate misses via trace coverage and repeated-noise patterns.
- Engine trace coverage is healthy enough for stronger attribution confidence.

### Were unnecessary advisories/memories triggered?
- Yes. Top repeated advisories account for ~66.65% of all advice items in this window.

## Top Repeated Advice (Noise Candidates)
- 20x (23.81%) Always Read a file before Edit to verify current content
- 10x (11.9%) Security holes in agent ecosystems are concerning - aitimesorg tracking vulnerabilities. Gap: agent security auditing tools.
- 8x (9.52%) ClaudeCraft integrating OpenClaw and Moltbook into Minecraft server - autonomous agents with persistent worlds and real execution
- 6x (7.14%) Use packet guidance.
- 6x (7.14%) Live guidance.
- 6x (7.14%) Live guidance with policy.

## Top Repeated Advice (Non-Benchmark Window)
- 20x (23.81%) Always Read a file before Edit to verify current content
- 10x (11.9%) Security holes in agent ecosystems are concerning - aitimesorg tracking vulnerabilities. Gap: agent security auditing tools.
- 8x (9.52%) ClaudeCraft integrating OpenClaw and Moltbook into Minecraft server - autonomous agents with persistent worlds and real execution
- 6x (7.14%) Use packet guidance.
- 6x (7.14%) Live guidance.
- 6x (7.14%) Live guidance with policy.

## Bad Outcome Records
- trace `delta-selective_loop_pass2_note_1800-20260216_144309-0003` | source `cognitive` | insight `context:security_holes_in_agent_ecosystems_are_c` | Security holes in agent ecosystems are concerning - aitimesorg tracking vulnerabilities. Gap: agent 
- trace `delta-selective_loop_pass1_warning_1800-20260216_144145-0003` | source `cognitive` | insight `context:claudecraft_integrating_openclaw_and_mol` | ClaudeCraft integrating OpenClaw and Moltbook into Minecraft server - autonomous agents with persist
- trace `delta-synth_fallback_fix_probe-20260216_143128-0003` | source `cognitive` | insight `reasoning:bookmark-worthy_content_needs_reference_` | Bookmark-worthy content needs reference value - lists, frameworks, how-tos that people save

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
