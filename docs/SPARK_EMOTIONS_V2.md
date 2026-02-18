# Spark Emotions V2 (Stateful Continuity)

Status: `canonical`
Scope: bounded emotions runtime behavior and advisory shaping hooks

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

## Live wiring (V2 -> runtime behavior)
Emotions V2 hooks are now consumed in the live advisory response path:

- `lib/advisory_synthesizer.py::_emotion_decision_hooks()` loads `SparkEmotions().decision_hooks()` with fail-closed guardrails.
- `synthesize_programmatic(...)` applies hook strategy to real output shaping:
  - `verbosity=concise|structured|medium` changes how much context is emitted.
  - `response_pace=slow|balanced|lively` adjusts detail budget in emitted guidance.
  - `tone_shape` selects the opener style (e.g., `Calm focus:`, `Grounded take:`).
  - `ask_clarifying_question=true` appends a short user-guided clarifier.
- `_build_synthesis_prompt(...)` injects pace/verbosity/tone strategy for AI synthesis mode.

Safety is preserved: if guardrails are missing (`user_guided` + `no_autonomous_objectives`), synthesis falls back to neutral defaults.

### Quick verification
Run:

```bash
pytest -q tests/test_advisory_synthesizer_emotions.py
```

Expected: tests pass and confirm Emotions V2 hooks affect both programmatic output shaping and AI prompt shaping.
