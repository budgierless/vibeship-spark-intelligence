from pathlib import Path

from lib.personality_evolver import EvolutionConfig, PersonalityEvolver


def test_update_bounds_per_step_and_total_clamp(tmp_path: Path):
    state_path = tmp_path / "personality.json"
    evolver = PersonalityEvolver(
        state_path=state_path,
        enabled=True,
        config=EvolutionConfig(step_size=0.05),
    )

    before = evolver.state["traits"]["warmth"]
    result = evolver.ingest_signals({"user_guided": True, "trait_deltas": {"warmth": 10}}, persist=False)
    after = result["proposed_state"]["traits"]["warmth"]
    assert round(after - before, 6) == 0.05

    for _ in range(30):
        evolver.ingest_signals({"user_guided": True, "trait_deltas": {"warmth": 10}}, persist=False)
    assert 0.0 <= evolver.state["traits"]["warmth"] <= 1.0


def test_clamp_behavior_for_lower_bound(tmp_path: Path):
    state_path = tmp_path / "personality.json"
    evolver = PersonalityEvolver(
        state_path=state_path,
        enabled=True,
        config=EvolutionConfig(step_size=0.5),
    )
    evolver.state["traits"]["assertiveness"] = 0.1

    evolver.ingest_signals(
        {"user_guided": True, "trait_deltas": {"assertiveness": -10}},
        persist=False,
    )
    assert evolver.state["traits"]["assertiveness"] == 0.0


def test_reset_behavior(tmp_path: Path):
    state_path = tmp_path / "personality.json"
    evolver = PersonalityEvolver(state_path=state_path, enabled=True)

    evolver.ingest_signals(
        {"user_guided": True, "trait_deltas": {"playfulness": 1.0}},
        persist=True,
    )
    assert state_path.exists()

    reset = evolver.reset_state(persist=True)
    assert reset["interaction_count"] == 0
    assert all(value == 0.5 for value in reset["traits"].values())
