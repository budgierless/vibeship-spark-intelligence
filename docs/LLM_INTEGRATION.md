# LLM Integration — Claude CLI via PowerShell Bridge

## Overview

Spark Intelligence uses Claude (via Claude Code CLI with OAuth) for:
- **Advisory synthesis** — turning raw patterns into actionable recommendations
- **EIDOS distillation** — updating the agent's self-model from behavioral observations
- **Pattern interpretation** — finding deeper patterns that rule-based detection misses

No API keys required. Uses Claude Max subscription via OAuth.

## Architecture

```
Python (bridge_cycle.py)
  └─ lib/llm.py → ask_claude()
       └─ subprocess: start /wait /min powershell -File claude_call.ps1
            └─ PowerShell reads prompt file, calls claude CLI, writes response file
                 └─ claude -p --output-format text <prompt>
```

### Why the PowerShell Bridge?

Claude CLI on Windows requires a real console/TTY for OAuth authentication. Python's `subprocess` module doesn't provide one. The workaround:

1. **Write** prompt to `~/.spark/llm_prompt.txt`
2. **Launch** `start /wait /min powershell -File claude_call.ps1` — this spawns a **minimized console window** that gives Claude its required TTY
3. **Read** response from `~/.spark/llm_response.txt` with `utf-8-sig` encoding (handles BOM from PowerShell's `Set-Content`)

On Linux/Mac, direct `subprocess.run(['claude', '-p', ...])` works fine.

## Files

| File | Purpose |
|------|---------|
| `lib/llm.py` | Python wrapper — `ask_claude()`, `synthesize_advisory()`, `distill_eidos()`, `interpret_patterns()` |
| `scripts/claude_call.ps1` | PowerShell bridge — reads prompt file, calls Claude, writes response |
| `scripts/claude_call.cmd` | Batch wrapper (alternative approach, less reliable) |

## Integration Points

### Bridge Cycle (`lib/bridge_cycle.py`)

LLM hooks fire at the end of each bridge cycle:

1. **Advisory synthesis** — triggers when `≥5 patterns detected` OR `≥2 insights merged`
   - Gathers ranked cognitive insights + self-awareness insights
   - Calls `synthesize_advisory()` with patterns + insights
   - Writes output to `SPARK_ADVISORY.md` in `~/.spark/` and OpenClaw workspace

2. **EIDOS distillation** — triggers every **10th productive cycle**
   - Gathers behavioral observations (advisory, chip stats, auto-tuner recs)
   - Calls `distill_eidos()` to update self-model
   - Appends to `~/.spark/eidos_distillations.jsonl`

### Rate Limiting

- **30 calls/hour** (tracked in `~/.spark/llm_calls.json`)
- Prevents runaway LLM usage during high-frequency bridge cycles

## Setup

### Prerequisites

1. **Claude Code CLI** installed: `npm install -g @anthropic-ai/claude-code`
2. **Claude Max subscription** (or any Claude plan with CLI access)
3. **OAuth login**: Run `claude` in a terminal, then `/login`

### Verify

```bash
# Quick test
claude -p "say OK"

# Python test
python scripts/test_advisory.py
```

Manual bridge diagnostics are archived under `scripts/experimental/manual_llm/`.
They are useful for troubleshooting, but they are not part of the canonical startup path.

### Environment

| Variable | Default | Description |
|----------|---------|-------------|
| `SPARK_EMBEDDINGS` | `"1"` | Set to `"0"` to disable fastembed (REQUIRED for bridge_worker — prevents 8GB+ memory leak) |

## Troubleshooting

### "Invalid API key · Please run /login"
Claude CLI isn't authenticated. Run `claude` in a terminal and type `/login`.

### No response file created
The minimized PowerShell window may have been blocked by security software. Check:
- PowerShell execution policy: `Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy Bypass`
- Antivirus didn't block the spawned window

### Rate limited
Check `~/.spark/llm_calls.json` — if >30 entries in the last hour, wait or increase `_MAX_CALLS_PER_HOUR` in `lib/llm.py`.

### UTF-8 BOM in response
Always read response files with `encoding="utf-8-sig"` to strip the BOM that PowerShell adds.
