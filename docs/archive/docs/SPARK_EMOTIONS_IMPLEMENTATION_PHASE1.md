# Spark Emotions — Implementation Notes (Phase 1)

## Scope
Phase 1 delivers a standalone runtime module for emotional state handling and voice-profile mapping.

## Added
- `lib/spark_emotions.py`
  - `EmotionState` dataclass
  - bounded mode transitions (`spark_alive`, `real_talk`, `calm_focus`)
  - feedback application (`too_fast`, `too_sharp`, `too_flat`, `too_intense`, `wants_more_emotion`)
  - deterministic TTS profile mapping from emotional state
  - default persistence in `~/.spark/emotion_state.json`
  - optional override via `SPARK_EMOTION_STATE_FILE`
  - one-time migration from legacy repo-local `.spark/emotion_state.json` when runtime file is absent

## Why standalone first
To avoid piecemeal wiring and regressions. This keeps the core logic testable and ready for one-shot integration.

## Integration plan (Phase 2)
1. Hook module into response-style preprocessor.
2. Hook voice_profile into TTS directive generator.
3. Add chat commands:
   - `/emotion mode <spark_alive|real_talk|calm_focus>`
   - `/emotion feedback <too_fast|too_sharp|too_flat|too_intense|more_emotion>`
   - `/emotion status`
4. Add weekly summary report with outcome deltas.

## Current behavior
- Mode changes are gradual, not abrupt.
- Feedback nudges state with bounded deltas.
- Voice profile remains constrained (safe min/max ranges).
- Safety flags are explicit in `status()`.

## Safety constraints
- No fabricated claims of biological emotions.
- No manipulative emotional framing.
- Clarity over theatricality in high-stakes contexts.
