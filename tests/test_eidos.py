"""
EIDOS Integration Tests

Tests the EIDOS rehabilitation fixes:
1. Goal enrichment (pending goals, generic goal detection)
2. Descriptive step intents/decisions (not templates)
3. Pre-action DB save (steps always tracked)
4. Primitive distillation filter (catches tautologies)
5. Selective feedback loop (only meaningful signals)
6. Step evaluation (pass/fail recorded)
7. End-to-end episode lifecycle
8. Auto-tuner integration
"""

from __future__ import annotations

import json
import sqlite3
import time
from pathlib import Path

import pytest

from lib.eidos.models import (
    Episode, Step, Distillation, DistillationType,
    Budget, Phase, Outcome, Evaluation, ActionType,
)
from lib.eidos.store import EidosStore
from lib.eidos.integration import (
    _is_primitive_distillation,
    _is_generic_goal,
    _describe_intent,
    _describe_decision,
)


# ===== Primitive Distillation Filter =====

class TestPrimitiveFilter:
    """Test _is_primitive_distillation catches tautologies and noise."""

    def test_rejects_tool_name_tautology(self):
        assert _is_primitive_distillation("When Execute Read, try: Use Read tool")

    def test_rejects_short_statements(self):
        assert _is_primitive_distillation("Use Read tool")

    def test_rejects_sequence_patterns(self):
        assert _is_primitive_distillation("Read -> Edit -> Bash is effective for fixing bugs")

    def test_rejects_success_rate_statements(self):
        assert _is_primitive_distillation("Read tool has a 95% success rate over 100 uses")

    def test_rejects_mechanical_playbook(self):
        assert _is_primitive_distillation(
            "Playbook for 'Session in unknown project': 1. Use Glob tool -> 2. Use Read tool -> 3. Use Grep tool"
        )

    def test_rejects_generic_session_playbook(self):
        assert _is_primitive_distillation(
            "Playbook for 'Claude Code session': 1. Use Read tool -> 2. Use Read tool"
        )

    def test_rejects_try_use_tool_pattern(self):
        assert _is_primitive_distillation("When something, try: Use Bash tool to run")

    def test_rejects_command_echo_tautology(self):
        """Catches 'When Run command: X, try: Execute: X' tautologies."""
        assert _is_primitive_distillation(
            'When Run command: start "" "http://localhost:5555", try: Execute: start "" "http://localhost:5555"'
        )

    def test_rejects_cross_prefix_tautology(self):
        """Catches tautologies even when condition/action use different prefixes."""
        assert _is_primitive_distillation(
            'When Run command: cd /project && npm test, try: Execute: cd /project && npm test'
        )

    def test_keeps_budget_heuristic(self):
        assert not _is_primitive_distillation(
            "When budget is 82% used without progress, simplify scope"
        )

    def test_keeps_domain_specific_advice(self):
        assert not _is_primitive_distillation(
            "Always use UTC for token timestamps to avoid timezone drift"
        )

    def test_keeps_anti_pattern(self):
        assert not _is_primitive_distillation(
            "When debugging async logic, avoid time.sleep - use await instead"
        )

    def test_keeps_user_preference(self):
        assert not _is_primitive_distillation(
            "User prefers iterative fixes over large refactors in this codebase"
        )

    def test_keeps_architecture_insight(self):
        assert not _is_primitive_distillation(
            "Use dependency injection for database connections to improve testability"
        )


# ===== Generic Goal Detection =====

class TestGenericGoal:
    """Test _is_generic_goal identifies placeholder goals."""

    def test_session_in_unknown(self):
        assert _is_generic_goal("Session in unknown project")

    def test_session_in_project(self):
        assert _is_generic_goal("Session in vibeship-spark-intelligence")

    def test_claude_code_session(self):
        assert _is_generic_goal("Claude Code session")

    def test_empty_goal(self):
        assert _is_generic_goal("")

    def test_specific_goal(self):
        assert not _is_generic_goal("Fix the authentication timeout in user dashboard")

    def test_short_specific_goal(self):
        assert not _is_generic_goal("Add dark mode")


# ===== Descriptive Intent/Decision =====

