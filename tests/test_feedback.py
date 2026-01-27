from pathlib import Path

import lib.feedback as fb
import lib.skills_registry as sr


def _write_skill(path: Path, content: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def test_update_skill_effectiveness(tmp_path, monkeypatch):
    monkeypatch.setenv("SPARK_SKILLS_DIR", str(tmp_path))
    monkeypatch.setattr(sr, "INDEX_FILE", tmp_path / "skills_index.json")
    monkeypatch.setattr(fb, "SKILLS_EFFECTIVENESS_FILE", tmp_path / "skills_effectiveness.json")

    content = """name: auth-specialist
description: Authentication and OAuth flows
owns:
  - oauth
"""
    _write_skill(tmp_path / "security" / "auth-specialist.yaml", content)

    # Build index
    sr.load_skills_index(force_refresh=True)

    # Update effectiveness
    fb.update_skill_effectiveness("oauth login", success=True, limit=1)
    data = fb._load_json(fb.SKILLS_EFFECTIVENESS_FILE)
    assert data["auth-specialist"]["success"] == 1
