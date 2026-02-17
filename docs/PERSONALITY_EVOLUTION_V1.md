# Personality Evolution V1 (Safe, User-Guided)

## Purpose
Enable Spark to evolve conversational style over time from interaction signals **without autonomous goal-seeking**.

This V1 is intentionally narrow: trait tuning only, behind a feature flag, with explicit inspect/reset controls.

---

## Safety Principles

1. **User-guided only**
   - Updates apply only when the signal payload includes `user_guided: true`.
   - No self-initiated optimization or long-horizon objective planning.

2. **Reversible**
   - State is persisted in a single JSON file (`~/.spark/personality_evolution_v1.json`).
   - Reset operation restores defaults immediately.

3. **Bounded autonomy**
   - Trait deltas are incremental and clamped.
   - No trait can move outside `[0.0, 1.0]`.
   - Per-update step is capped (default `0.04`).

4. **No self-directed objectives**
   - Module does not create tasks, pursue goals, or infer intent beyond explicit user-guided signals.
   - Output is style profile only (how to speak), not action policy.

5. **Feature-flag gated**
   - `SPARK_PERSONALITY_EVOLUTION_V1` must be enabled (`1/true/on`).
   - Default behavior is conservative/off.
   - Optional observer mode: `SPARK_PERSONALITY_EVOLUTION_OBSERVER=1` computes proposals without applying them.

---

## Data Model

State schema (`version: 1`):

```json
{
  "version": 1,
  "updated_at": 1739787000.0,
  "interaction_count": 12,
  "traits": {
    "warmth": 0.55,
    "directness": 0.62,
    "playfulness": 0.48,
    "pacing": 0.51,
    "assertiveness": 0.57
  },
  "last_signals": {
    "user_guided": true,
    "trait_deltas": {"directness": 1.0}
  }
}
```

### Traits (V1)
- `warmth`
- `directness`
- `playfulness`
- `pacing`
- `assertiveness`

All default to `0.5` (balanced).

### Input Signals
Accepted payload keys:
- `user_guided: bool` (**required** to apply)
- `trait_deltas: {trait: float}` where each value is interpreted in `[-1, 1]` intensity
- fallback keys: `<trait>_up`, `<trait>_down`

Example:

```json
{
  "user_guided": true,
  "trait_deltas": {"warmth": 0.8, "directness": -0.4}
}
```

---

## Update Loop + Guardrails

1. Load persisted state (or defaults).
2. Verify feature flag is enabled.
3. Verify `user_guided: true`.
4. Extract trait deltas from signal payload.
5. For each trait:
   - bound delta to per-step cap (`step_size`, default `0.04`)
   - apply increment
   - clamp final trait into `[0.0, 1.0]`
6. Increment `interaction_count`; store `last_signals`; update timestamp.
7. Persist state unless observer mode is enabled.
8. Emit style profile with numeric traits + human-readable labels.

---

## Inspect / Apply / Reset

Utility script added:

- `scripts/personality_evolution.py`

### Inspect
```bash
python scripts/personality_evolution.py inspect
```

### Apply signals (feature must be enabled)
```bash
set SPARK_PERSONALITY_EVOLUTION_V1=1
python scripts/personality_evolution.py apply --signals "{\"user_guided\": true, \"trait_deltas\": {\"warmth\": 1.0}}"
```

### Reset
```bash
set SPARK_PERSONALITY_EVOLUTION_V1=1
python scripts/personality_evolution.py reset --yes
```

### Optional observer mode
```bash
set SPARK_PERSONALITY_EVOLUTION_V1=1
set SPARK_PERSONALITY_EVOLUTION_OBSERVER=1
python scripts/personality_evolution.py apply --signals "{\"user_guided\": true, \"trait_deltas\": {\"playfulness\": 1.0}}"
```

In observer mode, output includes `proposed_state` while persisted state remains unchanged.

---

## Test Coverage (minimal)

`tests/test_personality_evolver.py` validates:
- bounded per-step updates and overall clamp behavior
- lower-bound clamp behavior
- reset returns to defaults
