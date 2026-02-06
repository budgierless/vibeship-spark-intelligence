# Local AI Analysis for Spark Intelligence and Self-Evolution

Date: 2026-02-06

## Executive Summary

Local AI should be applied selectively, not everywhere.

- Best quality gains: advisory synthesis, distillation quality, contradiction resolution assistance.
- Best utility gains: Pulse chat privacy/cost control, high-context summarization, retrieval disambiguation.
- Biggest risk: synchronous hook latency in `PreToolUse` paths.
- Hard rule: keep control-plane enforcement deterministic.

The right architecture is:
- Deterministic core for enforcement and scoring.
- Local AI as a constrained proposal/synthesis layer.
- Strict validators and fallback paths.

## Live Evidence Snapshot

### 1) Model benchmark (live-connected stress suite)

Source run:
`tmp/local_model_compare_intel_speed_useful_r5_live12.json`

Configuration:
- 19 scenarios
- 5 repeats
- Included 12 scenarios synthesized from real `~/.spark/queue/events.jsonl` contexts

Key outcomes:
- `llama3.2:3b`: best speed and strict 3s reliability.
- `phi4-mini`: best intelligence/usefulness/quality.
- `qwen2.5-coder:3b`: strongest on long noisy context in this run.

Observed scores:
- `llama3.2:3b`: speed `90.65`, intelligence `86.75`, usefulness `77.36`, strict pass `43.2%`
- `phi4-mini`: speed `86.04`, intelligence `89.42`, usefulness `82.58`, strict pass `35.8%`
- `qwen2.5-coder:3b`: speed `86.72`, intelligence `86.31`, usefulness `77.69`, strict pass `29.5%`

### 2) Production loop readiness (live)

Source run:
`python scripts/production_loop_report.py`

Current state: `READY (13/13 passed)`

Important signals:
- `acted_on_rate=68.0%`
- `effectiveness=84.3%`
- strict trace coverage `92.2%`
- strict effectiveness `83.0%`

This indicates the current loop is healthy enough for controlled local-AI expansion.

### 3) Advisory hook latency risk (live logs)

Source:
`~/.spark/advisory_engine.jsonl`

Recent observed advisory engine elapsed time:
- last 100 avg: ~`5404.6ms`
- last 100 p95: ~`8322.3ms`

This is materially above the configured advisory budget expectation and confirms the main operational risk:
local AI in synchronous pre-tool paths can degrade responsiveness.

## Where Local AI Should Improve Spark Most

## A) Advisory Synthesis (High ROI, already active)

Current:
- Retrieval/gating is deterministic.
- Local AI composes final guidance text.
- Called in `PreToolUse` path.

Why it helps:
- Better wording/actionability from mixed insight sources.
- Better conflict handling between old/new learnings.

Risk:
- Synchronous latency in hook path.

Recommendation:
- Keep local AI for synthesis, but add hard guardrails:
  - if remaining budget is low: force programmatic synthesis.
  - cache aggressively by `(tool, intent, advice_ids)`.
  - skip AI synthesis for low-risk tools when queue pressure is high.

## B) Distillation Quality Upgrade (High ROI, not fully exploited)

Current:
- Distillation generation is mostly heuristic/template-driven.
- Reflection layer references LLM intent but implementation is deterministic.

Why local AI helps:
- Better generalized rule statements from noisy step lessons.
- Better extraction of causal "why" and anti-pattern rationale.
- Better playbook compression.

Risk:
- Hallucinated policies if not validated.

Recommendation:
- Use local AI only to produce distillation *candidates*.
- Run deterministic memory-gate + evidence checks before persistence.
- Never bypass existing confidence/revalidation logic.

## C) Retrieval Disambiguation / Rerank (Medium-High ROI)

Current:
- Structural retrieval is deterministic by distillation type/trigger.
- Semantic retrieval uses embeddings + optional triggers.

Why local AI helps:
- Query rewrite and intent disambiguation for ambiguous prompts.
- Better reranking when several candidates have similar score.

Risk:
- Latency and non-deterministic ranking drift.

Recommendation:
- Apply local AI rerank only in async/background or post-filter phase.
- Keep deterministic primary ranking as baseline.
- Use AI rerank only when candidate entropy is high.

## D) Contradiction Resolution Assistant (Medium ROI)

Current:
- Contradiction detection uses embeddings + opposition heuristics.

Why local AI helps:
- Better classification: temporal vs contextual vs direct contradiction.
- Better suggested resolution text for operator review.

Risk:
- Incorrect auto-resolution.

Recommendation:
- AI proposes resolution only.
- Human or deterministic policy confirms update.
- Track resolution quality before auto-trust.

## E) Pulse Chat Utility (High UX ROI, now aligned)

Current:
- Pulse supports OpenAI/Anthropic/Gemini/Ollama, provider order by config.
- Ollama model now defaults to `phi4-mini`.

Why local AI helps:
- Lower cost, better privacy, offline resilience.
- Better continuity with same local model family as advisory.

Risk:
- If `CHAT_PROVIDER=auto` and cloud keys exist, local may not be chosen first.

Recommendation:
- For local-first mode, set `CHAT_PROVIDER=ollama`.
- Keep cloud as explicit fallback only.

## Where Local AI Should NOT Be Used as Decision Authority

## 1) EIDOS control and guardrails

Reason:
- Control plane is explicitly deterministic enforcement by design.
- LLM should not decide phase transitions, safety blocks, or budget rules.

Policy:
- LLM may propose.
- Control plane must decide.

## 2) Gate metrics and readiness scoring

Reason:
- Production gates need stable, auditable measurements.

Policy:
- Keep metrics deterministic.
- Use AI only for narrative summaries, never for pass/fail criteria.

## 3) Schema-critical outputs without validators

Reason:
- Benchmark showed weak strict behavior on structured output tasks without hard schema enforcement.

Policy:
- Use JSON schema validation + repair loop.
- Reject/repair invalid output deterministically.

## Practical Routing Recommendation

Based on live benchmark outcomes:

- Quality-first default: `phi4-mini`
- Strict latency fallback: `llama3.2:3b`
- Noisy long-context fallback: `qwen2.5-coder:3b`

Methodology-specific:
- advisory/semantic/chip-routing: prefer `phi4-mini`
- control-plane/live-execution speed-sensitive: prefer `llama3.2:3b`
- long noisy contexts: prefer `qwen2.5-coder:3b`

## 30-Day Rollout Plan (Honest, low-risk)

1. Stabilize pre-tool latency
- Add hard timeout and forced programmatic fallback for advisory synthesis.
- Success metric: advisory p95 under configured hook budget.

2. Add distillation-candidate AI pass (offline/background)
- Run only after episode completion.
- Require deterministic evidence gate before save.
- Success metric: increase in accepted high-quality distillations without quality-rate drift.

3. Add contradiction-resolution suggestions
- AI-generated resolution labels (`temporal/contextual/direct`) with confidence.
- Human-confirmed initially.
- Success metric: reduced unresolved contradiction backlog.

4. Enable local-first Pulse mode for development environments
- `CHAT_PROVIDER=ollama`.
- Success metric: reduced external API dependency and cost.

## Bottom Line

Using local AI will make Spark better when it is used for:
- synthesis,
- disambiguation,
- candidate generation,
- and UX response quality.

It will make Spark worse if used as:
- the enforcement layer,
- the metric gatekeeper,
- or synchronous authority in hot paths without strict timeout/fallback control.
