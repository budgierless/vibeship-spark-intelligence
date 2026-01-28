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


def test_inject_agent_context_opt_in(monkeypatch):
    import lib.orchestration as orch_mod

    # Off by default
    monkeypatch.delenv("SPARK_AGENT_INJECT", raising=False)
    assert orch_mod.inject_agent_context("hello") == "hello"

    # On: prepend context
    monkeypatch.setenv("SPARK_AGENT_INJECT", "1")
    monkeypatch.setenv("SPARK_AGENT_CONTEXT_MAX_CHARS", "50")

    def _fake_context(**_):
        return ("CTX BLOCK", 1)

    monkeypatch.setattr(orch_mod, "build_compact_context", _fake_context)
    out = orch_mod.inject_agent_context("hello")
    assert out.startswith("CTX BLOCK")
    assert out.endswith("hello")
