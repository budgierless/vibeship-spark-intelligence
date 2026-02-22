from __future__ import annotations

from pathlib import Path

from adapters import clawdbot_tailer, openclaw_tailer, stdin_ingest


def test_stdin_ingest_prefers_cli_token(monkeypatch, tmp_path: Path):
    token_file = tmp_path / "sparkd.token"
    token_file.write_text("file-token", encoding="utf-8")
    monkeypatch.setattr(stdin_ingest, "TOKEN_FILE", token_file)
    monkeypatch.setenv("SPARKD_TOKEN", "env-token")
    assert stdin_ingest._resolve_token("cli-token") == "cli-token"


def test_openclaw_tailer_uses_env_then_file(monkeypatch, tmp_path: Path):
    token_file = tmp_path / "sparkd.token"
    token_file.write_text("file-token", encoding="utf-8")
    monkeypatch.setattr(openclaw_tailer, "TOKEN_FILE", token_file)

    monkeypatch.setenv("SPARKD_TOKEN", "env-token")
    assert openclaw_tailer._resolve_token(None) == "env-token"

    monkeypatch.delenv("SPARKD_TOKEN", raising=False)
    assert openclaw_tailer._resolve_token(None) == "file-token"


def test_clawdbot_tailer_returns_none_when_no_token(monkeypatch, tmp_path: Path):
    token_file = tmp_path / "sparkd.token"
    monkeypatch.setattr(clawdbot_tailer, "TOKEN_FILE", token_file)
    monkeypatch.delenv("SPARKD_TOKEN", raising=False)
    assert clawdbot_tailer._resolve_token(None) is None
