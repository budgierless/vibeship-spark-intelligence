from __future__ import annotations

from pathlib import Path

import lib.mind_bridge as mind_bridge
from lib.cognitive_learner import CognitiveCategory, CognitiveInsight


class _Resp:
    def __init__(self, status_code: int, payload: dict | None = None, text: str = ""):
        self.status_code = status_code
        self._payload = payload or {}
        self.text = text

    def json(self):
        return self._payload


def test_resolve_mind_token_prefers_env(monkeypatch, tmp_path: Path):
    token_file = tmp_path / "mind_server.token"
    token_file.write_text("file-token", encoding="utf-8")
    monkeypatch.setattr(mind_bridge, "MIND_TOKEN_FILE", token_file)
    monkeypatch.setenv("MIND_TOKEN", "env-token")
    assert mind_bridge._resolve_mind_token() == "env-token"


def test_sync_insight_posts_with_bearer_token(monkeypatch, tmp_path: Path):
    token_file = tmp_path / "mind_server.token"
    token_file.write_text("token-from-file", encoding="utf-8")

    monkeypatch.setattr(mind_bridge, "MIND_TOKEN_FILE", token_file)
    monkeypatch.setattr(mind_bridge, "SYNC_STATE_FILE", tmp_path / "sync_state.json")
    monkeypatch.setattr(mind_bridge, "OFFLINE_QUEUE_FILE", tmp_path / "offline_queue.jsonl")
    monkeypatch.delenv("MIND_TOKEN", raising=False)

    captured = {}

    def _fake_post(url, json=None, headers=None, timeout=None):
        captured["url"] = url
        captured["headers"] = headers or {}
        return _Resp(201, {"memory_id": "m-1"})

    monkeypatch.setattr(mind_bridge.requests, "post", _fake_post)
    monkeypatch.setattr(mind_bridge.MindBridge, "_check_mind_health", lambda self, **_: True)

    bridge = mind_bridge.MindBridge(mind_url="http://127.0.0.1:8099")
    insight = CognitiveInsight(
        category=CognitiveCategory.WISDOM,
        insight="Prefer explicit tests for auth regressions.",
        evidence=["audit"],
        confidence=0.9,
        context="tests",
    )

    result = bridge.sync_insight(insight)
    assert result.status == mind_bridge.SyncStatus.SUCCESS
    assert captured["url"].endswith("/v1/memories/")
    assert captured["headers"].get("Authorization") == "Bearer token-from-file"
