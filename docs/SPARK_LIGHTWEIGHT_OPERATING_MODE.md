# Spark Lightweight Operating Mode

Date: 2026-02-12
Owner: Spark Intelligence
Status: Active operating policy

## Why We Are Doing This

Spark currently works end-to-end, but reliability trust is limited by noise and churn:
- advisory can still fall back too often
- repeated low-signal outputs reduce trust
- optional subsystems can create operational noise
- system complexity can grow faster than measurable value

The goal is not "more intelligence surface area." The goal is:
- faster useful guidance
- fewer repeated/noisy actions
- lower runtime overhead
- tighter accountability for what actually improves outcomes

This policy keeps Spark lightweight and outcome-focused.

## Operating Principle

Optimize one critical path first:

`retrieval -> advisory -> action -> outcome attribution`

Every change must improve this path, or be removed.

## Carmack Style Rules (Applied to Spark)

1. One north-star metric:
   - `acted_on_useful_advisory_rate`
2. Hard runtime budgets:
   - advisory path must stay within strict latency budget
   - fail fast when budget is exceeded
3. Kill low-value complexity:
   - suppress or remove paths with no measurable lift
4. Deterministic failures:
   - every failure must classify cleanly (`auth|timeout|policy|transport|no_hit|stale|unknown`)
5. Short validation loop:
   - ship small
   - measure on real sessions
   - keep or delete quickly

## 7-Day Lightweight Execution Loop

1. Freeze feature expansion.
2. Allow only changes tied to KPI lift.
3. Review metrics daily:
   - fallback ratio
   - duplicate advisory rate
   - advisory actionability rate
   - core health status
4. Run weekly delete pass:
   - remove rules/systems with no measurable lift in 7 days.

## Required Runtime Guardrails

- Packet-first advisory stays primary.
- Repeat suppression remains enabled.
- Actionability enforcement remains enabled.
- Packet no-emit fallback emission stays disabled by default (opt-in only).
- If packet no-emit fallback is enabled, fallback-rate guard must remain enabled (`fallback_rate_guard_enabled`) with a bounded max ratio window.
- Sync context defaults to core adapters only (`openclaw`, `exports`).
- Optional adapter failures must not degrade core health.
- Memory fusion must filter primitive/tool-error telemetry before advisory ranking.
- Sync-heavy exposure sources stay deduped/capped.
- Chip merge low-quality cooldown suppression stays enabled.
- Chip merge duplicate-churn throttle stays enabled.
- Auto-tuner remains conservative (`suggest` by default, then `conservative` when stable).

## What Gets Removed or Downgraded

Downgrade or remove when all are true:
- no KPI lift across 7 days
- non-trivial runtime cost
- adds operator/debug noise
- no direct contribution to critical path quality

Examples:
- optional connector spam
- duplicate advisory variants
- low-quality chip merge churn
- no-op tuning write churn

## Change Acceptance Gate

Before merging any optimization:

1. Define target metric delta.
2. Define budget impact (latency/memory/churn).
3. Run real-session validation slice.
4. Record keep/rollback decision in:
   - `docs/OPENCLAW_RESEARCH_AND_UPDATES.md`

No metric delta, no merge.

## Documentation Integration Checklist

Use this checklist whenever lightweight policy changes:

1. Update policy doc:
   - `docs/SPARK_LIGHTWEIGHT_OPERATING_MODE.md`
2. Update runtime/tuneables behavior:
   - `Intelligence_Flow.md`
   - `TUNEABLES.md`
   - `docs/SPARK_CARMACK_OPTIMIZATION_IMPLEMENTATION.md`
3. Update operator runbook:
   - `docs/OPENCLAW_OPERATIONS.md`
4. Update navigation hubs:
   - `docs/DOCS_INDEX.md`
   - `docs/GLOSSARY.md`
   - `README.md` (Documentation section)
5. Log experiment decision:
   - `docs/OPENCLAW_RESEARCH_AND_UPDATES.md`

## Definition of Done

Lightweight mode is working when:
- advisory usefulness improves with lower noise
- fallback and duplicate rates trend down
- core services remain stable under normal load
- monthly docs drift stays low (policy and runtime docs match code)
