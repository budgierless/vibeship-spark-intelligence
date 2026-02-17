# Spark Emotions V2 (Stateful Continuity)

Spark Emotions V2 upgrades the runtime from tone-only adjustments to a bounded emotional continuity model.

## What V2 adds
- **Emotion timeline state** (`emotion_timeline`): lightweight event history to preserve conversational continuity across turns/restarts.
- **Trigger mapping** (`TRIGGER_MAP`): deterministic trigger -> emotion transitions (`user_frustration`, `high_stakes_request`, etc.).
- **Recovery behavior** (`recover()`): gradual de-escalation toward mode targets with cooldown handling.
- **Decision hooks** (`decision_hooks()`): response-strategy hints (pace, verbosity, tone shape) based on emotional state.

## Safety guardrails
- User-guided behavior only; no autonomous objectives.
- No manipulative emotional framing.
- No claims of biological feelings or sentience.
- Strategy hooks influence communication style only (not independent goal-seeking).

## Example flow
1. Turn N: trigger `user_frustration` -> emotion becomes `supportive_focus`, calm increases, strain rises.
2. Next response uses hooks: slower pace, concise, reassuring clarity.
3. Turn N+1: `recover()` step lowers strain and moves state toward mode baseline.
4. After cooldown resolves and strain normalizes, emotion returns to `steady`.

## Runtime surface
- `register_trigger(trigger, intensity=..., note=...)` (unknown triggers are ignored + logged in timeline)
- `recover()`
- `decision_hooks()`
- Existing APIs retained: `set_mode()`, `apply_feedback()`, `voice_profile()`, `status()`.
