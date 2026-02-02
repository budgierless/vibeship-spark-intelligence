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

## 3) Merge into your Claude Code settings

If you already have `~/.claude/settings.json`, you can:
- copy the `hooks` object from `spark-hooks.json` into your settings, or
- if Claude Code supports multiple hook files, reference it there.

We intentionally **do not auto-merge** settings.json to avoid clobbering custom hooks.

## 4) Confirm

- Dashboard: http://127.0.0.1:8585
- sparkd health: http://127.0.0.1:8787/health

If you want richer capture (chat text), ensure `UserPromptSubmit` is enabled.
Spark normalizes hook names to runtime event types used by chips:
- PostToolUse -> post_tool
- PostToolUseFailure -> post_tool_failure
- UserPromptSubmit -> user_prompt
