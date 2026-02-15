<p align="center">
  <img src="logo.png" alt="Spark Intelligence" width="120">
  <h1 align="center">Spark Intelligence</h1>
  <p align="center">
    <strong>Your AI coding agent gets smarter every day. Automatically.</strong>
  </p>
  <p align="center">
    <img src="https://img.shields.io/badge/python-3.10+-blue?style=flat-square" alt="Python">
    <img src="https://img.shields.io/badge/no_API_keys-Claude_OAuth-green?style=flat-square" alt="OAuth">
    <img src="https://img.shields.io/badge/embeddings-OFF_(free)-orange?style=flat-square" alt="Embeddings">
    <img src="https://img.shields.io/badge/platform-Win%20%7C%20Mac%20%7C%20Linux-lightgrey?style=flat-square" alt="Platform">
  </p>
</p>

---

## What is this?

Spark Intelligence is a self-evolution layer for AI coding agents.
It captures interaction signals, distills them into learnings, and feeds those learnings back into your agent to improve behavior over time.

Not a chatbot. Not a wrapper. A learning engine.

## Responsible Use (Important)

This repo is dual-use. If you are planning a public release or high-autonomy deployment, read:
- `docs/RESPONSIBLE_PUBLIC_RELEASE.md`
- `docs/security/THREAT_MODEL.md`
- `docs/security/SECRETS_AND_RELEASE_CHECKLIST.md`
- `docs/research/AGI_GUARDRAILS_IMMUTABILITY.md`

Vulnerability reporting: `SECURITY.md`

```
You code -> Spark learns -> Agent adapts -> You code better -> Spark learns more
```

## Install (One Command)

```powershell
# Windows
git clone https://github.com/vibeforge1111/spark-openclaw-installer.git; cd spark-openclaw-installer; .\\install.ps1
```

```bash
# Mac/Linux
git clone https://github.com/vibeforge1111/spark-openclaw-installer.git && cd spark-openclaw-installer && ./install.sh
```

The installer handles Python deps, OpenClaw, Claude CLI, config files, and starts services.
No API keys needed (Claude OAuth only).

## Quickstart

- Newcomer path: `docs/GETTING_STARTED_5_MIN.md`
- Full setup + ops: `docs/QUICKSTART.md`

## What You Get

- Local services:
  - `sparkd` API + ingest pipeline
  - bridge workers and learning/distillation loops (EIDOS)
- Dashboards:
  - Spark Pulse (primary dashboard)
  - Meta-Ralph quality analyzer (aux)
- Tooling:
  - CLI (`spark ...`) for status, services, opportunities, etc.
  - Hook integration for Claude Code (and other agents that can run a hook command)

## Architecture (High-Level)

```
Your Agent (OpenClaw/Claude Code/Cursor)
  -> hooks + tailers capture events
  -> Spark Intelligence processes + distills learnings
  -> context files updated (agent reads and adapts)
  -> dashboards show health, loops, and outcomes
```

## Common Commands

Start/stop services:
```bash
spark up
spark down
spark services
```

Health/status:
```bash
spark health
spark status
```

## Documentation

Primary navigation hub: `docs/DOCS_INDEX.md`

If you use:
- Claude Code: `docs/claude_code.md`
- Cursor/VS Code: `docs/cursor.md`

## Related Repos

- `spark-openclaw-installer`: installer
- `vibeship-spark-pulse`: primary dashboard

---

<p align="center">
  <sub>Built by <a href="https://github.com/vibeforge1111">Vibeforge</a> - AI agents that evolve</sub>
</p>

