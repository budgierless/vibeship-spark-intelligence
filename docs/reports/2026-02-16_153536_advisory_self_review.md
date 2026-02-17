# Advisory Self-Review (2026-02-16T15:35:36.953056+00:00)

## Window
- Hours analyzed: 1.0
- State: unclear

## Core Metrics
- Advisory rows: 79
- Advisory trace coverage: 79/79 (100.0%)
- Advice items emitted: 79
- Non-benchmark advisory rows: 79 (excluded 0)
- Engine events: 500
- Engine trace coverage: 500/500 (100.0%)
- Fallback share (delivered): 0.0%
- Strict action rate: 0.25
- Strict effectiveness rate: 0.0
- Trace mismatch count: 3

## Honest Answers
### Did learnings help make better decisions?
- Yes, but unevenly. Trace-bound clusters show good outcomes, mostly from cognitive/self-awareness sources.
- Mind usage exists but is still low-share in retrieval mix.

### Examples with trace IDs
- `liveprobe-focus-warning1800-gate035-t09-20260216-0000` | tool `Read` | source `cognitive` | Always Read a file before Edit to verify current content
- `liveprobe-focus-whisper1200-gate035-t09-20260216-0000` | tool `Read` | source `cognitive` | Always Read a file before Edit to verify current content
- `spark-auto-s7-read-1771255612770` | tool `Read` | source `advisor` | Note-level guidance.
- `spark-auto-s6-edit-1771255612703` | tool `Edit` | source `advisor` | Warning-level guidance.
- `trace-auto-1` | tool `Read` | source `advisor` | Trace-linked live guidance.
- `spark-auto-s2d-read-1771255612403` | tool `Read` | source `cognitive` | Fallback from emitted advice text.
- `spark-auto-s2b-read-1771255612330` | tool `Read` | source `advisor` | Live guidance with policy.
- `spark-auto-s2-read-1771255612256` | tool `Read` | source `advisor` | Live guidance.

### Were there misses despite memory existing?
- Mixed. Fallback was not dominant in this window; evaluate misses via trace coverage and repeated-noise patterns.
- Engine trace coverage is healthy enough for stronger attribution confidence.

### Were unnecessary advisories/memories triggered?
- Yes. Top repeated advisories account for ~70.89% of all advice items in this window.

## Top Repeated Advice (Noise Candidates)
- 26x (32.91%) Always Read a file before Edit to verify current content
- 10x (12.66%) Security holes in agent ecosystems are concerning - aitimesorg tracking vulnerabilities. Gap: agent security auditing tools.
- 5x (6.33%) Use packet guidance.
- 5x (6.33%) Live guidance.
- 5x (6.33%) Live guidance with policy.
- 5x (6.33%) Fallback from emitted advice text.

## Top Repeated Advice (Non-Benchmark Window)
- 26x (32.91%) Always Read a file before Edit to verify current content
- 10x (12.66%) Security holes in agent ecosystems are concerning - aitimesorg tracking vulnerabilities. Gap: agent security auditing tools.
- 5x (6.33%) Use packet guidance.
- 5x (6.33%) Live guidance.
- 5x (6.33%) Live guidance with policy.
- 5x (6.33%) Fallback from emitted advice text.

## Bad Outcome Records
- trace `delta-selective_loop_pass2_note_1800-20260216_144309-0003` | source `cognitive` | insight `context:security_holes_in_agent_ecosystems_are_c` | Security holes in agent ecosystems are concerning - aitimesorg tracking vulnerabilities. Gap: agent 
- trace `delta-selective_loop_pass1_warning_1800-20260216_144145-0003` | source `cognitive` | insight `context:claudecraft_integrating_openclaw_and_mol` | ClaudeCraft integrating OpenClaw and Moltbook into Minecraft server - autonomous agents with persist

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
