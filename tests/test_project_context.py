"""Tests for project context detection and filtering."""

import json
from types import SimpleNamespace

from lib import project_context as pc


def test_detect_project_context_js(tmp_path, monkeypatch):
    monkeypatch.setattr(pc, "CACHE_PATH", tmp_path / "cache.json")
    (tmp_path / "package.json").write_text(
        json.dumps({"dependencies": {"react": "1.0.0", "typescript": "5.0.0"}}),
        encoding="utf-8",
    )
    ctx = pc.get_project_context(tmp_path)
    assert "javascript" in ctx["languages"]
    assert "typescript" in ctx["languages"]
    assert "react" in ctx["frameworks"]


def test_detect_project_context_python(tmp_path):
    (tmp_path / "requirements.txt").write_text("django==3.2\npytest\n", encoding="utf-8")
    ctx = pc.detect_project_context(tmp_path)
    assert "python" in ctx["languages"]
    assert "django" in ctx["frameworks"]
    assert "pytest" in ctx["tools"]


def test_filter_insights_for_context():
    ctx = {"languages": ["python"], "frameworks": []}
    insights = [
        SimpleNamespace(insight="User prefers TypeScript for scripts"),
        SimpleNamespace(insight="Use pytest fixtures for tests"),
    ]
    filtered = pc.filter_insights_for_context(insights, ctx)
    assert len(filtered) == 1
    assert "pytest" in filtered[0].insight.lower()
