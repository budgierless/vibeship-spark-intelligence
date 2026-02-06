# Advisory Latency and Predictive Prefetch Analysis

Date: 2026-02-06

## Scope

This report answers:
- How long advisory takes in most cases right now.
- How to design a predictable system that preloads the right advice/memory in the background ("chips") before it is needed.

## Live Data Sources Used

- `~/.spark/advisory_engine.jsonl` (500-event rolling engine log, includes `elapsed_ms`)
- `tmp/advisory_latency_probe_auto_phi4_r3.json`
- `tmp/advisory_latency_probe_programmatic_r3.json`
- `tmp/advisory_latency_probe_auto_phi4_r1.json`
- `tmp/advisory_latency_probe_auto_llama3.2-3b_r1.json`
- `tmp/local_model_compare_intel_speed_useful_r5_live12.json`

## Real-Time Advisory Timing

### A) Historical rolling log (last 500 engine events)

- avg: `5476.32ms`
- median: `5664.0ms`
- p95: `11248.42ms`
- <=3s: `20.4%`

Interpretation:
- In current mixed production behavior, synchronous advisory is often too slow for a strict 3s hot-path budget.

### B) Recent behavior windows (same engine log)

- last 50:
  - avg: `1385.24ms`
  - median: `107.9ms`
  - p95: `6312.73ms`
  - <=3s: `78.0%`
- last 100:
  - avg: `2795.8ms`
  - median: `556.9ms`
  - p95: `9261.96ms`
  - <=3s: `59.0%`

Interpretation:
- Performance is bimodal: many very fast calls, but still significant tail spikes.

### C) Controlled probe (same scenarios, 36 runs each)

`auto` mode (`phi4-mini`):
- avg: `1708.78ms`
- median: `47.77ms`
- p95: `6291.31ms`
- <=3s: `66.7%`

`programmatic` mode:
- avg: `569.75ms`
- median: `106.34ms`
- p95: `2858.72ms`
- <=3s: `94.4%`

Delta (`auto` vs `programmatic`):
- avg: `+1139.03ms`
- p95: `+3432.59ms`

Interpretation:
- For hot-path predictability, programmatic synthesis is currently much safer.

### D) First-hit model comparison in advisory path (no repeat cache, 12 runs each)

`auto + phi4-mini`:
- avg: `4765.09ms`
- median: `4515.01ms`
- p95: `5972.4ms`

`auto + llama3.2:3b`:
- avg: `4463.14ms`
- median: `4218.64ms`
- p95: `5946.08ms`

Difference (`phi - llama`):
- avg: `+301.95ms`
- median: `+296.37ms`
- p95: `+26.32ms`

Interpretation:
- In real advisory first-hit, speed difference is small.
- Both models are too slow for strict 3s synchronous guarantees if AI synthesis is always in the critical path.

## Honest “Most Cases” Answer

Current expected advisory latency depends on mode:

1. Hot path with AI first-hit (`auto`): usually `~4.2s to ~4.8s`, tail near `~6s+`.
2. Hot path with programmatic synthesis: usually `~0.1s to ~1.3s`, with p95 around `~2.9s` in probe.
3. Mixed live production (historical 500): median around `~5.7s`, indicating unacceptable tail risk unless routing/fallback is tightened.

## Predictable Design: Chip-Driven Proactive Advisory

Goal:
- Show high-value advice before it is needed without blocking PreTool hot path.

### 1) Split advisory into two lanes

- Lane A (synchronous, deterministic, hard budget <=1200ms):
  - retrieval + gate + programmatic synthesis
  - always available
- Lane B (asynchronous, quality lane):
  - local AI synthesis/refinement
  - runs in background and updates cached advisory packets

### 2) Build project-aware advisory packets

Packet key:
- `(project_fingerprint, phase, chip_category, likely_tool, intent_cluster)`

Packet contents:
- top ranked deterministic advice ids
- pre-synthesized short guidance (AI or programmatic)
- confidence + freshness timestamp + evidence trace ids

Storage:
- `~/.spark/advice_packets/*.json`

### 3) Trigger background prefetch early

Trigger on:
- `on_user_prompt` (already available in `lib/advisory_engine.py`)
- project/chip signals from queue and recent failures

Prefetch flow:
- classify prompt into chip categories
- predict next likely tools
- fetch and synthesize top packets in background
- write packet cache before first PreTool call where possible

### 4) Use a strict hot-path router

PreTool order:
1. Packet cache hit -> emit immediately (target <150ms).
2. Cache miss -> deterministic programmatic synthesis.
3. AI synthesis only if remaining budget is sufficient and not in protected mode.

### 5) Add predictability metrics

Track:
- `packet_hit_rate`
- `prefetch_lead_time_ms` (prefetch finished before usage)
- `hot_path_latency_p95`
- `% emitted within 3s`
- `acted_on_rate` and strict effectiveness by packet source (programmatic vs AI-prepared)

### 6) Keep control deterministic

Non-negotiable:
- control plane, gating, and pass/fail readiness remain deterministic.
- local AI only proposes/synthesizes text, never decides enforcement.

## Practical Routing Recommendation

Given current data:

- `phi4-mini` as quality default for async/background packet synthesis.
- `llama3.2:3b` optional low-latency fallback for interactive refinement.
- `programmatic` mandatory synchronous fallback in PreTool hot path.

This keeps quality while restoring latency predictability.

## Bottom Line

Using local AI everywhere in the synchronous advisory path is not currently predictable enough.
Using local AI in background packet prefetch + deterministic hot-path fallback is the architecture that best improves Spark intelligence, self-evolution utility, and responsiveness at the same time.