class TestDescriptiveSteps:
    """Test that _describe_intent and _describe_decision produce meaningful text."""

    def test_read_intent(self):
        intent = _describe_intent("Read", {"file_path": "/project/lib/auth.py"})
        assert "auth.py" in intent
        assert "Read" in intent

    def test_edit_intent(self):
        intent = _describe_intent("Edit", {
            "file_path": "/project/lib/auth.py",
            "old_string": "token.expired()",
            "new_string": "token.expired_utc()",
        })
        assert "auth.py" in intent
        assert "token.expired()" in intent or "Edit" in intent

    def test_bash_intent(self):
        intent = _describe_intent("Bash", {"command": "pytest tests/test_auth.py"})
        assert "pytest" in intent

    def test_grep_intent(self):
        intent = _describe_intent("Grep", {"pattern": "def authenticate"})
        assert "authenticate" in intent

    def test_glob_intent(self):
        intent = _describe_intent("Glob", {"pattern": "**/*.py"})
        assert "*.py" in intent

    def test_edit_decision(self):
        decision = _describe_decision("Edit", {
            "file_path": "/lib/auth.py",
            "new_string": "token.expired_utc()",
        })
        assert "auth.py" in decision
        assert decision != "Use Edit tool"  # Not a template


# ===== Store Operations =====

class TestEidosStore:
    """Test EIDOS store CRUD operations."""

    def test_save_and_retrieve_episode(self, tmp_path):
        store = EidosStore(str(tmp_path / "eidos.db"))
        ep = Episode(
            episode_id="",
            goal="Fix auth timeout",
            success_criteria="test",
            budget=Budget(max_steps=50, max_time_seconds=1800),
        )
        store.save_episode(ep)
        retrieved = store.get_episode(ep.episode_id)
        assert retrieved is not None
        assert retrieved.goal == "Fix auth timeout"

    def test_save_and_retrieve_step(self, tmp_path):
        store = EidosStore(str(tmp_path / "eidos.db"))
        ep = Episode(episode_id="", goal="Test step save", success_criteria="test", budget=Budget())
        store.save_episode(ep)

        step = Step(
            step_id="",
            episode_id=ep.episode_id,
            intent="Read auth.py",
            decision="Inspect authentication module",
        )
        store.save_step(step)

        steps = store.get_episode_steps(ep.episode_id)
        assert len(steps) == 1
        assert steps[0].intent == "Read auth.py"
        assert steps[0].decision == "Inspect authentication module"

    def test_step_insert_or_replace(self, tmp_path):
        """Pre-action save followed by post-action update should produce one row."""
        store = EidosStore(str(tmp_path / "eidos.db"))
        ep = Episode(episode_id="", goal="Test upsert", success_criteria="test", budget=Budget())
        store.save_episode(ep)

        # Pre-action: save preliminary step
        step = Step(
            step_id="step-001",
            episode_id=ep.episode_id,
            intent="Read config.py",
            decision="Check configuration",
            evaluation=Evaluation.UNKNOWN,
        )
        store.save_step(step)

        # Post-action: update same step with result
        step.evaluation = Evaluation.PASS
        step.result = "Config loaded successfully"
        step.lesson = "Config is always in project root"
        store.save_step(step)

        # Should be one step, not two
        steps = store.get_episode_steps(ep.episode_id)
        assert len(steps) == 1
        assert steps[0].evaluation == Evaluation.PASS
        assert steps[0].result == "Config loaded successfully"

    def test_distillation_save_and_retrieve(self, tmp_path):
        store = EidosStore(str(tmp_path / "eidos.db"))
        dist = Distillation(
            distillation_id="",
            type=DistillationType.HEURISTIC,
            statement="When budget is high, simplify scope",
            domains=["general"],
            triggers=["budget"],
        )
        did = store.save_distillation(dist)
        assert did

        all_dists = store.get_all_distillations()
        assert len(all_dists) == 1
        assert all_dists[0].statement == "When budget is high, simplify scope"
        assert all_dists[0].type == DistillationType.HEURISTIC

    def test_distillation_deduplication(self, tmp_path):
        store = EidosStore(str(tmp_path / "eidos.db"))
        d1 = Distillation(
            distillation_id="", type=DistillationType.HEURISTIC,
            statement="Always use UTC for timestamps",
        )
        d2 = Distillation(
            distillation_id="", type=DistillationType.HEURISTIC,
            statement="Always use UTC for timestamps",
        )
        store.save_distillation(d1)
        store.save_distillation(d2)

        all_dists = store.get_all_distillations()
        assert len(all_dists) == 1  # Merged, not duplicated

    def test_distillation_feedback(self, tmp_path):
        store = EidosStore(str(tmp_path / "eidos.db"))
        dist = Distillation(
            distillation_id="", type=DistillationType.HEURISTIC,
            statement="Test feedback tracking",
        )
        did = store.save_distillation(dist)

        store.record_distillation_usage(did, helped=True)
        store.record_distillation_usage(did, helped=True)
        store.record_distillation_usage(did, helped=False)

        updated = store.get_all_distillations()[0]
        assert updated.times_used == 3
        assert updated.times_helped == 2
        assert updated.contradiction_count == 1


