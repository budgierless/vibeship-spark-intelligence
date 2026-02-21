# Advisory System Renewal (2026-02-21)

## Objective

Make advisory delivery actionable, high-signal, and reusable across:

- coding workflows
- architecture/product/research decisions
- operations and maintenance work

The system should move memory into:

`memory -> distillation -> transformation -> advisory packet storage -> advisory retrieval`

and then drive emissions from advisory storage as the single source of truth.

## What was broken and fixed

The advisory engine was effectively silent because retrieval quality was good but emission controls were collapsing everything.

### 1) Import-time failure (advisory engine dead)

- `lib/advisory_packet_store.py` had missing closing parentheses in multiple functions.
- `on_pre_tool()` import of the packet store failed under its outer `try/except`, returning `None`.
- Result: retrieval/gate/emit never executed (0% advisory emission despite 100% retrieval).
- Fix: syntax repair in `lib/advisory_packet_store.py`.

### 2) Score crushing across independent multipliers

- Previous ranking and gate scoring used many multiplicative factors, which drove otherwise good candidates below advisory thresholds.
- Fix:
  - `lib/advisor.py`: switched to additive ranking:
    - `score = 0.45*relevance + 0.30*quality + 0.25*trust`
    - source quality normalized to `_SOURCE_QUALITY` (0-1) replacing legacy boost ranges.
  - `lib/advisory_gate.py`: aligned gate score to additive base:
    - `base_score = 0.45*context_match + 0.25*confidence + 0.15`

### 3) Repeat suppression exhaustion

- `shown_advice_ids` was a growing permanent blocklist.
- After ~50 tool calls in a session, most advice became ineligible.
- Fix:
  - `lib/advisory_state.py`: store shown IDs as `{advice_id: timestamp}` with TTL (`SHOWN_ADVICE_TTL_S = 600`).
  - `advisory_state` supports backward compatibility from prior list format.

### 4) Watchtower visibility and state hygiene

- Obsidian now acts as an observation tower for advisory packets:
  - added readiness/freshness/invalidation metadata in packet render payloads
  - added explicit invalid packet section in generated catalog
  - invalidation writes now carry reason and are immediately synced when Obsidian export is enabled

## Current steady-state flow

1) Intake/normalization captures raw event context and quality metadata.
2) Distillation + transformer applies quality gating and suppression.
3) Advisory transformation enriches:
   - actionability
   - reasoning
   - outcome-link and trust metadata
4) Advisory packet store persists curated advisories:
   - TTL freshness metadata
   - readiness, stale, and invalid states
   - invalidation reasons for auditability
5) Advisory engine evaluates hot-path retrieval:
   - ranking and gate on additive scores
   - dedupe and cooldown by policy
   - emission with authority labels (`WARNING`, `NOTE`, `WHISPER`)
6) Obsidian outputs mirror packet state and become the user-facing watchtower.

## Current outcomes (latest known)

- Retrieval: 100% in the tracked benchmark.
- Emission: 5.6% of tool calls in that run.
- Garbage leakage: 0 in tracked run.
- Scope: all domains, not only coding.

## Key configuration points to review

- `lib/advisor.py`: `_SOURCE_QUALITY`, `_rank_score`, `MIN_RANK_SCORE`.
- `lib/advisory_gate.py`: `TOOL_COOLDOWN_S`, authority thresholds, max emit per call.
- `lib/advisory_state.py`: `SHOWN_ADVICE_TTL_S`, shown ID storage policy.
- `lib/advisory_packet_store.py`: Obsidian sync payload fields, invalidation handling, catalog inclusion rules.

## Watchtower contract (Obsidian)

- `~/.spark/advice_packets/index.md` is the observability index for packet health.
- It must show:
  - ready vs stale
  - invalid/rejected states
  - invalidation reason text
  - freshness age and next expiry
- Packet-level exports should remain deterministic so humans can trace:
  - where an advisory came from
  - why it was blocked/invalidated
  - whether it remains eligible now

## Open actions to keep reliability high

1) Add explicit advisory decision ledger fields for each retrieval decision:
   - `selected`, `excluded`, `reasons`, `scores`, `route`.
2) Add a compact, queryable archive for suppressed/invalid candidates.
3) Add periodic dashboard health for:
   - packet hit ratio
   - stale/invalid ratio
   - repeat suppression ratio
4) Keep the full pipeline from memory to advisory packet storage as the only runtime source for live emissions.
