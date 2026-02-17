# CONSCIOUSNESS_BRIDGE_V1

## Purpose
Define how **vibeship-spark-intelligence** ingests emotional context from **vibeship-spark-consciousness** in a controlled, fallback-safe way.

---

## 1) Ingestion points in intelligence pipeline

Primary ingestion target (V1):
- `lib.advisory_synthesizer` before synthesis composition

Secondary optional ingestion points:
- `lib.bridge_cycle` context assembly (for richer active context views)
- `lib.bridge` / dashboard status exposure (observability only)

### Recommended flow
1. Read consciousness payload from bridge file (local contract).
2. Validate schema and freshness.
3. Convert to bounded advisory shaping hints.
4. Apply only to:
   - tone
   - verbosity
   - pacing
   - questioning behavior
5. Never apply to:
   - autonomous goal generation
   - safety gate overrides
   - action execution permissions

---

## 2) Fallback behavior when bridge is unavailable

Bridge is considered unavailable when:
- file missing
- JSON malformed
- unsupported schema_version
- stale (`staleness_seconds > ttl_seconds` or file age too high)
- boundary flags violate safe contract

Fallback mode:
- use current neutral/default strategy:
  - `response_pace = balanced`
  - `verbosity = medium`
  - `tone_shape = grounded_warm`
  - `ask_clarifying_question = false`
- log debug marker (`consciousness_bridge=fallback`)
- continue pipeline without hard failure

Degradation principle:
- **soft failure only** (no runtime breakage)

---

## 3) Bounded influence policy

### Influence cap
- Consume `boundaries.max_influence` from payload, clamp to `[0.0, 0.35]`.
- If missing, default to `0.25`.

### Influence scope
Allowed:
- response framing
- wording warmth/calmness
- clarifying-question tendency

Disallowed:
- changing objective hierarchy
- suppressing warnings/safety checks
- introducing manipulative nudging

### Policy guards
Required true flags from payload:
- `user_guided`
- `no_autonomous_objectives`
- `no_manipulative_affect`

If any false/missing -> reject payload and fallback.

---

## 4) Initial implementation plan

Phase 1 (this change):
- docs + minimal loader/validator in `lib/consciousness_bridge.py`
- no hard coupling to core path

Phase 2:
- wire loader into `advisory_synthesizer._emotion_decision_hooks` path as upstream override layer
- emit bridge read metrics (ok/fallback/stale/invalid)

Phase 3:
- expand to optional local-service transport
- add integration tests with fixture payloads

---

## 5) Quick contract mapping (consumer-side)

Input `emotional_state` + `guidance` maps to runtime style strategy:
- `guidance.response_pace` -> advisory pace
- `guidance.verbosity` -> advisory detail budget
- `guidance.tone_shape` -> opener/tone profile
- `guidance.ask_clarifying_question` -> question suffix switch

`mission.kernel` can be used as an additional confidence gate for advisory emission, but never as a sole safety mechanism.
