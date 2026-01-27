from pathlib import Path

from lib.orchestration import SparkOrchestrator


def test_recommend_agent_by_skill(tmp_path, monkeypatch):
    orch = SparkOrchestrator(root_dir=tmp_path)

    # Register agents with skill capabilities
    orch.register_agent("agent-a", "Agent A", ["auth-specialist"])
    orch.register_agent("agent-b", "Agent B", ["multi-agent-orchestration"])

    # Monkeypatch skill router to return a known skill
    import lib.orchestration as orch_mod
    monkeypatch.setattr(
        orch_mod, "recommend_skills",
        lambda query, limit=3: [{"skill_id": "multi-agent-orchestration"}]
    )

    agent_id, reason = orch.recommend_agent("coordinate agents", "")
    assert agent_id == "agent-b"
    assert "Matched skills" in reason
