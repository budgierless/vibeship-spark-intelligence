from lib.spark_emotions import SparkEmotions


def test_emotion_timeline_continuity_persists(tmp_path):
    state_file = tmp_path / "emotion_state.json"
    emotions = SparkEmotions(state_file=state_file)

    emotions.register_trigger("user_confusion", intensity=0.8, note="asked for clarification")
    first_len = len(emotions.state.emotion_timeline)

    reloaded = SparkEmotions(state_file=state_file)
    assert len(reloaded.state.emotion_timeline) >= first_len
    assert any(e["event"] == "trigger_applied" for e in reloaded.state.emotion_timeline)


def test_trigger_mapping_updates_emotional_state(tmp_path):
    emotions = SparkEmotions(state_file=tmp_path / "emotion_state.json")
    before = emotions.state
    base_calm = before.calm
    base_strain = before.strain

    emotions.register_trigger("user_frustration", intensity=1.0)

    assert emotions.state.primary_emotion == "supportive_focus"
    assert emotions.state.calm > base_calm
    assert emotions.state.strain > base_strain
    assert emotions.state.recovery_cooldown >= 1


def test_recovery_de_escalates_strain_and_resets_emotion(tmp_path):
    emotions = SparkEmotions(state_file=tmp_path / "emotion_state.json")

    emotions.register_trigger("high_stakes_request", intensity=1.0)
    strained = emotions.state.strain

    for _ in range(6):
        emotions.recover()

    assert emotions.state.strain < strained
    assert emotions.state.primary_emotion == "steady"


def test_unknown_trigger_is_safe_and_logged(tmp_path):
    emotions = SparkEmotions(state_file=tmp_path / "emotion_state.json")
    before = len(emotions.state.emotion_timeline)

    emotions.register_trigger("not_a_real_trigger", intensity=1.0)

    assert len(emotions.state.emotion_timeline) == before + 1
    assert emotions.state.emotion_timeline[-1]["event"] == "trigger_ignored"
