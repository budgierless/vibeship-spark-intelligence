from __future__ import annotations


from lib.cognitive_learner import CognitiveLearner


def test_noise_filter_rejects_lets_transcript_fragments_without_apostrophe():
    learner = CognitiveLearner()
    assert learner.is_noise_insight(
        "lets push gitthub, and then clean up the whole system except this spark, and at some point bring the council of 50"
    )


def test_noise_filter_rejects_rambling_when_using_remember_transcript():
    learner = CognitiveLearner()
    assert learner.is_noise_insight(
        "When using Bash, remember: Do it, and is this system fully connected to spark intelligence flow right now, for spark to e"
    )


def test_noise_filter_rejects_indented_code_snippet():
    learner = CognitiveLearner()
    assert learner.is_noise_insight(
        "        current.confidence = max(current.confidence, disk.confidence)\n"
        "        # Use max instead of sum to avoid double-counting from the same process,\n"
        "        #"
    )
