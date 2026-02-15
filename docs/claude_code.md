# Claude Code integration (portable)

## 1) Start Spark services

From anywhere on your PATH:
```bash
spark up
```

## 2) Install hooks file

Claude Code needs an **absolute path** for hook commands.
Run:
```bash
./scripts/install_claude_hooks.sh
```
This writes:
- `~/.claude/spark-hooks.json`

Windows (PowerShell):
```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\\install_claude_hooks.ps1
```

## 3) Merge into your Claude Code settings

If you already have `~/.claude/settings.json`, you can:
- copy the `hooks` object from `spark-hooks.json` into your settings, or
- if Claude Code supports multiple hook files, reference it there.

We intentionally **do not auto-merge** settings.json to avoid clobbering custom hooks.

## 4) Confirm

Defaults (override via env; see `lib/ports.py`):
- Dashboard: http://127.0.0.1:${SPARK_DASHBOARD_PORT:-8585}
- sparkd health: http://127.0.0.1:${SPARKD_PORT:-8787}/health

Hook smoke test (generates a minimal PreToolUse/PostToolUse/UserPromptSubmit set):
```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\\claude_hook_smoke_test.ps1
```

If you want richer capture (chat text), ensure `UserPromptSubmit` is enabled.
Spark normalizes hook names to runtime event types used by chips:
- PostToolUse -> post_tool
- PostToolUseFailure -> post_tool_failure
- UserPromptSubmit -> user_prompt