# ===== Auto-Tuner =====

class TestAutoTuner:
    """Test the auto-tuner engine."""

    def test_compute_ideal_boost(self):
        from lib.auto_tuner import AutoTuner
        tuner = AutoTuner()

        # High effectiveness -> boost above 1.0
        boost = tuner.compute_ideal_boost(0.85, 0.5)
        assert boost > 1.0

        # Low effectiveness -> boost below 1.0
        boost = tuner.compute_ideal_boost(0.05, 0.5)
        assert boost < 1.0

        # Average effectiveness -> boost near 1.0
        boost = tuner.compute_ideal_boost(0.5, 0.5)
        assert 0.9 <= boost <= 1.1

    def test_dry_run_makes_no_changes(self, tmp_path):
        from lib.auto_tuner import AutoTuner, _write_json_atomic

        tuneables = {
            "auto_tuner": {
                "enabled": True,
                "max_change_per_run": 0.15,
                "source_boosts": {"cognitive": 1.0},
                "source_effectiveness": {},
                "tuning_log": [],
            }
        }
        tp = tmp_path / "tuneables.json"
        _write_json_atomic(tp, tuneables)

        tuner = AutoTuner(tp)
        report = tuner.run(dry_run=True, force=True)

        # File should be unchanged
        after = json.loads(tp.read_text())
        assert after["auto_tuner"]["source_boosts"]["cognitive"] == 1.0

    def test_skips_low_sample_sources(self):
        from lib.auto_tuner import AutoTuner
        tuner = AutoTuner()

        report = tuner.run(dry_run=True, force=True)
        # Sources with < MIN_SAMPLES should be in skipped list
        skipped_names = [s.split(" ")[0] for s in report.skipped]
        for src in skipped_names:
            # Verify these actually have low samples
            data = tuner.get_effectiveness_data()
            if src in data:
                assert data[src].get("total", 0) < tuner.MIN_SAMPLES

    def test_respects_max_change_per_run(self):
        from lib.auto_tuner import AutoTuner
        tuner = AutoTuner()

        report = tuner.run(dry_run=True, force=True)
        for change in report.changes:
            assert abs(change.delta) <= tuner.max_change + 0.001  # float tolerance

    def test_apply_recommendations_skips_noop_changes(self, tmp_path):
        from lib.auto_tuner import AutoTuner, TuneRecommendation, _write_json_atomic

        tuneables = {
            "auto_tuner": {
                "enabled": True,
                "max_change_per_run": 0.15,
                "source_boosts": {},
                "source_effectiveness": {},
                "tuning_log": [],
            },
            "advisor": {
                "min_rank_score": 0.25,
            },
        }
        tp = tmp_path / "tuneables.json"
        _write_json_atomic(tp, tuneables)
        before = tp.read_text(encoding="utf-8")

        rec = TuneRecommendation(
            section="advisor",
            key="min_rank_score",
            current_value=0.25,
            recommended_value=0.25,
            reason="already set",
            confidence=0.9,
            impact="low",
        )

        tuner = AutoTuner(tp)
        applied = tuner.apply_recommendations([rec], mode="aggressive")

        assert applied == []
        assert tp.read_text(encoding="utf-8") == before

    def test_apply_changes_skips_noop_boost_updates(self, tmp_path):
        from lib.auto_tuner import AutoTuner, BoostChange, _write_json_atomic

        tuneables = {
            "auto_tuner": {
                "enabled": True,
                "max_change_per_run": 0.15,
                "source_boosts": {"cognitive": 1.0},
                "source_effectiveness": {},
                "tuning_log": [],
            }
        }
        tp = tmp_path / "tuneables.json"
        _write_json_atomic(tp, tuneables)
        before = tp.read_text(encoding="utf-8")

        tuner = AutoTuner(tp)
        tuner._apply_changes(
            changes=[
                BoostChange(
                    source="cognitive",
                    old_boost=1.0,
                    new_boost=1.0,
                    effectiveness=0.5,
                    sample_count=30,
                    reason="no-op",
                )
            ],
            new_effectiveness={"cognitive": 0.5},
            timestamp="2026-02-12T12:00:00+00:00",
            data_basis="test",
        )

        assert tp.read_text(encoding="utf-8") == before

    def test_run_records_last_run_on_noop_cycle(self, tmp_path):
        from lib.auto_tuner import AutoTuner, _write_json_atomic

        tuneables = {
            "auto_tuner": {
                "enabled": True,
                "run_interval_s": 86400,
                "max_change_per_run": 0.15,
                "source_boosts": {},
                "source_effectiveness": {},
                "tuning_log": [],
            }
        }
        tp = tmp_path / "tuneables.json"
        _write_json_atomic(tp, tuneables)

        tuner = AutoTuner(tp)
        tuner.get_effectiveness_data = lambda: {}

        assert tuner.should_run() is True
        report = tuner.run(dry_run=False, force=True)
        assert report.changes == []

        after = json.loads(tp.read_text(encoding="utf-8"))
        auto = after.get("auto_tuner", {})
        assert auto.get("last_run")
        assert auto.get("tuning_log")
        assert auto["tuning_log"][-1].get("action") == "auto_tune_noop"

        assert tuner.should_run() is False


