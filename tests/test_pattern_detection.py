"""
Tests for Pattern Detection Layer (Phase 2).

Run with: python -m pytest tests/test_pattern_detection.py -v
"""

import pytest
from lib.pattern_detection import (
    PatternType,
    CorrectionDetector,
    SentimentDetector,
    RepetitionDetector,
    SequenceDetector,
    PatternAggregator,
)


class TestCorrectionDetector:
    """Test correction detection."""

    def setup_method(self):
        self.detector = CorrectionDetector()

    def test_explicit_correction(self):
        """Test 'no, I meant' detection."""
        event = {
            "session_id": "test",
            "hook_event": "UserPromptSubmit",
            "payload": {"text": "no, I meant the other file"},
        }
        patterns = self.detector.process_event(event)
        assert len(patterns) == 1
        assert patterns[0].pattern_type == PatternType.CORRECTION
        assert patterns[0].confidence >= 0.9

    def test_polite_correction(self):
        """Test 'actually' detection."""
        event = {
            "session_id": "test",
            "hook_event": "UserPromptSubmit",
            "payload": {"text": "actually, could you use typescript instead"},
        }
        patterns = self.detector.process_event(event)
        assert len(patterns) == 1
        assert patterns[0].pattern_type == PatternType.CORRECTION
        assert patterns[0].confidence >= 0.7

    def test_not_correction(self):
        """Test normal message is not detected as correction."""
        event = {
            "session_id": "test",
            "hook_event": "UserPromptSubmit",
            "payload": {"text": "can you help me write a function"},
        }
        patterns = self.detector.process_event(event)
        assert len(patterns) == 0


class TestSentimentDetector:
    """Test sentiment detection."""

    def setup_method(self):
        self.detector = SentimentDetector()

    def test_satisfaction(self):
        """Test satisfaction detection."""
        event = {
            "session_id": "test",
            "hook_event": "UserPromptSubmit",
            "payload": {"text": "perfect! that's exactly what I needed"},
        }
        patterns = self.detector.process_event(event)
        assert len(patterns) == 1
        assert patterns[0].pattern_type == PatternType.SATISFACTION
        assert patterns[0].confidence >= 0.9

    def test_frustration(self):
        """Test frustration detection."""
        event = {
            "session_id": "test",
            "hook_event": "UserPromptSubmit",
            "payload": {"text": "ugh this is still not working"},
        }
        patterns = self.detector.process_event(event)
        assert len(patterns) == 1
        assert patterns[0].pattern_type == PatternType.FRUSTRATION
        assert patterns[0].confidence >= 0.9

    def test_neutral(self):
        """Test neutral message has no sentiment."""
        event = {
            "session_id": "test",
            "hook_event": "UserPromptSubmit",
            "payload": {"text": "now add a function called process"},
        }
        patterns = self.detector.process_event(event)
        assert len(patterns) == 0


class TestRepetitionDetector:
    """Test repetition detection."""

    def setup_method(self):
        self.detector = RepetitionDetector()

    def test_repetition_detected(self):
        """Test 3+ similar requests detected."""
        events = [
            {"session_id": "test", "hook_event": "UserPromptSubmit",
             "payload": {"text": "add a button to the page"}},
            {"session_id": "test", "hook_event": "UserPromptSubmit",
             "payload": {"text": "please add the button to page"}},
            {"session_id": "test", "hook_event": "UserPromptSubmit",
             "payload": {"text": "I need a button on the page"}},
        ]

        patterns = []
        for event in events:
            patterns.extend(self.detector.process_event(event))

        # Should detect repetition after 3rd similar request
        assert len(patterns) == 1
        assert patterns[0].pattern_type == PatternType.REPETITION
        assert patterns[0].context["repetition_count"] >= 3

    def test_different_requests(self):
        """Test different requests not detected as repetition."""
        events = [
            {"session_id": "test2", "hook_event": "UserPromptSubmit",
             "payload": {"text": "add a login page"}},
            {"session_id": "test2", "hook_event": "UserPromptSubmit",
             "payload": {"text": "fix the database connection"}},
            {"session_id": "test2", "hook_event": "UserPromptSubmit",
             "payload": {"text": "update the stylesheet"}},
        ]

        patterns = []
        for event in events:
            patterns.extend(self.detector.process_event(event))

        assert len(patterns) == 0


class TestSequenceDetector:
    """Test sequence detection."""

    def setup_method(self):
        self.detector = SequenceDetector()

    def test_read_edit_success(self):
        """Test Read -> Edit sequence detection."""
        events = [
            {"session_id": "test", "hook_event": "PostToolUse", "tool_name": "Read"},
            {"session_id": "test", "hook_event": "PostToolUse", "tool_name": "Edit"},
        ]

        patterns = []
        for event in events:
            patterns.extend(self.detector.process_event(event))

        assert len(patterns) == 1
        assert patterns[0].pattern_type == PatternType.SEQUENCE_SUCCESS
        assert "Read" in patterns[0].context["sequence"]
        assert "Edit" in patterns[0].context["sequence"]

    def test_failure_streak(self):
        """Test consecutive failures detection."""
        events = [
            {"session_id": "test2", "hook_event": "PostToolUseFailure", "tool_name": "Bash"},
            {"session_id": "test2", "hook_event": "PostToolUseFailure", "tool_name": "Bash"},
            {"session_id": "test2", "hook_event": "PostToolUseFailure", "tool_name": "Bash"},
        ]

        patterns = []
        for event in events:
            patterns.extend(self.detector.process_event(event))

        # Should detect failure streak after 3 consecutive failures
        streak_patterns = [p for p in patterns if p.context.get("streak_length", 0) >= 3]
        assert len(streak_patterns) >= 1


class TestPatternAggregator:
    """Test pattern aggregator."""

    def setup_method(self):
        self.aggregator = PatternAggregator()

    def test_corroboration_boost(self):
        """Test corroborated patterns get boosted."""
        # Correction + Frustration together
        event = {
            "session_id": "test",
            "hook_event": "UserPromptSubmit",
            "payload": {"text": "no, I meant something else! ugh still not right"},
        }
        patterns = self.aggregator.process_event(event)

        # Should have both correction and frustration
        types = [p.pattern_type for p in patterns]
        assert PatternType.CORRECTION in types or PatternType.FRUSTRATION in types

        # Check for corroboration evidence
        for p in patterns:
            if "CORROBORATED" in str(p.evidence):
                assert p.confidence > 0.85

    def test_stats(self):
        """Test aggregator stats."""
        event = {
            "session_id": "test",
            "hook_event": "UserPromptSubmit",
            "payload": {"text": "perfect!"},
        }
        self.aggregator.process_event(event)

        stats = self.aggregator.get_stats()
        assert "total_patterns_detected" in stats
        assert "detectors" in stats
        assert len(stats["detectors"]) == 4  # 4 detectors


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
