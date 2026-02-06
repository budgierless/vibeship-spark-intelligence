# Local LLM Recommendations for Spark (Pre-Implementation Decision)

Date: 2026-02-06

## Context

Goal: choose model roles before implementing predictive advisory prefetch.

Roles to optimize:

- realtime advisory hot path,
- async/background packet refinement,
- retrieval and structured-output quality.

## Environment Snapshot

Local host (measured):

- GPU: `NVIDIA GeForce RTX 4090` (24 GB VRAM via `nvidia-smi`)
- RAM: `~64 GB`
- Ollama: `0.15.4`

Installed models:

- `llama3.2:3b`
- `phi4-mini`
- `qwen2.5-coder:3b`
- `gemma3:4b`
- `qwen3:4b`
- `qwen2.5:32b`
- `gpt-oss:20b`

## Empirical Results (Local)

Primary benchmark (19 scenarios, 5 repeats, includes live scenarios):
- source: `tmp/local_model_compare_intel_speed_useful_r5_live12.json`

Secondary benchmark (7 scenarios, 2 repeats):
- source: `tmp/local_model_compare_gemma3_qwen3_r2.json`

Large-model timeout check (7 scenarios, 1 repeat):
- sources:
  - `tmp/local_model_compare_gptoss_qwen32b_r1.json`
  - `tmp/local_model_compare_gptoss_qwen32b_bg_r1.json`

### A) Strongest currently-tested small models

`llama3.2:3b`:
- strict pass: `43.16%`
- latency avg/p95: `2966ms / 3371ms`
- intelligence/usefulness: `86.75 / 77.36`

`phi4-mini`:
- strict pass: `35.79%`
- latency avg/p95: `3145ms / 3746ms`
- intelligence/usefulness: `89.42 / 82.58`

`qwen2.5-coder:3b`:
- strict pass: `29.47%`
- latency avg/p95: `3110ms / 3645ms`
- intelligence/usefulness: `86.31 / 77.69`

### B) Additional small-model check

`gemma3:4b` (different run profile; directional only):
- strict pass: `50.0%`
- latency avg/p95: `3158ms / 4305ms`
- intelligence/usefulness: `76.71 / 76.14`

`qwen3:4b`:
- strict pass: `0.0%`
- latency avg/p95: `3844ms / 4708ms`
- intelligence/usefulness: `47.43 / 47.57`

### C) Large-model status in current harness

`gpt-oss:20b` and `qwen2.5:32b` timed out in this harness configuration:
- strict pass: `0.0%`
- errors: all requests timed out
- measured timeout latencies ~`6s` (strict profile) and ~`14.5s` (raised budget profile)

Interpretation:
- these are not viable for realtime advisory with current timeout settings,
- they may still be useful for offline/async tasks if run in a different worker profile and generation settings.

## Recommendation (Before Proceeding)

## 1) Realtime defaults (advisory hot path)

- Primary quality model (async/prefetch): `phi4-mini`
- Realtime fallback model: `llama3.2:3b`
- Mandatory sync fallback mode: programmatic synthesis

Rationale:
- `phi4-mini` has best intelligence/usefulness in your main benchmark.
- `llama3.2:3b` has better strict-speed behavior.
- current data still shows AI sync tails; deterministic fallback is required.

## 2) Keep vs drop decisions now

Keep:

- `phi4-mini` (quality anchor)
- `llama3.2:3b` (latency fallback)
- `qwen2.5-coder:3b` (secondary coding fallback and diversity)

Conditional keep:

- `gemma3:4b` (worth a full apples-to-apples rerun with the 19-scenario profile)

De-prioritize:

- `qwen3:4b` (current results weak for this workflow)

Not for realtime:

- `gpt-oss:20b`, `qwen2.5:32b` (timeout under current harness profile)

## 3) Other LLMs to evaluate next (officially available)

Priority shortlist:

1. `mistral-small3.1`
   - Candidate for stronger reasoning quality in async packet refinement.
2. `qwen2.5-coder` larger variants (7B/14B class)
   - Candidate for higher coding quality in background advisory synthesis.
3. `gemma3` larger variants (12B class)
   - Candidate for richer long-context and planning tasks.
4. `deepseek-r1` distilled variants
   - Candidate for structured reasoning and policy proposal generation (background only).

For retrieval stack (non-chat model, but high impact):

5. `nomic-embed-text`
6. `bge-m3`

These two should be tested for semantic retrieval quality and stability, especially if predictive packets depend on intent-cluster matching.

## 4) Proposed role mapping

- Realtime advisory emit:
  - `programmatic` first, optional `llama3.2:3b` when budget allows.
- Async packet upgrade:
  - `phi4-mini` default.
- Heavy/offline policy drafting:
  - trial `mistral-small3.1` and/or larger `qwen2.5-coder`.
- Retrieval embeddings:
  - benchmark `nomic-embed-text` vs `bge-m3`.

## 5) Decision Gate to Proceed

Proceed with implementation if all are true:

1. Realtime lane keeps deterministic fallback mandatory.
2. AI sync synthesis is budget-gated.
3. `phi4-mini` remains default for async quality lane.
4. `llama3.2:3b` remains fast fallback.
5. Additional model trials are run in isolated benchmark profile (no production flip until passing).

## Sources

Official model/library pages:

- https://ollama.com/library/llama3.2
- https://ollama.com/library/phi4-mini
- https://ollama.com/library/qwen2.5-coder
- https://ollama.com/library/qwen3
- https://ollama.com/library/gemma3
- https://ollama.com/library/mistral-small3.1
- https://ollama.com/library/deepseek-r1
- https://ollama.com/library/gpt-oss
- https://ollama.com/library/nomic-embed-text
- https://ollama.com/library/bge-m3