# ===== Anti-Pattern Fix Tests =====

class TestAntiPatternFixes:
    """Test the anti-pattern contradiction storm fixes."""

    def test_generalize_failed_decision_bash(self):
        from lib.eidos.elevated_control import _generalize_failed_decision
        result = _generalize_failed_decision("Execute: cd /home/user/project && find . -name '*.py'")
        assert "commands" in result.lower()  # Should generalize to "'cd' commands" or similar
        assert "/home/user" not in result  # No literal paths

    def test_generalize_failed_decision_git(self):
        from lib.eidos.elevated_control import _generalize_failed_decision
        result = _generalize_failed_decision("Execute: git push origin main")
        assert "git" in result.lower()

    def test_generalize_failed_decision_non_bash(self):
        from lib.eidos.elevated_control import _generalize_failed_decision
        result = _generalize_failed_decision("Inspect auth.py")
        assert "Read" in result or "operations" in result

    def test_generalize_failed_decision_glob(self):
        from lib.eidos.elevated_control import _generalize_failed_decision
        result = _generalize_failed_decision("Locate files by pattern **/*.py")
        assert "Glob" in result

    def test_anti_pattern_relevance_matching(self):
        from lib.eidos.integration import _is_anti_pattern_relevant
        # Anti-pattern about 'find' should match find commands
        assert _is_anti_pattern_relevant(
            "When repeated 'find' commands fail, try a different approach",
            "Execute: find . -name '*.py'"
        )

    def test_anti_pattern_relevance_no_match(self):
        from lib.eidos.integration import _is_anti_pattern_relevant
        # Anti-pattern about 'find' should NOT match git commands
        assert not _is_anti_pattern_relevant(
            "When repeated 'find' commands fail, try a different approach",
            "Execute: git push origin main"
        )

    def test_confidence_decay_on_high_contradiction(self, tmp_path):
        """Distillations with >80% contradiction rate should lose confidence."""
        store = EidosStore(str(tmp_path / "eidos.db"))
        dist = Distillation(
            distillation_id="", type=DistillationType.ANTI_PATTERN,
            statement="Test decay", confidence=0.7,
        )
        did = store.save_distillation(dist)

        # Simulate 12 contradictions (100% rate, > 10 uses)
        for _ in range(12):
            store.record_distillation_usage(did, helped=False)

        updated = store.get_distillation(did)
        assert updated.confidence < 0.7  # Should have decayed
        assert updated.contradiction_count == 12

    def test_confidence_grows_when_helped(self, tmp_path):
        """Distillations with good track record should grow confidence."""
        store = EidosStore(str(tmp_path / "eidos.db"))
        dist = Distillation(
            distillation_id="", type=DistillationType.HEURISTIC,
            statement="Test stable", confidence=0.7,
        )
        did = store.save_distillation(dist)

        # 8 helped, 2 contradicted (80% helpful, not > 80% contradictions)
        for _ in range(8):
            store.record_distillation_usage(did, helped=True)
        for _ in range(2):
            store.record_distillation_usage(did, helped=False)

        updated = store.get_distillation(did)
        # Confidence should grow above 0.7 due to positive outcomes
        assert updated.confidence > 0.7
        # But not hit 1.0 with only 8 positives
        assert updated.confidence < 1.0

