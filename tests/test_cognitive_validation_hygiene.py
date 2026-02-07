from __future__ import annotations

from lib.cognitive_learner import CognitiveCategory, CognitiveInsight


def test_reliability_discounts_telemetry_heavy_struggle_insight():
    insight = CognitiveInsight(
        category=CognitiveCategory.SELF_AWARENESS,
        insight="I struggle with Glob_error tasks",
        evidence=[
            "tool=Glob success=True",
            "Auto-linked from Glob",
            "tool=Bash success=False",
            "Auto-linked from Bash",
        ],
        confidence=0.95,
        context="tool telemetry",
        times_validated=400,
        times_contradicted=5,
    )
    # Raw reliability would be ~0.988 without hygiene; it should now be discounted.
    assert insight.reliability < 0.9


def test_reliability_keeps_clean_outcome_backed_insight_high():
    insight = CognitiveInsight(
        category=CognitiveCategory.WISDOM,
        insight="Validate authentication inputs server-side.",
        evidence=[
            "Outcome link: fixed auth bypass regression in middleware",
            "Outcome link: prevented token misuse in integration tests",
        ],
        confidence=0.8,
        context="security hardening",
        times_validated=20,
        times_contradicted=1,
    )
    assert insight.reliability > 0.9
